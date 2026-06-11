import copy
import json
import random
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# small_talk da ishlatilmasligi kerak (tasdiq bilan aralashadi)
_SMALL_TALK_BLOCKLIST = frozenset({"ha", "xa", "ok", "da", "aha", "mayli", "bo'pti", "bopti", "xop", "xo'p", "yaxshi"})

# Tasdiq / rad javoblari
_CONFIRM_RE = re.compile(
    r"^(ha|xa|xop|xo'p|ok|okay|to'g'ri|togri|tasdiq|da|aha|shunday|roziman|mayli|"
    r"bo'pti|bopti|davom|roziman|tasdiqlayman|to'g'ri\s*mi)\b",
    re.IGNORECASE,
)
_DENY_RE = re.compile(r"^(yo'q|yoq|noto'g'ri|xato|boshqa)\b", re.IGNORECASE)

# Kutish / shoshilish (qadam o'tkazilmaydi)
_WAITING_RE = re.compile(
    r"(kutib|kutayap|kutmoq|kutaman|kutvom|kutib\s+tur|qachon\s|tezro?q|tez\s+bo|"
    r"bo'ldimi|bo'ladimi|ishlayaptimi|ishlamayapti|qotib|qotvot|tugadimi|tayyormi|"
    r"necha\s+daqiqa|hali\s+tayyor|ha\s+men\s+bu|men\s+bu\s+yerda|yerdaman|"
    r"shu\s+narsa\s+qachon|kutib\s+qoldim)",
    re.IGNORECASE,
)

# «Ha» bilan boshlansa ham tasdiq emas — suhbat/javob
_NOT_CONFIRM_PHRASE = re.compile(
    r"(ha\s+men|men\s+sizni|kutayap|kutib|qachon|tezroq|bo'ldimi|ishlayapti|"
    r"muammo|internetim|uzoqlash)",
    re.IGNORECASE,
)

# Raqam / login
_MSISDN_RE = re.compile(r"(998\d{9}|m\d{5,}|\d{9,12})", re.IGNORECASE)

# Sana
_DATE_RE = re.compile(
    r"(bugun|ertaga|hozir|xozir|srazu|boshlab|sanadan|oy\.|kun\.|\d{1,2}[./]\d{1,2})",
    re.IGNORECASE,
)

# Tarif nomi (raqam+harf yoki aniq tarif so'zlari)
_TARIFF_HINT_RE = re.compile(
    r"(tarif|mbit|mbps|wifi|internet|zo'r|zor|unlim|paket|rate|plan|\d+\s*mb)",
    re.IGNORECASE,
)

# Qadam turi: data = ma'lumot kiritish, confirm = ha/yo'q, notes = izoh, free = har qanday
_STEP_KIND: Dict[str, str] = {
    "start": "free",
    "greeting": "dealer",
    "ask_dealer": "area",
    "ask_area": "area",
    "ask_area_extra": "area",
    "ask_login": "confirm",
    "ask_number": "confirm",
    "confirm_login": "tariff",
    "confirm_number": "tariff",
    "ask_tariff": "confirm",
    "confirm_tariff": "date",
    "ask_start_date": "notes",
    "ask_notes": "notes",
    "ask_notes_extra": "notes",
    "processing": "waiting",
    "completed": "free",
}

