import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader

from extractors import obtener_extractor
from llm.ollama_client import consultar_ollama
from settings.config import OLLAMA_MODEL
from settings.path import DOCS_DIR, OUTPUT_DIR

_NOMBRE_SEGURO = re.compile(r"[^\w.\-() ]+", re.UNICODE)


def texto_pdf(ruta: Path) -> str:
    reader = PdfReader(ruta)
    return "\n".join((pagina.extract_text() or "") for pagina in reader.pages)


def nombre_seguro(nombre: str) -> str:
    """Normaliza un nombre de archivo para guardarlo sin path traversal."""
    base = Path(nombre).name.strip() or "documento.pdf"
    limpio = _NOMBRE_SEGURO.sub("_", base).strip("._") or "documento.pdf"
    if not limpio.lower().endswith(".pdf"):
        limpio = f"{limpio}.pdf"
    return limpio


def procesar(
    clave_extractor: str | None = None,
    pdfs: list[Path] | None = None,
) -> list[dict]:
    """Extrae datos de una lista de PDFs (o de `docs/` si no se pasan archivos)."""
    extractor = obtener_extractor(clave_extractor)

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

    OUTPUT_DIR.mkdir(exist_ok=True)
    resultados: list[dict] = []

    for ruta in rutas:
        texto = texto_pdf(ruta)
        destino = OUTPUT_DIR / f"{ruta.stem}.json"

        if not texto.strip():
            salida = {
                "archivo": ruta.name,
                "extractor": extractor.clave,
                "modelo": OLLAMA_MODEL,
                "error": "El PDF no tiene texto extraíble.",
                "datos": extractor.organizar({}),
            }
            _guardar(destino, salida)
            resultados.append(salida)
            continue

        bruto = consultar_ollama(extractor.prompt(), texto, extractor.esquema())
        datos = extractor.organizar(bruto)
        salida = {
            "archivo": ruta.name,
            "extractor": extractor.clave,
            "modelo": OLLAMA_MODEL,
            "datos": datos,
        }
        _guardar(destino, salida)
        resultados.append(salida)

    return resultados


def _guardar(destino: Path, salida: dict) -> None:
    destino.write_text(
        json.dumps(salida, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extrae datos de los PDF en docs usando Ollama."
    )
    parser.add_argument(
        "--extractor",
        default=None,
        help="Clave del extractor. Si se omite, usa EXTRACTOR del archivo .env.",
    )
    args = parser.parse_args()
    try:
        resultados = procesar(args.extractor)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Extractor: {resultados[0]['extractor']}")
    print(f"Modelo: {OLLAMA_MODEL}")
    print(f"Archivos: {len(resultados)}")
    for salida in resultados:
        rfc = (salida.get("datos") or {}).get("rfc", "")
        if salida.get("error"):
            print(f"  {salida['archivo']}: {salida['error']}")
        else:
            print(f"  RFC: {rfc} -> {Path(salida['archivo']).stem}.json")


if __name__ == "__main__":
    main()
