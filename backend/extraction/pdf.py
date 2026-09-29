"""Lectura de PDF y normalización de nombres de archivo."""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

from settings.config import MAX_PDF_CHARS, MAX_PDF_PAGES

_NOMBRE_SEGURO = re.compile(r"[^\w.\-() ]+", re.UNICODE)


class PdfLimitError(ValueError):
    """El PDF supera los límites configurados de páginas o caracteres."""


def texto_pdf(
    ruta: Path,
    *,
    max_paginas: int | None = None,
    max_chars: int | None = None,
) -> str:
    """Extrae texto de un PDF respetando topes de páginas y caracteres."""
    limite_paginas = MAX_PDF_PAGES if max_paginas is None else max_paginas
    limite_chars = MAX_PDF_CHARS if max_chars is None else max_chars

    reader = PdfReader(ruta)
    total_paginas = len(reader.pages)
    if total_paginas > limite_paginas:
        raise PdfLimitError(
            f"El PDF tiene {total_paginas} páginas; el máximo permitido es {limite_paginas}."
        )

    partes: list[str] = []
    acumulado = 0
    for pagina in reader.pages:
        trozo = pagina.extract_text() or ""
        if acumulado + len(trozo) > limite_chars:
            restante = limite_chars - acumulado
            if restante > 0:
                partes.append(trozo[:restante])
            raise PdfLimitError(
                f"El texto del PDF supera el máximo de {limite_chars} caracteres."
            )
        partes.append(trozo)
        acumulado += len(trozo)

    return "\n".join(partes)


def nombre_seguro(nombre: str) -> str:
    """Normaliza un nombre de archivo para guardarlo sin path traversal."""
    base = Path(nombre).name.strip() or "documento.pdf"
    limpio = _NOMBRE_SEGURO.sub("_", base).strip("._") or "documento.pdf"
    if not limpio.lower().endswith(".pdf"):
        limpio = f"{limpio}.pdf"
    return limpio
