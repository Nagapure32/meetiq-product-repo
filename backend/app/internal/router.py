from fastapi import APIRouter

from app.internal.routes import bot

router = APIRouter()
router.include_router(bot.router, prefix="/bot", tags=["internal-bot"])

