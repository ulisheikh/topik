# -*- coding: utf-8 -*-
"""
TIL TIZIMI
Foydalanuvchi tilini boshqarish
"""

import json
import os
from .texts import TEXTS
from config import SETTINGS_FILE, DEFAULT_LANGUAGE

def load_user_settings():
    """Foydalanuvchi sozlamalarini yuklash"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_user_settings(settings):
    """Foydalanuvchi sozlamalarini saqlash"""
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)

def get_user_language(user_id):
    """Foydalanuvchi tilini olish"""
    settings = load_user_settings()
    return settings.get(str(user_id), {}).get('language', DEFAULT_LANGUAGE)

def set_user_language(user_id, language):
    """Foydalanuvchi tilini o'rnatish"""
    settings = load_user_settings()
    if str(user_id) not in settings:
        settings[str(user_id)] = {}
    settings[str(user_id)]['language'] = language
    save_user_settings(settings)

def get_text(user_id, key, **kwargs):
    """Matnni foydalanuvchi tilida olish"""
    lang = get_user_language(user_id)
    text = TEXTS.get(lang, TEXTS['uz']).get(key, key)
    
    # Formatni qo'llash
    if kwargs:
        try:
            text = text.format(**kwargs)
        except:
            pass
    
    return text