from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config import get_settings
from sqlalchemy import select

from app.db.models import GuarantorProfile, RoleAssignment, UserRole
from app.db.session import SessionLocal
from app.services.repositories import get_user_by_tg, has_role, set_setting

router = Router()
settings = get_settings()


async def require_admin(message: Message) -> bool:
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, message.from_user.id)
        return bool(user and await has_role(session, user.id, UserRole.ADMIN, settings, message.from_user.id))


@router.message(Command("set_setting"))
async def set_setting_command(message: Message) -> None:
    if not await require_admin(message):
        await message.answer("Нет доступа.")
        return
    _, _, payload = message.text.partition(" ")
    key, _, value = payload.partition(" ")
    if not key or not value:
        await message.answer("Использование: /set_setting KEY VALUE")
        return
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, message.from_user.id)
        await set_setting(session, key, value, user.id if user else None)
    await message.answer(f"Настройка <code>{key}</code> обновлена.")


@router.message(Command("set_groups"))
async def set_groups(message: Message) -> None:
    if not await require_admin(message):
        await message.answer("Нет доступа.")
        return
    await message.answer(
        "Группы указываются главным админом прямо в боте:\n"
        "/set_setting MODERATION_GROUP_ID tg://chat?id=...\n"
        "/set_setting LOG_GROUP_ID tg://chat?id=..."
    )


@router.message(Command("add_guarantor"))
async def add_guarantor(message: Message) -> None:
    if not await require_admin(message):
        await message.answer("Нет доступа.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /add_guarantor TELEGRAM_ID [min_amount] [max_amount]")
        return
    telegram_id = int(parts[1])
    min_amount = float(parts[2]) if len(parts) > 2 else None
    max_amount = float(parts[3]) if len(parts) > 3 else None
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, telegram_id)
        if user is None:
            await message.answer("Пользователь сначала должен нажать /start.")
            return
        if not await has_role(session, user.id, UserRole.GUARANTOR):
            session.add(RoleAssignment(user_id=user.id, role=UserRole.GUARANTOR))
        profile = await session.scalar(select(GuarantorProfile).where(GuarantorProfile.user_id == user.id))
        if profile is None:
            session.add(GuarantorProfile(user_id=user.id, min_deal_amount=min_amount, max_deal_amount=max_amount, telegram_public_id=telegram_id))
        else:
            profile.min_deal_amount = min_amount
            profile.max_deal_amount = max_amount
        await session.commit()
    await message.answer("Гарант добавлен/обновлён.")
