"""Register the pretrained CLIP model configuration and promote it as champion.

Run from backend/: python -m video.register_model
This registers metadata only; CLIP weights are downloaded/cached on first inference.
"""
from __future__ import annotations

import json
import os
import tempfile

from . import config


def register_model(model_id: str | None = None, promote: bool = True) -> dict:
    try:
        import mlflow
        from mlflow import MlflowClient
    except ImportError as exc:
        raise RuntimeError("Install MLflow before registering Video: pip install mlflow") from exc

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        raise RuntimeError("Set MLFLOW_TRACKING_URI to the shared MLflow server")
    mlflow.set_tracking_uri(tracking_uri)
    name = config.registered_model_name()
    alias = config.model_alias()
    payload = {
        "model_id": model_id or config.model_id(),
        "prompt_set": "v1",
        "categories": config.CATEGORIES,
        "prompts": config.PROMPTS,
        "unknown_threshold": config.unknown_threshold(),
        "real_data_validated": False,
        "evaluation_note": "Pretrained CLIP zero-shot baseline; not validated on a representative labelled video dataset.",
    }
    with mlflow.start_run(run_name="video-clip-config") as run:
        mlflow.log_dict(payload, "video_model_config.json")
        run_id = run.info.run_id
    client = MlflowClient(tracking_uri=tracking_uri)
    try:
        client.get_registered_model(name)
    except Exception:
        client.create_registered_model(name)
    mv = client.create_model_version(
        name=name,
        source=f"runs:/{run_id}/video_model_config.json",
        run_id=run_id,
        description="Pretrained CLIP zero-shot video classifier configuration; weights cached separately.",
    )
    client.set_model_version_tag(name, mv.version, "video_model_id", payload["model_id"])
    client.set_model_version_tag(name, mv.version, "video_prompt_set", payload["prompt_set"])
    if promote:
        client.set_registered_model_alias(name, alias, mv.version)
    return {"name": name, "version": str(mv.version), "alias": alias if promote else None,
            "model_id": payload["model_id"], "run_id": run_id}


if __name__ == "__main__":
    print(json.dumps(register_model(), indent=2))
