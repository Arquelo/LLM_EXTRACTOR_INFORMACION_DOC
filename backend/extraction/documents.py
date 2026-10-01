"""Lectura unificada de documentos PDF o texto (.txt)."""

from __future__ import annotations

from pathlib import Path

from pypdf.errors import PdfReadError

from extraction.pdf import PdfLimitError, texto_pdf

EXTENSIONES = {".pdf", ".txt"}


def leer_documento(ruta: Path) -> str:
    """Devuelve el texto del documento según su extensión."""
    sufijo = ruta.suffix.lower()
    if sufijo == ".pdf":
        return texto_pdf(ruta)
    if sufijo == ".txt":
        return ruta.read_text(encoding="utf-8", errors="replace")
    raise ValueError(f"Formato no soportado: {sufijo}")


def es_documento_soportado(ruta: Path) -> bool:
    return ruta.is_file() and ruta.suffix.lower() in EXTENSIONES


# Reexport útil para el pipeline.
__all__ = [
    "EXTENSIONES",
    "PdfLimitError",
    "PdfReadError",
    "es_documento_soportado",
    "leer_documento",
]
