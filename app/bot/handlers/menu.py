from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.keyboards import back_menu
from app.bot.utils import send_banner
from app.config import get_settings
from app.db.models import UserRole
from app.db.session import SessionLocal
from app.services.repositories import get_user_by_tg, has_role, list_guarantors

router = Router()
settings = get_settings()

MENU_SCREENS = {
    "top_guarantors": ("top_guarantors", "<b>Лучшие гаранты сервиса</b>\n\nЗдесь отображаются гаранты с высоким рейтингом и числом успешных сделок."),
    "favorites": ("favorites", "<b>Избранные гаранты</b>\n\nВаш личный список сохранённых гарантов."),
    "profile": ("profile", "<b>Личный кабинет</b>\n\nПрофиль, история сделок, статусы и ограничения."),
    "history": ("history", "<b>История сделок</b>\n\nАрхив ваших активных, завершённых и отменённых сделок."),
    "reviews": ("reviews", "<b>Отзывы пользователей</b>\n\nРейтинги и текстовые отзывы по гарантам."),
    "support": ("support", "<b>Центр поддержки</b>\n\nНапишите /support описание проблемы или используйте команду внутри сделки."),
    "staff": ("staff", "<b>Команда проекта</b>\n\nГлавный админ, администраторы и модераторы отображаются ссылками по Telegram ID."),
    "guarantor_cabinet": ("guarantor_cabinet", "<b>Кабинет гаранта</b>\n\nПрофиль, комиссии, лимиты суммы сделки, рученцы, отзывы и статистика."),
    "moderator": ("moderator", "<b>Панель модератора</b>\n\nРепорты, обращения и служебная очередь."),
    "admin": ("admin", "<b>Панель администратора</b>\n\nНастройки бота, роли, группы, таймеры, лимиты, логи и блокировки."),
}


@router.callback_query(F.data == "menu:guarantors")
async def guarantors(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        profiles = await list_guarantors(session)
    if not profiles:
        text = "<b>Каталог гарантов</b>\n\nПока нет активных гарантов."
    else:
        rows = []
        for profile in profiles[:20]:
            min_amount = "—" if profile.min_deal_amount is None else f"{profile.min_deal_amount:g}₽"
            max_amount = "—" if profile.max_deal_amount is None else f"{profile.max_deal_amount:g}₽"
            rows.append(
                f"• ID {profile.user_id}: ⭐ {profile.rating:.2f}, сделок {profile.successful_deals}, лимиты {min_amount}–{max_amount}"
            )
        text = "<b>Каталог гарантов</b>\n\n" + "\n".join(rows)
    await send_banner(callback.bot, callback.message.chat.id, "guarantors", text, reply_markup=back_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("menu:"))
async def static_menu(callback: CallbackQuery) -> None:
    key = callback.data.split(":", 1)[1]
    if key not in MENU_SCREENS:
        await callback.answer("Раздел в разработке", show_alert=True)
        return
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, callback.from_user.id)
        if key == "admin" and not (user and await has_role(session, user.id, UserRole.ADMIN, settings, callback.from_user.id)):
            await callback.answer("Нет доступа", show_alert=True)
            return
        if key == "moderator" and not (user and await has_role(session, user.id, UserRole.MODERATOR)):
            await callback.answer("Нет доступа", show_alert=True)
            return
        if key == "guarantor_cabinet" and not (user and await has_role(session, user.id, UserRole.GUARANTOR)):
            await callback.answer("Нет доступа", show_alert=True)
            return
    banner_key, text = MENU_SCREENS[key]
    await send_banner(callback.bot, callback.message.chat.id, banner_key, text, reply_markup=back_menu())
    await callback.answer()
