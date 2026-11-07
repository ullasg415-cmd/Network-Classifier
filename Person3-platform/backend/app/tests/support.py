"""Shared helpers for the tests (no pytest needed, so they also run with `python -m unittest`)."""
from __future__ import annotations

import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
NETWORK = BACKEND / "network"
if str(NETWORK) not in sys.path:
    sys.path.insert(0, str(NETWORK))

REAL_MODEL_FEATURES = ["protocol", "packet_count", "total_bytes", "avg_packet_size", "duration",
                       "packet_rate", "byte_rate", "syn", "fin", "rst", "psh", "ack"]


def install_train_compare_stub_if_needed() -> bool:
    """network/classify_network.py imports train_compare, which imports mlflow and xgboost.
    Where those are not installed (e.g. a sandbox) we stand in for ONLY that module, with the
    same MODEL_FEATURES list. Everything else (rules.py, classify_network.py, rf.joblib) is real.
    Returns True if a stub was installed."""
    try:
        import train_compare  # noqa: F401
        return False
    except ImportError:
        stub = types.ModuleType("train_compare")
        stub.MODEL_FEATURES = list(REAL_MODEL_FEATURES)
        sys.modules["train_compare"] = stub
        return True


def has(module: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(module) is not None


MODEL_COLUMNS = ["packet_count", "total_bytes", "avg_packet_size", "duration", "packet_rate", "byte_rate"]


def csv_bytes(rows, header=None) -> bytes:
    """rows: list of dicts. Builds a CSV with src_port, dst_port and the six model features."""
    header = header or (["src_port", "dst_port"] + MODEL_COLUMNS)
    lines = [",".join(header)]
    for row in rows:
        lines.append(",".join(str(row.get(c, "")) for c in header))
    return ("\n".join(lines) + "\n").encode()


def flow(src=50000, dst=443, **kw):
    base = {"src_port": src, "dst_port": dst, "packet_count": 40, "total_bytes": 20000, "avg_packet_size": 500.0,
            "duration": 2.0, "packet_rate": 20.0, "byte_rate": 10000.0}
    base.update(kw)
    return base


class AppTestCase(unittest.TestCase):
    """Isolated environment: private data dir, no MLflow, fresh network adapter."""

    def setUp(self):
        install_train_compare_stub_if_needed()
        self._tmp = tempfile.TemporaryDirectory()
        self._env = mock.patch.dict(os.environ, {"APP_DATA_DIR": self._tmp.name}, clear=False)
        self._env.start()
        for var in ("MLFLOW_TRACKING_URI", "APP_MAX_UPLOAD_BYTES", "APP_MAX_FLOWS", "TEXT_MODEL_SOURCE",
                    "TEXT_MAX_BYTES", "NETWORK_MODEL_NAME", "TEXT_MODEL_NAME"):
            os.environ.pop(var, None)
        from app.core import network_adapter
        network_adapter.reset_for_tests()
        install_train_compare_stub_if_needed()

    def tearDown(self):
        self._env.stop()
        self._tmp.cleanup()
