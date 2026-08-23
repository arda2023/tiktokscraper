"""
TikTok Scraper & Transcriber – Command-Line Interface

Usage:
    python main.py <username> [--model medium] [--language de]

Examples:
    python main.py someuser
    python main.py someuser --model large-v2 --language en
"""

import argparse
import sys

import yt_dlp.utils

from downloader import download_audio
from transcriber import transcribe_files


# ---------------------------------------------------------------------------
# Progress callbacks
# ---------------------------------------------------------------------------

def _download_progress(d: dict) -> None:
    """Called by yt-dlp after each file finishes downloading."""
    info = d.get("info_dict", {})
    video_id = info.get("id", "unknown")
    title = info.get("title", video_id)
    print(f"  [download] ✓ {title} ({video_id})")


def _transcribe_progress(file_name: str, success: bool, index: int, total: int) -> None:
    """Called by transcribe_files after each file is processed."""
    status = "✓" if success else "✗"
    label = "ok" if success else "FAILED"
    print(f"  [transcribe] {status} ({index}/{total}) {file_name}  [{label}]")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "Download every TikTok audio clip from a public account and "
            "transcribe them with Whisper.\n\n"
            "Usage:  python main.py <username> [--model medium] [--language de]"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "username",
        help="TikTok username (without @) whose videos should be scraped.",
    )
    parser.add_argument(
        "--model",
        default="medium",
        metavar="SIZE",
        help=(
            "Whisper model size to use for transcription "
            "(e.g. tiny, base, small, medium, large-v2). Default: medium"
        ),
    )
    parser.add_argument(
        "--language",
        default="de",
        metavar="LANG",
        help="BCP-47 language code for transcription (e.g. de, en, fr). Default: de",
    )
    args = parser.parse_args()

    username: str = args.username
    model_size: str = args.model
    language: str = args.language
    output_dir_downloads = "downloads"
    output_dir_transcripts = "transcripts"

    # ------------------------------------------------------------------
    # Step 1 – Download
    # ------------------------------------------------------------------
    print(f"\n=== Downloading audio from @{username} ===")
    try:
        downloaded_files = download_audio(
            username=username,
            output_dir=output_dir_downloads,
            progress_callback=_download_progress,
        )
    except yt_dlp.utils.DownloadError as exc:
        # Covers private/nonexistent accounts and similar hard errors
        print(
            f"\nError: could not download videos for @{username}.\n"
            f"The account may be private, banned, or does not exist.\n"
            f"Details: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    n_downloaded = len(downloaded_files)
    print(f"\nDownloaded {n_downloaded} file(s) to '{output_dir_downloads}/'.")

    if n_downloaded == 0:
        print("Nothing to transcribe. Exiting.")
        sys.exit(0)

    # ------------------------------------------------------------------
    # Step 2 – Transcribe
    # ------------------------------------------------------------------
    print(f"\n=== Transcribing with model '{model_size}' (language: {language}) ===")
    results = transcribe_files(
        file_paths=downloaded_files,
        output_dir=output_dir_transcripts,
        model_size=model_size,
        language=language,
        progress_callback=_transcribe_progress,
    )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    n_transcribed = len(results)
    n_failed = n_downloaded - n_transcribed
    print("\n=== Summary ===")
    print(f"  Videos downloaded   : {n_downloaded}")
    print(f"  Successfully transcribed: {n_transcribed}")
    if n_failed:
        print(f"  Failed to transcribe    : {n_failed}")
    print(f"  Transcript files saved to: '{output_dir_transcripts}/'")


if __name__ == "__main__":
    main()