# Qayta so'rash / kutish javoblari (qadam bo'yicha)
_REASK: Dict[str, list] = {
    "greeting": [
        "WiFi o'rnatish uchun avval diler nomini yozing.",
        "Salomdan keyin — qaysi diler?",
        "Bo'pti, diler nomi kerak.",
    ],
    "ask_dealer": [
        "Diler bor. WiFi qayerga o'rnatiladi — manzil/hudud?",
        "Qaysi tuman yoki uy manzili?",
        "O'rnatiladigan joyni yozing.",
    ],
    "ask_area": [
        "Manzil qabul qilindi. Biroz kuting — bazadan raqam tanlab beraman.",
        "Hudud ok. Hozir bazadan raqam ko'raman.",
        "Yaxshi, manzil yozildi. Raqamni bazadan olaman.",
    ],
    "ask_area_extra": [
        "Yana aniqroq manzil — ko'cha yoki uy raqami?",
        "Mo'ljal yoki pod'ezd bormi?",
    ],
    "ask_notes_extra": [
        "Montaj vaqti qulaymi?",
        "Qo'shimcha eslatma bormi?",
    ],
    "ask_login": [
        "Bazadan raqam bor — mijozga ayting. Rozi bo'lsa «ha» deb yozing.",
        "Raqamni mijozga berdingizmi? Tasdiq bering.",
        "Shu raqamni oladimi — ha yoki yo'q?",
    ],
    "ask_number": [
        "Raqam to'g'rimi? Ha deb yozing.",
        "Shu raqam bo'lsa tasdiq.",
    ],
    "confirm_login": [
        "Raqam qabul qilindi. Qaysi WiFi tarif?",
        "Zo'r, mijoz raqamni oldi. Tarif nomini yozing.",
        "Endi internet/WiFi tarifi kerak.",
    ],
    "confirm_number": [
        "Tarif nomini yozing.",
        "Qaysi tarif ulaymiz?",
    ],
    "ask_tariff": [
        "Tarif to'g'rimi? Ha yoki qayta yozing.",
        "Shu tarifmi?",
        "Tasdiq bering — to'g'rimi?",
    ],
    "confirm_tariff": [
        "Qachondan? Bugunmi?",
        "Sanani yozing.",
        "Qachon yoqamiz?",
    ],
    "ask_start_date": [
        "Izoh bormi? Yo'q bo'lsa «yo'q».",
        "Yana biror narsa?",
        "Qo'shimcha gap bo'lsa yozing.",
    ],
    "ask_notes": [
        "Ok, izoh bor. Boshqa narsa?",
        "Yana ma'lumot bormi?",
    ],
}

_WAITING_REPLY = [
    "Ha, ko'rib chiqyapman — biroz kuting.",
    "Bazaga tushyapti, ozgina sabr.",
    "Ok, ish ketmoqda. Tez javob beraman.",
    "Kutib turing aka, hozir.",
    "Tekshiryapman, xabar beraman.",
]

_ACK_TEMPLATES = {
    "dealer": ["{value} — ok.", "Bo'pti, {value}.", "Diler {value}, tushunarli."],
    "area": ["{value} — yozildi.", "Hudud {value}, ok.", "Ha, {value}."],
    "msisdn": [
        "Bazadan {value} — mijozga shu raqamni bering.",
        "Mana raqam: {value}.",
        "{value} — bazadan oldim.",
    ],
    "tariff": ["{value} — tarif ok.", "Tarif {value}.", "Ha, {value}."],
    "date": ["{value} — sana ok.", "Bo'pti, {value} dan.", "{value}, tushunarli."],
    "notes": ["Izoh ham bor.", "Ok, yozildi.", "Rahmat."],
    "confirm_yes": ["Zo'r.", "Ok.", "Bo'pti, ketdik."],
}

_SUMMARY_FOR_STEP = {
    "ask_login": [
        "Bazadan sizga {msisdn} raqam bor. Shu raqamni olasizmi?",
        "Mana raqam: {msisdn}. Rozimisiz?",
        "WiFi uchun {msisdn} — shu raqamni beramiz, to'g'rimi?",
    ],
    "ask_number": [
        "Raqam {msisdn} — to'g'rimi?",
        "{msisdn} bo'lsa ha.",
    ],
    "ask_tariff": [
        "Tarif {tariff} — shundaymi?",
        "Demak {tariff} — to'g'rimi?",
        "{tariff} ulaymizmi?",
    ],
    "confirm_tariff": [
        "Tarif {tariff} ok. Qachondan?",
        "{tariff} — qachon yoqamiz?",
    ],
    "ask_start_date": [
        "Sana {date}. Izoh bormi?",
        "{date} dan. Yana biror narsa?",
    ],
    "processing": [
        "Raqam {msisdn} va tarif {tariff} bazada. WiFi o'rnatilmoqda — kuting.",
        "{dealer}, {area} — raqam {msisdn}. Bazaga kiritildi, o'rnatish ketmoqda.",
        "Hammasi bazada. Hozir WiFi o'rnatish jarayoni.",
    ],
}


