"""Qo'lda sotuv — joriy oy Excel formatidagi ustunlar bilan bir xil."""
from datetime import datetime, timezone
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import (
    Branch,
    Dealer,
    InternetSale,
    MobileSale,
    RatePlan,
    ReportPeriod,
    SaleSource,
    SaleStatus,
    User,
)


async def get_or_create_current_period_id(session: AsyncSession) -> int:
    now = datetime.now()
    y, m = now.year, now.month
    stmt = select(ReportPeriod.id).where(ReportPeriod.year == y, ReportPeriod.month == m)
    period_id = (await session.execute(stmt)).scalar_one_or_none()
    if period_id:
        return period_id
    months_uz = [
        "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
        "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr",
    ]
    period = ReportPeriod(year=y, month=m, name=f"{y} - {months_uz[m - 1]}")
    session.add(period)
    await session.flush()
    return period.id


async def _navi_user_for_operator(session: AsyncSession, tg_id: int) -> str:
    row = (
        await session.execute(
            select(User.navi_username, User.username).where(User.tg_id == tg_id)
        )
    ).first()
    if row and row.navi_username:
        value = _normalize_text(row.navi_username)
        return value
    if row and row.username:
        return _normalize_text(row.username).lstrip("@")
    return str(tg_id)


async def _name_by_id(session: AsyncSession, model, obj_id: int | None) -> str | None:
    if not obj_id:
        return None
    obj = await session.get(model, obj_id)
    return obj.name if obj else None


async def create_manual_internet_sale(
    session: AsyncSession,
    *,
    operator_tg_id: int | None,
    branch_id: int,
    department_name_raw: str,
    msisdn: str,
    rate_plan_id: int | None,
    rt_lc_state: str = "active",
) -> InternetSale:
    """internet: filial, bo'lim, msisdn, tarif + navi_user, holat."""
    period_id = await get_or_create_current_period_id(session)
    navi = "AUTO_CHAT"
    if operator_tg_id:
        navi = await _navi_user_for_operator(session, operator_tg_id)
    branch_name = await _name_by_id(session, Branch, branch_id)
    rate_name = await _name_by_id(session, RatePlan, rate_plan_id)
    branch_name = _normalize_text(branch_name)
    rate_name = _normalize_text(rate_name)
    now = datetime.now(timezone.utc)

    sale = InternetSale(
        period_id=period_id,
        branch_id=branch_id,
        branch_name_raw=branch_name,
        department_name_raw=_normalize_text(department_name_raw),
        rate_plan_id=rate_plan_id,
        rate_plan_raw=rate_name,
        operator_tg_id=operator_tg_id,
        msisdn=_normalize_text(msisdn),
        navi_user=_normalize_text(navi),
        rt_lc_state=rt_lc_state,
        sale_amount=0,
        confirmed_at=now,
        source=SaleSource.MANUAL,
        status=SaleStatus.CONFIRMED,
    )
    session.add(sale)
    await session.commit()
    return sale


async def create_manual_mobile_sale(
    session: AsyncSession,
    *,
    operator_tg_id: int,
    dealer_id: int,
    branch_id: int,
    msisdn: str,
    rate_plan_id: int | None,
) -> MobileSale:
    """mobil: diler, msisdn, tarif, filial + navi_user."""
    period_id = await get_or_create_current_period_id(session)
    navi = await _navi_user_for_operator(session, operator_tg_id)
    branch_name = await _name_by_id(session, Branch, branch_id)
    dealer_name = await _name_by_id(session, Dealer, dealer_id)
    rate_name = await _name_by_id(session, RatePlan, rate_plan_id)
    branch_name = _normalize_text(branch_name)
    dealer_name = _normalize_text(dealer_name)
    rate_name = _normalize_text(rate_name)
    now = datetime.now(timezone.utc)

    sale = MobileSale(
        period_id=period_id,
        dealer_id=dealer_id,
        dealer_name_raw=dealer_name,
        branch_id=branch_id,
        branch_name_raw=branch_name,
        rate_plan_id=rate_plan_id,
        rate_plan_raw=rate_name,
        operator_tg_id=operator_tg_id,
        msisdn=_normalize_text(msisdn),
        navi_user=_normalize_text(navi),
        charged_amount=0,
        confirmed_at=now,
        source=SaleSource.MANUAL,
        status=SaleStatus.CONFIRMED,
    )
    session.add(sale)
    await session.commit()
    return sale


def _normalize_text(value: object) -> str:
    if value is None:
        return ""
    s = str(value).replace("\u00a0", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return s.strip()
