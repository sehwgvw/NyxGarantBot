from __future__ import annotations

from html import escape
from math import ceil

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.keyboards import (
    back_menu,
    deal_card_keyboard,
    deals_list_keyboard,
    guarantor_card_keyboard,
    guarantors_list_keyboard,
    profile_keyboard,
    reviews_list_keyboard,
)
from app.bot.utils import send_banner
from app.config import get_settings
from app.db.models import Deal, GuarantorProfile, User, UserRole
from app.db.session import SessionLocal
from app.services.repositories import (
    count_user_deals,
    count_user_reviews,
    get_deal_for_user,
    get_guarantor_card,
    get_user_by_tg,
    has_role,
    is_favorite_guarantor,
    list_deals_for_user,
    list_favorite_guarantors,
    list_guarantors_page,
    list_reviews_page,
    set_favorite_guarantor,
)

router = Router()
settings = get_settings()

GUARANTORS_PER_PAGE = 5
DEALS_PER_PAGE = 6
REVIEWS_PER_PAGE = 5

MENU_SCREENS = {
    "support": (
        "support",
        "<b>Центр поддержки</b>\n\n"
        "Напишите /support описание проблемы или используйте команду внутри сделки.",
    ),
    "staff": (
        "staff",
        "<b>Команда проекта</b>\n\n"
        "Главный админ, администраторы и модераторы отображаются ссылками по Telegram ID.",
    ),
    "moderator": (
        "moderator",
        "<b>Панель модератора</b>\n\nРепорты, обращения и служебная очередь.",
    ),
    "admin": (
        "admin",
        "<b>Панель администратора</b>\n\n"
        "Настройки бота, роли, группы, таймеры, лимиты, логи и блокировки.",
    ),
}


def _money(value: float | None, currency: str = "₽") -> str:
    if value is None:
        return "—"
    return f"{value:g} {currency}"


def _user_label(user: User | None) -> str:
    if user is None:
        return "—"
    name = user.username or user.full_name or str(user.telegram_id)
    if user.username:
        return f"@{escape(name)}"
    return f"<a href='tg://user?id={user.telegram_id}'>{escape(name)}</a>"


def _profile_name(profile: GuarantorProfile, user: User) -> str:
    name = profile.display_username or user.username or user.full_name or str(user.telegram_id)
    return (
        f"@{escape(name)}"
        if not name.startswith("@") and (profile.display_username or user.username)
        else escape(name)
    )


def _status(value) -> str:
    return getattr(value, "value", str(value))


def _page_count(total: int, per_page: int) -> int:
    return max(1, ceil(total / per_page))


def _clamp_page(page: int, total: int, per_page: int) -> int:
    return max(0, min(page, _page_count(total, per_page) - 1))


def _guarantor_line(profile: GuarantorProfile, user: User, is_favorite: bool = False) -> str:
    badge = "⭐ " if is_favorite else ""
    top = " 🏆" if profile.is_top else ""
    verified = " ✅" if profile.is_verified else ""
    return (
        f"{badge}<b>{_profile_name(profile, user)}</b>{top}{verified}\n"
        f"   ⭐ {profile.rating:.2f} · успешных: {profile.successful_deals}"
        f" · комиссия: {profile.commission_percent:g}%\n"
        f"   лимиты: {_money(profile.min_deal_amount)} – {_money(profile.max_deal_amount)}"
    )


def _guarantor_card_text(profile: GuarantorProfile, user: User, is_favorite: bool) -> str:
    description = escape(profile.description or "Описание пока не заполнено.")
    reviews = profile.review_link or "—"
    pledge_links = profile.pledge_links or []
    pledges = "\n".join(f"• {escape(link)}" for link in pledge_links) if pledge_links else "—"
    favorite = "добавлен в избранное" if is_favorite else "не в избранном"
    public_id = profile.telegram_public_id or user.telegram_id
    return (
        f"<b>Карточка гаранта {_profile_name(profile, user)}</b>\n\n"
        f"Telegram ID: <code>{public_id}</code>\n"
        f"Статус: {'🟢 онлайн' if profile.is_online else '⚪️ офлайн'}"
        f" · {'✅ верифицирован' if profile.is_verified else 'без верификации'}\n"
        f"Избранное: {favorite}\n\n"
        f"<b>Условия</b>\n"
        f"Мин. сумма: <code>{_money(profile.min_deal_amount)}</code>\n"
        f"Макс. сумма: <code>{_money(profile.max_deal_amount)}</code>\n"
        f"Комиссия: <code>{profile.commission_percent:g}%</code>\n\n"
        f"<b>Статистика</b>\n"
        f"Рейтинг: ⭐ <code>{profile.rating:.2f}</code>\n"
        f"Успешных сделок: <code>{profile.successful_deals}</code>\n"
        f"Отменённых сделок: <code>{profile.cancelled_deals}</code>\n"
        f"Жалоб: <code>{profile.complaints_count}</code>\n"
        f"Отзывов: <code>{profile.reviews_count}</code>\n\n"
        f"<b>Отзывы</b>\n{escape(reviews)}\n\n"
        f"<b>Рученцы / залоги</b>\n{pledges}\n\n"
        f"<b>Описание</b>\n{description}"
    )


