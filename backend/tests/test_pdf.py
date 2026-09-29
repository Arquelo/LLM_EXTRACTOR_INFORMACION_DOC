"""Tests de límites al leer PDF."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from extraction.pdf import PdfLimitError, texto_pdf


def test_texto_pdf_respeta_max_paginas(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    reader = MagicMock()
    reader.pages = [MagicMock(), MagicMock(), MagicMock()]

    with (
        patch("extraction.pdf.PdfReader", return_value=reader),
        pytest.raises(PdfLimitError, match="páginas"),
    ):
        texto_pdf(pdf, max_paginas=2, max_chars=10_000)


def test_texto_pdf_respeta_max_chars(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    pagina = MagicMock()
    pagina.extract_text.return_value = "abcdefghij"
    reader = MagicMock()
    reader.pages = [pagina]

    with (
        patch("extraction.pdf.PdfReader", return_value=reader),
        pytest.raises(PdfLimitError, match="caracteres"),
    ):
        texto_pdf(pdf, max_paginas=10, max_chars=5)
