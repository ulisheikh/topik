import asyncio
import random
import os
import json
import time as time_module
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router, BaseMiddleware
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile,
    BotCommand,
    BotCommandScopeDefault,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Callable, Dict, Any, Awaitable

from database.db import UserDatabase
from utils.db_handler import DictionaryHandler
from utils.exam_generator import create_exam_word, split_words_into_groups, create_exam_word_bilingual
from utils.exam_keyboards import get_exam_main_keyboard, get_exam_star_direction_keyboard
#--------token----------
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from bot_tokens import MEMO_BOT_TOKEN
from config import  DICTIONARY_BASE_PATH, USER_DB_PATH, EXAM_AUTO_TIME, EXAM_WORDS_PER_FILE

# ADMIN_PASSWORD config faylida ikki xil nom bilan bo'lishi mumkin - ikkisini ham qo'llab-quvvatlaymiz
try:
    from config import ADMIN_PASSWORD
except ImportError:
    from config import EXAM_ADMIN_PASSWORD as ADMIN_PASSWORD


# ==================== FSM STATES ====================

class GameModeState(StatesGroup):
    selecting_mode = State()
    selecting_topic = State()
    selecting_section = State()
    waiting_for_range = State()
    playing = State()

class AutoPlayState(StatesGroup):
    selecting_time = State()
    selecting_mode = State()
    selecting_topic = State()
    selecting_section = State()
    playing = State()

class AdminState(StatesGroup):
    waiting_password = State()
    waiting_block_reason = State()


# ==================== BOT VA ROUTER ====================

