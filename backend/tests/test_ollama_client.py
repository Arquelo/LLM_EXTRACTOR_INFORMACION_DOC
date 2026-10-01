"""Tests del cliente Ollama."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from llm.ollama_client import (
    OllamaError,
    _truncar_detalle,
    cargar_json,
    consultar_ollama,
    verificar_ollama,
)


# --- cargar_json -------------------------------------------------------------


def test_cargar_json_objeto_plano() -> None:
    assert cargar_json('{"rfc": "XAXX010101000"}') == {"rfc": "XAXX010101000"}


def test_cargar_json_con_markdown() -> None:
    bruto = '```json\n{"a": 1}\n```'
    assert cargar_json(bruto) == {"a": 1}


def test_cargar_json_invalido() -> None:
    with pytest.raises(OllamaError, match="JSON válido"):
        cargar_json("no-es-json")


def test_cargar_json_no_objeto() -> None:
    with pytest.raises(OllamaError, match="objeto JSON"):
        cargar_json("[1, 2, 3]")


# --- truncar detalle ---------------------------------------------------------


def test_truncar_detalle_corto() -> None:
    assert _truncar_detalle("hola") == "hola"


def test_truncar_detalle_largo() -> None:
    texto = "x" * 600
    cortado = _truncar_detalle(texto, max_len=100)
    assert cortado.startswith("x" * 100)
    assert "+500 chars" in cortado
    assert len(cortado) < len(texto)


# --- consultar_ollama (httpx mock) -------------------------------------------


def _respuesta(
    *,
    status: int = 200,
    body: dict[str, Any] | str | None = None,
    text: str | None = None,
) -> httpx.Response:
    if text is not None:
        content = text.encode("utf-8")
    elif isinstance(body, dict):
        content = json.dumps(body).encode("utf-8")
    else:
        content = b"{}"
    return httpx.Response(
        status_code=status,
        content=content,
        request=httpx.Request("POST", "http://test/api/chat"),
    )


def test_consultar_ollama_exito_con_cliente() -> None:
    cliente = MagicMock(spec=httpx.Client)
    cliente.post.return_value = _respuesta(
        body={"message": {"content": '{"rfc": "XAXX010101000"}'}}
    )

    datos = consultar_ollama(
        "prompt",
        "texto doc",
        {"type": "object"},
        base_url="http://ollama.test",
        model="demo",
        client=cliente,
    )

    assert datos == {"rfc": "XAXX010101000"}
    cliente.post.assert_called_once()
    args, kwargs = cliente.post.call_args
    assert args[0] == "http://ollama.test/api/chat"
    assert kwargs["json"]["model"] == "demo"


def test_consultar_ollama_http_error_trunca_detalle() -> None:
    cliente = MagicMock(spec=httpx.Client)
    cliente.post.return_value = _respuesta(status=500, text="E" * 800)

    with pytest.raises(OllamaError, match=r"Ollama respondió 500:.*\+\d+ chars"):
        consultar_ollama("p", "t", {}, client=cliente, base_url="http://x", retries=0)


def test_consultar_ollama_sin_message() -> None:
    cliente = MagicMock(spec=httpx.Client)
    cliente.post.return_value = _respuesta(body={"done": True})

    with pytest.raises(OllamaError, match="message"):
        consultar_ollama("p", "t", {}, client=cliente, retries=0)


def test_consultar_ollama_content_vacio() -> None:
    cliente = MagicMock(spec=httpx.Client)
    cliente.post.return_value = _respuesta(body={"message": {"content": "  "}})

    with pytest.raises(OllamaError, match="message.content"):
        consultar_ollama("p", "t", {}, client=cliente, retries=0)


def test_consultar_ollama_error_de_red() -> None:
    cliente = MagicMock(spec=httpx.Client)
    cliente.post.side_effect = httpx.ConnectError(
        "connection refused",
        request=httpx.Request("POST", "http://x/api/chat"),
    )

    with pytest.raises(OllamaError, match="No se pudo conectar"):
        consultar_ollama(
            "p", "t", {}, client=cliente, base_url="http://x", retries=0
        )


def test_consultar_ollama_timeout() -> None:
    cliente = MagicMock(spec=httpx.Client)
    cliente.post.side_effect = httpx.ReadTimeout(
        "timed out",
        request=httpx.Request("POST", "http://x/api/chat"),
    )

    with pytest.raises(OllamaError, match="Timeout"):
        consultar_ollama(
            "p",
            "t",
            {},
            client=cliente,
            base_url="http://x",
            timeout=1,
            connect_timeout=0.5,
            retries=0,
        )


def test_consultar_ollama_reintenta_y_recupera() -> None:
    cliente = MagicMock(spec=httpx.Client)
    cliente.post.side_effect = [
        _respuesta(status=503, text="busy"),
        _respuesta(body={"message": {"content": '{"ok": true}'}}),
    ]

    with patch("llm.ollama_client.time.sleep"):
        datos = consultar_ollama(
            "p", "t", {}, client=cliente, retries=2, retry_backoff=0.01
        )

    assert datos == {"ok": True}
    assert cliente.post.call_count == 2


def test_consultar_ollama_reintenta_json_invalido() -> None:
    cliente = MagicMock(spec=httpx.Client)
    cliente.post.side_effect = [
        _respuesta(body={"message": {"content": "no-es-json"}}),
        _respuesta(body={"message": {"content": '{"ok": true}'}}),
    ]

    with patch("llm.ollama_client.time.sleep"):
        datos = consultar_ollama(
            "p", "t", {}, client=cliente, retries=2, retry_backoff=0.01
        )

    assert datos == {"ok": True}
    assert cliente.post.call_count == 2


def test_verificar_ollama_ok() -> None:
    cliente = MagicMock(spec=httpx.Client)
    cliente.get.return_value = _respuesta(
        body={"models": [{"name": "llama3.2:latest"}]}
    )

    info = verificar_ollama(client=cliente, model="llama3.2")
    assert info["ok"] is True
    assert info["modelo_disponible"] is True


def test_verificar_ollama_modelo_ausente() -> None:
    cliente = MagicMock(spec=httpx.Client)
    cliente.get.return_value = _respuesta(body={"models": [{"name": "otro"}]})

    info = verificar_ollama(client=cliente, model="llama3.2")
    assert info["ok"] is True
    assert info["modelo_disponible"] is False
    assert info["error"]


def test_consultar_ollama_inyecta_url_y_modelo() -> None:
    """Sin client real: mockea httpx.Client como context manager."""
    respuesta = _respuesta(
        body={"message": {"content": '{"ok": true}'}}
    )
    mock_client = MagicMock()
    mock_client.post.return_value = respuesta
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False

    with patch("llm.ollama_client.httpx.Client", return_value=mock_client):
        datos = consultar_ollama(
            "sys",
            "doc",
            {"type": "object"},
            base_url="http://custom:11434/",
            model="mistral",
            timeout=12,
            connect_timeout=3,
        )

    assert datos == {"ok": True}
    args, kwargs = mock_client.post.call_args
    assert args[0] == "http://custom:11434/api/chat"
    assert kwargs["json"]["model"] == "mistral"
