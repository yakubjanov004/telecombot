from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import re
from backend.models import InternetApplication, MobileApplication, StatusEnum


def _operator_code_from_msisdn(msisdn: str) -> str:
    digits = re.sub(r"\D+", "", msisdn or "")
    if digits.startswith("998") and len(digits) >= 5:
        return digits[3:5]
    if len(digits) >= 2:
        return digits[:2]
    return "00"


def _clean(value: str | None) -> str:
    return (value or "").strip()


class ApplicationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_internet(
        self,
        branches: str | None,
        departments: str | None,
        navi_user: str | None,
        rt_lc_states: str | None,
        msisdn: str | None,
        rate_plan_first_connection: str | None,
        selected_tariff_id: int = None,
        selected_tariff_code: str = None,
    ) -> InternetApplication:
        branches = _clean(branches)
        departments = _clean(departments)
        navi_user = _clean(navi_user)
        rt_lc_states = _clean(rt_lc_states) or "active"
        msisdn = _clean(msisdn)
        rate_plan_first_connection = _clean(rate_plan_first_connection)
        rate_plan = selected_tariff_code or rate_plan_first_connection
        app = InternetApplication(
            city=branches or "Operator belgilaydi",
            first_name=navi_user or "Client",
            last_name=departments or "Operator belgilaydi",
            father_name=msisdn or "Operator belgilaydi",
            phone=msisdn or None,
            selected_tariff_id=selected_tariff_id,
            selected_tariff_code=rate_plan,
            address=departments,
            branches=branches,
            departments=departments,
            navi_user=navi_user,
            rt_lc_states=rt_lc_states,
            msisdn=msisdn,
            rate_plan_first_connection=rate_plan_first_connection,
            status=StatusEnum.NEW
        )
        self.db.add(app)
        await self.db.commit()
        await self.db.refresh(app)
        return app

    async def create_mobile(
        self,
        dealer: str | None,
        navi_user: str | None,
        msisdn: str,
        rate_plan_first_connection: str | None,
        branches: str | None,
        selected_tariff_id: int = None,
        selected_tariff_code: str = None,
    ) -> MobileApplication:
        dealer = _clean(dealer)
        navi_user = _clean(navi_user)
        msisdn = _clean(msisdn)
        rate_plan_first_connection = _clean(rate_plan_first_connection)
        branches = _clean(branches)
        rate_plan = selected_tariff_code or rate_plan_first_connection
        app = MobileApplication(
            phone=msisdn,
            operator_code=_operator_code_from_msisdn(msisdn),
            first_name=navi_user or "Client",
            last_name=dealer or "Operator belgilaydi",
            father_name=branches or "Operator belgilaydi",
            selected_tariff_id=selected_tariff_id,
            selected_tariff_code=rate_plan,
            address=branches,
            dealer=dealer,
            navi_user=navi_user,
            msisdn=msisdn,
            rate_plan_first_connection=rate_plan_first_connection,
            branches=branches,
            status=StatusEnum.NEW
        )
        self.db.add(app)
        await self.db.commit()
        await self.db.refresh(app)
        return app
