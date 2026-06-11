"""Chat sessiyasida bazadan raqam tanlash va operator yozuvini yangilash."""
import logging
import random
from typing import Any, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import ChatSession, InternetSale, ServiceType
from backend.services.manual_sale_service import create_manual_internet_sale
from backend.services.mapping_service import MappingService
from backend.services.simulation_helpers import sale_to_meta

logger = logging.getLogger(__name__)


def _pick(collected: dict, meta: dict, *keys: str) -> Optional[str]:
    for k in keys:
        if collected.get(k):
            return str(collected[k]).strip()
    for k in keys:
        if meta.get(k):
            return str(meta[k]).strip()
    if meta.get("msisdn"):
        return str(meta["msisdn"]).strip()
    if collected.get("confirm_login") and "rate_plan" in keys:
        return str(collected["confirm_login"]).strip()
    if meta.get("rate_plan"):
        return str(meta["rate_plan"]).strip()
    return None


async def ensure_msisdn_from_db(
    session: AsyncSession,
    collected_data: dict,
) -> dict:
    """Bazadan MSISDN olib _meta va collected_data ga qo'yadi (operator mijozga beradi)."""
    data = dict(collected_data or {})
    meta = dict(data.get("_meta") or {})
    if meta.get("msisdn"):
        data["msisdn"] = str(meta["msisdn"]).strip()
        data["_meta"] = meta
        return data

    res = await session.execute(select(InternetSale).order_by(func.random()).limit(1))
    sale = res.scalar()

    if sale:
        meta = {**sale_to_meta(sale, "internet"), **meta}
    else:
        meta.update(
            {
                "seeded": True,
                "msisdn": f"99890{random.randint(1000000, 9999999)}",
                "dealer": meta.get("dealer") or "Asosiy filial",
                "area": meta.get("area") or "Toshkent",
                "rate_plan": meta.get("rate_plan") or "Uy internet 100",
            }
        )

    data["_meta"] = meta
    data["msisdn"] = str(meta["msisdn"]).strip()
    return data


async def persist_wifi_sale_from_session(
    session: AsyncSession,
    chat_session: ChatSession,
    collected_data: dict,
    *,
    operator_tg_id: Optional[int] = None,
) -> bool:
    """
    Mijoz tasdiqlagan bazadagi raqam bo'yicha internet_sales yozuvini yangilash yoki yozish.
    """
    if not isinstance(collected_data, dict):
        return False
    data = collected_data
    meta = dict(data.get("_meta") or {})

    if meta.get("sale_persisted"):
        return False

    msisdn = _pick(data, meta, "msisdn")
    if not msisdn:
        return False

    dealer_name = _pick(data, meta, "dealer", "greeting", "ask_dealer")
    area_name = _pick(data, meta, "area", "ask_dealer", "ask_area")
    rate_name = _pick(data, meta, "rate_plan", "tariff", "confirm_login", "ask_tariff")

    tg_id = operator_tg_id or chat_session.operator_tg_id

    sale: InternetSale | None = None
    sale_id = meta.get("sale_id")
    if sale_id:
        res = await session.execute(
            select(InternetSale).where(InternetSale.id == int(sale_id))
        )
        sale = res.scalar_one_or_none()
    if not sale:
        res = await session.execute(
            select(InternetSale).where(InternetSale.msisdn == msisdn).limit(1)
        )
        sale = res.scalar_one_or_none()

    if sale:
        if area_name:
            sale.department_name_raw = area_name
        if tg_id:
            sale.operator_tg_id = tg_id
        if rate_name and not sale.rate_plan_id:
            mapper = MappingService(session)
            rp_id = await mapper.get_rate_plan_id(rate_name, ServiceType.INTERNET)
            if rp_id:
                sale.rate_plan_id = rp_id
                sale.rate_plan_raw = rate_name
        await session.commit()

        meta = dict(meta)
        meta["sale_persisted"] = True
        data["_meta"] = meta
        logger.info(
            "Sale updated from session %s: msisdn=%s sale_id=%s",
            chat_session.id,
            msisdn,
            sale.id,
        )
        return True

    mapper = MappingService(session)
    branch_id = await mapper.get_branch_id(dealer_name or area_name or "Filial")
    if not branch_id:
        return False

    rate_plan_id = None
    if rate_name:
        rate_plan_id = await mapper.get_rate_plan_id(rate_name, ServiceType.INTERNET)

    try:
        await create_manual_internet_sale(
            session,
            operator_tg_id=tg_id,
            branch_id=branch_id,
            department_name_raw=area_name or "",
            msisdn=msisdn,
            rate_plan_id=rate_plan_id,
        )
        meta = dict(meta)
        meta["sale_persisted"] = True
        data["_meta"] = meta
        logger.info(
            "Sale persisted from session %s: msisdn=%s branch_id=%s",
            chat_session.id,
            msisdn,
            branch_id,
        )
        return True
    except Exception as exc:
        logger.error("persist_wifi_sale_from_session failed: %s", exc, exc_info=True)
        return False
