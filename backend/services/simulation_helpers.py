"""Simulyatsiya uchun yordamchi: Excel kontekst, persona, kechikish, xabar bo'lish."""
import random
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

import backend.config as settings
from backend.models import InternetSale


def is_night_time() -> bool:
    try:
        tz = ZoneInfo(settings.TIMEZONE)
    except Exception:
        tz = ZoneInfo("Asia/Tashkent")
    local_hour = datetime.now(tz).hour
    start, end = settings.NIGHT_START_HOUR, settings.NIGHT_END_HOUR
    if start > end:
        return local_hour >= start or local_hour < end
    return start <= local_hour < end

UZ_CITIES = [
    "Toshkent", "Samarqand", "Buxoro", "Namangan", "Andijon", "Farg'ona",
    "Qashqadaryo", "Surxondaryo", "Xorazm", "Navoiy", "Sirdaryo", "Jizzax",
]

_TYPO_MAP = {
    "to'g'ri": "togri",
    "xo'p": "xop",
    "bo'pti": "bopti",
    "yo'q": "yoq",
    "qo'shimcha": "qoshimcha",
    "o'rnatish": "ornatish",
    "tezroq": "tezroq",
}


def area_from_branch_name(name: Optional[str]) -> str:
    if not name:
        return random.choice(UZ_CITIES)
    low = name.lower()
    for city in UZ_CITIES:
        if city.lower() in low:
            return city
    return name.split(",")[0].strip()[:40] or random.choice(UZ_CITIES)


def sale_to_meta(sale: Any, service_type: str) -> Dict[str, str]:
    if service_type == "mobile":
        dealer = (sale.dealer_name_raw or sale.branch_name_raw or "Diler").strip()
        area = (sale.sale_point_name_raw or sale.branch_name_raw or "").strip()
        area = area_from_branch_name(area) if area else area_from_branch_name(dealer)
    else:
        dealer = (
            sale.branch_name_raw or sale.dealer_name_raw or "Filial"
        ).strip()
        area = (sale.department_name_raw or "").strip()
        area = area if area else area_from_branch_name(dealer)

    msisdn = (sale.msisdn or "").strip() or f"99890{random.randint(1000000, 9999999)}"
    rate = (sale.rate_plan_raw or ("Zo'r 5" if service_type == "mobile" else "Uy internet 100")).strip()

    return {
        "seeded": True,
        "msisdn": msisdn,
        "dealer": dealer,
        "area": area,
        "rate_plan": rate,
        "sale_id": getattr(sale, "id", None),
    }


async def seed_simulation_meta(
    db: AsyncSession,
    collected_data: dict,
    service_type: str,
) -> dict:
    """Bitta Excel qatoridan sessiya konteksti — diler/hudud/raqam mos keladi."""
    data = dict(collected_data or {})
    meta = data.get("_meta") or {}
    if meta.get("seeded"):
        return data

    res = await db.execute(select(InternetSale).order_by(func.random()).limit(1))
    sale = res.scalar()

    if sale:
        meta = {**sale_to_meta(sale, "internet"), "persona": meta.get("persona")}
    else:
        meta = {
            "seeded": True,
            "msisdn": f"99890{random.randint(1000000, 9999999)}",
            "dealer": "Asosiy filial",
            "area": random.choice(UZ_CITIES),
            "rate_plan": "Uy internet 100",
        }

    if not meta.get("persona"):
        meta["persona"] = random.choice(["sen", "siz"])

    data["_meta"] = meta
    return data


def get_meta(collected_data: dict) -> Dict[str, str]:
    return (collected_data or {}).get("_meta") or {}


def persona_messages(persona: str) -> Dict[str, List[str]]:
    sen = persona == "sen"
    if sen:
        return {
            "confirm": ["Ha, to'g'ri.", "Axa to'g'ri", "xop shunday", "Da to'g'ri", "Ha shunaqa"],
            "notes": [
                "Yo'q, hammasi to'g'ri.", "Izoh yo'q.", "Boshqa gapim yo'q.", "Bo'ldi.", "Tugadi.",
            ],
            "dates": [
                "Bugundan.", "Hoziroq.", "Bungundan ishlatsa bo'ladi.", "Xozirdan.", "Srazu yonsin.",
            ],
            "waiting": [
                "Ok, kutayapman.", "Jigar kutibturipman", "Bo'ldimi?", "Kutaman.", "Tezroq bo'lsa yaxshi.",
            ],
        }
    return {
        "confirm": ["Ha, to'g'ri.", "Ha shunaqa.", "Tasdiq.", "Ok to'g'ri."],
        "notes": ["Yo'q, boshqa yo'q.", "Izoh yo'q.", "Hammasi shu.", "Bo'ldi."],
        "dates": ["Bugundan.", "Hoziroq.", "Bugun bo'lsin.", "Srazu."],
        "waiting": [
            "Ok kutaman.", "Kutib turaman.", "Bo'ldimi?", "Tezroq bo'lsa yaxshi.",
        ],
    }


