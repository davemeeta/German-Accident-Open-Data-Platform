import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

API_BASE_URL = os.environ.get("UNFALLATLAS_API_BASE_URL", "http://127.0.0.1:8000")

DB_PATH = Path(os.environ.get(
    "UNFALLATLAS_DB_PATH",
    str(REPO_ROOT / "data" / "processed" / "accidents.db"),
))
