# Person 3 integration changes for latest Person 2 text branch

Date: 2026-11-07

## Applied

1. Replaced `backend/text/` with the latest supplied Person 2 branch.
2. Kept Person 3's existing app, network branch, registry, metrics, activity log, and frontend structure.
3. Extended `RegistryService.serving_status()` to return `real_data_validated`, `evaluation_note`, and model metrics from `text.model_info()`.
4. Added a visible `DEMO MODEL` warning to the text model card when `real_data_validated` is false.
5. Updated the shared Starlette/FastAPI HTTP exception handler to preserve dictionary-valued `detail` objects as structured `error.details` instead of stringifying them.
6. Added regression tests for registry metadata propagation and structured HTTP error handling.
7. Documented the outstanding shared scikit-learn retraining requirement and current test results in the root README.

## Validation performed

Command:

```bash
cd backend
python -m pytest app/tests text/tests -q -rs
```

Result: **235 passed, 18 skipped, 1 failed**.

The one failure is `test_shipped_model_matches_installed_sklearn_and_loads_without_warnings`: the packaged text model metadata says scikit-learn 1.9.1, while the build environment has 1.8.0. The shared backend requirements pin scikit-learn 1.6.1 to match Sumukh's network model. This is not resolved by this ZIP; retrain the text model using the shared 1.6.1 environment via `scripts/retrain_text_demo_model.sh`, then rerun the full suite. Do not manually edit model metadata.

18 skipped tests require real MLflow, a running Apache Tika server, or Docker/Compose. Those services have not been verified in this environment.

## Not claimed as complete

- Real-data accuracy: blocked; model is synthetic-demo trained.
- MLflow server/registry calls: not verified against a real server.
- Apache Tika server: not verified against a real server.
- Docker containers: not started; only project tests were attempted.
- Network model MLflow promotion: remains read-only until Sumukh changes the serving loader.
- Frontend production build: not run because npm dependencies were not installed in the build environment.
