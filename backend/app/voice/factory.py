from app.config import get_settings
from app.voice.base import SpeechProvider
from app.voice.mock import MockSpeechProvider


def get_speech_provider() -> SpeechProvider:
    """Sarvam implementation is deliberately not activated until the current API contract is verified with credentials."""
    settings = get_settings()
    if settings.mock_voice_enabled or not settings.sarvam_api_key:
        return MockSpeechProvider()
    raise RuntimeError("A production Sarvam adapter must be configured after API-contract verification.")