def _deal_line(deal: Deal) -> str:
    return (
        f"<b>#{deal.id}</b> · {_status(deal.status)}"
        f" · {_money(deal.amount, deal.currency)} · {escape(deal.method)}"
    )


def _deal_card_text(
    deal: Deal,
    creator: User | None,
    buyer: User | None,
    seller: User | None,
    guarantor: User | None,
) -> str:
    group = deal.group_invite_link or (
        f"tg://chat?id={deal.group_chat_id}" if deal.group_chat_id else "—"
    )
    return (
        f"<b>Сделка #{deal.id}</b>\n\n"
        f"Статус: <code>{_status(deal.status)}</code>\n"
        f"Сумма: <code>{_money(deal.amount, deal.currency)}</code>\n"
        f"Метод: {escape(deal.method)}\n"
        f"Предмет: {escape(deal.subject)}\n\n"
        f"<b>Участники</b>\n"
        f"Создатель: {_user_label(creator)}\n"
        f"Покупатель: {_user_label(buyer)}\n"
        f"Продавец: {_user_label(seller)}\n"
        f"Гарант: {_user_label(guarantor)}\n\n"
        f"Группа: {escape(group)}"
    )


async def _render_guarantors(callback: CallbackQuery, mode: str, page: int = 0) -> None:
    titles = {
        "catalog": ("guarantors", "Каталог гарантов", "Все активные гаранты сервиса."),
        "top": (
            "top_guarantors",
            "Топ гарантов",
            "Гаранты с отметкой ТОП, высоким рейтингом и успешными сделками.",
        ),
        "favorites": ("favorites", "Избранные гаранты", "Ваш личный список сохранённых гарантов."),
    }
    banner_key, title, subtitle = titles[mode]
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, callback.from_user.id)
        if mode == "favorites" and user is None:
            await callback.answer("Сначала нажмите /start", show_alert=True)
            return
        if mode == "favorites":
            rows, total = await list_favorite_guarantors(
                session, user.id, page, GUARANTORS_PER_PAGE
            )  # type: ignore[union-attr]
        else:
            rows, total = await list_guarantors_page(
                session,
                page,
                GUARANTORS_PER_PAGE,
                only_top=mode == "top",
                favorite_user_id=user.id if user else None,
            )
    page = _clamp_page(page, total, GUARANTORS_PER_PAGE)
    lines = [_guarantor_line(profile, guarantor, favorite) for profile, guarantor, favorite in rows]
    text = f"<b>{title}</b>\n\n{subtitle}\n\n"
    text += "\n\n".join(lines) if lines else "Пока здесь пусто."
    text += f"\n\nСтраница <code>{page + 1}/{_page_count(total, GUARANTORS_PER_PAGE)}</code>"
    await send_banner(
        callback.bot,
        callback.message.chat.id,
        banner_key,
        text,
        reply_markup=guarantors_list_keyboard(rows, mode, page, total, GUARANTORS_PER_PAGE),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:guarantors")
async def guarantors(callback: CallbackQuery) -> None:
    await _render_guarantors(callback, "catalog", 0)


@router.callback_query(F.data == "menu:top_guarantors")
async def top_guarantors(callback: CallbackQuery) -> None:
    await _render_guarantors(callback, "top", 0)


@router.callback_query(F.data == "menu:favorites")
async def favorite_guarantors(callback: CallbackQuery) -> None:
    await _render_guarantors(callback, "favorites", 0)


@router.callback_query(F.data.startswith("guarantors:list:"))
async def guarantors_page(callback: CallbackQuery) -> None:
    _, _, mode, page = callback.data.split(":")
    await _render_guarantors(callback, mode, int(page))


@router.callback_query(F.data.startswith("guarantor:card:"))
async def guarantor_card(callback: CallbackQuery) -> None:
    _, _, guarantor_id, origin, page = callback.data.split(":")
    async with SessionLocal() as session:
        viewer = await get_user_by_tg(session, callback.from_user.id)
        card = await get_guarantor_card(session, int(guarantor_id))
        if card is None:
            await callback.answer("Гарант не найден", show_alert=True)
            return
        profile, user = card
        favorite = bool(
            viewer and await is_favorite_guarantor(session, viewer.id, int(guarantor_id))
        )
    await send_banner(
        callback.bot,
        callback.message.chat.id,
        "guarantor_card",
        _guarantor_card_text(profile, user, favorite),
        reply_markup=guarantor_card_keyboard(int(guarantor_id), favorite, origin, int(page)),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("favorite:toggle:"))
async def toggle_favorite(callback: CallbackQuery) -> None:
    _, _, guarantor_id, origin, page = callback.data.split(":")
    async with SessionLocal() as session:
        viewer = await get_user_by_tg(session, callback.from_user.id)
        if viewer is None:
            await callback.answer("Сначала нажмите /start", show_alert=True)
            return
        card = await get_guarantor_card(session, int(guarantor_id))
        if card is None:
            await callback.answer("Гарант не найден", show_alert=True)
            return
        current = await is_favorite_guarantor(session, viewer.id, int(guarantor_id))
        await set_favorite_guarantor(session, viewer.id, int(guarantor_id), not current)
    await callback.answer("Добавлено в избранное" if not current else "Удалено из избранного")
    async with SessionLocal() as session:
        viewer = await get_user_by_tg(session, callback.from_user.id)
        card = await get_guarantor_card(session, int(guarantor_id))
        if card is None:
            await callback.answer("Гарант не найден", show_alert=True)
            return
        profile, user = card
        favorite = bool(
            viewer and await is_favorite_guarantor(session, viewer.id, int(guarantor_id))
        )
    await send_banner(
        callback.bot,
        callback.message.chat.id,
        "guarantor_card",
        _guarantor_card_text(profile, user, favorite),
        reply_markup=guarantor_card_keyboard(int(guarantor_id), favorite, origin, int(page)),
    )


@router.callback_query(F.data == "menu:history")
async def history(callback: CallbackQuery) -> None:
    await _render_deals(callback, 0)


@router.callback_query(F.data.startswith("deals:list:"))
async def deals_page(callback: CallbackQuery) -> None:
    page = int(callback.data.rsplit(":", 1)[1])
    await _render_deals(callback, page)


async def _render_deals(callback: CallbackQuery, page: int) -> None:
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, callback.from_user.id)
        if user is None:
            await callback.answer("Сначала нажмите /start", show_alert=True)
            return
        deals, total = await list_deals_for_user(session, user.id, page, DEALS_PER_PAGE)
    page = _clamp_page(page, total, DEALS_PER_PAGE)
    text = (
        "<b>История сделок</b>\n\nАктивные, завершённые и отменённые сделки, где вы участвуете.\n\n"
    )
    text += "\n".join(_deal_line(deal) for deal in deals) if deals else "Сделок пока нет."
    text += f"\n\nСтраница <code>{page + 1}/{_page_count(total, DEALS_PER_PAGE)}</code>"
    await send_banner(
        callback.bot,
        callback.message.chat.id,
        "history",
        text,
        reply_markup=deals_list_keyboard(deals, page, total, DEALS_PER_PAGE),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("deal:card:"))
