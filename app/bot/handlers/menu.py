from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select

from app.bot.keyboards import back_menu
from app.bot.utils import send_banner
from app.config import get_settings
from app.db.models import GuarantorProfile, Review, User, UserRole
from app.db.session import SessionLocal
from app.services.repositories import (
    favorite_guarantors,
    get_user_by_tg,
    has_role,
    list_guarantors,
    list_staff,
    user_deals,
)

router = Router()
settings = get_settings()

MENU_SCREENS = {
    "support": ("support", "<b>Центр поддержки</b>\n\nНапишите /support описание проблемы или используйте команду внутри сделки."),
    "moderator": ("moderator", "<b>Панель модератора</b>\n\nРепорты, обращения и служебная очередь."),
    "admin": ("admin", "<b>Панель администратора</b>\n\nНастройки бота, роли, группы, таймеры, лимиты, логи и блокировки.\n\nКоманды: /set_setting, /set_groups, /add_guarantor, /set_role, /logs"),
}


def format_guarantor(profile: GuarantorProfile) -> str:
    min_amount = "—" if profile.min_deal_amount is None else f"{profile.min_deal_amount:g}₽"
    max_amount = "—" if profile.max_deal_amount is None else f"{profile.max_deal_amount:g}₽"
    statuses = []
    if profile.is_verified:
        statuses.append("Проверен")
    if profile.is_top:
        statuses.append("ТОП")
    statuses.append("online" if profile.is_online else "offline")
    return (
        f"• <b>{profile.display_username or 'Гарант #' + str(profile.user_id)}</b>\n"
        f"  ⭐ {profile.rating:.2f} · ✅ {profile.successful_deals} · ❌ {profile.cancelled_deals} · ⚠️ {profile.complaints_count}\n"
        f"  Комиссия: {profile.commission_percent:g}% · лимиты {min_amount}–{max_amount}\n"
        f"  Статусы: {', '.join(statuses)}"
    )


@router.callback_query(F.data == "menu:guarantors")
async def guarantors(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        profiles = await list_guarantors(session)
    text = "<b>Каталог гарантов</b>\n\n" + ("Пока нет активных гарантов." if not profiles else "\n\n".join(format_guarantor(p) for p in profiles[:20]))
    await send_banner(callback.bot, callback.message.chat.id, "guarantors", text, reply_markup=back_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:top_guarantors")
async def top_guarantors(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        profiles = await list_guarantors(session, only_top=True)
    text = "<b>Лучшие гаранты сервиса</b>\n\n" + ("ТОП-гаранты пока не назначены." if not profiles else "\n\n".join(format_guarantor(p) for p in profiles[:10]))
    await send_banner(callback.bot, callback.message.chat.id, "top_guarantors", text, reply_markup=back_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:favorites")
async def favorites(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, callback.from_user.id)
        profiles = await favorite_guarantors(session, user.id) if user else []
    text = "<b>Избранные гаранты</b>\n\n" + ("Вы пока не добавили гарантов в избранное." if not profiles else "\n\n".join(format_guarantor(p) for p in profiles))
    await send_banner(callback.bot, callback.message.chat.id, "favorites", text, reply_markup=back_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:profile")
async def profile(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, callback.from_user.id)
        deals = await user_deals(session, user.id, 5) if user else []
    if not user:
        text = "Сначала нажмите /start."
    else:
        text = (
            "<b>Личный кабинет</b>\n\n"
            f"ID: <code>{user.telegram_id}</code>\n"
            f"Username: @{user.username or '—'}\n"
            f"Блокировка: {'да' if user.is_blocked else 'нет'}\n"
            f"Отмен без оплаты: {user.unpaid_cancel_count}\n"
            f"Последние сделки: {', '.join('#' + str(d.id) for d in deals) if deals else 'нет'}"
        )
    await send_banner(callback.bot, callback.message.chat.id, "profile", text, reply_markup=back_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:history")
async def history(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, callback.from_user.id)
        deals = await user_deals(session, user.id) if user else []
    rows = [f"• #{d.id}: {d.status.value}, {d.amount:g} {d.currency}, {d.method}" for d in deals]
    text = "<b>История сделок</b>\n\n" + ("История пока пустая." if not rows else "\n".join(rows))
    await send_banner(callback.bot, callback.message.chat.id, "history", text, reply_markup=back_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:reviews")
async def reviews(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        rows = list((await session.execute(select(Review, User).join(User, User.id == Review.author_id).order_by(Review.created_at.desc()).limit(10))).all())
    if not rows:
        text = "<b>Отзывы пользователей</b>\n\nОтзывов пока нет."
    else:
        text = "<b>Отзывы пользователей</b>\n\n" + "\n\n".join(f"⭐ {r.stars}/5 от <a href='tg://user?id={u.telegram_id}'>{u.full_name or u.telegram_id}</a>\n{r.text or 'Без текста'}" for r, u in rows)
    await send_banner(callback.bot, callback.message.chat.id, "reviews", text, reply_markup=back_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:staff")
async def staff(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        rows = await list_staff(session, settings)
    text = "<b>Команда проекта</b>\n\n" + ("Сотрудники пока не назначены." if not rows else "\n".join(f"• {title}: <a href='tg://user?id={user.telegram_id}'>{user.full_name or user.telegram_id}</a>" for title, user in rows))
    await send_banner(callback.bot, callback.message.chat.id, "staff", text, reply_markup=back_menu())
    await callback.answer()


@router.callback_query(F.data == "menu:guarantor_cabinet")
async def guarantor_cabinet(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, callback.from_user.id)
        allowed = bool(user and await has_role(session, user.id, UserRole.GUARANTOR))
        profile = await session.scalar(select(GuarantorProfile).where(GuarantorProfile.user_id == user.id)) if allowed and user else None
    if not allowed:
        await callback.answer("Нет доступа", show_alert=True)
        return
    text = "<b>Кабинет гаранта</b>\n\n" + (format_guarantor(profile) if profile else "Профиль гаранта ещё не заполнен администратором.")
    await send_banner(callback.bot, callback.message.chat.id, "guarantor_cabinet", text, reply_markup=back_menu())
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
    banner_key, text = MENU_SCREENS[key]
    await send_banner(callback.bot, callback.message.chat.id, banner_key, text, reply_markup=back_menu())
    await callback.answer()
