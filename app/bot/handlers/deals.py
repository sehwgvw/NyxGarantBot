import asyncio

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.banners import banner_path
from app.bot.keyboards import (
    confirm_deal,
    deal_methods,
    deal_sides,
    group_confirmation,
    guarantor_choice,
    guarantor_select,
    join_deal,
    rating_keyboard,
    success_confirmation,
)
from app.bot.states import CreateDeal, ReviewState
from app.bot.utils import send_banner
from app.config import get_settings
from app.db.models import Deal, DealStatus, User
from app.db.session import SessionLocal
from app.services.group_provider import build_group_provider
from app.services.repositories import (
    add_review,
    bind_counterparty,
    choose_auto_guarantor,
    confirm_group_entry,
    confirm_success,
    create_deal,
    get_user_by_tg,
    list_guarantors,
    log_event,
)

router = Router()
settings = get_settings()
group_provider = build_group_provider(settings)


@router.callback_query(F.data == "menu:create_deal")
async def start_create_deal(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CreateDeal.amount)
    await send_banner(callback.bot, callback.message.chat.id, "create_deal", "<b>Создание новой сделки</b>\n\nВведите сумму сделки числом. Например: <code>3000</code>")
    await callback.answer()


@router.message(CreateDeal.amount)
async def deal_amount(message: Message, state: FSMContext) -> None:
    try:
        amount = float(message.text.replace(",", "."))
    except (ValueError, AttributeError):
        await message.answer("Введите сумму числом, например: 3000")
        return
    if amount <= 0:
        await message.answer("Сумма должна быть больше нуля.")
        return
    await state.update_data(amount=amount, currency="RUB")
    await state.set_state(CreateDeal.subject)
    await message.answer("Опишите суть сделки и, если знаете, Telegram ID второй стороны: что передаётся, какие условия, за что отвечает гарант.")


@router.message(CreateDeal.subject)
async def deal_subject(message: Message, state: FSMContext) -> None:
    if not message.text or len(message.text.strip()) < 5:
        await message.answer("Описание слишком короткое. Укажите суть сделки подробнее.")
        return
    await state.update_data(subject=message.text.strip())
    await state.set_state(CreateDeal.method)
    await message.answer("Выберите метод сделки:", reply_markup=deal_methods())


@router.callback_query(CreateDeal.method, F.data.startswith("deal_method:"))
async def deal_method(callback: CallbackQuery, state: FSMContext) -> None:
    method_map = {
        "item": "Передача товара через гаранта",
        "rub": "Передача оплаты через гаранта в ₽",
        "ton": "Передача оплаты через гаранта в TON",
        "stars": "Передача оплаты через гаранта в Stars",
    }
    method = callback.data.split(":", 1)[1]
    await state.update_data(method=method_map[method])
    await state.set_state(CreateDeal.side)
    await callback.message.answer("Выберите вашу сторону в сделке:", reply_markup=deal_sides())
    await callback.answer()


@router.callback_query(CreateDeal.side, F.data.startswith("deal_side:"))
async def deal_side(callback: CallbackQuery, state: FSMContext) -> None:
    side = callback.data.split(":", 1)[1]
    await state.update_data(side=side)
    await state.set_state(CreateDeal.guarantor)
    await callback.message.answer("Выберите гаранта вручную или используйте автоподбор:", reply_markup=guarantor_choice())
    await callback.answer()


