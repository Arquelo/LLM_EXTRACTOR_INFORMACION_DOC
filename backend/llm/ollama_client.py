"""Cliente HTTP para consultar Ollama y obtener JSON estructurado.

Envía el prompt del extractor junto con el texto del documento a
`POST {OLLAMA_BASE_URL}/api/chat`, fuerza la respuesta al esquema JSON
indicado y parsea el contenido devuelto.

La configuración (URL, modelo y timeout) sale de `settings.config`.
Si Ollama no responde, el JSON es inválido o no es un objeto, se aborta
con `SystemExit` y un mensaje orientado al operador.
"""

import json
import urllib.error
import urllib.request

from settings.config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT


def consultar_ollama(prompt: str, texto: str, esquema: dict) -> dict:
    """Consulta el chat de Ollama y devuelve un dict con los datos extraídos.

    Args:
        prompt: Instrucciones de sistema (rol del extractor y reglas de salida).
        texto: Contenido textual del documento a analizar.
        esquema: JSON Schema que Ollama debe respetar en `format`.

    Returns:
        Objeto JSON parseado a partir del mensaje de la respuesta.

    Raises:
        SystemExit: Si hay error HTTP/de red, o si el contenido no es un
            objeto JSON válido.
    """
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": f"Extrae los datos de este documento:\n\n{texto}",
            },
        ],
        "stream": False,
        "format": esquema,
        "options": {"temperature": 0},
    }
    cuerpo = json.dumps(payload).encode("utf-8")
    solicitud = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/chat",
        data=cuerpo,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(solicitud, timeout=OLLAMA_TIMEOUT) as respuesta:
            data = json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detalle = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Ollama respondió {exc.code}: {detalle}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"No se pudo conectar con Ollama en {OLLAMA_BASE_URL}. "
            f"Confirma que el servicio esté activo y que el modelo '{OLLAMA_MODEL}' exista. "
            f"Detalle: {exc.reason}"
        ) from exc

    contenido = data.get("message", {}).get("content", "")
    return _cargar_json(contenido)


def _cargar_json(contenido: str) -> dict:
    """Parsea el contenido de la respuesta a un objeto JSON.

    Si el modelo envuelve el JSON en un bloque markdown (```), lo elimina
    antes de hacer `json.loads`.

    Args:
        contenido: Texto crudo del campo `message.content` de Ollama.

    Returns:
        Diccionario resultante del parseo.

    Raises:
        SystemExit: Si el texto no es JSON válido o no es un objeto (`dict`).
    """
    texto = contenido.strip()
    if texto.startswith("```"):
        texto = texto.split("\n", 1)[-1]
        cierre = texto.rfind("```")
        if cierre != -1:
            texto = texto[:cierre]
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Ollama no devolvió JSON válido: {exc}") from exc
    if not isinstance(datos, dict):
        raise SystemExit("Ollama no devolvió un objeto JSON.")
    return datos
