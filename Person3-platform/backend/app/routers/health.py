from __future__ import annotations

from fastapi import APIRouter, Response

from ..core import network_adapter
from ..core.errors import AppError
from ..core.metrics import metrics

router = APIRouter(tags=["ops"])


@router.get("/health")
def health():
    """Liveness: the process is up. Cheap; Kubernetes can call it often."""
    return {"status": "ok"}


@router.get("/ready")
def ready(response: Response):
    """Readiness: can this instance actually classify? Reports each part separately."""
    checks = {}
    try:
        network_adapter.model_features()
        checks["network"] = {"ok": True}
    except AppError as e:
        checks["network"] = {"ok": False, "error": e.message}
    try:
        import text
        info = text.model_info()
        checks["text"] = {"ok": True, "model_source": info.get("source"), "model_version": info.get("version")}
    except Exception as e:
        checks["text"] = {"ok": False, "error": str(e)}
    ok = all(c["ok"] for c in checks.values())
    if not ok:
        response.status_code = 503
    return {"status": "ready" if ok else "not_ready", "checks": checks}


@router.get("/metrics", include_in_schema=False)
def prometheus_metrics():
    return Response(content=metrics.render(), media_type="text/plain; version=0.0.4; charset=utf-8")