bot = Bot(token=MEMO_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

print(f"\n{'='*50}")
print(f"📂 Hozirgi papka: {os.getcwd()}")
print(f"📂 Dictionary path: {DICTIONARY_BASE_PATH}")
print(f"📂 Mavjudmi: {os.path.exists(DICTIONARY_BASE_PATH)}")
if os.path.exists(DICTIONARY_BASE_PATH):
    print(f"📄 Fayllar: {os.listdir(DICTIONARY_BASE_PATH)}")
print(f"{'='*50}\n")

dict_handler = DictionaryHandler(DICTIONARY_BASE_PATH)
user_db = UserDatabase(USER_DB_PATH)

# Global so'zlar tracking (umumiy rejim uchun)
user_word_pool = {}


# ==================== MATNLAR ====================

ALL_TEXTS = {
    "uz": {
        "choose_language": "🌐 Tilni tanlang:",
        "language_changed": "✅ Til muvaffaqiyatli o'zgartirildi!",
        "main_menu": "📋 Asosiy menyu:",
        "game_mode": "🎮 O'yin boshlash",
        "chapters": "📂 Bo'limlar",
        "settings": "⚙️ Sozlamalar",
        "statistics": "📊 Statistika",
        "admin_panel": "🔐 Admin Panel",
        "back": "◀️ Orqaga",
        "back_to_menu": "🏠 Asosiy menyu",
        "about_bot_btn": "ℹ️ Bot haqida",
        "change_language": "🌐 Tilni o'zgartirish",
        "stop_game": "🛑 To'xtatish",
        "settings_menu": "⚙️ <b>Sozlamalar menyusi</b>\n\nBu yerda tilni o'zgartirishingiz yoki bot sozlamalarini tahrirlashingiz mumkin:",
        "format_hint": "Format: [Savol]-[So'zlar soni]",
        "select_chapter_title": "📚 <b>{topic}-Topik | {section}</b>",
        "start_message": "🎓 <b>Memorize Bot'ga xush kelibsiz!</b>\n\nBu bot TOPIK so'zlarini smart tarzda yodlashga yordam beradi.\n\n📊 <b>Bot ma'lumotlari:</b>\n👥 Foydalanuvchilar: {users}\n📚 Topiklar: {topics}\n📖 Jami so'zlar: {words}\n\nQuyidagi tugmalardan foydalaning! 👇",
        "my_stats": "📊 <b>Sizning statistikangiz:</b>\n\n✅ To'g'ri javoblar: {correct}\n❌ Noto'g'ri javoblar: {wrong}\n⏱ Faol vaqt: {time} daqiqa\n🏆 Reyting: {rank}/{total}",
        "bot_statistics": "📈 <b>Bot Statistikasi:</b>\n\n👥 Jami foydalanuvchilar: {users}\n📚 Bazadagi so'zlar: {words}",
        "about_bot": (
            "ℹ️ <b>Bot haqida:</b>\n\n"
            "📌 Versiya: 2.0\n"
            "🔧 Texnologiya: Aiogram 3\n"
            "🎯 Maqsad: TOPIK so'zlarini yodlash\n\n"
            "🎮 O'yin rejimi - cheksiz mashq\n"
            "📂 Bo'limlar - Topik bo'yicha taqsimlangan\n"
            "📊 Statistika - Natijalarni kuzatish\n"
            "⏰ Avtomatik - Rejali yodlash\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📖 <b>FOYDALANISH YO'RIQNOMASI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>➕ SO'Z QO'SHISH:</b>\n"
            "Botga shunchaki yozing:\n"
            "<code>안녕 salom</code>\n\n"
            "<b>⭐ YULDUZLI SO'Z qo'shish:</b>\n"
            "<code>*안녕 salom</code>  ← * bilan boshlang\n\n"
            "<b>🎮 /game — SO'Z O'YINI:</b>\n"
            "• <b>🌍 Umumiy rejim</b> — barcha so'zlaringizdan tasodifiy\n"
            "• <b>🎯 Belgilangan rejim</b> — topik va bo'lim tanlaysiz\n"
            "• <b>⭐ Yulduzli so'zlar</b> — faqat * bilan belgilanganlar\n"
            "• <b>❌ Bilmaydigan so'zlar</b> — avval bilmagan so'zlar (**)\n\n"
            "O'yin jarayonida:\n"
            "✅ <b>Bilaman</b> — bilsangiz bosing, keyingisiga o'tadi\n"
            "❌ <b>Bilmayman</b> — so'z bilmaydiganlar ro'yxatiga tushadi\n"
            "🛑 <b>To'xtatish</b> — o'yinni yakunlaydi\n"
            "👁 <b>So'zni ko'rish</b> — javobni ko'rish (statistikaga ta'sir qilmaydi)\n\n"
            "<b>⏰ /avtogame — AVTOMATIK REJIM:</b>\n"
            "Vaqt oralig'i tanlaysiz (5/10/15/30/60 daqiqa)\n"
            "Har shu vaqtda 10 ta so'z avtomatik yuboriladi\n\n"
            "<b>📂 /bo'limlar — BO'LIMLAR:</b>\n"
            "Topik → Bo'lim → Savol bo'yicha so'zlarni ko'rish\n\n"
            "<b>📄 /exam_doc — IMTIHON FAYLI:</b>\n"
            "So'zlaringizdan Word formatida imtihon varaqasi yaratadi\n"
            "Har bir so'z uchun 4 ta variant (test shaklida)\n\n"
            "<b>📥 /download_words — LUG'ATNI YUKLAB OLISH:</b>\n"
            "• Word (한국어 → O'zbekcha)\n"
            "• Word (O'zbekcha → 한국어)\n"
            "• Word (ikki tilda birga)\n"
            "• JSON format\n\n"
            "<b>📊 Statistika:</b>\n"
            "Asosiy menyu → Statistika tugmasidan ko'rasiz\n"
            "To'g'ri/noto'g'ri javoblar va reyting ko'rsatiladi"
        ),
        "game_select_mode": "🎮 <b>O'yin rejimini tanlang:</b>",
        "btn_general_mode": "🌍 Umumiy rejim",
        "btn_custom_mode": "🎯 Belgilangan rejim",
        "btn_star_mode": "⭐ Yulduzli so'zlar",
        "btn_unknown_mode": "❌ Bilmaydigan so'zlar",
        "no_star_words": "❌ Yulduzli so'zlar yo'q!\n\n💡 So'z qo'shishda * bilan boshlang:\n<code>*안녕 salom</code>",
        "no_unknown_words": "❌ Bilmaydigan so'zlar yo'q! Hammasini bilasiz 🎉",
        "game_select_topic": "📚 <b>Topikni tanlang:</b>",
        "game_select_section": "📖 <b>Bo'limni tanlang:</b>\n<i>{topic}</i>",
        "game_select_section_only": "📖 <b>{topic}</b>\n\nBo'limni tanlang:",
        "game_finished": "🎊 <b>O'yin tugadi!</b>\n\n✅ To'g'ri: <b>{correct}</b>\n❌ Noto'g'ri: <b>{wrong}</b>",
        "game_stopped": "🛑 <b>O'yin to'xtatildi!</b>\n\n✅ To'g'ri: {correct}\n❌ Noto'g'ri: {wrong}",
        "auto_select_time": "⏰ <b>Avtomatik rejim sozalamalari:</b>\n\nNecha daqiqada so'zlar kelsin?",
        "auto_time_set": "✅ Har {time} daqiqada 10 ta so'z yuboriladi!",
        "btn_5min": "⏱ 5 daqiqa", "btn_10min": "⏱ 10 daqiqa", "btn_15min": "⏱ 15 daqiqa", "btn_30min": "⏱ 30 daqiqa", "btn_60min": "⏱ 60 daqiqa",
        "no_words": "❌ So'zlar topilmadi!",
        "no_topics": "❌ Topiklar yo'q!",
        "no_sections": "❌ Bo'limlar yo'q!",
        "admin_welcome": "✅ Admin panelga xush kelibsiz!",
        "admin_enter_password": "🔐 Admin panelga kirish uchun parolni kiriting:",
        "admin_wrong_password": "❌ Noto'g'ri parol!",
        "admin_user_blocked": "✅ Foydalanuvchi bloklandi!",
        "admin_user_unblocked": "✅ Foydalanuvchi blokdan chiqarildi!",
        "admin_users": "👥 Foydalanuvchilar",
        "admin_user_list": "👥 <b>Foydalanuvchilar ro'yxati:</b>",
        "admin_enter_block_reason": "✏️ Bloklash sababini yozing (yoki /skip bosing):",
        "admin_block": "🚫 Bloklash",
        "admin_unblock": "✅ Blokdan chiqarish",
        "chapters_select_topic": "📚 <b>Topikni tanlang:</b>",
        "chapters_select_section": "📖 <b>{topic}</b>\n\nBo'limni tanlang:",
        "chapters_select_chapter": "📖 <b>{topic} > {section}</b>\n\nSavolni tanlang:",
        "chapters_words": "📝 <b>{topic} > {section} > {chapter}</b>\n\nSo'zlar:\n\n{words}",
        "chapters_no_words": "❌ Bu bo'limda so'zlar yo'q!",
        "blocked_message": "🚫 Siz bloklangansiz.\nSabab: {reason}",
    },
    "ko": {
        "choose_language": "🌐 언어 선택:",
        "language_changed": "✅ 언어가 성공적으로 변경되었습니다!",
        "main_menu": "📋 메인 메뉴:",
        "game_mode": "🎮 게임 시작",
        "chapters": "📂 섹션",
        "settings": "⚙️ 설정",
        "statistics": "📊 통계",
        "admin_panel": "🔐 관리자 패널",
        "back": "◀️ 뒤로",
        "back_to_menu": "🏠 메인 메뉴",
        "about_bot_btn": "ℹ️ 봇 정보",
        "change_language": "🌐 언어 변경",
        "stop_game": "🛑 중지",
        "settings_menu": "⚙️ <b>설정 메뉴</b>\n\n여기에서 언어를 변경하거나 봇 설정을 편집할 수 있습니다:",
        "format_hint": "형식: [문항]-[단어 수]",
        "select_chapter_title": "📚 <b>{topic}-토픽 | {section}</b>",
        "start_message": "🎓 <b>Memorize Bot에 오신 것을 환영합니다!</b>\n\n이 봇은 TOPIK 단어를 스마트하게 암기하는 데 도움을 줍니다.\n\n📊 <b>봇 정보:</b>\n👥 사용자: {users}\n📚 토픽: {topics}\n📖 총 단어: {words}\n\n아래 버튼을 사용하세요! 👇",
        "my_stats": "📊 <b>내 통계:</b>\n\n✅ 정답: {correct}\n❌ 오답: {wrong}\n⏱ 활동 시간: {time}분\n🏆 순위: {rank}/{total}",
        "bot_statistics": "📈 <b>봇 통계:</b>\n\n👥 총 사용자: {users}\n📚 데이터베이스 단어: {words}",
        "about_bot": (
            "ℹ️ <b>봇 정보:</b>\n\n"
            "📌 버전: 2.0\n"
            "🔧 기술: Aiogram 3\n"
            "🎯 목적: TOPIK 단어 암기\n\n"
            "🎮 게임 모드 - 무한 연습\n"
            "📂 섹션 - 토픽별 분류\n"
            "📊 통계 - 결과 추적\n"
            "⏰ 자동 - 정기 학습\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📖 <b>사용 가이드</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>➕ 단어 추가:</b>\n"
            "봇에 바로 입력:\n"
            "<code>안녕 salom</code>\n\n"
            "<b>⭐ 별표 단어 추가:</b>\n"
            "<code>*안녕 salom</code>  ← *로 시작\n\n"
            "<b>🎮 /game — 단어 게임:</b>\n"
            "• <b>🌍 일반 모드</b> — 전체 단어에서 랜덤\n"
            "• <b>🎯 맞춤 모드</b> — 토픽과 섹션 선택\n"
            "• <b>⭐ 별표 단어</b> — *로 표시된 단어만\n"
            "• <b>❌ 모르는 단어</b> — **로 표시된 단어만\n\n"
            "게임 중:\n"
            "✅ <b>알아요</b> — 다음 단어로 넘어감\n"
            "❌ <b>몰라요</b> — 모르는 단어 목록에 추가됨\n"
            "🛑 <b>중지</b> — 게임 종료\n"
            "👁 <b>단어 보기</b> — 정답 확인 (통계 영향 없음)\n\n"
            "<b>⏰ /avtogame — 자동 모드:</b>\n"
            "간격 선택 (5/10/15/30/60분)\n"
            "해당 시간마다 단어 10개 자동 전송\n\n"
            "<b>📂 /bo'limlar — 섹션:</b>\n"
            "토픽 → 섹션 → 문항별 단어 보기\n\n"
            "<b>📄 /exam_doc — 시험 파일:</b>\n"
            "Word 형식으로 시험지 생성\n"
            "각 단어마다 4개 선택지\n\n"
            "<b>📥 /download_words — 사전 다운로드:</b>\n"
            "• Word (한국어 → 우즈베크어)\n"
            "• Word (우즈베크어 → 한국어)\n"
            "• Word (두 언어 함께)\n"
            "• JSON 형식\n\n"
            "<b>📊 통계:</b>\n"
            "메인 메뉴 → 통계 버튼에서 확인\n"
            "정답/오답 수와 순위 표시"
        ),
        "game_select_mode": "🎮 <b>게임 모드 선택:</b>",
        "btn_general_mode": "🌍 일반 모드",
        "btn_custom_mode": "🎯 맞춤 모드",
        "btn_star_mode": "⭐ 별표 단어",
        "btn_unknown_mode": "❌ 모르는 단어",
        "no_star_words": "❌ 별표 단어가 없습니다!\n\n💡 단어 추가 시 *로 시작:\n<code>*안녕 salom</code>",
        "no_unknown_words": "❌ 모르는 단어가 없습니다! 모두 알고 있습니다 🎉",
        "game_select_topic": "📚 <b>토픽 선택:</b>",
        "game_select_section": "📖 <b>섹션 선택:</b>\n<i>{topic}</i>",
        "game_select_section_only": "📖 <b>{topic}</b>\n\n섹션 선택:",
        "game_finished": "🎊 <b>게임 종료!</b>\n\n✅ 정답: <b>{correct}</b>\n❌ 오답: <b>{wrong}</b>",
        "game_stopped": "🛑 <b>게임 중지!</b>\n\n✅ 정답: {correct}\n❌ 오답: {wrong}",
        "auto_select_time": "⏰ <b>자동 모드 설정:</b>\n\n몇 분마다 단어를 받으시겠습니까?",
        "auto_time_set": "✅ {time}분마다 10개 단어가 전송됩니다!",
        "btn_5min": "⏱ 5분", "btn_10min": "⏱ 10분", "btn_15min": "⏱ 15분", "btn_30min": "⏱ 30분", "btn_60min": "⏱ 60분",
        "no_words": "❌ 단어를 찾을 수 없습니다!",
        "no_topics": "❌ 토픽 없음!",
        "no_sections": "❌ 섹션 없음!",
        "admin_welcome": "✅ 관리자 패널에 오신 것을 환영합니다!",
        "admin_enter_password": "🔐 관리자 패널에 접근하려면 비밀번호를 입력하세요:",
        "admin_wrong_password": "❌ 잘못된 비밀번호!",
        "admin_user_blocked": "✅ 사용자가 차단되었습니다!",
        "admin_user_unblocked": "✅ 사용자 차단이 해제되었습니다!",
        "admin_users": "👥 사용자",
        "admin_user_list": "👥 <b>사용자 목록:</b>",
        "admin_enter_block_reason": "✏️ 차단 이유를 입력하세요 (또는 /skip):",
        "admin_block": "🚫 차단",
        "admin_unblock": "✅ 차단 해제",
        "chapters_select_topic": "📚 <b>토픽 선택:</b>",
        "chapters_select_section": "📖 <b>{topic}</b>\n\n섹션 선택:",
        "chapters_select_chapter": "📖 <b>{topic} > {section}</b>\n\n질문 선택:",
        "chapters_words": "📝 <b>{topic} > {section} > {chapter}</b>\n\n단어:\n\n{words}",
        "chapters_no_words": "❌ 이 섹션에 단어가 없습니다!",
        "blocked_message": "🚫 차단되었습니다.\n이유: {reason}",
    }
}

def get_text(lang, key, **kwargs):
    target_lang = "ko" if lang in ["ko", "kr"] else "uz"
    text = ALL_TEXTS.get(target_lang, {}).get(key, f"Missing key: {key}")
    try:
        return text.format(**kwargs)
    except KeyError:
        return text


# ==================== WORD POOL MANAGER (umumiy rejim) ====================

def get_next_word(user_id: int):
    """Takrorlanmaslik uchun so'z olish (umumiy rejim uchun pool asosida)"""
    all_words = dict_handler.get_all_words(user_id)
    if not all_words:
        return None
    if user_id not in user_word_pool or len(user_word_pool[user_id]) == 0:
        user_word_pool[user_id] = [w['id'] for w in all_words if 'id' in w]
        random.shuffle(user_word_pool[user_id])
    word_id = user_word_pool[user_id].pop(0)
    word = next((w for w in all_words if w.get('id') == word_id), None)
    return word if word else random.choice(all_words)


# ==================== KEYBOARDS ====================

def get_main_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Asosiy menyu klaviaturasi"""
    keyboard = [
        [KeyboardButton(text="/start")],
        [KeyboardButton(text="/game"), KeyboardButton(text="/avtogame")],
        [KeyboardButton(text="/bo'limlar"), KeyboardButton(text="/exam_doc")],
        [KeyboardButton(text="/download_words")],
        [KeyboardButton(text="/sozlamalar")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Inline asosiy menyu"""
    keyboard = [
        [InlineKeyboardButton(text=get_text(lang, "game_mode"), callback_data="start_game")],
        [InlineKeyboardButton(text=get_text(lang, "chapters"), callback_data="chapters_main")],
        [InlineKeyboardButton(text=get_text(lang, "statistics"), callback_data="show_stats")],
        [InlineKeyboardButton(text=get_text(lang, "settings"), callback_data="settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_game_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    O'YIN PAYTIDAGI YAGONA KLAVIATURA.
    Talab qilingan ko'rinish:
        [ ✅ Bilaman ]   [ ❌ Bilmayman ]
                [ 🛑 To'xtatish ]
    Hammasi REPLY keyboard - hech qanday inline tugma yo'q.
    """
    keyboard = [
        [KeyboardButton(text="✅ Bilaman"), KeyboardButton(text="❌ Bilmayman")],
        [KeyboardButton(text="🛑 To'xtatish")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_chapters_topics_keyboard(user_id: int, lang: str) -> InlineKeyboardMarkup:
    topics = dict_handler.get_all_topics(user_id)
    keyboard = []
    for topic in topics:
        keyboard.append([InlineKeyboardButton(text=f"📚 {topic}", callback_data=f"topic_{topic}")])
    keyboard.append([InlineKeyboardButton(text=get_text(lang, "back"), callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_chapters_sections_keyboard(user_id: int, topic: str, lang: str) -> InlineKeyboardMarkup:
    sections = dict_handler.get_topic_sections(user_id, topic)
    keyboard = []
    for section in sections:
        keyboard.append([InlineKeyboardButton(text=f"📖 {section.title()}", callback_data=f"section_{topic}_{section}")])
    keyboard.append([InlineKeyboardButton(text=get_text(lang, "back"), callback_data="chapters_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_language_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")],
        [InlineKeyboardButton(text="🇰🇷 한국어", callback_data="lang_kr")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_settings_keyboard(lang: str, is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    if is_admin:
        buttons.append([InlineKeyboardButton(text=get_text(lang, "admin_panel"), callback_data="admin_panel")])
    buttons.extend([
        [InlineKeyboardButton(text=get_text(lang, "change_language"), callback_data="change_language")],
        [InlineKeyboardButton(text=get_text(lang, "about_bot_btn"), callback_data="about_bot")],
        [InlineKeyboardButton(text=get_text(lang, "back_to_menu"), callback_data="back_to_menu")]
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_keyboard(lang: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text=get_text(lang, "admin_users"), callback_data="admin_users")],
        [InlineKeyboardButton(text=get_text(lang, "statistics"), callback_data="admin_stats")],
        [InlineKeyboardButton(text=get_text(lang, "back_to_menu"), callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_user_action_keyboard(user_id: int, is_blocked: bool, lang: str) -> InlineKeyboardMarkup:
    if is_blocked:
        button_text = get_text(lang, "admin_unblock")
        callback_data = f"unblock_{user_id}"
    else:
        button_text = get_text(lang, "admin_block")
        callback_data = f"block_{user_id}"
    keyboard = [
        [InlineKeyboardButton(text=button_text, callback_data=callback_data)],
        [InlineKeyboardButton(text=get_text(lang, "back"), callback_data="admin_users")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ==================== MIDDLEWARE ====================

class BlockCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        is_blocked, reason = await user_db.is_blocked(user_id)
        if is_blocked:
            lang = await user_db.get_language(user_id) or "uz"
            reason_text = reason or "Sabab ko'rsatilmagan"
            await event.answer(get_text(lang, "blocked_message", reason=reason_text))
            return
        return await handler(event, data)

router.message.middleware(BlockCheckMiddleware())


# ==================== ASOSIY HANDLERLAR ====================

@router.message(Command("download_words"))
async def cmd_download_words(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()
    all_words_data = dict_handler.get_all_words(user_id)
    if not all_words_data:
        await message.answer("❌ Sizda hali so'zlar yo'q!")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Word (한국어→우즈베크어)", callback_data="download_all:word_ko_uz")],
        [InlineKeyboardButton(text="📄 Word (우즈베크어→한국어)", callback_data="download_all:word_uz_ko")],
        [InlineKeyboardButton(text="📋 JSON File", callback_data="download_all:json")],
        [InlineKeyboardButton(text="📄 Word (🇰🇷 + 🇺🇿 tarjima bilan)", callback_data="download_all:word_both")],
        [InlineKeyboardButton(text="◀️ Bekor qilish", callback_data="cancel_download")]
    ])
    await message.answer(
        f"📥 <b>Lug'atni yuklash</b>\n\n📊 Jami so'zlar: {len(all_words_data)}\n\nQaysi formatda yuklamoqchisiz?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    await user_db.add_user(
        user_id=user_id,
        username=message.from_user.username or "unknown",
        first_name=message.from_user.first_name or "User"
    )
    lang = await user_db.get_language(user_id) or "uz"
    total_users = await user_db.get_total_users()
    total_topics = len(dict_handler.get_all_topics(user_id))
    total_words = dict_handler.get_total_words(user_id)
    await message.answer(
        get_text(lang, "start_message", users=total_users, topics=total_topics, words=total_words),
        parse_mode="HTML",
        reply_markup=get_main_keyboard(lang)
    )
    await message.answer(get_text(lang, "main_menu"), reply_markup=get_main_menu_keyboard(lang))


@router.message(Command("help"))
async def cmd_help(message: Message):
    user_id = message.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    if lang == "uz":
        help_text = """📚 <b>MEMORIZE BOT - YORDAM</b>

<b>🎮 ASOSIY KOMANDALAR:</b>
/start - Botni qayta ishga tushirish
/help - Bu yordam matni
/game - So'z o'yinini boshlash
/avtogame - Avtomatik rejim (vaqt bo'yicha)
/bo'limlar - Topiklar va so'zlarni ko'rish
/exam_doc - Imtihon fayli yaratish
/download_words - Lug'atni yuklash
/sozlamalar - Til va sozlamalar

<b>⭐ YULDUZLI SO'ZLAR:</b>
• So'z qo'shishda <code>*</code> bilan boshlang
• Masalan: <code>*안녕 salom</code>

<b>🎮 O'YIN QANDAY ISHLAYDI:</b>
• So'z ko'rsatiladi, siz ichingizda javobni o'ylaysiz
• ✅ Bilaman - bilsangiz, keyingi so'zga o'tadi
• ❌ Bilmayman - bilmasangiz, so'z "bilmaydiganlar" ro'yxatiga tushadi va qayta-qayta beriladi
• 🛑 To'xtatish - o'yinni tugatish

💡 <i>Har yerdan e. va s. ishlatishingiz mumkin!</i>"""
    else:
        help_text = """📚 <b>MEMORIZE BOT - 도움말</b>

<b>🎮 기본 명령어:</b>
/start - 봇 재시작
/help - 이 도움말
/game - 단어 게임 시작
/avtogame - 자동 모드 (시간별)
/bo'limlar - 토픽 및 단어 보기
/exam_doc - 시험 파일 만들기
/download_words - 사전 다운로드
/sozlamalar - 언어 및 설정

<b>⭐ 별표 단어:</b>
• 단어 추가 시 <code>*</code>로 시작
• 예: <code>*안녕 salom</code>"""
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("sozlamalar"))
async def cmd_settings(message: Message):
    user_id = message.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    is_admin = await user_db.is_admin(user_id)
    await message.answer(
        get_text(lang, "settings_menu"),
        reply_markup=get_settings_keyboard(lang, is_admin),
        parse_mode="HTML"
    )


@router.message(Command("bo'limlar"))
async def cmd_chapters(message: Message):
    user_id = message.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    await message.answer(
        get_text(lang, "chapters_select_topic"),
        reply_markup=get_chapters_topics_keyboard(user_id, lang),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("lang_"))
async def set_language_callback(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    await user_db.set_language(user_id, lang)
    await callback.message.edit_text(
        get_text(lang, "language_changed"),
        reply_markup=get_main_menu_keyboard(lang)
    )
    await callback.message.answer(get_text(lang, "main_menu"), reply_markup=get_main_keyboard(lang))
    await callback.answer()


@router.callback_query(F.data == "show_stats")
async def show_my_stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    stats = await user_db.get_statistics(user_id)
    rank, total = await user_db.get_ranking(user_id)
    time_minutes = stats['active_time'] // 60
    await callback.message.edit_text(
        get_text(lang, "my_stats", correct=stats['correct'], wrong=stats['wrong'], time=time_minutes, rank=rank, total=total),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, "back_to_menu"), callback_data="back_to_menu")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "settings")
async def settings_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    is_admin = await user_db.is_admin(user_id)
    await callback.message.edit_text(
        get_text(lang, "settings_menu"),
        reply_markup=get_settings_keyboard(lang, is_admin),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "about_bot")
async def show_about(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    is_admin = await user_db.is_admin(user_id)
    await callback.message.edit_text(
        get_text(lang, "about_bot"),
        parse_mode="HTML",
        reply_markup=get_settings_keyboard(lang, is_admin)
    )
    await callback.answer()


@router.callback_query(F.data == "change_language")
async def change_lang_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    await callback.message.edit_text(get_text(lang, "choose_language"), reply_markup=get_language_keyboard())
    await callback.answer()


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    await callback.message.edit_text(get_text(lang, "main_menu"), reply_markup=get_main_menu_keyboard(lang))
    await callback.answer()


# ============================================
# /GAME — YANGI TIZIM (TUGMA ASOSIDA)
# ============================================
#
# Ishlash tartibi:
#   1. /game -> rejim tanlash (umumiy / belgilangan / yulduzli / bilmaydiganlar)
#   2. (agar kerak bo'lsa) topik -> bo'lim tanlash
#   3. yo'nalish tanlash (Uz->Ko yoki Ko->Uz)
#   4. So'z ko'rsatiladi (faqat savol, javob YO'Q)
#   5. Foydalanuvchi pastdagi REPLY tugmalardan birini bosadi:
#        ✅ Bilaman    -> statistika +1 to'g'ri, keyingi so'z
#        ❌ Bilmayman  -> so'z "bilmaydiganlar" ro'yxatiga belgilanadi (mark_as_unknown),
#                         statistika +1 xato, keyingi so'z
#        🛑 To'xtatish -> o'yin tugaydi, asosiy menyu qaytadi
#

def _build_question_text(word: dict, direction: str, q_count: int, mode: str, extra_info: str = "") -> str:
    """So'z savolini matn sifatida tayyorlash (javobsiz)"""
    korean = (word.get('korean') or '').lstrip('*')
    uzbek = (word.get('uzbek') or '').lstrip('*')

    if direction == "uz_ko":
        question = uzbek
        hint = "🇰🇷 Koreyschasi nima edi?"
    else:
        question = korean
        hint = "🇺🇿 O'zbekchasi nima edi?"

    prefix_map = {
        'star': "⭐",
        'unknown': "❌",
        'custom': "🎯",
        'general': "🎮",
    }
    prefix = prefix_map.get(mode, "🎮")

    text = (
        f"{prefix} <b>So'z #{q_count}{extra_info}</b>\n\n"
        f"❓ <b>{question}</b>\n"
        f"💡 {hint}\n\n"
        f"📍 {word.get('topic','?')} › {word.get('section','?')}"
    )
    return text


def get_reveal_keyboard() -> InlineKeyboardMarkup:
    """So'z savoli ostida chiqadigan yagona inline tugma"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👁 So'zni ko'rish", callback_data="reveal_word")]
    ])


@router.callback_query(F.data == "reveal_word")
async def reveal_word_callback(callback: CallbackQuery, state: FSMContext):
    """'So'zni ko'rish' tugmasi - javobni alert oynada ko'rsatadi"""
    data = await state.get_data()
    word = data.get('current_word')
    direction = data.get('direction', 'uz_ko')
    if not word:
        await callback.answer("❌ So'z topilmadi", show_alert=True)
        return
    korean = (word.get('korean') or '').lstrip('*')
    uzbek = (word.get('uzbek') or '').lstrip('*')
    answer = korean if direction == "uz_ko" else uzbek
    await callback.answer(f"✅ {answer}", show_alert=True)


async def _track_and_trim(state: FSMContext, chat_id: int, new_message_id: int, keep: int = 1):
    """Yuborilgan xabar ID'larini kuzatib, eskirganlarini o'chirib turish"""
    data = await state.get_data()
    ids = data.get('bot_msg_ids', [])
    ids.append(new_message_id)
    # Faqat oxirgi `keep` ta xabarni saqlab qolamiz, qolganini o'chiramiz
    while len(ids) > keep:
        old_id = ids.pop(0)
        try:
            await bot.delete_message(chat_id, old_id)
        except Exception:
            pass
    await state.update_data(bot_msg_ids=ids)


async def send_question_message(message_or_chat, state: FSMContext, user_id: int, text: str, setup_reply_kb: bool = False):
    """
    Savol xabarini yuborish: xabar ichida inline 'So'zni ko'rish' tugmasi bilan.
    Eski savol xabarini avtomatik o'chirib turadi (chat tarixini band qilmaslik uchun).

    setup_reply_kb=True bo'lsa (faqat o'yin BOSHLANISHIDA bir marta kerak):
    avval pastdagi Bilaman/Bilmayman/To'xtatish reply keyboardni o'rnatuvchi
    qisqa xabar yuboriladi, so'ng savol xabari inline tugma bilan yuboriladi.
    Telegramda reply keyboard bir marta o'rnatilgach doim pastda qolib turadi,
    shuning uchun keyingi savollarda setup_reply_kb=False bo'lishi kifoya.
    """
    send_fn = message_or_chat.answer if hasattr(message_or_chat, 'answer') else None

    if setup_reply_kb:
        if send_fn:
            await send_fn("🎮 O'yin boshlandi", reply_markup=get_game_reply_keyboard())
        else:
            await bot.send_message(user_id, "🎮 O'yin boshlandi", reply_markup=get_game_reply_keyboard())

    if send_fn:
        sent = await send_fn(text, reply_markup=get_reveal_keyboard(), parse_mode="HTML")
    else:
        sent = await bot.send_message(user_id, text, reply_markup=get_reveal_keyboard(), parse_mode="HTML")

    await _track_and_trim(state, user_id, sent.message_id, keep=1)
    return sent


async def auto_cleanup_loop():
    """Har 15 soniyada barcha faol o'yinchilar uchun eski bot xabarlarini tozalaydi"""
    while True:
        try:
            users = await user_db.get_all_users()
            for user in users:
                user_id = user['user_id']
                state_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
                fsm = FSMContext(storage=storage, key=state_key)
                current_state = await fsm.get_state()
                if current_state in (GameModeState.playing, AutoPlayState.playing):
                    data = await fsm.get_data()
                    ids = data.get('bot_msg_ids', [])
                    if len(ids) > 1:
                        # Oxirgi savol xabaridan tashqari hammasini o'chiramiz
                        keep_last = ids[-1]
                        for old_id in ids[:-1]:
                            try:
                                await bot.delete_message(user_id, old_id)
                            except Exception:
                                pass
                        await fsm.update_data(bot_msg_ids=[keep_last])
        except Exception as e:
            print(f"❌ auto_cleanup_loop xatosi: {e}")
        await asyncio.sleep(15)


async def _pick_word_for_mode(user_id: int, mode: str, topic=None, section=None):
    """Berilgan rejim bo'yicha bitta so'z tanlash"""
    if mode == 'star':
        return dict_handler.get_random_star_word(user_id)
    elif mode == 'unknown':
        unknown_list = dict_handler.get_unknown_words(user_id)
        return unknown_list[0] if unknown_list else None
    elif mode == 'custom':
        return dict_handler.get_random_word(user_id, topic=topic, section=section)
    else:  # general
        return dict_handler.get_random_word(user_id)


@router.message(Command("game"))
async def cmd_game(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    await state.clear()

    star_words = dict_handler.get_star_words(user_id)
    unknown_words = dict_handler.get_unknown_words(user_id)

    keyboard = [
        [InlineKeyboardButton(text=get_text(lang, "btn_general_mode"), callback_data="game_mode_general")],
        [InlineKeyboardButton(text=get_text(lang, "btn_custom_mode"), callback_data="game_mode_custom")]
    ]
    if star_words:
        keyboard.append([InlineKeyboardButton(
            text=f"⭐ Yulduzli so'zlar ({len(star_words)} ta)",
            callback_data="game_mode_star"
        )])
    if unknown_words:
        keyboard.append([InlineKeyboardButton(
            text=f"❌ Bilmaydigan so'zlar ({len(unknown_words)} ta)",
            callback_data="game_mode_unknown"
        )])

    await state.set_state(GameModeState.selecting_mode)
    await message.answer(get_text(lang, "game_select_mode"), reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")


@router.callback_query(F.data == "start_game")
async def inline_start_game(callback: CallbackQuery, state: FSMContext):
    """Asosiy menyudagi '🎮 O'yin boshlash' tugmasi orqali kirish - cmd_game bilan bir xil"""
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    await state.clear()

    star_words = dict_handler.get_star_words(user_id)
    unknown_words = dict_handler.get_unknown_words(user_id)

    keyboard = [
        [InlineKeyboardButton(text=get_text(lang, "btn_general_mode"), callback_data="game_mode_general")],
        [InlineKeyboardButton(text=get_text(lang, "btn_custom_mode"), callback_data="game_mode_custom")]
    ]
    if star_words:
        keyboard.append([InlineKeyboardButton(
            text=f"⭐ Yulduzli so'zlar ({len(star_words)} ta)",
            callback_data="game_mode_star"
        )])
    if unknown_words:
        keyboard.append([InlineKeyboardButton(
            text=f"❌ Bilmaydigan so'zlar ({len(unknown_words)} ta)",
            callback_data="game_mode_unknown"
        )])

    await state.set_state(GameModeState.selecting_mode)
    await callback.message.edit_text(get_text(lang, "game_select_mode"), reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()


# ---------- UMUMIY REJIM ----------

@router.callback_query(F.data == "game_mode_general")
async def game_general_mode(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 Uz → 🇰🇷 Ko", callback_data="game_dir_general_uz_ko")],
        [InlineKeyboardButton(text="🇰🇷 Ko → 🇺🇿 Uz", callback_data="game_dir_general_ko_uz")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="game_back_to_mode")]
    ])
    await callback.message.edit_text("🎮 <b>Tarjima yo'nalishini tanlang:</b>", reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("game_dir_general_"))
async def game_general_direction_selected(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    direction = callback.data.replace("game_dir_general_", "")

    word = dict_handler.get_random_word(user_id)
    if not word:
        await callback.answer(get_text(lang, "no_words"), show_alert=True)
        await state.clear()
        return

    await state.set_state(GameModeState.playing)
    await state.update_data(
        current_word=word, direction=direction, mode='general',
        start_time=datetime.now().timestamp(), question_count=1
    )

    text = _build_question_text(word, direction, 1, 'general')
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_question_message(callback.message, state, user_id, text, setup_reply_kb=True)
    await callback.answer()


# ---------- YULDUZLI SO'ZLAR REJIMI ----------

@router.callback_query(F.data == "game_mode_star")
async def game_star_mode(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    star_words = dict_handler.get_star_words(user_id)
    if not star_words:
        await callback.answer(get_text(lang, "no_star_words"), show_alert=True)
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 Uz → 🇰🇷 Ko", callback_data="game_dir_star_uz_ko")],
        [InlineKeyboardButton(text="🇰🇷 Ko → 🇺🇿 Uz", callback_data="game_dir_star_ko_uz")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="game_back_to_mode")]
    ])
    await callback.message.edit_text(
        f"⭐ <b>Yulduzli so'zlar: {len(star_words)} ta</b>\n\nTarjima yo'nalishini tanlang:",
        reply_markup=keyboard, parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("game_dir_star_"))
async def game_star_direction_selected(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    direction = callback.data.replace("game_dir_star_", "")

    word = dict_handler.get_random_star_word(user_id)
    if not word:
        await callback.answer(get_text(lang, "no_star_words"), show_alert=True)
        await state.clear()
        return

    await state.set_state(GameModeState.playing)
    await state.update_data(
        current_word=word, direction=direction, mode='star',
        start_time=datetime.now().timestamp(), question_count=1
    )

    text = _build_question_text(word, direction, 1, 'star')
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_question_message(callback.message, state, user_id, text, setup_reply_kb=True)
    await callback.answer()


# ---------- BILMAYDIGAN SO'ZLAR REJIMI ----------

@router.callback_query(F.data == "game_mode_unknown")
async def game_unknown_mode(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    unknown_words = dict_handler.get_unknown_words(user_id)
    if not unknown_words:
        await callback.answer(get_text(lang, "no_unknown_words"), show_alert=True)
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 Uz → 🇰🇷 Ko", callback_data="game_dir_unknown_uz_ko")],
        [InlineKeyboardButton(text="🇰🇷 Ko → 🇺🇿 Uz", callback_data="game_dir_unknown_ko_uz")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="game_back_to_mode")]
    ])
    await callback.message.edit_text(
        f"❌ <b>Bilmaydigan so'zlar: {len(unknown_words)} ta</b>\n\nTarjima yo'nalishini tanlang:",
        reply_markup=keyboard, parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("game_dir_unknown_"))
async def game_unknown_direction_selected(callback: CallbackQuery, state: FSMContext):
    direction = callback.data.replace("game_dir_unknown_", "")
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"

    unknown_words = dict_handler.get_unknown_words(user_id)
    if not unknown_words:
        await callback.answer(get_text(lang, "no_unknown_words"), show_alert=True)
        return

    word = unknown_words[0]
    await state.set_state(GameModeState.playing)
    await state.update_data(
        mode='unknown', direction=direction, current_word=word,
        unknown_queue=unknown_words, unknown_index=0,
        start_time=datetime.now().timestamp(), question_count=1
    )

    text = _build_question_text(word, direction, 1, 'unknown', extra_info=f"/{len(unknown_words)}")
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_question_message(callback.message, state, user_id, text, setup_reply_kb=True)
    await callback.answer()


# ---------- ORQAGA QAYTISH ----------

@router.callback_query(F.data == "game_back_to_mode")
async def game_back_to_mode(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"

    star_words = dict_handler.get_star_words(user_id)
    unknown_words = dict_handler.get_unknown_words(user_id)

    keyboard = [
        [InlineKeyboardButton(text=get_text(lang, "btn_general_mode"), callback_data="game_mode_general")],
        [InlineKeyboardButton(text=get_text(lang, "btn_custom_mode"), callback_data="game_mode_custom")]
    ]
    if star_words:
        keyboard.append([InlineKeyboardButton(text=f"⭐ Yulduzli so'zlar ({len(star_words)} ta)", callback_data="game_mode_star")])
    if unknown_words:
        keyboard.append([InlineKeyboardButton(text=f"❌ Bilmaydigan so'zlar ({len(unknown_words)} ta)", callback_data="game_mode_unknown")])

    await state.set_state(GameModeState.selecting_mode)
    await callback.message.edit_text(get_text(lang, "game_select_mode"), reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()


# ---------- BELGILANGAN REJIM: TOPIK -> BO'LIM -> YO'NALISH ----------

@router.callback_query(F.data == "game_mode_custom")
async def game_custom_mode(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    topics = dict_handler.get_all_topics(user_id)
    if not topics:
        await callback.answer(get_text(lang, "no_topics"), show_alert=True)
        return
    keyboard = [[InlineKeyboardButton(text=f"📚 {topic}", callback_data=f"game_topic_{topic}")] for topic in topics]
    keyboard.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="game_back_to_mode")])
    await state.set_state(GameModeState.selecting_topic)
    await callback.message.edit_text(get_text(lang, "game_select_topic"), reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("game_topic_"))
async def game_select_topic(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    topic = callback.data.replace("game_topic_", "")

    sections = dict_handler.get_topic_sections(user_id, topic)
    if not sections:
        await callback.answer(get_text(lang, "no_sections"), show_alert=True)
        return

    keyboard = [[InlineKeyboardButton(text=f"📖 {s.title()}", callback_data=f"game_section_{topic}_{s}")] for s in sections]
    keyboard.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="game_mode_custom")])

    await state.set_state(GameModeState.selecting_section)
    await state.update_data(selected_topic=topic)
    await callback.message.edit_text(
        get_text(lang, "game_select_section", topic=topic),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("game_section_"))
async def game_select_section(callback: CallbackQuery, state: FSMContext):
    """Bo'lim tanlandi - endi to'g'ridan-to'g'ri yo'nalish so'raymiz (oraliq talab qilinmaydi)"""
    parts = callback.data.replace("game_section_", "").split("_", 1)
    topic = parts[0]
    section = parts[1]

    await state.update_data(selected_topic=topic, selected_section=section)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 Uz → 🇰🇷 Ko", callback_data="game_dir_custom_uz_ko")],
        [InlineKeyboardButton(text="🇰🇷 Ko → 🇺🇿 Uz", callback_data="game_dir_custom_ko_uz")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"game_topic_{topic}")]
    ])
    await callback.message.edit_text(
        f"📚 <b>{topic} › {section.title()}</b>\n\n🎮 Tarjima yo'nalishini tanlang:",
        reply_markup=keyboard, parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("game_dir_custom_"))
