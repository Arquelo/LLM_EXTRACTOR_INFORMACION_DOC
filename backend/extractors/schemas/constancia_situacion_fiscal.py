"""Esquema Pydantic del dominio Constancia de Situación Fiscal.

Define campos obligatorios/opcionales, tipos (numérico, fecha, categórico)
y valida la salida del modelo de forma independiente del JSON Schema de Ollama.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class EstatusPadron(str, Enum):
    """Categoría / enum del estatus en el padrón del SAT."""

    ACTIVO = "ACTIVO"
    SUSPENDIDO = "SUSPENDIDO"
    CANCELADO = "CANCELADO"
    NO_LOCALIZADO = "NO LOCALIZADO"
    OTRO = "OTRO"


_ESTATUS_VALIDOS = {e.value for e in EstatusPadron}


class ActividadEconomica(BaseModel):
    model_config = ConfigDict(extra="ignore")

    orden: str = ""
    actividad: str = ""
    porcentaje: str = ""
    fecha_inicio: str = ""
    fecha_fin: str = ""


class RegimenFiscal(BaseModel):
    model_config = ConfigDict(extra="ignore")

    regimen: str = ""
    fecha_inicio: str = ""
    fecha_fin: str = ""


class ObligacionFiscal(BaseModel):
    model_config = ConfigDict(extra="ignore")

    descripcion: str = ""
    descripcion_vencimiento: str = ""
    fecha_inicio: str = ""
    fecha_fin: str = ""


class ConstanciaSituacionFiscalDatos(BaseModel):
    """Contrato de datos extraídos (validación programática post-modelo)."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    rfc: str = Field(default="", description="RFC obligatorio")
    fecha_inicio_operaciones: str = Field(default="", description="Fecha dd/mm/aaaa")
    estatus_padron: str = Field(default="", description="Enum categórico")
    codigo_postal: str = Field(default="", description="CP 5 dígitos")
    id_cif: str = Field(default="", description="idCIF numérico")

    curp: str = ""
    nombre: str = ""
    primer_apellido: str = ""
    segundo_apellido: str = ""
    denominacion_razon_social: str = ""
    regimen_capital: str = ""
    nombre_comercial: str = ""
    fecha_ultimo_cambio_estado: str = ""
    lugar_fecha_emision: str = ""
    tipo_vialidad: str = ""
    nombre_vialidad: str = ""
    numero_exterior: str = ""
    numero_interior: str = ""
    colonia: str = ""
    localidad: str = ""
    municipio: str = ""
    entidad_federativa: str = ""
    entre_calle: str = ""
    y_calle: str = ""

    actividades_economicas: list[ActividadEconomica] = Field(default_factory=list)
    regimenes: list[RegimenFiscal] = Field(default_factory=list)
    obligaciones: list[ObligacionFiscal] = Field(default_factory=list)

    @field_validator("rfc")
    @classmethod
    def rfc_obligatorio(cls, valor: str) -> str:
        if not (valor or "").strip():
            raise ValueError("Campo obligatorio 'rfc' vacío")
        return valor.strip().upper()

    @field_validator("fecha_inicio_operaciones")
    @classmethod
    def fecha_obligatoria(cls, valor: str) -> str:
        if not (valor or "").strip():
            raise ValueError("Campo obligatorio 'fecha_inicio_operaciones' vacío")
        return valor.strip()

    @field_validator("codigo_postal")
    @classmethod
    def cp_obligatorio(cls, valor: str) -> str:
        if not (valor or "").strip():
            raise ValueError("Campo obligatorio 'codigo_postal' vacío")
        return valor.strip()

    @field_validator("estatus_padron")
    @classmethod
    def estatus_categorico(cls, valor: str) -> str:
        normalizado = (valor or "").strip().upper()
        if not normalizado:
            raise ValueError("Campo obligatorio 'estatus_padron' vacío")
        alias = {
            "ACTIVO": EstatusPadron.ACTIVO.value,
            "SUSPENDIDO": EstatusPadron.SUSPENDIDO.value,
            "CANCELADO": EstatusPadron.CANCELADO.value,
            "NO LOCALIZADO": EstatusPadron.NO_LOCALIZADO.value,
            "NOLOCALIZADO": EstatusPadron.NO_LOCALIZADO.value,
            "OTRO": EstatusPadron.OTRO.value,
        }
        if normalizado in alias:
            return alias[normalizado]
        if normalizado in _ESTATUS_VALIDOS:
            return normalizado
        raise ValueError(
            f"estatus_padron debe ser uno de: {', '.join(sorted(_ESTATUS_VALIDOS))}"
        )


def validar_con_pydantic(datos: dict[str, Any]) -> list[dict[str, str]]:
    """Devuelve errores en el formato {campo, valor, motivo}."""
    try:
        ConstanciaSituacionFiscalDatos.model_validate(datos or {})
        return []
    except ValidationError as exc:
        errores: list[dict[str, str]] = []
        for err in exc.errors():
            loc_parts = err.get("loc", ())
            loc = ".".join(str(p) for p in loc_parts)
            valor = ""
            cursor: Any = datos or {}
            for p in loc_parts:
                if isinstance(cursor, dict):
                    cursor = cursor.get(p, "")
                elif isinstance(cursor, list) and isinstance(p, int) and p < len(cursor):
                    cursor = cursor[p]
                else:
                    cursor = ""
                    break
            if not isinstance(cursor, (dict, list)):
                valor = "" if cursor is None else str(cursor)
            errores.append(
                {
                    "campo": loc or "datos",
                    "valor": valor,
                    "motivo": err.get("msg", "Error de validación Pydantic"),
                }
            )
        return errores


CAMPOS_OBLIGATORIOS = (
    "rfc",
    "fecha_inicio_operaciones",
    "estatus_padron",
    "codigo_postal",
)

ESTATUS_OPCIONES = tuple(e.value for e in EstatusPadron)
