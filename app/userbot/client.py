from dataclasses import dataclass

from app.config import Settings


@dataclass
class UserbotCreatedGroup:
    chat_id: int
    invite_link: str


class UserbotClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def create_deal_group(
        self,
        title: str,
        user_ids: list[int | None],
        bot_username: str | None = None,
        guarantor_tg_id: int | None = None,
    ) -> UserbotCreatedGroup | None:
        if not self.settings.api_id or not self.settings.api_hash:
            return None
        from telethon import TelegramClient
        from telethon.functions.channels import (
            CreateChannelRequest,
            EditAdminRequest,
            ExportInviteRequest,
            InviteToChannelRequest,
        )
        from telethon.types import ChatAdminRights

        async with TelegramClient(
            str(self.settings.session_path),
            self.settings.api_id,
            self.settings.api_hash,
        ) as client:
            result = await client(
                CreateChannelRequest(
                    title=title,
                    about="Сделочная группа NyxGarant",
                    megagroup=True,
                )
            )
            channel = result.chats[0]
            invite_targets: list[int | str] = [user_id for user_id in user_ids if user_id]
            if bot_username:
                invite_targets.append(bot_username)
            if invite_targets:
                try:
                    await client(InviteToChannelRequest(channel=channel, users=invite_targets))
                except Exception:
                    # Privacy settings can prevent direct invites; invite link remains usable.
                    pass
            admin_rights = ChatAdminRights(
                change_info=True,
                post_messages=True,
                edit_messages=True,
                delete_messages=True,
                ban_users=True,
                invite_users=True,
                pin_messages=True,
                add_admins=True,
                anonymous=False,
                manage_call=True,
            )
            for target in (guarantor_tg_id, bot_username):
                if target:
                    try:
                        await client(
                            EditAdminRequest(
                                channel=channel,
                                user_id=target,
                                admin_rights=admin_rights,
                                rank="NyxGarant",
                            )
                        )
                    except Exception:
                        pass
            invite = await client(ExportInviteRequest(channel))
            return UserbotCreatedGroup(chat_id=int(f"-100{channel.id}"), invite_link=invite.link)
