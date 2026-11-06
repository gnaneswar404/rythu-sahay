from app.config import get_settings
from app.telephony.base import TelephonyProvider
from app.telephony.mock import MockTelephonyProvider


def get_telephony_provider() -> TelephonyProvider:
    settings = get_settings()
    if settings.mock_telephony_enabled or not all([settings.exotel_api_key, settings.exotel_api_token, settings.exotel_sid]):
        return MockTelephonyProvider()
    raise RuntimeError("Configure and verify an Exotel adapter before enabling production telephony.")
