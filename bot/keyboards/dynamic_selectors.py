from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import re

from backend.models import Branch, Dealer, RatePlan, ServiceType, ReportPeriod

_SELECTOR_PAGE_SIZE = 10


def _normalize_name(value: str | None) -> str:
    if value is None:
        return ""
    value = str(value).replace("\u00a0", " ").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def _clamp_page(page: int, total: int) -> int:
    max_page = max((total - 1) // _SELECTOR_PAGE_SIZE, 0)
    if page < 0:
        return 0
    if page > max_page:
        return max_page
    return page


def _append_page_buttons(
    buttons: list[list[InlineKeyboardButton]],
    total: int,
    page: int,
    kind: str,
) -> None:
    if total <= _SELECTOR_PAGE_SIZE:
        return

    max_page = max((total - 1) // _SELECTOR_PAGE_SIZE, 0)
    current_page = _clamp_page(page, total)
    if current_page > max_page:
        current_page = max_page

    nav: list[InlineKeyboardButton] = []
    if current_page > 0:
        nav.append(
            InlineKeyboardButton(
                text="< Oldingi",
                callback_data=f"sel:{kind}_page:{current_page - 1}",
            )
        )
    if current_page < max_page:
        nav.append(
            InlineKeyboardButton(
                text="Keyingi >",
                callback_data=f"sel:{kind}_page:{current_page + 1}",
            )
        )
    if nav:
        buttons.append(nav)


async def branch_selector(
    session: AsyncSession,
    page: int = 0,
) -> InlineKeyboardMarkup:
    total_stmt = select(func.count(Branch.id)).where(Branch.is_active == True)
    total = (await session.execute(total_stmt)).scalar_one() or 0
    if total == 0:
        buttons = [
            [InlineKeyboardButton(text="— Filial yo'q —", callback_data="sel:branch:0")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    current_page = _clamp_page(page, total)
    stmt = (
        select(Branch)
        .where(Branch.is_active == True)
        .order_by(Branch.name.asc())
        .offset(current_page * _SELECTOR_PAGE_SIZE)
        .limit(_SELECTOR_PAGE_SIZE)
    )
    res = await session.execute(stmt)
    branches = res.scalars().all()

    buttons = [
        [InlineKeyboardButton(text=_normalize_name(b.name), callback_data=f"sel:branch:{b.id}")]
        for b in branches
    ]
    _append_page_buttons(buttons, total, current_page, "branch")
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def dealer_selector(
    session: AsyncSession,
    page: int = 0,
    branch_id: int = None,
) -> InlineKeyboardMarkup:
    filters = [Dealer.is_active == True]
    if branch_id is not None:
        filters.append(Dealer.branch_id == branch_id)

    total_stmt = select(func.count(Dealer.id)).where(*filters)
    total = (await session.execute(total_stmt)).scalar_one() or 0
    if total == 0:
        buttons = [
            [InlineKeyboardButton(text="— Diler yo'q —", callback_data="sel:dealer:0")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    current_page = _clamp_page(page, total)
    stmt = (
        select(Dealer)
        .where(*filters)
        .order_by(Dealer.name.asc())
        .offset(current_page * _SELECTOR_PAGE_SIZE)
        .limit(_SELECTOR_PAGE_SIZE)
    )
    res = await session.execute(stmt)
    dealers = res.scalars().all()

    buttons = [
        [InlineKeyboardButton(text=_normalize_name(d.name), callback_data=f"sel:dealer:{d.id}")]
        for d in dealers
    ]
    _append_page_buttons(buttons, total, current_page, "dealer")
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def rate_plan_selector(session: AsyncSession, service_type: ServiceType) -> InlineKeyboardMarkup:
    stmt = (
        select(RatePlan)
        .where(RatePlan.service_type == service_type, RatePlan.is_active == True)
        .order_by(RatePlan.name.asc())
    )
    res = await session.execute(stmt)
    plans = res.scalars().all()

    buttons = [
        [InlineKeyboardButton(text=p.name, callback_data=f"sel:rateplan:{p.id}")]
        for p in plans
    ]
    if not buttons:
        buttons = [
            [InlineKeyboardButton(text="— Tarif yo'q —", callback_data="sel:rateplan:0")]
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def period_selector(session: AsyncSession) -> InlineKeyboardMarkup:
    stmt = select(ReportPeriod).order_by(ReportPeriod.year.desc(), ReportPeriod.month.desc())
    res = await session.execute(stmt)
    periods = res.scalars().all()

    buttons = [
        [InlineKeyboardButton(text=p.name, callback_data=f"sel:period:{p.id}")]
        for p in periods
    ]
    if not buttons:
        buttons = [
            [InlineKeyboardButton(text="— Davr yo'q —", callback_data="sel:period:0")]
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
