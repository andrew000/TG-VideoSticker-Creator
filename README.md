# TG-VideoSticker-Creator

[![MIT License](https://img.shields.io/github/license/andrew000/TG-VideoSticker-Creator)](https://opensource.org/licenses/MIT)

A simple script to create video stickers for Telegram.
Just for fun. Not for production.

⚠️ Be careful, this script may create a video sticker longer than 3 seconds limit by Telegram

## Requirements

- Python 3.10+

## Installation

- Install Python 3.10+ from [here](https://www.python.org/downloads/)
- Download ffmpeg and ffprobe from [here](https://www.gyan.dev/ffmpeg/builds/#release-builds)
- Extract the downloaded zip file and copy the `ffmpeg.exe` and `ffprobe.exe` files to the same directory as the script.

## Usage

- Put the video file in the same directory as the script.
- Rename the video file to `input_video.mp4`.
- Run the script using `python main.py`.
- It may take a while to process the video.
- The output webm parts will be in the `output` directory.
- Finally, you can send the webm parts to t.me/stickers bot to create a video sticker.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
