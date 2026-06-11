"""Har scenario_index uchun almashinuv SONI (qisqa / o'rta / uzun suhbat)."""
from __future__ import annotations

import random
from typing import Dict, List, Tuple

DIALOGUE_PROFILES: List[Dict] = [
    {
        "name": "qisqa_8",
        "flow": "short",
        "client_burst": (1, 1),
        "greeting_multi_chance": 0.08,
        "processing_chatter_pct": 15,
        "operator_followup_chance": 0.04,
        "target_exchanges": "8-10",
    },
    {
        "name": "qisqa_9",
        "flow": "short",
        "client_burst": (1, 2),
        "greeting_multi_chance": 0.12,
        "processing_chatter_pct": 20,
        "operator_followup_chance": 0.06,
        "target_exchanges": "9-11",
    },
    {
        "name": "qisqa_10",
        "flow": "short",
        "client_burst": (1, 1),
        "greeting_multi_chance": 0.1,
        "processing_chatter_pct": 25,
        "operator_followup_chance": 0.08,
        "target_exchanges": "10-12",
    },
    {
        "name": "qisqa_11",
        "flow": "short",
        "client_burst": (1, 2),
        "greeting_multi_chance": 0.15,
        "processing_chatter_pct": 18,
        "operator_followup_chance": 0.05,
        "target_exchanges": "10-12",
    },
    {
        "name": "orta_12",
        "flow": "normal",
        "client_burst": (1, 2),
        "greeting_multi_chance": 0.22,
        "processing_chatter_pct": 35,
        "operator_followup_chance": 0.1,
        "target_exchanges": "12-14",
    },
    {
        "name": "orta_13",
        "flow": "normal",
        "client_burst": (1, 2),
        "greeting_multi_chance": 0.25,
        "processing_chatter_pct": 40,
        "operator_followup_chance": 0.12,
        "target_exchanges": "13-15",
    },
    {
        "name": "orta_14",
        "flow": "normal",
        "client_burst": (1, 3),
        "greeting_multi_chance": 0.28,
        "processing_chatter_pct": 42,
        "operator_followup_chance": 0.11,
        "target_exchanges": "14-16",
    },
    {
        "name": "orta_15",
        "flow": "normal",
        "client_burst": (2, 2),
        "greeting_multi_chance": 0.3,
        "processing_chatter_pct": 45,
        "operator_followup_chance": 0.13,
        "target_exchanges": "14-17",
    },
    {
        "name": "uzun_16",
        "flow": "long",
        "client_burst": (2, 3),
        "greeting_multi_chance": 0.4,
        "processing_chatter_pct": 55,
        "operator_followup_chance": 0.18,
        "target_exchanges": "16-19",
    },
    {
        "name": "uzun_18",
        "flow": "long",
        "client_burst": (2, 3),
        "greeting_multi_chance": 0.45,
        "processing_chatter_pct": 60,
        "operator_followup_chance": 0.2,
        "target_exchanges": "17-20",
    },
    {
        "name": "uzun_20",
        "flow": "long",
        "client_burst": (2, 4),
        "greeting_multi_chance": 0.5,
        "processing_chatter_pct": 65,
        "operator_followup_chance": 0.22,
        "target_exchanges": "18-22",
    },
    {
        "name": "uzun_22",
        "flow": "long",
        "client_burst": (3, 4),
        "greeting_multi_chance": 0.55,
        "processing_chatter_pct": 70,
        "operator_followup_chance": 0.25,
        "target_exchanges": "20-24",
    },
]

OPERATOR_FOLLOWUPS: Dict[str, List[str]] = {
    "greeting": [
        "Diler nomini aniqroq yozing — filial nomi bo'lsa ham bo'ladi.",
        "Qaysi diler ekanini yana bir bor yozib yuboring.",
    ],
    "ask_dealer": [
        "Manzilni batafsilroq — tuman, ko'cha bo'lsa yaxshi.",
        "Qaysi tomonda ekanini aniqroq ayting.",
    ],
    "ask_area": [
        "Yana bir jumla bilan manzilni yozing, iltimos.",
        "Ko'cha yoki mo'ljal bormi?",
    ],
    "ask_area_extra": [
        "Uy raqami yoki pod'ezd bormi?",
        "Aniqroq manzil kerak bo'lishi mumkin.",
    ],
    "confirm_login": [
        "Tarif nomini lotincha yoki o'zbekcha yozing.",
        "Qaysi paket — nomini to'liq yozing.",
    ],
    "ask_tariff": [
        "Tarif to'g'rimi — yana bir bor tasdiq bering.",
    ],
}

CLIENT_BURST_FILLERS: List[str] = [
    "Ok.",
    "Tushundim.",
    "Ha, shunday.",
    "Bo'pti.",
    "Iltimos, davom eting.",
    "Rahmat.",
    "Xop.",
]


def get_dialogue_profile(scenario_index: int) -> Dict:
    return DIALOGUE_PROFILES[(scenario_index or 0) % len(DIALOGUE_PROFILES)]


def expand_client_burst(
    messages: List[str],
    processor_text: str,
    scenario_index: int,
    step: str,
) -> Tuple[List[str], str]:
    profile = get_dialogue_profile(scenario_index)
    lo, hi = profile["client_burst"]
    target = random.randint(lo, hi)

    if step == "greeting":
        if len(messages) >= target:
            return messages, processor_text
        if random.randint(1, 100) > int(profile["greeting_multi_chance"] * 100):
            return messages, processor_text

    out = list(messages)
    while len(out) < target:
        filler = random.choice(CLIENT_BURST_FILLERS)
        if filler not in out:
            out.append(filler)
    return out, processor_text


def should_processing_chatter(scenario_index: int) -> bool:
    profile = get_dialogue_profile(scenario_index)
    return random.randint(1, 100) <= int(profile["processing_chatter_pct"])


def should_operator_followup(scenario_index: int, step: str) -> bool:
    profile = get_dialogue_profile(scenario_index)
    if step not in OPERATOR_FOLLOWUPS:
        return False
    return random.random() < float(profile["operator_followup_chance"])


def operator_followup_text(step: str) -> str:
    return random.choice(OPERATOR_FOLLOWUPS.get(step, ["Yana bir bor yozing."]))
