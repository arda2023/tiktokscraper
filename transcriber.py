import logging
import os
from pathlib import Path
from typing import Callable, Optional

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


def _load_model(model_size: str) -> WhisperModel:
    """
    Load the WhisperModel with CUDA (float16) and fall back to CPU (int8) on failure.

    Args:
        model_size: The Whisper model size to load (e.g. "medium", "large-v2").

    Returns:
        A loaded WhisperModel instance.
    """
    try:
        model = WhisperModel(model_size, device="cuda", compute_type="float16")
        logger.info("Loaded WhisperModel '%s' on CUDA with float16.", model_size)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to load WhisperModel on CUDA (%s). Falling back to CPU with int8.", exc
        )
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        logger.info("Loaded WhisperModel '%s' on CPU with int8.", model_size)
    return model


def transcribe_files(
    file_paths: list[str],
    output_dir: str = "transcripts",
    model_size: str = "medium",
    progress_callback: Optional[Callable[[str, bool, int, int], None]] = None,
    language: str = "de",
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

    Returns:
        A mapping of ``video_id -> transcript_text`` for every successfully
        transcribed file.  Files that raised an exception are omitted.
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    model = _load_model(model_size)

    results: dict[str, str] = {}
    total = len(file_paths)

    for index, file_path in enumerate(file_paths, start=1):
        file_name = Path(file_path).name
        video_id = Path(file_path).stem
        success = False

        try:
            segments, _info = model.transcribe(file_path, language=language)
            transcript = "".join(segment.text for segment in segments)

            output_path = Path(output_dir) / f"{video_id}.txt"
            output_path.write_text(transcript, encoding="utf-8")

            results[video_id] = transcript
            success = True
            logger.info("Transcribed '%s' -> '%s'.", file_name, output_path)

        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to transcribe '%s': %s", file_name, exc)

        if progress_callback is not None:
            progress_callback(file_name, success, index, total)

    return results
