# TikTok Scraper & Transcriber

A Python command-line tool to download individual TikTok videos by URL and transcribe their audio using [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

## Setup Instructions

1. Ensure Python 3.11 is installed.
2. Create a virtual environment:
   ```cmd
   py -3.11 -m venv venv
   ```
3. Activate the virtual environment:
   - Windows (Command Prompt): `venv\Scripts\activate.bat`
   - Windows (PowerShell): `venv\Scripts\Activate.ps1`
4. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
5. Ensure `ffmpeg` is installed and available in your system PATH.

## Usage

### Pass URLs directly

```cmd
python main.py <url1> [<url2> ...] [--model medium] [--language de]
```

```cmd
python main.py https://www.tiktok.com/@user/video/123 https://www.tiktok.com/@user/video/456
```

### Read URLs from a file

Create a plain-text file with one TikTok video URL per line.  
Blank lines and lines starting with `#` are ignored.

```
# links.txt
https://www.tiktok.com/@user/video/123
https://www.tiktok.com/@user/video/456
```

```cmd
python main.py --links-file links.txt [--model large-v2] [--language en]
```

> **Auto-clear:** When `--links-file` is used, the file is automatically truncated to empty after the run completes, so it's ready for the next batch of links.

### Options

| Flag | Default | Description |
|---|---|---|
| `--links-file FILE` | — | Text file with one URL per line (cleared after run) |
| `--model SIZE` | `medium` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large-v2` |
| `--language LANG` | `de` | BCP-47 language code (e.g. `de`, `en`, `fr`) |

## Output

- Downloaded MP3 files are saved to the `downloads/` directory.
- All transcripts from a single run are written into **one combined file** inside `transcripts/`, named `batch_N.txt` where `N` auto-increments (e.g. `batch_1.txt`, `batch_2.txt`, …).

### Batch file format

Each video gets its own section, separated by a blank line:

```
Video 1
Source: https://www.tiktok.com/@user/video/123
---
First segment text.
Second segment text.
Third segment text.

Video 2
Source: https://www.tiktok.com/@user/video/456
---
Segment text here.
```

Each line of transcript text corresponds to one faster-whisper segment (roughly one sentence or 15–20 seconds of speech), giving natural paragraph breaks.

### Failed videos

If a video fails to download or transcribe, a placeholder entry is written so the numbering stays consistent with the original link list:

```
Video 2 [FAILED - could not download]
Source: https://www.tiktok.com/@user/video/456
---
```
