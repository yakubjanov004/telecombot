from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from sqlalchemy import delete, func, select
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from backend.migrations import migrate_schema
from backend.models import Base, ImportBatch, InternetSale, MobileSale, ReportPeriod, SaleSource, ServiceType
from backend.services.import_service import ImportService
from backend.utils.excel_reader import ExcelReader, MONTH_MAP, detect_service_type_by_headers

DEFAULT_EXCEL_ROOT = PROJECT_ROOT / "assets" / "excel"
POSTGRES_DB_KEYS = ("POSTGRES_DB", "DB_NAME", "PGDATABASE")


@dataclass(frozen=True)
class DirectoryDefaults:
    year: int
    month: int | None
    anchor_month: int | None
    wraps_year: bool


@dataclass
class SheetPlan:
    sheet_name: str
    service_type: ServiceType
    year: int
    month: int
    rows: int


@dataclass
class FilePlan:
    path: Path
    file_hash: str
    default_year: int
    default_month: int | None
    sheets: list[SheetPlan] = field(default_factory=list)


def _load_env_values() -> dict[str, str]:
    env_values: dict[str, Any] = {}
    for env_name in (".env.example", ".env"):
        env_path = PROJECT_ROOT / env_name
        if env_path.exists():
            env_values.update({k: v for k, v in dotenv_values(env_path).items() if v is not None})

    env_values.update({k: v for k, v in os.environ.items() if v is not None})
    return {str(k): str(v) for k, v in env_values.items()}


def _env_first(env_values: dict[str, str], *keys: str, default: str | None = None) -> str | None:
    for key in keys:
        value = env_values.get(key)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default


def _postgres_url_from_parts(env_values: dict[str, str]) -> str | None:
    db_name = _env_first(env_values, *POSTGRES_DB_KEYS)
    if not db_name:
        return None

    port = _env_first(env_values, "POSTGRES_PORT", "PGPORT", default="5432")
    return URL.create(
        "postgresql+asyncpg",
        username=_env_first(env_values, "POSTGRES_USER", "PGUSER", default="postgres"),
        password=_env_first(env_values, "POSTGRES_PASSWORD", "PGPASSWORD"),
        host=_env_first(env_values, "POSTGRES_HOST", "PGHOST", default="localhost"),
        port=int(port or "5432"),
        database=db_name,
    ).render_as_string(hide_password=False)


def _normalize_database_url(raw: str) -> str:
    raw = str(raw).strip()

    if raw.startswith("postgresql://"):
        raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)

    url = make_url(raw)
    if not url.drivername.startswith("postgresql"):
        raise RuntimeError(
            "DATABASE_URL must point to PostgreSQL. Set DATABASE_URL to "
            "postgresql+asyncpg://user:password@host:5432/database_name "
            "or set POSTGRES_DB/POSTGRES_USER/POSTGRES_PASSWORD in .env."
        )
    return url.render_as_string(hide_password=False)


def _load_database_url(override_url: str | None = None) -> str:
    env_values = _load_env_values()
    raw = override_url or _env_first(env_values, "DATABASE_URL")
    parts_url = _postgres_url_from_parts(env_values)

    if raw:
        return _normalize_database_url(raw)

    if parts_url:
        return _normalize_database_url(parts_url)

    raise RuntimeError(
        "PostgreSQL config not found. Add DATABASE_URL or POSTGRES_DB settings to .env."
    )


def _public_database_name(database_url: str) -> str:
    url = make_url(database_url)
    return f"{url.drivername}://{url.host or 'localhost'}/{url.database}"


async def _ensure_postgres_database(url: URL) -> None:
    try:
        import asyncpg
    except ImportError as exc:
        raise RuntimeError("asyncpg is required to create PostgreSQL databases") from exc

    db_name = url.database
    if not db_name:
        raise RuntimeError("PostgreSQL DATABASE_URL has no database name")

    env_values = _load_env_values()
    maintenance_db = _env_first(env_values, "POSTGRES_MAINTENANCE_DB", default="postgres")
    conn = await asyncpg.connect(
        user=url.username,
        password=url.password,
        host=url.host or "localhost",
        port=url.port or 5432,
        database=maintenance_db,
    )
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if not exists:
            safe_name = '"' + db_name.replace('"', '""') + '"'
            await conn.execute(f"CREATE DATABASE {safe_name}")
            print(f"Created PostgreSQL database: {db_name}")
    finally:
        await conn.close()


