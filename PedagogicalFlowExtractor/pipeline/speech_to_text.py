"""Speech-to-Text module using OpenAI Whisper.

Takes a video/audio file and produces a timestamped transcript.
Supports code-mixed (Hinglish) content.
"""

import json
import os
import subprocess
import tempfile

from utils.config import load_config, resolve_path
from utils.helpers import format_timestamp, now_iso, save_json
from utils.logger import get_logger

logger = get_logger(__name__)


def extract_audio(video_path: str, audio_path: str = None) -> str:
    """Extract audio from a video file using ffmpeg.

    Args:
        video_path: Absolute path to the video file.
        audio_path: Where to save the .wav file. Auto-generated if None.

    Returns:
        Path to the extracted audio file.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if audio_path is None:
        base = os.path.splitext(os.path.basename(video_path))[0]
        audio_dir = resolve_path("data/transcripts")
        os.makedirs(audio_dir, exist_ok=True)
        audio_path = os.path.join(audio_dir, f"{base}.wav")

    logger.info("Extracting audio from: %s", video_path)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",                  # no video
        "-acodec", "pcm_s16le", # 16-bit PCM
        "-ar", "16000",         # 16kHz sample rate (Whisper expects this)
        "-ac", "1",             # mono
        audio_path,
    ]

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=300
    )
    if result.returncode != 0:
        logger.error("ffmpeg error: %s", result.stderr)
        raise RuntimeError(f"Audio extraction failed: {result.stderr[:500]}")

    logger.info("Audio saved to: %s", audio_path)
    return audio_path


def transcribe(
    file_path: str,
    model_name: str = None,
    language: str = None,
) -> dict:
    """Transcribe an audio or video file using Whisper.

    Args:
        file_path: Path to audio (.wav/.mp3) or video (.mp4/.mkv) file.
        model_name: Whisper model size. Defaults to config value.
        language: Language hint. Defaults to config value.

    Returns:
        Transcript dict with metadata and timestamped segments.
    """
    import whisper

    cfg = load_config()
    model_name = model_name or cfg["whisper"]["model"]
    language = language or cfg["whisper"].get("language")  # None = auto-detect

    # If it's a video file, extract audio first
    video_extensions = {".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv"}
    ext = os.path.splitext(file_path)[1].lower()
    audio_path = file_path

    if ext in video_extensions:
        # Check if audio was already extracted
        base = os.path.splitext(os.path.basename(file_path))[0]
        cached_audio = os.path.join(resolve_path("data/transcripts"), f"{base}.wav")
        if os.path.isfile(cached_audio):
            logger.info("Reusing existing audio: %s", cached_audio)
            audio_path = cached_audio
        else:
            audio_path = extract_audio(file_path)
    elif not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    logger.info("Loading Whisper model: %s", model_name)
    model = whisper.load_model(model_name)

    logger.info("Transcribing: %s", audio_path)
    transcribe_kwargs = {
        "task": cfg["whisper"].get("task", "transcribe"),
        "verbose": False,
    }
    if language:
        transcribe_kwargs["language"] = language
    result = model.transcribe(audio_path, **transcribe_kwargs)

    # Build structured transcript
    segments = []
    full_text_parts = []
    for seg in result.get("segments", []):
        segment_data = {
            "id": seg["id"],
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
            "timestamp_label": format_timestamp(seg["start"]),
        }
        segments.append(segment_data)
        full_text_parts.append(seg["text"].strip())

    video_name = os.path.splitext(os.path.basename(file_path))[0]
    transcript = {
        "video_id": video_name,
        "metadata": {
            "source_file": os.path.basename(file_path),
            "language_detected": result.get("language", language),
            "model_used": model_name,
            "processed_at": now_iso(),
        },
        "full_text": " ".join(full_text_parts),
        "segments": segments,
    }

    # Save transcript
    out_path = resolve_path(f"data/transcripts/{video_name}_transcript.json")
    save_json(transcript, out_path)
    logger.info("Transcript saved to: %s (%d segments)", out_path, len(segments))

    return transcript


def load_transcript(transcript_path: str) -> dict:
    """Load an existing transcript JSON file.

    Args:
        transcript_path: Path to the transcript JSON file.

    Returns:
        Transcript dictionary.
    """
    full_path = resolve_path(transcript_path) if not os.path.isabs(transcript_path) else transcript_path
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)
