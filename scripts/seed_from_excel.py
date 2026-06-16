import asyncio
import sys
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from backend.database import AsyncSessionLocal
from backend.services.import_service import ImportService
from backend.utils.logger import logger

EXCEL_ROOT = PROJECT_ROOT / "assets" / "excel"
IMPORT_YEAR = 2026

MONTH_BY_TOKEN = {
    "yanvar": 1,
    "yan": 1,
    "yanвар": 1,
    "январь": 1,
    "январ": 1,
    "fevral": 2,
    "fev": 2,
    "февраль": 2,
    "феврал": 2,
    "mart": 3,
    "mar": 3,
    "март": 3,
    "aprel": 4,
    "apr": 4,
    "апрель": 4,
    "апрел": 4,
    "may": 5,
    "май": 5,
    "iyun": 6,
    "jun": 6,
    "июнь": 6,
    "iyul": 7,
    "jul": 7,
    "июль": 7,
    "avgust": 8,
    "avg": 8,
    "август": 8,
    "sentabr": 9,
    "sep": 9,
    "сентябрь": 9,
    "sen": 9,
    "oktabr": 10,
    "oct": 10,
    "октябрь": 10,
    "okt": 10,
    "noyabr": 11,
    "nov": 11,
    "ноябрь": 11,
    "december": 12,
    "dec": 12,
    "dekabr": 12,
    "декабрь": 12,
    "дек": 12,
}


def _extract_month_candidates(name: str) -> list[int]:
    seen: list[int] = []
    text = name.lower()
    seen_set = set()
    for token in re.findall(r"[a-zа-яё]+", text):
        month = MONTH_BY_TOKEN.get(token)
        if month and month not in seen_set:
            seen.append(month)
            seen_set.add(month)
    return seen


def _unique_months(months: list[int]) -> list[int]:
    return list(dict.fromkeys(months))


def _wraps_year(months: list[int]) -> bool:
    unique = _unique_months(months)
    return 12 in unique and 1 in unique


def _directory_default_month(name: str) -> int | None:
    months = _unique_months(_extract_month_candidates(name))
    if len(months) == 1:
        return months[0]
    if _wraps_year(months):
        return min(months)
    return None


def _extract_default_year(name: str) -> int | None:
    year_match = re.search(r"20[0-9]{2}", name)
    return int(year_match.group()) if year_match else None


def _file_default_month(file_name: str, fallback_months: list[int] | None) -> int | None:
    file_months = _extract_month_candidates(file_name)
    if len(file_months) == 1:
        return file_months[0]
    if len(file_months) > 1:
        return None
    if fallback_months and len(fallback_months) == 1:
        return fallback_months[0]
    if fallback_months and _wraps_year(fallback_months):
        return min(_unique_months(fallback_months))
    return None


def _file_default_year(file_name: str, default_year: int, fallback_months: list[int] | None) -> int:
    file_year = _extract_default_year(file_name)
    if file_year is not None:
        return file_year

    file_months = _extract_month_candidates(file_name)
    if len(file_months) == 1 and fallback_months and _wraps_year(fallback_months):
        anchor_month = min(_unique_months(fallback_months))
        if file_months[0] > anchor_month:
            return default_year - 1

    return default_year


def _discover_data_dirs() -> list[dict[str, object]]:
    if not EXCEL_ROOT.exists():
        return []

    directories = [
        p
        for p in sorted(EXCEL_ROOT.iterdir(), key=lambda p: p.name.lower())
        if p.is_dir() and any(f.suffix.lower() == ".xlsx" for f in p.iterdir())
    ]

    if directories:
        return [
            {
                "path": d,
                "label": d.name,
                "default_year": _extract_default_year(d.name) or IMPORT_YEAR,
                "default_month": _directory_default_month(d.name),
                "default_months": _extract_month_candidates(d.name),
            }
            for d in directories
        ]

    return []


DATA_DIRS = _discover_data_dirs()