async def ensure_database_exists(database_url: str) -> None:
    url = make_url(database_url)
    if not url.drivername.startswith("postgresql"):
        raise RuntimeError("This setup script is PostgreSQL-only.")
    await _ensure_postgres_database(url)


def create_session_factory(database_url: str) -> tuple[Any, sessionmaker]:
    engine = create_async_engine(database_url, echo=False)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory


async def create_schema(engine: Any) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(migrate_schema)


def decode_hash_u_name(value: str) -> str:
    return re.sub(
        r"#U([0-9a-fA-F]{4})",
        lambda match: chr(int(match.group(1), 16)),
        value,
    )


def strip_excel_suffixes(name: str) -> str:
    result = decode_hash_u_name(name)
    lowered = result.lower()
    changed = True
    while changed:
        changed = False
        for suffix in (".xlsx", ".xlsm", ".xls", ".dec"):
            if lowered.endswith(suffix):
                result = result[: -len(suffix)]
                lowered = result.lower()
                changed = True
                break
    return result.strip()


def _tokens(value: str) -> list[str]:
    clean = strip_excel_suffixes(value).lower()
    return re.findall(r"[^\W\d_]+", clean, flags=re.UNICODE)


def month_candidates(value: str) -> list[int]:
    found: list[int] = []
    seen: set[int] = set()
    for token in _tokens(value):
        month = MONTH_MAP.get(token)
        if month and month not in seen:
            found.append(month)
            seen.add(month)
    return found


def extract_year(value: str) -> int | None:
    match = re.search(r"20[0-9]{2}", value)
    return int(match.group(0)) if match else None


def directory_defaults(directory: Path, fallback_year: int) -> DirectoryDefaults:
    months = month_candidates(directory.name)
    year = extract_year(directory.name) or fallback_year
    unique_months = list(dict.fromkeys(months))
    wraps_year = 12 in unique_months and 1 in unique_months

    if len(unique_months) == 1:
        month = unique_months[0]
        anchor = month
    elif wraps_year:
        month = None
        anchor = min(unique_months)
    else:
        month = None
        anchor = None

    return DirectoryDefaults(year=year, month=month, anchor_month=anchor, wraps_year=wraps_year)


def file_defaults(path: Path, defaults: DirectoryDefaults) -> tuple[int, int | None]:
    file_months = month_candidates(path.name)
    file_year = extract_year(path.name)
    year = file_year or defaults.year

    if len(file_months) == 1:
        month = file_months[0]
        if defaults.wraps_year and not file_year and defaults.anchor_month and month > defaults.anchor_month:
            year -= 1
        return year, month

    if defaults.wraps_year:
        return year, defaults.anchor_month

    return year, defaults.month


def resolve_period(
    file_period_hint: dict[str, int | None],
    sheet_period_hint: dict[str, int | None],
    default_year: int | None,
    default_month: int | None,
) -> tuple[int | None, int | None]:
    sheet_month = sheet_period_hint.get("month")
    file_month = file_period_hint.get("month")
    month = sheet_month or file_month or default_month
    year = sheet_period_hint.get("year") or file_period_hint.get("year") or default_year

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


def logical_file_key(excel_root: Path, path: Path) -> tuple[str, str]:
    parent = str(path.parent.relative_to(excel_root)).lower()
    base = strip_excel_suffixes(path.name).lower()
    base = re.sub(r"\s+", " ", base)
    return parent, base


def file_preference(path: Path) -> tuple[int, int, int, str]:
    name = path.name
    lowered = name.lower()
    decrypted_rank = 0 if ".dec." in lowered or lowered.endswith(".dec.xlsx") else 1
    readable_rank = 0 if "#u" not in lowered else 1
    return decrypted_rank, readable_rank, len(name), str(path).lower()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _has_matching_decrypted_file(path: Path, all_files: list[Path], excel_root: Path) -> bool:
    key = logical_file_key(excel_root, path)
    for candidate in all_files:
        if candidate == path:
            continue
        lowered = candidate.name.lower()
        if ".dec." not in lowered and not lowered.endswith(".dec.xlsx"):
            continue
        if logical_file_key(excel_root, candidate) == key:
            return True
    return False


