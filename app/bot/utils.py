from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile, Message

from app.banners import banner_path


async def answer_banner(message: Message, key: str, caption: str, reply_markup=None) -> None:
    path = banner_path(key)
    if path.exists():
        await message.answer_photo(FSInputFile(path), caption=caption, reply_markup=reply_markup)
    else:
        await message.answer(caption, reply_markup=reply_markup)


async def send_banner(bot: Bot, chat_id: int, key: str, caption: str, reply_markup=None) -> None:
    path = banner_path(key)
    if Path(path).exists():
        await bot.send_photo(chat_id, FSInputFile(path), caption=caption, reply_markup=reply_markup)
    else:
        await bot.send_message(chat_id, caption, reply_markup=reply_markup)
