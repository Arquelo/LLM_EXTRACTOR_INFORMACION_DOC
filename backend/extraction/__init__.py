"""Paquete de extracción: documento → LLM → validación → JSON + reporte.

Módulos:
    documents.py Lectura PDF/TXT
    pdf.py       Lectura PDF y sanitizar nombres
    pipeline.py  Orquestar el lote (Ollama + validación)
    results.py   Armar ResultadoExtraccion (exito/parcial/fallido)
    report.py    Reporte agregado del lote (JSON/CSV)
    storage.py   Guardar JSON en output/
    types.py     TypedDict del contrato
    cli.py       Entrada por línea de comandos

API pública estable para `server.py` y la CLI (`extract.py`).
"""

from extraction.pdf import nombre_seguro, texto_pdf
from extraction.pipeline import (
    procesar,
    procesar_archivo,
    procesar_con_reporte,
    procesar_muestras,
)
from extraction.report import cargar_reporte, construir_reporte
from extraction.types import ErrorValidacion, EstadoExtraccion, ReporteLote, ResultadoExtraccion

__all__ = [
    "ErrorValidacion",
    "EstadoExtraccion",
    "ReporteLote",
    "ResultadoExtraccion",
    "cargar_reporte",
    "construir_reporte",
    "nombre_seguro",
    "procesar",
    "procesar_archivo",
    "procesar_con_reporte",
    "procesar_muestras",
    "texto_pdf",
]
