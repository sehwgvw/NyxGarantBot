from sqlalchemy import Select, delete, func, or_, select
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


async def upsert_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    full_name: str | None,
    settings: Settings,
) -> User:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            language=settings.default_language,
        )
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


async def has_role(
    session: AsyncSession,
    user_id: int,
    role: UserRole,
    settings: Settings | None = None,
    telegram_id: int | None = None,
) -> bool:
    if role == UserRole.ADMIN and settings and telegram_id == settings.main_admin_id:
        return True
    exists = await session.scalar(
        select(RoleAssignment.id).where(
            RoleAssignment.user_id == user_id, RoleAssignment.role == role
        )
    )
    return exists is not None


async def ensure_main_admin(session: AsyncSession, user: User, settings: Settings) -> None:
    if user.telegram_id != settings.main_admin_id:
        return
    for role in (UserRole.USER, UserRole.ADMIN):
        exists = await session.scalar(
            select(RoleAssignment.id).where(
                RoleAssignment.user_id == user.id, RoleAssignment.role == role
            )
        )
        if exists is None:
            session.add(RoleAssignment(user_id=user.id, role=role, granted_by_id=user.id))
    await session.commit()


async def get_setting(session: AsyncSession, key: str, default=None):
    setting = await session.get(BotSetting, key)
    return default if setting is None else setting.value


async def set_setting(
    session: AsyncSession, key: str, value, updated_by_id: int | None = None
) -> None:
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
    session.add(
        AuditLog(
            event_type=event_type,
            severity=severity,
            actor_id=actor_id,
            target_user_id=target_user_id,
            deal_id=deal_id,
            payload=payload or {},
        )
    )
    await session.commit()


async def create_deal(
    session: AsyncSession, creator: User, data: dict, guarantor_id: int | None
) -> Deal:
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
        status=DealStatus.WAITING_GROUP,
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
        .where(
            (GuarantorProfile.min_deal_amount.is_(None))
            | (GuarantorProfile.min_deal_amount <= amount)
        )
        .where(
            (GuarantorProfile.max_deal_amount.is_(None))
            | (GuarantorProfile.max_deal_amount >= amount)
        )
        .order_by(
            GuarantorProfile.is_online.desc(),
            GuarantorProfile.successful_deals.desc(),
            GuarantorProfile.rating.desc(),
        )
        .limit(1)
    )
    return await session.scalar(stmt)


async def list_guarantors(
    session: AsyncSession, amount: float | None = None, only_top: bool = False
) -> list[GuarantorProfile]:
    stmt = select(GuarantorProfile).where(GuarantorProfile.is_active.is_(True))
    if only_top:
        stmt = stmt.where(GuarantorProfile.is_top.is_(True))
    if amount is not None:
        stmt = stmt.where(
            (GuarantorProfile.min_deal_amount.is_(None))
            | (GuarantorProfile.min_deal_amount <= amount)
        )
        stmt = stmt.where(
            (GuarantorProfile.max_deal_amount.is_(None))
            | (GuarantorProfile.max_deal_amount >= amount)
        )
    stmt = stmt.order_by(
        GuarantorProfile.is_top.desc(),
        GuarantorProfile.rating.desc(),
        GuarantorProfile.successful_deals.desc(),
    )
    result = await session.scalars(stmt)
    return list(result)


async def confirm_group_entry(session: AsyncSession, deal: Deal, user: User) -> Deal:
    if deal.buyer_id == user.id:
        deal.buyer_confirmed_group = True
    if deal.seller_id == user.id:
        deal.seller_confirmed_group = True
    if deal.guarantor_id == user.id:
        deal.guarantor_confirmed_group = True
    if (
        deal.buyer_confirmed_group
        and deal.seller_confirmed_group
        and deal.guarantor_confirmed_group
    ):
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
        deal.completed_at = func.now()
        if deal.guarantor_id:
            profile = await session.scalar(
                select(GuarantorProfile).where(GuarantorProfile.user_id == deal.guarantor_id)
            )
            if profile:
                profile.successful_deals += 1
    await session.commit()
    return finished


async def create_report(
    session: AsyncSession,
    author: User,
    text: str,
    kind: str = "support",
    deal_id: int | None = None,
) -> Report:
    report = Report(author_id=author.id, text=text, kind=kind, deal_id=deal_id)
    session.add(report)
    await session.flush()
    await log_event(
        session,
        f"report.{kind}.created",
        actor_id=author.id,
        deal_id=deal_id,
        payload={"text": text, "report_id": report.id},
    )
    return report


