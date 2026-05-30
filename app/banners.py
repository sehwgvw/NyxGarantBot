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
    "start": Banner("start", "start_banner.png", "Безопасные сделки через гарантов", "/start, главное меню", "shield, handshake, digital trust symbols"),
    "create_deal": Banner("create_deal", "create_deal_banner.png", "Создание новой сделки", "Экран создания сделки", "buyer and seller initiating a deal"),
    "active_deal": Banner("active_deal", "active_deal_banner.png", "Сделка активна", "Карточка активной сделки", "buyer, seller and guarantor connected"),
    "success": Banner("success", "success_banner.png", "Сделка успешно завершена", "Завершение сделки, просьба оценить гаранта", "success checkmark, trophy"),
    "cancel": Banner("cancel", "cancel_banner.png", "Сделка отменена", "Экран отмены сделки", "red cancel indicator, broken contract"),
    "dispute": Banner("dispute", "dispute_banner.png", "Арбитраж сделки", "/dispute, спорные ситуации", "justice scales, arbitration UI"),
    "scam": Banner("scam", "scam_banner.png", "Проверка жалобы", "/scam, жалоба на скам", "shield, alert symbol, investigation"),
    "support": Banner("support", "support_banner.png", "Центр поддержки", "/support, служба помощи", "support operator, tickets"),
    "guarantors": Banner("guarantors", "guarantors_banner.png", "Каталог гарантов", "Раздел всех гарантов", "guarantor cards, ratings, filters"),
    "guarantor_profile": Banner("guarantor_profile", "guarantor_profile_banner.png", "Профиль гаранта", "Карточка конкретного гаранта", "profile card, rating stars"),
    "top_guarantors": Banner("top_guarantors", "top_guarantors_banner.png", "Лучшие гаранты сервиса", "Раздел ТОП гарантов", "podium, gold silver bronze"),
    "favorites": Banner("favorites", "favorites_banner.png", "Избранные гаранты", "Избранные гаранты пользователя", "heart, saved guarantor cards"),
    "profile": Banner("profile", "profile_banner.png", "Личный кабинет", "Профиль пользователя", "avatar card, stats dashboard"),
    "history": Banner("history", "history_banner.png", "История сделок", "История сделок", "archive, document timeline"),
    "reviews": Banner("reviews", "reviews_banner.png", "Отзывы пользователей", "Раздел отзывов гаранта", "stars, comments, social proof"),
    "guarantor_cabinet": Banner("guarantor_cabinet", "guarantor_cabinet_banner.png", "Кабинет гаранта", "Личный кабинет гаранта", "dashboard, statistics, commission widgets"),
    "add_ruch": Banner("add_ruch", "add_ruch_banner.png", "Добавление рученца", "/add_ruch, добавление рученца в сделку", "guarantor plus assistant"),
    "staff": Banner("staff", "staff_banner.png", "Команда проекта", "Список сотрудников бота", "role hierarchy, admins, moderators"),
    "moderator": Banner("moderator", "moderator_banner.png", "Панель модератора", "Кабинет модератора", "moderation tickets, service queue"),
    "admin": Banner("admin", "admin_banner.png", "Панель администратора", "Кабинет администратора", "dashboard, charts, settings, logs"),
    "logs": Banner("logs", "logs_banner.png", "Системные журналы", "Раздел логов", "terminal logs, event monitoring"),
    "blocked": Banner("blocked", "blocked_banner.png", "Доступ ограничен", "Блокировка пользователя", "lock, red shield, access denied"),
    "waiting_user": Banner("waiting_user", "waiting_user_banner.png", "Ожидание подключения участника", "Ожидание регистрации /start", "clock, user icon, waiting"),
    "waiting_group": Banner("waiting_group", "waiting_group_banner.png", "Ожидание подтверждения входа", "Статус после создания группы сделки", "Telegram group, three avatars"),
    "deal_commands": Banner("deal_commands", "deal_commands_banner.png", "Команды управления сделкой", "Сообщение с командами внутри группы сделки", "command terminal, command list"),
    "report": Banner("report", "report_banner.png", "Репорт принят", "Support/report экран", "incident accepted, report processing"),
}


def banner_path(key: str) -> Path:
    return BANNERS[key].path
