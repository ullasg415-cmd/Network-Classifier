from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app


def test_video_endpoint_returns_classification_contract():
    expected = {
        "filename": "sample.mp4", "category": "Animals", "confidence": 0.8,
        "best_guess": "Animals", "top_k": [], "reason": "ok", "source": "pretrained",
        "model_version": "clip-test", "extractor": "ffmpeg", "file_type": "video/mp4",
        "duration_seconds": 2.0, "frame_count": 1, "sampling_interval_seconds": 2.0,
        "audio_detected": False, "audio_assisted": False, "real_data_validated": False,
    }
    with patch("video.api.classify_video", return_value=expected):
        response = TestClient(app).post("/classify/video", files={"file": ("sample.mp4", b"bytes", "video/mp4")})
    assert response.status_code == 200
    assert response.json() == expected