async def game_custom_direction_selected(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    direction = callback.data.replace("game_dir_custom_", "")

    data = await state.get_data()
    topic = data.get('selected_topic')
    section = data.get('selected_section')

    word = dict_handler.get_random_word(user_id, topic=topic, section=section)
    if not word:
        await callback.answer(get_text(lang, "no_words"), show_alert=True)
        return

    await state.set_state(GameModeState.playing)
    await state.update_data(
        current_word=word, direction=direction, mode='custom',
        topic=topic, section=section,
        start_time=datetime.now().timestamp(), question_count=1
    )

    text = (
        f"🎮 <b>O'yin boshlandi!</b>\n📂 {topic} › {section}\n\n"
        f"━━━━━━━━━━━━━━\n\n"
        + _build_question_text(word, direction, 1, 'custom')
    )
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_question_message(callback.message, state, user_id, text, setup_reply_kb=True)
    await callback.answer()


# ---------- TUGMALAR: BILAMAN / BILMAYMAN / TO'XTATISH ----------

@router.message(GameModeState.playing, F.text == "🛑 To'xtatish")
async def game_stop_reply(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    stats = await user_db.get_statistics(user_id)
    await state.clear()
    await message.answer(
        get_text(lang, "game_stopped", correct=stats['correct'], wrong=stats['wrong']),
        reply_markup=get_main_keyboard(lang),
        parse_mode="HTML"
    )


@router.message(GameModeState.playing, F.text == "✅ Bilaman")
async def game_know_word(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    word = data.get('current_word')
    if not word:
        return
    start_time = data.get('start_time', datetime.now().timestamp())
    time_spent = int(datetime.now().timestamp() - start_time)
    await user_db.update_statistics(user_id, is_correct=True, time_spent=time_spent)
    await _send_next_game_word(message, state, user_id, data, knew=True)


@router.message(GameModeState.playing, F.text == "❌ Bilmayman")
async def game_dont_know_word(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    word = data.get('current_word')
    if not word:
        return

    # So'zni "bilmaydiganlar" ro'yxatiga belgilash (** prefiks bilan)
    dict_handler.mark_as_unknown(
        user_id,
        word.get('korean', ''),
        word.get('uzbek', ''),
        word.get('topic', ''),
        word.get('section', ''),
        word.get('chapter', '')
    )

    start_time = data.get('start_time', datetime.now().timestamp())
    time_spent = int(datetime.now().timestamp() - start_time)
    await user_db.update_statistics(user_id, is_correct=False, time_spent=time_spent)
    await _send_next_game_word(message, state, user_id, data, knew=False)


async def _send_next_game_word(message: Message, state: FSMContext, user_id: int, data: dict, knew: bool):
    """/game uchun keyingi so'zni yuborish - barcha rejimlar uchun umumiy"""
    lang = await user_db.get_language(user_id) or "uz"
    mode = data.get('mode', 'general')
    direction = data.get('direction', 'uz_ko')
    q_count = data.get('question_count', 1) + 1
    status = "✅ Bildingiz!" if knew else "❌ Bilmaydiganlar ro'yxatiga qo'shildi!"
    extra_info = ""
    next_word = None

    if mode == 'unknown':
        unknown_queue = data.get('unknown_queue', [])
        idx = data.get('unknown_index', 0)

        # ✅ YANGI: Bilaman bosilsa, shu so'zni ** ro'yxatidan o'chiramiz
        if knew:
            current_word = data.get('current_word', {})
            dict_handler.mark_as_known(
                user_id,
                current_word.get('original_korean', current_word.get('korean', '')),
                current_word.get('original_uzbek', current_word.get('uzbek', '')),
                current_word.get('topic', ''),
                current_word.get('section', ''),
                current_word.get('chapter', '')
            )
            # Queue'dan ham o'chiramiz
            unknown_queue = [w for i, w in enumerate(unknown_queue) if i != idx]
            status = "✅ Bildingiz! Bilmaydiganlar ro'yxatidan o'chirildi 🗑"

        # Keyingi so'zni aniqlash
        # knew bo'lsa idx o'zida qoladi (chunk siljidi), bilmasa idx+1
        next_idx = idx if knew else idx + 1

        if unknown_queue and next_idx < len(unknown_queue):
            next_word = unknown_queue[next_idx]
            await state.update_data(unknown_queue=unknown_queue, unknown_index=next_idx)
            extra_info = f"/{len(unknown_queue)}"
        else:
            # Navbat tugadi - bazadan yangilab qayta boshlaymiz
            fresh = dict_handler.get_unknown_words(user_id)
            if fresh:
                next_word = fresh[0]
                await state.update_data(unknown_queue=fresh, unknown_index=0)
                extra_info = f"/{len(fresh)}"
            else:
                await message.answer(
                    f"{status}\n\n🎉 <b>Barcha bilmaydigan so'zlarni o'zdingiz!</b>",
                    reply_markup=get_main_keyboard(lang), parse_mode="HTML"
                )
                await state.clear()
                return

    elif mode == 'star':
        next_word = dict_handler.get_random_star_word(user_id)
    elif mode == 'custom':
        next_word = dict_handler.get_random_word(user_id, topic=data.get('topic'), section=data.get('section'))
    else:
        next_word = dict_handler.get_random_word(user_id)

    if not next_word:
        await message.answer(
            f"{status}\n\n🏁 <b>So'zlar tugadi!</b>",
            reply_markup=get_main_keyboard(lang), parse_mode="HTML"
        )
        await state.clear()
        return

    await state.update_data(current_word=next_word, start_time=datetime.now().timestamp(), question_count=q_count)

    text = f"{status}\n\n━━━━━━━━━━━━━━\n\n" + _build_question_text(next_word, direction, q_count, mode, extra_info)
    await send_question_message(message, state, user_id, text)


# ============================================
# /AVTOGAME — YANGI TIZIM (TUGMA ASOSIDA)
# ============================================
#
# /game bilan bir xil tugma mantig'i (Bilaman/Bilmayman/To'xtatish),
# farqi shundaki - so'zlar avtomatik, belgilangan vaqt oralig'ida keladi.
# 10 ta so'z tugagandan keyin foydalanuvchi javob bermasa ham,
# keyingi vaqt kelganda yana 10 ta so'z avtomatik yuboriladi.
#

@router.message(Command("avtogame"))
async def cmd_auto_game(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, "btn_5min"), callback_data="auto_time_5")],
        [InlineKeyboardButton(text=get_text(lang, "btn_10min"), callback_data="auto_time_10")],
        [InlineKeyboardButton(text=get_text(lang, "btn_15min"), callback_data="auto_time_15")],
        [InlineKeyboardButton(text=get_text(lang, "btn_30min"), callback_data="auto_time_30")],
        [InlineKeyboardButton(text=get_text(lang, "btn_60min"), callback_data="auto_time_60")]
    ])
    await state.set_state(AutoPlayState.selecting_time)
    await message.answer(get_text(lang, "auto_select_time"), reply_markup=markup, parse_mode="HTML")


