"""Persistencia de resultados JSON en OUTPUT_DIR."""

from __future__ import annotations

import json
from pathlib import Path

from extraction.types import ResultadoExtraccion
from settings.path import OUTPUT_DIR


def destino_json(stem: str, usados: set[str], carpeta: Path | None = None) -> Path:
    """Evita pisar JSON previos cuando varios PDF comparten el mismo stem."""
    base = stem or "documento"
    candidato = base
    indice = 2
    while candidato.lower() in usados:
        candidato = f"{base}_{indice}"
        indice += 1
    usados.add(candidato.lower())
    return (carpeta or OUTPUT_DIR) / f"{candidato}.json"


def guardar_resultado(destino: Path, salida: ResultadoExtraccion) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(salida, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
