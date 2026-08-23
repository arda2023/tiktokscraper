"""
TikTok Scraper & Transcriber – Command-Line Interface

Download individual TikTok videos by URL and transcribe their audio with Whisper.
All transcripts from a single run are written into one combined batch_N.txt file.

Usage:
    # Pass URLs directly on the command line
    python main.py <url1> [<url2> ...] [--model medium] [--language de]

    # Or read URLs from a text file (one per line; # comments and blank lines ignored)
    python main.py --links-file links.txt [--model medium] [--language de]

Examples:
    python main.py https://www.tiktok.com/@user/video/123 https://www.tiktok.com/@user/video/456
    python main.py --links-file my_links.txt --model large-v2 --language en
"""

import argparse
import logging
import re
import sys
from pathlib import Path

import yt_dlp.utils

from downloader import download_single_video
from transcriber import load_model, transcribe_single

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_links_file(path: str) -> list[str]:
    """Read URLs from a text file, skipping blank lines and # comments."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]


def _next_batch_number(output_dir: str) -> int:
    """
    Scan *output_dir* for files matching ``batch_N.txt`` and return the next N.

    Returns 1 if no batch files exist yet.
    """
    pattern = re.compile(r"^batch_(\d+)\.txt$")
    highest = 0
    try:
        for entry in Path(output_dir).iterdir():
            m = pattern.match(entry.name)
            if m:
                highest = max(highest, int(m.group(1)))
    except FileNotFoundError:
        pass
    return highest + 1


def _format_entry(video_num: int, url: str, segments: list) -> str:
    """
    Format a single video's transcript entry for the batch file.

    Each faster-whisper segment gets its own line, giving natural paragraph
    breaks roughly every sentence / 15-20 seconds of speech.
    """
    lines = [f"Video {video_num}", f"Source: {url}", "---"]
    for seg in segments:
        lines.append(seg.text.strip())
    return "\n".join(lines)


def _format_failed_entry(video_num: int, url: str, reason: str) -> str:
    """Format a placeholder entry for a video that could not be processed."""
    return f"Video {video_num} [FAILED - {reason}]\nSource: {url}\n---"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "Download individual TikTok videos by URL and transcribe their audio.\n"
            "All transcripts are combined into a single batch_N.txt file.\n\n"
            "Usage:\n"
            "  python main.py <url1> [<url2> ...] [--model medium] [--language de]\n"
            "  python main.py --links-file links.txt [--model medium] [--language de]"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "urls",
        nargs="*",
        metavar="URL",
        help="One or more TikTok video URLs to download and transcribe.",
    )
    parser.add_argument(
        "--links-file",
        metavar="FILE",
        help=(
            "Path to a text file containing one TikTok video URL per line. "
            "Blank lines and lines starting with # are ignored. "
            "The file is cleared (truncated) after a successful run."
        ),
    )
    parser.add_argument(
        "--model",
        default="medium",
        metavar="SIZE",
        help="Whisper model size (tiny, base, small, medium, large-v2). Default: medium",
    )
    parser.add_argument(
        "--language",
        default="de",
        metavar="LANG",
        help="BCP-47 language code for transcription (e.g. de, en, fr). Default: de",
    )
    args = parser.parse_args()

    # ── Collect URLs ─────────────────────────────────────────────────────────
    urls: list[str] = list(args.urls or [])

    if args.links_file:
        try:
            file_urls = _load_links_file(args.links_file)
        except OSError as exc:
            parser.error(f"Cannot read --links-file '{args.links_file}': {exc}")
        urls.extend(file_urls)

    if not urls:
        parser.error(
            "No URLs provided. Pass URLs as positional arguments or use --links-file."
        )

    model_size: str = args.model
    language: str = args.language
    output_dir_downloads = "downloads"
    output_dir_transcripts = "transcripts"

    n_links = len(urls)
    print(f"\n=== Processing {n_links} link(s) | model: {model_size} | lang: {language} ===\n")

    # ── Load model once for the whole batch ──────────────────────────────────
    print("Loading Whisper model…")
    model = load_model(model_size)
    print()

    # ── Determine batch output file ──────────────────────────────────────────
    Path(output_dir_transcripts).mkdir(parents=True, exist_ok=True)
    batch_n = _next_batch_number(output_dir_transcripts)
    batch_path = Path(output_dir_transcripts) / f"batch_{batch_n}.txt"

    # ── Per-video download + transcribe loop ─────────────────────────────────
    n_downloaded = 0
    n_transcribed = 0
    batch_entries: list[str] = []

    for video_num, url in enumerate(urls, start=1):
        print(f"[{video_num}/{n_links}] {url}")

        # -- Download --------------------------------------------------------
        mp3_path: str | None = None
        try:
            mp3_path = download_single_video(url, output_dir=output_dir_downloads)
            n_downloaded += 1
            print(f"    [download] ✓ {mp3_path}")
        except (yt_dlp.utils.DownloadError, RuntimeError) as exc:
            reason = "could not download"
            print(f"    [download] ✗ FAILED – {exc}", file=sys.stderr)
            batch_entries.append(_format_failed_entry(video_num, url, reason))
            print()
            continue

        # -- Transcribe ------------------------------------------------------
        try:
            segments = transcribe_single(mp3_path, model, language=language)
            n_transcribed += 1
            print(f"    [transcribe] ✓ {len(segments)} segment(s)")
            batch_entries.append(_format_entry(video_num, url, segments))
        except Exception as exc:  # noqa: BLE001
            reason = "transcription error"
            print(f"    [transcribe] ✗ FAILED – {exc}", file=sys.stderr)
            batch_entries.append(_format_failed_entry(video_num, url, reason))

        print()  # blank line between videos in console output

    # ── Write combined batch file ─────────────────────────────────────────────
    batch_path.write_text("\n\n".join(batch_entries) + "\n", encoding="utf-8")

    # ── Clear links file if it was used ──────────────────────────────────────
    if args.links_file:
        Path(args.links_file).write_text("", encoding="utf-8")
        print(f"Cleared links file: {args.links_file}")

    # ── Summary ──────────────────────────────────────────────────────────────
    print("=== Summary ===")
    print(f"  Links provided          : {n_links}")
    print(f"  Downloaded successfully : {n_downloaded}")
    print(f"  Transcribed successfully: {n_transcribed}")
    if n_downloaded - n_transcribed > 0:
        print(f"  Transcription failures  : {n_downloaded - n_transcribed}")
    print(f"  Batch transcript file   : {batch_path}")


if __name__ == "__main__":
    main()