@router.callback_query(CreateDeal.guarantor, F.data == "menu:guarantors_for_deal")
async def deal_manual_guarantor(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    async with SessionLocal() as session:
        profiles = await list_guarantors(session, amount=float(data["amount"]))
    if not profiles:
        await callback.answer("Нет доступных гарантов под эту сумму сделки", show_alert=True)
        return
    await send_banner(callback.bot, callback.message.chat.id, "guarantors", "<b>Выберите гаранта для сделки</b>", reply_markup=guarantor_select(profiles))
    await callback.answer()


@router.callback_query(CreateDeal.guarantor, F.data.startswith("deal_guarantor_pick:"))
async def deal_manual_guarantor_selected(callback: CallbackQuery, state: FSMContext) -> None:
    guarantor_user_id = int(callback.data.rsplit(":", 1)[1])
    data = await state.get_data()
    async with SessionLocal() as session:
        guarantor = await session.get(User, guarantor_user_id)
    if guarantor is None:
        await callback.answer("Гарант не найден", show_alert=True)
        return
    await state.update_data(guarantor_id=guarantor.id, guarantor_tg=guarantor.telegram_id)
    await state.set_state(CreateDeal.confirm)
    await callback.message.answer(
        "<b>Проверьте сделку</b>\n"
        f"Сумма: <code>{data['amount']:g} ₽</code>\n"
        f"Метод: {data['method']}\n"
        f"Сторона: {data['side']}\n"
        f"Гарант: @{guarantor.username or guarantor.telegram_id}\n\n"
        "Создать сделку?",
        reply_markup=confirm_deal(),
    )
    await callback.answer()


@router.callback_query(CreateDeal.guarantor, F.data == "deal_guarantor:auto")
async def deal_auto_guarantor(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    async with SessionLocal() as session:
        guarantor = await choose_auto_guarantor(session, amount=float(data["amount"]))
    if guarantor is None:
        await callback.answer("Нет доступных гарантов под эту сумму сделки", show_alert=True)
        return
    await state.update_data(guarantor_id=guarantor.id, guarantor_tg=guarantor.telegram_id)
    await state.set_state(CreateDeal.confirm)
    await callback.message.answer(
        "<b>Проверьте сделку</b>\n"
        f"Сумма: <code>{data['amount']:g} ₽</code>\n"
        f"Метод: {data['method']}\n"
        f"Сторона: {data['side']}\n"
        f"Гарант: @{guarantor.username or guarantor.telegram_id}\n\n"
        "Создать сделку?",
        reply_markup=confirm_deal(),
    )
    await callback.answer()


@router.callback_query(CreateDeal.confirm, F.data == "deal_confirm:create")
async def deal_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    async with SessionLocal() as session:
        creator = await get_user_by_tg(session, callback.from_user.id)
        if creator is None:
            await callback.answer("Сначала нажмите /start", show_alert=True)
            return
        deal = await create_deal(session, creator, data, data.get("guarantor_id"))
        guarantor = await session.get(User, data.get("guarantor_id")) if data.get("guarantor_id") else None
        bot_user = await callback.bot.get_me()
        created_group = await group_provider.create_deal_group(
            callback.bot,
            deal,
            bot_user.username,
            participant_tg_ids=[creator.telegram_id, guarantor.telegram_id if guarantor else None],
        )
        deal.group_chat_id = created_group.chat_id
        deal.group_invite_link = created_group.invite_link
        await session.commit()
    await state.clear()
    await send_banner(
        callback.bot,
        callback.message.chat.id,
        "waiting_group",
        "<b>Сделка создана</b>\n\n"
        f"Группа сделки: {created_group.invite_link}\n"
        "Покупатель, продавец и гарант должны перейти в группу и подтвердить вход кнопкой ниже.",
        reply_markup=join_deal(deal.id, created_group.invite_link),
    )
    await callback.answer("Сделка создана")


@router.callback_query(CreateDeal.confirm, F.data == "deal_confirm:cancel")
async def deal_cancel_create(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await send_banner(callback.bot, callback.message.chat.id, "cancel", "Создание сделки отменено.")
    await callback.answer()


@router.callback_query(F.data.startswith("deal_join:"))
async def deal_join(callback: CallbackQuery) -> None:
    deal_id = int(callback.data.rsplit(":", 1)[1])
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, callback.from_user.id)
        deal = await session.get(Deal, deal_id)
        if user is None or deal is None:
            await callback.answer("Сделка не найдена", show_alert=True)
            return
        try:
            await bind_counterparty(session, deal, user)
            await session.commit()
        except ValueError:
            await callback.answer("Все стороны сделки уже назначены", show_alert=True)
            return
    await callback.message.answer("Вы привязаны к сделке. Теперь подтвердите вход в группу.", reply_markup=group_confirmation(deal_id))
    await callback.answer()


@router.callback_query(F.data.startswith("deal_group_confirm:"))
async def deal_group_confirm(callback: CallbackQuery) -> None:
    deal_id = int(callback.data.rsplit(":", 1)[1])
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, callback.from_user.id)
        deal = await session.get(Deal, deal_id)
        if user is None or deal is None:
            await callback.answer("Сделка не найдена", show_alert=True)
            return
        deal = await confirm_group_entry(session, deal, user)
        active = deal.status == DealStatus.ACTIVE
        if active:
            await log_event(session, "deal.activated", actor_id=user.id, deal_id=deal.id)
    if active:
        await group_provider.send_deal_commands(callback.bot, deal, str(banner_path("deal_commands").resolve()))
        await send_banner(callback.bot, callback.message.chat.id, "active_deal", "Все участники подтвердили вход. Сделка активна.", reply_markup=success_confirmation(deal_id))
    else:
        await callback.message.answer("Ваш вход подтверждён. Ожидаем остальных участников.")
    await callback.answer()


@router.callback_query(F.data.startswith("deal_success:"))
async def deal_success(callback: CallbackQuery) -> None:
    deal_id = int(callback.data.rsplit(":", 1)[1])
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, callback.from_user.id)
        deal = await session.get(Deal, deal_id)
        if user is None or deal is None:
            await callback.answer("Сделка не найдена", show_alert=True)
            return
        finished = await confirm_success(session, deal, user)
    if finished:
        await send_banner(
            callback.bot,
            callback.message.chat.id,
            "success",
            "Сделка успешно завершена. Гаранту добавлена +1 успешная сделка. Через 10 минут бот без звука попросит стороны оценить гаранта.",
        )
        if deal.guarantor_id:
            async with SessionLocal() as session:
                guarantor = await session.get(User, deal.guarantor_id)
            if guarantor:
                await callback.bot.send_message(guarantor.telegram_id, "Сделка проведена успешно. +1 успешная сделка добавлена в ваш профиль.", disable_notification=True)
        asyncio.create_task(send_review_request_later(callback.bot, callback.message.chat.id, deal_id))
    else:
        await callback.message.answer("Ваше подтверждение принято. Ожидаем вторую сторону.")
    await callback.answer()


