# Network and document classification: backend, MLflow and web app (Person 3)

This folder holds Person 3's part of the project and the two branches it connects.

```
backend/
  network/   Sumukh's network branch (copied in unchanged; do not edit here)
  text/      Person 2's text branch (copied in unchanged; do not edit here)
  app/       Person 3: FastAPI app, registry logic, metrics, tests
  requirements.txt
frontend/    Person 3: React web app (Vite)
mlflow/      Person 3: start script and registry README
scripts/     retrain the demo text model on your scikit-learn version
sample_data/ flows.csv: eight made-up flows for trying the network endpoint
```

## How this works and why (for a beginner)

**The idea.** Two kinds of input come in: network traffic and documents. Each has its own classifier. The app is the
shell that receives a file, hands it to the right classifier, and shows the answer.

**Network traffic.** A capture is first summarised into *flows* (one row per conversation: ports, packets, bytes, duration).
Then simple rules look at the port: 80 is HTTP, 443 is HTTPS, 53 is DNS, 22 is SSH. If no rule matches the flow is labelled
**Unknown**. A Random Forest also gives an opinion on those unmatched flows, but the project's own evaluation showed the
model did not detect unfamiliar traffic from a different generator. So the app labels its opinion **advisory**: a hint,
not a verdict. In the UI, a solid chip means a rule or the text model answered; a dashed chip means the network model did.

**Documents.** The text is extracted (Apache Tika, or local libraries as a fallback), turned into numbers (TF-IDF: how
important each word is), and a Linear SVM picks a category. If it is not confident enough it answers **unknown**
instead of guessing, and the UI shows why.

**The registry (MLflow).** Every retrain produces a new numbered *version* of a model. A movable label called
**champion** marks the version that should be live. The backend loads "text-classifier@champion", so promoting a better
version, or rolling back a bad one, changes what is served without redeploying code. Promote and rollback ask for an
explicit confirmation and are written to an activity log (who, what, when).

**Why FastAPI + React.** FastAPI gives a typed, documented HTTP API (open `/docs`). React shows it. The two only
talk through that API, so Person 4 can containerise them separately.

**One error format.** Every failure, from any branch, looks like
`{"error": {"code": "EMPTY_FILE", "message": "...", "details": {...}}}`, so the UI can explain problems the same way everywhere.

## Run it (integration checklist)

Use Python 3.10 to 3.12 and Node 18 or newer.

```bash
# 0. install (the pins come from Sumukh's requirements; scikit-learn must be 1.6.1 for rf.joblib)
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# 1. retrain the demo text model once on this scikit-learn version (see "Known problems", item 1)
./scripts/retrain_text_demo_model.sh

# 2. run every test (the 25 HTTP tests need FastAPI, which step 0 installs; they were never run before)
cd backend && pytest app/tests text/tests -v && cd ..

# 3. terminal A: MLflow server and registry
./mlflow/start_mlflow.sh

# 4. terminal B: register two text versions, then start the backend
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
cd backend
python -m text.train --data-dir data/sample --data-source synthetic-demo --register force
python -m text.train --data-dir data/sample --data-source synthetic-demo --register never
uvicorn app.main:app --port 8000

# 5. terminal C: the web app
cd frontend && npm install && npm run dev        # http://localhost:5173
```

**Confirm both branches work end to end**

```bash
curl localhost:8000/health                       # {"status":"ok"}
curl localhost:8000/ready                        # network and text both "ok": true
curl -F file=@sample_data/flows.csv localhost:8000/classify/network
curl -F file=@backend/text/samples/invoice/invoice_0000.pdf localhost:8000/classify/text
curl localhost:8000/registry/models              # text-classifier with 2 versions, one champion
curl localhost:8000/metrics                      # Prometheus text (for Person 4)
```

In the browser: classify `sample_data/flows.csv` (Network traffic tab) and a sample document (Documents tab); refresh the
page and check History still lists them; on Models, compare the two versions, promote version 2, check Activity shows it, then roll back.
Also try a real `.pcap` from Sumukh's captures: that path has not been run (see below).

