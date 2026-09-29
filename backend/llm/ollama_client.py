"""Cliente HTTP para consultar Ollama y obtener JSON estructurado.

Envía el prompt del extractor junto con el texto del documento a
`POST {base_url}/api/chat`, fuerza la respuesta al esquema JSON
indicado y parsea el contenido devuelto.

Por defecto usa `settings.config` (URL, modelo, timeouts, retries). Se pueden
inyectar `base_url`, `model`, timeouts, `retries` o un `httpx.Client`.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from settings.config import (
    OLLAMA_BASE_URL,
    OLLAMA_CONNECT_TIMEOUT,
    OLLAMA_MODEL,
    OLLAMA_RETRIES,
    OLLAMA_RETRY_BACKOFF,
    OLLAMA_TIMEOUT,
)

logger = logging.getLogger(__name__)

_DETALLE_MAX = 500
# Errores HTTP que merecen reintento (transitorios).
_HTTP_RETRIABLE = frozenset({408, 425, 429, 500, 502, 503, 504})


class OllamaError(Exception):
    """Fallo al consultar Ollama o al interpretar su respuesta JSON."""

    def __init__(self, message: str, *, retriable: bool = False) -> None:
        super().__init__(message)
        self.retriable = retriable


def verificar_ollama(
    *,
    base_url: str | None = None,
    model: str | None = None,
    timeout: float | None = None,
    connect_timeout: float | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Comprueba que Ollama responde y, si es posible, que el modelo existe.

    Returns:
        Dict con `ok`, `base_url`, `modelo`, `modelo_disponible` y opcional `error`.
    """
    url_base = (base_url or OLLAMA_BASE_URL).rstrip("/")
    modelo = model or OLLAMA_MODEL
    read_timeout = float(min(OLLAMA_TIMEOUT if timeout is None else timeout, 15))
    conn_timeout = float(
        OLLAMA_CONNECT_TIMEOUT if connect_timeout is None else connect_timeout
    )
    http_timeout = httpx.Timeout(
        connect=conn_timeout,
        read=read_timeout,
        write=read_timeout,
        pool=conn_timeout,
    )
    tags_url = f"{url_base}/api/tags"

    def _get(c: httpx.Client) -> httpx.Response:
        return c.get(tags_url, timeout=http_timeout)

    try:
        if client is not None:
            respuesta = _get(client)
        else:
            with httpx.Client(timeout=http_timeout) as propio:
                respuesta = _get(propio)
    except httpx.HTTPError as exc:
        return {
            "ok": False,
            "base_url": url_base,
            "modelo": modelo,
            "modelo_disponible": False,
            "error": f"No se pudo contactar Ollama: {exc}",
        }

    if respuesta.is_error:
        return {
            "ok": False,
            "base_url": url_base,
            "modelo": modelo,
            "modelo_disponible": False,
            "error": f"Ollama respondió {respuesta.status_code}",
        }

    try:
        data = respuesta.json()
    except json.JSONDecodeError:
        return {
            "ok": False,
            "base_url": url_base,
            "modelo": modelo,
            "modelo_disponible": False,
            "error": "Respuesta /api/tags no es JSON válido",
        }

    nombres = {
        str(m.get("name", "")).split(":", 1)[0]
        for m in (data.get("models") or [])
        if isinstance(m, dict)
    }
    modelo_base = modelo.split(":", 1)[0]
    disponible = modelo in {str(m.get("name", "")) for m in (data.get("models") or []) if isinstance(m, dict)} or (
        modelo_base in nombres
    )

    return {
        "ok": True,
        "base_url": url_base,
        "modelo": modelo,
        "modelo_disponible": disponible,
        "error": None
        if disponible
        else f"El modelo '{modelo}' no aparece en Ollama (¿está descargado?).",
    }


