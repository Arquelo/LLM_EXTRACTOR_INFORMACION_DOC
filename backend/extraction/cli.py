"""Entrada por línea de comandos para la extracción."""

from __future__ import annotations

import argparse
from pathlib import Path

from extraction.pipeline import procesar_con_reporte, procesar_muestras
from settings.config import OLLAMA_MODEL


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extrae datos de documentos (PDF/TXT) usando Ollama."
    )
    parser.add_argument(
        "--extractor",
        default=None,
        help="Clave del extractor. Si se omite, usa EXTRACTOR del archivo .env.",
    )
    parser.add_argument(
        "--muestras",
        action="store_true",
        help="Procesa docs/muestras/ (lote académico versionado).",
    )
    args = parser.parse_args()
    try:
        if args.muestras:
            resultados, reporte = procesar_muestras(args.extractor)
        else:
            resultados, reporte = procesar_con_reporte(args.extractor)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    resumen = reporte["resumen"]
    print(f"Extractor: {reporte['extractor']}")
    print(f"Modelo: {OLLAMA_MODEL}")
    print(
        f"Total: {resumen['total']} · Éxito: {resumen['exitosos']} "
        f"({resumen['tasa_exito']}%) · Parcial: {resumen['parciales']} "
        f"({resumen['tasa_parcial']}%) · Fallido: {resumen['fallidos']} "
        f"({resumen['tasa_fallo']}%)"
    )
    for salida in resultados:
        estado = salida.get("estado", "?")
        if salida.get("error"):
            print(f"  [{estado}] {salida['archivo']}: {salida['error']}")
            for err in salida.get("errores_validacion") or []:
                print(f"    - {err['campo']}: {err['motivo']}")
        else:
            print(f"  [{estado}] {salida['archivo']} -> {Path(salida['archivo']).stem}.json")
