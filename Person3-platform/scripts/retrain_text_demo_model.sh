#!/usr/bin/env bash
# Rebuild the demo text model with the scikit-learn version installed in YOUR environment.
# Needed once: the model shipped in backend/text/models was trained with scikit-learn 1.9.1,
# while this backend pins 1.6.1 (to match the network model rf.joblib). A pickle trained by one
# version may not load in another, so retrain it locally. It is trained on SYNTHETIC documents.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../backend"
python -m text.data.generate_sample_dataset --out data/sample --per-class 60
python -m text.train --data-dir data/sample --data-source synthetic-demo
echo "Done. Check: python -m text text/samples/*/*"