def consultar_ollama(
    prompt: str,
    texto: str,
    esquema: dict[str, Any],
    *,
    base_url: str | None = None,
    model: str | None = None,
    timeout: float | None = None,
    connect_timeout: float | None = None,
    retries: int | None = None,
    retry_backoff: float | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Consulta el chat de Ollama y devuelve un dict con los datos extraídos.

    Reintenta ante timeouts, errores de red y HTTP transitorios (5xx/429).
    """
    url_base = (base_url or OLLAMA_BASE_URL).rstrip("/")
    modelo = model or OLLAMA_MODEL
    read_timeout = float(OLLAMA_TIMEOUT if timeout is None else timeout)
    conn_timeout = float(
        OLLAMA_CONNECT_TIMEOUT if connect_timeout is None else connect_timeout
    )
    max_intentos = 1 + (OLLAMA_RETRIES if retries is None else max(0, retries))
    backoff = float(
        OLLAMA_RETRY_BACKOFF if retry_backoff is None else retry_backoff
    )

    payload = {
        "model": modelo,
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

    http_timeout = httpx.Timeout(
        connect=conn_timeout,
        read=read_timeout,
        write=read_timeout,
        pool=conn_timeout,
    )
    endpoint = f"{url_base}/api/chat"
    ultimo_error: OllamaError | None = None

    for intento in range(1, max_intentos + 1):
        try:
            if client is not None:
                respuesta = client.post(
                    endpoint, json=payload, timeout=http_timeout
                )
            else:
                with httpx.Client(timeout=http_timeout) as propio:
                    respuesta = propio.post(endpoint, json=payload)
            return _interpretar_respuesta(
                respuesta, modelo=modelo, endpoint=endpoint
            )
        except OllamaError as exc:
            ultimo_error = exc
            if not exc.retriable or intento >= max_intentos:
                raise
            _esperar_reintento(intento, backoff, exc)
        except httpx.TimeoutException as exc:
            ultimo_error = OllamaError(
                f"Timeout al consultar Ollama en {endpoint} "
                f"(connect={conn_timeout}s, read={read_timeout}s).",
                retriable=True,
            )
            if intento >= max_intentos:
                raise ultimo_error from exc
            _esperar_reintento(intento, backoff, ultimo_error)
        except httpx.RequestError as exc:
            ultimo_error = OllamaError(
                f"No se pudo conectar con Ollama en {url_base}. "
                f"Confirma que el servicio esté activo y que el modelo '{modelo}' exista. "
                f"Detalle: {exc}",
                retriable=True,
            )
            if intento >= max_intentos:
                raise ultimo_error from exc
            _esperar_reintento(intento, backoff, ultimo_error)

    assert ultimo_error is not None
    raise ultimo_error


def _esperar_reintento(intento: int, backoff: float, error: OllamaError) -> None:
    espera = backoff * intento
    logger.warning(
        "Reintento Ollama %s tras error reintentable: %s (espera %.1fs)",
        intento,
        error,
        espera,
    )
    time.sleep(espera)


def _interpretar_respuesta(
    respuesta: httpx.Response,
    *,
    modelo: str,
    endpoint: str,
) -> dict[str, Any]:
    if respuesta.is_error:
        detalle = _truncar_detalle(respuesta.text)
        logger.warning(
            "Ollama HTTP %s en %s (modelo=%s): %s",
            respuesta.status_code,
            endpoint,
            modelo,
            detalle,
        )
        raise OllamaError(
            f"Ollama respondió {respuesta.status_code}: {detalle}",
            retriable=respuesta.status_code in _HTTP_RETRIABLE,
        )

    try:
        data = respuesta.json()
    except json.JSONDecodeError as exc:
        raise OllamaError(
            f"Ollama devolvió un cuerpo no JSON: {_truncar_detalle(respuesta.text)}"
        ) from exc

    if not isinstance(data, dict):
        raise OllamaError("Ollama devolvió un JSON que no es un objeto.")

    mensaje = data.get("message")
    if not isinstance(mensaje, dict):
        raise OllamaError(
            "Respuesta de Ollama sin 'message' objeto. "
            f"Claves recibidas: {sorted(data.keys())}"
        )

    contenido = mensaje.get("content")
    if not isinstance(contenido, str) or not contenido.strip():
        raise OllamaError(
            "Ollama no devolvió message.content usable (vacío o ausente)."
        )

    return cargar_json(contenido)


def cargar_json(contenido: str) -> dict[str, Any]:
    """Parsea el contenido de la respuesta a un objeto JSON.

    Si el modelo envuelve el JSON en un bloque markdown (```), lo elimina
    antes de hacer `json.loads`.
    """
    texto = contenido.strip()
    if texto.startswith("```"):
        texto = texto.split("\n", 1)[-1]
        cierre = texto.rfind("```")
        if cierre != -1:
            texto = texto[:cierre]
        texto = texto.strip()
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise OllamaError(f"Ollama no devolvió JSON válido: {exc}") from exc
    if not isinstance(datos, dict):
        raise OllamaError("Ollama no devolvió un objeto JSON.")
    return datos


def _truncar_detalle(texto: str, max_len: int = _DETALLE_MAX) -> str:
    limpio = (texto or "").strip().replace("\r", " ").replace("\n", " ")
    if len(limpio) <= max_len:
        return limpio
    omitidos = len(limpio) - max_len
    return f"{limpio[:max_len]}… (+{omitidos} chars)"
