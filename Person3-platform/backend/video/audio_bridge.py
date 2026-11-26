"""Optional adapter for the independently maintained Audio branch.

Expected future public contract: audio.classify_audio(file_bytes, filename) -> dict.
No Audio model is implemented here. Absence/failure must never block visual inference.
"""
from __future__ import annotations

def classify_audio_if_available(audio_bytes: bytes, filename: str = "audio.wav") -> dict | None:
    try:
        import audio  # supplied by the teammate's branch when integrated
        classify = getattr(audio, "classify_audio", None)
        if not callable(classify):
            return None
        return classify(audio_bytes, filename)
    except (ImportError, RuntimeError, ValueError, OSError):
        return None
