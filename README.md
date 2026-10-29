# My pod promax
**by Bipzilla** · iPod-inspired music library organiser.

## Repository status
This branch contains a **lightweight standalone Streamlit edition** of My pod promax (`app.py`, dependencies, launcher and theme). It is **not a byte-for-byte copy** of the larger downloadable project ZIP: advanced catalogue fallback, artwork repair and the original project modules are not included here. The application has not been tested end-to-end on macOS or a phone.

## Features in the mobile/desktop build
- Pink-and-white responsive interface with readable high-contrast buttons
- Artist and album discovery
- Import authorised links, TXT link lists and your own audio
- Convert to MP3, embed available cover artwork and ID3 metadata
- Export individual MP3s or a ZIP; clear a batch without deleting completed tracks

## Install
Requires Python 3.10+ and FFmpeg.

### macOS
```bash
cd "My pod promax"
chmod +x start_mac.sh
./start_mac.sh
```
Do **not** run `/usr/bin/python3 app.py`. The launcher uses one virtual environment with the required dependencies.

### Windows
```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### Linux
```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m streamlit run app.py
```

Open http://localhost:8501 on your computer.

## Phone access
Run Streamlit on your computer, keep it running, and open the **Network URL** shown in its terminal on a phone connected to the same Wi-Fi. `localhost` on the phone does not point to your Mac. This is a responsive web layout, **not** an iOS/Android native app. Do not expose the development server directly to the public internet.

## Colour and accessibility
Primary buttons: pink `#d84e92` with **white** text; hover `#b93274`. Secondary buttons: white with **dark** text `#41283e`. The mobile layout uses smaller margins, a compact hero, horizontally scrollable navigation, and touch-friendly controls.

Music catalogue information does not itself grant access to recordings. Only download audio you have permission to save.

## Troubleshooting: batch conversion and disk space
If you see `[Errno 28] No space left on device` or FFmpeg conversion failures, **stop the batch** (Ctrl+C) and check free disk space:

```bash
df -h /
ffmpeg -version
```

Free at least 5–10 GB before retrying a big batch. Restart with `./start_mac.sh` from the project directory, process **one** permitted source to verify conversion, then try five songs. Do not repeatedly retry a 100-song batch while storage is low. The app may need extra temporary space for both the source audio and the resulting MP3.

**Do not add an arbitrary delay to fix these errors.** Delays can help only when a remote service explicitly reports rate limiting (HTTP 429); they do not repair disk-full or FFmpeg failures. This edition's batch code has not been modified to add such delays.
