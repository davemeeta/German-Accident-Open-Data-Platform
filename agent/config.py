import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_BACKEND = os.environ.get("UNFALLATLAS_AGENT_BACKEND", "groq")  # "groq" | "ollama"

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("UNFALLATLAS_OLLAMA_MODEL", "llama3.2:3b")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_BASE_URL = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.environ.get("UNFALLATLAS_GROQ_MODEL", "openai/gpt-oss-120b")

MAX_TOOL_ITERATIONS = 8  # hard cap on tool-call round trips per question

LOG_DIR = Path(os.environ.get("UNFALLATLAS_AGENT_LOG_DIR", str(REPO_ROOT / "agent" / "logs")))
LOG_DIR.mkdir(parents=True, exist_ok=True)
MAX_TRACE_FILES = int(os.environ.get("UNFALLATLAS_MAX_TRACE_FILES", "500"))  # oldest traces pruned beyond this