def auto_decrypt_directories(directories: list[Path]) -> None:
    try:
        import io
        import msoffcrypto
    except ImportError:
        print("msoffcrypto-tool is not installed; encrypted files will be used only if .dec.xlsx exists.")
        return

    for directory in directories:
        password_path = directory / "password.txt"
        if not password_path.exists():
            continue
        password = password_path.read_text(encoding="utf-8").strip()
        if not password:
            continue

        all_files = [p for p in directory.glob("*.xlsx") if not p.name.startswith("~$")]
        for path in all_files:
            lowered = path.name.lower()
            if ".dec." in lowered or lowered.endswith(".dec.xlsx"):
                continue
            if _has_matching_decrypted_file(path, all_files, directory.parent):
                continue

            target = path.with_name(f"{path.name}.dec.xlsx")
            try:
                with path.open("rb") as fh:
                    office_file = msoffcrypto.OfficeFile(fh)
                    if not office_file.is_encrypted():
                        continue
                    office_file.load_key(password=password)
                    decrypted = io.BytesIO()
                    office_file.decrypt(decrypted)
                target.write_bytes(decrypted.getvalue())
                print(f"Decrypted: {path} -> {target.name}")
            except Exception as exc:
                print(f"Decrypt skipped for {path.name}: {exc}")


def discover_directories(excel_root: Path, latest_only: bool) -> list[Path]:
    if not excel_root.exists():
        raise FileNotFoundError(f"Excel root not found: {excel_root}")

    directories = [
        p
        for p in sorted(excel_root.iterdir(), key=lambda item: item.name.lower())
        if p.is_dir() and any(f.suffix.lower() == ".xlsx" for f in p.iterdir())
    ]
    if not directories and any(f.suffix.lower() == ".xlsx" for f in excel_root.iterdir()):
        directories = [excel_root]

    if latest_only and directories:
        directories = [
            max(
                directories,
                key=lambda directory: max(
                    (f.stat().st_mtime for f in directory.glob("*.xlsx")),
                    default=directory.stat().st_mtime,
                ),
            )
        ]

    return directories


def select_excel_files(excel_root: Path, directories: list[Path]) -> list[Path]:
    grouped: dict[tuple[str, str], Path] = {}
    for directory in directories:
        for path in sorted(directory.glob("*.xlsx"), key=lambda item: item.name.lower()):
            if path.name.startswith("~$"):
                continue
            key = logical_file_key(excel_root, path)
            existing = grouped.get(key)
            if existing is None or file_preference(path) < file_preference(existing):
                grouped[key] = path

    selected: list[Path] = []
    seen_hashes: set[str] = set()
    for path in sorted(grouped.values(), key=lambda item: str(item).lower()):
        file_hash = sha256_file(path)
        if file_hash in seen_hashes:
            continue
        seen_hashes.add(file_hash)
        selected.append(path)

    return selected


def build_file_plan(path: Path, defaults: DirectoryDefaults) -> FilePlan:
    default_year, default_month = file_defaults(path, defaults)
    reader = ExcelReader(path)
    file_hash = sha256_file(path)
    file_period_hint = reader.extract_period(strip_excel_suffixes(path.name))
    plan = FilePlan(
        path=path,
        file_hash=file_hash,
        default_year=default_year,
        default_month=default_month,
    )

    for sheet_name in reader.get_sheets():
        rows = list(reader.read_sheet(sheet_name))
        if not rows:
            continue

        service_name = detect_service_type_by_headers(list(rows[0].keys()))
        if service_name == "unknown":
            print(f"Skip unknown sheet: {path.name} / {sheet_name}")
            continue

        service_type = ServiceType.INTERNET if service_name == "internet" else ServiceType.MOBILE
        year, month = resolve_period(
            file_period_hint=file_period_hint,
            sheet_period_hint=reader.extract_period(sheet_name),
            default_year=default_year,
            default_month=default_month,
        )
        if not year or not month:
            print(f"Skip sheet without period: {path.name} / {sheet_name}")
            continue

        plan.sheets.append(
            SheetPlan(
                sheet_name=sheet_name,
                service_type=service_type,
                year=year,
                month=month,
                rows=len(rows),
            )
        )

    return plan


