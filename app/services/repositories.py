from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import (
    AuditLog,
    Block,
    BlockType,
    BotSetting,
    Deal,
    DealStatus,
    FavoriteGuarantor,
    GuarantorProfile,
    Report,
    Review,
    RoleAssignment,
    User,
    UserRole,
)


async def upsert_user(session: AsyncSession, telegram_id: int, username: str | None, full_name: str | None, settings: Settings) -> User:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(telegram_id=telegram_id, username=username, full_name=full_name, language=settings.default_language)
        session.add(user)
        await session.flush()
        session.add(RoleAssignment(user_id=user.id, role=UserRole.USER))
    else:
        user.username = username
        user.full_name = full_name
    await session.commit()
    return user


async def get_user_by_tg(session: AsyncSession, telegram_id: int) -> User | None:
    return await session.scalar(select(User).where(User.telegram_id == telegram_id))


async def has_role(session: AsyncSession, user_id: int, role: UserRole, settings: Settings | None = None, telegram_id: int | None = None) -> bool:
    if settings and telegram_id == settings.main_admin_id and role in {UserRole.ADMIN, UserRole.MAIN_ADMIN}:
        return True
    if role == UserRole.MAIN_ADMIN:
        return False
    exists = await session.scalar(select(RoleAssignment.id).where(RoleAssignment.user_id == user_id, RoleAssignment.role == role))
    return exists is not None


async def ensure_main_admin(session: AsyncSession, user: User, settings: Settings) -> None:
    if user.telegram_id != settings.main_admin_id:
        return
    for role in (UserRole.USER, UserRole.ADMIN, UserRole.MAIN_ADMIN):
        exists = await session.scalar(select(RoleAssignment.id).where(RoleAssignment.user_id == user.id, RoleAssignment.role == role))
        if exists is None:
            session.add(RoleAssignment(user_id=user.id, role=role, granted_by_id=user.id))
    await session.commit()


async def get_setting(session: AsyncSession, key: str, default=None):
    setting = await session.get(BotSetting, key)
    return default if setting is None else setting.value


async def set_setting(session: AsyncSession, key: str, value, updated_by_id: int | None = None) -> None:
    setting = await session.get(BotSetting, key)
    if setting is None:
        setting = BotSetting(key=key, value=value, updated_by_id=updated_by_id)
        session.add(setting)
    else:
        setting.value = value
        setting.updated_by_id = updated_by_id
    await session.commit()


async def log_event(
    session: AsyncSession,
    event_type: str,
    *,
    severity: str = "info",
    actor_id: int | None = None,
    target_user_id: int | None = None,
    deal_id: int | None = None,
    payload: dict | None = None,
) -> None:
    session.add(AuditLog(event_type=event_type, severity=severity, actor_id=actor_id, target_user_id=target_user_id, deal_id=deal_id, payload=payload or {}))
    await session.flush()


async def create_deal(session: AsyncSession, creator: User, data: dict, guarantor_id: int | None) -> Deal:
    side = data["side"]
    deal = Deal(
        amount=float(data["amount"]),
        currency=data.get("currency", "RUB"),
        subject=data["subject"],
        method=data["method"],
        creator_id=creator.id,
        buyer_id=creator.id if side == "buyer" else None,
        seller_id=creator.id if side == "seller" else None,
        guarantor_id=guarantor_id,
        pending_counterparty_tg_id=data.get("counterparty_tg_id"),
        status=DealStatus.WAITING_GROUP,
        metadata_json={"guarantor_tg_id": data.get("guarantor_tg")},
    )
    session.add(deal)
    await session.flush()
    await log_event(session, "deal.created", actor_id=creator.id, deal_id=deal.id, payload=data)
    return deal


async def choose_auto_guarantor(session: AsyncSession, amount: float) -> User | None:
    stmt: Select = (
        select(User)
        .join(GuarantorProfile, GuarantorProfile.user_id == User.id)
        .where(GuarantorProfile.is_active.is_(True))
        .where(User.is_blocked.is_(False))
        .where((GuarantorProfile.min_deal_amount.is_(None)) | (GuarantorProfile.min_deal_amount <= amount))
        .where((GuarantorProfile.max_deal_amount.is_(None)) | (GuarantorProfile.max_deal_amount >= amount))
        .order_by(GuarantorProfile.is_online.desc(), GuarantorProfile.successful_deals.desc(), GuarantorProfile.rating.desc())
        .limit(1)
    )
    return await session.scalar(stmt)


async def list_guarantors(session: AsyncSession, amount: float | None = None, only_top: bool = False) -> list[GuarantorProfile]:
    stmt = select(GuarantorProfile).where(GuarantorProfile.is_active.is_(True))
    if only_top:
        stmt = stmt.where(GuarantorProfile.is_top.is_(True))
    if amount is not None:
        stmt = stmt.where((GuarantorProfile.min_deal_amount.is_(None)) | (GuarantorProfile.min_deal_amount <= amount))
        stmt = stmt.where((GuarantorProfile.max_deal_amount.is_(None)) | (GuarantorProfile.max_deal_amount >= amount))
    stmt = stmt.order_by(GuarantorProfile.is_top.desc(), GuarantorProfile.rating.desc(), GuarantorProfile.successful_deals.desc())
    result = await session.scalars(stmt)
    return list(result)


