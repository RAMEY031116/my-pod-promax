# 🎵 My pod promax

**By Bipzilla** — a pink, iPod-inspired music-library organiser built with Python and Streamlit.

My pod promax helps you import audio you are authorised to use, read track information from supported video links, organise tracks, convert audio to MP3, embed available cover artwork and export files for your personal music library.

> **Which version is on GitHub?** This branch contains a **lightweight standalone Streamlit edition**. It is not a byte-for-byte copy of the larger downloadable project previously shared in ChatGPT. Some advanced artwork-repair and catalogue-fallback functions from that edition are **not included** here. This project has not yet been verified end-to-end on macOS or mobile.

## What you can do

- Search for artist and album names using a music catalogue (discovery only).
- Paste supported links or upload a TXT file of links.
- Preview available track information and choose which entries to process.
- Upload your own audio and optionally provide cover art.
- Convert supported audio to MP3 (requires FFmpeg).
- Embed ID3 information: title, artist, album, and available cover artwork.
- Download MP3 files individually or together as a ZIP.
- Access a responsive interface from a computer or phone browser.

**Important:** A catalogue entry is not an audio download. Some media sites prohibit downloading recordings without authorisation. Only process files and links you have permission to save. Artwork is best-effort and may not be available or match the official album.

---

## 1. Before installing

You need:

| Requirement | Why you need it |
| --- | --- |
| **Python 3.10 or newer** | Runs the application |
| **FFmpeg** | Converts audio to MP3 |
| **Internet access** | Searches catalogues and retrieves permitted media/metadata |
| **Free disk space** | Holds temporary downloads and converted MP3s |
| **A browser** | Displays the Streamlit interface |

For large batches, keep **at least 5–10 GB free**, preferably more. Final MP3 size is not the same as peak temporary space usage.

### Check whether Python and FFmpeg are installed

Open **Terminal** on macOS or Linux, or **PowerShell** on Windows:

```bash
python3 --version
ffmpeg -version
```

On Windows, try `py --version` if `python3` is not recognised.

