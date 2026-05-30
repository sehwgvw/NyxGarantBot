from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.db.models import GuarantorProfile


def main_menu(is_admin: bool = False, is_guarantor: bool = False, is_moderator: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🤝 Создать сделку", callback_data="menu:create_deal")],
        [InlineKeyboardButton(text="🏆 Выбрать топ гаранта", callback_data="menu:top_guarantors")],
        [InlineKeyboardButton(text="🛡 Каталог гарантов", callback_data="menu:guarantors")],
        [InlineKeyboardButton(text="⭐ Избранные гаранты", callback_data="menu:favorites")],
        [InlineKeyboardButton(text="📜 История сделок", callback_data="menu:history")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="menu:profile")],
        [InlineKeyboardButton(text="💬 Отзывы", callback_data="menu:reviews")],
        [InlineKeyboardButton(text="🆘 Поддержка", callback_data="menu:support")],
        [InlineKeyboardButton(text="👥 Команда проекта", callback_data="menu:staff")],
    ]
    if is_guarantor:
        rows.append([InlineKeyboardButton(text="🧾 Кабинет гаранта", callback_data="menu:guarantor_cabinet")])
    if is_moderator:
        rows.append([InlineKeyboardButton(text="🛎 Панель модератора", callback_data="menu:moderator")])
    if is_admin:
        rows.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="menu:admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:start")]])


def deal_methods() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Товар через гаранта", callback_data="deal_method:item")],
            [InlineKeyboardButton(text="₽ Оплата через гаранта", callback_data="deal_method:rub")],
            [InlineKeyboardButton(text="💎 TON", callback_data="deal_method:ton")],
            [InlineKeyboardButton(text="⭐ Stars", callback_data="deal_method:stars")],
        ]
    )


def deal_sides() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Я покупатель", callback_data="deal_side:buyer")],
            [InlineKeyboardButton(text="Я продавец", callback_data="deal_side:seller")],
        ]
    )


def guarantor_choice() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Автоподбор гаранта", callback_data="deal_guarantor:auto")],
            [InlineKeyboardButton(text="🛡 Выбрать вручную", callback_data="menu:guarantors_for_deal")],
        ]
    )


def guarantor_select(profiles: list[GuarantorProfile], *, prefix: str = "deal_guarantor_pick") -> InlineKeyboardMarkup:
    rows = []
    for profile in profiles[:20]:
        name = profile.display_username or f"ID {profile.user_id}"
        top = "🏆 " if profile.is_top else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{top}{name} · ⭐ {profile.rating:.2f} · {profile.successful_deals} сделок",
                    callback_data=f"{prefix}:{profile.user_id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:start")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_deal() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Создать сделку", callback_data="deal_confirm:create")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="deal_confirm:cancel")],
        ]
    )


def group_confirmation(deal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✅ Я вошёл в группу", callback_data=f"deal_group_confirm:{deal_id}")]]
    )


def join_deal(deal_id: int, invite_link: str | None = None) -> InlineKeyboardMarkup:
    rows = []
    if invite_link:
        rows.append([InlineKeyboardButton(text="🔗 Перейти в группу сделки", url=invite_link)])
    rows.append([InlineKeyboardButton(text="✅ Я участник сделки", callback_data=f"deal_join:{deal_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def success_confirmation(deal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить успешность сделки", callback_data=f"deal_success:{deal_id}")]]
    )


def report_actions(report_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👁 Принять в работу", callback_data=f"report_take:{report_id}")],
            [InlineKeyboardButton(text="✅ Проблема решена", callback_data=f"report_close:{report_id}")],
        ]
    )


def rating_keyboard(deal_id: int) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="⭐" * stars, callback_data=f"review:{deal_id}:{stars}")] for stars in range(1, 6)]
    rows.append([InlineKeyboardButton(text="Скрыть", callback_data=f"review_hide:{deal_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
