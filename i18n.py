from locales.ru import RU
from locales.uz import UZ

LANGUAGES = {
    "uz": UZ,
    "ru": RU,
}

current_lang = "uz"   # default

def set_lang(lang):
    global current_lang
    current_lang = lang

def t(key):
    return LANGUAGES[current_lang].get(key, key)
