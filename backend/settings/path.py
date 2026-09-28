"""Rutas base del backend.

Centraliza las carpetas del servicio para no hardcodear paths en extractores,
API u otros módulos. `ROOT_DIR` es siempre la carpeta `backend/`, aunque este
archivo viva dentro de `settings/`.
"""

from pathlib import Path

# Carpeta backend/ (padre de settings/).
ROOT_DIR = Path(__file__).resolve().parent.parent

# PDFs de entrada locales (uso CLI / respaldo).
DOCS_DIR = ROOT_DIR / "docs"

# JSON de salida generados por cada extracción.
OUTPUT_DIR = ROOT_DIR / "output"

# Subidas temporales desde el frontend (archivo o carpeta).
UPLOADS_DIR = ROOT_DIR / "uploads"