async def block_for_unpaid_cancel(session: AsyncSession, user: User, settings: Settings) -> Block:
    user.unpaid_cancel_count += 1
    permanent = (
        settings.permanent_block_after_limit
        and user.unpaid_cancel_count >= settings.max_unpaid_cancels
    )
    user.is_blocked = True
    block = Block(
        user_id=user.id,
        type=BlockType.PERMANENT if permanent else BlockType.TEMPORARY,
        reason="Отмена сделки без оплаты штрафа гаранту",
    )
    session.add(block)
    await log_event(
        session,
        "user.blocked.unpaid_cancel",
        target_user_id=user.id,
        severity="warning",
        payload={"permanent": permanent},
    )
    return block


async def add_review(
    session: AsyncSession, deal: Deal, author: User, stars: int, text: str | None = None
) -> Review:
    if not deal.guarantor_id:
        raise ValueError("Deal has no guarantor")
    review = Review(
        deal_id=deal.id, guarantor_id=deal.guarantor_id, author_id=author.id, stars=stars, text=text
    )
    session.add(review)
    profile = await session.scalar(
        select(GuarantorProfile).where(GuarantorProfile.user_id == deal.guarantor_id)
    )
    if profile:
        count = (
            await session.scalar(
                select(func.count(Review.id)).where(Review.guarantor_id == deal.guarantor_id)
            )
            or 0
        )
        profile.rating = ((profile.rating * count) + stars) / (count + 1)
        profile.reviews_count += 1
    await log_event(
        session, "review.created", actor_id=author.id, deal_id=deal.id, payload={"stars": stars}
    )
    return review


async def list_guarantors_page(
    session: AsyncSession,
    page: int = 0,
    per_page: int = 5,
    *,
    amount: float | None = None,
    only_top: bool = False,
    favorite_user_id: int | None = None,
) -> tuple[list[tuple[GuarantorProfile, User, bool]], int]:
    stmt = (
        select(GuarantorProfile, User)
        .join(User, User.id == GuarantorProfile.user_id)
        .where(GuarantorProfile.is_active.is_(True), User.is_blocked.is_(False))
    )
    count_stmt = (
        select(func.count(GuarantorProfile.id))
        .join(User, User.id == GuarantorProfile.user_id)
        .where(GuarantorProfile.is_active.is_(True), User.is_blocked.is_(False))
    )
    if only_top:
        stmt = stmt.where(GuarantorProfile.is_top.is_(True))
        count_stmt = count_stmt.where(GuarantorProfile.is_top.is_(True))
    if amount is not None:
        amount_filter = (
            (
                (GuarantorProfile.min_deal_amount.is_(None))
                | (GuarantorProfile.min_deal_amount <= amount)
            ),
            (
                (GuarantorProfile.max_deal_amount.is_(None))
                | (GuarantorProfile.max_deal_amount >= amount)
            ),
        )
        stmt = stmt.where(*amount_filter)
        count_stmt = count_stmt.where(*amount_filter)
    stmt = stmt.order_by(
        GuarantorProfile.is_top.desc(),
        GuarantorProfile.rating.desc(),
        GuarantorProfile.successful_deals.desc(),
        GuarantorProfile.id.asc(),
    )
    total = await session.scalar(count_stmt) or 0
    rows = (await session.execute(stmt.offset(max(page, 0) * per_page).limit(per_page))).all()
    favorites: set[int] = set()
    if favorite_user_id and rows:
        ids = [profile.user_id for profile, _ in rows]
        favorites = set(
            await session.scalars(
                select(FavoriteGuarantor.guarantor_id).where(
                    FavoriteGuarantor.user_id == favorite_user_id,
                    FavoriteGuarantor.guarantor_id.in_(ids),
                )
            )
        )
    return [(profile, user, profile.user_id in favorites) for profile, user in rows], total


async def list_favorite_guarantors(
    session: AsyncSession, user_id: int, page: int = 0, per_page: int = 5
) -> tuple[list[tuple[GuarantorProfile, User, bool]], int]:
    base = (
        select(GuarantorProfile, User)
        .join(FavoriteGuarantor, FavoriteGuarantor.guarantor_id == GuarantorProfile.user_id)
        .join(User, User.id == GuarantorProfile.user_id)
        .where(
            FavoriteGuarantor.user_id == user_id,
            GuarantorProfile.is_active.is_(True),
            User.is_blocked.is_(False),
        )
    )
    total = (
        await session.scalar(
            select(func.count(FavoriteGuarantor.id))
            .join(GuarantorProfile, GuarantorProfile.user_id == FavoriteGuarantor.guarantor_id)
            .join(User, User.id == GuarantorProfile.user_id)
            .where(
                FavoriteGuarantor.user_id == user_id,
                GuarantorProfile.is_active.is_(True),
                User.is_blocked.is_(False),
            )
        )
        or 0
    )
    rows = (
        await session.execute(
            base.order_by(FavoriteGuarantor.created_at.desc(), GuarantorProfile.rating.desc())
            .offset(max(page, 0) * per_page)
            .limit(per_page)
        )
    ).all()
    return [(profile, user, True) for profile, user in rows], total


