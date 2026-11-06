from app.voice.base import SpeechProvider


class MockSpeechProvider(SpeechProvider):
    """Honest fallback: it does not claim to transcribe or create audio."""

    async def transcribe_telugu(self, audio: bytes, mime_type: str | None = None) -> str:
        raise RuntimeError("Mock speech provider cannot transcribe audio; use text or browser speech recognition.")

    async def synthesize_telugu(self, text: str) -> bytes:
        raise RuntimeError("Mock speech provider cannot synthesize audio; browser speech synthesis may be used for the demo.")
