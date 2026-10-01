"""Construcción del dict de resultado por documento."""

from __future__ import annotations

from typing import Any

from extraction.types import ErrorValidacion, EstadoExtraccion, ResultadoExtraccion
from extractors.base import ExtractorBase
from settings.config import OLLAMA_MODEL


def construir_resultado(
    *,
    archivo: str,
    extractor: ExtractorBase,
    datos: dict[str, Any],
    error: str | None = None,
    errores_validacion: list[ErrorValidacion] | None = None,
    estado: EstadoExtraccion | None = None,
    ok: bool | None = None,
) -> ResultadoExtraccion:
    errores = errores_validacion or []
    if estado is None:
        # Si hay errores de validación, no tratar el mensaje como fallo duro:
        # clasificar permite 'parcial' cuando hay datos útiles.
        duro = None if errores else error
        estado = extractor.clasificar_estado(datos, errores, error_duro=duro)
    if ok is None:
        ok = estado == "exito"
    return {
        "archivo": archivo,
        "extractor": extractor.clave,
        "modelo": OLLAMA_MODEL,
        "ok": ok,
        "estado": estado,
        "datos": datos,
        "errores_validacion": errores,
        "error": error,
    }
