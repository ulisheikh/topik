# -*- coding: utf-8 -*-
"""
CONFIGURATION FILE
Bot sozlamalari
"""

import os

# ============================================
# BOT TOKEN
# ============================================
TOKEN = os.getenv("BOT_TOKEN", "8046756811:AAG7GOZleyqcsMXhv4__uFHWDhzPtYJMV8U")

# ============================================
# ADMIN ID
# ============================================
ADMIN_ID = 5830567800

# ============================================
# PAROLLAR
# ============================================
DEFAULT_USER_PASSWORD = "5555"
DEFAULT_ADMIN_PASSWORD = "7777"

# ============================================
# PAPKALAR (Absolyut yo'llar)
# ============================================
# Script joylashgan papka
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database papkasi
DATABASE_DIR = os.path.join(BASE_DIR, "database")

# User ma'lumotlari papkasi
USER_DATA_DIR = os.path.join(BASE_DIR, "user_data")

# Backup papkasi
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")

# ============================================
# FAYLLAR
# ============================================
# Parollar fayli
PASSWORDS_FILE = os.path.join(DATABASE_DIR, "passwords.json")

# User sessiyalari
SESSIONS_FILE = os.path.join(DATABASE_DIR, "user_sessions.json")

# User sozlamalari
SETTINGS_FILE = os.path.join(DATABASE_DIR, "user_settings.json")

# User ma'lumotlari
USERS_INFO_FILE = os.path.join(DATABASE_DIR, "users_info.json")

# ============================================
# SOZLAMALAR
# ============================================
# DEFAULT TIL
DEFAULT_LANGUAGE = "uz"

# MONITORING
BATTERY_WARNING_PERCENT = 10
RAM_WARNING_PERCENT = 90
BACKUP_CLEANUP_HOURS = 12

# Session muddati (soatlarda)
SESSION_TIMEOUT = 24  # 24 soat

# Backup muddati (kunlarda)
BACKUP_RETENTION_DAYS = 7  # 7 kun

# Maksimal noto'g'ri urinishlar
MAX_LOGIN_ATTEMPTS = 5

# Blok muddati (daqiqalarda)
BLOCK_DURATION = 5  # 5 daqiqa

# ============================================
# PAPKALARNI YARATISH
# ============================================
os.makedirs(DATABASE_DIR, exist_ok=True)
os.makedirs(USER_DATA_DIR, exist_ok=True)
os.makedirs(BACKUPS_DIR, exist_ok=True)