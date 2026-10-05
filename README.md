# LLM Extractor — Constancia / documentos PDF

Extrae datos estructurados de PDFs con **Ollama** (backend FastAPI + frontend Vite).

## Requisitos

- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.com/) con el modelo configurado (p. ej. `ollama pull llama3.2`)

## Configuración

```bash
cp .env.example .env
# Edita OLLAMA_MODEL, límites, CORS, etc.
```

El backend carga `.env` de la raíz del repo y, si existe, `backend/.env` (este último tiene prioridad).

## Resultados esperados

Las entradas de prueba (casos fáciles y difíciles) están en [`backend/docs/muestras/`](backend/docs/muestras/).  
Una corrida de referencia del lote académico queda en [`resultados_pruebas/`](resultados_pruebas/) (JSON por documento + `reporte_lote.json` / `.csv`), para contrastar tu ejecución local.


## Backend

```bash
cd backend
pip install -r requirements.txt
python server.py
```

- API: [http://127.0.0.1:8000](http://127.0.0.1:8000)  
- OpenAPI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)



### Endpoints


| Método | Ruta                    | Descripción                                        |
| ------ | ----------------------- | -------------------------------------------------- |
| GET    | `/health`               | API + estado de Ollama / modelo                    |
| GET    | `/api/extractors`       | Extractores disponibles                            |
| POST   | `/api/extract`          | Multipart PDF/TXT + opcional `extractor` → reporte |
| POST   | `/api/extract/muestras` | Lote académico en `docs/muestras/`                 |
| GET    | `/api/report`           | Último reporte (tasas éxito/parcial/fallo)         |
| GET    | `/api/results`          | Lista JSON en `output/`                            |
| DELETE | `/api/results`          | Vacía `output/`                                    |
| GET    | `/api/results/{nombre}` | Contenido de un resultado                          |




### Checklist académico

- Esquema Pydantic + formatos (numérico, fecha, enum `estatus_padron`)
- Structured output Ollama (`format` JSON Schema)
- Validación programática post-modelo (formatos + Pydantic)
- Obligatorios de negocio: `rfc`, `fecha_inicio_operaciones`, `estatus_padron` — ver [decisiones de validación](backend/docs/decisiones_validacion.md)
- Estados por documento: `exito` / `parcial` / `fallido`
- Reintentos con tope ante JSON inválido / HTTP transitorio
- 6 muestras versionadas (2 difíciles) en `backend/docs/muestras/`
- Reporte web + `output/reporte_lote.json` / `.csv`



### Tests

```bash
cd backend
python -m pytest tests -v
```



## Frontend

```bash
cd frontend
npm install
npm run dev
```

Abre [http://127.0.0.1:5173](http://127.0.0.1:5173) (proxy a `/api` y `/health`).

## Límites y resiliencia

Definidos en `.env`:

- `MAX_UPLOAD_FILES` / `MAX_UPLOAD_BYTES` — tope de lote y tamaño por archivo  
- `MAX_PDF_PAGES` / `MAX_PDF_CHARS` — tope al leer el PDF  
- `OLLAMA_RETRIES` / `OLLAMA_RETRY_BACKOFF` — reintentos ante timeout/5xx  
- `CORS_ORIGINS` — orígenes permitidos (sin `*`)



## Estructura

```
backend/
  extract.py          # Fachada CLI / imports
  extraction/         # Pipeline PDF → Ollama → JSON
  extractors/         # Esquemas por tipo de documento
  llm/ollama_client.py
  server.py
  docs/               # PDF locales para la CLI (no versionados)
  tests/
frontend/
```

Los PDF de `backend/docs/` son solo para uso local (`python extract.py`).
No van al repositorio; copia tus muestras ahí después del clon.