"""Pipeline: lote de documentos → extracción → validación → reporte."""

from __future__ import annotations

from pathlib import Path

from extraction.documents import (
    EXTENSIONES,
    PdfLimitError,
    PdfReadError,
    es_documento_soportado,
    leer_documento,
)
from extraction.report import construir_reporte, guardar_reporte
from extraction.results import construir_resultado
from extraction.storage import destino_json, guardar_resultado
from extraction.types import ReporteLote, ResultadoExtraccion
from extractors import obtener_extractor
from extractors.base import ExtractorBase
from llm.ollama_client import OllamaError, consultar_ollama
from settings.config import OLLAMA_MODEL
from settings.path import DOCS_DIR, OUTPUT_DIR

MUESTRAS_DIR = DOCS_DIR / "muestras"


def procesar(
    clave_extractor: str | None = None,
    pdfs: list[Path] | None = None,
) -> list[ResultadoExtraccion]:
    """Extrae datos de una lista de documentos (o de `docs/` / `docs/muestras`)."""
    extractor = obtener_extractor(clave_extractor)
    rutas = _resolver_rutas(pdfs)
    return _ejecutar_lote(extractor, rutas)


def procesar_muestras(clave_extractor: str | None = None) -> tuple[list[ResultadoExtraccion], ReporteLote]:
    """Procesa las muestras versionadas en `docs/muestras/` y genera reporte."""
    extractor = obtener_extractor(clave_extractor)
    if not MUESTRAS_DIR.is_dir():
        raise FileNotFoundError(f"No existe el directorio de muestras: {MUESTRAS_DIR}")
    rutas = sorted(
        (p for p in MUESTRAS_DIR.iterdir() if es_documento_soportado(p)),
        key=lambda p: p.name.lower(),
    )
    if not rutas:
        raise FileNotFoundError(f"No hay documentos de muestra en {MUESTRAS_DIR}")
    resultados = _ejecutar_lote(extractor, rutas)
    reporte = construir_reporte(
        resultados, extractor=extractor.clave, modelo=OLLAMA_MODEL
    )
    guardar_reporte(reporte)
    return resultados, reporte


def procesar_con_reporte(
    clave_extractor: str | None = None,
    documentos: list[Path] | None = None,
) -> tuple[list[ResultadoExtraccion], ReporteLote]:
    resultados = procesar(clave_extractor, documentos)
    extractor = resultados[0]["extractor"] if resultados else (clave_extractor or "")
    reporte = construir_reporte(
        resultados, extractor=extractor, modelo=OLLAMA_MODEL
    )
    guardar_reporte(reporte)
    return resultados, reporte


def _ejecutar_lote(
    extractor: ExtractorBase, rutas: list[Path]
) -> list[ResultadoExtraccion]:
    OUTPUT_DIR.mkdir(exist_ok=True)
    resultados: list[ResultadoExtraccion] = []
    stems_usados: set[str] = set()

    for ruta in rutas:
        destino = destino_json(ruta.stem, stems_usados, OUTPUT_DIR)
        resultado = procesar_archivo(extractor, ruta)
        try:
            guardar_resultado(destino, resultado)
        except OSError as exc:
            resultado = construir_resultado(
                archivo=ruta.name,
                extractor=extractor,
                datos=resultado.get("datos") or extractor.organizar({}),
                error=f"No se pudo guardar el resultado: {exc}",
                errores_validacion=resultado.get("errores_validacion") or [],
                estado="fallido",
            )
        resultados.append(resultado)

    return resultados


def procesar_archivo(
    extractor: ExtractorBase,
    ruta: Path,
) -> ResultadoExtraccion:
    """Procesa un documento. Cualquier fallo se convierte en resultado aislado."""
    try:
        texto = leer_documento(ruta)
    except PdfLimitError as exc:
        return construir_resultado(
            archivo=ruta.name,
            extractor=extractor,
            datos=extractor.organizar({}),
            error=str(exc),
            estado="fallido",
        )
    except (OSError, PdfReadError, ValueError, UnicodeError) as exc:
        return construir_resultado(
            archivo=ruta.name,
            extractor=extractor,
            datos=extractor.organizar({}),
            error=f"No se pudo leer el documento: {exc}",
            estado="fallido",
        )
    except Exception as exc:  # noqa: BLE001
        return construir_resultado(
            archivo=ruta.name,
            extractor=extractor,
            datos=extractor.organizar({}),
            error=f"Error inesperado al leer el documento: {exc}",
            estado="fallido",
        )

    if not texto.strip():
        return construir_resultado(
            archivo=ruta.name,
            extractor=extractor,
            datos=extractor.organizar({}),
            error="El documento no tiene texto extraíble.",
            estado="fallido",
        )

    try:
        bruto = consultar_ollama(extractor.prompt(), texto, extractor.esquema())
    except OllamaError as exc:
        return construir_resultado(
            archivo=ruta.name,
            extractor=extractor,
            datos=extractor.organizar({}),
            error=str(exc),
            estado="fallido",
        )
    except Exception as exc:  # noqa: BLE001
        return construir_resultado(
            archivo=ruta.name,
            extractor=extractor,
            datos=extractor.organizar({}),
            error=f"Error inesperado al consultar Ollama: {exc}",
            estado="fallido",
        )

    try:
        datos = extractor.organizar(bruto)
        errores_validacion = extractor.validar(datos)
    except Exception as exc:  # noqa: BLE001
        return construir_resultado(
            archivo=ruta.name,
            extractor=extractor,
            datos=extractor.organizar({}),
            error=f"Error al organizar/validar la respuesta: {exc}",
            estado="fallido",
        )

    estado = extractor.clasificar_estado(datos, errores_validacion)
    error = None
    if estado == "parcial":
        error = (
            "Extracción parcialmente exitosa: hay datos útiles pero faltan "
            "campos obligatorios o hay errores de formato. Revisa errores_validacion."
        )
    elif estado == "fallido":
        error = (
            "Extracción fallida: la salida no cumple el esquema y no hay "
            "datos suficientes. Revisa errores_validacion."
        )

    return construir_resultado(
        archivo=ruta.name,
        extractor=extractor,
        datos=datos,
        errores_validacion=errores_validacion,
        estado=estado,
        error=error,
    )


def _resolver_rutas(documentos: list[Path] | None) -> list[Path]:
    if documentos is None:
        rutas = sorted(
            p for p in DOCS_DIR.iterdir() if es_documento_soportado(p)
        ) if DOCS_DIR.is_dir() else []
        if not rutas and MUESTRAS_DIR.is_dir():
            rutas = sorted(
                p for p in MUESTRAS_DIR.iterdir() if es_documento_soportado(p)
            )
        origen = str(DOCS_DIR)
    else:
        rutas = sorted(
            (p for p in documentos if es_documento_soportado(p)),
            key=lambda p: p.name.lower(),
        )
        origen = "upload"

    if not rutas:
        raise FileNotFoundError(
            f"No hay documentos ({', '.join(sorted(EXTENSIONES))}) "
            f"para procesar ({origen})."
        )
    return rutas
