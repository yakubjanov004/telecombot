"""Matndan ovozli xabar (edge-tts) — scenario_index bo'yicha boshqa ovoz."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Optional

import backend.config as settings
from backend.services.sound_profiles import get_sound_profile

logger = logging.getLogger(__name__)

# Cache directory inside storage/tts_cache
_CACHE_DIR = Path(settings.project_root) / "storage" / "tts_cache"


def _cache_path(text: str, scenario_index: int) -> Path:
    profile = get_sound_profile(scenario_index)
    key = f"{profile['voice']}|{profile['rate']}|{text.strip()}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
    return _CACHE_DIR / f"{digest}.mp3"


async def synthesize_voice(text: str, scenario_index: int) -> Optional[Path]:
    """MP3 fayl qaytaradi; edge-tts yo'q bo'lsa None."""
    if not getattr(settings, "FAKE_VOICE_ENABLED", False):
        return None
    clean = (text or "").strip()
    if not clean or len(clean) > 500:
        return None

    try:
        import edge_tts  # type: ignore
    except ImportError:
        logger.debug("edge-tts o'rnatilmagan — faqat matn yuboriladi")
        return None

    profile = get_sound_profile(scenario_index)
    out = _cache_path(clean, scenario_index)
    if out.is_file():
        return out

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        communicate = edge_tts.Communicate(
            clean,
            profile["voice"],
            rate=profile["rate"],
        )
        await communicate.save(str(out))
        return out if out.is_file() else None
    except Exception as exc:
        logger.warning("TTS failed: %s", exc)
        return None