def _source_base_name(file_name: str) -> str:
    if file_name.endswith(".dec.xlsx"):
        file_name = file_name.removesuffix(".dec.xlsx")
    if file_name.endswith(".xlsx"):
        file_name = file_name.removesuffix(".xlsx")
    return file_name


async def collect_files(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        logger.warning(f"Directory not found: {data_dir}")
        return []

    all_excels = [f for f in data_dir.glob("*.xlsx") if not f.name.startswith("~$")]
    await auto_decrypt(data_dir, all_excels)
    all_excels = [f for f in data_dir.glob("*.xlsx") if not f.name.startswith("~$")]

    to_import = []
    for base in sorted({_source_base_name(f.name) for f in all_excels}):
        dec_file = data_dir / f"{base}.dec.xlsx"
        dec_file_alt = data_dir / f"{base}.xlsx.dec.xlsx"
        orig_file = data_dir / f"{base}.xlsx"

        if dec_file.exists():
            to_import.append(dec_file)
            logger.info(f"Selected: {dec_file.name} (decrypted)")
        elif dec_file_alt.exists():
            to_import.append(dec_file_alt)
            logger.info(f"Selected: {dec_file_alt.name} (decrypted)")
        elif orig_file.exists():
            to_import.append(orig_file)
            logger.info(f"Selected: {orig_file.name}")

    return to_import


async def auto_decrypt(data_dir: Path, files: list[Path]):
    password_file = data_dir / "password.txt"
    if not password_file.exists():
        return

    password = password_file.read_text().strip()
    if not password:
        return

    try:
        import io
        import msoffcrypto
    except ImportError:
        logger.warning("msoffcrypto-tool is not installed. Encrypted files are skipped.")
        return

    for f in files:
        if ".dec." in f.name:
            continue
        dec_path = data_dir / f"{f.stem}.dec.xlsx"
        dec_path_alt = data_dir / f"{f.name}.dec.xlsx"
        if dec_path.exists() or dec_path_alt.exists():
            continue

        try:
            with open(f, "rb") as fh:
                office_file = msoffcrypto.OfficeFile(fh)
                if office_file.is_encrypted():
                    office_file.load_key(password=password)
                    decrypted = io.BytesIO()
                    office_file.decrypt(decrypted)
                    decrypted.seek(0)
                    with open(dec_path, "wb") as out:
                        out.write(decrypted.read())
                    logger.info(f"Decrypted: {f.name} -> {dec_path.name}")
        except Exception as e:
            logger.error(f"Decrypt failed for {f.name}: {e}")


async def seed_from_excel():
    total_files = 0

    for dir_info in DATA_DIRS:
        data_dir = dir_info["path"]
        label = dir_info["label"]
        default_year = dir_info.get("default_year")
        default_month = dir_info.get("default_month")
        fallback_months = dir_info.get("default_months", [])

        logger.info(f"=== Processing: {label} ({data_dir}) ===")
        to_import = await collect_files(data_dir)

        if not to_import:
            logger.warning(f"No valid Excel files found in {label}.")
            continue

        logger.info(f"Starting import of {len(to_import)} files from {label}.")
        for file_path in to_import:
            file_month = _file_default_month(file_path.stem, fallback_months or [])
            effective_month = file_month if file_month is not None else default_month
            effective_year = _file_default_year(
                file_path.stem,
                int(default_year),
                fallback_months or [],
            )

            logger.info(
                f"-> Processing: {file_path.name} "
                f"(default={effective_year}/{effective_month or 'auto'})"
            )
            async with AsyncSessionLocal() as session:
                import_service = ImportService(session)
                try:
                    await import_service.import_from_file(
                        str(file_path),
                        default_year=effective_year,
                        default_month=effective_month,
                    )
                    logger.info(f"Success: {file_path.name}")
                    total_files += 1
                except Exception as e:
                    logger.error(f"Failed {file_path.name}: {e}")

    logger.info(f"Import process finished. {total_files} files imported.")


if __name__ == "__main__":
    asyncio.run(seed_from_excel())
