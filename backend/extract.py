"""Fachada de compatibilidad y punto de entrada CLI.

La lógica vive en el paquete `extraction/`. Este módulo reexporta la API
pública para no romper `from extract import procesar, nombre_seguro`.

Flujo: extraction/documents|pdf → pipeline → results/report/storage
(ver extraction/__init__.py).
"""

from extraction import (
    ErrorValidacion,
    EstadoExtraccion,
    ReporteLote,
    ResultadoExtraccion,
    nombre_seguro,
    procesar,
    procesar_archivo,
    procesar_con_reporte,
    procesar_muestras,
    texto_pdf,
)
from extraction.cli import main

__all__ = [
    "ErrorValidacion",
    "EstadoExtraccion",
    "ReporteLote",
    "ResultadoExtraccion",
    "main",
    "nombre_seguro",
    "procesar",
    "procesar_archivo",
    "procesar_con_reporte",
    "procesar_muestras",
    "texto_pdf",
]

if __name__ == "__main__":
    main()