**macOS installation:** Install Python 3.10+ from [python.org](https://www.python.org/downloads/) or Homebrew. With Homebrew, install FFmpeg using `brew install ffmpeg`. If you do not have Homebrew, see the [FFmpeg download page](https://ffmpeg.org/download.html).

**Windows installation:** Install Python from [python.org](https://www.python.org/downloads/) and ensure the launcher is available. Install FFmpeg from an appropriate package manager or the [FFmpeg download page](https://ffmpeg.org/download.html), then ensure `ffmpeg` is on PATH.

**Linux:** Install Python, the `venv` package, and FFmpeg using your distribution's package manager.

---

## 2. Download or clone the project

You can download this branch from GitHub using **Code → Download ZIP**, then extract the archive. Alternatively, use Git:

```bash
git clone --branch responsive-mobile-desktop https://github.com/RAMEY031116/my-pod-promax.git
cd my-pod-promax
```

**Important:** The GitHub repository uses the folder name `my-pod-promax`. If you extracted a separate ZIP named `My pod promax`, use that actual folder name in the commands below.

In your terminal, check where you are:

```bash
pwd
ls -la
```

You should see `app.py`, `requirements.txt`, and `start_mac.sh` (on the branch containing the app).

---

## 3. Start on macOS (recommended)

Open the macOS Terminal app **or** the terminal inside VS Code. Both work.

If you cloned the repo and are already inside it:

```bash
chmod +x start_mac.sh
./start_mac.sh
```

If your extracted folder is in Downloads, first navigate to its **exact** folder name:

```bash
cd ~/Downloads/"My pod promax"
ls -la
chmod +x start_mac.sh
./start_mac.sh
```

If that `cd` command fails, inspect your Downloads folder with `ls -la ~/Downloads`. It might be called `My pod promax 5` or something else.

The launcher creates a dedicated `.venv` environment (if needed), installs the required Python packages into it, and starts Streamlit.

**Do not launch the app with `/usr/bin/python3 app.py`.** On some Macs, the system Python does not have your project dependencies and may use older SSL libraries.

When Streamlit starts, it prints a **Local URL**, usually:

**http://localhost:8501**

Open that URL in your browser. Keep the terminal open while using the app. To stop it, press **Control+C** in that terminal.

### Alternative: manual Python environment on macOS

If the launcher is missing or doesn't work, run the following **inside the directory containing `app.py`**:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Always use `python -m pip` and `python -m streamlit` from the **same active virtual environment**. This prevents the `mutagen` error caused by installing packages into one Python environment but running another.

---

## 4. Start on Windows

Open **PowerShell** in the project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Then open **http://localhost:8501**. This uses the project's own Python environment without needing to activate it.

## 5. Start on Linux

From the project folder:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m streamlit run app.py
```

Open the Local URL printed by Streamlit.

---

## 6. Using My pod promax

### A. Search for an artist or album

1. Open the **Discover** tab.
2. Enter an artist or album name in the search field.
3. Select **Artists** or **Albums**.
4. Press **Search catalogue**.
5. Review the returned names and release information.

**Note:** The lightweight GitHub edition displays catalogue results; it does not turn a catalogue result directly into a downloadable recording.

### B. Import a YouTube link or TXT file

1. Open **Import links & audio**.
2. Paste a permitted video link into the large text field. For multiple tracks, place one URL on each line.
3. Alternatively, upload a `.txt` file containing the URLs.
4. Press **Preview links** to retrieve available title and uploader information.
5. Tick the tracks you want.
6. Press **Process selected links**.
7. Watch the status messages and handle any failures individually.
8. Open **My library** to download completed MP3s.

An invalid or restricted video link may fail, even when the address looks correct. Please respect the source site's rules and rights holders' permissions.

### C. Upload your own audio

1. In **Import links & audio**, scroll to **Upload an audio file**.
2. Choose a supported file, such as MP3, WAV, FLAC, M4A, OGG or AAC.
3. Edit **Song title**, **Artist**, and optionally **Album**.
4. Optionally upload a JPG, PNG or WebP cover image that you have permission to use.
5. Select **Convert and embed metadata**.
6. Download the resulting MP3 from **My library**.

### D. Export a batch and start another

- In **My library**, choose **Download MP3** for an individual song.
- Choose **Download entire library as ZIP** for all processed tracks.
- Use **New batch** in the import tab to clear the current link selection (completed library entries remain in the running session).
- Download your results before closing or resetting your app environment. This lightweight edition stores library data in Streamlit session memory rather than as a permanent account-based archive.

### E. Use the interface on your phone

1. Start Streamlit on your computer.
2. Connect your phone and computer to the same trusted Wi-Fi.
3. Find the **Network URL** in the computer's terminal output (for example, `http://192.168.x.x:8501`).
4. Open **that Network URL** in your phone browser.

Do not use `localhost:8501` on the phone; that refers to the phone itself. This is a **responsive website**, not a standalone iOS or Android application. Avoid exposing your local development server directly to the public internet.

---

## 7. Troubleshooting: common errors and how to fix them

### Error: `ModuleNotFoundError: No module named 'mutagen'`

**Cause:** You are probably running a different Python installation from the one where dependencies were installed.

**Fix on macOS:**

```bash
pwd
ls -la
./start_mac.sh
```

If the launcher is not present, follow the **manual Python environment** instructions in section 3. Avoid `/usr/bin/python3 app.py`. Installing packages with `pip` is not enough if `pip` belongs to another environment.

### Error: `start_mac.sh: No such file or directory`

**Cause:** Your terminal is in the wrong directory, or you extracted a different project version.

**Fix:**

```bash
pwd
ls -la
ls -la ~/Downloads
```

Navigate into the folder that actually contains `start_mac.sh`, then run it. Folder names with spaces require quotes: `cd ~/Downloads/"My pod promax 5"`.

### Error: `[Errno 28] No space left on device`

**Cause:** Your disk or temporary storage is full. A download may begin successfully but fail midway through writing.

**Fix:**

1. Stop processing with **Control+C**.
2. Check available storage:

   ```bash
   df -h /
   df -h /tmp
   ```

3. On macOS, open **System Settings → General → Storage** and review what uses space.
4. Find large folders **without deleting anything**:

   ```bash
   du -sh ~/Downloads ~/Movies ~/Music ~/Documents ~/Desktop ~/Library/Caches 2>/dev/null
   du -sh ~/Downloads/*(N) 2>/dev/null | sort -h | tail -20
   du -sh "${TMPDIR:-/tmp}" 2>/dev/null
   ```

5. Move or delete **only files you recognise and no longer need**; then empty Trash if appropriate.
6. Aim for **5–10 GB or more** of available space before large batches.
7. Recheck with `df -h /`. Test **one song**, then five, before restarting a large batch.

**Safety:** Never blindly erase `/tmp`, `~/Library`, `.venv`, or unknown system files. The `/` and `/tmp` reports on a Mac can refer to the same underlying disk, so do not add their available-space figures together.

### Error: `Postprocessing: audio conversion failed: Conversion failed!`

This is a general FFmpeg conversion error. **Disk space is one possible cause, not the only one.**

1. Confirm available storage with `df -h /`.
2. Confirm FFmpeg works with `ffmpeg -version`.
3. Restart My pod promax and try one permitted audio file or source.
4. If it still fails with plenty of space, copy the **full error immediately before and after the FFmpeg failure** into a GitHub issue. The generic message alone does not identify the exact cause.

Do not add a fixed delay for this error: delays will not repair a missing encoder, full disk or invalid audio stream.

### Error: `zsh: no matches found: /Users/.../Downloads/*`

This is a **Zsh wildcard-matching** message, not a My pod promax error. Try:

```bash
ls -la ~/Downloads
du -sh ~/Downloads/*(N) 2>/dev/null
```

The `(N)` qualifier means that the command won't error if there are no matching files.

### Artist or album search is unavailable

- Check that your connection works.
- Try a simpler name (artist only or album only).
- If the provider returns HTTP **429**, wait before retrying because it may be rate-limiting requests.
- If you see a timeout or SSL error, note the exact message when reporting it.
- The catalogue may have incomplete data; a missing result is not proof that a song or album doesn't exist.

### Cover artwork is missing

The lightweight GitHub edition embeds cover artwork when an available supported source provides it, or when you upload your own image for a local audio file. It cannot guarantee an official album sleeve or automatic matching for every track. If no cover is found, the audio may still be exported.

### Buttons look black or text is unreadable

1. Stop Streamlit using **Control+C**.
2. Check that `.streamlit/config.toml` exists in the project.
3. Restart the app.
4. Hard-refresh your browser with **Command+Shift+R** on macOS or **Ctrl+Shift+R** on Windows.

The intended theme is **pink primary buttons with white text**, and **white secondary buttons with dark text**.

### The browser cannot connect to Streamlit

- Make sure the terminal running Streamlit remains open.
- Use the **Local URL** shown in the latest terminal output; Streamlit may choose another port if 8501 is busy.
- On a phone, use the computer's **Network URL** and the same Wi-Fi, not localhost.
- Check any local firewall if the Network URL is inaccessible.

---

## 8. Reporting a bug

Open a GitHub issue and include:

1. What you were trying to do (search, upload, convert, download).
2. Your computer's operating system and Python version.
3. The exact error message from the terminal.
4. Steps to reproduce it with **one** non-sensitive example.
5. Whether it happens for all songs or only one.

**Do not post passwords, tokens, private file paths, personal music collections or session cookies.** Screenshots are useful, but review them for private information first.

## 9. For contributors

This is an early-stage open-source project. Keep the existing colour palette and accessibility contrast consistent, document new dependencies, test fixes on mobile and desktop, and avoid committing media files or temporary environments. The repository's `.gitignore` excludes common generated files.

To contribute, create a branch and open a pull request describing what changed and how you tested it. Avoid adding arbitrary waits to audio processing; retry/backoff belongs only around specific transient network failures, ideally with bounded attempts and clear errors.

---

Made with Python, Streamlit, FFmpeg, yt-dlp, Mutagen and Pillow. **By Bipzilla.**
