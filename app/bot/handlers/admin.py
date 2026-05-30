from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from app.bot.utils import answer_banner
from app.config import get_settings
from app.db.models import AuditLog, GuarantorProfile, RoleAssignment, UserRole
from app.db.session import SessionLocal
from app.services.repositories import get_user_by_tg, has_role, log_event, set_setting

router = Router()
settings = get_settings()


async def require_admin(message: Message) -> bool:
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, message.from_user.id)
        return bool(user and await has_role(session, user.id, UserRole.ADMIN, settings, message.from_user.id))


@router.message(Command("set_setting"))
async def set_setting_command(message: Message) -> None:
    if not await require_admin(message):
        await answer_banner(message, "blocked", "Нет доступа.")
        return
    _, _, payload = message.text.partition(" ")
    key, _, value = payload.partition(" ")
    if not key or not value:
        await message.answer("Использование: /set_setting KEY VALUE")
        return
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, message.from_user.id)
        await set_setting(session, key, value, user.id if user else None)
        await log_event(session, "setting.updated", actor_id=user.id if user else None, payload={"key": key})
        await session.commit()
    await message.answer(f"Настройка <code>{key}</code> обновлена.")


@router.message(Command("set_groups"))
async def set_groups(message: Message) -> None:
    if not await require_admin(message):
        await answer_banner(message, "blocked", "Нет доступа.")
        return
    await message.answer(
        "Группы указываются главным админом прямо в боте:\n"
        "/set_setting MODERATION_GROUP_ID tg://chat?id=...\n"
        "/set_setting LOG_GROUP_ID tg://chat?id=..."
    )


@router.message(Command("add_guarantor"))
async def add_guarantor(message: Message) -> None:
    if not await require_admin(message):
        await answer_banner(message, "blocked", "Нет доступа.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /add_guarantor TELEGRAM_ID [min_amount] [max_amount]")
        return
    telegram_id = int(parts[1])
    min_amount = float(parts[2]) if len(parts) > 2 else None
    max_amount = float(parts[3]) if len(parts) > 3 else None
    async with SessionLocal() as session:
        admin_user = await get_user_by_tg(session, message.from_user.id)
        user = await get_user_by_tg(session, telegram_id)
        if user is None:
            await message.answer("Пользователь сначала должен нажать /start.")
            return
        if not await has_role(session, user.id, UserRole.GUARANTOR):
            session.add(RoleAssignment(user_id=user.id, role=UserRole.GUARANTOR, granted_by_id=admin_user.id if admin_user else None))
        profile = await session.scalar(select(GuarantorProfile).where(GuarantorProfile.user_id == user.id))
        if profile is None:
            session.add(
                GuarantorProfile(
                    user_id=user.id,
                    min_deal_amount=min_amount,
                    max_deal_amount=max_amount,
                    telegram_public_id=telegram_id,
                    display_username=user.username,
                    is_verified=True,
                )
            )
        else:
            profile.min_deal_amount = min_amount
            profile.max_deal_amount = max_amount
            profile.is_verified = True
        await log_event(session, "guarantor.upserted", actor_id=admin_user.id if admin_user else None, target_user_id=user.id)
        await session.commit()
    await message.answer("Гарант добавлен/обновлён.")


@router.message(Command("set_role"))
async def set_role(message: Message) -> None:
    if not await require_admin(message):
        await answer_banner(message, "blocked", "Нет доступа.")
        return
    parts = message.text.split()
    if len(parts) != 3 or parts[2] not in {"admin", "moderator", "guarantor"}:
        await message.answer("Использование: /set_role TELEGRAM_ID admin|moderator|guarantor")
        return
    async with SessionLocal() as session:
        admin_user = await get_user_by_tg(session, message.from_user.id)
        user = await get_user_by_tg(session, int(parts[1]))
        if user is None:
            await message.answer("Пользователь сначала должен нажать /start.")
            return
        role = UserRole(parts[2])
        if not await has_role(session, user.id, role):
            session.add(RoleAssignment(user_id=user.id, role=role, granted_by_id=admin_user.id if admin_user else None))
        await log_event(session, "role.granted", actor_id=admin_user.id if admin_user else None, target_user_id=user.id, payload={"role": role.value})
        await session.commit()
    await message.answer("Роль выдана.")


@router.message(Command("logs"))
async def logs(message: Message) -> None:
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, message.from_user.id)
        if not (user and await has_role(session, user.id, UserRole.MAIN_ADMIN, settings, message.from_user.id)):
            await answer_banner(message, "blocked", "Логи доступны только главному администратору.")
            return
        rows = list((await session.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(20))).all())
    text = "<b>Системные журналы</b>\n\n" + ("Лог пуст." if not rows else "\n".join(f"#{r.id} {r.event_type} · {r.severity} · deal={r.deal_id or '—'}" for r in rows))
    await answer_banner(message, "logs", text)
