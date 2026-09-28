import json
import urllib.error
import urllib.request

from settings.config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT


def consultar_ollama(prompt: str, texto: str, esquema: dict) -> dict:
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
