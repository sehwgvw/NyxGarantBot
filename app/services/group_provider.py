from dataclasses import dataclass

from aiogram import Bot
from aiogram.types import FSInputFile

from app.config import Settings
from app.db.models import Deal
from app.userbot.client import UserbotClient


@dataclass
class CreatedGroup:
    chat_id: int | None
    invite_link: str


class GroupProvider:
    async def create_deal_group(self, bot: Bot, deal: Deal, bot_username: str) -> CreatedGroup:
        raise NotImplementedError

    async def send_deal_commands(self, bot: Bot, deal: Deal, banner_path: str) -> None:
        if deal.group_chat_id:
            await bot.send_photo(
                deal.group_chat_id,
                photo=FSInputFile(banner_path),
                caption=(
                    "<b>Команды управления сделкой</b>\n\n"
                    "/dispute — открыть спор по сделке\n"
                    "/scam — сообщить о скаме гаранта\n"
                    "/change_metod — запросить смену метода сделки\n"
                    "/support описание — обратиться в поддержку\n"
                    "/add_ruch @username — добавить рученца (только гарант)\n"
                    "/get_link — получить ссылку на группу (только гарант)"
                ),
            )


class BotApiFallbackGroupProvider(GroupProvider):
    async def create_deal_group(self, bot: Bot, deal: Deal, bot_username: str) -> CreatedGroup:
        # Telegram Bot API cannot create groups. This fallback creates a deep link so the
        # second side can join the deal flow, while the real group is created by userbot
        # when USE_USERBOT=true.
        return CreatedGroup(chat_id=None, invite_link=f"https://t.me/{bot_username}?start=join_{deal.id}")


class UserbotGroupProvider(GroupProvider):
    def __init__(self, settings: Settings) -> None:
        self.client = UserbotClient(settings)

    async def create_deal_group(self, bot: Bot, deal: Deal, bot_username: str) -> CreatedGroup:
        title = f"{deal.amount:g} {deal.currency}"
        created = await self.client.create_deal_group(title=title, user_ids=[deal.buyer_id, deal.seller_id, deal.guarantor_id])
        if created is None:
            return CreatedGroup(chat_id=None, invite_link=f"https://t.me/{bot_username}?start=join_{deal.id}")
        return CreatedGroup(chat_id=created.chat_id, invite_link=created.invite_link)


def build_group_provider(settings: Settings) -> GroupProvider:
    return UserbotGroupProvider(settings) if settings.use_userbot else BotApiFallbackGroupProvider()
