from dataclasses import dataclass

from app.config import Settings


@dataclass
class UserbotCreatedGroup:
    chat_id: int
    invite_link: str


class UserbotClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def create_deal_group(self, title: str, user_ids: list[int | None]) -> UserbotCreatedGroup | None:
        if not self.settings.api_id or not self.settings.api_hash:
            return None
        from telethon import TelegramClient
        from telethon.functions.channels import CreateChannelRequest, ExportInviteRequest, InviteToChannelRequest

        async with TelegramClient(str(self.settings.session_path), self.settings.api_id, self.settings.api_hash) as client:
            result = await client(CreateChannelRequest(title=title, about="Сделочная группа NyxGarant", megagroup=True))
            channel = result.chats[0]
            valid_user_ids = [user_id for user_id in user_ids if user_id]
            if valid_user_ids:
                try:
                    await client(InviteToChannelRequest(channel=channel, users=valid_user_ids))
                except Exception:
                    # Some users cannot be added by ID/privacy settings; the invite link is still issued.
                    pass
            invite = await client(ExportInviteRequest(channel))
            return UserbotCreatedGroup(chat_id=channel.id, invite_link=invite.link)