class ScenarioProcessor:
    def __init__(self, scenarios_dir: str):
        self.scenarios_dir = scenarios_dir
        self.scenarios = self._load_scenarios()

    @staticmethod
    def _scenario_sort_key(file_path: Path, data: dict) -> tuple:
        if "variant" in data:
            return (0, int(data["variant"]))
        m = re.search(r"_(\d+)$", file_path.stem)
        if m:
            return (0, int(m.group(1)))
        if file_path.stem.endswith("_scenario"):
            return (0, 0)
        return (1, file_path.stem)

    def _load_scenarios(self) -> Dict[str, Any]:
        groups: Dict[str, list] = {}
        try:
            path = Path(self.scenarios_dir)
            buckets: Dict[str, list] = {}
            for file_path in path.glob("*_scenario*.json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                stem = file_path.stem
                if stem.startswith("mobile"):
                    key = "mobile"
                elif stem.startswith("internet"):
                    key = "internet"
                else:
                    key = stem
                buckets.setdefault(key, []).append((file_path, data))
            for key, items in buckets.items():
                items.sort(key=lambda x: self._scenario_sort_key(x[0], x[1]))
                groups[key] = [d for _, d in items]
            return groups
        except Exception as e:
            logger.error(f"Error loading scenarios from {self.scenarios_dir}: {e}")
            return groups

    def get_variant_count(self, service_type: str) -> int:
        variants = self.scenarios.get(service_type) or self.scenarios.get("internet") or []
        return len(variants)

    def pick_scenario(self, service_type: str, index: int = 0) -> Dict[str, Any]:
        variants = self.scenarios.get(service_type) or self.scenarios.get("internet") or [{}]
        safe_index = index % len(variants) if variants else 0
        return variants[safe_index]

    def get_effective_scenario(self, service_type: str, index: int = 0) -> Dict[str, Any]:
        variants = self.scenarios.get(service_type) or self.scenarios.get("internet") or [{}]
        if not variants:
            return {}
        variant = variants[index % len(variants)]
        return {
            "intents": copy.deepcopy(variant.get("intents", {})),
            "flow": copy.deepcopy(variant.get("flow", {})),
        }

    @staticmethod
    def _trigger_matches(trigger: str, text_lower: str) -> bool:
        t = trigger.strip().lower()
        if not t:
            return False
        if t in _SMALL_TALK_BLOCKLIST:
            return bool(re.search(r"\b" + re.escape(t) + r"\b", text_lower))
        if len(t) <= 4:
            return bool(re.search(r"\b" + re.escape(t) + r"\b", text_lower))
        return t in text_lower

    def detect_intent(
        self,
        service_type: str,
        text: str,
        scenario_index: int = 0,
        current_step: Optional[str] = None,
    ) -> Optional[str]:
        if not text:
            return None

        scenario = self.get_effective_scenario(service_type, scenario_index)
        intents = scenario.get("intents", {})
        text_lower = text.lower()
        step_kind = _STEP_KIND.get(current_step or "", "data")

        for intent_name, intent_data in intents.items():
            if intent_name == "small_talk" and step_kind == "confirm":
                continue
            for trigger in intent_data.get("triggers", []):
                if intent_name == "small_talk" and trigger.strip().lower() in _SMALL_TALK_BLOCKLIST:
                    if self._classify_reply(text, current_step or "") == "confirm":
                        continue
                if self._trigger_matches(trigger, text_lower):
                    return intent_name
        return None

    def _classify_reply(self, text: str, step: str) -> str:
        if not text or not text.strip():
            return "empty"

        t = text.strip()
        kind = _STEP_KIND.get(step, "data")

        if _WAITING_RE.search(t):
            return "waiting"

        if kind == "confirm":
            if _NOT_CONFIRM_PHRASE.search(t) or _WAITING_RE.search(t):
                return "waiting"
            if _DENY_RE.match(t):
                return "deny"
            short = t.lower().strip()
            if short in ("ha", "xa", "ok", "xop", "xo'p", "da", "aha", "to'g'ri", "togri"):
                return "confirm"
            if re.match(r"^ha[,.]?\s*(to'?g'?ri|shunday|shu)$", short):
                return "confirm"
            if _CONFIRM_RE.match(t) and len(t) <= 35:
                return "confirm"
            return "unclear"

        if kind == "msisdn":
            if _MSISDN_RE.search(t):
                return "msisdn"
            if _CONFIRM_RE.match(t):
                return "confirm"
            return "data"

        if kind == "tariff":
            if _TARIFF_HINT_RE.search(t) or (len(t) > 2 and not _WAITING_RE.search(t)):
                return "tariff"
            return "unclear"

        if kind == "date":
            if _DATE_RE.search(t):
                return "date"
            return "data"

        if kind in ("dealer", "area", "notes"):
            if kind == "notes" and (_DENY_RE.match(t) or "yo'q" in t.lower() or "yoq" in t.lower()):
                return "notes_empty"
            return "data"

        return "data"

    def _short_value(self, text: str, max_len: int = 40) -> str:
        v = text.strip()
        if len(v) > max_len:
            return v[: max_len - 3] + "..."
        return v

    def _acknowledge(self, kind: str, value: str) -> str:
        if kind == "confirm_yes":
            templates = _ACK_TEMPLATES["confirm_yes"]
            return random.choice(templates)
        templates = _ACK_TEMPLATES.get(kind, _ACK_TEMPLATES["confirm_yes"])
        short = self._short_value(value)
        tpl = random.choice(templates)
        return tpl.replace("{value}", short)

    def _combine_ack_and_question(self, ack: str, question: str) -> str:
        if random.random() < 0.35:
            return f"{ack} {question}"
        return question

    def get_operator_greeting(self, service_type: str, scenario_index: int = 0) -> Dict[str, Any]:
        scenario = self.get_effective_scenario(service_type, scenario_index)
        flow = scenario.get("flow", {})
        step_data = flow.get("greeting", {})

        responses = step_data.get("responses", ["Salom! Diler nomini yozing, boshlaymiz."])
        return {
            "response": random.choice(responses),
            "next_step": step_data.get("next_step", "ask_dealer"),
        }

    def _reply_for_step(self, flow: dict, step_name: str) -> str:
        step_data = flow.get(step_name, {})
        responses = step_data.get("responses", ["Batafsilroq ma'lumot bera olasizmi?"])
        return random.choice(responses)

    def _reask_for_step(self, flow: dict, step_name: str) -> str:
        step_data = flow.get(step_name, {})
        if step_data.get("responses"):
            return random.choice(step_data["responses"])
        return random.choice(_REASK.get(step_name, ["Iltimos, ma'lumotni yuboring."]))

    def _field_from_collected(self, collected_data: dict, *keys: str) -> str:
        meta = collected_data.get("_meta") or {}
        for key in keys:
            if collected_data.get(key):
                return self._short_value(str(collected_data[key]))
            if meta.get(key):
                return self._short_value(str(meta[key]))
        alias = {
            "msisdn": ["msisdn"],
            "tariff": ["rate_plan", "tariff"],
            "dealer": ["dealer"],
            "area": ["area"],
            "date": ["date"],
        }
        for key in keys:
            for alt in alias.get(key, []):
                if meta.get(alt):
                    return self._short_value(str(meta[alt]))
        if "msisdn" in keys and collected_data.get("msisdn"):
            return self._short_value(str(collected_data["msisdn"]))
        if "tariff" in keys and collected_data.get("confirm_login"):
            return self._short_value(str(collected_data["confirm_login"]))
        if "tariff" in keys and collected_data.get("confirm_number"):
            return self._short_value(str(collected_data["confirm_number"]))
        if "date" in keys and collected_data.get("confirm_tariff"):
            return self._short_value(str(collected_data["confirm_tariff"]))
        if "dealer" in keys and collected_data.get("greeting"):
            return self._short_value(str(collected_data["greeting"]))
        if "area" in keys and collected_data.get("ask_dealer"):
            return self._short_value(str(collected_data["ask_dealer"]))
        return ""

    def _summary_question(self, next_step: str, collected_data: dict, fallback: str) -> str:
        templates = _SUMMARY_FOR_STEP.get(next_step)
        if not templates:
            return fallback

        ctx = {
            "msisdn": self._field_from_collected(collected_data, "msisdn"),
            "tariff": self._field_from_collected(collected_data, "tariff", "confirm_login", "confirm_number"),
            "dealer": self._field_from_collected(collected_data, "dealer", "greeting"),
            "area": self._field_from_collected(collected_data, "area", "ask_dealer"),
            "date": self._field_from_collected(collected_data, "date", "confirm_tariff"),
        }
        if next_step == "ask_login" and not ctx["msisdn"]:
            return fallback
        if next_step == "ask_tariff" and not ctx["tariff"]:
            return fallback
        if next_step == "processing" and not ctx["msisdn"]:
            return fallback

        tpl = random.choice(templates)
        try:
            return tpl.format(**ctx)
        except KeyError:
            return fallback

    def _stamp_msisdn_offer(self, collected_data: dict) -> dict:
        meta = collected_data.get("_meta") or {}
        if meta.get("msisdn"):
            collected_data["msisdn"] = str(meta["msisdn"]).strip()
        return collected_data

    def _advance(
        self,
        flow: dict,
        current_step: str,
        collected_data: dict,
        ack_kind: Optional[str] = None,
        ack_value: Optional[str] = None,
    ) -> Dict[str, Any]:
        step_data = flow.get(current_step, {})
        next_step_name = step_data.get("next_step", "completed")

        if next_step_name in ("ask_login", "ask_number", "processing"):
            collected_data = self._stamp_msisdn_offer(collected_data)

        if next_step_name == "completed":
            res_data = flow.get("completed", {})
            responses = res_data.get("responses", ["Rahmat! Operatorimiz bog'lanadi."])
            return {
                "response": random.choice(responses),
                "next_step": "completed",
                "collected_data": collected_data,
            }

        question = self._reply_for_step(flow, next_step_name)
        question = self._summary_question(next_step_name, collected_data, question)

        if ack_kind and ack_value is not None:
            ack = self._acknowledge(ack_kind, ack_value)
            response = self._combine_ack_and_question(ack, question)
        else:
            response = question

        msisdn = self._field_from_collected(collected_data, "msisdn")
        if msisdn:
            response = response.replace("{msisdn}", msisdn)
        for key, val in collected_data.items():
            if key.startswith("_"):
                continue
            response = response.replace(f"{{{key}}}", str(val))

        return {
            "response": response,
            "next_step": next_step_name,
            "collected_data": collected_data,
        }

    def process_operator_step(
        self,
        service_type: str,
        current_step: str,
        intent: Optional[str],
        text: Optional[str],
        collected_data: dict,
        scenario_index: int = 0,
    ) -> Dict[str, Any]:
        scenario = self.get_effective_scenario(service_type, scenario_index)
        flow = scenario.get("flow", {})
        intents = scenario.get("intents", {})

        if intent == "small_talk" and _STEP_KIND.get(current_step) == "confirm":
            intent = None

        if intent and intent in intents:
            intent_data = intents[intent]
            response = random.choice(intent_data["responses"])
            action = intent_data.get("action")
            if intent == "small_talk" and current_step not in ("processing", "completed"):
                return {
                    "response": response,
                    "next_step": current_step,
                    "action": action,
                    "collected_data": collected_data,
                }
            return {
                "response": response,
                "next_step": current_step if action != "handoff" else "completed",
                "action": action,
                "collected_data": collected_data,
            }

        classified = self._classify_reply(text or "", current_step)
        step_kind = _STEP_KIND.get(current_step, "data")

        if current_step == "start" and text:
            collected_data["start"] = text.strip()
            greeting = self.get_operator_greeting(service_type, scenario_index=scenario_index)
            if _WAITING_RE.search(text):
                openers = ["Ha, tez qilamiz. ", "Ok, ko'ramiz. ", "Bo'pti, hozir. "]
                greeting["response"] = random.choice(openers) + greeting["response"]
            else:
                openers = ["Ha, tushundim. ", "Ok. ", "Bo'pti. ", "Zo'r, "]
                greeting["response"] = random.choice(openers) + greeting["response"]
            return {
                "response": greeting["response"],
                "next_step": greeting["next_step"],
                "collected_data": collected_data,
            }

        if current_step in ("processing", "completed"):
            if classified == "waiting" or (text and _WAITING_RE.search(text)):
                return {
                    "response": random.choice(_WAITING_REPLY),
                    "next_step": current_step,
                    "collected_data": collected_data,
                }
            if current_step == "completed":
                return {
                    "response": random.choice([
                        "Ha, tekshiryapman — kuting.",
                        "Bitdi deyarli, xabar beraman.",
                        "Ok, kutib turing.",
                    ]),
                    "next_step": "completed",
                    "collected_data": collected_data,
                }
            return self._advance(flow, current_step, collected_data)

        if current_step not in flow:
            return {
                "response": "Ok, operator tezroq chiqadi.",
                "next_step": "completed",
                "collected_data": collected_data,
            }

        if classified == "waiting" and step_kind not in ("waiting", "notes"):
            return {
                "response": self._reask_for_step(flow, current_step),
                "next_step": current_step,
                "collected_data": collected_data,
            }

        if step_kind == "confirm" and classified in ("unclear", "data") and text:
            return {
                "response": self._reask_for_step(flow, current_step),
                "next_step": current_step,
                "collected_data": collected_data,
            }

        if step_kind == "confirm" and classified == "deny":
            return {
                "response": random.choice([
                    "Ok, to'g'risini qayta yozing.",
                    "Xato bo'lsa qayta yuboring.",
                    "Boshqacha yozib ko'ring.",
                ]),
                "next_step": current_step,
                "collected_data": collected_data,
            }

        ack_kind = None
        ack_value = None

        if text and text.strip():
            collected_data[current_step] = text.strip()

            if step_kind == "confirm" and classified == "confirm":
                ack_kind, ack_value = "confirm_yes", text
            elif step_kind == "msisdn" and classified == "msisdn":
                ack_kind, ack_value = "msisdn", text
            elif step_kind == "tariff" and classified in ("tariff", "data"):
                ack_kind, ack_value = "tariff", text
            elif step_kind == "date" and classified == "date":
                ack_kind, ack_value = "date", text
            elif step_kind == "dealer":
                ack_kind, ack_value = "dealer", text
            elif step_kind == "area":
                ack_kind, ack_value = "area", text
            elif step_kind in ("notes",) or classified == "notes_empty":
                ack_kind, ack_value = "notes", text

        advance_result = self._advance(
            flow, current_step, collected_data, ack_kind, ack_value
        )
        from backend.services.dialogue_profiles import (
            operator_followup_text,
            should_operator_followup,
        )

        if (
            ack_kind
            and advance_result.get("next_step") != current_step
            and should_operator_followup(scenario_index, current_step)
        ):
            advance_result["response"] = operator_followup_text(current_step)
            advance_result["next_step"] = current_step
        return advance_result
