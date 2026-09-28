"""Configuración del backend vía variables de entorno.

Lee `backend/.env` (si existe) y expone valores tipados para Ollama, el
extractor activo y el servidor HTTP. Si una variable no está definida, se usa
el valor por defecto indicado en cada constante.

Variables reconocidas:
    OLLAMA_BASE_URL: URL del servicio Ollama (sin barra final).
    OLLAMA_MODEL: nombre del modelo a consultar.
    OLLAMA_TIMEOUT: timeout de la petición a Ollama, en segundos.
    EXTRACTOR: clave del extractor registrado en `extractors`.
    SERVER_HOST: interfaz de escucha del API.
    SERVER_PORT: puerto del API.
"""

import os

from dotenv import load_dotenv

from settings.path import ROOT_DIR

load_dotenv(ROOT_DIR / ".env")

# --- Ollama ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))

# Extractor por defecto cuando la petición no envía uno explícito.
# Debe coincidir con una clave en `extractors.EXTRACTORES`.
EXTRACTOR = os.getenv("EXTRACTOR", "constancia_situacion_fiscal")

# --- Servidor HTTP (server.py) ---
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