async def get_guarantor_card(
    session: AsyncSession, guarantor_id: int
) -> tuple[GuarantorProfile, User] | None:
    return (
        await session.execute(
            select(GuarantorProfile, User)
            .join(User, User.id == GuarantorProfile.user_id)
            .where(
                GuarantorProfile.user_id == guarantor_id,
                GuarantorProfile.is_active.is_(True),
                User.is_blocked.is_(False),
            )
        )
    ).one_or_none()


async def is_favorite_guarantor(session: AsyncSession, user_id: int, guarantor_id: int) -> bool:
    exists = await session.scalar(
        select(FavoriteGuarantor.id).where(
            FavoriteGuarantor.user_id == user_id, FavoriteGuarantor.guarantor_id == guarantor_id
        )
    )
    return exists is not None


async def set_favorite_guarantor(
    session: AsyncSession, user_id: int, guarantor_id: int, enabled: bool
) -> None:
    if enabled:
        if not await is_favorite_guarantor(session, user_id, guarantor_id):
            session.add(FavoriteGuarantor(user_id=user_id, guarantor_id=guarantor_id))
    else:
        await session.execute(
            delete(FavoriteGuarantor).where(
                FavoriteGuarantor.user_id == user_id, FavoriteGuarantor.guarantor_id == guarantor_id
            )
        )
    await session.commit()


async def list_deals_for_user(
    session: AsyncSession, user_id: int, page: int = 0, per_page: int = 6
) -> tuple[list[Deal], int]:
    membership = or_(
        Deal.creator_id == user_id,
        Deal.buyer_id == user_id,
        Deal.seller_id == user_id,
        Deal.guarantor_id == user_id,
    )
    total = await session.scalar(select(func.count(Deal.id)).where(membership)) or 0
    deals = list(
        await session.scalars(
            select(Deal)
            .where(membership)
            .order_by(Deal.created_at.desc(), Deal.id.desc())
            .offset(max(page, 0) * per_page)
            .limit(per_page)
        )
    )
    return deals, total


async def count_user_deals(session: AsyncSession, user_id: int) -> int:
    membership = or_(
        Deal.creator_id == user_id,
        Deal.buyer_id == user_id,
        Deal.seller_id == user_id,
        Deal.guarantor_id == user_id,
    )
    return await session.scalar(select(func.count(Deal.id)).where(membership)) or 0


async def get_deal_for_user(
    session: AsyncSession, deal_id: int, user_id: int
) -> tuple[Deal, User | None, User | None, User | None, User | None] | None:
    deal = await session.get(Deal, deal_id)
    if deal is None or user_id not in {
        deal.creator_id,
        deal.buyer_id,
        deal.seller_id,
        deal.guarantor_id,
    }:
        return None
    user_ids = {
        value
        for value in (deal.creator_id, deal.buyer_id, deal.seller_id, deal.guarantor_id)
        if value is not None
    }
    users = (
        {user.id: user for user in await session.scalars(select(User).where(User.id.in_(user_ids)))}
        if user_ids
        else {}
    )
    return (
        deal,
        users.get(deal.creator_id),
        users.get(deal.buyer_id),
        users.get(deal.seller_id),
        users.get(deal.guarantor_id),
    )


async def list_reviews_page(
    session: AsyncSession, page: int = 0, per_page: int = 5
) -> tuple[list[tuple[Review, User | None, User | None]], int]:
    total = await session.scalar(select(func.count(Review.id))) or 0
    reviews = list(
        await session.scalars(
            select(Review)
            .order_by(Review.created_at.desc(), Review.id.desc())
            .offset(max(page, 0) * per_page)
            .limit(per_page)
        )
    )
    user_ids = {
        value
        for review in reviews
        for value in (review.guarantor_id, review.author_id)
        if value is not None
    }
    users = (
        {user.id: user for user in await session.scalars(select(User).where(User.id.in_(user_ids)))}
        if user_ids
        else {}
    )
    return [
        (review, users.get(review.guarantor_id), users.get(review.author_id)) for review in reviews
    ], total


async def count_user_reviews(session: AsyncSession, user_id: int) -> int:
    return (
        await session.scalar(select(func.count(Review.id)).where(Review.author_id == user_id)) or 0
    )
