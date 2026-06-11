from datetime import datetime
import re
from typing import Any
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Branch, Dealer, SalePoint, RatePlan, User, ReportPeriod, ServiceType
from backend.utils.logger import logger


def _normalize_name(value: Any) -> str:
    if value is None:
        return ""

    s = str(value)
    s = s.replace("\u00a0", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return s.strip()


class MappingService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._branch_cache: Dict[str, int] = {}
        self._dealer_cache: Dict[str, int] = {}
        self._sale_point_cache: Dict[str, int] = {}
        self._rate_plan_cache: Dict[str, int] = {}
        self._operator_cache: Dict[str, int] = {}
        self._period_cache: Dict[str, int] = {}

    async def get_branch_id(self, branch_name: str) -> Optional[int]:
        if not branch_name:
            return None
        name = _normalize_name(branch_name)
        if not name:
            return None
        if name in self._branch_cache:
            return self._branch_cache[name]

        stmt = select(Branch.id).where(Branch.name.ilike(f"{name}"))
        result = await self.session.execute(stmt)
        branch_id = result.scalar_one_or_none()

        if not branch_id:
            new_branch = Branch(name=name)
            self.session.add(new_branch)
            await self.session.flush()  # Commit on upper layer
            branch_id = new_branch.id

        self._branch_cache[name] = branch_id
        return branch_id

    async def get_dealer_id(self, branch_id: Optional[int], dealer_name: str) -> Optional[int]:
        if not dealer_name:
            return None
        name = _normalize_name(dealer_name)
        if not name:
            return None
        cache_key = f"{branch_id}_{name}"
        if cache_key in self._dealer_cache:
            return self._dealer_cache[cache_key]

        stmt = select(Dealer.id).where(Dealer.branch_id == branch_id, Dealer.name.ilike(f"{name}"))
        result = await self.session.execute(stmt)
        dealer_id = result.scalar_one_or_none()

        if not dealer_id:
            new_dealer = Dealer(branch_id=branch_id, name=name)
            self.session.add(new_dealer)
            await self.session.flush()
            dealer_id = new_dealer.id

        self._dealer_cache[cache_key] = dealer_id
        return dealer_id

    async def get_sale_point_id(self, dealer_id: Optional[int], sp_name: str) -> Optional[int]:
        if not sp_name:
            return None
        name = _normalize_name(sp_name)
        if not name:
            return None
        cache_key = f"{dealer_id}_{name}"
        if cache_key in self._sale_point_cache:
            return self._sale_point_cache[cache_key]

        stmt = select(SalePoint.id).where(
            SalePoint.dealer_id == dealer_id,
            SalePoint.name.ilike(f"{name}"),
        )
        result = await self.session.execute(stmt)
        sp_id = result.scalar_one_or_none()

        if not sp_id:
            new_sp = SalePoint(dealer_id=dealer_id, name=name)
            self.session.add(new_sp)
            await self.session.flush()
            sp_id = new_sp.id

        self._sale_point_cache[cache_key] = sp_id
        return sp_id

    async def get_rate_plan_id(self, rp_name: str, service_type: ServiceType) -> Optional[int]:
        if not rp_name:
            return None
        name = _normalize_name(rp_name)
        if not name:
            return None
        cache_key = f"{service_type}_{name}"
        if cache_key in self._rate_plan_cache:
            return self._rate_plan_cache[cache_key]

        stmt = select(RatePlan.id).where(
            RatePlan.name.ilike(f"{name}"),
            RatePlan.service_type == service_type,
        )
        result = await self.session.execute(stmt)
        rp_id = result.scalar_one_or_none()

        if not rp_id:
            new_rp = RatePlan(name=name, service_type=service_type)
            self.session.add(new_rp)
            await self.session.flush()
            rp_id = new_rp.id

        self._rate_plan_cache[cache_key] = rp_id
        return rp_id

    async def get_operator_tg_id(self, navi_username: str) -> Optional[int]:
        if not navi_username:
            return None
        name = _normalize_name(navi_username).lstrip("@")
        if not name:
            return None
        if name in self._operator_cache:
            return self._operator_cache[name]

        stmt = select(User.tg_id).where(User.navi_username.ilike(f"{name}"))
        result = await self.session.execute(stmt)
        tg_id = result.scalar_one_or_none()

        if tg_id:
            self._operator_cache[name] = tg_id
        return tg_id

    async def get_report_period_id(self, year: Optional[int], month: Optional[int], name: str) -> Optional[int]:
        if not year or not month:
            now = datetime.now()
            year = year or now.year
            month = month or now.month

        cache_key = f"{year}_{month}"
        if cache_key in self._period_cache:
            return self._period_cache[cache_key]

        stmt = select(ReportPeriod.id).where(ReportPeriod.year == year, ReportPeriod.month == month)
        result = await self.session.execute(stmt)
        p_id = result.scalar_one_or_none()

        if not p_id:
            new_period = ReportPeriod(year=year, month=month, name=name)
            self.session.add(new_period)
            await self.session.flush()
            p_id = new_period.id

        self._period_cache[cache_key] = p_id
        return p_id
