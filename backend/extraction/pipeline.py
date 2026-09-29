"""Pipeline: lote de PDFs → extracción → validación → guardado."""

from __future__ import annotations

from pathlib import Path

from pypdf.errors import PdfReadError

from extraction.pdf import PdfLimitError, texto_pdf
from extraction.results import construir_resultado
from extraction.storage import destino_json, guardar_resultado
from extraction.types import ResultadoExtraccion
from extractors import obtener_extractor
from extractors.base import ExtractorBase
from llm.ollama_client import OllamaError, consultar_ollama
from settings.path import DOCS_DIR, OUTPUT_DIR


def procesar(
    clave_extractor: str | None = None,
    pdfs: list[Path] | None = None,
) -> list[ResultadoExtraccion]:
    """Extrae datos de una lista de PDFs (o de `docs/` si no se pasan archivos)."""
    extractor = obtener_extractor(clave_extractor)
    rutas = _resolver_rutas(pdfs)

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
                ok=False,
                datos=resultado.get("datos") or extractor.organizar({}),
                error=f"No se pudo guardar el resultado: {exc}",
                errores_validacion=resultado.get("errores_validacion") or [],
            )
        resultados.append(resultado)

    return resultados


def procesar_archivo(
    extractor: ExtractorBase,
    ruta: Path,
) -> ResultadoExtraccion:
    """Procesa un PDF. Cualquier fallo se convierte en resultado `ok=False`."""
    try:
        texto = texto_pdf(ruta)
    except PdfLimitError as exc:
        return construir_resultado(
            archivo=ruta.name,
            extractor=extractor,
            ok=False,
            datos=extractor.organizar({}),
            error=str(exc),
        )
    except (OSError, PdfReadError, ValueError) as exc:
        return construir_resultado(
            archivo=ruta.name,
            extractor=extractor,
            ok=False,
            datos=extractor.organizar({}),
            error=f"No se pudo leer el PDF: {exc}",
        )
    except Exception as exc:  # noqa: BLE001 — no tumbar el lote por un PDF raro
        return construir_resultado(
            archivo=ruta.name,
            extractor=extractor,
            ok=False,
            datos=extractor.organizar({}),
            error=f"Error inesperado al leer el PDF: {exc}",
        )

    if not texto.strip():
        return construir_resultado(
            archivo=ruta.name,
            extractor=extractor,
            ok=False,
            datos=extractor.organizar({}),
            error="El PDF no tiene texto extraíble.",
        )

    try:
        bruto = consultar_ollama(extractor.prompt(), texto, extractor.esquema())
    except OllamaError as exc:
        return construir_resultado(
            archivo=ruta.name,
            extractor=extractor,
            ok=False,
            datos=extractor.organizar({}),
            error=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        return construir_resultado(
            archivo=ruta.name,
            extractor=extractor,
            ok=False,
            datos=extractor.organizar({}),
            error=f"Error inesperado al consultar Ollama: {exc}",
        )

    try:
        datos = extractor.organizar(bruto)
        errores_validacion = extractor.validar(datos)
    except Exception as exc:  # noqa: BLE001
        return construir_resultado(
            archivo=ruta.name,
            extractor=extractor,
            ok=False,
            datos=extractor.organizar({}),
            error=f"Error al organizar/validar la respuesta: {exc}",
        )

    if errores_validacion:
        return construir_resultado(
            archivo=ruta.name,
            extractor=extractor,
            ok=False,
            datos=datos,
            errores_validacion=errores_validacion,
            error=(
                "Uno o más campos no cumplen el formato esperado. "
                "Revisa errores_validacion; los datos extraídos se conservan."
            ),
        )

    return construir_resultado(
        archivo=ruta.name,
        extractor=extractor,
        ok=True,
        datos=datos,
    )


def _resolver_rutas(pdfs: list[Path] | None) -> list[Path]:
    if pdfs is None:
        rutas = sorted(DOCS_DIR.glob("*.pdf"))
        origen = str(DOCS_DIR)
    else:
        rutas = sorted(
            (p for p in pdfs if p.is_file() and p.suffix.lower() == ".pdf"),
            key=lambda p: p.name.lower(),
        )
        origen = "upload"

    if not rutas:
        raise FileNotFoundError(
            f"No hay archivos PDF para procesar ({origen})."
        )
    return rutas
