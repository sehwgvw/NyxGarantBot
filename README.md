# NyxGarantBot

Telegram-бот гаранта / escrow-сервис по ТЗ из `ТЗ_телеграм_бот_гарант_ФИНАЛ.docx`.

## Возможности

- Главное меню через inline-кнопки.
- Роли: пользователь, гарант, модератор, администратор, главный администратор.
- Создание сделки с суммой, описанием, методом, стороной и выбором гаранта.
- Автоподбор гаранта с учётом рейтинга, успешных сделок, online-статуса и лимитов суммы сделки.
- Минимальная и максимальная сумма сделки в профиле гаранта: если гарант указал `min_deal_amount=3000`, пользователь сможет выбрать его только для сделки от `3000₽`; аналогично работает `max_deal_amount`.
- Архитектурно выделенный userbot/session-модуль для создания приватных групп сделок.
- Подтверждение входа покупателем, продавцом и гарантом; после трёх подтверждений в группу отправляется баннер `deal_commands_banner.png` и список команд.
- Команды внутри группы: `/dispute`, `/scam`, `/change_metod`, `/support`, `/add_ruch`, `/get_link`.
- Support/reports со служебной группой, принятием в работу и закрытием репорта.
- Отзывы и рейтинг гаранта.
- Блокировки за неоплаченный штраф отмены сделки.
- Настройки через бота командой `/set_setting KEY VALUE`; ID служебных групп можно менять прямо в боте главным администратором.
- Автобэкапы PostgreSQL по расписанию.

## Быстрый старт

1. Скопируйте `.env.example` в `.env` и заполните реальные значения:

```bash
cp .env.example .env
```

2. Запустите проект:

```bash
docker compose up --build
```

3. Главный администратор задаётся переменной `MAIN_ADMIN_ID`. При первом `/start` пользователь с этим Telegram ID автоматически получает роль администратора.

## Конфигурация

Поддерживаются переменные:

- `BOT_TOKEN`
- `MAIN_ADMIN_ID`
- `DATABASE_URL`
- `DEFAULT_LANGUAGE`
- `SUPPORT_USERNAME`
- `MODERATION_GROUP_ID`
- `LOG_GROUP_ID`
- `USE_USERBOT`
- `API_ID`
- `API_HASH`
- `SESSION_PATH`
- `DEFAULT_DEAL_CONFIRM_TIMEOUT`
- `DEFAULT_DEAL_FINISH_TIMEOUT`
- `DEFAULT_DISPUTE_TIMEOUT`
- `MAX_UNPAID_CANCELS`
- `PERMANENT_BLOCK_AFTER_LIMIT`
- `TOP_GUARANTOR_MIN_RATING`
- `TOP_GUARANTOR_MIN_SUCCESS_DEALS`
- `BACKUP_ENABLED`
- `BACKUP_INTERVAL_HOURS`

> `.env` намеренно добавлен в `.gitignore`: реальные токены и API hash не должны попадать в коммит. Локальный `.env` можно хранить на сервере рядом с проектом.

## Настройка групп прямо в боте

Главный администратор может изменить ID служебных групп без правки кода:

```text
/set_setting MODERATION_GROUP_ID tg://chat?id=5293025142
/set_setting LOG_GROUP_ID tg://chat?id=5012673507
```

Команда-подсказка:

```text
/set_groups
```

## Добавление гаранта

Пользователь сначала должен нажать `/start`, затем главный администратор выполняет:

```text
/add_guarantor TELEGRAM_ID [min_amount] [max_amount]
```

Пример:

```text
/add_guarantor 123456789 3000 100000
```

Такой гарант будет доступен только для сделок от `3000₽` до `100000₽`.

## Полный список баннеров и привязка к меню/событиям

Все баннеры должны быть PNG, `1280x720`, `16:9`, единый стиль: 2D minimalistic premium, dark background, neon blue / purple palette.

