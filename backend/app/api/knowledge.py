from fastapi import APIRouter

from app.knowledge.repository import get_verified_guidance, list_guidance

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("")
def get_knowledge(query: str | None = None):
    if query:
        return {"record": get_verified_guidance(query), "safety_notice": "Demo records are not expert-approved treatment instructions."}
    return {"records": list_guidance(), "safety_notice": "All records currently bundled for demonstration are clearly marked demo-only."}