def maybe_typo(text: str, chance: float = 0.12) -> str:
    if random.random() > chance:
        return text
    for src, dst in _TYPO_MAP.items():
        if src in text and random.random() < 0.5:
            return text.replace(src, dst, 1)
    return text


def compute_operator_delay(
    text: str,
    *,
    night: bool = False,
    scenario_index: int = 0,
) -> float:
    from backend.services.sound_profiles import get_sound_profile

    profile = get_sound_profile(scenario_index)
    base = 2.0 + len(text) * 0.06 + random.uniform(0.5, 2.5)
    base *= float(profile["op_delay_mul"])
    if night:
        base += random.uniform(2, 5)
    return min(max(base, 2.5), 22.0)


def split_message(text: str, max_len: int = 130, scenario_index: int = 0) -> List[str]:
    from backend.services.sound_profiles import get_sound_profile

    if max_len == 130:
        max_len = int(get_sound_profile(scenario_index)["chunk_max"])
    text = text.strip()
    if len(text) <= max_len:
        return [text]

    parts: List[str] = []
    for chunk in re.split(r"(?<=[.?!])\s+", text):
        if not chunk:
            continue
        if len(chunk) <= max_len:
            parts.append(chunk)
        else:
            while len(chunk) > max_len:
                sp = chunk.rfind(" ", 0, max_len)
                if sp < 20:
                    sp = max_len
                parts.append(chunk[:sp].strip())
                chunk = chunk[sp:].strip()
            if chunk:
                parts.append(chunk)

    return parts or [text[:max_len]]


# Har scenario_index uchun boshqa mijoz talaffuzi (12 uslub)
_CLIENT_START: List[List[str]] = [
    [
        "Assalomu alaykum. Uyga WiFi o'rnatish kerak.",
        "Salom aka, yangi manzilga internet ulatmoqchiman.",
        "Vaalaykum! WiFi o'rnatib bering.",
        "Salom, uyimizga WiFi kerak.",
    ],
    [
        "Salom. WiFi qo'yish kerak.",
        "Aka internet kerak yangi uyga.",
        "Assalom, WiFi ulating.",
        "Vaalaykum, router o'rnatish kerak.",
    ],
    [
        "Xayrli kun! Uy interneti uchun murojaat.",
        "Assalomu alaykum, WiFi xizmati kerak.",
        "Salom, yangi ulanish kerak.",
        "Hurmat bilan — WiFi o'rnatish.",
    ],
    [
        "Aka salom! WiFi qildirasizmi?",
        "Jigar salom, internet kerak uyga.",
        "Vaalaykum aka, WiFi masalasi.",
        "Salom, yangi nuqtaga WiFi.",
    ],
    [
        "Salom. SHPD/WiFi buyurtma.",
        "Assalom. Uy interneti kerak.",
        "WiFi ulanish kerak.",
        "Yangi internet.",
    ],
    [
        "Salom, qalaysiz? WiFi o'rnatmoqchiman.",
        "Yaxshimisiz? Internet kerak edi.",
        "Assalom, uyga WiFi qo'ymoqchimiz.",
        "Salom aka, router kerak.",
    ],
    [
        "Xayrli kun! WiFi o'rnatish kerak bo'ladi.",
        "Salom, iltimos internet ulating.",
        "Assalom, yangi manzil — WiFi.",
        "Salom, yordam kerak WiFi bo'yicha.",
    ],
    [
        "Salom tez. WiFi.",
        "Internet kerak. Salom.",
        "WiFi, diler bor.",
        "Assalom, WiFi.",
    ],
    [
        "Assalomu alaykum. Yangi uyimizga WiFi router o'rnatish kerak.",
        "Salom! Internet ulanishi bo'yicha murojaat qilmoqchiman.",
        "WiFi xizmatini ulatmoqchimiz, salom.",
        "Yangi manzil, WiFi kerak — salom.",
    ],
    [
        "Salom, qalaysiz aka? WiFi qo'ymoqchidim.",
        "Vaalaykum! Internet masalasida.",
        "Salom, WiFi haqida yozmoqchiman.",
        "Aka salom, uyga net kerak.",
    ],
    [
        "Salom! WiFi o'rnatish kerak.",
        "Assalom, internet ulatish kerak.",
        "Yangi uy — WiFi kerak.",
        "Salom aka, router masalasi.",
    ],
    [
        "Salom. WiFi order.",
        "Internet kerak, salom.",
        "WiFi install kerak.",
        "Assalom, connection.",
    ],
]

