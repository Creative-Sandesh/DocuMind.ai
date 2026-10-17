"""Ollama chat client shared by plain chat and document-grounded RAG."""

import os

import httpx


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_URL = f"{OLLAMA_BASE_URL}/api/chat"
MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
MAX_CONVERSATION_MESSAGES = 20

DEFAULT_SYSTEM_PROMPT = """You are an education AI tutor.
Explain concepts clearly, use examples when useful, and use recent conversation
to understand follow-up questions."""


class OllamaResponseError(Exception):
    """Ollama returned a successful HTTP response without usable answer text."""


async def get_ollama_status() -> dict[str, str]:
    """Check that the local Ollama server and configured model are available."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
    except (httpx.RequestError, httpx.HTTPStatusError, ValueError, AttributeError):
        return {"status": "unavailable", "model": MODEL_NAME}

    installed = {
        model.get("name")
        for model in models
        if isinstance(model, dict)
    } if isinstance(models, list) else set()
    return {
        "status": "ready" if MODEL_NAME in installed else "model_missing",
        "model": MODEL_NAME,
    }


def prepare_ollama_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep system instructions outside the bounded conversation history."""
    system_messages = [message for message in messages if message["role"] == "system"]
    conversation = [
        message for message in messages if message["role"] != "system"
    ][-MAX_CONVERSATION_MESSAGES:]
    if not system_messages:
        system_messages = [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT}
        ]
    return [*system_messages, *conversation]


async def generate_response(messages: list[dict[str, str]]) -> str:
    payload = {
        "model": MODEL_NAME,
        "messages": prepare_ollama_messages(messages),
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError as error:
            raise OllamaResponseError("Ollama returned invalid JSON") from error

    message = data.get("message") if isinstance(data, dict) else None
    answer = message.get("content") if isinstance(message, dict) else None
    if not isinstance(answer, str) or not answer.strip():
        raise OllamaResponseError("Ollama returned no answer text")
    return answer.strip()