@router.callback_query(F.data.startswith("review:"))
async def review(callback: CallbackQuery, state: FSMContext) -> None:
    _, deal_id, stars = callback.data.split(":")
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, callback.from_user.id)
        deal = await session.get(Deal, int(deal_id))
        if user is None or deal is None:
            await callback.answer("Сделка не найдена", show_alert=True)
            return
        await add_review(session, deal, user, int(stars))
        await session.commit()
    await state.set_state(ReviewState.text)
    await state.update_data(review_deal_id=int(deal_id), review_stars=int(stars))
    await callback.message.answer("Оценка сохранена. Можете отправить текстовый отзыв одним сообщением или нажать «Скрыть».")
    await callback.answer()


@router.callback_query(F.data.startswith("review_hide:"))
async def review_hide(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Оценка скрыта. Вы можете оставить отзыв позже.")
    await callback.answer()


@router.message(ReviewState.text)
async def review_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, message.from_user.id)
        deal = await session.get(Deal, int(data["review_deal_id"]))
        if user is None or deal is None:
            await message.answer("Сделка не найдена")
            await state.clear()
            return
        await add_review(session, deal, user, int(data["review_stars"]), message.text.strip() if message.text else None)
        await session.commit()
    await state.clear()
    await message.answer("Спасибо за текстовый отзыв!")


async def send_review_request_later(bot, chat_id: int, deal_id: int) -> None:
    await asyncio.sleep(600)
    await send_banner(
        bot,
        chat_id,
        "success",
        "Пожалуйста, оцените гаранта по завершённой сделке. Это не обязательно — можно скрыть.",
        reply_markup=rating_keyboard(deal_id),
    )
