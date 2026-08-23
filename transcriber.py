import logging
import os
from pathlib import Path
from typing import Callable, Generator, NamedTuple, Optional

from faster_whisper import WhisperModel
from faster_whisper.transcribe import Segment

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def load_model(model_size: str, use_gpu: bool = False) -> WhisperModel:
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


# ---------------------------------------------------------------------------
# Single-file transcription (returns raw segments)
# ---------------------------------------------------------------------------

def transcribe_single(
    file_path: str,
    model: WhisperModel,
    language: str = "de",
) -> list[Segment]:
    """
    Transcribe one audio file and return the raw faster-whisper segments.

    Each segment has ``.text``, ``.start``, and ``.end`` attributes so the
    caller can format the output however it likes (e.g. newlines between
    segments, timestamps, etc.).

    Args:
        file_path: Path to the audio file to transcribe.
        model:     A pre-loaded WhisperModel instance.
        language:  BCP-47 language code (default: ``"de"``).

    Returns:
        List of faster-whisper ``Segment`` objects.

    Raises:
        Exception: Propagated from faster-whisper on any transcription error.
    """
    segments_gen, _info = model.transcribe(file_path, language=language)
    # Materialise the generator so errors surface here, not lazily later.
    return list(segments_gen)


# ---------------------------------------------------------------------------
# Legacy batch helper (kept for backwards compatibility)
# ---------------------------------------------------------------------------

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
    Transcribe a batch of audio files and write one .txt per file.

    This is the original batch helper retained for backwards compatibility.
    New code should use :func:`load_model` + :func:`transcribe_single` directly
    for more control over output formatting.

    Args:
        file_paths:        Paths to audio files.
        output_dir:        Directory for output ``.txt`` files.
        model_size:        faster-whisper model size string.
        progress_callback: ``(file_name, success, index, total) -> None``.
        language:          BCP-47 language code (default ``"de"``).
        use_gpu:           Attempt CUDA when True (default False).
        source_urls:       Parallel list of source URLs written into headers.
        video_numbers:     Parallel list of video numbers for headers.

    Returns:
        Mapping of ``video_id -> joined transcript text``.
    """
    os.makedirs(output_dir, exist_ok=True)
    model = load_model(model_size, use_gpu=use_gpu)

    results: dict[str, str] = {}
    total = len(file_paths)

    for index, file_path in enumerate(file_paths, start=1):
        file_name = Path(file_path).name
        video_id = Path(file_path).stem
        success = False

        try:
            segments = transcribe_single(file_path, model, language=language)
            transcript = "".join(seg.text for seg in segments)

            video_num = (video_numbers[index - 1] if video_numbers else index)
            source_url = (source_urls[index - 1] if source_urls else None)
            header = f"Video {video_num}\nSource: {source_url}\n---\n" if source_url else ""

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
