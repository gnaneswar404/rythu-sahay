from app.telephony.base import TelephonyProvider


class MockTelephonyProvider(TelephonyProvider):
    def incoming_call_response(self, call_id: str, caller_number: str | None, digits: str | None) -> dict:
        return {
            "mode": "mock",
            "call_id": call_id,
            "message_te": "ఇది రీతు సహాయ డెమో కాల్. నల్గొండ జిల్లా పత్తి పంట సమస్యను చెప్పండి.",
            "dtmf_options": {"1": "తెలుగులో కొనసాగించండి", "9": "కాల్ ముగించండి"},
            "notice": "No real telephone number or provider delivery is claimed in mock mode.",
        }
