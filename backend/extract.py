"""Fachada de compatibilidad y punto de entrada CLI.

La lógica vive en el paquete `extraction/`. Este módulo reexporta la API
pública para no romper `from extract import procesar, nombre_seguro`.

Flujo: extraction/pdf → pipeline → results/storage (ver extraction/__init__.py).
"""

from extraction import (
    ErrorValidacion,
    ResultadoExtraccion,
    nombre_seguro,
    procesar,
    procesar_archivo,
    texto_pdf,
)
from extraction.cli import main

__all__ = [
    "ErrorValidacion",
    "ResultadoExtraccion",
    "main",
    "nombre_seguro",
    "procesar",
    "procesar_archivo",
    "texto_pdf",
]

if __name__ == "__main__":
    main()
