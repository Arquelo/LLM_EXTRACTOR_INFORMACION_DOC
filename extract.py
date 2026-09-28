import argparse
import json
from pathlib import Path

from pypdf import PdfReader

from config import OLLAMA_MODEL
from extractors import obtener_extractor
from llm.ollama_client import consultar_ollama
from path import DOCS_DIR, OUTPUT_DIR


def texto_pdf(ruta: Path) -> str:
    reader = PdfReader(ruta)
    return "\n".join((pagina.extract_text() or "") for pagina in reader.pages)


def procesar(clave_extractor: str | None = None) -> None:
    extractor = obtener_extractor(clave_extractor)
    pdfs = sorted(DOCS_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No hay archivos PDF en {DOCS_DIR}")

    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"Extractor: {extractor.clave}")
    print(f"Modelo: {OLLAMA_MODEL}")
    print(f"Archivos: {len(pdfs)}")

    for ruta in pdfs:
        print(f"Procesando {ruta.name}...")
        texto = texto_pdf(ruta)
        destino = OUTPUT_DIR / f"{ruta.stem}.json"

        if not texto.strip():
            salida = {
                "archivo": ruta.name,
                "extractor": extractor.clave,
                "error": "El PDF no tiene texto extraíble.",
                "datos": extractor.organizar({}),
            }
            _guardar(destino, salida)
            print("  Sin texto extraíble.")
            continue

        bruto = consultar_ollama(extractor.prompt(), texto, extractor.esquema())
        datos = extractor.organizar(bruto)
        salida = {
            "archivo": ruta.name,
            "extractor": extractor.clave,
            "datos": datos,
        }
        _guardar(destino, salida)
        print(f"  RFC: {datos.get('rfc', '')} -> {destino.name}")


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
    procesar(args.extractor)


if __name__ == "__main__":
    main()