_CLIENT_CONFIRM_MSISDN: List[List[str]] = [
    ["Ha, {m} bo'lsin.", "Shu raqam — {m}.", "Ok, {m}.", "Roziman, {m}."],
    ["Ha.", "{m} olaman.", "Ok.", "Bo'pti."],
    ["Ha, ushbu raqam ma'qul — {m}.", "Roziman.", "{m} bo'yicha.", "Tasdiq."],
    ["Aka {m} bo'lsin.", "Ha shu nomer.", "{m} yaxshi.", "Oladi."],
    ["Qabul.", "{m}.", "Ha.", "OK."],
    ["Ha, shu raqam.", "{m} mos.", "Roziman.", "To'g'ri."],
    ["Juda yaxshi, {m}.", "Ma'qul.", "Ha, iltimos.", "{m}."],
    ["Ha.", "Ok.", "{m}.", "Xa."],
    ["Tasdiqlaymiz — {m}.", "Ushbu raqam.", "Ha, {m}.", "Roziman."],
    ["Ha aka.", "{m} bo'lsin.", "Shunday.", "Ok."],
    ["Ha, shu.", "{m}.", "Roziman.", "Bo'ldi."],
    ["Confirm {m}.", "Ha.", "OK {m}.", "Yes."],
]


def build_client_messages(
    step: str,
    meta: Dict[str, str],
    service_type: str,
    scenario_index: int = 0,
) -> Tuple[List[str], str]:
    persona = meta.get("persona", "siz")
    pools = persona_messages(persona)
    d, a, m, r = meta["dealer"], meta["area"], meta["msisdn"], meta["rate_plan"]
    vi = (scenario_index or 0) % 12
    from backend.services.dialogue_profiles import expand_client_burst, get_dialogue_profile

    profile = get_dialogue_profile(scenario_index)

    def _pack(msgs: List[str], proc: str) -> Tuple[List[str], str]:
        return expand_client_burst(msgs, proc, scenario_index, step)

    if step == "start":
        opts = _CLIENT_START[vi]
        msg = random.choice(opts)
        return _pack([maybe_typo(msg)], msg)

    if step == "greeting":
        if persona == "sen":
            opts = [
                f"{d} danman.",
                f"Diler: {d}",
                f"Aka {d} dan.",
                f"Men {d} orqali murojaat qilaman.",
            ]
        else:
            opts = [
                f"Biz {d} dileridanmiz.",
                f"Dilerimiz {d}.",
                f"{d} filialidan yozmoqdamiz.",
            ]
        greet_chance = int(profile["greeting_multi_chance"] * 100)
        if random.randint(1, 100) <= greet_chance:
            opener = random.choice(["Assalomu alaykum", "Salom", "Vaalaykum"])
            main = random.choice(opts)
            return _pack([maybe_typo(opener), maybe_typo(main)], main)
        msg = random.choice(opts)
        return _pack([maybe_typo(msg)], msg)

    if step == "ask_dealer":
        opts = [
            f"{a}.",
            f"Manzil: {a}",
            f"WiFi shu yerga: {a}",
            f"{a} hududida o'rnatiladi.",
            f"Uyimiz {a} da.",
        ]
        msg = random.choice(opts)
        return _pack([maybe_typo(msg)], msg)

    if step in ("ask_area", "ask_area_extra"):
        opts = [
            f"{a}.",
            f"Manzil: {a}",
            f"WiFi shu manzilga: {a}",
            f"Uy {a} da o'rnatiladi.",
        ]
        msg = random.choice(opts)
        return _pack([maybe_typo(msg)], msg)

    if step in ("ask_login", "ask_number"):
        opts = [t.format(m=m) for t in _CLIENT_CONFIRM_MSISDN[vi]] + pools["confirm"]
        msg = random.choice(opts)
        return _pack([maybe_typo(msg)], msg)

    if step in ("confirm_login", "confirm_number"):
        opts = [
            f"WiFi uchun {r} tarifini xohlaymiz.",
            f"Tarif: {r}",
            f"Mijoz {r} ni tanladi.",
            f"{r} paket bo'lsin.",
        ]
        msg = random.choice(opts)
        return _pack([maybe_typo(msg)], msg)

    if step == "ask_tariff":
        msg = random.choice(pools["confirm"])
        return _pack([maybe_typo(msg)], msg)

    if step == "confirm_tariff":
        msg = random.choice(pools["dates"])
        return _pack([maybe_typo(msg)], msg)

    if step == "ask_start_date":
        msg = random.choice(pools["notes"])
        return _pack([maybe_typo(msg)], msg)

    if step in ("ask_notes", "ask_notes_extra"):
        msg = random.choice(pools["notes"] + ["Yo'q, boshqa narsa yo'q.", "Rahmat, hammasi aytildi."])
        return _pack([maybe_typo(msg)], msg)

    if step == "processing":
        msg = random.choice(pools["waiting"])
        return _pack([maybe_typo(msg)], msg)

    return _pack([maybe_typo("Ok.")], "Ok.")
