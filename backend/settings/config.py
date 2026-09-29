"""Configuración del backend vía variables de entorno.

Carga `.env` del repo (raíz del proyecto) y luego `backend/.env` si existe.
Los valores del segundo archivo tienen prioridad.

Variables reconocidas: ver `.env.example` en la raíz del repositorio.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from settings.path import ROOT_DIR

# Raíz del repo (padre de backend/) y luego backend/.env opcional.
load_dotenv(ROOT_DIR.parent / ".env")
load_dotenv(ROOT_DIR / ".env", override=True)


def _int(nombre: str, default: str) -> int:
    return int(os.getenv(nombre, default))


def _float(nombre: str, default: str) -> float:
    return float(os.getenv(nombre, default))


def _lista(nombre: str, default: str) -> list[str]:
    crudo = os.getenv(nombre, default)
    return [p.strip() for p in crudo.split(",") if p.strip()]


# --- Ollama ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT = _int("OLLAMA_TIMEOUT", "300")
OLLAMA_CONNECT_TIMEOUT = _float("OLLAMA_CONNECT_TIMEOUT", "10")
OLLAMA_RETRIES = _int("OLLAMA_RETRIES", "2")
OLLAMA_RETRY_BACKOFF = _float("OLLAMA_RETRY_BACKOFF", "1.5")

# Extractor por defecto cuando la petición no envía uno explícito.
EXTRACTOR = os.getenv("EXTRACTOR", "constancia_situacion_fiscal")

# --- Servidor HTTP ---
SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = _int("SERVER_PORT", "8000")
CORS_ORIGINS = _lista(
    "CORS_ORIGINS",
    "http://127.0.0.1:5173,http://localhost:5173",
)

# --- Límites de carga / PDF ---
MAX_UPLOAD_FILES = _int("MAX_UPLOAD_FILES", "20")
MAX_UPLOAD_BYTES = _int("MAX_UPLOAD_BYTES", str(15 * 1024 * 1024))  # 15 MiB
MAX_PDF_PAGES = _int("MAX_PDF_PAGES", "50")
MAX_PDF_CHARS = _int("MAX_PDF_CHARS", "120000")
