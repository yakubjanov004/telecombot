class ButtonTexts:
    LANG_UZ = "Tilni o'zgartirish"
    LANG_RU = "Изменить язык"

    OPERATOR_CANCEL_UZ = "Bekor qilish"
    OPERATOR_CANCEL_RU = "Отмена"
    OP_INTERNET_UZ = "Internet sotuvni kiritish"
    OP_INTERNET_RU = "Ввести продажу интернета"
    OP_MOBILE_UZ = "Mobil sotuvni kiritish"
    OP_MOBILE_RU = "Ввести мобильную продажу"

    MGR_STATS_UZ = "Statistika"
    MGR_STATS_RU = "Статистика"
    MGR_EXPORT_UZ = "Excel eksport"
    MGR_EXPORT_RU = "Экспорт Excel"
    MGR_COMPARE_UZ = "Oylar taqqoslash"
    MGR_COMPARE_RU = "Сравнение месяцев"


class LegacyButtonTexts:
    LANG_RU = "Izmenit yazyk"
    OPERATOR_CANCEL_RU = "Otmena"
    OP_INTERNET_RU = "Vvesti prodazhu interneta"
    OP_MOBILE_RU = "Vvesti mobilnuyu prodazhu"
    MGR_COMPARE_RU = "Sravnenie mesyatsev"


OPERATOR_MENU_BUTTON_TEXTS = {
    ButtonTexts.OP_INTERNET_UZ,
    ButtonTexts.OP_INTERNET_RU,
    LegacyButtonTexts.OP_INTERNET_RU,
    ButtonTexts.OP_MOBILE_UZ,
    ButtonTexts.OP_MOBILE_RU,
    LegacyButtonTexts.OP_MOBILE_RU,
    ButtonTexts.LANG_UZ,
    ButtonTexts.LANG_RU,
    LegacyButtonTexts.LANG_RU,
}

MANAGER_MENU_BUTTON_TEXTS = {
    ButtonTexts.MGR_STATS_UZ,
    ButtonTexts.MGR_STATS_RU,
    ButtonTexts.MGR_EXPORT_UZ,
    ButtonTexts.MGR_EXPORT_RU,
    ButtonTexts.MGR_COMPARE_UZ,
    ButtonTexts.MGR_COMPARE_RU,
    LegacyButtonTexts.MGR_COMPARE_RU,
    ButtonTexts.OP_INTERNET_UZ,
    ButtonTexts.OP_INTERNET_RU,
    LegacyButtonTexts.OP_INTERNET_RU,
    ButtonTexts.OP_MOBILE_UZ,
    ButtonTexts.OP_MOBILE_RU,
    LegacyButtonTexts.OP_MOBILE_RU,
    ButtonTexts.LANG_UZ,
    ButtonTexts.LANG_RU,
    LegacyButtonTexts.LANG_RU,
}

STAFF_MENU_BUTTON_TEXTS = OPERATOR_MENU_BUTTON_TEXTS | MANAGER_MENU_BUTTON_TEXTS
