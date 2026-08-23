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

### Options

| Flag | Default | Description |
|---|---|---|
| `--links-file FILE` | — | Text file with one URL per line |
| `--model SIZE` | `medium` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large-v2` |
| `--language LANG` | `de` | BCP-47 language code (e.g. `de`, `en`, `fr`) |

## Output

- Downloaded MP3 files are saved to the `downloads/` directory.
- Transcript `.txt` files are saved to the `transcripts/` directory, named by TikTok video ID.
- Each transcript file is prefixed with a header:

```
Video 1
Source: https://www.tiktok.com/@user/video/123
---
<transcript text>
```
