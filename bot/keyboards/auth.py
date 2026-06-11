from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def lang_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="O'zbekcha"),
                KeyboardButton(text="Russkiy"),
            ]
        ],
        resize_keyboard=True,
    )
