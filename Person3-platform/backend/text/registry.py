"""MLflow glue: log a training run, register the model, move the `champion` alias,
and load whatever is currently `champion`.

mlflow is imported lazily so the text branch still works (from the local joblib
file) on a machine without MLflow. Same registry as Sumukh's network model, a
different registered-model name ("text-classifier" vs. his).
"""
from __future__ import annotations

import logging
import os
import tempfile

from . import config

log = logging.getLogger(__name__)


class RegistryUnavailable(RuntimeError):
    """MLflow is not installed, not configured, or has no champion model yet."""


def _mlflow():
    try:
        import mlflow  # noqa: F401
        from mlflow import MlflowClient
    except ImportError as e:
        raise RegistryUnavailable("mlflow is not installed (pip install mlflow)") from e
    return mlflow, MlflowClient


def should_promote(new_f1: float, champion_f1: float | None) -> bool:
    """Promotion gate: the new version becomes champion if there is no champion yet,
    or if its macro-F1 on the held-out set is at least as good."""
    return champion_f1 is None or new_f1 >= champion_f1


def log_and_register(pipeline, meta: dict, params: dict, promote: str = "auto") -> dict:
    """Log a run, register a new model version, optionally move the champion alias.

    promote: "auto"  = gate on macro-F1 (see should_promote)
             "force" = always move the alias
             "never" = register only
    Returns {"version": str, "run_id": str, "promoted": bool}.
    """
    mlflow, MlflowClient = _mlflow()
    name, alias = config.registered_model_name(), config.model_alias()
    f1 = float(meta["metrics"]["f1_macro"])

    mlflow.set_experiment(config.experiment_name())
    with mlflow.start_run() as run:
        mlflow.log_params(params)
        mlflow.log_metrics({
            "f1_macro": f1,
            "accuracy": float(meta["metrics"]["accuracy"]),
            "cv_f1_macro_mean": float(meta["metrics"]["cv_f1_macro_mean"]),
        })
        mlflow.log_dict(meta, "model_meta.json")
        try:                                   # MLflow 3.x
            info = mlflow.sklearn.log_model(pipeline, name="model")
        except TypeError:                      # MLflow 2.x
            info = mlflow.sklearn.log_model(pipeline, artifact_path="model")
        run_id = run.info.run_id
        model_uri = getattr(info, "model_uri", None) or f"runs:/{run_id}/model"

    client = MlflowClient()
    mv = mlflow.register_model(model_uri, name)

    champion_f1 = None
    try:
        champ = client.get_model_version_by_alias(name, alias)
        champion_f1 = client.get_run(champ.run_id).data.metrics.get("f1_macro")
    except Exception:  # no champion yet
        pass

    promoted = promote == "force" or (promote == "auto" and should_promote(f1, champion_f1))
    if promoted:
        client.set_registered_model_alias(name, alias, mv.version)
    log.info("registered %s v%s (f1=%.4f, champion_f1=%s, promoted=%s)", name, mv.version, f1, champion_f1, promoted)
    return {"version": str(mv.version), "run_id": run_id, "promoted": promoted}


def load_champion():
    """Return (pipeline, meta) for the model currently tagged with the champion alias."""
    if not os.getenv("MLFLOW_TRACKING_URI"):
        raise RegistryUnavailable("MLFLOW_TRACKING_URI is not set")
    mlflow, MlflowClient = _mlflow()
    name, alias = config.registered_model_name(), config.model_alias()
    client = MlflowClient()
    try:
        mv = client.get_model_version_by_alias(name, alias)
    except Exception as e:
        raise RegistryUnavailable(f"No model '{name}' with alias '{alias}' in the registry: {e}") from e
    try:
        pipeline = mlflow.sklearn.load_model(f"models:/{name}@{alias}")
    except Exception as e:
        raise RegistryUnavailable(f"Could not load '{name}@{alias}': {e}") from e

    meta = {"name": name, "version": str(mv.version), "run_id": mv.run_id}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            import json
            path = client.download_artifacts(mv.run_id, "model_meta.json", tmp)
            with open(path, encoding="utf-8") as f:
                meta = {**json.load(f), **meta}
    except Exception:
        log.warning("model_meta.json not found for %s v%s; using minimal metadata", name, mv.version)
    return pipeline, meta
