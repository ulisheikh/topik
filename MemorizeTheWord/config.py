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
EXAM_WORDS_PER_FILE = 25  # Har bir listda 25 ta so'z (qator balandligi shu songa qarab hisoblab, A5 balandligini to'liq to'ldiradi)
TEMP_DIR = "temp"  # Vaqtinchalik fayllar

# ============================================
# PDF SOZLAMALARI
# ============================================
# Har bir PDF - A4 o'lchamda, "kitob shaklida" ikki yonga (chap/o'ng) bo'lib chiqadi.
# Har bir yon aynan A5 o'lchamida (14.8 x 21 sm) bo'ladi - ya'ni bitta A4 varaqda
# ikkita "kitob sahifasi" yonma-yon joylashadi.
PDF_HALF_WIDTH_CM = 14.8    # Har bir yon (A5) kengligi
PDF_HALF_HEIGHT_CM = 21.0   # Har bir yon (A5) balandligi
PDF_MARGIN_CM = 0.8         # Har bir yonning ichki chegarasi (chap/o'ng)

# Raqam (번호) ustuni - qisqa joy
PDF_COL_NUMBER_WIDTH_CM = 1.0

# Oddiy (savol/javob) rejim uchun boshlang'ich nisbat - javob ustuni bo'sh
# (qo'lda yozish uchun), shuning uchun unga ko'proq joy beriladi.
# DIQQAT: bu faqat BOSHLANG'ICH (minimal) nisbat - agar savol ustunidagi
# so'zlar (masalan uz_to_kr rejimida o'zbekcha so'zlar) uzunroq bo'lsa,
# exam_generator.py buni avtomatik kattalashtiradi, chunki aks holda
# so'zlar ko'p qatorga bo'linib PDF balandligiga sig'may qolishi mumkin.
PDF_QUESTION_RATIO = 0.42
PDF_ANSWER_RATIO = 0.58

# Javob (yozish uchun bo'sh) ustuni qanchalik torayishi mumkinligining
# pastki chegarasi - savol ustuni qanchalik uzun bo'lishidan qat'iy nazar
# javob ustuni bu nisbatdan tor bo'lmaydi.
PDF_ANSWER_MIN_RATIO = 0.35

# Ikki tilda (한국어 | O'zbekcha) jadval uchun - ustun kengligi so'zlarning
# HAQIQIY uzunligiga qarab AVTOMATIK hisoblanadi (odatda o'zbekcha so'zlar
# uzunroq bo'lgani uchun uning ustuni sal kengroq chiqadi; agar uzunliklar
# teng bo'lsa - ustunlar ham teng bo'lib qoladi). Bu min/max faqat haddan
# tashqari qiyshayib ketmasligi uchun chegara:
PDF_BILINGUAL_MIN_RATIO = 0.35
PDF_BILINGUAL_MAX_RATIO = 0.65

# ADMIN PASSWORD (exam uchun)
EXAM_ADMIN_PASSWORD = "admin123"  # O'zgartiring!