def build_import_plan(excel_root: Path, directories: list[Path], fallback_year: int) -> list[FilePlan]:
    defaults_by_directory = {
        directory: directory_defaults(directory, fallback_year) for directory in directories
    }
    selected_files = select_excel_files(excel_root, directories)
    plans: list[FilePlan] = []
    for path in selected_files:
        defaults = defaults_by_directory.get(path.parent) or directory_defaults(path.parent, fallback_year)
        plan = build_file_plan(path, defaults)
        if plan.sheets:
            plans.append(plan)
    return plans


def expected_counts(plans: list[FilePlan]) -> Counter[tuple[int, int, ServiceType]]:
    counts: Counter[tuple[int, int, ServiceType]] = Counter()
    for plan in plans:
        for sheet in plan.sheets:
            counts[(sheet.year, sheet.month, sheet.service_type)] += sheet.rows
    return counts


async def import_plans(session_factory: sessionmaker, plans: list[FilePlan]) -> None:
    cleared_period_services: set[tuple[int, ServiceType]] = set()
    async with session_factory() as session:
        importer = ImportService(session)
        for plan in plans:
            print(
                "Importing "
                f"{plan.path.relative_to(PROJECT_ROOT)} "
                f"(default={plan.default_year}/{plan.default_month or 'auto'})"
            )
            await importer.import_from_file(
                str(plan.path),
                default_year=plan.default_year,
                default_month=plan.default_month,
                clear_existing=True,
                cleared_period_services=cleared_period_services,
            )


async def clear_excel_imports(session_factory: sessionmaker) -> None:
    async with session_factory() as session:
        await session.execute(delete(InternetSale).where(InternetSale.source == SaleSource.EXCEL_IMPORT))
        await session.execute(delete(MobileSale).where(MobileSale.source == SaleSource.EXCEL_IMPORT))
        await session.execute(delete(ImportBatch).where(ImportBatch.source == SaleSource.EXCEL_IMPORT))
        await session.commit()


async def actual_counts(
    session_factory: sessionmaker,
    expected: Counter[tuple[int, int, ServiceType]],
) -> Counter[tuple[int, int, ServiceType]]:
    result: Counter[tuple[int, int, ServiceType]] = Counter()
    periods = {(year, month) for year, month, _service_type in expected.keys()}

    async with session_factory() as session:
        for year, month in sorted(periods):
            period_id = await session.scalar(
                select(ReportPeriod.id).where(
                    ReportPeriod.year == year,
                    ReportPeriod.month == month,
                )
            )
            if not period_id:
                continue

            internet_count = await session.scalar(
                select(func.count(InternetSale.id)).where(InternetSale.period_id == period_id)
            )
            mobile_count = await session.scalar(
                select(func.count(MobileSale.id)).where(MobileSale.period_id == period_id)
            )
            result[(year, month, ServiceType.INTERNET)] = int(internet_count or 0)
            result[(year, month, ServiceType.MOBILE)] = int(mobile_count or 0)

    return result


async def validate_required_fields(
    session_factory: sessionmaker,
    expected: Counter[tuple[int, int, ServiceType]],
) -> list[str]:
    errors: list[str] = []
    periods = {(year, month) for year, month, _service_type in expected.keys()}

    async with session_factory() as session:
        for year, month in sorted(periods):
            period_id = await session.scalar(
                select(ReportPeriod.id).where(
                    ReportPeriod.year == year,
                    ReportPeriod.month == month,
                )
            )
            if not period_id:
                errors.append(f"{year}-{month:02d}: report period not found")
                continue

            internet_missing = await session.scalar(
                select(func.count(InternetSale.id)).where(
                    InternetSale.period_id == period_id,
                    ((InternetSale.msisdn == "") | (InternetSale.navi_user == "")),
                )
            )
            mobile_missing = await session.scalar(
                select(func.count(MobileSale.id)).where(
                    MobileSale.period_id == period_id,
                    ((MobileSale.msisdn == "") | (MobileSale.navi_user == "")),
                )
            )
            if internet_missing:
                errors.append(f"{year}-{month:02d}: internet rows with empty msisdn/navi={internet_missing}")
            if mobile_missing:
                errors.append(f"{year}-{month:02d}: mobile rows with empty msisdn/navi={mobile_missing}")

    return errors


