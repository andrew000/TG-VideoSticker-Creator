import subprocess
import os
from multiprocessing import Pool, cpu_count
from pathlib import Path
from time import perf_counter

SLICES_DIR_PATH = Path("slices")
PARTS_DIR_PATH = Path("parts")

SLICES_DIR_PATH.mkdir(exist_ok=True)
PARTS_DIR_PATH.mkdir(exist_ok=True)

if os.name == 'nt':
    ffmpeg = './ffmpeg.exe'
    ffprobe = './ffprobe.exe'
else:
    ffmpeg = 'ffmpeg'
    ffprobe = 'ffprobe'

class Slice:
    def __init__(self, slice_id: int):
        self.id = slice_id
        self.name = f"slice_{slice_id}.mp4"
        self.path = SLICES_DIR_PATH / self.name

    def __repr__(self):
        return f"Slice(id={self.id}, name={self.name}, path={self.path})"


class Part:
    def __init__(self, part_id: int, path: Path):
        self.id = part_id
        self.name = f"part_{part_id}.webm"
        self.path = path

    def __repr__(self):
        return f"Part(id={self.id}, path={self.path})"


def get_duration(path: Path) -> float:
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return float(result.stdout)


def format_time(seconds: float) -> str:
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"


def cleanup():
    for path in SLICES_DIR_PATH.iterdir():
        path.unlink()

    for path in PARTS_DIR_PATH.iterdir():
        path.unlink()


def slice_video(path: Path, start: float, end: float, output: Path):
    # .\ffmpeg.exe -loglevel quiet -u -i $path -ss $start -to $end -c copy $output
    subprocess.run(
        [
            ffmpeg,
            "-loglevel",
            "quiet",
            "-y",
            "-i",
            path,
            "-ss",
            str(start),
            "-to",
            str(end),
            "-c",
            "copy",
            output,
        ]
    )


def make_video_slices(input_video: Path, slice_range_durations: list[int], slices: list[Slice]):
    tasks = []

    with Pool(processes=cpu_count() // 2 or 1) as pool:
        for video_slice in slices:
            start = slice_range_durations[video_slice.id]
            end = slice_range_durations[video_slice.id + 1]
            print(f"Creating {video_slice.name}")
            task = pool.starmap_async(slice_video, [(input_video, start, end, video_slice.path)])
            tasks.append(task)

        for task in tasks:
            task.wait()


def make_webm(video_slice: Slice, fps: int, part: Part):
    # .\ffmpeg.exe -loglevel quiet -y -i $video_slice -c:v libvpx-vp9 -vf scale=512:-1
    # -r $fps -b:v 4k -an $output
    print(f"Converting {video_slice.name} to {part.name}")

    subprocess.run(
        [
            ffmpeg,
            "-loglevel",
            "quiet",
            "-y",
            "-i",
            video_slice.path,
            "-c:v",
            "libvpx-vp9",
            "-vf",
            "scale=512:-1",
            "-r",
            str(fps),
            "-b:v",
            "4k",
            "-an",
            part.path,
        ]
    )
    print(f"Converted {video_slice.name} to {part.name}")


def make_webm_parts_from_video_slices(video_slices: list[Slice], parts: list[Part], fps: int = 10):
    tasks = []

    with Pool(processes=cpu_count() // 2 or 1) as pool:
        for part, video_slice in zip(parts, video_slices):
            task = pool.starmap_async(make_webm, [(video_slice, fps, part)])
            tasks.append(task)

        for task in tasks:
            task.wait()


def check_sizes(parts: list[Part]) -> list[tuple[Part, int]]:
    """
    Check if all parts are the allowed size.
    Will return a list of tuples with the part and the size in bytes.
    """
    return [
        (part, size) for part, size in zip(parts, [part.path.stat().st_size for part in parts]) if size >= 256000
    ]


def main():
    cleanup()

    input_video = Path("input_video.mp4")
    duration = get_duration(input_video)
    print(f"Duration of {input_video.name}: {format_time(duration)}")

    slice_range_durations = [i for i in range(0, int(duration), 120)]

    if slice_range_durations[-1] != duration:
        slice_range_durations.append(int(duration))

    print(f"Splitting into {len(slice_range_durations) - 1} slices")
    video_slices = [Slice(i) for i in range(len(slice_range_durations) - 1)]
    make_video_slices(input_video, slice_range_durations, video_slices)
    print(f"Splitting done. {len(video_slices)} slices created")

    parts = [
        Part(video_slice.id, PARTS_DIR_PATH / f"part_{video_slice.id}.webm")
        for video_slice in video_slices
    ]
    make_webm_parts_from_video_slices(video_slices, parts)
    print(f"Converting done. {len(parts)} parts created")

    fps = 9
    while (bad_parts := check_sizes(parts)) and (fps > 0):
        print(f"Bad parts: {bad_parts}")
        bad_video_slices = [video_slices[bad_part[0].id] for bad_part in bad_parts]
        print(f"Bad video slices: {bad_video_slices}")

        print(f"Trying to convert with {fps=}")
        make_webm_parts_from_video_slices(bad_video_slices, [bad_part[0] for bad_part in bad_parts], fps)
        print(f"Converting done. {len(parts)} parts created")

        for bad_part in bad_parts:
            parts[bad_part[0].id] = bad_part[0]

        fps -= 1

    if fps == 0:
        print("Could not convert all parts to the allowed size. Exiting...")
        return

    for part in parts:
        data = bytearray(part.path.read_bytes())
        data[254:255] = b"\x30"
        part.path.write_bytes(data)


if __name__ == "__main__":
    start_time = perf_counter()
    main()
    print(f"Done in {perf_counter() - start_time:.2f}s")
