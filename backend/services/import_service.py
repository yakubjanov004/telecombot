"""Excel import service for the real source workbooks under assets/excel."""
from pathlib import Path
import re
from typing import Any

from backend.models import (
    ImportBatch,
    InternetSale,
    MobileSale,
    SaleSource,
    SaleStatus,
    ServiceType,
)
from backend.services.mapping_service import MappingService
from backend.utils.excel_reader import ExcelReader, detect_service_type_by_headers
from backend.utils.logger import logger


MONTHS_UZ = [
    "Yanvar",
    "Fevral",
    "Mart",
    "Aprel",
    "May",
    "Iyun",
    "Iyul",
    "Avgust",
    "Sentabr",
    "Oktabr",
    "Noyabr",
    "Dekabr",
]


def _clean_str(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).replace("\u00a0", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return s or None


def _row_has(row: dict, key: str) -> bool:
    return key in row and row[key] is not None and str(row[key]).strip() != ""


def _to_int_amount(val: Any) -> int:
    if val is None:
        return 0
    try:
        if isinstance(val, str):
            val = val.replace(" ", "").replace(",", ".")
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _to_int_optional(val: Any) -> int | None:
    if val is None:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _extract_navi_user(row: dict[str, Any]) -> str:
    for key in [
        "NAVI_USER",
        "NAVI_USERNAME",
        "USER",
        "OPERATOR",
        "NAVI USER",
        "NAVIUSER",
        "NAVIUSERNAME",
    ]:
        value = _clean_str(row.get(key))
        if value:
            value = value.lstrip("@")
            return value

    for key, value in row.items():
        if not isinstance(key, str):
            continue
        k = key.upper().replace(" ", "_")
        if "NAVI" in k and ("USER" in k or "OPERATOR" in k or "USERNAME" in k):
            text = _clean_str(value)
            if text:
                text = text.lstrip("@")
                return text

    return "unknown"


class ImportService:
    def __init__(self, session):
        self.session = session
        self.mapper = MappingService(session)

    async def import_from_file(
        self,
        file_path: str,
        default_year: int | None = None,
        default_month: int | None = None,
        clear_existing: bool = True,
        cleared_period_services: set[tuple[int, ServiceType]] | None = None,
    ) -> None:
        path = Path(file_path)
        reader = ExcelReader(path)
        sheets = reader.get_sheets()
        if not sheets:
            logger.warning("No sheets in %s", file_path)
            return

        file_period_hint = reader.extract_period(path.stem)
        cleared_period_st = cleared_period_services if cleared_period_services is not None else set()

        for sheet_name in sheets:
            rows = list(reader.read_sheet(sheet_name))
            if not rows:
                continue

            headers = list(rows[0].keys())
            service_type = detect_service_type_by_headers(headers)
            if service_type == "unknown":
                logger.warning("Skip sheet %s - unknown type", sheet_name)
                continue

            st = ServiceType.INTERNET if service_type == "internet" else ServiceType.MOBILE
            sheet_period_hint = reader.extract_period(sheet_name)
            year, month = self._resolve_period(
                file_period_hint=file_period_hint,
                sheet_period_hint=sheet_period_hint,
                default_year=default_year,
                default_month=default_month,
            )
            period_name = (
                f"{year} - {MONTHS_UZ[month - 1]}" if year and month else path.stem
            )
            period_id = await self.mapper.get_report_period_id(year, month, period_name)
            if not period_id:
                logger.warning("Skip sheet %s - period not resolved", sheet_name)
                continue

            period_st_key = (period_id, st)
            if clear_existing and period_st_key not in cleared_period_st:
                from sqlalchemy import delete

                if st == ServiceType.INTERNET:
                    await self.session.execute(
                        delete(InternetSale).where(InternetSale.period_id == period_id)
                    )
                else:
                    await self.session.execute(
                        delete(MobileSale).where(MobileSale.period_id == period_id)
                    )
                await self.session.execute(
                    delete(ImportBatch).where(
                        ImportBatch.period_id == period_id,
                        ImportBatch.service_type == st,
                    )
                )
                await self.session.flush()
                cleared_period_st.add(period_st_key)

            batch = ImportBatch(
                service_type=st,
                period_id=period_id,
                file_name=path.name,
                sheet_name=sheet_name,
                source=SaleSource.EXCEL_IMPORT,
                rows_total=len(rows),
            )
            self.session.add(batch)
            await self.session.flush()

            ok = 0
            for row in rows:
                try:
                    if service_type == "internet":
                        await self._import_internet_row(row, period_id, batch.id)
                    else:
                        await self._import_mobile_row(row, period_id, batch.id)
                    ok += 1
                except Exception as exc:
                    logger.error("Row %s import failed: %s", row.get("ROW_NUMBER"), exc)

            batch.rows_success = ok
            batch.rows_failed = len(rows) - ok
            await self.session.commit()

    def _resolve_period(
        self,
        file_period_hint: dict,
        sheet_period_hint: dict,
        default_year: int | None,
        default_month: int | None,
    ) -> tuple[int | None, int | None]:
        sheet_month = sheet_period_hint.get("month")
        file_month = file_period_hint.get("month")
        month = sheet_month or file_month or default_month
        year = (
            sheet_period_hint.get("year")
            or file_period_hint.get("year")
            or default_year
        )

        if (
            sheet_month
            and not sheet_period_hint.get("year")
            and not file_period_hint.get("year")
            and default_year
            and default_month
            and sheet_month > default_month
        ):
            year = default_year - 1

        return year, month

    async def _import_internet_row(self, row: dict, period_id: int, batch_id: int) -> None:
        branch_raw = _clean_str(row.get("BRANCHES"))
        branch_id = await self.mapper.get_branch_id(branch_raw) if branch_raw else None
        rp_raw = _clean_str(row.get("RATE_PLAN"))
        rp_id = (
            await self.mapper.get_rate_plan_id(rp_raw, ServiceType.INTERNET) if rp_raw else None
        )
        navi = _extract_navi_user(row)

        sale = InternetSale(
            import_batch_id=batch_id,
            period_id=period_id,
            branch_id=branch_id,
            branch_name_raw=branch_raw,
            department_name_raw=_clean_str(row.get("DEPARTMENTS")),
            navi_user=navi,
            rt_lc_state=_clean_str(row.get("RT_LC_STATES")) or "active",
            msisdn=_clean_str(row.get("MSISDN")) or "",
            rate_plan_id=rp_id,
            rate_plan_raw=rp_raw,
            row_number=row.get("ROW_NUMBER"),
            operator_tg_id=await self.mapper.get_operator_tg_id(navi),
            source=SaleSource.EXCEL_IMPORT,
            status=SaleStatus.CONFIRMED,
            sale_amount=0,
        )

        if _row_has(row, "DEALER"):
            dealer_raw = _clean_str(row.get("DEALER"))
            sale.dealer_id = await self.mapper.get_dealer_id(branch_id, dealer_raw)
            sale.dealer_name_raw = dealer_raw
        if _row_has(row, "STANDARD_TYPE"):
            sale.standard_type = _clean_str(row.get("STANDARD_TYPE"))
        if _row_has(row, "AMOUNT"):
            sale.sale_amount = _to_int_amount(row.get("AMOUNT"))
        if _row_has(row, "QUANTITY"):
            sale.sale_quantity = _to_int_optional(row.get("QUANTITY"))
        if row.get("ACTIVATION_DATE"):
            sale.activation_date = row.get("ACTIVATION_DATE")

        self.session.add(sale)

    async def _import_mobile_row(self, row: dict, period_id: int, batch_id: int) -> None:
        branch_raw = _clean_str(row.get("BRANCHES"))
        dealer_raw = _clean_str(row.get("DEALER"))
        branch_id = await self.mapper.get_branch_id(branch_raw) if branch_raw else None
        dealer_id = (
            await self.mapper.get_dealer_id(branch_id, dealer_raw) if dealer_raw else None
        )
        rp_raw = _clean_str(row.get("RATE_PLAN"))
        rp_id = (
            await self.mapper.get_rate_plan_id(rp_raw, ServiceType.MOBILE) if rp_raw else None
        )
        navi = _extract_navi_user(row)

        sale = MobileSale(
            import_batch_id=batch_id,
            period_id=period_id,
            branch_id=branch_id,
            branch_name_raw=branch_raw,
            dealer_id=dealer_id,
            dealer_name_raw=dealer_raw,
            navi_user=navi,
            msisdn=_clean_str(row.get("MSISDN")) or "",
            rate_plan_id=rp_id,
            rate_plan_raw=rp_raw,
            row_number=row.get("ROW_NUMBER"),
            operator_tg_id=await self.mapper.get_operator_tg_id(navi),
            source=SaleSource.EXCEL_IMPORT,
            status=SaleStatus.CONFIRMED,
            charged_amount=0,
        )

        if _row_has(row, "SALE_POINT"):
            sp_raw = _clean_str(row.get("SALE_POINT"))
            sale.sale_point_id = await self.mapper.get_sale_point_id(dealer_id, sp_raw)
            sale.sale_point_name_raw = sp_raw
        if _row_has(row, "RT_LC_STATES"):
            sale.rt_lc_state = _clean_str(row.get("RT_LC_STATES"))
        if _row_has(row, "AMOUNT"):
            sale.charged_amount = _to_int_amount(row.get("AMOUNT"))
        if _row_has(row, "QUANTITY"):
            sale.sale_quantity = _to_int_optional(row.get("QUANTITY"))
        if row.get("ACTIVATION_DATE"):
            sale.activation_date = row.get("ACTIVATION_DATE")

        self.session.add(sale)
