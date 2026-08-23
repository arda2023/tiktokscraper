import os
import random
import time

import yt_dlp
import yt_dlp.utils


# ---------------------------------------------------------------------------
# Shared yt-dlp options factory
# ---------------------------------------------------------------------------

def _ydl_opts(output_dir: str, hooks: list) -> dict:
    """Return a yt-dlp options dict for audio extraction."""
    return {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
        }],
        "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
        "ignoreerrors": True,
        "progress_hooks": hooks,
    }


# ---------------------------------------------------------------------------
# Batch download (by username / profile URL)
# ---------------------------------------------------------------------------

def download_audio(username: str, output_dir: str = "downloads", progress_callback=None) -> list[str]:
    """
    Download all audio from a public TikTok profile using yt-dlp.

    Args:
        username:          TikTok username (without @).
        output_dir:        Directory where MP3 files are saved.
        progress_callback: Optional callable invoked with the yt-dlp progress
                           dict whenever a file finishes downloading.

    Returns:
        List of absolute paths to the downloaded MP3 files.
    """
    url = f"https://www.tiktok.com/@{username}"

    os.makedirs(output_dir, exist_ok=True)

    downloaded_files: list[str] = []

    def hook(d: dict) -> None:
        if d["status"] == "finished":
            video_id = d.get("info_dict", {}).get("id", "")
            if video_id:
                mp3_filepath = os.path.join(output_dir, f"{video_id}.mp3")
                if mp3_filepath not in downloaded_files:
                    downloaded_files.append(mp3_filepath)

            if progress_callback:
                progress_callback(d)

            # Polite delay to avoid rate-limiting
            time.sleep(random.uniform(1, 3))

    with yt_dlp.YoutubeDL(_ydl_opts(output_dir, [hook])) as ydl:
        ydl.download([url])

    return downloaded_files


# ---------------------------------------------------------------------------
# Single-video download (by direct URL)
# ---------------------------------------------------------------------------

def download_single_video(url: str, output_dir: str = "downloads") -> str:
    """
    Download one specific TikTok video as an MP3.

    Args:
        url:        Full TikTok video URL
                    (e.g. ``https://www.tiktok.com/@user/video/123456``).
        output_dir: Directory where the MP3 file is saved.

    Returns:
        Absolute path to the downloaded MP3 file.

    Raises:
        RuntimeError: If yt-dlp does not produce an output file (private video,
                      deleted video, network error, etc.).
        yt_dlp.utils.DownloadError: Propagated from yt-dlp on hard failures.
    """
    os.makedirs(output_dir, exist_ok=True)

    downloaded: list[str] = []

    def hook(d: dict) -> None:
        if d["status"] == "finished":
            video_id = d.get("info_dict", {}).get("id", "")
            if video_id:
                mp3_filepath = os.path.join(output_dir, f"{video_id}.mp3")
                if mp3_filepath not in downloaded:
                    downloaded.append(mp3_filepath)

    # For a single URL we want errors to propagate, so override ignoreerrors.
    opts = _ydl_opts(output_dir, [hook])
    opts["ignoreerrors"] = False

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    if not downloaded:
        raise RuntimeError(
            f"Download produced no output file for URL: {url}\n"
            "The video may be private, deleted, or geo-restricted."
        )

    return downloaded[0]
