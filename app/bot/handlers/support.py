from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import report_actions
from app.bot.utils import answer_banner
from app.config import get_settings
from app.db.models import Report, ReportStatus
from app.db.session import SessionLocal
from app.services.repositories import create_report, get_setting, get_user_by_tg, log_event

router = Router()
settings = get_settings()


def parse_chat_id(raw: str | None) -> int | None:
    if not raw:
        return None
    if raw.startswith("tg://chat?id="):
        return int(raw.rsplit("=", 1)[1])
    try:
        return int(raw)
    except ValueError:
        return None


@router.message(Command("support"))
async def support(message: Message) -> None:
    text = message.text.partition(" ")[2].strip()
    if not text:
        await answer_banner(message, "support", "Напишите обращение так: <code>/support описание проблемы</code>")
        return
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, message.from_user.id)
        if user is None:
            await message.answer("Сначала нажмите /start")
            return
        report = await create_report(session, user, text=text, kind="support")
        moderation_group = await get_setting(session, "MODERATION_GROUP_ID", settings.moderation_group_id)
        chat_id = parse_chat_id(moderation_group)
        if chat_id:
            sent = await message.bot.send_message(
                chat_id,
                "<b>Новый support/report</b>\n"
                f"ID: <code>{report.id}</code>\n"
                f"От: <a href='tg://user?id={message.from_user.id}'>{message.from_user.full_name}</a>\n"
                f"Текст: {text}",
                reply_markup=report_actions(report.id),
            )
            report.moderation_message_id = sent.message_id
            await session.commit()
    await answer_banner(message, "report", "Репорт принят. Модератор или администратор возьмёт его в работу.")


@router.callback_query(F.data.startswith("report_take:"))
async def report_take(callback: CallbackQuery) -> None:
    report_id = int(callback.data.rsplit(":", 1)[1])
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, callback.from_user.id)
        report = await session.get(Report, report_id)
        if user is None or report is None:
            await callback.answer("Репорт не найден", show_alert=True)
            return
        report.assignee_id = user.id
        report.status = ReportStatus.IN_PROGRESS
        await log_event(session, "report.taken", actor_id=user.id, payload={"report_id": report.id})
    await callback.message.edit_text(callback.message.html_text + "\n\n<b>В работе</b>")
    await callback.answer("Репорт принят в работу")


@router.callback_query(F.data.startswith("report_close:"))
async def report_close(callback: CallbackQuery) -> None:
    report_id = int(callback.data.rsplit(":", 1)[1])
    async with SessionLocal() as session:
        user = await get_user_by_tg(session, callback.from_user.id)
        report = await session.get(Report, report_id)
        if user is None or report is None:
            await callback.answer("Репорт не найден", show_alert=True)
            return
        report.status = ReportStatus.CLOSED
        report.assignee_id = user.id
        await log_event(session, "report.closed", actor_id=user.id, payload={"report_id": report.id})
    await callback.message.edit_text("репорт закрыт✅")
    await callback.answer("Репорт закрыт")
