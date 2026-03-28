from locales.ru import RU
from locales.uz import UZ

LANGUAGES = {
    "uz": UZ,
    "ru": RU,
}

current_lang = "uz"   # default


def _looks_broken(text: str) -> bool:
    if not isinstance(text, str):
        return False
    bad_tokens = ("Рџ", "Р°", "СЃ", "вЂ", "Ð", "Ñ", "�")
    return any(token in text for token in bad_tokens)

def set_lang(lang):
    global current_lang
    current_lang = lang

def t(key):
    lang_map = LANGUAGES.get(current_lang, LANGUAGES["uz"])
    value = lang_map.get(key, key)
    if _looks_broken(value):
        fallback = LANGUAGES["uz"].get(key, key)
        return fallback if isinstance(fallback, str) else key
    return value
