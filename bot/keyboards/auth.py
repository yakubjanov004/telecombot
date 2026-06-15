from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def lang_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="O'zbekcha"),
                KeyboardButton(text="Русский"),
            ]
        ],
        resize_keyboard=True,
    )
