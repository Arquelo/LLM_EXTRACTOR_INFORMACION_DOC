"""Servicio HTTP del extractor de documentos.

Expone una API FastAPI que orquesta la extracción con Ollama y
consulta los JSON / reportes generados en `output/`.

Arranque (desde la carpeta backend/):
    python server.py
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from extract import nombre_seguro, procesar_con_reporte, procesar_muestras
from extraction.report import cargar_reporte
from extractors import EXTRACTORES
from llm.ollama_client import verificar_ollama
from settings.config import (
    CORS_ORIGINS,
    EXTRACTOR,
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_FILES,
    OLLAMA_MODEL,
    SERVER_HOST,
    SERVER_PORT,
)
from settings.path import OUTPUT_DIR, UPLOADS_DIR

app = FastAPI(
    title="LLM Extractor Informacion Doc",
    description=(
        "API para extraer datos estructurados de documentos (PDF/TXT) con Ollama, "
        "validación Pydantic y reporte éxito/parcial/fallido."
    ),
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    ollama = verificar_ollama()
    status = "ok" if ollama.get("ok") and ollama.get("modelo_disponible") else "degraded"
    if not ollama.get("ok"):
        status = "error"
    return {
        "status": status,
        "modelo": OLLAMA_MODEL,
        "extractor": EXTRACTOR,
        "ollama": ollama,
    }


@app.get("/api/extractors")
def listar_extractores() -> dict:
    return {
        "activo": EXTRACTOR,
        "disponibles": sorted(EXTRACTORES.keys()),
    }


@app.post("/api/extract")
async def ejecutar_extraccion(
    files: list[UploadFile] = File(
        ...,
        description="Uno o más PDF/TXT (archivo suelto o carpeta).",
    ),
    extractor: str | None = Form(
        default=None,
        description="Clave del extractor. Si se omite, usa el configurado en .env.",
    ),
) -> dict:
    docs = [f for f in files if _es_documento(f)]
    if not docs:
        raise HTTPException(
            status_code=400,
            detail="No se recibieron PDF/TXT. Selecciona archivo(s) o una carpeta.",
        )
    if len(docs) > MAX_UPLOAD_FILES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Demasiados archivos ({len(docs)}). "
                f"Máximo permitido: {MAX_UPLOAD_FILES}."
            ),
        )

    lote = UPLOADS_DIR / uuid.uuid4().hex
    lote.mkdir(parents=True, exist_ok=True)
    rutas: list[Path] = []

    try:
        usados: set[str] = set()
        for archivo in docs:
            original = archivo.filename or "documento.pdf"
            destino_nombre = _nombre_unico(nombre_seguro(original), usados)
            usados.add(destino_nombre.lower())
            destino = lote / destino_nombre
            contenido = await archivo.read()
            if not contenido:
                continue
            if len(contenido) > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"'{original}' supera el tamaño máximo "
                        f"({MAX_UPLOAD_BYTES} bytes)."
                    ),
                )
            destino.write_bytes(contenido)
            rutas.append(destino)

        if not rutas:
            raise HTTPException(
                status_code=400,
                detail="Los archivos enviados están vacíos.",
            )

        try:
            resultados, reporte = procesar_con_reporte(extractor, rutas)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        shutil.rmtree(lote, ignore_errors=True)

    return _respuesta_lote(reporte)


@app.post("/api/extract/muestras")
def ejecutar_muestras(
    extractor: str | None = Query(default=None),
) -> dict:
    """Procesa el lote académico versionado en `docs/muestras/`."""
    try:
        _resultados, reporte = procesar_muestras(extractor)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _respuesta_lote(reporte)


@app.get("/api/report")
def obtener_reporte() -> dict:
    """Último reporte de lote (éxito / parcial / fallido + tasas)."""
    reporte = cargar_reporte()
    if reporte is None:
        raise HTTPException(
            status_code=404,
            detail="No hay reporte aún. Ejecuta /api/extract o /api/extract/muestras.",
        )
    return reporte


@app.get("/api/results")
def listar_resultados() -> dict:
    if not OUTPUT_DIR.exists():
        return {"total": 0, "archivos": []}

    archivos = sorted(
        p.name
        for p in OUTPUT_DIR.glob("*.json")
        if p.name not in {"reporte_lote.json"}
    )
    return {"total": len(archivos), "archivos": archivos}


@app.delete("/api/results")
def limpiar_resultados() -> dict:
    eliminados = _limpiar_output_dir()
    return {"eliminados": eliminados, "total": 0, "archivos": []}


@app.get("/api/results/{nombre}")
def obtener_resultado(nombre: str) -> dict:
    if "/" in nombre or "\\" in nombre or nombre.startswith("."):
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido.")

    ruta = OUTPUT_DIR / nombre
    if not ruta.is_file():
        raise HTTPException(status_code=404, detail=f"No existe {nombre}")

    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500, detail=f"JSON inválido en {nombre}"
        ) from exc


def _respuesta_lote(reporte: dict) -> dict:
    resumen = reporte.get("resumen") or {}
    return {
        "extractor": reporte.get("extractor", EXTRACTOR),
        "modelo": reporte.get("modelo", OLLAMA_MODEL),
        "total": resumen.get("total", 0),
        "exitosos": resumen.get("exitosos", 0),
        "parciales": resumen.get("parciales", 0),
        "fallidos": resumen.get("fallidos", 0),
        "tasa_exito": resumen.get("tasa_exito", 0),
        "tasa_parcial": resumen.get("tasa_parcial", 0),
        "tasa_fallo": resumen.get("tasa_fallo", 0),
        "reporte": reporte,
        "resultados": reporte.get("resultados", []),
    }


def _es_documento(archivo: UploadFile) -> bool:
    nombre = (archivo.filename or "").lower()
    tipo = (archivo.content_type or "").lower()
    return (
        nombre.endswith(".pdf")
        or nombre.endswith(".txt")
        or tipo in {"application/pdf", "application/x-pdf", "text/plain"}
    )


def _nombre_unico(nombre: str, usados: set[str]) -> str:
    if nombre.lower() not in usados:
        return nombre
    stem = Path(nombre).stem
    sufijo = Path(nombre).suffix or ".pdf"
    indice = 2
    while True:
        candidato = f"{stem}_{indice}{sufijo}"
        if candidato.lower() not in usados:
            return candidato
        indice += 1


def _limpiar_output_dir() -> int:
    if not OUTPUT_DIR.exists():
        return 0

    eliminados = 0
    for ruta in OUTPUT_DIR.iterdir():
        if ruta.is_file():
            ruta.unlink(missing_ok=True)
            eliminados += 1
    return eliminados


def main() -> None:
    print(f"Servicio en http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"Docs OpenAPI: http://127.0.0.1:{SERVER_PORT}/docs")
    print(f"CORS origins: {', '.join(CORS_ORIGINS)}")
    uvicorn.run(
        "server:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
