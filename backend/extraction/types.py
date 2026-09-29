"""Tipos del contrato de extracción (API / CLI / JSON en output/)."""

from __future__ import annotations

from typing import Any, TypedDict


class ErrorValidacion(TypedDict):
    campo: str
    valor: str
    motivo: str


class ResultadoExtraccion(TypedDict):
    archivo: str
    extractor: str
    modelo: str
    ok: bool
    datos: dict[str, Any]
    errores_validacion: list[ErrorValidacion]
    error: str | None
