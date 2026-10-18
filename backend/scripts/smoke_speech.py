"""Exercise authenticated offline speech endpoints with a temporary student."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.student import router
from app.services import memory_service


PHRASE = "The quick brown fox jumps over the lazy dog."


def main() -> None:
    with TemporaryDirectory() as directory, patch.object(
        memory_service, "DB_PATH", Path(directory) / "speech-smoke.sqlite3"
    ):
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            account = client.post("/api/student/register", json={
                "email": "speech-smoke@example.invalid",
                "password": "speech-smoke-password",
                "display_name": "Speech Smoke",
            })
            account.raise_for_status()
            headers = {"Authorization": f"Bearer {account.json()['token']}"}

            status = client.get("/api/student/speech/status", headers=headers)
            status.raise_for_status()
            if not all((status.json()["offline_only"], status.json()["text_to_speech"],
                        status.json()["speech_to_text"])):
                raise RuntimeError(f"Local speech engines are unavailable: {status.json()}")

            audio = client.post("/api/student/speech/synthesize", headers=headers,
                                json={"text": PHRASE})
            audio.raise_for_status()
            if audio.headers.get("content-type") != "audio/wav" or not audio.content.startswith(b"RIFF"):
                raise RuntimeError("Piper did not return WAV audio")

            transcript = client.post("/api/student/speech/transcribe", headers=headers,
                                     files={"audio": ("sample.wav", audio.content, "audio/wav")})
            transcript.raise_for_status()
            heard = transcript.json()["text"]
            if "quick brown fox" not in heard.lower():
                raise RuntimeError(f"Vosk did not recognize the sample phrase: {heard!r}")
            print(f"offline speech OK: {len(audio.content)} WAV bytes; recognized: {heard}")


if __name__ == "__main__":
    main()
