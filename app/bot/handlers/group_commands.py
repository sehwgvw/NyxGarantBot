from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.handlers.support import parse_chat_id
from app.bot.keyboards import report_actions
from app.bot.utils import answer_banner
from app.config import get_settings
from app.db.models import Deal, DealStatus, RuchMember
from app.db.session import SessionLocal
from app.services.repositories import create_report, get_setting, get_user_by_tg, log_event

router = Router()
settings = get_settings()


async def find_deal_by_chat(session, chat_id: int) -> Deal | None:
    from sqlalchemy import select

    return await session.scalar(select(Deal).where(Deal.group_chat_id == chat_id))


@router.message(Command("dispute"))
async def dispute(message: Message) -> None:
    async with SessionLocal() as session:
        deal = await find_deal_by_chat(session, message.chat.id)
        user = await get_user_by_tg(session, message.from_user.id)
        if not deal or not user:
            await message.answer("Команда доступна только внутри группы сделки.")
            return
        deal.status = DealStatus.DISPUTE
        report = await create_report(session, user, text="Открыт арбитраж сделки", kind="dispute", deal_id=deal.id)
        await log_event(session, "deal.dispute.opened", actor_id=user.id, deal_id=deal.id, payload={"report_id": report.id})
        moderation_group = await get_setting(session, "MODERATION_GROUP_ID", settings.moderation_group_id)
        chat_id = parse_chat_id(moderation_group)
        if chat_id:
            await message.bot.send_message(chat_id, f"<b>Спор по сделке</b>\nСделка: {deal.id}", reply_markup=report_actions(report.id))
        await session.commit()
    await answer_banner(message, "dispute", "Арбитраж сделки открыт. Модераторы получат данные по спору.")


@router.message(Command("scam"))
async def scam(message: Message) -> None:
    text = message.text.partition(" ")[2].strip() or "Жалоба на скам гаранта"
    async with SessionLocal() as session:
        deal = await find_deal_by_chat(session, message.chat.id)
        user = await get_user_by_tg(session, message.from_user.id)
        if not deal or not user:
            await message.answer("Команда доступна только внутри группы сделки.")
            return
        report = await create_report(session, user, text=text, kind="scam", deal_id=deal.id)
        moderation_group = await get_setting(session, "MODERATION_GROUP_ID", settings.moderation_group_id)
        chat_id = parse_chat_id(moderation_group)
        if chat_id:
            await message.bot.send_message(chat_id, f"<b>SCAM report</b>\nСделка: {deal.id}\nТекст: {text}", reply_markup=report_actions(report.id))
    await answer_banner(message, "scam", "Жалоба принята на проверку.")


@router.message(Command("change_metod"))
async def change_method(message: Message) -> None:
    await message.answer("Запрос на изменение метода сделки зафиксирован. Метод может быть изменён по правилам администратора.")


@router.message(Command("add_ruch"))
async def add_ruch(message: Message) -> None:
    target = message.text.partition(" ")[2].strip()
    if not target:
        await answer_banner(message, "add_ruch", "Использование: <code>/add_ruch @username</code>")
        return
    async with SessionLocal() as session:
        deal = await find_deal_by_chat(session, message.chat.id)
        user = await get_user_by_tg(session, message.from_user.id)
        if not deal or not user or deal.guarantor_id != user.id:
            await message.answer("Добавлять рученца может только гарант этой сделки.")
            return
        session.add(RuchMember(deal_id=deal.id, user_id=user.id, added_by_id=user.id))
        await log_event(session, "deal.ruch.added", actor_id=user.id, deal_id=deal.id, payload={"target": target})
        await session.commit()
    await answer_banner(message, "add_ruch", f"Рученец {target} добавлен в сделку. Добавьте его в группу, если он ещё не внутри.")


@router.message(Command("get_link"))
async def get_link(message: Message) -> None:
    async with SessionLocal() as session:
        deal = await find_deal_by_chat(session, message.chat.id)
        user = await get_user_by_tg(session, message.from_user.id)
        if not deal or not user or deal.guarantor_id != user.id:
            await message.answer("Получить ссылку может только гарант этой сделки.")
            return
    await message.answer(f"Ссылка на группу сделки: {deal.group_invite_link or 'не создана'}")
