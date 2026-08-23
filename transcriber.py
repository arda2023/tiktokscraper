import logging
import os
from pathlib import Path
from typing import Callable, Optional

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


def _load_model(model_size: str, use_gpu: bool = False) -> WhisperModel:
    """
    Load the WhisperModel on CPU (default) or CUDA.

    GPU support is kept but disabled by default while the CUDA DLL loading
    issue is being resolved.  Set ``use_gpu=True`` to re-enable it once
    cublas64_12.dll / cudnn can be located reliably at runtime.

    Args:
        model_size: The Whisper model size to load (e.g. "medium", "large-v2").
        use_gpu:    When True, attempt CUDA (float16) and fall back to CPU
                    (int8) on failure.  When False (default), always use CPU.

    Returns:
        A loaded WhisperModel instance.
    """
    if use_gpu:
        # --- GPU path (re-enable once CUDA DLL issue is resolved) ---
        try:
            model = WhisperModel(model_size, device="cuda", compute_type="float16")
            logger.info("Loaded WhisperModel '%s' on CUDA with float16.", model_size)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to load WhisperModel on CUDA (%s). Falling back to CPU with int8.", exc
            )
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            logger.info("Loaded WhisperModel '%s' on CPU with int8.", model_size)
    else:
        # --- CPU path (forced while CUDA DLL loading is unreliable) ---
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        logger.info("Loaded WhisperModel '%s' on CPU with int8.", model_size)
    return model


def transcribe_files(
    file_paths: list[str],
    output_dir: str = "transcripts",
    model_size: str = "medium",
    progress_callback: Optional[Callable[[str, bool, int, int], None]] = None,
    language: str = "de",
    use_gpu: bool = False,
    source_urls: Optional[list[str]] = None,
    video_numbers: Optional[list[int]] = None,
) -> dict[str, str]:
    """
    Transcribe a batch of audio files using faster-whisper.

    Each file is transcribed individually so that a failure on one file does
    not abort the entire batch.  Results are written as plain-text ``.txt``
    files inside *output_dir*, named after the input file's stem (video ID).

    Args:
        file_paths:        Absolute or relative paths to the audio files to transcribe.
        output_dir:        Directory where transcript ``.txt`` files are saved.
                           Created automatically if it does not exist.
        model_size:        faster-whisper model size string (default: ``"medium"``).
        progress_callback: Optional callable invoked after every file with the
                           signature ``(file_name: str, success: bool,
                           current_index: int, total_count: int) -> None``.
        language:          BCP-47 language code passed to the Whisper model
                           (default: ``"de"`` for German).
        use_gpu:           When True, attempt GPU transcription (re-enable once
                           the CUDA DLL issue is resolved). Default: False.
        source_urls:       Optional list of source URLs parallel to *file_paths*.
                           When provided, each transcript file gets a header block::

                               Video <N>
                               Source: <url>
                               ---
                               <transcript>
        video_numbers:     Optional list of integers parallel to *file_paths* that
                           control the ``Video <N>`` label in the header.  Defaults
                           to 1-based position within *file_paths* when omitted.

    Returns:
        A mapping of ``video_id -> transcript_text`` for every successfully
        transcribed file.  Files that raised an exception are omitted.
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    model = _load_model(model_size, use_gpu=use_gpu)

    results: dict[str, str] = {}
    total = len(file_paths)

    for index, file_path in enumerate(file_paths, start=1):
        file_name = Path(file_path).name
        video_id = Path(file_path).stem
        success = False

        try:
            segments, _info = model.transcribe(file_path, language=language)
            transcript = "".join(segment.text for segment in segments)

            # Build optional header
            video_num = (video_numbers[index - 1] if video_numbers else index)
            source_url = (source_urls[index - 1] if source_urls else None)
            if source_url:
                header = f"Video {video_num}\nSource: {source_url}\n---\n"
            else:
                header = ""

            output_path = Path(output_dir) / f"{video_id}.txt"
            output_path.write_text(header + transcript, encoding="utf-8")

            results[video_id] = transcript
            success = True
            logger.info("Transcribed '%s' -> '%s'.", file_name, output_path)

        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to transcribe '%s': %s", file_name, exc)

        if progress_callback is not None:
            progress_callback(file_name, success, index, total)

    return results
