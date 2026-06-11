from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from bot.core.constants import ButtonTexts

def operator_main_menu(lang: str = "uz", operator_type=None) -> ReplyKeyboardMarkup:
    inet = ButtonTexts.OP_INTERNET_RU if lang == "ru" else ButtonTexts.OP_INTERNET_UZ
    mob = ButtonTexts.OP_MOBILE_RU if lang == "ru" else ButtonTexts.OP_MOBILE_UZ
    lang_btn = ButtonTexts.LANG_RU if lang == "ru" else ButtonTexts.LANG_UZ

    # Montyor faqat internet kiritishi mumkin
    if operator_type == "montyor":
        rows = [[inet], [lang_btn]]
    else:
        rows = [[inet, mob], [lang_btn]]

    keyboard = [[KeyboardButton(text=t) for t in row] for row in rows]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def manager_main_menu(lang: str = "uz") -> ReplyKeyboardMarkup:
    if lang == "ru":
        rows = [
            [ButtonTexts.MGR_STATS_RU],
            [ButtonTexts.MGR_EXPORT_RU, ButtonTexts.MGR_COMPARE_RU],
            [ButtonTexts.OP_INTERNET_RU, ButtonTexts.OP_MOBILE_RU],
            [ButtonTexts.LANG_RU],
        ]
    else:
        rows = [
            [ButtonTexts.MGR_STATS_UZ],
            [ButtonTexts.MGR_EXPORT_UZ, ButtonTexts.MGR_COMPARE_UZ],
            [ButtonTexts.OP_INTERNET_UZ, ButtonTexts.OP_MOBILE_UZ],
            [ButtonTexts.LANG_UZ],
        ]
    keyboard = [[KeyboardButton(text=t) for t in row] for row in rows]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def cancel_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    text = ButtonTexts.OPERATOR_CANCEL_RU if lang == "ru" else ButtonTexts.OPERATOR_CANCEL_UZ
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text)]],
        resize_keyboard=True,
    )

def topic_control_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    text = "🛑 Chatni yopish" if lang == "uz" else "🛑 Закрыть чат"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data="close_chat")]
    ])