async def bind_counterparty(session: AsyncSession, deal: Deal, user: User) -> None:
    if user.id in {deal.buyer_id, deal.seller_id, deal.guarantor_id}:
        return
    if deal.buyer_id is None:
        deal.buyer_id = user.id
    elif deal.seller_id is None:
        deal.seller_id = user.id
    else:
        raise ValueError("Both deal sides are already assigned")
    await log_event(session, "deal.counterparty.joined", actor_id=user.id, deal_id=deal.id)


async def confirm_group_entry(session: AsyncSession, deal: Deal, user: User) -> Deal:
    if deal.buyer_id == user.id:
        deal.buyer_confirmed_group = True
    if deal.seller_id == user.id:
        deal.seller_confirmed_group = True
    if deal.guarantor_id == user.id:
        deal.guarantor_confirmed_group = True
    if deal.buyer_confirmed_group and deal.seller_confirmed_group and deal.guarantor_confirmed_group:
        deal.status = DealStatus.ACTIVE
    await session.commit()
    return deal


async def confirm_success(session: AsyncSession, deal: Deal, user: User) -> bool:
    if deal.buyer_id == user.id:
        deal.buyer_success_confirmed = True
    if deal.seller_id == user.id:
        deal.seller_success_confirmed = True
    finished = deal.buyer_success_confirmed and deal.seller_success_confirmed
    if finished and deal.status != DealStatus.COMPLETED:
        deal.status = DealStatus.COMPLETED
        deal.completed_at = datetime.now(UTC)
        if deal.guarantor_id:
            profile = await session.scalar(select(GuarantorProfile).where(GuarantorProfile.user_id == deal.guarantor_id))
            if profile:
                profile.successful_deals += 1
        await log_event(session, "deal.completed", actor_id=user.id, deal_id=deal.id)
    await session.commit()
    return finished


async def create_report(session: AsyncSession, author: User, text: str, kind: str = "support", deal_id: int | None = None) -> Report:
    report = Report(author_id=author.id, text=text, kind=kind, deal_id=deal_id)
    session.add(report)
    await session.flush()
    await log_event(session, f"report.{kind}.created", actor_id=author.id, deal_id=deal_id, payload={"text": text, "report_id": report.id})
    await session.commit()
    return report


async def block_for_unpaid_cancel(session: AsyncSession, user: User, settings: Settings) -> Block:
    user.unpaid_cancel_count += 1
    permanent = settings.permanent_block_after_limit and user.unpaid_cancel_count >= settings.max_unpaid_cancels
    user.is_blocked = True
    block = Block(
        user_id=user.id,
        type=BlockType.PERMANENT if permanent else BlockType.TEMPORARY,
        reason="Отмена сделки без оплаты штрафа гаранту",
    )
    session.add(block)
    await log_event(session, "user.blocked.unpaid_cancel", target_user_id=user.id, severity="warning", payload={"permanent": permanent})
    await session.commit()
    return block


async def add_review(session: AsyncSession, deal: Deal, author: User, stars: int, text: str | None = None) -> Review:
    if not deal.guarantor_id:
        raise ValueError("Deal has no guarantor")
    review = await session.scalar(select(Review).where(Review.deal_id == deal.id, Review.author_id == author.id))
    if review is None:
        review = Review(deal_id=deal.id, guarantor_id=deal.guarantor_id, author_id=author.id, stars=stars, text=text)
        session.add(review)
    else:
        review.stars = stars
        review.text = text or review.text
    await session.flush()
    profile = await session.scalar(select(GuarantorProfile).where(GuarantorProfile.user_id == deal.guarantor_id))
    if profile:
        rows = await session.scalars(select(Review.stars).where(Review.guarantor_id == deal.guarantor_id))
        values = list(rows)
        profile.rating = sum(values) / len(values) if values else 0.0
        profile.reviews_count = len(values)
    await log_event(session, "review.created", actor_id=author.id, deal_id=deal.id, payload={"stars": stars, "has_text": bool(text)})
    return review


async def list_staff(session: AsyncSession, settings: Settings) -> list[tuple[str, User]]:
    stmt = select(User, RoleAssignment.role).join(RoleAssignment, RoleAssignment.user_id == User.id).where(
        RoleAssignment.role.in_([UserRole.ADMIN, UserRole.MODERATOR])
    )
    rows = list((await session.execute(stmt)).all())
    result: list[tuple[str, User]] = []
    seen: set[int] = set()
    main_admin = await get_user_by_tg(session, settings.main_admin_id)
    if main_admin:
        result.append(("Главный администратор", main_admin))
        seen.add(main_admin.id)
    for user, role in rows:
        if user.id in seen:
            continue
        title = "Администратор" if role == UserRole.ADMIN else "Модератор"
        result.append((title, user))
        seen.add(user.id)
    return result


async def user_deals(session: AsyncSession, user_id: int, limit: int = 20) -> list[Deal]:
    stmt = (
        select(Deal)
        .where((Deal.creator_id == user_id) | (Deal.buyer_id == user_id) | (Deal.seller_id == user_id) | (Deal.guarantor_id == user_id))
        .order_by(Deal.created_at.desc())
        .limit(limit)
    )
    return list(await session.scalars(stmt))


async def favorite_guarantors(session: AsyncSession, user_id: int) -> list[GuarantorProfile]:
    stmt = (
        select(GuarantorProfile)
        .join(FavoriteGuarantor, FavoriteGuarantor.guarantor_id == GuarantorProfile.user_id)
        .where(FavoriteGuarantor.user_id == user_id)
        .order_by(GuarantorProfile.rating.desc())
    )
    return list(await session.scalars(stmt))
