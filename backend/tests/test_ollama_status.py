import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.services.ollama_service import MODEL_NAME, generate_response, get_ollama_status


class OllamaStatusTests(unittest.IsolatedAsyncioTestCase):
    async def test_structured_generation_sends_schema_and_temperature(self):
        response = MagicMock()
        response.json.return_value = {"message": {"content": '{"answer":"ok"}'}}
        client = MagicMock()
        client.post = AsyncMock(return_value=response)
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=None)
        schema = {"type": "object", "properties": {"answer": {"type": "string"}}}
        with patch("app.services.ollama_service.httpx.AsyncClient", return_value=context):
            answer = await generate_response(
                [{"role": "user", "content": "Hello"}],
                response_format=schema, temperature=0,
            )
        self.assertEqual(answer, '{"answer":"ok"}')
        payload = client.post.call_args.kwargs["json"]
        self.assertEqual(payload["format"], schema)
        self.assertEqual(payload["options"], {"temperature": 0})

    async def test_reports_installed_model(self):
        response = MagicMock()
        response.json.return_value = {"models": [{"name": MODEL_NAME}]}
        client = MagicMock()
        client.get = AsyncMock(return_value=response)
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=None)
        with patch("app.services.ollama_service.httpx.AsyncClient", return_value=context):
            self.assertEqual(
                (await get_ollama_status())["status"], "ready"
            )

    async def test_reports_missing_model_and_offline_server(self):
        response = MagicMock()
        response.json.return_value = {"models": []}
        client = MagicMock()
        client.get = AsyncMock(return_value=response)
        context = MagicMock()
        context.__aenter__ = AsyncMock(return_value=client)
        context.__aexit__ = AsyncMock(return_value=None)
        with patch("app.services.ollama_service.httpx.AsyncClient", return_value=context):
            self.assertEqual(
                (await get_ollama_status())["status"], "model_missing"
            )

        client.get = AsyncMock(side_effect=httpx.ConnectError("offline"))
        with patch("app.services.ollama_service.httpx.AsyncClient", return_value=context):
            self.assertEqual(
                (await get_ollama_status())["status"], "unavailable"
            )


if __name__ == "__main__":
    unittest.main()
