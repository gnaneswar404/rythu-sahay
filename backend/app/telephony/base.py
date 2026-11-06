from abc import ABC, abstractmethod


class TelephonyProvider(ABC):
    """Provider adapter boundary for Exotel or a local mock."""

    @abstractmethod
    def incoming_call_response(self, call_id: str, caller_number: str | None, digits: str | None) -> dict:
        raise NotImplementedError
