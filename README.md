# Advanced Video Compressor

Python GUI video compressor using FFmpeg.

## Features

- H.264 and H.265 support
- CRF quality slider
- Resolution selection
- Frame rate selection
- Real progress bar
- Cancel compression
- Open output folder when finished

## Build EXE

Place `ffmpeg.exe` in the same folder as the Python script.

```cmd
python -m PyInstaller --onefile --noconsole --add-binary "ffmpeg.exe;." Video_Compress_Tool_by_Vlad.py