@router.callback_query(F.data.startswith("auto_time_"))
async def auto_select_time(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    time_minutes = int(callback.data.split("_")[2])
    await state.update_data(auto_interval=time_minutes)

    star_words = dict_handler.get_star_words(user_id)
    markup_buttons = [
        [InlineKeyboardButton(text=get_text(lang, "btn_general_mode"), callback_data="auto_mode_general")],
        [InlineKeyboardButton(text=get_text(lang, "btn_custom_mode"), callback_data="auto_mode_custom")],
    ]
    if star_words:
        markup_buttons.append([InlineKeyboardButton(text="⭐ Yulduzli so'zlar", callback_data="auto_mode_star")])

    await state.set_state(AutoPlayState.selecting_mode)
    await callback.message.edit_text(
        get_text(lang, "auto_time_set", time=time_minutes) + "\n\n" + get_text(lang, "game_select_mode"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=markup_buttons),
        parse_mode="HTML"
    )
    await callback.answer()


# ---------- AVTO: UMUMIY REJIM ----------

@router.callback_query(F.data == "auto_mode_general")
async def auto_general_mode(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 Uz → 🇰🇷 Ko", callback_data="auto_dir_general_uz_ko")],
        [InlineKeyboardButton(text="🇰🇷 Ko → 🇺🇿 Uz", callback_data="auto_dir_general_ko_uz")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="auto_back_to_mode")]
    ])
    await callback.message.edit_text("🤖 <b>Avtomatik rejim uchun yo'nalishni tanlang:</b>", reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("auto_dir_general_"))
