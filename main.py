"""
TikTok Scraper & Transcriber – Command-Line Interface

Download individual TikTok videos by URL and transcribe their audio with Whisper.

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
import sys
from pathlib import Path

import yt_dlp.utils

from downloader import download_single_video
from transcriber import transcribe_files

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


def _transcribe_progress(file_name: str, success: bool, index: int, total: int) -> None:
    """Progress callback for transcribe_files."""
    status = "✓" if success else "✗"
    label = "ok" if success else "FAILED"
    print(f"    [transcribe] {status} {file_name}  [{label}]")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "Download individual TikTok videos by URL and transcribe their audio.\n\n"
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
            "Blank lines and lines starting with # are ignored."
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

    # ── Collect URLs from both sources ──────────────────────────────────────
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

    # ── Per-video download + transcribe loop ─────────────────────────────────
    n_downloaded = 0
    n_transcribed = 0

    for video_num, url in enumerate(urls, start=1):
        print(f"[{video_num}/{n_links}] {url}")

        # -- Download --------------------------------------------------------
        mp3_path: str | None = None
        try:
            mp3_path = download_single_video(url, output_dir=output_dir_downloads)
            n_downloaded += 1
            print(f"    [download] ✓ saved to {mp3_path}")
        except (yt_dlp.utils.DownloadError, RuntimeError) as exc:
            print(f"    [download] ✗ FAILED – {exc}", file=sys.stderr)
            continue  # skip transcription for this video

        # -- Transcribe ------------------------------------------------------
        results = transcribe_files(
            file_paths=[mp3_path],
            output_dir=output_dir_transcripts,
            model_size=model_size,
            language=language,
            progress_callback=_transcribe_progress,
            source_urls=[url],
            video_numbers=[video_num],
        )

        if results:
            n_transcribed += 1
        print()  # blank line between videos

    # ── Summary ──────────────────────────────────────────────────────────────
    print("=== Summary ===")
    print(f"  Links provided          : {n_links}")
    print(f"  Downloaded successfully : {n_downloaded}")
    print(f"  Transcribed successfully: {n_transcribed}")
    if n_downloaded - n_transcribed > 0:
        print(f"  Transcription failures  : {n_downloaded - n_transcribed}")
    print(f"  Transcript files saved to: '{output_dir_transcripts}/'")


if __name__ == "__main__":
    main()