## API

| Route | What it does |
|---|---|
| `POST /classify/network` (field `file`) | `.pcap`/`.pcapng` or a CSV of flows; one result per flow. IPFIX/NetFlow files get a clear 415 |
| `POST /classify/text` (field `file`) | Person 2's router, mounted unchanged. `GET /classify/text/model`, `POST /classify/text/model/reload` too |
| `GET /registry/models` | models, versions, metrics, champion, what is live. Returns `available: false` with a reason if MLflow is down |
| `GET /registry/models/{name}/compare?versions=1,2` | metrics side by side |
| `POST /registry/models/{name}/promote` | `{"version","confirm":true,"actor"}`; refuses without `confirm` |
| `POST /registry/models/{name}/rollback` | `{"confirm":true,"actor"}` (optional `to_version`) |
| `POST /registry/models/{name}/reload` | reload the live model |
| `GET /registry/activity`, `GET /registry/network/runs` | activity log; read-only runs of Sumukh's experiment |
| `GET /health`, `GET /ready`, `GET /metrics` | liveness, readiness, Prometheus |

Network result fields: `label`, `is_unknown` (absorbs `Unknown`/`unknown`), `source` (`rule`, `default`, `ml`), `advisory`,
`ml_label`, `ml_confidence`, `confidence`. The three shapes of `classify_network` are all passed through.

## Settings (environment variables only)

| Variable | Default | Meaning |
|---|---|---|
| `MLFLOW_TRACKING_URI` | unset | MLflow server. Unset = registry page shows a notice; text uses its local file |
| `APP_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | allowed frontend origins |
| `APP_MAX_UPLOAD_BYTES` / `APP_MAX_FLOWS` | 100 MB / 20000 | network upload limits |
| `APP_DATA_DIR` | `backend/app_data` | activity log. Mount as a volume in containers |
| `NETWORK_MODEL_NAME` / `TEXT_MODEL_NAME` / `MODEL_ALIAS` | `network-classifier` / `text-classifier` / `champion` | registry names |
| `NETWORK_MLFLOW_EXPERIMENT` | `network-known-unknown` | experiment shown read-only |
| `TEXT_*`, `TIKA_URL` | see `backend/text/README.md` | text branch settings |
| `VITE_API_URL` (frontend, build time) | `http://localhost:8000` | backend address |

For Person 4: the backend is `uvicorn app.main:app`, listens on one port, needs `/health` and `/ready` for probes, and
exposes `/metrics`: `app_http_requests_total{method,path,status}`, `app_http_request_duration_seconds`,
`app_classifications_total{branch,source}`.

## What was actually verified

| Item | Status |
|---|---|
| Network upload logic against Sumukh's real `rules.py`, `classify_network.py` and `rf.joblib` (all three output shapes, 12 error cases, PCAP path with a fake extractor) | **Ran and passed** (only `train_compare` was stubbed, because MLflow and XGBoost are not installed in the build sandbox) |
| Registry logic (list, compare, promote, rollback, reload, confirmation, activity log) | **Ran and passed**, against a fake MLflow client that mimics the real `MlflowClient` calls |
| Metrics text format, error format | **Ran and passed** |
| Frontend helper tests (13) | **Ran and passed** (`npm test`) |
| Whole UI in headless Chromium: classify network and text, errors, history after refresh, compare, promote with confirmation, rollback, activity, read-only network model, mobile width (17 checks, no console errors) | **Ran and passed**, against a stand-in server that runs the real backend logic over plain HTTP, with the code compiled by TypeScript instead of Vite |
| FastAPI wiring (`main.py`, routers, schemas, CORS, error handlers) | **Written, not run.** FastAPI could not be installed; the 25 tests in `app/tests/test_api.py` skip here and will be the first real test on your machine |
| Real MLflow (registry calls against `mlflow==2.22.4`, `start_mlflow.sh`) | **Written, not run** |
| PCAP extraction with NFStream | **Not run.** Only the code around it was tested |
| `rf.joblib` under scikit-learn 1.6.1 | **Not run.** It loaded here under 1.9.1 with a version warning |
| `npm install`, Vite dev server and build, React 19 from npm | **Not run** |
| Text branch tests (`text/tests`) | **Not re-run** after copying |
| Docker, Podman | Not touched |

