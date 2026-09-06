# Teligram3 YouTube bot

The bot accepts public YouTube URLs and sends either an MP3 audio file or an
MP4 video file to Telegram. It does not use cookies, login credentials, or any
other method to bypass private, DRM-protected, or access-controlled content.

## Configuration

Set `BOT_TOKEN` in the environment before starting the bot:

```sh
set BOT_TOKEN=your_token_here
python main.py
```

`MAX_FILE_SIZE` optionally sets the local size limit in bytes. It defaults to
49 MiB, below Telegram Bot API's commonly enforced 50 MB upload limit.

## ffmpeg

Install `ffmpeg` and make both `ffmpeg` and `ffprobe` available on `PATH`.
yt-dlp needs them to extract MP3 audio and merge separate video/audio streams.
The hosting runtime must include these binaries; installing the Python package
alone is not sufficient.

## Runtime

Install Python dependencies with `pip install -r requirements.txt`. The
included `Procfile` starts the polling bot with `python main.py`.
