from abc import ABC, abstractmethod


class SpeechProvider(ABC):
    """Replaceable Telugu speech provider contract; keys never leave the backend."""

    @abstractmethod
    async def transcribe_telugu(self, audio: bytes, mime_type: str | None = None) -> str:
        raise NotImplementedError

    @abstractmethod
    async def synthesize_telugu(self, text: str) -> bytes:
        raise NotImplementedError
