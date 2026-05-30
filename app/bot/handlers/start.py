from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import main_menu
from app.bot.utils import answer_banner, send_banner
from app.config import get_settings
from app.db.models import UserRole
from app.db.session import SessionLocal
from app.services.repositories import ensure_main_admin, get_user_by_tg, has_role, upsert_user

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
