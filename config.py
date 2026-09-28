from dotenv import load_dotenv
from path import ROOT_DIR
import os

load_dotenv(ROOT_DIR / ".env")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))

# Clave del extractor activo. Cambiarla apunta a otro prompt y a otra clase.
EXTRACTOR = os.getenv("EXTRACTOR", "constancia_situacion_fiscal")
