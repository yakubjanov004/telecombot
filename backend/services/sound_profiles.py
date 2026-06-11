"""Har scenario_index uchun alohida ritm (kutish, typing) va ovoz profili."""
from __future__ import annotations

import random
from typing import Dict, Tuple
import backend.config as settings

# client_wait: (min, max) sek; op_delay_mul: operator javob sekinligi
# chunk_max: xabar bo'lak uzunligi; inter_msg: mijoz xabarlari orasi
# voice: edge-tts; rate: nutq tezligi; voice_chance: ovozli xabar ehtimoli
SOUND_PROFILES: list[Dict] = [
    {
        "name": "oddiy",
        "client_wait": (8, 16),
        "op_delay_mul": 1.0,
        "typing_mul": 1.0,
        "chunk_max": 130,
        "inter_msg": (2.0, 4.5),
        "voice": "uz-UZ-SardorNeural",
        "rate": "+0%",
        "voice_chance": 0.22,
    },
    {
        "name": "tez",
        "client_wait": (5, 10),
        "op_delay_mul": 0.72,
        "typing_mul": 0.75,
        "chunk_max": 90,
        "inter_msg": (1.2, 2.8),
        "voice": "uz-UZ-MadinaNeural",
        "rate": "+12%",
        "voice_chance": 0.18,
    },
    {
        "name": "sekin",
        "client_wait": (12, 22),
        "op_delay_mul": 1.35,
        "typing_mul": 1.4,
        "chunk_max": 160,
        "inter_msg": (3.0, 6.0),
        "voice": "uz-UZ-SardorNeural",
        "rate": "-15%",
        "voice_chance": 0.28,
    },
    {
        "name": "qisqa_bo'lak",
        "client_wait": (6, 12),
        "op_delay_mul": 0.9,
        "typing_mul": 0.85,
        "chunk_max": 70,
        "inter_msg": (1.5, 3.0),
        "voice": "uz-UZ-MadinaNeural",
        "rate": "+5%",
        "voice_chance": 0.2,
    },
    {
        "name": "uzun_javob",
        "client_wait": (10, 18),
        "op_delay_mul": 1.15,
        "typing_mul": 1.2,
        "chunk_max": 180,
        "inter_msg": (2.5, 5.0),
        "voice": "ru-RU-DmitryNeural",
        "rate": "+0%",
        "voice_chance": 0.25,
    },
    {
        "name": "muloqot",
        "client_wait": (7, 14),
        "op_delay_mul": 1.05,
        "typing_mul": 1.1,
        "chunk_max": 110,
        "inter_msg": (2.0, 3.5),
        "voice": "ru-RU-SvetlanaNeural",
        "rate": "+8%",
        "voice_chance": 0.3,
    },
    {
        "name": "tushkun",
        "client_wait": (14, 24),
        "op_delay_mul": 1.45,
        "typing_mul": 1.5,
        "chunk_max": 140,
        "inter_msg": (3.5, 7.0),
        "voice": "ru-RU-DariyaNeural",
        "rate": "-10%",
        "voice_chance": 0.32,
    },
    {
        "name": "juda_tez",
        "client_wait": (4, 8),
        "op_delay_mul": 0.6,
        "typing_mul": 0.65,
        "chunk_max": 65,
        "inter_msg": (0.8, 2.0),
        "voice": "uz-UZ-MadinaNeural",
        "rate": "+18%",
        "voice_chance": 0.15,
    },
    {
        "name": "batafsil",
        "client_wait": (11, 20),
        "op_delay_mul": 1.25,
        "typing_mul": 1.3,
        "chunk_max": 200,
        "inter_msg": (2.8, 5.5),
        "voice": "tr-TR-EmelNeural",
        "rate": "-5%",
        "voice_chance": 0.27,
    },
    {
        "name": "do'stona",
        "client_wait": (6, 13),
        "op_delay_mul": 0.95,
        "typing_mul": 0.9,
        "chunk_max": 100,
        "inter_msg": (1.8, 3.2),
        "voice": "tr-TR-AhmetNeural",
        "rate": "+10%",
        "voice_chance": 0.24,
    },
    {
        "name": "rasmiy",
        "client_wait": (9, 17),
        "op_delay_mul": 1.1,
        "typing_mul": 1.15,
        "chunk_max": 150,
        "inter_msg": (2.2, 4.0),
        "voice": "ru-RU-DmitryNeural",
        "rate": "-8%",
        "voice_chance": 0.2,
    },
    {
        "name": "ovozli",
        "client_wait": (7, 15),
        "op_delay_mul": 1.0,
        "typing_mul": 1.0,
        "chunk_max": 120,
        "inter_msg": (2.0, 4.0),
        "voice": "uz-UZ-SardorNeural",
        "rate": "+3%",
        "voice_chance": 0.45,
    },
]


def get_sound_profile(scenario_index: int) -> Dict:
    return SOUND_PROFILES[(scenario_index or 0) % len(SOUND_PROFILES)]


def client_wait_seconds(scenario_index: int, *, night: bool = False) -> Tuple[int, int]:
    lo, hi = get_sound_profile(scenario_index)["client_wait"]
    if night:
        lo = int(lo * 1.3)
        hi = int(hi * 1.4)
    return lo, hi


def inter_message_delay(scenario_index: int) -> float:
    lo, hi = get_sound_profile(scenario_index)["inter_msg"]
    return random.uniform(lo, hi)


def should_send_voice(scenario_index: int, step: str, *, operator: bool = False) -> bool:
    if operator:
        if not getattr(settings, "FAKE_OPERATOR_VOICE_ENABLED", False):
            return False
    elif not getattr(settings, "FAKE_VOICE_ENABLED", False):
        return False

    profile = get_sound_profile(scenario_index)
    chance = float(profile["voice_chance"])
    if operator:
        chance *= 0.85
    if step in ("start", "greeting", "ask_login"):
        chance = min(0.55, chance + 0.12)
    if step in ("processing", "completed"):
        chance *= 0.5
    return random.random() < chance
