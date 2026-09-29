"""Tests del paquete extraction (vía fachada extract)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from extract import nombre_seguro, procesar, texto_pdf
from llm.ollama_client import OllamaError

# Los mocks apuntan a donde se usan los símbolos (pipeline / pdf).
_TEXTO = "extraction.pipeline.texto_pdf"
_OLLAMA = "extraction.pipeline.consultar_ollama"
_OUT = "extraction.pipeline.OUTPUT_DIR"


# --- nombre_seguro -----------------------------------------------------------


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("informe.pdf", "informe.pdf"),
        ("", "documento.pdf"),
        ("   ", "documento.pdf"),
        ("../etc/passwd", "passwd.pdf"),
        ("carpeta/sub/doc.PDF", "doc.PDF"),
        ("a<>:|?.pdf", "a_.pdf"),
        ("sin_ext", "sin_ext.pdf"),
        ("...", "documento.pdf"),
    ],
)
def test_nombre_seguro(entrada: str, esperado: str) -> None:
    assert nombre_seguro(entrada) == esperado


# --- procesar: casos de error / éxito ----------------------------------------


def _pdf_falso(tmp_path: Path, nombre: str = "doc.pdf") -> Path:
    ruta = tmp_path / nombre
    ruta.write_bytes(b"%PDF-1.4 fake")
    return ruta


def test_procesar_sin_pdfs_levanta() -> None:
    with pytest.raises(FileNotFoundError, match="No hay archivos PDF"):
        procesar(pdfs=[])


def test_procesar_pdf_sin_texto(tmp_path: Path) -> None:
    pdf = _pdf_falso(tmp_path, "vacio.pdf")
    with (
        patch(_TEXTO, return_value="   "),
        patch(_OUT, tmp_path / "out"),
    ):
        (tmp_path / "out").mkdir()
        resultados = procesar(pdfs=[pdf])

    assert len(resultados) == 1
    assert resultados[0]["ok"] is False
    assert resultados[0]["error"] == "El PDF no tiene texto extraíble."
    assert resultados[0]["errores_validacion"] == []
    assert isinstance(resultados[0]["datos"], dict)


def test_procesar_pdf_ilegible_no_tumba_lote(tmp_path: Path) -> None:
    malo = _pdf_falso(tmp_path, "malo.pdf")
    bueno = _pdf_falso(tmp_path, "bueno.pdf")

    def _texto(ruta: Path) -> str:
        if ruta.name == "malo.pdf":
            raise OSError("archivo corrupto")
        return "Texto de constancia de prueba"

    def _ollama(_prompt: str, _texto: str, _esquema: dict[str, Any]) -> dict[str, Any]:
        return {"rfc": "XAXX010101000", "colonia": "12"}

    with (
        patch(_TEXTO, side_effect=_texto),
        patch(_OLLAMA, side_effect=_ollama),
        patch(_OUT, tmp_path / "out"),
    ):
        (tmp_path / "out").mkdir()
        resultados = procesar(pdfs=[malo, bueno])

    assert len(resultados) == 2
    por_nombre = {r["archivo"]: r for r in resultados}
    assert por_nombre["malo.pdf"]["ok"] is False
    assert "No se pudo leer el PDF" in (por_nombre["malo.pdf"]["error"] or "")
    assert "No se pudo leer el PDF" not in (por_nombre["bueno.pdf"]["error"] or "")
    assert por_nombre["bueno.pdf"]["archivo"] == "bueno.pdf"


def test_procesar_ollama_error_por_archivo(tmp_path: Path) -> None:
    a = _pdf_falso(tmp_path, "a.pdf")
    b = _pdf_falso(tmp_path, "b.pdf")

    llamadas = {"n": 0}

    def _ollama_mixto(
        _prompt: str, _texto: str, _esquema: dict[str, Any]
    ) -> dict[str, Any]:
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            raise OllamaError("Ollama caído")
        return {"rfc": "XAXX010101000", "colonia": "1"}

    with (
        patch(_TEXTO, return_value="contenido"),
        patch(_OLLAMA, side_effect=_ollama_mixto),
        patch(_OUT, tmp_path / "out"),
    ):
        (tmp_path / "out").mkdir()
        resultados = procesar(pdfs=[a, b])

    assert len(resultados) == 2
    assert resultados[0]["ok"] is False
    assert resultados[0]["error"] == "Ollama caído"
    assert resultados[1]["archivo"] == "b.pdf"
    assert "Ollama caído" not in (resultados[1]["error"] or "")


def test_procesar_validacion_fallida_conserva_datos(tmp_path: Path) -> None:
    pdf = _pdf_falso(tmp_path, "doc.pdf")
    bruto = {
        "rfc": "XAXX010101000",
        "curp": "CURP_INVALIDA",
        "colonia": "12",
        "codigo_postal": "01000",
        "fecha_inicio_operaciones": "15/03/2019",
    }

    with (
        patch(_TEXTO, return_value="contenido"),
        patch(_OLLAMA, return_value=bruto),
        patch(_OUT, tmp_path / "out"),
    ):
        (tmp_path / "out").mkdir()
        resultados = procesar(pdfs=[pdf])

    assert len(resultados) == 1
    r = resultados[0]
    assert r["ok"] is False
    assert r["error"] is not None
    assert "formato" in (r["error"] or "").lower()
    assert r["datos"]["curp"] == "CURP_INVALIDA"
    assert any(e["campo"] == "curp" for e in r["errores_validacion"])


def test_procesar_exito(tmp_path: Path) -> None:
    pdf = _pdf_falso(tmp_path, "ok.pdf")
    bruto = {
        "rfc": "XAXX010101000",
        "curp": "",
        "id_cif": "123",
        "colonia": "12",
        "codigo_postal": "01000",
        "fecha_inicio_operaciones": "01/01/2020",
        "fecha_ultimo_cambio_estado": "02/02/2020",
        "actividades_economicas": [],
        "regimenes": [],
        "obligaciones": [],
    }

    with (
        patch(_TEXTO, return_value="contenido"),
        patch(_OLLAMA, return_value=bruto),
        patch(_OUT, tmp_path / "out"),
    ):
        out = tmp_path / "out"
        out.mkdir()
        resultados = procesar(pdfs=[pdf])

    assert len(resultados) == 1
    assert resultados[0]["ok"] is True
    assert resultados[0]["error"] is None
    assert resultados[0]["errores_validacion"] == []
    assert (out / "ok.json").is_file()


def test_destino_json_unico_por_stem(tmp_path: Path) -> None:
    dir_a = tmp_path / "dir_a"
    dir_b = tmp_path / "dir_b"
    dir_a.mkdir()
    dir_b.mkdir()
    a = _pdf_falso(dir_a, "mismo.pdf")
    b = _pdf_falso(dir_b, "mismo.pdf")

    with (
        patch(_TEXTO, return_value=""),
        patch(_OUT, tmp_path / "out"),
    ):
        out = tmp_path / "out"
        out.mkdir()
        procesar(pdfs=[a, b])

    assert (out / "mismo.json").is_file()
    assert (out / "mismo_2.json").is_file()


def test_texto_pdf_usa_reader(tmp_path: Path) -> None:
    pdf = _pdf_falso(tmp_path)
    pagina = MagicMock()
    pagina.extract_text.return_value = "hola"
    reader = MagicMock()
    reader.pages = [pagina]

    with patch("extraction.pdf.PdfReader", return_value=reader):
        assert texto_pdf(pdf) == "hola"
