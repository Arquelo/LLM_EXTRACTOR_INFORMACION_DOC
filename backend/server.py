"""Servicio HTTP del extractor de documentos.

Expone una API FastAPI que orquesta la extracción de PDFs con Ollama y
consulta los JSON ya generados en `output/`.

Arranque (desde la carpeta backend/):
    python server.py

Host y puerto salen de `settings.config` (`SERVER_HOST`, `SERVER_PORT`).
La documentación interactiva queda en `/docs`.

Rutas:
    GET  /health                 Estado del servicio, modelo y extractor activos.
    GET  /api/extractors         Extractores registrados y el activo por defecto.
    POST /api/extract            Recibe PDF(s) por multipart y ejecuta extracción.
    GET  /api/results            Lista los JSON disponibles en `output/`.
    GET  /api/results/{nombre}   Devuelve el contenido de un JSON concreto.
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
from settings.config import EXTRACTOR, OLLAMA_MODEL, SERVER_HOST, SERVER_PORT
from settings.path import OUTPUT_DIR, UPLOADS_DIR

app = FastAPI(
    title="LLM Extractor Informacion Doc",
    description="API para extraer datos estructurados de documentos PDF con Ollama.",
    version="0.1.0",
)

# Permite que el frontend (otro origen/puerto) consuma la API en desarrollo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    """Comprueba que el API responde e indica modelo/extractor configurados."""
    return {"status": "ok", "modelo": OLLAMA_MODEL, "extractor": EXTRACTOR}


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
    """Recibe PDF(s) del cliente, los guarda temporalmente y ejecuta la extracción.

    El frontend puede enviar un archivo, varios, o todos los PDF de una carpeta
    seleccionada con `webkitdirectory`. No es necesario copiarlos a `docs/`.
    """
    pdfs = [f for f in files if _es_pdf(f)]
    if not pdfs:
        raise HTTPException(
            status_code=400,
            detail="No se recibieron archivos PDF. Selecciona un archivo o una carpeta.",
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
        except SystemExit as exc:
            # Errores de conexión o respuesta inválida desde el cliente Ollama.
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        shutil.rmtree(lote, ignore_errors=True)

    return {
        "extractor": resultados[0]["extractor"] if resultados else EXTRACTOR,
        "modelo": OLLAMA_MODEL,
        "total": len(resultados),
        "resultados": resultados,
    }


@app.get("/api/results")
def listar_resultados() -> dict:
    """Lista los nombres de JSON ya generados en `output/`."""
    if not OUTPUT_DIR.exists():
        return {"total": 0, "archivos": []}

    archivos = sorted(p.name for p in OUTPUT_DIR.glob("*.json"))
    return {"total": len(archivos), "archivos": archivos}


@app.get("/api/results/{nombre}")
def obtener_resultado(nombre: str) -> dict:
    """Devuelve el contenido de un resultado JSON por nombre de archivo.

    Rechaza rutas con separadores o que empiecen por punto para evitar
    lecturas fuera de `output/`.
    """
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


def main() -> None:
    """Arranca Uvicorn con el host y puerto definidos en settings."""
    print(f"Servicio en http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"Docs OpenAPI: http://127.0.0.1:{SERVER_PORT}/docs")
    uvicorn.run(
        "server:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
