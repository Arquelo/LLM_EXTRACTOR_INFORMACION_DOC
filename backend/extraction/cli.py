"""Entrada por línea de comandos para la extracción."""

from __future__ import annotations

import argparse
from pathlib import Path

from extraction.pipeline import procesar
from settings.config import OLLAMA_MODEL


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
    exitosos = sum(1 for r in resultados if r["ok"])
    print(f"Exitosos: {exitosos} · Fallidos: {len(resultados) - exitosos}")
    for salida in resultados:
        if salida["error"]:
            print(f"  {salida['archivo']}: {salida['error']}")
            for err in salida["errores_validacion"]:
                print(f"    - {err['campo']}: {err['motivo']}")
        else:
            print(f"  OK {salida['archivo']} -> {Path(salida['archivo']).stem}.json")