## Known problems to settle with the team

1. **scikit-learn version conflict.** Sumukh pins 1.6.1; Person 2's text model was trained with 1.9.1 (and `text/requirements.txt` pins it). One backend process can have only one. This backend uses 1.6.1, so retrain the text model once (`scripts/retrain_text_demo_model.sh`). Python 3.9 can't install 1.9.1.
2. **The network model is not served from the registry.** `classify_network.py` loads `rf.joblib` from disk, so promotion would change nothing. The app shows it read-only, with its MLflow runs, and says why. Fix on Sumukh's side: load `models:/network-classifier@champion`, keeping the file as a fallback.
3. **Sumukh's import coupling.** `classify_network.py` imports `MODEL_FEATURES` from `train_compare.py`, which imports MLflow and XGBoost. `app/core/network_adapter.py` works around his flat imports by adding his folder to `sys.path`. Moving `MODEL_FEATURES` into a small shared module and using relative imports would remove both.
4. **IPFIX/NetFlow is not supported**: there is no extractor for it yet. The endpoint refuses it with a 415 saying so.
5. **Nothing bridges the branches.** Readable HTTP payloads from a capture are not passed to the text branch.
6. **`python-multipart` is missing from Sumukh's requirements**; FastAPI needs it for uploads. It is added in `backend/requirements.txt`.
7. **The text model's scores are not evidence.** It is trained on synthetic documents (see `backend/text/README.md`). The same holds for `sample_data/flows.csv`: eight made-up flows to try the pipeline.
8. **History is per browser** (localStorage, first 200 flows per result). The activity log is one file on the server.
9. **No authentication.** The "your name" box only labels activity entries; anyone who can reach the API can promote a model.

## Person 2 latest text-branch integration (2026-11-07)

The `backend/text/` directory in this package has been replaced with the latest Person 2 branch. It includes the detailed classification response, Tika fallback fixes, `/classify/text/health`, model metadata (`real_data_validated`), and the latest validation/integration guides.

### Important: shared scikit-learn model compatibility

The network model was serialized with scikit-learn 1.6.1. The latest text model was serialized with scikit-learn 1.9.1. The shared `backend/requirements.txt` currently pins 1.6.1 to match the network model, so **the text model must be retrained in that shared environment before the two models can be considered compatible**. Do not edit the model metadata by hand. From `backend/`, after installing the shared requirements, run:

```bash
../scripts/retrain_text_demo_model.sh
```

Then run:

```bash
python -m pytest app/tests text/tests -q -rs
```

A clean compatibility test must pass without `InconsistentVersionWarning`. The current packaged text model remains the 1.9.1 artifact until this retraining is performed. The model is still trained on synthetic demo documents; it is not validated on real labelled documents.

### Person 2 integration additions

- The text router is mounted unchanged from `text.api` and includes `GET /classify/text/health`.
- Registry serving status exposes `real_data_validated`, `data_source`, `evaluation_note`, and available metrics.
- The Models page displays a demo-model warning when `real_data_validated` is false.
- Structured HTTP exception details (including the text health report) are retained in the shared error envelope.
- Network serving remains read-only in the registry until Sumukh wires its serving loader to the MLflow champion alias.

### Verification status of this merged package

The combined backend suite was run in the build environment (Python 3.13.5, scikit-learn 1.8.0): 235 passed, 18 skipped, 1 failed. The one failure is the expected text model version check (model metadata 1.9.1 versus installed 1.8.0). Network and text model deserialization emitted version warnings in this environment. MLflow, Tika server, and Docker integration tiers were skipped because those services/dependencies were unavailable. See `backend/text/MAC_VALIDATION.md` and `backend/text/TEST_RESULTS.md` for the Person 2 service validation steps.
