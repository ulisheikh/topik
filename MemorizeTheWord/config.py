
# Database path
import os
# User database yo'li
USER_DB_PATH = "database/users.db"

# Yangi holati (to'g'risi):
DICTIONARY_BASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "DictionaryBot", "user_data")

# Languages
LANGUAGES = {
    "uz": "🇺🇿 O'zbekcha",
    "en": "🇺🇸 English",
    "kr": "🇰🇷 한국어"
}

# Avtomatik rejim sozlamalari
AUTO_MODE_INTERVAL = 900  # 15 minut (sekundlarda: 15 * 60 = 900)
AUTO_MODE_WORDS_MIN = 10  # Minimal so'zlar soni
AUTO_MODE_WORDS_MAX = 15  # Maksimal so'zlar soni

# EXAM TIZIMI
EXAM_AUTO_TIME = "05:00"  # Soat 05:00
EXAM_WORDS_PER_FILE = 20  # Har bir faylda 23 ta so'z
TEMP_DIR = "temp"  # Vaqtinchalik fayllar

# WORD JADVAL O'LCHAMLARI (santimetr)
WORD_COL_NUMBER_WIDTH = 1.2   # 번호 ustuni
WORD_COL_QUESTION_WIDTH = 5.0  # 질문 ustuni
WORD_COL_ANSWER_WIDTH = 7.0    # 답안 ustuni
WORD_ROW_HEIGHT = 0.8          # Qator balandligi

# Word o'lchamlari (A5)
A5_WIDTH_CM = 14.8
A5_HEIGHT_CM = 21.0

# ADMIN PASSWORD (exam uchun)
EXAM_ADMIN_PASSWORD = "admin123"  # O'zgartiring!