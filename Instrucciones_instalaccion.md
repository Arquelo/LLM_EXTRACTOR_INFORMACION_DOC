# Instrucciones de instalación — LLM Extractor

Pasos para configurar el entorno desde cero (backend, frontend y Ollama). Resumen ampliado de lo descrito en el [README.md](README.md).

## Requisitos previos

| Herramienta | Versión sugerida | Para qué |
|-------------|------------------|----------|
| Python | 3.11 o superior | Backend FastAPI |
| Node.js | 18 o superior (incluye npm) | Frontend Vite |
| Ollama | Última estable | Modelo LLM local |
| Git | Cualquiera | Clonar el repositorio |

Comprueba versiones:

```bash
python --version
node --version
npm --version
ollama --version
```

---

## 1. Clonar / abrir el proyecto

```bash
cd Ruta/donde/tengas/el/repo
# Si aún no lo tienes:
# git clone <url-del-repositorio>
cd Extractor-Contenido-LLM
```

---

## 2. Instalar Ollama y el modelo

1. Descarga e instala Ollama desde [https://ollama.com/](https://ollama.com/).
2. Abre una terminal y descarga el modelo configurado en el proyecto (por defecto `llama3.2`):

```bash
ollama pull llama3.2
```

3. Deja el servicio Ollama en ejecución. En la mayoría de instalaciones arranca solo; puedes probar:

```bash
ollama list
```

El backend habla con Ollama en `http://localhost:11434` (`OLLAMA_BASE_URL` en `.env`).

---

## 3. Configurar variables de entorno

En la **raíz** del repositorio:

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

Edita `.env` si necesitas cambiar modelo, timeouts, CORS o límites. Valores importantes:

| Variable | Descripción |
|----------|-------------|
| `EXTRACTOR` | Extractor activo (`constancia_situacion_fiscal`) |
| `OLLAMA_BASE_URL` | URL de Ollama |
| `OLLAMA_MODEL` | Nombre del modelo (debe existir en `ollama list`) |
| `OLLAMA_TIMEOUT` | Segundos máximos de espera por consulta |
| `OLLAMA_RETRIES` | Reintentos ante timeout / errores reintentables |
| `CORS_ORIGINS` | Orígenes del frontend (sin `*`) |
| `MAX_UPLOAD_FILES` / `MAX_UPLOAD_BYTES` | Límites de carga |
| `MAX_PDF_PAGES` / `MAX_PDF_CHARS` | Límites al leer PDF |

El backend carga `.env` de la raíz y, si existe, `backend/.env` (este último tiene prioridad).

---

## 4. Backend (Python)

```bash
cd backend
```

### (Recomendado) Entorno virtual

```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### Instalar librerías

```bash
pip install -r requirements.txt
```

Dependencias incluidas: FastAPI, uvicorn, pypdf, python-dotenv, python-multipart, httpx, pydantic, pytest.

### Arrancar la API

```bash
python server.py
```

- API: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Documentación OpenAPI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Salud: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

Deja esta terminal abierta mientras uses el sistema.

### Tests (opcional)

```bash
cd backend
python -m pytest tests -v
```

---

## 5. Frontend (Node / Vite)

Abre **otra** terminal:

```bash
cd frontend
npm install
npm run dev
```

Abre [http://127.0.0.1:5173](http://127.0.0.1:5173). Vite hace proxy de `/api` y `/health` hacia el backend en el puerto 8000.

El uso de la interfaz está en [Manual_Usuario.md](Manual_Usuario.md).

---

## 6. Orden de arranque (checklist)

1. Ollama instalado y modelo descargado (`ollama pull llama3.2`).
2. Archivo `.env` creado a partir de `.env.example`.
3. Backend: `pip install -r requirements.txt` → `python server.py`.
4. Frontend: `npm install` → `npm run dev`.
5. Navegador en `http://127.0.0.1:5173` con estado **Listo · Ollama OK**.

---

## Endpoints principales (referencia)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | API + estado de Ollama / modelo |
| GET | `/api/extractors` | Extractores disponibles |
| POST | `/api/extract` | Multipart PDF/TXT → reporte |
| POST | `/api/extract/muestras` | Lote académico en `docs/muestras/` |
| GET | `/api/report` | Último reporte |
| GET | `/api/results` | Lista JSON en `output/` |
| DELETE | `/api/results` | Vacía `output/` |
| GET | `/api/results/{nombre}` | Contenido de un resultado |

---

## Problemas frecuentes

| Síntoma | Qué revisar |
|---------|-------------|
| Frontend: no conecta al backend | ¿`python server.py` está corriendo? ¿Puerto 8000 libre? |
| Estado “modelo no disponible” | `ollama pull <modelo>` y que coincida con `OLLAMA_MODEL` |
| Timeout al extraer | Subir `OLLAMA_TIMEOUT`, lote más pequeño, o modelo más liviano |
| Error de CORS | `CORS_ORIGINS` debe incluir `http://127.0.0.1:5173` |
| `pip` / `npm` fallan | Versiones de Python ≥ 3.11 y Node ≥ 18 |

---

## Estructura relevante

```
Extractor-Contenido-LLM/
  .env.example          # Plantilla de configuración
  backend/
    requirements.txt    # Dependencias Python
    server.py           # API FastAPI
    docs/muestras/      # Muestras académicas
    output/             # JSON generados (local)
  frontend/
    package.json        # Dependencias Node
    src/main.js         # Lógica de la UI
```