async def auto_general_direction_selected(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    direction = callback.data.replace("auto_dir_general_", "")
    data = await state.get_data()
    interval = data.get('auto_interval', 15)

    word = dict_handler.get_random_word(user_id)
    if not word:
        await callback.answer(get_text(lang, "no_words"), show_alert=True)
        return

    await state.update_data(
        mode='general', topic=None, section=None, direction=direction,
        current_word=word, auto_current_step=1,
        last_auto_sent=time_module.time()
    )
    await state.set_state(AutoPlayState.playing)

    text = (
        f"🤖 <b>Avtomatik rejim boshlandi!</b>\n⏰ Har {interval} daqiqada yangi so'zlar (10 tadan)\n\n"
        f"━━━━━━━━━━━━━━\n\n"
        + _build_question_text(word, direction, 1, 'general', extra_info="/10")
    )
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_question_message(callback.message, state, user_id, text, setup_reply_kb=True)
    await callback.answer()


# ---------- AVTO: YULDUZLI SO'ZLAR REJIMI ----------

@router.callback_query(F.data == "auto_mode_star")
async def auto_star_mode(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    star_words = dict_handler.get_star_words(user_id)
    if not star_words:
        await callback.answer(get_text(lang, "no_star_words"), show_alert=True)
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 Uz → 🇰🇷 Ko", callback_data="auto_dir_star_uz_ko")],
        [InlineKeyboardButton(text="🇰🇷 Ko → 🇺🇿 Uz", callback_data="auto_dir_star_ko_uz")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="auto_back_to_mode")]
    ])
    await callback.message.edit_text(
        f"⭐ <b>Yulduzli so'zlar: {len(star_words)} ta</b>\n\n🎮 Tarjima yo'nalishini tanlang:",
        reply_markup=keyboard, parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("auto_dir_star_"))
async def auto_star_direction_selected(callback: CallbackQuery, state: FSMContext):
    direction = callback.data.replace("auto_dir_star_", "")
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"

    word = dict_handler.get_random_star_word(user_id)
    if not word:
        await callback.answer(get_text(lang, "no_star_words"), show_alert=True)
        return

    data = await state.get_data()
    interval = data.get('auto_interval', 15)

    await state.update_data(
        mode='auto_star', direction=direction, current_word=word,
        auto_current_step=1, last_auto_sent=time_module.time()
    )
    await state.set_state(AutoPlayState.playing)

    text = (
        f"⭐ <b>Yulduzli avtomatik rejim boshlandi!</b>\n⏰ Har {interval} daqiqada yangi so'zlar (10 tadan)\n\n"
        f"━━━━━━━━━━━━━━\n\n"
        + _build_question_text(word, direction, 1, 'star', extra_info="/10")
    )
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_question_message(callback.message, state, user_id, text, setup_reply_kb=True)
    await callback.answer()


# ---------- AVTO: BELGILANGAN REJIM (TOPIK + BO'LIM) ----------