async def deal_card(callback: CallbackQuery) -> None:
    _, _, deal_id, page = callback.data.split(":")
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, callback.from_user.id)
        if user is None:
            await callback.answer("Сначала нажмите /start", show_alert=True)
            return
        card = await get_deal_for_user(session, int(deal_id), user.id)
        if card is None:
            await callback.answer("Сделка не найдена", show_alert=True)
            return
        deal, creator, buyer, seller, guarantor = card
    await send_banner(
        callback.bot,
        callback.message.chat.id,
        "deal_card",
        _deal_card_text(deal, creator, buyer, seller, guarantor),
        reply_markup=deal_card_keyboard(int(page)),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:profile")
async def profile(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, callback.from_user.id)
        if user is None:
            await callback.answer("Сначала нажмите /start", show_alert=True)
            return
        total_deals = await count_user_deals(session, user.id)
        total_reviews = await count_user_reviews(session, user.id)
        is_admin = await has_role(session, user.id, UserRole.ADMIN, settings, callback.from_user.id)
        is_guarantor = await has_role(session, user.id, UserRole.GUARANTOR)
        is_moderator = await has_role(session, user.id, UserRole.MODERATOR)
    roles = ["пользователь"]
    if is_guarantor:
        roles.append("гарант")
    if is_moderator:
        roles.append("модератор")
    if is_admin:
        roles.append("администратор")
    text = (
        "<b>Личный кабинет</b>\n\n"
        f"ID профиля: <code>{user.id}</code>\n"
        f"Telegram ID: <code>{user.telegram_id}</code>\n"
        f"Имя: {escape(user.full_name or '—')}\n"
        f"Username: @{escape(user.username) if user.username else '—'}\n"
        f"Роли: {', '.join(roles)}\n"
        f"Блокировка: {'да' if user.is_blocked else 'нет'}\n"
        f"Неоплаченных отмен: <code>{user.unpaid_cancel_count}</code>\n\n"
        f"Сделок в истории: <code>{total_deals}</code>\n"
        f"Оставлено отзывов: <code>{total_reviews}</code>"
    )
    await send_banner(
        callback.bot,
        callback.message.chat.id,
        "profile",
        text,
        reply_markup=profile_keyboard(is_guarantor),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:reviews")
async def reviews(callback: CallbackQuery) -> None:
    await _render_reviews(callback, 0)


@router.callback_query(F.data.startswith("reviews:list:"))
async def reviews_page(callback: CallbackQuery) -> None:
    await _render_reviews(callback, int(callback.data.rsplit(":", 1)[1]))


async def _render_reviews(callback: CallbackQuery, page: int) -> None:
    async with SessionLocal() as session:
        rows, total = await list_reviews_page(session, page, REVIEWS_PER_PAGE)
    page = _clamp_page(page, total, REVIEWS_PER_PAGE)
    lines = []
    for review, guarantor, author in rows:
        text = escape(review.text or "Без текста")
        if len(text) > 120:
            text = text[:117] + "..."
        lines.append(
            f"⭐ <code>{review.stars}/5</code> для {_user_label(guarantor)}"
            f" от {_user_label(author)}\n{text}"
        )
    body = "\n\n".join(lines) if lines else "Пока нет отзывов."
    text = (
        f"<b>Отзывы пользователей</b>\n\n{body}\n\n"
        f"Страница <code>{page + 1}/{_page_count(total, REVIEWS_PER_PAGE)}</code>"
    )
    await send_banner(
        callback.bot,
        callback.message.chat.id,
        "reviews",
        text,
        reply_markup=reviews_list_keyboard(page, total, REVIEWS_PER_PAGE),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:guarantor_cabinet")
async def guarantor_cabinet(callback: CallbackQuery) -> None:
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, callback.from_user.id)
        if user is None or not await has_role(session, user.id, UserRole.GUARANTOR):
            await callback.answer("Нет доступа", show_alert=True)
            return
        card = await get_guarantor_card(session, user.id)
        deals_total = await count_user_deals(session, user.id)
        if card is None:
            text = (
                "<b>Кабинет гаранта</b>\n\n"
                "Профиль гаранта ещё не создан. Обратитесь к администратору."
            )
        else:
            profile_obj, profile_user = card
            favorite = await is_favorite_guarantor(session, user.id, user.id)
            text = _guarantor_card_text(profile_obj, profile_user, favorite)
            text = (
                "<b>Кабинет гаранта</b>\n\n"
                + text
                + f"\n\nСделок с вашим участием: <code>{deals_total}</code>"
            )
    await send_banner(
        callback.bot, callback.message.chat.id, "guarantor_cabinet", text, reply_markup=back_menu()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("menu:"))
async def static_menu(callback: CallbackQuery) -> None:
    key = callback.data.split(":", 1)[1]
    if key not in MENU_SCREENS:
        await callback.answer("Раздел в разработке", show_alert=True)
        return
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, callback.from_user.id)
        if key == "admin" and not (
            user
            and await has_role(session, user.id, UserRole.ADMIN, settings, callback.from_user.id)
        ):
            await callback.answer("Нет доступа", show_alert=True)
            return
        if key == "moderator" and not (
            user and await has_role(session, user.id, UserRole.MODERATOR)
        ):
            await callback.answer("Нет доступа", show_alert=True)
            return
    banner_key, text = MENU_SCREENS[key]
    await send_banner(
        callback.bot, callback.message.chat.id, banner_key, text, reply_markup=back_menu()
    )
    await callback.answer()
