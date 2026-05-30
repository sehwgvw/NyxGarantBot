from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Banner:
    key: str
    file: str
    title: str
    used_in: str
    prompt: str

    @property
    def path(self) -> Path:
        return Path("assets/banners") / self.file


BANNERS: dict[str, Banner] = {
    "start": Banner("start", "start_banner.png", "Безопасные сделки через гарантов", "/start, главное меню", "2D minimalistic premium banner; dark background; neon blue and purple glow; shield of security, handshake, digital trust symbols, refined Telegram escrow atmosphere; high detail, clean composition, elegant centered title."),
    "create_deal": Banner("create_deal", "create_deal_banner.png", "Создание новой сделки", "Экран создания сделки", "2D minimalistic premium banner; dark futuristic interface, buyer and seller initiating a deal, floating UI elements, subtle money/TON/stars icons, sleek composition, clean title, high quality."),
    "active_deal": Banner("active_deal", "active_deal_banner.png", "Сделка активна", "Карточка активной сделки", "2D minimalistic premium banner; buyer, seller and guarantor connected by digital lines; transparent glowing network, premium dark UI, strong hierarchy, crisp title."),
    "success": Banner("success", "success_banner.png", "Сделка успешно завершена", "Завершение сделки, просьба оценить гаранта", "2D minimalistic premium banner; success checkmark, subtle confetti, trophy, polished glow, minimal but celebratory, clean centered text."),
    "cancel": Banner("cancel", "cancel_banner.png", "Сделка отменена", "Экран отмены сделки", "2D minimalistic premium banner; red cancel indicator, broken contract motif, restrained warning style, premium dark look, minimal clutter."),
    "dispute": Banner("dispute", "dispute_banner.png", "Арбитраж сделки", "/dispute, спорные ситуации", "2D minimalistic premium banner; justice scales, dispute between two parties, modern arbitration UI, blue-purple with warning accents, elegant and serious."),
    "scam": Banner("scam", "scam_banner.png", "Проверка жалобы", "/scam, жалоба на скам", "2D minimalistic premium banner; shield, alert symbol, investigation mood, refined modern report screen, high quality, minimal explanatory text only."),
    "support": Banner("support", "support_banner.png", "Центр поддержки", "/support, служба помощи", "2D minimalistic premium banner; support operator headset, service tickets, clean help-desk dashboard, dark premium tone."),
    "guarantors": Banner("guarantors", "guarantors_banner.png", "Каталог гарантов", "Раздел всех гарантов", "2D minimalistic premium banner; multiple guarantor cards, ratings, filters, premium directory feel, dark background, neon accents."),
    "guarantor_profile": Banner("guarantor_profile", "guarantor_profile_banner.png", "Профиль гаранта", "Карточка конкретного гаранта", "2D minimalistic premium banner; large guarantor profile card, rating stars, statistics, trust badge, elegant composition."),
    "top_guarantors": Banner("top_guarantors", "top_guarantors_banner.png", "Лучшие гаранты сервиса", "Раздел ТОП гарантов", "2D minimalistic premium banner; podium, gold silver bronze emphasis, premium leaderboard look, dark + neon palette."),
    "favorites": Banner("favorites", "favorites_banner.png", "Избранные гаранты", "Избранные гаранты пользователя", "2D minimalistic premium banner; heart/favorite symbols, saved guarantor cards, elegant personal collection layout."),
    "profile": Banner("profile", "profile_banner.png", "Личный кабинет", "Профиль пользователя", "2D minimalistic premium banner; user avatar card, stats dashboard, personal account feel, premium clean layout."),
    "history": Banner("history", "history_banner.png", "История сделок", "История сделок", "2D minimalistic premium banner; archive, document timeline, transaction history UI, neat and readable."),
    "reviews": Banner("reviews", "reviews_banner.png", "Отзывы пользователей", "Раздел отзывов гаранта", "2D minimalistic premium banner; stars, comments, social proof cards, trustworthy community feel."),
    "guarantor_cabinet": Banner("guarantor_cabinet", "guarantor_cabinet_banner.png", "Кабинет гаранта", "Личный кабинет гаранта", "2D minimalistic premium banner; guarantor dashboard, statistics, deal counts, commission widgets, premium control panel."),
    "add_ruch": Banner("add_ruch", "add_ruch_banner.png", "Добавление рученца", "/add_ruch, добавление рученца в сделку", "2D minimalistic premium banner; guarantor plus assistant, team-work motif, clean admin action view."),
    "staff": Banner("staff", "staff_banner.png", "Команда проекта", "Список сотрудников бота", "2D minimalistic premium banner; role hierarchy, chief admin, admins, moderators, guarantors, clean organizational look."),
    "moderator": Banner("moderator", "moderator_banner.png", "Панель модератора", "Кабинет модератора", "2D minimalistic premium banner; shield, moderation tickets, service queue, professional control interface."),
    "admin": Banner("admin", "admin_banner.png", "Панель администратора", "Кабинет администратора", "2D minimalistic premium banner; admin dashboard, charts, settings, logs, strong control panel look."),
    "logs": Banner("logs", "logs_banner.png", "Системные журналы", "Раздел логов", "2D minimalistic premium banner; terminal logs, event monitoring, structured system view, serious technical feel."),
    "blocked": Banner("blocked", "blocked_banner.png", "Доступ ограничен", "Блокировка пользователя", "2D minimalistic premium banner; lock, red shield, access denied mood, minimalist warning style."),
    "waiting_user": Banner("waiting_user", "waiting_user_banner.png", "Ожидание подключения участника", "Ожидание регистрации /start", "2D minimalistic premium banner; clock, user icon, waiting state, clean progress mood."),
    "waiting_group": Banner("waiting_group", "waiting_group_banner.png", "Ожидание подтверждения входа", "Статус после создания группы сделки", "2D minimalistic premium banner; Telegram group, three avatars, waiting for confirmations, elegant status screen."),
    "deal_commands": Banner("deal_commands", "deal_commands_banner.png", "Команды управления сделкой", "Сообщение с командами внутри группы сделки", "2D minimalistic premium banner; command terminal, command list interface, clean instructions screen."),
    "report": Banner("report", "report_banner.png", "Репорт принят", "Support/report экран", "2D minimalistic premium banner; incident accepted, report processing, service notification layout."),
}


def banner_path(key: str) -> Path:
    return BANNERS[key].path


def banner_usage_lines() -> list[str]:
    return [f"{banner.path} — {banner.title}: {banner.used_in}" for banner in BANNERS.values()]