@router.callback_query(F.data == "auto_mode_custom")
async def auto_custom_mode(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    topics = dict_handler.get_all_topics(user_id)
    if not topics:
        await callback.answer(get_text(lang, "no_topics"), show_alert=True)
        return
    keyboard = [[InlineKeyboardButton(text=f"📚 {t}", callback_data=f"auto_topic_{t}")] for t in topics]
    keyboard.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="auto_back_to_mode")])
    await state.set_state(AutoPlayState.selecting_topic)
    await callback.message.edit_text(
        get_text(lang, "game_select_topic"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("auto_topic_"))
async def auto_select_topic(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    topic = callback.data.replace("auto_topic_", "")
    sections = dict_handler.get_topic_sections(user_id, topic)
    if not sections:
        await callback.answer(get_text(lang, "no_sections"), show_alert=True)
        return
    await state.update_data(topic=topic)
    keyboard = [[InlineKeyboardButton(text=f"📖 {s.title()}", callback_data=f"auto_section_{s}")] for s in sections]
    keyboard.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="auto_mode_custom")])
    await state.set_state(AutoPlayState.selecting_section)
    await callback.message.edit_text(
        get_text(lang, "game_select_section_only", topic=topic),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("auto_section_"))
async def auto_select_section(callback: CallbackQuery, state: FSMContext):
    section = callback.data.replace("auto_section_", "")
    data = await state.get_data()
    await state.update_data(section=section)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 Uz → 🇰🇷 Ko", callback_data="auto_dir_custom_uz_ko")],
        [InlineKeyboardButton(text="🇰🇷 Ko → 🇺🇿 Uz", callback_data="auto_dir_custom_ko_uz")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"auto_topic_{data.get('topic')}")]
    ])
    await callback.message.edit_text("🤖 <b>Avtomatik rejim uchun yo'nalishni tanlang:</b>", reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("auto_dir_custom_"))
async def auto_custom_direction_selected(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    direction = callback.data.replace("auto_dir_custom_", "")
    data = await state.get_data()
    interval = data.get('auto_interval', 15)
    topic = data.get('topic')
    section = data.get('section')

    word = dict_handler.get_random_word(user_id, topic=topic, section=section)
    if not word:
        await callback.answer(get_text(lang, "no_words"), show_alert=True)
        return

    await state.update_data(
        mode='custom', direction=direction, current_word=word,
        auto_current_step=1, last_auto_sent=time_module.time()
    )
    await state.set_state(AutoPlayState.playing)

    text = (
        f"🤖 <b>Avtomatik rejim boshlandi!</b>\n📂 {topic} › {section}\n"
        f"⏰ Har {interval} daqiqada yangi so'zlar (10 tadan)\n\n"
        f"━━━━━━━━━━━━━━\n\n"
        + _build_question_text(word, direction, 1, 'custom', extra_info="/10")
    )
    try:
        await callback.message.delete()
    except Exception:
        pass
    await send_question_message(callback.message, state, user_id, text, setup_reply_kb=True)
    await callback.answer()


@router.callback_query(F.data == "auto_back_to_mode")
async def auto_back_to_mode(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    star_words = dict_handler.get_star_words(user_id)
    markup_buttons = [
        [InlineKeyboardButton(text=get_text(lang, "btn_general_mode"), callback_data="auto_mode_general")],
        [InlineKeyboardButton(text=get_text(lang, "btn_custom_mode"), callback_data="auto_mode_custom")],
    ]
    if star_words:
        markup_buttons.append([InlineKeyboardButton(text="⭐ Yulduzli so'zlar", callback_data="auto_mode_star")])
    await state.set_state(AutoPlayState.selecting_mode)
    await callback.message.edit_text(
        get_text(lang, "game_select_mode"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=markup_buttons),
        parse_mode="HTML"
    )
    await callback.answer()


# ---------- AVTOGAME TUGMALARI: BILAMAN / BILMAYMAN / TO'XTATISH ----------

@router.message(AutoPlayState.playing, F.text == "🛑 To'xtatish")
async def auto_stop_reply(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    stats = await user_db.get_statistics(user_id)
    await state.clear()
    await message.answer(
        get_text(lang, "game_stopped", correct=stats['correct'], wrong=stats['wrong']),
        reply_markup=get_main_keyboard(lang),
        parse_mode="HTML"
    )


@router.message(AutoPlayState.playing, F.text == "✅ Bilaman")
async def auto_know_word(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    word = data.get('current_word')
    if not word:
        return
    await user_db.update_statistics(user_id, is_correct=True, time_spent=0)
    await _send_next_auto_word(message, state, user_id, data, knew=True)


@router.message(AutoPlayState.playing, F.text == "❌ Bilmayman")
async def auto_dont_know_word(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    word = data.get('current_word')
    if not word:
        return
    dict_handler.mark_as_unknown(
        user_id,
        word.get('korean', ''), word.get('uzbek', ''),
        word.get('topic', ''), word.get('section', ''), word.get('chapter', '')
    )
    await user_db.update_statistics(user_id, is_correct=False, time_spent=0)
    await _send_next_auto_word(message, state, user_id, data, knew=False)


async def _send_next_auto_word(message: Message, state: FSMContext, user_id: int, data: dict, knew: bool):
    """Avtogame: keyingi so'zni yuborish (10 tagacha hisoblanadi)"""
    lang = await user_db.get_language(user_id) or "uz"
    mode = data.get('mode', 'general')
    direction = data.get('direction', 'uz_ko')
    step = data.get('auto_current_step', 1)
    status = "✅ Bildingiz!" if knew else "❌ Bilmaydiganlar ro'yxatiga qo'shildi!"

    if step >= 10:
        stats = await user_db.get_statistics(user_id)
        await message.answer(
            f"{status}\n\n🎉 <b>10 ta so'z tugadi!</b>\n\n"
            f"✅ To'g'ri: {stats.get('correct', 0)}\n❌ Xato: {stats.get('wrong', 0)}\n\n"
            f"⏰ Keyingi 10 ta so'z belgilangan vaqt kelganda avtomatik yuboriladi.\n"
            f"To'xtatish uchun 🛑 tugmasini bosing.",
            reply_markup=get_game_reply_keyboard(), parse_mode="HTML"
        )
        # Stateni saqlab qolamiz (playing holatida), faqat qadamni nollaymiz.
        # send_auto_words fon vazifasi navbatdagi vaqt kelganda davom ettiradi.
        await state.update_data(auto_current_step=0)
        return

    if mode == 'auto_star':
        next_word = dict_handler.get_random_star_word(user_id)
    else:
        next_word = dict_handler.get_random_word(user_id, topic=data.get('topic'), section=data.get('section'))

    if not next_word:
        await message.answer(f"{status}\n\n🏁 So'zlar tugadi!", reply_markup=get_main_keyboard(lang), parse_mode="HTML")
        return

    new_step = step + 1
    await state.update_data(current_word=next_word, auto_current_step=new_step)

    text = f"{status}\n\n━━━━━━━━━━━━━━\n\n" + _build_question_text(next_word, direction, new_step, mode if mode != 'auto_star' else 'star', extra_info="/10")
    await send_question_message(message, state, user_id, text)


# ============================================
# AVTOMATIK YUBORISH TIZIMI (Fon vazifasi)
# ============================================

async def send_auto_words():
    """Belgilangan vaqt oralig'ida har bir foydalanuvchiga yangi 10 ta so'z yuborish"""
    while True:
        try:
            users = await user_db.get_all_users()
            for user in users:
                user_id = user['user_id']
                state_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
                fsm = FSMContext(storage=storage, key=state_key)
                current_state = await fsm.get_state()

                if current_state == AutoPlayState.playing:
                    data = await fsm.get_data()
                    interval_min = data.get('auto_interval', 15)
                    interval_sec = interval_min * 60
                    last_sent = data.get('last_auto_sent', 0)
                    now = time_module.time()

                    # Faqat 10 talik bosqich tugagandan keyin (auto_current_step == 0) yangi to'plam yuboriladi
                    step = data.get('auto_current_step', 1)
                    if step == 0 and (now - last_sent >= interval_sec):
                        direction = data.get('direction', 'uz_ko')
                        mode = data.get('mode', 'general')

                        if mode == 'auto_star':
                            word = dict_handler.get_random_star_word(user_id)
                        else:
                            word = dict_handler.get_random_word(user_id, topic=data.get('topic'), section=data.get('section'))

                        if word:
                            await fsm.update_data(current_word=word, last_auto_sent=now, auto_current_step=1)
                            text = (
                                "⏰ <b>Vaqt keldi! Yangi 10 ta so'z:</b>\n\n"
                                + _build_question_text(word, direction, 1, mode if mode != 'auto_star' else 'star', extra_info="/10")
                            )
                            try:
                                sent = await bot.send_message(
                                    user_id, text, parse_mode="HTML",
                                    reply_markup=get_reveal_keyboard()
                                )
                                await _track_and_trim(fsm, user_id, sent.message_id, keep=1)
                            except Exception as send_err:
                                print(f"⚠️ send_auto_words: foydalanuvchiga yuborib bo'lmadi {user_id}: {send_err}")
        except Exception as e:
            print(f"❌ send_auto_words xatosi: {e}")

        await asyncio.sleep(20)


# ==================== BO'LIMLAR ====================

@router.callback_query(F.data == "chapters_main")
async def chapters_main_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    await callback.message.edit_text(
        get_text(lang, "chapters_select_topic"),
        reply_markup=get_chapters_topics_keyboard(user_id, lang),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("topic_"))
async def chapters_topic_selected(callback: CallbackQuery):
    topic = callback.data.replace("topic_", "")
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    await callback.message.edit_text(
        get_text(lang, "chapters_select_section", topic=topic),
        reply_markup=get_chapters_sections_keyboard(user_id, topic, lang),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("section_"))
async def chapters_section_selected(callback: CallbackQuery):
    parts = callback.data.replace("section_", "").split("_", 1)
    topic = parts[0]
    section = parts[1]

    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"

    data = dict_handler.load_user_data(user_id)
    topic_key = f"Topik-{topic.replace('-topik', '')}"

    section_data = {}
    if topic_key in data and section in data[topic_key]:
        section_data = data[topic_key][section]

    builder = InlineKeyboardBuilder()

    for i in range(1, 50):
        chapter_key = f"{i}-savol so'zlari"
        word_count = len(section_data.get(chapter_key, {}))
        btn_text = f"{i}-{word_count}"
        builder.button(text=btn_text, callback_data=f"chapter_{topic}_{section}_{i}-savol")

    builder.adjust(7)

    ch50_key = "50-savol so'zlari"
    count50 = len(section_data.get(ch50_key, {}))
    builder.row(InlineKeyboardButton(text=f"50-{count50}", callback_data=f"chapter_{topic}_{section}_50-savol"))

    builder.row(InlineKeyboardButton(text=get_text(lang, "back"), callback_data=f"topic_{topic}"))

    await callback.message.edit_text(
        text=f"📚 <b>{topic.upper()} | {section.upper()}</b>\n\nFormat: [Savol]-[So'zlar soni]",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("chapter_"))
async def chapters_chapter_selected(callback: CallbackQuery):
    parts = callback.data.replace("chapter_", "").split("_", 2)
    topic = parts[0]
    section = parts[1]
    chapter = parts[2]

    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"

    words = dict_handler.get_chapter_words(user_id, topic, section, chapter)

    if not words:
        ch_num = chapter.split("-")[0]
        await callback.answer(f"⚠️ {ch_num}-savolda so'zlar yo'q", show_alert=True)
        return

    text = f"📚 <b>{chapter.replace('-', ' ').title()}</b>\n\n"
    for korean, uzbek in words.items():
        korean_display = korean.lstrip('*')
        uzbek_display = uzbek.lstrip('*')
        text += f"🇰🇷 {korean_display} – 🇺🇿 {uzbek_display}\n"
    text += f"\n📊 {get_text(lang, 'statistics')}: {len(words)}"

    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, "back"), callback_data=f"section_{topic}_{section}")]
        ])
    )
    await callback.answer()