def print_plan(plans: list[FilePlan]) -> None:
    print("Selected Excel files:")
    for plan in plans:
        print(f"  - {plan.path.relative_to(PROJECT_ROOT)}")
        for sheet in plan.sheets:
            print(
                "      "
                f"{sheet.sheet_name}: {sheet.service_type.value} "
                f"{sheet.year}-{sheet.month:02d}, rows={sheet.rows}"
            )


def print_counts(title: str, counts: Counter[tuple[int, int, ServiceType]]) -> None:
    print(title)
    for (year, month, service_type), count in sorted(
        counts.items(), key=lambda item: (item[0][0], item[0][1], item[0][2].value)
    ):
        print(f"  {year}-{month:02d} {service_type.value}: {count}")


async def run(args: argparse.Namespace) -> int:
    database_url = _load_database_url(
        override_url=args.database_url,
    )
    print(f"Database: {_public_database_name(database_url)}")

    excel_root = Path(args.excel_root).resolve()
    directories = discover_directories(excel_root, latest_only=args.latest_only)
    if not directories:
        print(f"No Excel directories found under {excel_root}")
        return 1

    if not args.no_decrypt:
        auto_decrypt_directories(directories)

    plans = build_import_plan(excel_root, directories, args.year)
    if not plans:
        print("No importable Excel sheets found.")
        return 1

    expected = expected_counts(plans)
    print_plan(plans)
    print_counts("Expected rows from Excel:", expected)

    if args.dry_run:
        print("Dry run finished; database was not changed.")
        return 0

    await ensure_database_exists(database_url)
    engine, session_factory = create_session_factory(database_url)
    try:
        await create_schema(engine)

        if not args.keep_existing_excel_imports:
            print("Clearing previous EXCEL_IMPORT rows before rebuild.")
            await clear_excel_imports(session_factory)

        await import_plans(session_factory, plans)
        actual = await actual_counts(session_factory, expected)
        print_counts("Rows stored in database:", actual)

        mismatches = []
        for key, expected_count in sorted(expected.items()):
            actual_count = actual.get(key, 0)
            if actual_count != expected_count:
                year, month, service_type = key
                mismatches.append(
                    f"{year}-{month:02d} {service_type.value}: "
                    f"expected {expected_count}, got {actual_count}"
                )

        field_errors = await validate_required_fields(session_factory, expected)
        if mismatches or field_errors:
            print("Verification failed:")
            for item in mismatches + field_errors:
                print(f"  - {item}")
            return 1

        print("Verification passed: Excel row counts match database row counts.")
        return 0
    finally:
        await engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create the database schema and import real Excel data from assets/excel."
    )
    parser.add_argument(
        "--excel-root",
        default=str(DEFAULT_EXCEL_ROOT),
        help="Directory containing Excel period folders.",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=datetime.now().year,
        help="Fallback year when a workbook/folder has no explicit year.",
    )
    parser.add_argument(
        "--latest-only",
        action="store_true",
        help="Import only the newest Excel subdirectory by file modification time.",
    )
    parser.add_argument(
        "--no-decrypt",
        action="store_true",
        help="Do not attempt to decrypt original workbooks; use existing .dec.xlsx files only.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read and validate Excel files without changing the database.",
    )
    parser.add_argument(
        "--database-url",
        help="Override DATABASE_URL from .env. PostgreSQL is required.",
    )
    parser.add_argument(
        "--keep-existing-excel-imports",
        action="store_true",
        help="Do not clear old EXCEL_IMPORT rows before importing.",
    )
    return parser.parse_args()


async def main() -> int:
    try:
        return await run(parse_args())
    except Exception as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
