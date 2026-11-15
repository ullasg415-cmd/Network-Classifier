import json
import os
import runpy
import sys
import time
from pathlib import Path

sys.path.insert(0, os.environ["NETWORK_ML_REPOSITORY"])
import train_compare
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

metrics = {
    "cross_validation_wall_seconds": 0.0,
    "cross_validation_fit_seconds": 0.0,
    "final_fit_seconds": 0.0,
    "final_prediction_seconds": 0.0,
    "final_metrics_seconds": 0.0,
}
stage = ["setup"]
original_cross_validate = train_compare._cross_validate
def timed_cross_validate(*args, **kwargs):
    stage[0] = "cross_validation"
    start = time.perf_counter()
    try:
        return original_cross_validate(*args, **kwargs)
    finally:
        metrics["cross_validation_wall_seconds"] += time.perf_counter() - start
        stage[0] = "final"
train_compare._cross_validate = timed_cross_validate

original_make_models = train_compare._make_models
def timed_make_models(*args, **kwargs):
    models = original_make_models(*args, **kwargs)
    for model in models.values():
        for method_name in ("predict", "predict_proba"):
            original = getattr(model, method_name)
            def timed_prediction(*positional, _original=original, **named):
                start = time.perf_counter()
                try:
                    return _original(*positional, **named)
                finally:
                    if stage[0] == "final":
                        metrics["final_prediction_seconds"] += time.perf_counter() - start
            setattr(model, method_name, timed_prediction)
    return models
train_compare._make_models = timed_make_models

for model_class in (RandomForestClassifier, XGBClassifier):
    original_fit = model_class.fit
    def make_timed_fit(original):
        def timed_fit(self, *args, **kwargs):
            start = time.perf_counter()
            try:
                return original(self, *args, **kwargs)
            finally:
                key = "cross_validation_fit_seconds" if stage[0] == "cross_validation" else "final_fit_seconds"
                metrics[key] += time.perf_counter() - start
        return timed_fit
    model_class.fit = make_timed_fit(original_fit)

original_metrics = train_compare._print_metrics
def timed_metrics(*args, **kwargs):
    start = time.perf_counter()
    try:
        return original_metrics(*args, **kwargs)
    finally:
        metrics["final_metrics_seconds"] += time.perf_counter() - start
train_compare._print_metrics = timed_metrics

try:
    train_compare.main()
except BaseException as error:
    metrics["error"] = repr(error)
    Path(os.environ["NETWORK_ML_STAGE_METRICS"]).write_text(json.dumps(metrics, indent=2) + "\n")
    raise
Path(os.environ["NETWORK_ML_STAGE_METRICS"]).write_text(json.dumps(metrics, indent=2) + "\n")
