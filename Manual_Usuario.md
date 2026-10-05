# Manual de usuario — LLM Extractor

Guía para usar la interfaz web. Antes de empezar, el backend y Ollama deben estar en ejecución (ver [Instrucciones_instalaccion,md](Instrucciones_instalaccion,md)).

## Abrir la aplicación

1. Arranca el backend (`python server.py` en `backend/`).
2. Arranca el frontend (`npm run dev` en `frontend/`).
3. Abre en el navegador: [http://127.0.0.1:5173](http://127.0.0.1:5173)

Al cargar, la pantalla comprueba automáticamente el backend y Ollama. El mensaje de estado (barra superior del panel) indica si todo está listo.

| Mensaje típico | Significado |
|----------------|-------------|
| `Listo · modelo … · Ollama OK` | Puedes extraer documentos |
| `Backend up · Ollama: …` | La API responde, pero el modelo no está disponible |
| `No se pudo conectar con el backend…` | No está corriendo el servidor en el puerto 8000 |

---

## Controles de la interfaz

### Extractor (lista desplegable)

Elige el tipo de documento a procesar. Por defecto usa `constancia_situacion_fiscal` (el configurado en `.env`). Si el backend no responde, la lista queda deshabilitada.

### Elegir archivo(s)

Abre el diálogo del sistema para seleccionar uno o varios archivos **PDF** o **TXT**.

- Solo se aceptan esos formatos; otros tipos se ignoran.
- Al elegir archivos, se limpia cualquier selección previa hecha con “Elegir carpeta”.
- Debajo verás un resumen: `1 archivo: nombre.pdf` o `N archivos listos.`

### Elegir carpeta

Permite seleccionar una **carpeta completa**. El navegador incluirá los archivos de esa carpeta; la app filtra y deja solo PDF/TXT.

- Útil para lotes (por ejemplo 10 constancias en una carpeta).
- Al elegir carpeta, se limpia la selección hecha con “Elegir archivo(s)”.
- Si la carpeta no tiene PDF/TXT válidos, verás: `Ningún PDF/TXT válido en la selección.`

### Ejecutar extracción

Envía los archivos seleccionados al backend (`POST /api/extract`), que:

1. Lee el texto de cada PDF/TXT.
2. Consulta Ollama con el esquema del extractor.
3. Valida los datos (formatos + Pydantic).
4. Clasifica cada documento como **éxito**, **parcial** o **fallido**.
5. Guarda JSON en `backend/output/` y actualiza el reporte del lote.

El botón está **deshabilitado** hasta que:

- el backend y Ollama estén OK, y
- haya al menos un archivo seleccionado.

Durante el proceso verás `Extrayendo N archivo(s)…`. Con documentos grandes o muchos archivos puede tardar varios minutos (timeout de Ollama por defecto: 300 s por consulta).

### Correr muestras académicas

No usa tus archivos: procesa el lote versionado en `backend/docs/muestras/` (casos fáciles y difíciles). Sirve para demostrar el flujo completo, incluidos documentos que fallan o quedan parciales.

Requiere backend + Ollama OK. No hace falta seleccionar archivos.

### Ver último reporte

Carga el último reporte guardado en el servidor (`GET /api/report`), sin volver a llamar a Ollama. Útil si ya corriste una extracción y quieres revisar tasas y resultados otra vez.

Si aún no hay reporte, verás un error indicando que primero debes ejecutar una extracción o las muestras.

### Limpiar resultados

Pide confirmación y vacía la carpeta `backend/output/` en el servidor (`DELETE /api/results`). Borra los JSON generados y el reporte en disco. No borra tus PDF originales.

---

## Cómo leer los resultados

Tras una extracción exitosa (o al ver el reporte), el panel inferior muestra:

### Reporte del lote (tarjetas)

- **Éxito** — documentos que cumplieron el esquema (obligatorios válidos, sin errores de formato).
- **Parcial** — hay datos útiles, pero faltan obligatorios o hay formatos inválidos.
- **Fallido** — error duro (lectura, Ollama, timeout) o sin datos útiles.
- **Total** — cantidad de documentos y modelo usado.

### Lista por documento

Cada ítem indica estado + nombre de archivo. Si aplica:

- mensaje de error,
- lista de `errores_validacion` (campo y motivo),
- JSON de los datos extraídos.

### JSON completo

El payload completo de la respuesta (tasas, resultados, etc.) para copiar o inspeccionar.

---

## Flujo recomendado

1. Confirma que el estado diga **Listo · Ollama OK**.
2. Selecciona el extractor (si hay más de uno).
3. Usa **Elegir archivo(s)** o **Elegir carpeta**.
4. Pulsa **Ejecutar extracción** y espera el reporte.
5. Revisa estados éxito / parcial / fallido.
6. Opcional: **Ver último reporte** más tarde, o **Limpiar resultados** cuando ya no necesites los JSON.

Para la demo académica: **Correr muestras académicas** y observar al menos un caso parcial o fallido (por ejemplo `04_dificil_incompleto.txt` / `05_dificil_ambiguo.txt`).

---

## Notas útiles

- Obligatorios de negocio: `rfc`, `fecha_inicio_operaciones`, `estatus_padron`. Detalle en [backend/docs/decisiones_validacion.md](backend/docs/decisiones_validacion.md).
- Límites de lote/tamaño/páginas están en `.env` (`MAX_UPLOAD_FILES`, `MAX_UPLOAD_BYTES`, etc.).
- Si ves reintentos o timeouts con muchos PDF, Ollama está tardando más del tiempo configurado; puedes subir `OLLAMA_TIMEOUT` o reducir el tamaño del lote.