# ==================== ADMIN PANEL ====================

@router.callback_query(F.data == "admin_panel")
async def admin_panel_entry(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    is_admin = await user_db.is_admin(user_id)
    if is_admin:
        await callback.message.edit_text(get_text(lang, "admin_welcome"), reply_markup=get_admin_keyboard(lang))
        await callback.answer()
        return
    await callback.message.edit_text(get_text(lang, "admin_enter_password"))
    await state.set_state(AdminState.waiting_password)
    await callback.answer()


@router.message(AdminState.waiting_password)
async def check_admin_password(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    if message.text == ADMIN_PASSWORD:
        await user_db.add_admin(user_id)
        await message.answer(get_text(lang, "admin_welcome"), reply_markup=get_admin_keyboard(lang))
        await state.clear()
    else:
        await message.answer(get_text(lang, "admin_wrong_password"))
        await state.clear()


@router.callback_query(F.data == "admin_users")
async def admin_show_users(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    users = await user_db.get_all_users()
    text = get_text(lang, "admin_user_list") + "\n\n"
    keyboard = []
    for idx, user in enumerate(users[:15], 1):
        status = "🚫" if user['is_blocked'] else "✅"
        rank, total = await user_db.get_ranking(user['user_id'])
        text += (
            f"{idx}. {status} <b>{user['first_name']}</b> (@{user['username']})\n"
            f"   📊 ✅ {user['correct']} | ❌ {user['wrong']} | 🏆 {rank}/{total}\n\n"
        )
        keyboard.append([InlineKeyboardButton(text=f"{user['first_name'][:20]}", callback_data=f"user_detail_{user['user_id']}")])
    keyboard.append([InlineKeyboardButton(text=get_text(lang, "back"), callback_data="admin_panel")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()


@router.callback_query(F.data.startswith("user_detail_"))
async def admin_user_detail(callback: CallbackQuery):
    target_user_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    users = await user_db.get_all_users()
    user = next((u for u in users if u['user_id'] == target_user_id), None)
    if not user:
        await callback.answer("❌ User topilmadi!", show_alert=True)
        return
    is_blocked, reason = await user_db.is_blocked(target_user_id)
    rank, total = await user_db.get_ranking(target_user_id)
    status = "🚫 Bloklangan" if is_blocked else "✅ Faol"
    block_reason = f"\n📝 Sabab: {reason}" if is_blocked and reason else ""
    text = (
        f"👤 <b>Foydalanuvchi ma'lumotlari:</b>\n\n"
        f"📛 Ism: {user['first_name']}\n"
        f"🆔 Username: @{user['username']}\n"
        f"🔢 ID: <code>{user['user_id']}</code>\n"
        f"🎯 Status: {status}{block_reason}\n\n"
        f"📊 <b>Statistika:</b>\n"
        f"✅ To'g'ri: {user['correct']}\n"
        f"❌ Noto'g'ri: {user['wrong']}\n"
        f"⏱ Faol vaqt: {user['active_time'] // 60} daqiqa\n"
        f"🏆 Reyting: {rank}/{total}\n"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_user_action_keyboard(target_user_id, is_blocked, lang))
    await callback.answer()


@router.callback_query(F.data.startswith("block_"))
async def admin_block_user(callback: CallbackQuery, state: FSMContext):
    target_user_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    await state.update_data(target_user_id=target_user_id)
    await callback.message.edit_text(get_text(lang, "admin_enter_block_reason"))
    await state.set_state(AdminState.waiting_block_reason)
    await callback.answer()


@router.callback_query(F.data.startswith("unblock_"))
async def admin_unblock_user(callback: CallbackQuery):
    target_user_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    await user_db.unblock_user(target_user_id)
    await callback.answer(get_text(lang, "admin_user_unblocked"), show_alert=True)
    await admin_user_detail(callback)


@router.message(AdminState.waiting_block_reason)
async def admin_block_with_reason(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    if message.text == "/cancel":
        await message.answer(get_text(lang, "main_menu"), reply_markup=get_main_keyboard(lang))
        await state.clear()
        return
    data = await state.get_data()
    target_user_id = data['target_user_id']
    reason = None if message.text == "/skip" else message.text
    await user_db.block_user(target_user_id, reason)
    await message.answer(get_text(lang, "admin_user_blocked"))
    await message.answer(get_text(lang, "admin_welcome"), reply_markup=get_admin_keyboard(lang))
    await state.clear()


@router.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    total_users = await user_db.get_total_users()
    all_users = await user_db.get_all_users()
    total_words = sum(dict_handler.get_total_words(u['user_id']) for u in all_users)
    await callback.message.edit_text(
        get_text(lang, "bot_statistics", users=total_users, words=total_words),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, "back"), callback_data="admin_panel")]
        ])
    )
    await callback.answer()


# ==================== EXAM TIZIMI ====================

@router.message(F.text == "/exam_doc")
async def cmd_exam_list(message: Message, state: FSMContext):
    """Bo'limlarni ko'rsatish (exam uchun asosiy kirish nuqtasi)"""
    user_id = message.from_user.id
    await state.clear()

    topics = dict_handler.get_all_topics(user_id)
    if not topics:
        await message.answer("❌ Lug'atingizda ma'lumot topilmadi!")
        return

    keyboard = []
    for topic in topics:
        sections = dict_handler.get_topic_sections(user_id, topic)
        for section in sections:
            section_map = {'reading': '읽기', 'writing': '쓰기', 'listening': '듣기'}
            section_korean = section_map.get(section, section)
            keyboard.append([InlineKeyboardButton(
                text=f"📚 {topic} › {section_korean}",
                callback_data=f"exam_section:{topic}:{section}"
            )])

    if not keyboard:
        await message.answer("❌ Bo'limlar topilmadi!")
        return

    star_words = dict_handler.get_star_words(user_id)
    if star_words:
        keyboard.append([InlineKeyboardButton(
            text=f"⭐ Yulduzli so'zlar ({len(star_words)} ta)",
            callback_data="exam_star"
        )])

    await message.answer(
        "📚 시험 섹션을 선택하세요:\n(Imtihon bo'limini tanlang:)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data.startswith("exam_section:"))
async def exam_section_selected(callback: CallbackQuery, state: FSMContext):
    """Bo'lim tanlandi - endi yo'nalish (mode) so'raymiz"""
    parts = callback.data.split(":")
    topic = parts[1]
    section = parts[2]

    await state.update_data(exam_topic=topic, exam_section=section)

    section_map = {'reading': '읽기', 'writing': '쓰기', 'listening': '듣기'}
    section_korean = section_map.get(section, section)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇰🇷 한국어 ➔ 🇺🇿 우즈베크어", callback_data="exam_mode:kr_to_uz")],
        [InlineKeyboardButton(text="🇺🇿 우즈베크어 ➔ 🇰🇷 한국어", callback_data="exam_mode:uz_to_kr")],
        [InlineKeyboardButton(text="🇰🇷 + 🇺🇿 Tarjima bilan (ikki tilda)", callback_data="exam_mode:both")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="exam_back_to_sections")]
    ])

    await callback.message.edit_text(
        f"📚 {topic} › {section_korean}\n\n🔄 시험 형식을 선택하세요:\n(Imtihon formatini tanlang:)",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("exam_mode:"))
async def exam_mode_selected(callback: CallbackQuery, state: FSMContext):
    """Yo'nalish tanlandi - fayl yaratamiz va yuboramiz"""
    mode = callback.data.split(":")[1]
    data = await state.get_data()
    topic = data.get('exam_topic')
    section = data.get('exam_section')
    user_id = callback.from_user.id

    if not topic or not section:
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)
        await state.clear()
        return

    await callback.message.edit_text("⏳ 파일을 준비 중입니다...\n(Fayl tayyorlanmoqda...)")

    try:
        topic_key = f"Topik-{topic.replace('-topik', '')}"
        all_words_data = dict_handler.get_all_words(user_id)

        words = []
        for w in all_words_data:
            if w.get('topic', '') == topic_key and w.get('section', '') == section:
                korean_clean = w['korean'].lstrip('*') if isinstance(w['korean'], str) else w['korean']
                uzbek_clean = w['uzbek'].lstrip('*') if isinstance(w['uzbek'], str) else w['uzbek']
                words.append((korean_clean, uzbek_clean))

        if not words:
            await callback.message.edit_text(
                f"❌ Bu bo'limda so'zlar topilmadi!\n(topic={topic_key}, section={section})"
            )
            await state.clear()
            return

        section_map = {'reading': '읽기', 'writing': '쓰기', 'listening': '듣기', 'general': '일반'}
        section_korean = section_map.get(section, section)
        location = f"{topic} › {section_korean}"

        topic_num = topic.replace('-topik', '')
        address_part = f"{topic_num}{section_korean}"

        if mode == "both":
            filename_prefix = f"{address_part}_ikki-tilda"
            filepath = create_exam_word_bilingual(words, location=location, filename_prefix=filename_prefix)
            mode_text = "🇰🇷 한국어 + 🇺🇿 O'zbekcha"
        else:
            filename_prefix = f"{address_part}_{'ko-uz' if mode == 'kr_to_uz' else 'uz-ko'}"
            filepath = create_exam_word(words, location=location, mode=mode, filename_prefix=filename_prefix)
            mode_text = "🇰🇷 ➔ 🇺🇿" if mode == "kr_to_uz" else "🇺🇿 ➔ 🇰🇷"

        file = FSInputFile(filepath)
        await callback.message.answer_document(
            document=file,
            caption=f"✅ 시험지가 준비되었습니다!\n\n📂 {location}\n🔄 {mode_text}\n📊 {len(words)}개 단어"
        )
        await callback.message.delete()
        if os.path.exists(filepath):
            os.remove(filepath)
        await state.clear()

    except Exception as e:
        print(f"Exam error: {e}")
        import traceback
        traceback.print_exc()
        await callback.message.edit_text(f"❌ Xatolik yuz berdi!\n\nError: {str(e)}")
        await state.clear()


