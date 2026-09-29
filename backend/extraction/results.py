"""Construcción del dict de resultado por documento."""

from __future__ import annotations

from typing import Any

from extraction.types import ErrorValidacion, ResultadoExtraccion
from extractors.base import ExtractorBase
from settings.config import OLLAMA_MODEL


def construir_resultado(
    *,
    archivo: str,
    extractor: ExtractorBase,
    ok: bool,
    datos: dict[str, Any],
    error: str | None = None,
    errores_validacion: list[ErrorValidacion] | None = None,
) -> ResultadoExtraccion:
    return {
        "archivo": archivo,
        "extractor": extractor.clave,
        "modelo": OLLAMA_MODEL,
        "ok": ok,
        "datos": datos,
        "errores_validacion": errores_validacion or [],
        "error": error,
    }