| Файл | Заголовок | Где используется |
| --- | --- | --- |
| `assets/banners/start_banner.png` | Безопасные сделки через гарантов | `/start`, главное меню |
| `assets/banners/create_deal_banner.png` | Создание новой сделки | Экран создания сделки |
| `assets/banners/active_deal_banner.png` | Сделка активна | Карточка активной сделки |
| `assets/banners/success_banner.png` | Сделка успешно завершена | Завершение сделки, просьба оценить гаранта |
| `assets/banners/cancel_banner.png` | Сделка отменена | Экран отмены сделки |
| `assets/banners/dispute_banner.png` | Арбитраж сделки | `/dispute`, спорные ситуации |
| `assets/banners/scam_banner.png` | Проверка жалобы | `/scam`, жалоба на скам |
| `assets/banners/support_banner.png` | Центр поддержки | `/support`, служба помощи |
| `assets/banners/guarantors_banner.png` | Каталог гарантов | Раздел всех гарантов |
| `assets/banners/guarantor_profile_banner.png` | Профиль гаранта | Карточка конкретного гаранта |
| `assets/banners/top_guarantors_banner.png` | Лучшие гаранты сервиса | Раздел ТОП гарантов |
| `assets/banners/favorites_banner.png` | Избранные гаранты | Избранные гаранты пользователя |
| `assets/banners/profile_banner.png` | Личный кабинет | Профиль пользователя |
| `assets/banners/history_banner.png` | История сделок | История сделок |
| `assets/banners/reviews_banner.png` | Отзывы пользователей | Раздел отзывов гаранта |
| `assets/banners/guarantor_cabinet_banner.png` | Кабинет гаранта | Личный кабинет гаранта |
| `assets/banners/add_ruch_banner.png` | Добавление рученца | `/add_ruch`, добавление рученца в сделку |
| `assets/banners/staff_banner.png` | Команда проекта | Список сотрудников бота |
| `assets/banners/moderator_banner.png` | Панель модератора | Кабинет модератора |
| `assets/banners/admin_banner.png` | Панель администратора | Кабинет администратора |
| `assets/banners/logs_banner.png` | Системные журналы | Раздел логов |
| `assets/banners/blocked_banner.png` | Доступ ограничен | Блокировка пользователя |
| `assets/banners/waiting_user_banner.png` | Ожидание подключения участника | Ожидание регистрации `/start` |
| `assets/banners/waiting_group_banner.png` | Ожидание подтверждения входа | Статус после создания группы сделки |
| `assets/banners/deal_commands_banner.png` | Команды управления сделкой | Сообщение с командами внутри группы сделки после подтверждения 3 участников |
| `assets/banners/report_banner.png` | Репорт принят | Support/report экран |

## Userbot

`USE_USERBOT=false` оставляет основной bot-flow рабочим, но Telegram Bot API не создаёт группы самостоятельно. Для реального автосоздания приватных групп включите:

```env
USE_USERBOT=true
API_ID=...
API_HASH=...
SESSION_PATH=sessions/nyx_userbot.session
```

Session-файл создаётся владельцем аккаунта отдельно и хранится вне git.

## Описание привязки баннеров списком

- `assets/banners/start_banner.png` — `/start` и главное меню: стартовый экран с inline-навигацией по разделам.
- `assets/banners/create_deal_banner.png` — мастер создания сделки: ввод суммы, сути сделки, метода, стороны и выбора гаранта.
- `assets/banners/active_deal_banner.png` — момент, когда покупатель, продавец и гарант подтвердили вход, а сделка переведена в активный статус.
- `assets/banners/success_banner.png` — завершение сделки после двух подтверждений сторон и экран оценки гаранта.
- `assets/banners/cancel_banner.png` — отмена создания сделки или отменённая сделка.
- `assets/banners/dispute_banner.png` — команда `/dispute` внутри сделочной группы и сценарии арбитража.
- `assets/banners/scam_banner.png` — команда `/scam` внутри сделки, жалоба на скам/нарушение.
- `assets/banners/support_banner.png` — команда `/support` и раздел центра поддержки.
- `assets/banners/guarantors_banner.png` — каталог всех активных гарантов и ручной выбор гаранта для сделки.
- `assets/banners/guarantor_profile_banner.png` — карточка конкретного гаранта с рейтингом, лимитами, комиссией и статусами.
- `assets/banners/top_guarantors_banner.png` — раздел выбора ТОП-гаранта.
- `assets/banners/favorites_banner.png` — личный список избранных гарантов пользователя.
- `assets/banners/profile_banner.png` — личный кабинет пользователя, статусы, ограничения и последние сделки.
- `assets/banners/history_banner.png` — история сделок пользователя.
- `assets/banners/reviews_banner.png` — список отзывов и оценок пользователей по гарантам.
- `assets/banners/guarantor_cabinet_banner.png` — кабинет гаранта: статистика, комиссия, лимиты, статусы.
- `assets/banners/add_ruch_banner.png` — команда `/add_ruch` для добавления рученца в конкретную сделку.
- `assets/banners/staff_banner.png` — список сотрудников проекта: главный админ, админы и модераторы.
- `assets/banners/moderator_banner.png` — кабинет модератора и очередь support/report.
- `assets/banners/admin_banner.png` — кабинет администратора, управление ролями, группами, настройками и гарантам.
- `assets/banners/logs_banner.png` — просмотр структурированных системных журналов главным администратором.
- `assets/banners/blocked_banner.png` — сообщение об ограничении доступа или отсутствии прав.
- `assets/banners/waiting_user_banner.png` — ожидание подключения второго участника через `/start`/deep-link.
- `assets/banners/waiting_group_banner.png` — сделка создана, ожидается вход/подтверждение покупателя, продавца и гаранта.
- `assets/banners/deal_commands_banner.png` — закреплённое/служебное сообщение с командами управления внутри группы сделки.
- `assets/banners/report_banner.png` — подтверждение, что support/report принят и передан модераторам.

Бинарные изображения в репозиторий не добавляются: бот ожидает готовые PNG-файлы с указанными именами в `assets/banners/`. Если файла нет, соответствующий экран автоматически отправляется текстом без падения.
