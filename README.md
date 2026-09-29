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

## Backend

```bash
cd backend
pip install -r requirements.txt
python server.py
```

- API: http://127.0.0.1:8000  
- OpenAPI: http://127.0.0.1:8000/docs  

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | API + estado de Ollama / modelo |
| GET | `/api/extractors` | Extractores disponibles |
| POST | `/api/extract` | Multipart `files` + opcional `extractor` |
| GET | `/api/results` | Lista JSON en `output/` |
| DELETE | `/api/results` | Vacía `output/` |
| GET | `/api/results/{nombre}` | Contenido de un resultado |

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

Abre http://127.0.0.1:5173 (proxy a `/api` y `/health`).

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
