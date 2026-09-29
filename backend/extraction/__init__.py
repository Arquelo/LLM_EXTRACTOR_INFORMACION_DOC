"""Paquete de extracción: PDF → LLM → validación → JSON.

Módulos:
    pdf.py       Leer PDF y sanitizar nombres
    pipeline.py  Orquestar el lote (Ollama + validación)
    results.py   Armar ResultadoExtraccion
    storage.py   Guardar JSON en output/
    types.py     TypedDict del contrato
    cli.py       Entrada por línea de comandos

API pública estable para `server.py` y la CLI (`extract.py`).
"""

from extraction.pdf import nombre_seguro, texto_pdf
from extraction.pipeline import procesar, procesar_archivo
from extraction.types import ErrorValidacion, ResultadoExtraccion

__all__ = [
    "ErrorValidacion",
    "ResultadoExtraccion",
    "nombre_seguro",
    "procesar",
    "procesar_archivo",
    "texto_pdf",
]
