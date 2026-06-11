from sqlalchemy.ext.asyncio import AsyncSession
from backend.repositories.application_repository import ApplicationRepository


class ApplicationService:
    def __init__(self, db: AsyncSession):
        self.repo = ApplicationRepository(db)

    async def create_internet(
        self,
        branches: str,
        departments: str,
        navi_user: str,
        rt_lc_states: str,
        msisdn: str,
        rate_plan_first_connection: str,
        selected_tariff_id: int = None,
        selected_tariff_code: str = None,
    ):
        return await self.repo.create_internet(
            branches,
            departments,
            navi_user,
            rt_lc_states,
            msisdn,
            rate_plan_first_connection,
            selected_tariff_id,
            selected_tariff_code,
        )

    async def create_mobile(
        self,
        dealer: str,
        navi_user: str,
        msisdn: str,
        rate_plan_first_connection: str,
        branches: str,
        selected_tariff_id: int = None,
        selected_tariff_code: str = None,
    ):
        return await self.repo.create_mobile(
            dealer,
            navi_user,
            msisdn,
            rate_plan_first_connection,
            branches,
            selected_tariff_id,
            selected_tariff_code,
        )
