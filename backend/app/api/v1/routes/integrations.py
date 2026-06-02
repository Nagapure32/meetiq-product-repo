from fastapi import APIRouter

from app.services.integrations import get_bot_health, list_bot_events

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/bot-health")
async def bot_health() -> dict:
    return await get_bot_health()


@router.get("/bot-events")
async def bot_events() -> dict[str, list]:
    return {"items": await list_bot_events()}