@router.callback_query(F.data == "exam_back_to_sections")
async def exam_back_to_sections(callback: CallbackQuery, state: FSMContext):
    """Bo'limlar ro'yxatiga qaytish"""
    user_id = callback.from_user.id
    await state.clear()

    topics = dict_handler.get_all_topics(user_id)
    keyboard = []
    for topic in topics:
        sections = dict_handler.get_topic_sections(user_id, topic)
        for section in sections:
            section_map = {'reading': '읽기', 'writing': '쓰기', 'listening': '듣기'}
            section_korean = section_map.get(section, section)
            keyboard.append([InlineKeyboardButton(
                text=f"📚 {topic} › {section_korean}",
                callback_data=f"exam_section:{topic}:{section}"
            )])

    keyboard.append([InlineKeyboardButton(text="◀️ Orqaga (Asosiy menyuga)", callback_data="exam_back_main")])

    await callback.message.edit_text(
        "📚 시험 섹션을 선택하세요:\n(Imtihon bo'limini tanlang:)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


@router.callback_query(F.data == "exam_back_main")
async def exam_back_main_handler(callback: CallbackQuery):
    """Exam asosiy menyuga qaytish"""
    await callback.message.edit_text(
        "📚 <b>Exam menyusi</b>\n\nTanlang:",
        reply_markup=get_exam_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "exam_star")
async def exam_star_handler(callback: CallbackQuery):
    """Yulduzli so'zlar yo'nalishi tanlash"""
    user_id = callback.from_user.id
    star_words = dict_handler.get_star_words(user_id)
    if not star_words:
        await callback.answer(get_text("uz", "no_star_words"), show_alert=True)
        return
    await callback.message.edit_text(
        f"⭐ <b>Yulduzli so'zlar: {len(star_words)} ta</b>\n\nYo'nalishni tanlang:",
        reply_markup=get_exam_star_direction_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("exam_star_"))
async def exam_star_direction_handler(callback: CallbackQuery):
    """Yulduzli so'zlar .docx yaratish - uchta variant: uz_ko, ko_uz, both"""
    user_id = callback.from_user.id
    direction = callback.data.replace("exam_star_", "")

    if direction == "back_main":
        return

    await callback.message.edit_text("⏳ Fayl yaratilmoqda...")

    star_words = dict_handler.get_star_words(user_id)
    if not star_words:
        await callback.message.edit_text("❌ Yulduzli so'zlar topilmadi!")
        return

    words_list = [(w['korean'], w['uzbek']) for w in star_words]
    location = f"⭐ Yulduzli so'zlar ({len(words_list)} ta)"

    try:
        if direction == "both":
            filename_prefix = "yulduzli-sozlar_ikki-tilda"
            filepath = create_exam_word_bilingual(words_list, location=location, filename_prefix=filename_prefix)
            mode_text = "🇰🇷 + 🇺🇿 (Ikki tilda)"
        else:
            mode = "kr_to_uz" if direction == "ko_uz" else "uz_to_kr"
            filename_prefix = f"yulduzli-sozlar_{'ko-uz' if mode == 'kr_to_uz' else 'uz-ko'}"
            filepath = create_exam_word(words_list, location=location, mode=mode, filename_prefix=filename_prefix)
            mode_text = "🇰🇷 Ko → 🇺🇿 Uz" if mode == "kr_to_uz" else "🇺🇿 Uz → 🇰🇷 Ko"

        doc_file = FSInputFile(filepath)
        await callback.message.answer_document(
            document=doc_file,
            caption=f"⭐ <b>Yulduzli so'zlar</b>\n\n📊 Jami: {len(words_list)} ta so'z\n🎯 Format: {mode_text}",
            parse_mode="HTML"
        )

        if os.path.exists(filepath):
            os.remove(filepath)
        await callback.message.delete()
        await callback.answer("✅ Fayl yuborildi!")

    except Exception as e:
        import traceback
        traceback.print_exc()
        await callback.message.edit_text(f"❌ Xatolik: {str(e)}")
        await callback.answer()


@router.message(F.text == "*")
async def star_list_handler(message: Message):
    """* yuborilganda yulduzli so'zlar ro'yxatini ko'rsatish"""
    user_id = message.from_user.id
    star_words = dict_handler.get_star_words(user_id)
    if not star_words:
        await message.answer(
            "❌ <b>Yulduzli so'zlar yo'q!</b>\n\n"
            "💡 So'z qo'shishda <code>*</code> bilan boshlang:\n<code>*안녕 salom</code>",
            parse_mode="HTML"
        )
        return

    text = f"⭐ <b>YULDUZLI SO'ZLAR ({len(star_words)} ta):</b>\n\n"
    for idx, word in enumerate(star_words, 1):
        text += f"{idx}. <b>{word['korean']}</b> - {word['uzbek']}\n"
        if idx % 40 == 0 and idx < len(star_words):
            await message.answer(text, parse_mode="HTML")
            text = ""
    if text:
        await message.answer(text, parse_mode="HTML")


# ==================== LUG'ATNI YUKLASH (DOWNLOAD) ====================

@router.callback_query(F.data.startswith("download_all:"))
async def download_all_words(callback: CallbackQuery, state: FSMContext):
    """Barcha so'zlarni yuklash"""
    format_type = callback.data.split(":")[1]
    user_id = callback.from_user.id

    await callback.message.edit_text("⏳ Fayl tayyorlanmoqda...")

    try:
        all_words_data = dict_handler.get_all_words(user_id)
        if not all_words_data:
            await callback.message.edit_text("❌ So'zlar topilmadi!\n\nIltimos avval /game orqali so'z qo'shing.")
            return

        if format_type == "word_ko_uz":
            all_words = [(w['korean'], w['uzbek']) for w in all_words_data]
            filepath = create_exam_word(
                all_words, location="📚 Barcha so'zlar", mode="kr_to_uz",
                filename_prefix="barcha-sozlar_ko-uz"
            )
            file = FSInputFile(filepath)
            await callback.message.answer_document(
                document=file,
                caption=f"✅ Lug'at tayyor!\n\n📊 Jami: {len(all_words)} so'z\n🔄 한국어 ➔ 우즈베크어"
            )
            if os.path.exists(filepath):
                os.remove(filepath)

        elif format_type == "word_uz_ko":
            all_words = [(w['korean'], w['uzbek']) for w in all_words_data]
            filepath = create_exam_word(
                all_words, location="📚 Barcha so'zlar", mode="uz_to_kr",
                filename_prefix="barcha-sozlar_uz-ko"
            )
            file = FSInputFile(filepath)
            await callback.message.answer_document(
                document=file,
                caption=f"✅ Lug'at tayyor!\n\n📊 Jami: {len(all_words)} so'z\n🔄 우즈베크어 ➔ 한국어"
            )
            if os.path.exists(filepath):
                os.remove(filepath)

        elif format_type == "json":
            temp_dir = "temp_exams"
            os.makedirs(temp_dir, exist_ok=True)
            filename = f"dictionary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(temp_dir, filename)
            json_data = {
                "total_words": len(all_words_data),
                "export_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "words": all_words_data
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            file = FSInputFile(filepath)
            await callback.message.answer_document(document=file, caption=f"✅ JSON tayyor!\n\n📊 Jami: {len(all_words_data)} so'z")
            if os.path.exists(filepath):
                os.remove(filepath)

        elif format_type == "word_both":
            all_words = [(w['korean'], w['uzbek']) for w in all_words_data]
            filepath = create_exam_word_bilingual(
                all_words, location="📚 Barcha so'zlar",
                filename_prefix="barcha-sozlar_ikki-tilda"
            )
            file = FSInputFile(filepath)
            await callback.message.answer_document(
                document=file,
                caption=f"✅ Lug'at tayyor!\n\n📊 Jami: {len(all_words)} so'z\n🔄 🇰🇷 한국어 + 🇺🇿 O'zbekcha"
            )
            if os.path.exists(filepath):
                os.remove(filepath)

        await callback.message.delete()

    except Exception as e:
        print(f"Download error: {e}")
        import traceback
        traceback.print_exc()
        await callback.message.edit_text("❌ Xatolik yuz berdi!\n\nIltimos qayta urinib ko'ring.")

    await callback.answer()


@router.callback_query(F.data == "cancel_download")
async def cancel_download(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer()


# ==================== AVTOMATIK EXAM (KUNLIK) ====================

def check_new_words_last_24h(user_id: int) -> bool:
    """Oxirgi 24 soatda yangi so'zlar qo'shilganmi?"""
    user_file = dict_handler.get_user_dict_file(user_id)
    if not os.path.exists(user_file):
        return False
    file_mtime = os.path.getmtime(user_file)
    return time_module.time() - file_mtime <= 86400


async def send_auto_exam():
    """Har kuni belgilangan vaqtda avtomatik exam yuborish"""
    all_users = await user_db.get_all_users()
    for user in all_users:
        user_id = user['user_id']
        if not check_new_words_last_24h(user_id):
            continue

        all_words_data = dict_handler.get_all_words(user_id)
        if not all_words_data:
            continue

        all_words = [(w['korean'], w['uzbek']) for w in all_words_data]
        groups = split_words_into_groups(all_words, EXAM_WORDS_PER_FILE)

        msg = f"📚 시험 시간!\n\n✅ 새 단어: {len(all_words)}개\n📄 옵션: {len(groups)}개\n\n"
        try:
            await bot.send_message(user_id, msg)
            for idx, group in enumerate(groups, 1):
                filepath = create_exam_word(
                    group, location="📚 Auto Exam", mode="kr_to_uz",
                    filename_prefix=f"kunlik-imtihon_{idx}-qism"
                )
                file = FSInputFile(filepath)
                await bot.send_document(user_id, document=file, caption=f"📝 옵션 {idx}: {len(group)}개 단어")
                if os.path.exists(filepath):
                    os.remove(filepath)
        except Exception as e:
            print(f"Auto exam error for {user_id}: {e}")


def schedule_exam_checker():
    """Belgilangan vaqtda kunlik exam tekshiruvchisi (alohida thread'da ishlatiladi)"""
    import schedule
    schedule.every().day.at(EXAM_AUTO_TIME).do(lambda: asyncio.create_task(send_auto_exam()))
    while True:
        schedule.run_pending()
        time_module.sleep(60)


@router.message(Command("checkwords"))
async def debug_check_words(message: Message):
    """So'zlarni tekshirish (debug komandasi)"""
    user_id = message.from_user.id
    all_words = dict_handler.get_all_words(user_id)
    if not all_words:
        await message.answer("❌ So'zlar topilmadi!")
        return

    topics = {}
    for w in all_words:
        t = w.get('topic', 'Unknown')
        s = w.get('section', 'general')
        topics.setdefault(t, {})
        topics[t][s] = topics[t].get(s, 0) + 1

    text = f"📊 So'zlar statistikasi:\n\nJami: {len(all_words)}\n\n"
    for t, sections in topics.items():
        text += f"📚 {t}:\n"
        for s, count in sections.items():
            text += f"  • {s}: {count} ta\n"
        text += "\n"
    await message.answer(text)


# ==================== MAIN ====================

async def main():
    try:
        print("⏳ Ma'lumotlar bazasi ishga tushmoqda...")
        await user_db.init_db()

        dp.include_router(router)

        commands = [
            BotCommand(command="start", description="🏠 Botni qayta ishga tushirish"),
            BotCommand(command="help", description="❓ Yordam va yo'riqnoma")
        ]
        print("📝 Menyu komandalari o'rnatilmoqda...")
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

        asyncio.create_task(send_auto_words())
        asyncio.create_task(auto_cleanup_loop())

        await bot.delete_webhook(drop_pending_updates=True)

        print("✅ Bot ishga tushdi!")
        print("📋 Menu commands o'rnatildi!")
        print("⏰ Avtomatik so'z yuborish faollashtirildi")

        await dp.start_polling(bot)

    except Exception as e:
        print(f"❌ BOT ISHGA TUSHISHIDA XATOLIK: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Bot to'xtatildi!")