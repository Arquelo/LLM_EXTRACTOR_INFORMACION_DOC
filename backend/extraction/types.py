"""Tipos del contrato de extracción (API / CLI / JSON en output/)."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

EstadoExtraccion = Literal["exito", "parcial", "fallido"]


class ErrorValidacion(TypedDict):
    campo: str
    valor: str
    motivo: str


class ResultadoExtraccion(TypedDict):
    archivo: str
    extractor: str
    modelo: str
    ok: bool
    estado: EstadoExtraccion
    datos: dict[str, Any]
    errores_validacion: list[ErrorValidacion]
    error: str | None


class ResumenLote(TypedDict):
    total: int
    exitosos: int
    parciales: int
    fallidos: int
    tasa_exito: float
    tasa_parcial: float
    tasa_fallo: float


class ReporteLote(TypedDict):
    extractor: str
    modelo: str
    resumen: ResumenLote
    resultados: list[ResultadoExtraccion]
