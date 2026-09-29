"""Servicio HTTP del extractor de documentos.

Expone una API FastAPI que orquesta la extracción de PDFs con Ollama y
consulta los JSON ya generados en `output/`.

Arranque (desde la carpeta backend/):
    python server.py

Host, puerto, CORS y límites salen de `settings.config` / `.env`.
La documentación interactiva queda en `/docs`.

Rutas:
    GET    /health                 Estado del API + reachability de Ollama.
    GET    /api/extractors         Extractores registrados y el activo por defecto.
    POST   /api/extract            Recibe PDF(s) por multipart y ejecuta extracción.
    GET    /api/results            Lista los JSON en `output/`.
    DELETE /api/results            Vacía `output/` (acción explícita).
    GET    /api/results/{nombre}   Devuelve el contenido de un JSON concreto.
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from extract import nombre_seguro, procesar
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
    description="API para extraer datos estructurados de documentos PDF con Ollama.",
    version="0.2.0",
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
    """Comprueba API + Ollama (tags) y disponibilidad del modelo configurado."""
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
    """Lista las claves de extractores disponibles y cuál está activo por defecto."""
    return {
        "activo": EXTRACTOR,
        "disponibles": sorted(EXTRACTORES.keys()),
    }


@app.post("/api/extract")
async def ejecutar_extraccion(
    files: list[UploadFile] = File(
        ...,
        description="Uno o más PDF (archivo suelto o contenido de una carpeta).",
    ),
    extractor: str | None = Form(
        default=None,
        description="Clave del extractor. Si se omite, usa el configurado en .env.",
    ),
) -> dict:
    """Recibe PDF(s) del cliente, los guarda temporalmente y ejecuta la extracción."""
    pdfs = [f for f in files if _es_pdf(f)]
    if not pdfs:
        raise HTTPException(
            status_code=400,
            detail="No se recibieron archivos PDF. Selecciona un archivo o una carpeta.",
        )
    if len(pdfs) > MAX_UPLOAD_FILES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Demasiados PDF ({len(pdfs)}). "
                f"Máximo permitido: {MAX_UPLOAD_FILES}."
            ),
        )

    lote = UPLOADS_DIR / uuid.uuid4().hex
    lote.mkdir(parents=True, exist_ok=True)
    rutas: list[Path] = []

    try:
        usados: set[str] = set()
        for archivo in pdfs:
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
            resultados = procesar(extractor, rutas)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        shutil.rmtree(lote, ignore_errors=True)

    return {
        "extractor": resultados[0]["extractor"] if resultados else EXTRACTOR,
        "modelo": OLLAMA_MODEL,
        "total": len(resultados),
        "exitosos": sum(1 for r in resultados if r.get("ok", True)),
        "fallidos": sum(1 for r in resultados if not r.get("ok", True)),
        "resultados": resultados,
    }


@app.get("/api/results")
def listar_resultados() -> dict:
    """Lista los JSON en `output/` (no modifica la carpeta)."""
    if not OUTPUT_DIR.exists():
        return {"total": 0, "archivos": []}

    archivos = sorted(p.name for p in OUTPUT_DIR.glob("*.json"))
    return {"total": len(archivos), "archivos": archivos}


@app.delete("/api/results")
def limpiar_resultados() -> dict:
    """Vacía `output/`. Acción destructiva explícita (no usar GET)."""
    eliminados = _limpiar_output_dir()
    return {"eliminados": eliminados, "total": 0, "archivos": []}


@app.get("/api/results/{nombre}")
def obtener_resultado(nombre: str) -> dict:
    """Devuelve el contenido de un resultado JSON por nombre de archivo."""
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


def _es_pdf(archivo: UploadFile) -> bool:
    nombre = (archivo.filename or "").lower()
    tipo = (archivo.content_type or "").lower()
    return nombre.endswith(".pdf") or tipo in {
        "application/pdf",
        "application/x-pdf",
    }


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
