"""Reporte agregado del lote de extracción."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from extraction.types import ReporteLote, ResultadoExtraccion, ResumenLote
from settings.path import OUTPUT_DIR

REPORTE_JSON = "reporte_lote.json"
REPORTE_CSV = "reporte_lote.csv"


def construir_reporte(
    resultados: list[ResultadoExtraccion],
    *,
    extractor: str,
    modelo: str,
) -> ReporteLote:
    total = len(resultados)
    exitosos = sum(1 for r in resultados if r.get("estado") == "exito")
    parciales = sum(1 for r in resultados if r.get("estado") == "parcial")
    fallidos = sum(1 for r in resultados if r.get("estado") == "fallido")
    resumen: ResumenLote = {
        "total": total,
        "exitosos": exitosos,
        "parciales": parciales,
        "fallidos": fallidos,
        "tasa_exito": round((exitosos / total) * 100, 2) if total else 0.0,
        "tasa_parcial": round((parciales / total) * 100, 2) if total else 0.0,
        "tasa_fallo": round((fallidos / total) * 100, 2) if total else 0.0,
    }
    return {
        "extractor": extractor,
        "modelo": modelo,
        "resumen": resumen,
        "resultados": resultados,
    }


def guardar_reporte(reporte: ReporteLote, carpeta: Path | None = None) -> dict[str, str]:
    """Guarda JSON + CSV del reporte. Devuelve rutas relativas."""
    out = carpeta or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    ruta_json = out / REPORTE_JSON
    ruta_csv = out / REPORTE_CSV

    ruta_json.write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with ruta_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["archivo", "estado", "ok", "error", "errores_validacion"],
        )
        writer.writeheader()
        for r in reporte["resultados"]:
            writer.writerow(
                {
                    "archivo": r.get("archivo", ""),
                    "estado": r.get("estado", ""),
                    "ok": r.get("ok", False),
                    "error": r.get("error") or "",
                    "errores_validacion": "; ".join(
                        f"{e.get('campo')}: {e.get('motivo')}"
                        for e in (r.get("errores_validacion") or [])
                    ),
                }
            )

    return {"json": str(ruta_json), "csv": str(ruta_csv)}


def cargar_reporte(carpeta: Path | None = None) -> ReporteLote | None:
    ruta = (carpeta or OUTPUT_DIR) / REPORTE_JSON
    if not ruta.is_file():
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))
