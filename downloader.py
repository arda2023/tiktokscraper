import yt_dlp
import os
import time
import random

def download_audio(username: str, output_dir: str = "downloads", progress_callback=None) -> list[str]:
    """
    Download audio from TikTok using yt-dlp.
    """
    url = f"https://www.tiktok.com/@{username}"
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    downloaded_files = []

    def hook(d):
        if d['status'] == 'finished':
            # Collect the final expected mp3 filename
            video_id = d.get('info_dict', {}).get('id', '')
            if video_id:
                mp3_filepath = os.path.join(output_dir, f"{video_id}.mp3")
                if mp3_filepath not in downloaded_files:
                    downloaded_files.append(mp3_filepath)
            
            if progress_callback:
                progress_callback(d)
            
            # Add a random delay between 1 and 3 seconds
            time.sleep(random.uniform(1, 3))

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'ignoreerrors': True,
        'progress_hooks': [hook],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return downloaded_files
