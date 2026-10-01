"""Esquemas Pydantic por dominio de extracción."""

from extractors.schemas.constancia_situacion_fiscal import (
    CAMPOS_OBLIGATORIOS,
    ESTATUS_OPCIONES,
    ConstanciaSituacionFiscalDatos,
    EstatusPadron,
    validar_con_pydantic,
)

__all__ = [
    "CAMPOS_OBLIGATORIOS",
    "ESTATUS_OPCIONES",
    "ConstanciaSituacionFiscalDatos",
    "EstatusPadron",
    "validar_con_pydantic",
]
