from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import group_confirmation, main_menu
from app.bot.utils import answer_banner, send_banner
from app.config import get_settings
from app.db.models import Deal, UserRole
from app.db.session import SessionLocal
from app.services.repositories import (
    bind_counterparty,
    ensure_main_admin,
    get_user_by_tg,
    has_role,
    upsert_user,
)

router = Router()
settings = get_settings()


async def menu_flags(telegram_id: int) -> tuple[bool, bool, bool]:
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, telegram_id)
        if user is None:
            return False, False, False
        is_admin = await has_role(session, user.id, UserRole.ADMIN, settings, telegram_id)
        is_guarantor = await has_role(session, user.id, UserRole.GUARANTOR)
        is_moderator = await has_role(session, user.id, UserRole.MODERATOR)
        return is_admin, is_guarantor, is_moderator


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with SessionLocal() as session:
        user = await upsert_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            settings=settings,
        )
        await ensure_main_admin(session, user, settings)
    payload = ""
    if message.text:
        payload = message.text.partition(" ")[2].strip()
    if payload.startswith("join_"):
        deal_id = int(payload.removeprefix("join_"))
        async with SessionLocal() as session:
            deal = await session.get(Deal, deal_id)
            if deal is None:
                await message.answer("Сделка не найдена.")
                return
            try:
                await bind_counterparty(session, deal, user)
                await session.commit()
            except ValueError:
                await message.answer("Все стороны сделки уже назначены.")
                return
        await answer_banner(
            message,
            "waiting_user",
            "Вы подключены к сделке. Подтвердите вход после перехода в группу.",
            reply_markup=group_confirmation(deal_id),
        )
        return

    is_admin, is_guarantor, is_moderator = await menu_flags(message.from_user.id)
    await answer_banner(
        message,
        "start",
        "<b>NyxGarant</b> — безопасные сделки через гарантов.\n\nВыберите нужный раздел:",
        reply_markup=main_menu(is_admin=is_admin, is_guarantor=is_guarantor, is_moderator=is_moderator),
    )


@router.callback_query(F.data == "menu:start")
async def start_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    is_admin, is_guarantor, is_moderator = await menu_flags(callback.from_user.id)
    await send_banner(
        callback.bot,
        callback.message.chat.id,
        "start",
        "<b>NyxGarant</b> — безопасные сделки через гарантов.\n\nВыберите нужный раздел:",
        reply_markup=main_menu(is_admin=is_admin, is_guarantor=is_guarantor, is_moderator=is_moderator),
    )
    await callback.answer()
