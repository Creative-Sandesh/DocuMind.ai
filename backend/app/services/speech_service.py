"""Optional offline speech using locally configured Piper and Vosk models."""

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from functools import lru_cache
from pathlib import Path


MAX_AUDIO_BYTES = 4 * 1024 * 1024
MAX_AUDIO_SECONDS = 30
_MODEL_DIR = Path(__file__).resolve().parents[2] / ".models" / "speech"
_DEFAULT_PIPER_MODEL = _MODEL_DIR / "piper" / "en_US-lessac-medium.onnx"
_DEFAULT_VOSK_MODEL = _MODEL_DIR / "vosk" / "vosk-model-small-en-us-0.15"


class SpeechUnavailableError(Exception):
    pass


class InvalidAudioError(Exception):
    pass


def _piper_executable() -> str:
    local_binary = Path(sys.executable).with_name("piper.exe" if os.name == "nt" else "piper")
    return os.environ.get("PIPER_EXECUTABLE", str(local_binary) if local_binary.is_file() else "piper")


def _piper_model() -> str:
    return os.environ.get("PIPER_MODEL_PATH", str(_DEFAULT_PIPER_MODEL))


def _vosk_model() -> str:
    return os.environ.get("VOSK_MODEL_PATH", str(_DEFAULT_VOSK_MODEL))


def status() -> dict:
    piper_bin = _piper_executable()
    piper_model = _piper_model()
    vosk_model = _vosk_model()
    tts_ready = bool(piper_bin and shutil.which(piper_bin) and piper_model
                     and Path(piper_model).is_file()
                     and Path(piper_model + ".json").is_file())
    stt_ready = bool(vosk_model and Path(vosk_model, "am", "final.mdl").is_file()
                     and Path(vosk_model, "conf", "model.conf").is_file()
                     and importlib.util.find_spec("vosk"))
    return {"text_to_speech": tts_ready, "speech_to_text": stt_ready,
            "language": os.getenv("SPEECH_LANGUAGE", "en-US"), "offline_only": True,
            "message": "Install local Piper/Vosk models to enable unavailable speech features." if not (tts_ready and stt_ready)
            else "Local speech engines are ready."}


def synthesize(text: str) -> bytes:
    if not status()["text_to_speech"]:
        raise SpeechUnavailableError("Local text-to-speech is not configured")
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "speech.wav"
        try:
            result = subprocess.run(
                [_piper_executable(), "--model", _piper_model(),
                 "--output_file", str(output)], input=text, text=True,
                capture_output=True, timeout=45, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise SpeechUnavailableError("Local text-to-speech failed") from error
        if result.returncode != 0 or not output.is_file():
            raise SpeechUnavailableError("Local text-to-speech failed")
        audio = output.read_bytes()
        if not audio.startswith(b"RIFF") or len(audio) > 10 * 1024 * 1024:
            raise SpeechUnavailableError("Local text-to-speech returned invalid audio")
        return audio


@lru_cache(maxsize=2)
def _model(path: str):
    from vosk import Model
    return Model(path)


def transcribe(audio: bytes) -> dict:
    if not status()["speech_to_text"]:
        raise SpeechUnavailableError("Local speech-to-text is not configured")
    if len(audio) > MAX_AUDIO_BYTES:
        raise InvalidAudioError("Audio must be 4 MB or smaller")
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav:
            if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getcomptype() != "NONE":
                raise InvalidAudioError("Use mono 16-bit PCM WAV audio")
            if wav.getframerate() < 8000 or wav.getframerate() > 48000:
                raise InvalidAudioError("Unsupported WAV sample rate")
            if wav.getnframes() == 0 or wav.getnframes() / wav.getframerate() > MAX_AUDIO_SECONDS:
                raise InvalidAudioError("Audio must be between 0 and 30 seconds")
            from vosk import KaldiRecognizer
            recognizer = KaldiRecognizer(_model(_vosk_model()), wav.getframerate())
            segments = []
            while chunk := wav.readframes(4000):
                if recognizer.AcceptWaveform(chunk):
                    segments.append(json.loads(recognizer.Result()).get("text", ""))
            segments.append(json.loads(recognizer.FinalResult()).get("text", ""))
    except (wave.Error, EOFError) as error:
        raise InvalidAudioError("Invalid WAV audio") from error
    except InvalidAudioError:
        raise
    except Exception as error:
        raise SpeechUnavailableError("Local speech recognition failed") from error
    return {"text": " ".join(part for part in segments if part).strip(),
            "language": status()["language"], "pronunciation_scored": False,
            "note": "This is a rough transcription for repeat-after-me practice, not a phonetic assessment."}
