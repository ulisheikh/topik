import asyncio
import random
from datetime import datetime
from aiogram.fsm.storage.base import StorageKey
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, 
    CallbackQuery, 
    ReplyKeyboardMarkup, 
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove
)
from database.db import UserDatabase
from aiogram import F
from aiogram import types
from aiogram.filters import Command, CommandObject

from config import BOT_TOKEN,DICTIONARY_BASE_PATH, USER_DB_PATH
from utils.db_handler import DictionaryHandler
import schedule
import threading
import time as time_module
from utils.exam_generator import create_exam_word, split_words_into_groups
from utils.exam_keyboards import (
    get_exam_main_keyboard,
    get_exam_topics_keyboard,
    get_exam_sections_keyboard
)
from config import EXAM_AUTO_TIME, EXAM_WORDS_PER_FILE

def get_text(lang: str, key: str, **kwargs) -> str:
    """Game matnini olish"""
    text = ALL_TEXTS.get(lang, ALL_TEXTS['uz']).get(key, key)  # ← TO'G'RI!
    try:
        return text.format(**kwargs)
    except:
        return text


class GameModeState(StatesGroup):
    selecting_mode = State()
    selecting_topic = State()
    selecting_section = State()
    playing = State()

class AutoPlayState(StatesGroup):
    selecting_time = State()  # Bu qator aniq mavjudligini tekshiring
    selecting_mode = State()
    selecting_topic = State()
    selecting_section = State()
    playing = State()

class ExamState(StatesGroup):
    selecting_mode = State()
    selecting_topic = State()
    selecting_section = State()

# ============================================
# 4. BOT VA ROUTER (FSM dan keyin)
# ============================================
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()


# DEBUG: Yo'lni tekshirish
import os
print(f"\n{'='*50}")
print(f"📂 Hozirgi papka: {os.getcwd()}")
print(f"📂 Dictionary path: {DICTIONARY_BASE_PATH}")
print(f"📂 Mavjudmi: {os.path.exists(DICTIONARY_BASE_PATH)}")

if os.path.exists(DICTIONARY_BASE_PATH):
    files = os.listdir(DICTIONARY_BASE_PATH)
    print(f"📄 Fayllar: {files}")
print(f"{'='*50}\n")

# Dictionary handler
dict_handler = DictionaryHandler(DICTIONARY_BASE_PATH)

# Initialization
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

dict_handler = DictionaryHandler(DICTIONARY_BASE_PATH)
user_db = UserDatabase(USER_DB_PATH)

# Global so'zlar tracking
user_word_pool = {}  # {user_id: [word_ids]}


class AdminState(StatesGroup):
    waiting_password = State()
    waiting_block_reason = State()
ALL_TEXTS = {
    "uz": {
        # ASOSIY MENYU VA UMUMIY
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
        "settings_menu": "⚙️ <b>Sozlamalar menyusi</b>\n\nBu yerda tilni o'zgartirishingiz yoki bot sozlamalarini tahrirlashingiz mumkin:", # QO'SHILDI
        "format_hint": "Format: [Savol]-[So'zlar soni]", # QO'SHILDI
        "select_chapter_title": "📚 <b>{topic}-Topik | {section}</b>", # QO'SHILDI

        # START VA STATISTIKA
        "start_message": "🎓 <b>Memorize Bot'ga xush kelibsiz!</b>\n\nBu bot TOPIK so'zlarini smart tarzda yodlashga yordam beradi.\n\n📊 <b>Bot ma'lumotlari:</b>\n👥 Foydalanuvchilar: {users}\n📚 Topiklar: {topics}\n📖 Jami so'zlar: {words}\n\nQuyidagi tugmalardan foydalaning! 👇",
        "my_stats": "📊 <b>Sizning statistikangiz:</b>\n\n✅ To'g'ri javoblar: {correct}\n❌ Noto'g'ri javoblar: {wrong}\n⏱ Faol vaqt: {time} daqiqa\n🏆 Reyting: {rank}/{total}",
        "bot_statistics": "📈 <b>Bot Statistikasi:</b>\n\n👥 Jami foydalanuvchilar: {users}\n📚 Bazadagi so'zlar: {words}",
        "about_bot": "ℹ️ <b>Bot haqida:</b>\n\n📌 Versiya: 2.0\n🔧 Texnologiya: Aiogram 3\n🎯 Maqsad: TOPIK so'zlarini yodlash\n\n🎮 O'yin rejimi - cheksiz mashq\n📂 Bo'limlar - Topik bo'yicha taqsimlangan\n📊 Statistika - Natijalarni kuzatish\n⏰ Avtomatik - Rejali yodlash",

        # O'YIN REJIMLARI
        "game_select_mode": "🎮 <b>O'yin rejimini tanlang:</b>",
        "btn_general_mode": "🌍 Umumiy rejim",
        "btn_custom_mode": "🎯 Belgilangan rejim",
        "game_select_topic": "📚 <b>Topikni tanlang:</b>",
        "game_select_section": "📖 <b>Bo'limni tanlang:</b>\n<i>{topic}</i>",
        "game_select_section_only": "📖 <b>{topic}</b>\n\nBo'limni tanlang:",
        "game_starting_custom": "🎮 <b>O'yin boshlandi!</b>\n\n📂 Topik: {topic}\n📖 Bo'lim: {section}\n\nYuborilayotgan so'zlar shu bo'limdan!",

        # SAVOLLAR
        "game_question": "🎮 <b>Savol #{count}:</b>\n>>> <i>{uzbek}</i>\n\n📍 {topic} › {section} › {chapter}\n📝 Koreys tilida yozing:",
        "auto_question_first": "🎮 <b>Savol:</b>\n>>> <i>{uzbek}</i>\n\n📍 {topic} › {section} › {chapter}\n📝 Koreys tilida yozing:",
        "auto_question": "🤖 <b>(AVTOMATIK SAVOL)</b> {count}/10\n\n⏰ So'z yodlash vaqti!\n\nSen bu so'zni bilasanmi? 🤔\n\n>>> <b>{uzbek}</b>\n\n📍 {topic} › {section} › {chapter}\n📝 Koreys tilida yozing:",

        # JAVOBLAR (FEEDBACK)
        "feedback_correct": "✅ <b>To'g'ri!</b> 🇰🇷 <code>{korean}</code>",
        "feedback_wrong": "❌ <b>Noto'g'ri!</b>\n🇰🇷 To'g'ri: <code>{korean}</code>\n📌 Siz: <s>{user_answer}</s>",
        "game_correct_short": "✅ <b>To'g'ri!</b> 🇰🇷 <code>{korean}</code>",
        "game_wrong_short": "❌ <b>Noto'g'ri!</b> 🇰🇷 <code>{korean}</code>\n📌 Siz: <s>{user_answer}</s>",

        # O'YIN TUGASHI VA TO'XTATISH
        "game_finished": "🎊 <b>O'yin tugadi!</b>\n\n✅ To'g'ri: <b>{correct}</b>\n❌ Noto'g'ri: <b>{wrong}</b>",
        "auto_game_finished": "🎉 <b>Avtomatik o'yin tugadi!</b>\n\n✅ To'g'ri: {correct}\n❌ Noto'g'ri: {wrong}\n\nKeyingi vaqtda yana so'zlar yuboriladi! ⏰",
        "game_stopped": "🛑 <b>O'yin to'xtatildi!</b>\n\n✅ To'g'ri: {correct}\n❌ Noto'g'ri: {wrong}",
        "btn_stop_game": "🛑 To'xtatish",

        # AVTO REJIM SOZLAMALARI
        "auto_select_time": "⏰ <b>Avtomatik rejim sozalamalari:</b>\n\nNecha daqiqada so'zlar kelsin?",
        "auto_time_set": "✅ Har {time} daqiqada 10 ta so'z yuboriladi!",
        "btn_5min": "⏱ 5 daqiqa", "btn_10min": "⏱ 10 daqiqa", "btn_15min": "⏱ 15 daqiqa", "btn_30min": "⏱ 30 daqiqa", "btn_60min": "⏱ 60 daqiqa",

        # ADMIN VA XATOLAR
        "no_words": "❌ So'zlar topilmadi!",
        "no_topics": "❌ Topiklar yo'q!",
        "no_sections": "❌ Bo'limlar yo'q!",
        "admin_welcome": "✅ Admin panelga xush kelibsiz!",
        "admin_enter_password": "🔐 Admin panelga kirish uchun parolni kiriting:",
        "admin_wrong_password": "❌ Noto'g'ri parol!",
        "admin_user_blocked": "✅ Foydalanuvchi bloklandi!",
        "admin_user_unblocked": "✅ Foydalanuvchi blokdan chiqarildi!",
        "chapters_select_topic": "📚 <b>Topikni tanlang:</b>",
        "chapters_select_section": "📖 <b>{topic}</b>\n\nBo'limni tanlang:",
        "chapters_select_chapter": "📖 <b>{topic} > {section}</b>\n\nSavolni tanlang:",
        "chapters_words": "📝 <b>{topic} > {section} > {chapter}</b>\n\nSo'zlar:\n\n{words}",
        "chapters_no_words": "❌ Bu bo'limda so'zlar yo'q!",
    },
    "ko": {
        # ASOSIY MENYU VA UMUMIY
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
        "settings_menu": "⚙️ <b>설정 메뉴</b>\n\n여기에서 언어를 변경하거나 봇 설정을 편집할 수 있습니다:", # QO'SHILDI
        "format_hint": "형식: [문항]-[단어 수]", # QO'SHILDI
        "select_chapter_title": "📚 <b>{topic}-토픽 | {section}</b>", # QO'SHILDI

        # START VA STATISTIKA
        "start_message": "🎓 <b>Memorize Bot에 오신 것을 환영합니다!</b>\n\n이 봇은 TOPIK 단어를 스마트하게 암기하는 데 도움을 줍니다.\n\n📊 <b>봇 정보:</b>\n👥 사용자: {users}\n📚 토픽: {topics}\n📖 총 단어: {words}\n\n아래 버튼을 사용하세요! 👇",
        "my_stats": "📊 <b>내 통계:</b>\n\n✅ 정답: {correct}\n❌ 오답: {wrong}\n⏱ 활동 시간: {time}분\n🏆 순위: {rank}/{total}",
        "bot_statistics": "📈 <b>봇 통계:</b>\n\n👥 총 사용자: {users}\n📚 데이터베이스 단어: {words}",
        "about_bot": "ℹ️ <b>봇 정보:</b>\n\n📌 버전: 2.0\n🔧 기술: Aiogram 3\n🎯 목적: TOPIK 단어 암기\n\n🎮 게임 모드 - 무한 연습\n📂 섹션 - 토픽별 분류\n📊 통계 - 결과 추적\n⏰ 자동 - 정기 학습",

        # O'YIN REJIMLARI
        "game_select_mode": "🎮 <b>게임 모드 선택:</b>",
        "btn_general_mode": "🌍 일반 모드",
        "btn_custom_mode": "🎯 맞춤 모드",
        "game_select_topic": "📚 <b>퇴픽 선택:</b>",
        "game_select_section": "📖 <b>섹션 선택:</b>\n<i>{topic}</i>",
        "game_select_section_only": "📖 <b>{topic}</b>\n\n섹션 선택:",
        "game_starting_custom": "🎮 <b>게임 시작!</b>\n\n📂 토픽: {topic}\n📖 섹션: {section}\n\n이 섹션에서 단어가 전송됩니다!",

        # SAVOLLAR
        "game_question": "🎮 <b>질문 #{count}:</b>\n>>> <i>{uzbek}</i>\n\n📍 {topic} › {section} › {chapter}\n📝 한국어로 작성하세요:",
        "auto_question_first": "🎮 <b>질문:</b>\n>>> <i>{uzbek}</i>\n\n📍 {topic} › {section} › {chapter}\n📝 한국어로 작성하세요:",
        "auto_question": "🤖 <b>(자동질문 모드)</b> {count}/10\n\n⏰ <b>단어 학습 시간!</b>\n📊 <b>질문: {count}/10</b>\n\n<i>이 단어를 알고 있나요?</i> 🤔\n\n>>> <i>{uzbek}</i>\n\n📍 {topic} › {section} › {chapter}\n📝 한국어로 작성하세요:",

        # JAVOBLAR (FEEDBACK)
        "feedback_correct": "✅ <b>정답!</b> 🇰🇷 <code>{korean}</code>",
        "feedback_wrong": "❌ <b>오답!</b>\n🇰🇷 정답: <code>{korean}</code>\n📌 입력: <s>{user_answer}</s>",
        "game_correct_short": "✅ <b>정답!</b> 🇰🇷 <code>{korean}</code>",
        "game_wrong_short": "❌ <b>오답!</b> 🇰🇷 <code>{korean}</code>\n📌 입력: <s>{user_answer}</s>",

        # O'YIN TUGASHI VA TO'XTATISH
        "game_finished": "🎊 <b>게임 종료!</b>\n\n✅ 정답: <b>{correct}</b>\n❌ 오답: <b>{wrong}</b>",
        "auto_game_finished": "🎉 <b>자동 게임 완료!</b>\n\n✅ 정답: {correct}\n❌ 오답: {wrong}\n\n다음 시간에 다시 단어가 전송됩니다! ⏰",
        "game_stopped": "🛑 <b>게임 중지!</b>\n\n✅ 정답: {correct}\n❌ 오답: {wrong}",
        "btn_stop_game": "🛑 중지",

        # AVTO REJIM SOZLAMALARI
        "auto_select_time": "⏰ <b>자동 모드 설정:</b>\n\n몇 분마다 단어를 받으시겠습니까?",
        "auto_time_set": "✅ {time}분마다 10개 단어가 전송됩니다!",
        "btn_5min": "⏱ 5분", "btn_10min": "⏱ 10분", "btn_15min": "⏱ 15분", "btn_30min": "⏱ 30분", "btn_60min": "⏱ 60분",

        # ADMIN VA XATOLAR
        "no_words": "❌ 단어를 찾을 수 없습니다!",
        "no_topics": "❌ 토픽 없음!",
        "no_sections": "❌ 섹션 없음!",
        "admin_welcome": "✅ 관리자 패널에 오신 것을 환영합니다!",
        "admin_enter_password": "🔐 관리자 패널에 접근하려면 비밀번호를 입력하세요:",
        "admin_wrong_password": "❌ 잘못된 비밀번호!",
        "admin_user_blocked": "✅ 사용자가 차단되었습니다!",
        "admin_user_unblocked": "✅ 사용자 차단이 해제되었습니다!",
        "chapters_select_topic": "📚 <b>토픽 선택:</b>",
        "chapters_select_section": "📖 <b>{topic}</b>\n\n섹션 선택:",
        "chapters_select_chapter": "📖 <b>{topic} > {section}</b>\n\n질문 선택:",
        "chapters_words": "📝 <b>{topic} > {section} > {chapter}</b>\n\n단어:\n\n{words}",
        "chapters_no_words": "❌ 이 섹션에 단어가 없습니다!",
        
        # EXAM
        "exam_select_mode": "📝 시험 유형을 선택하세요:",
        "exam_select_topic": "📚 토픽을 선택하세요:",
        "exam_select_section": "📚 {topic_num}-토픽\n\n섹션을 선택하세요:",
        "exam_file_sent": "✅ 파일이 전송되었습니다",
        "exam_no_words": "❌ 단어가 없습니다!",
    }
}
def get_text(lang, key, **kwargs):
    # Til kodlarini standartlashtirish
    target_lang = "ko" if lang in ["ko", "kr", "kr"] else "uz"
    
    # Matnni olish
    text = ALL_TEXTS.get(target_lang, {}).get(key, f"Missing key: {key}")
    
    # Formatlash (kwargs orqali o'zgaruvchilarni joylash)
    try:
        return text.format(**kwargs)
    except KeyError:
        return text

# ==================== WORD POOL MANAGER ====================

def get_next_word(user_id: int):
    """Takrorlanmaslik uchun so'z olish"""
    all_words = dict_handler.get_all_words(user_id)  # ✅ user_id qo'shildi
    
    if not all_words:
        return None
    
    # Agar user uchun pool bo'lmasa yoki tugasa, yangi pool yaratish
    if user_id not in user_word_pool or len(user_word_pool[user_id]) == 0:
        user_word_pool[user_id] = [w['id'] for w in all_words if 'id' in w]
        random.shuffle(user_word_pool[user_id])
    
    # Pool'dan birinchi so'zni olish
    word_id = user_word_pool[user_id].pop(0)
    
    # So'zni topish
    word = next((w for w in all_words if w.get('id') == word_id), None)
    
    return word if word else random.choice(all_words)

# ==================== KEYBOARDS ====================

def get_main_keyboard(lang: str) -> ReplyKeyboardMarkup:
    """Asosiy menyu klaviaturasi"""
    keyboard = [
        [KeyboardButton(text="/start")],
        [KeyboardButton(text="/game"), KeyboardButton(text="/avtogame")],
        [KeyboardButton(text="/bo'limlar"), KeyboardButton(text="/exam_doc")],  # ← YANGI
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

def get_game_keyboard(lang: str) -> InlineKeyboardMarkup:
    """O'yin klaviaturasi (To'xtatish tugmasi - INLINE)"""
    keyboard = [
        [InlineKeyboardButton(
            text=get_text(lang, "btn_stop_game"),
            callback_data="stop_game"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_chapters_topics_keyboard(user_id: int, lang: str) -> InlineKeyboardMarkup:
    """Topiklar ro'yxati"""
    topics = dict_handler.get_all_topics(user_id)  # ✅
    
    keyboard = []
    for topic in topics:
        keyboard.append([InlineKeyboardButton(
            text=f"📚 {topic}",
            callback_data=f"topic_{topic}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        text=get_text(lang, "back"),
        callback_data="main_menu"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_chapters_sections_keyboard(user_id: int, topic: str, lang: str) -> InlineKeyboardMarkup:
    sections = dict_handler.get_topic_sections(user_id, topic)  # ✅
    
    keyboard = []
    for section in sections:
        keyboard.append([InlineKeyboardButton(
            text=f"📖 {section.title()}",
            callback_data=f"section_{topic}_{section}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        text=get_text(lang, "back"),
        callback_data="chapters_main"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_chapters_chapters_keyboard(user_id: int, topic: str, section: str, lang: str) -> InlineKeyboardMarkup:
    chapters = dict_handler.get_section_chapters(user_id, topic, section)  # ✅
    
    keyboard = []
    for chapter in chapters:
        keyboard.append([InlineKeyboardButton(
            text=f"📝 {chapter}",
            callback_data=f"chapter_{topic}_{section}_{chapter}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        text=get_text(lang, "back"),
        callback_data=f"section_{topic}_{section}"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_language_keyboard() -> InlineKeyboardMarkup:
    """Til tanlash klaviaturasi"""
    keyboard = [
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")],
        [InlineKeyboardButton(text="🇰🇷 한국어", callback_data="lang_kr")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_settings_keyboard(lang: str, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Sozlamalar menyusi"""
    buttons = []
    
    # Faqat admin bo'lsa
    if is_admin:
        buttons.append([InlineKeyboardButton(text=get_text(lang, "admin_panel"), callback_data="admin_panel")])
    
    buttons.extend([
        [InlineKeyboardButton(text=get_text(lang, "change_language"), callback_data="change_language")],
        [InlineKeyboardButton(text=get_text(lang, "about_bot_btn"), callback_data="about_bot")],
        [InlineKeyboardButton(text=get_text(lang, "back_to_menu"), callback_data="back_to_menu")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Admin panel klaviaturasi"""
    keyboard = [
        [InlineKeyboardButton(text=get_text(lang, "admin_users"), callback_data="admin_users")],
        [InlineKeyboardButton(text=get_text(lang, "statistics"), callback_data="admin_stats")],
        [InlineKeyboardButton(text=get_text(lang, "back_to_menu"), callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_user_action_keyboard(user_id: int, is_blocked: bool, lang: str) -> InlineKeyboardMarkup:
    """User uchun block/unblock tugmasi"""
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

from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable

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

# ==================== HANDLERS ====================

# /start command
@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    
    # Foydalanuvchini ro'yxatdan o'tkazish
    await user_db.add_user(
        user_id=user_id,
        username=message.from_user.username or "unknown",
        first_name=message.from_user.first_name or "User"
    )
    
    lang = await user_db.get_language(user_id) or "uz"
    
    # Statistika
    total_users = await user_db.get_total_users()
    total_topics = len(dict_handler.get_all_topics(user_id))  # ✅ user_id qo'shildi
    total_words = dict_handler.get_total_words(user_id)       # ✅ user_id qo'shildi
    
    await message.answer(
        get_text(lang, "start_message", users=total_users, topics=total_topics, words=total_words),
        parse_mode="HTML",
        reply_markup=get_main_keyboard(lang)
    )
    
    await message.answer(
        get_text(lang, "main_menu"),
        reply_markup=get_main_menu_keyboard(lang)
    )

# /sozlamalar command
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

# /bo'limlar command
@router.message(Command("bo'limlar"))
async def cmd_chapters(message: Message):
    user_id = message.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    await message.answer(
        get_text(lang, "chapters_select_topic"),
        reply_markup=get_chapters_topics_keyboard(user_id, lang),
        parse_mode="HTML"  # ✅
    )

# Til tanlash callback
@router.callback_query(F.data.startswith("lang_"))
async def set_language_callback(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    await user_db.set_language(user_id, lang)
    
    await callback.message.edit_text(
        get_text(lang, "language_changed"),
        reply_markup=get_main_menu_keyboard(lang)
    )
    
    # Pastki tugmalarni yangilash
    await callback.message.answer(
        get_text(lang, "main_menu"),
        reply_markup=get_main_keyboard(lang)
    )
    await callback.answer()

# Statistika callback
@router.callback_query(F.data == "show_stats")
async def show_my_stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    stats = await user_db.get_statistics(user_id)
    rank, total = await user_db.get_ranking(user_id)
    
    time_minutes = stats['active_time'] // 60
    
    await callback.message.edit_text(
        get_text(
            lang, "my_stats",
            correct=stats['correct'],
            wrong=stats['wrong'],
            time=time_minutes,
            rank=rank,
            total=total
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, "back_to_menu"), callback_data="back_to_menu")]
        ])
    )
    await callback.answer()

# Sozlamalar callback
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

# About Bot
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

# Tilni o'zgartirish
@router.callback_query(F.data == "change_language")
async def change_lang_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    await callback.message.edit_text(
        get_text(lang, "choose_language"),
        reply_markup=get_language_keyboard()
    )
    await callback.answer()

# Asosiy menyuga qaytish
@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    await callback.message.edit_text(
        get_text(lang, "main_menu"),
        reply_markup=get_main_menu_keyboard(lang)
    )
    await callback.answer()

## ============================================
# /GAME KOMANDASI VA INLINE BOSHLASH
# ============================================

@router.message(Command("game"))
async def cmd_game(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, "btn_general_mode"), callback_data="game_mode_general")],
        [InlineKeyboardButton(text=get_text(lang, "btn_custom_mode"), callback_data="game_mode_custom")]
    ])
    await state.set_state(GameModeState.selecting_mode)
    await message.answer(get_text(lang, "game_select_mode"), reply_markup=markup, parse_mode="HTML")

@router.callback_query(F.data == "start_game")
async def inline_start_game(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, "btn_general_mode"), callback_data="game_mode_general")],
        [InlineKeyboardButton(text=get_text(lang, "btn_custom_mode"), callback_data="game_mode_custom")]
    ])
    
    await state.set_state(GameModeState.selecting_mode)
    await callback.message.edit_text(get_text(lang, "game_select_mode"), reply_markup=markup, parse_mode="HTML")
    await callback.answer()

# ============================================
# UMUMIY REJIM HANDLERI
# ============================================

@router.callback_query(F.data == "game_mode_general")
async def game_general_mode(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    # Direction tanlash klaviaturasi
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 Uz → 🇰🇷 Ko", callback_data="game_dir_general_uz_ko")],
        [InlineKeyboardButton(text="🇰🇷 Ko → 🇺🇿 Uz", callback_data="game_dir_general_ko_uz")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="game_back_to_mode")]
    ])
    
    await callback.message.edit_text(
        "🎮 <b>Tarjima yo'nalishini tanlang:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

# Direction tanlanganidan keyin umumiy rejim boshlash:
@router.callback_query(F.data.startswith("game_dir_general_"))
async def game_general_direction_selected(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    direction = callback.data.replace("game_dir_general_", "")  # uz_ko yoki ko_uz
    
    word = dict_handler.get_random_word(user_id)
    
    if not word:
        await callback.answer(get_text(lang, "no_words"), show_alert=True)
        await state.clear()
        return
    
    await state.set_state(GameModeState.playing)
    await state.update_data(
        current_word=word,
        start_time=datetime.now().timestamp(),
        question_count=1,
        mode='general',
        direction=direction  # ← YANGI
    )
    
    # Direction ga qarab savol yaratish
    if direction == "uz_ko":
        question_text = word['uzbek']
        answer_lang = "Koreys"
    else:  # ko_uz
        question_text = word['korean']
        answer_lang = "O'zbek"
    
    await callback.message.edit_text(
        f"🎮 <b>Savol #1:</b>\n>>> <i>{question_text}</i>\n\n"
        f"📍 {word['topic']} › {word['section']} › {word['chapter']}\n"
        f"📝 {answer_lang} tilida yozing:",
        reply_markup=get_game_keyboard(lang),
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================
# BELGILANGAN REJIM - TOPIK TANLASH
# ============================================

@router.callback_query(F.data == "game_mode_custom")
async def game_custom_mode(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    topics = dict_handler.get_all_topics(user_id)
    if not topics:
        await callback.answer(get_text(lang, "no_topics"), show_alert=True)
        return
    
    keyboard = [[InlineKeyboardButton(text=f"📚 {topic}", callback_data=f"game_topic_{topic}")] for topic in topics]
    
    await state.set_state(GameModeState.selecting_topic)
    await callback.message.edit_text(get_text(lang, "game_select_topic"), 
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

# ============================================
# BELGILANGAN REJIM - BO'LIM TANLASH
# ============================================

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
    
    await state.set_state(GameModeState.selecting_section)
    await state.update_data(selected_topic=topic)
    
    await callback.message.edit_text(get_text(lang, "game_select_section", topic=topic),
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

# ============================================
# BELGILANGAN REJIM - O'YIN BOSHLASH
# ============================================

@router.callback_query(F.data.startswith("game_section_"))
async def game_select_section(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    # Callbackni ajratib olish
    parts = callback.data.replace("game_section_", "").split("_", 1)
    topic = parts[0]
    section = parts[1]
    
    # Topik va sectionni saqlash
    await state.update_data(selected_topic=topic, selected_section=section)
    
    # Direction tanlash klaviaturasi
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 Uz → 🇰🇷 Ko", callback_data="game_dir_custom_uz_ko")],
        [InlineKeyboardButton(text="🇰🇷 Ko → 🇺🇿 Uz", callback_data="game_dir_custom_ko_uz")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"game_topic_{topic}")]
    ])
    
    await callback.message.edit_text(
        "🎮 <b>Tarjima yo'nalishini tanlang:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("game_dir_custom_"))
async def game_custom_direction_selected(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    direction = callback.data.replace("game_dir_custom_", "")  # uz_ko yoki ko_uz
    data = await state.get_data()
    topic = data.get('selected_topic')
    section = data.get('selected_section')
    
    # Bo'limdan birinchi so'zni olish
    word = dict_handler.get_random_word(user_id, topic=topic, section=section)
    
    if not word:
        await callback.answer(get_text(lang, "no_words"), show_alert=True)
        return
    
    await state.update_data(
        mode='custom',
        topic=topic,
        section=section,
        current_word=word,
        start_time=datetime.now().timestamp(),
        question_count=1,
        direction=direction  # ← YANGI
    )
    await state.set_state(GameModeState.playing)
    
    # Direction ga qarab savol yaratish
    if direction == "uz_ko":
        question_text = word['uzbek']
        answer_lang = "Koreys"
    else:  # ko_uz
        question_text = word['korean']
        answer_lang = "O'zbek"
    
    await callback.message.edit_text(
        get_text(lang, "game_starting_custom", topic=topic, section=section) + "\n\n" +
        f"🎮 <b>Savol #1:</b>\n>>> <i>{question_text}</i>\n\n"
        f"📍 {topic} › {section} › {word.get('chapter', '---')}\n"
        f"📝 {answer_lang} tilida yozing:",
        reply_markup=get_game_keyboard(lang),
        parse_mode="HTML"
    )
    await callback.answer()

# ============================================
# JAVOBNI TEKSHIRISH (ASOSIY MANTIQ)
# ============================================

@router.message(GameModeState.playing, lambda message: not message.text.startswith('/'))
async def process_game_answer(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    data = await state.get_data()
    
    word = data.get('current_word')
    direction = data.get('direction', 'uz_ko')  # Default uz_ko
    
    if not word:
        return

    user_answer = message.text.strip().lower()
    
    # Direction ga qarab to'g'ri javobni aniqlash
    if direction == "uz_ko":
        correct_answer = word['korean'].strip().lower()
        correct_display = word['korean']
    else:  # ko_uz
        correct_answer = word['uzbek'].strip().lower()
        correct_display = word['uzbek']
    
    is_correct = (user_answer == correct_answer)
    
    # Statistika
    start_time = data.get('start_time', datetime.now().timestamp())
    time_spent = int(datetime.now().timestamp() - start_time)
    await user_db.update_statistics(user_id, is_correct, time_spent)
    
    # Natija matni
    if is_correct:
        feedback = f"✅ <b>To'g'ri!</b>\n✔️ {correct_display}"
    else:
        feedback = f"❌ <b>Noto'g'ri!</b>\nTo'g'ri: <code>{correct_display}</code>"
    
    # Keyingi so'zni olish
    mode = data.get('mode', 'general')
    next_word = dict_handler.get_random_word(user_id, 
                                             topic=data.get('topic') if mode == 'custom' else None, 
                                             section=data.get('section') if mode == 'custom' else None)
    
    if not next_word:
        await message.answer(f"{feedback}\n\n🏁 " + get_text(lang, "no_words"))
        await state.clear()
        return

    q_count = data.get('question_count', 1) + 1
    await state.update_data(current_word=next_word, start_time=datetime.now().timestamp(), question_count=q_count)

    # Direction ga qarab keyingi savolni yaratish
    if direction == "uz_ko":
        question_text = next_word['uzbek']
        answer_lang = "Koreys"
    else:  # ko_uz
        question_text = next_word['korean']
        answer_lang = "O'zbek"

    next_question = f"🎮 <b>Savol #{q_count}:</b>\n>>> <i>{question_text}</i>\n\n" \
                   f"📍 {next_word['topic']} › {next_word['section']} › {next_word['chapter']}\n" \
                   f"📝 {answer_lang} tilida yozing:"

    await message.answer(f"{feedback}\n\n━━━━━━━━━━━━━━\n\n{next_question}", 
                         reply_markup=get_game_keyboard(lang), parse_mode="HTML")


# process_auto_answer ni ALMASHTIRISH:
@router.message(AutoPlayState.playing, lambda message: not message.text.startswith('/'))
async def process_auto_answer(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    data = await state.get_data()
    word = data.get('current_word')
    direction = data.get('direction', 'uz_ko')

    if not word: 
        return

    # Javobni tekshirish
    user_answer = message.text.strip().lower()
    
    # Direction ga qarab to'g'ri javob
    if direction == "uz_ko":
        correct_answer = word['korean'].strip().lower()
        correct_display = word['korean']
    else:  # ko_uz
        correct_answer = word['uzbek'].strip().lower()
        correct_display = word['uzbek']
    
    if user_answer == correct_answer:
        await user_db.update_statistics(user_id, True, 0)
        if lang == "uz":
            await message.answer(f"✅ <b>To'g'ri!</b> (Avtomatik)", parse_mode="HTML")
        else:
            await message.answer(f"✅ <b>정답!</b> (자동)", parse_mode="HTML")
    else:
        await user_db.update_statistics(user_id, False, 0)
        await message.answer(f"❌ <b>Xato!</b> ✔️: <code>{correct_display}</code>", parse_mode="HTML")

    # Keyingi savolga o'tish
    current_step = data.get('auto_current_step', 1)
    max_steps = 10

    if current_step < max_steps:
        next_word = dict_handler.get_random_word(
            user_id,
            topic=data.get('topic'),
            section=data.get('section')
        )
        if next_word:
            new_step = current_step + 1
            await state.update_data(current_word=next_word, auto_current_step=new_step)
            
            # Direction ga qarab savol
            if direction == "uz_ko":
                question_text = next_word['uzbek']
                answer_lang = "Koreys"
            else:  # ko_uz
                question_text = next_word['korean']
                answer_lang = "O'zbek"
            
            text = (
                f"🤖 <b>(AVTOMATIK SAVOL)</b> {new_step}/10\n\n"
                f"⏰ So'z yodlash vaqti!\n\n"
                f"Sen bu so'zni bilasanmi? 🤔\n\n"
                f">>> <b>{question_text}</b>\n\n"
                f"📍 {next_word.get('topic', '...')} › {next_word.get('section', '...')} › {next_word.get('chapter', '...')}\n"
                f"📝 {answer_lang} tilida yozing:"
            )
            await message.answer(text, parse_mode="HTML")
    else:
        stats = await user_db.get_statistics(user_id)
        await message.answer(
            f"🎉 10 ta so'z tugadi!\n\n✅ To'g'ri: {stats.get('correct', 0)}\n❌ Xato: {stats.get('wrong', 0)}",
            parse_mode="HTML"
        )


# ============================================
# O'YINNI TO'XTATISH
# ============================================

@router.callback_query(F.data == "stop_game")
async def stop_game_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    stats = await user_db.get_statistics(user_id)
    await state.clear()
    
    await callback.message.edit_text(
        get_text(lang, "game_stopped", correct=stats['correct'], wrong=stats['wrong']),
        parse_mode="HTML"
    )
    # Asosiy menyu tugmalarini yuborish
    from main import get_main_menu_keyboard # Import muammosi bo'lmasligi uchun
    await callback.message.answer("🏠", reply_markup=get_main_menu_keyboard(lang))
    await callback.answer()

# ============================================
# AVTOMATIK O'YIN TIZIMI
# ============================================

# /avtogame komandasi
@router.message(Command("avtogame"))
async def cmd_auto_game(message: Message, state: FSMContext):
    """Avtomatik o'yin - vaqtni tanlash"""
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
    await message.answer(
        get_text(lang, "auto_select_time"),
        reply_markup=markup,
        parse_mode="HTML"
    )

# Avto vaqtni tanlash
@router.callback_query(F.data.startswith("auto_time_"))
async def auto_select_time(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    time_minutes = int(callback.data.split("_")[2])
    await state.update_data(auto_interval=time_minutes)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang, "btn_general_mode"), callback_data="auto_mode_general")],
        [InlineKeyboardButton(text=get_text(lang, "btn_custom_mode"), callback_data="auto_mode_custom")]
    ])
    
    await state.set_state(AutoPlayState.selecting_mode)
    await callback.message.edit_text(
        get_text(lang, "auto_time_set", time=time_minutes) + "\n\n" + get_text(lang, "game_select_mode"),
        reply_markup=markup,
        parse_mode="HTML"
    )
    await callback.answer()

# Avto umumiy rejim
@router.callback_query(F.data == "auto_mode_general")
async def auto_general_mode(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    # Direction tanlash klaviaturasi
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 Uz → 🇰🇷 Ko", callback_data="auto_dir_general_uz_ko")],
        [InlineKeyboardButton(text="🇰🇷 Ko → 🇺🇿 Uz", callback_data="auto_dir_general_ko_uz")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="auto_back_to_mode")]
    ])
    
    await callback.message.edit_text(
        "🤖 <b>Avtomatik rejim uchun yo'nalishni tanlang:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("auto_dir_general_"))
async def auto_general_direction_selected(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    direction = callback.data.replace("auto_dir_general_", "")
    data = await state.get_data()
    interval = data.get('auto_interval', 15)
    
    await state.update_data(mode='general', topic=None, section=None, direction=direction)
    
    msg = (f"✅ Avtomatik rejim faollashtirildi!\n⏰ Har {interval} daqiqada so'zlar keladi." if lang == "uz" 
           else f"✅ 자동 모드가 활성화되었습니다!\n⏰ {interval}분마다 단어가 전송됩니다.")
    
    await callback.message.edit_text(msg, parse_mode="HTML")
    await state.set_state(AutoPlayState.playing)
    await callback.answer()

# Avto belgilangan rejim - topik
@router.callback_query(F.data == "auto_mode_custom")
async def auto_custom_mode(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    topics = dict_handler.get_all_topics(user_id)
    if not topics:
        await callback.answer(get_text(lang, "no_topics"), show_alert=True)
        return
    
    keyboard = [[InlineKeyboardButton(text=f"📚 {t}", callback_data=f"auto_topic_{t}")] for t in topics]
    
    await state.set_state(AutoPlayState.selecting_topic)
    await callback.message.edit_text(
        get_text(lang, "game_select_topic"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await callback.answer()

# Avto topik tanlandi - bo'lim tanlash
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
    
    await state.set_state(AutoPlayState.selecting_section)
    await callback.message.edit_text(
        get_text(lang, "game_select_section_only", topic=topic),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await callback.answer()

# Avto bo'lim tanlandi - faollashtirish
@router.callback_query(F.data.startswith("auto_section_"))
async def auto_select_section(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    section = callback.data.replace("auto_section_", "")
    data = await state.get_data()
    
    await state.update_data(selected_section=section)
    
    # Direction tanlash klaviaturasi
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 Uz → 🇰🇷 Ko", callback_data="auto_dir_custom_uz_ko")],
        [InlineKeyboardButton(text="🇰🇷 Ko → 🇺🇿 Uz", callback_data="auto_dir_custom_ko_uz")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"auto_topic_{data.get('topic')}")]
    ])
    
    await callback.message.edit_text(
        "🤖 <b>Avtomatik rejim uchun yo'nalishni tanlang:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================
# AVTOMATIK YUBORISH TIZIMI (Scheduler)
# ============================================
# send_auto_words funksiyasini ALMASHTIRISH (1033-1098 qatorlar):
async def send_auto_words():
    from aiogram.fsm.storage.base import StorageKey
    import time

    while True:
        try:
            users = await user_db.get_all_users()
            for user in users:
                user_id = user['user_id']
                state_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
                state = FSMContext(storage=storage, key=state_key)
                current_state = await state.get_state()
                
                if current_state == AutoPlayState.playing:
                    data = await state.get_data()
                    
                    interval_min = data.get('auto_interval', 15) 
                    interval_sec = interval_min * 60
                    last_sent = data.get('last_auto_sent', 0)
                    now = time.time()

                    if now - last_sent >= interval_sec:
                        lang = await user_db.get_language(user_id) or "uz"
                        direction = data.get('direction', 'uz_ko')
                        
                        word = dict_handler.get_random_word(
                            user_id,
                            topic=data.get('topic'),
                            section=data.get('section')
                        )
                        
                        if word:
                            await state.update_data(
                                current_word=word, 
                                last_auto_sent=now, 
                                auto_current_step=1
                            )
                            
                            # Direction ga qarab savol
                            if direction == "uz_ko":
                                question_text = word['uzbek']
                                answer_lang = "Koreys"
                            else:  # ko_uz
                                question_text = word['korean']
                                answer_lang = "O'zbek"
                            
                            if lang == "uz":
                                text = (
                                    f"🤖 <b>(AVTOMATIK SAVOL)</b> 1/10\n\n"
                                    f"⏰ So'z yodlash vaqti!\n\n"
                                    f"Sen bu so'zni bilasanmi? 🤔\n\n"
                                    f">>> <b>{question_text}</b>\n\n"
                                    f"📍 {word.get('topic', '...')} › {word.get('section', '...')} › {word.get('chapter', '...')}\n"
                                    f"📝 {answer_lang} tilida yozing:"
                                )
                            else:
                                text = (
                                    f"🤖 <b>(자동질문 모드)</b> 1/10\n\n"
                                    f"⏰ <b>단어 학습 시간!</b>\n"
                                    f"📊 <b>질문: 1/10</b>\n\n"
                                    f"<i>이 단어를 알고 있나요?</i> 🤔\n\n"
                                    f">>> <i>{question_text}</i>\n\n"
                                    f"📍 {word.get('topic', '...')} › {word.get('section', '...')} › {word.get('chapter', '...')}\n"
                                    f"📝 {answer_lang}로 작성하세요:"
                                )
                            
                            await bot.send_message(user_id, text, parse_mode="HTML")
                            
        except Exception as e:
            print(f"❌ send_auto_words xatosi: {e}")
            
        await asyncio.sleep(20)

# ==================== BO'LIMLAR ====================
from aiogram.utils.keyboard import InlineKeyboardBuilder

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
    
    # Ma'lumotlarni yuklash
    data = dict_handler.load_user_data(user_id)
    topic_key = f"Topik-{topic.replace('-topik', '')}"
    
    section_data = {}
    if topic_key in data and section in data[topic_key]:
        section_data = data[topic_key][section]

    builder = InlineKeyboardBuilder()
    
    # 1. 1-dan 49-savolgacha (7 ta ustun)
    for i in range(1, 50):
        chapter_key = f"{i}-savol so'zlari"
        word_count = len(section_data.get(chapter_key, {}))
        
        # Format: 1-0, 1-12 va hokazo
        btn_text = f"{i}-{word_count}"
        
        builder.button(
            text=btn_text, 
            callback_data=f"chapter_{topic}_{section}_{i}-savol"
        )
    
    builder.adjust(7)

    # 2. 50-savol (eng pastda, "savol" so'zisiz)
    ch50_key = "50-savol so'zlari"
    count50 = len(section_data.get(ch50_key, {}))
    builder.row(InlineKeyboardButton(
        text=f"50-{count50}", 
        callback_data=f"chapter_{topic}_{section}_50-savol"
    ))

    # 3. Orqaga qaytish
    builder.row(InlineKeyboardButton(
        text=get_text(lang, "back"), 
        callback_data=f"topic_{topic}"
    ))

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
        # Raqamni ajratib ko'rsatish: "1-savol" -> "1"
        ch_num = chapter.split("-")[0]
        await callback.answer(f"⚠️ {ch_num}-savolda so'zlar yo'q", show_alert=True)
        return
    
    text = f"📚 <b>{chapter.replace('-', ' ').title()}</b>\n\n"
    for korean, uzbek in words.items():
        text += f"🇰🇷 {korean} – 🇺🇿 {uzbek}\n"
    
    text += f"\n📊 {get_text(lang, 'statistics')}: {len(words)}"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
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
        await callback.message.edit_text(
            get_text(lang, "admin_welcome"),
            reply_markup=get_admin_keyboard(lang)
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        get_text(lang, "admin_enter_password")
    )
    await state.set_state(AdminState.waiting_password)
    await callback.answer()

@router.message(AdminState.waiting_password)
async def check_admin_password(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    if message.text == ADMIN_PASSWORD:
        await user_db.add_admin(user_id)
        
        await message.answer(
            get_text(lang, "admin_welcome"),
            reply_markup=get_admin_keyboard(lang)
        )
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
        
        keyboard.append([
            InlineKeyboardButton(
                text=f"{user['first_name'][:20]}",
                callback_data=f"user_detail_{user['user_id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text=get_text(lang, "back"), callback_data="admin_panel")
    ])
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
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
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_user_action_keyboard(target_user_id, is_blocked, lang)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("block_"))
async def admin_block_user(callback: CallbackQuery, state: FSMContext):
    target_user_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    await state.update_data(target_user_id=target_user_id)
    await callback.message.edit_text(
        get_text(lang, "admin_enter_block_reason")
    )
    await state.set_state(AdminState.waiting_block_reason)
    await callback.answer()

@router.callback_query(F.data.startswith("unblock_"))
async def admin_unblock_user(callback: CallbackQuery):
    target_user_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    await user_db.unblock_user(target_user_id)
    await callback.answer(get_text(lang, "admin_user_unblocked"), show_alert=True)
    
    # Detail sahifaga qaytish
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
    
    if message.text == "/skip":
        reason = None
    else:
        reason = message.text
    
    await user_db.block_user(target_user_id, reason)
    
    await message.answer(get_text(lang, "admin_user_blocked"))
    await message.answer(
        get_text(lang, "admin_welcome"),
        reply_markup=get_admin_keyboard(lang)
    )
    
    await state.clear()

@router.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await user_db.get_language(user_id) or "uz"
    
    total_users = await user_db.get_total_users()
    
    # BARCHA userlarning so'zlari
    all_users = await user_db.get_all_users()
    total_words = sum(dict_handler.get_total_words(u['user_id']) for u in all_users)  # ✅
    
    await callback.message.edit_text(
        get_text(lang, "bot_statistics", users=total_users, words=total_words),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text(lang, "back"), callback_data="admin_panel")]
        ])
    )
    await callback.answer()

# ============================================
# EXAM TIZIMI - DEBUG VERSIYA
# ============================================

import os
import random
from aiogram import F, types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext


# ============================================
# 1. ASOSIY TUGMA - BO'LIMLAR RO'YXATI (DEBUG)
# ============================================

@router.message(F.text == "/exam_doc")
async def cmd_exam_list(message: Message, state: FSMContext):
    """Bo'limlarni ko'rsatish - DEBUG versiya"""
    user_id = message.from_user.id
    await state.clear()
    
    # DEBUG: Ma'lumotlarni tekshirish
    print(f"\n{'='*50}")
    print(f"USER ID: {user_id}")
    
    # 1. Barcha so'zlarni olish (asosiy metod)
    all_words = dict_handler.get_all_words(user_id)
    print(f"Jami so'zlar: {len(all_words) if all_words else 0}")
    
    if all_words:
        print(f"Birinchi so'z: {all_words[0]}")
    
    # 2. Topiklar
    topics = dict_handler.get_all_topics(user_id)
    print(f"Topiklar: {topics}")
    
    # 3. User data
    try:
        user_data = dict_handler.load_user_data(user_id)
        keys_text = list(user_data.keys()) if user_data else "BO'SH"
        print(f"User data keys: {keys_text}")
    except Exception as e:
        print(f"User data xatosi: {e}")
    
    print(f"{'='*50}\n")
    
    # Agar hech narsa bo'lmasa
    if not all_words:
        await message.answer(
            "❌ Sizda hali so'zlar yo'q!\n\n"
            "Iltimos avval /game orqali so'z qo'shing."
        )
        return
    
    # YANGI YONDASHUV: Topiklar emas, balki BARCHA so'zlardan bo'limlarni olish
    keyboard = []
    sections_found = set()
    
    for word in all_words:
        topic = word.get('topic', 'Unknown')
        section = word.get('section', 'general')
        
        # Unique bo'limlarni saqlash
        section_key = f"{topic}:{section}"
        if section_key not in sections_found:
            sections_found.add(section_key)
            
            # Bo'lim nomini koreyscha
            section_map = {
                'reading': '읽기',
                'writing': '쓰기', 
                'listening': '듣기',
                'general': '일반'
            }
            section_korean = section_map.get(section, section)
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📚 {topic} › {section_korean}",
                    callback_data=f"exam_section:{topic}:{section}"
                )
            ])
    
    # Agar bo'limlar topilmasa
    if not keyboard:
        await message.answer(
            "❌ Bo'limlar aniqlanmadi!\n\n"
            "Debug info:\n"
            f"• So'zlar: {len(all_words)}\n"
            f"• Topiklar: {len(topics)}\n\n"
            "So'z strukturasini tekshiring."
        )
        return
    
    # Random exam tugmasi
    keyboard.append([
        InlineKeyboardButton(
            text="🎲 Barcha so'zlardan (Random)",
            callback_data="exam_random_all"
        )
    ])
    
    await message.answer(
        f"📚 시험 섹션을 선택하세요:\n"
        f"(Mavjud bo'limlar: {len(sections_found)})\n\n"
        f"Imtihon bo'limini tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


# ============================================
# 2. BO'LIM TANLANDI - YO'NALISH SO'RASH
# ============================================

@router.callback_query(F.data.startswith("exam_section:"))
async def exam_section_selected(callback: CallbackQuery, state: FSMContext):
    """Bo'lim tanlandi - yo'nalish so'rash"""
    parts = callback.data.split(":")
    topic = parts[1]
    section = parts[2]
    
    user_id = callback.from_user.id
    
    # DEBUG: So'zlar borligini tekshirish
    all_words = dict_handler.get_all_words(user_id)
    filtered_words = [w for w in all_words if w.get('topic') == topic and w.get('section') == section]
    
    print(f"\n{'='*50}")
    print(f"Bo'lim tanlandi: {topic} › {section}")
    print(f"Filtrlangan so'zlar: {len(filtered_words)}")
    print(f"{'='*50}\n")
    
    if not filtered_words:
        await callback.answer("❌ Bu bo'limda so'zlar topilmadi!", show_alert=True)
        return
    
    # State ga saqlaymiz
    await state.update_data(exam_topic=topic, exam_section=section)
    
    # Bo'lim nomini koreyscha
    section_map = {
        'reading': '읽기',
        'writing': '쓰기',
        'listening': '듣기',
        'general': '일반'
    }
    section_korean = section_map.get(section, section)
    
    # Yo'nalish tanlash tugmalari
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🇰🇷 한국어 ➔ 🇺🇿 우즈베크어",
                callback_data="exam_mode:kr_to_uz"
            )
        ],
        [
            InlineKeyboardButton(
                text="🇺🇿 우즈베크어 ➔ 🇰🇷 한국어", 
                callback_data="exam_mode:uz_to_kr"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Orqaga",
                callback_data="exam_back_to_sections"
            )
        ]
    ])
    
    await callback.message.edit_text(
        f"📚 {topic} › {section_korean}\n"
        f"📊 {len(filtered_words)}개 단어\n\n"
        f"🔄 시험 형식을 선택하세요:\n"
        f"(Imtihon formatini tanlang:)",
        reply_markup=keyboard
    )
    await callback.answer()


# ============================================
# 3. YO'NALISH TANLANDI - FAYL YARATISH
# ============================================

@router.callback_query(F.data.startswith("exam_mode:"))
async def exam_mode_selected(callback: CallbackQuery, state: FSMContext):
    """Yo'nalish tanlandi - fayl yaratish"""
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
        # So'zlarni olish (to'g'ridan-to'g'ri get_all_words dan)
        all_words = dict_handler.get_all_words(user_id)
        
        # Filtrlash
        words = []
        for w in all_words:
            if w.get('topic') == topic and w.get('section') == section:
                words.append((w['korean'], w['uzbek']))
        
        print(f"\n{'='*50}")
        print(f"Fayl yaratish: {topic} › {section}")
        print(f"Topilgan so'zlar: {len(words)}")
        print(f"Mode: {mode}")
        print(f"{'='*50}\n")
        
        if not words:
            await callback.message.edit_text(
                "❌ Bu bo'limda so'zlar topilmadi!\n\n"
                "Debug info:\n"
                f"• Topic: {topic}\n"
                f"• Section: {section}\n"
                f"• Jami so'zlar: {len(all_words)}"
            )
            await state.clear()
            return
        
        # Random aralashtirish
        random.shuffle(words)
        
        # Bo'lim nomini koreyscha
        section_map = {
            'reading': '읽기',
            'writing': '쓰기',
            'listening': '듣기',
            'general': '일반'
        }
        section_korean = section_map.get(section, section)
        
        # Manzil
        location = f"{topic} › {section_korean}"
        
        # Word fayl yaratish
        filepath = create_exam_word(words, location=location, mode=mode)
        
        # Yuborish
        file = FSInputFile(filepath)
        mode_text = "🇰🇷 ➔ 🇺🇿" if mode == "kr_to_uz" else "🇺🇿 ➔ 🇰🇷"
        
        await callback.message.answer_document(
            document=file,
            caption=f"✅ 시험지가 준비되었습니다!\n\n"
                   f"📂 {location}\n"
                   f"🔄 {mode_text}\n"
                   f"📊 {len(words)}개 단어"
        )
        
        await callback.message.delete()
        
        if os.path.exists(filepath):
            os.remove(filepath)
        
        await state.clear()
        
    except Exception as e:
        print(f"Exam error: {e}")
        import traceback
        traceback.print_exc()
        
        await callback.message.edit_text(
            f"❌ Xatolik yuz berdi!\n\n"
            f"Error: {str(e)}"
        )
        await state.clear()


# ============================================
# 4. ORQAGA QAYTISH
# ============================================

@router.callback_query(F.data == "exam_back_to_sections")
async def exam_back_to_sections(callback: CallbackQuery, state: FSMContext):
    """Bo'limlar ro'yxatiga qaytish"""
    user_id = callback.from_user.id
    await state.clear()
    
    all_words = dict_handler.get_all_words(user_id)
    
    keyboard = []
    sections_found = set()
    
    for word in all_words:
        topic = word.get('topic', 'Unknown')
        section = word.get('section', 'general')
        
        section_key = f"{topic}:{section}"
        if section_key not in sections_found:
            sections_found.add(section_key)
            
            section_map = {
                'reading': '읽기',
                'writing': '쓰기',
                'listening': '듣기',
                'general': '일반'
            }
            section_korean = section_map.get(section, section)
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📚 {topic} › {section_korean}",
                    callback_data=f"exam_section:{topic}:{section}"
                )
            ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="🎲 Barcha so'zlardan (Random)",
            callback_data="exam_random_all"
        )
    ])
    
    await callback.message.edit_text(
        "📚 시험 섹션을 선택하세요:\n(Imtihon bo'limini tanlang:)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


# ============================================
# 5. RANDOM EXAM
# ============================================

@router.callback_query(F.data == "exam_random_all")
async def exam_random_handler(callback: CallbackQuery, state: FSMContext):
    """Random exam - barcha so'zlardan"""
    user_id = callback.from_user.id
    await state.clear()
    
    all_words_data = dict_handler.get_all_words(user_id)
    
    if not all_words_data:
        await callback.answer("❌ So'zlar topilmadi!", show_alert=True)
        return
    
    all_words = [(w['korean'], w['uzbek']) for w in all_words_data]
    random.shuffle(all_words)
    
    await state.update_data(exam_random_words=all_words[:50])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🇰🇷 한국어 ➔ 🇺🇿 우즈베크어",
                callback_data="exam_random_mode:kr_to_uz"
            )
        ],
        [
            InlineKeyboardButton(
                text="🇺🇿 우즈베크어 ➔ 🇰🇷 한국어",
                callback_data="exam_random_mode:uz_to_kr"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Orqaga",
                callback_data="exam_back_to_sections"
            )
        ]
    ])
    
    await callback.message.edit_text(
        f"🎲 Tasodifiy imtihon\n\n"
        f"📊 {len(all_words[:50])}개 단어\n\n"
        f"🔄 형식을 선택하세요:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("exam_random_mode:"))
async def exam_random_mode_selected(callback: CallbackQuery, state: FSMContext):
    """Random exam yo'nalishi"""
    mode = callback.data.split(":")[1]
    data = await state.get_data()
    words = data.get('exam_random_words', [])
    
    if not words:
        await callback.answer("❌ Xatolik!", show_alert=True)
        return
    
    await callback.message.edit_text("⏳ 파일을 준비 중입니다...")
    
    try:
        filepath = create_exam_word(words, location="Random", mode=mode)
        
        file = FSInputFile(filepath)
        mode_text = "🇰🇷 ➔ 🇺🇿" if mode == "kr_to_uz" else "🇺🇿 ➔ 🇰🇷"
        
        await callback.message.answer_document(
            document=file,
            caption=f"✅ 랜덤 시험!\n\n🔄 {mode_text}\n📊 {len(words)}개"
        )
        
        await callback.message.delete()
        
        if os.path.exists(filepath):
            os.remove(filepath)
        
        await state.clear()
        
    except Exception as e:
        print(f"Random exam error: {e}")
        await callback.message.edit_text(f"❌ Xatolik: {str(e)}")
        await state.clear()


# ============================================
# 6. AVTOMATIK EXAM (05:00)
# ============================================

def check_new_words_last_24h(user_id: int) -> bool:
    """Oxirgi 24 soatda yangi so'zlar qo'shilganmi?"""
    user_file = dict_handler.get_user_dict_file(user_id)
    
    if not os.path.exists(user_file):
        return False
    
    file_mtime = os.path.getmtime(user_file)
    time_diff = time_module.time() - file_mtime
    
    return time_diff <= 86400


async def send_auto_exam():
    """Har kuni 05:00 da avtomatik exam"""
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
        
        msg = "📚 시험 시간!\n\n"
        msg += f"✅ 새 단어: {len(all_words)}개\n"
        msg += f"📄 옵션: {len(groups)}개\n\n"
        
        try:
            await bot.send_message(user_id, msg)
            
            for idx, group in enumerate(groups, 1):
                filepath = create_exam_word(group, location=None, mode="kr_to_uz")
                file = FSInputFile(filepath)
                await bot.send_document(
                    user_id,
                    document=file,
                    caption=f"📝 옵션 {idx}: {len(group)}개 단어"
                )
                os.remove(filepath)
        
        except Exception as e:
            print(f"Auto exam error for {user_id}: {e}")


def schedule_exam_checker():
    """05:00 scheduler"""
    import schedule
    
    schedule.every().day.at(EXAM_AUTO_TIME).do(
        lambda: asyncio.create_task(send_auto_exam())
    )
    
    while True:
        schedule.run_pending()
        time_module.sleep(60)


# ============================================
# DEBUG UCHUN QO'SHIMCHA KOMANDA
# ============================================

@router.message(Command("checkwords"))
async def debug_check_words(message: Message):
    """So'zlarni tekshirish (debug)"""
    user_id = message.from_user.id
    
    all_words = dict_handler.get_all_words(user_id)
    
    if not all_words:
        await message.answer("❌ So'zlar topilmadi!")
        return
    
    # Statistika
    topics = {}
    for w in all_words:
        topic = w.get('topic', 'Unknown')
        section = w.get('section', 'general')
        
        if topic not in topics:
            topics[topic] = {}
        if section not in topics[topic]:
            topics[topic][section] = 0
        topics[topic][section] += 1
    
    # Matn
    text = f"📊 So'zlar statistikasi:\n\n"
    text += f"Jami: {len(all_words)}\n\n"
    
    for topic, sections in topics.items():
        text += f"📚 {topic}:\n"
        for section, count in sections.items():
            text += f"  • {section}: {count} ta\n"
        text += "\n"
    
    await message.answer(text)

# ============================================
# EXAM TIZIMI - TO'LIQ KOD (BOSHQA KODLARNI O'CHIRING!)
# ============================================
# Bu kodlarni ishlatishdan oldin eski exam handlerlarni BUTUNLAY o'chiring!

# import os
# import random
# from aiogram import F, types
# from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
# from aiogram.fsm.context import FSMContext


# ============================================
# 1. ASOSIY TUGMA - BO'LIMLAR RO'YXATI
# ============================================

@router.message(F.text == "/exam_doc")
async def cmd_exam_list(message: Message, state: FSMContext):
    """Bo'limlarni ko'rsatish (asosiy kirish nuqtasi)"""
    user_id = message.from_user.id
    await state.clear()
    
    # Barcha mavjud topiklar va bo'limlarni olish
    topics = dict_handler.get_all_topics(user_id)
    
    if not topics:
        await message.answer("❌ Lug'atingizda ma'lumot topilmadi!")
        return
    
    # Bo'limlar ro'yxatini yaratish
    keyboard = []
    
    for topic in topics:
        sections = dict_handler.get_topic_sections(user_id, topic)
        for section in sections:
            # Bo'lim nomini koreyscha
            section_map = {
                'reading': '읽기',
                'writing': '쓰기', 
                'listening': '듣기'
            }
            section_korean = section_map.get(section, section)
            
            # Har bir bo'lim uchun tugma
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📚 {topic} › {section_korean}",
                    callback_data=f"exam_section:{topic}:{section}"
                )
            ])
    
    # Agar bo'limlar topilmasa
    if not keyboard:
        await message.answer("❌ Bo'limlar topilmadi!")
        return
    
    # Qo'shimcha: Random exam tugmasi (ixtiyoriy)
    keyboard.append([
        InlineKeyboardButton(
            text="🎲 Tasodifiy (Random)",
            callback_data="exam_random_all"
        )
    ])
    
    await message.answer(
        "📚 시험 섹션을 선택하세요:\n(Imtihon bo'limini tanlang:)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


# ============================================
# 2. BO'LIM TANLANDI - YO'NALISH SO'RASH
# ============================================

@router.callback_query(F.data.startswith("exam_section:"))
async def exam_section_selected(callback: CallbackQuery, state: FSMContext):
    """Bo'lim tanlandi - endi yo'nalish (mode) so'raymiz"""
    # Data formati: exam_section:Topik-35:reading
    parts = callback.data.split(":")
    topic = parts[1]
    section = parts[2]
    
    # State ga saqlaymiz (keyingi bosqichda kerak bo'ladi)
    await state.update_data(exam_topic=topic, exam_section=section)
    
    # Bo'lim nomini koreyscha
    section_map = {
        'reading': '읽기',
        'writing': '쓰기',
        'listening': '듣기'
    }
    section_korean = section_map.get(section, section)
    
    # Yo'nalish tanlash tugmalari
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🇰🇷 한국어 ➔ 🇺🇿 우즈베크어",
                callback_data="exam_mode:kr_to_uz"
            )
        ],
        [
            InlineKeyboardButton(
                text="🇺🇿 우즈베크어 ➔ 🇰🇷 한국어", 
                callback_data="exam_mode:uz_to_kr"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Orqaga",
                callback_data="exam_back_to_sections"
            )
        ]
    ])
    
    await callback.message.edit_text(
        f"📚 {topic} › {section_korean}\n\n"
        f"🔄 시험 형식을 선택하세요:\n"
        f"(Imtihon formatini tanlang:)",
        reply_markup=keyboard
    )
    await callback.answer()


# ============================================
# 3. YO'NALISH TANLANDI - FAYL YARATISH
# ============================================

@router.callback_query(F.data.startswith("exam_mode:"))
async def exam_mode_selected(callback: CallbackQuery, state: FSMContext):
    """Yo'nalish tanlandi - fayl yaratamiz va yuboramiz"""
    # Mode olish
    mode = callback.data.split(":")[1]  # kr_to_uz yoki uz_to_kr
    
    # State dan ma'lumotlarni olish
    data = await state.get_data()
    topic = data.get('exam_topic')
    section = data.get('exam_section')
    user_id = callback.from_user.id
    
    if not topic or not section:
        await callback.answer("❌ Xatolik yuz berdi!", show_alert=True)
        await state.clear()
        return
    
    # Kutish xabari
    await callback.message.edit_text("⏳ 파일을 준비 중입니다...\n(Fayl tayyorlanmoqda...)")
    
    try:
        # So'zlarni olish
        user_data = dict_handler.load_user_data(user_id)
        
        if topic not in user_data or section not in user_data[topic]:
            await callback.message.edit_text("❌ Bu bo'limda so'zlar topilmadi!")
            await state.clear()
            return
        
        # Barcha so'zlarni yig'ish
        words = []
        for chapter_data in user_data[topic][section].values():
            for korean, uzbek in chapter_data.items():
                words.append((korean, uzbek))
        
        if not words:
            await callback.message.edit_text("❌ So'zlar topilmadi!")
            await state.clear()
            return
        
        # Random aralashtirish
        random.shuffle(words)
        
        # Bo'lim nomini koreyscha
        section_map = {
            'reading': '읽기',
            'writing': '쓰기',
            'listening': '듣기'
        }
        section_korean = section_map.get(section, section)
        
        # Manzil (location)
        location = f"{topic} › {section_korean}"
        
        # Word fayl yaratish (maksimal 25 ta so'z)
        filepath = create_exam_word(words[:25], location=location, mode=mode)
        
        # Faylni yuborish
        file = FSInputFile(filepath)
        
        mode_text = "🇰🇷 ➔ 🇺🇿" if mode == "kr_to_uz" else "🇺🇿 ➔ 🇰🇷"
        
        await callback.message.answer_document(
            document=file,
            caption=f"✅ 시험지가 준비되었습니다!\n\n"
                   f"📂 {location}\n"
                   f"🔄 {mode_text}\n"
                   f"📊 {len(words[:25])}개 단어"
        )
        
        # Kutish xabarini o'chirish
        await callback.message.delete()
        
        # Faylni serverdan o'chirish
        if os.path.exists(filepath):
            os.remove(filepath)
        
        await state.clear()
        
    except Exception as e:
        print(f"Exam file creation error: {e}")
        await callback.message.edit_text(
            f"❌ 오류가 발생했습니다.\n(Xatolik yuz berdi)\n\n"
            f"Iltimos qayta urinib ko'ring."
        )
        await state.clear()


# ============================================
# 4. ORQAGA QAYTISH (BO'LIMLAR RO'YXATIGA)
# ============================================

@router.callback_query(F.data == "exam_back_to_sections")
async def exam_back_to_sections(callback: CallbackQuery, state: FSMContext):
    """Bo'limlar ro'yxatiga qaytish"""
    user_id = callback.from_user.id
    await state.clear()
    
    # Bo'limlar ro'yxatini qayta ko'rsatish
    topics = dict_handler.get_all_topics(user_id)
    
    keyboard = []
    for topic in topics:
        sections = dict_handler.get_topic_sections(user_id, topic)
        for section in sections:
            section_map = {
                'reading': '읽기',
                'writing': '쓰기',
                'listening': '듣기'
            }
            section_korean = section_map.get(section, section)
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📚 {topic} › {section_korean}",
                    callback_data=f"exam_section:{topic}:{section}"
                )
            ])
    
    # Random exam tugmasi
    keyboard.append([
        InlineKeyboardButton(
            text="🎲 Tasodifiy (Random)",
            callback_data="exam_random_all"
        )
    ])
    
    await callback.message.edit_text(
        "📚 시험 섹션을 선택하세요:\n(Imtihon bo'limini tanlang:)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()


# ============================================
# 5. RANDOM EXAM (IXTIYORIY)
# ============================================

@router.callback_query(F.data == "exam_random_all")
async def exam_random_handler(callback: CallbackQuery, state: FSMContext):
    """Random exam - barcha so'zlardan tasodifiy"""
    user_id = callback.from_user.id
    await state.clear()
    
    # Barcha so'zlarni olish
    all_words_data = dict_handler.get_all_words(user_id)
    
    if not all_words_data:
        await callback.answer("❌ So'zlar topilmadi!", show_alert=True)
        return
    
    # Formatga solish
    all_words = [(w['korean'], w['uzbek']) for w in all_words_data]
    random.shuffle(all_words)
    
    # Yo'nalish so'rash (state ga saqlaymiz)
    await state.update_data(exam_random_words=all_words[:25])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🇰🇷 한국어 ➔ 🇺🇿 우즈베크어",
                callback_data="exam_random_mode:kr_to_uz"
            )
        ],
        [
            InlineKeyboardButton(
                text="🇺🇿 우즈베크어 ➔ 🇰🇷 한국어",
                callback_data="exam_random_mode:uz_to_kr"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Orqaga",
                callback_data="exam_back_to_sections"
            )
        ]
    ])
    
    await callback.message.edit_text(
        f"🎲 Tasodifiy imtihon\n\n"
        f"📊 {len(all_words[:25])}개 단어\n\n"
        f"🔄 형식을 선택하세요:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("exam_random_mode:"))
async def exam_random_mode_selected(callback: CallbackQuery, state: FSMContext):
    """Random exam yo'nalishi tanlandi"""
    mode = callback.data.split(":")[1]
    data = await state.get_data()
    words = data.get('exam_random_words', [])
    
    if not words:
        await callback.answer("❌ Xatolik!", show_alert=True)
        return
    
    await callback.message.edit_text("⏳ 파일을 준비 중입니다...")
    
    try:
        filepath = create_exam_word(words, location="Random", mode=mode)
        
        file = FSInputFile(filepath)
        mode_text = "🇰🇷 ➔ 🇺🇿" if mode == "kr_to_uz" else "🇺🇿 ➔ 🇰🇷"
        
        await callback.message.answer_document(
            document=file,
            caption=f"✅ 랜덤 시험!\n\n🔄 {mode_text}\n📊 {len(words)}개"
        )
        
        await callback.message.delete()
        
        if os.path.exists(filepath):
            os.remove(filepath)
        
        await state.clear()
        
    except Exception as e:
        print(f"Random exam error: {e}")
        await callback.message.edit_text("❌ Xatolik yuz berdi!")
        await state.clear()


# ============================================
# 6. AVTOMATIK EXAM YUBORISH (05:00)
# ============================================

def check_new_words_last_24h(user_id: int) -> bool:
    """Oxirgi 24 soatda yangi so'zlar qo'shilganmi?"""
    user_file = dict_handler.get_user_dict_file(user_id)
    
    if not os.path.exists(user_file):
        return False
    
    file_mtime = os.path.getmtime(user_file)
    time_diff = time_module.time() - file_mtime
    
    return time_diff <= 86400  # 24 soat


async def send_auto_exam():
    """Har kuni 05:00 da avtomatik exam yuborish"""
    # Barcha userlarni olish
    all_users = await user_db.get_all_users()
    
    for user in all_users:
        user_id = user['user_id']
        
        # Oxirgi 24 soatda yangi so'zlar bormi?
        if not check_new_words_last_24h(user_id):
            continue
        
        # Barcha so'zlarni olish
        all_words_data = dict_handler.get_all_words(user_id)
        
        if not all_words_data:
            continue
        
        # So'zlarni formatga solish
        all_words = [(w['korean'], w['uzbek']) for w in all_words_data]
        
        # Guruhga bo'lish (har birida 25 ta)
        groups = split_words_into_groups(all_words, EXAM_WORDS_PER_FILE)
        
        # Xabar (한국어)
        msg = "📚 시험 시간!\n\n"
        msg += f"✅ 새 단어: {len(all_words)}개\n"
        msg += f"📄 옵션: {len(groups)}개\n\n"
        
        try:
            await bot.send_message(user_id, msg)
            
            # Har bir guruhni fayl sifatida yuborish
            for idx, group in enumerate(groups, 1):
                # Default mode: kr_to_uz
                filepath = create_exam_word(group, location=None, mode="kr_to_uz")
                
                file = FSInputFile(filepath)
                await bot.send_document(
                    user_id,
                    document=file,
                    caption=f"📝 옵션 {idx}: {len(group)}개 단어"
                )
                
                os.remove(filepath)
        
        except Exception as e:
            print(f"Error sending exam to {user_id}: {e}")


def schedule_exam_checker():
    """Soat 05:00 da tekshiruvchi"""
    import schedule
    
    schedule.every().day.at(EXAM_AUTO_TIME).do(
        lambda: asyncio.create_task(send_auto_exam())
    )
    
    while True:
        schedule.run_pending()
        time_module.sleep(60)




# ==================== MAIN ====================

async def main():
    await user_db.init_db()
    dp.include_router(router)
    
    # Avtomatik so'z yuborish
    asyncio.create_task(send_auto_words())
    
    print("✅ Bot ishga tushdi!")
    print("⏰ Avtomatik so'z yuborish faollashtirildi")
    print("📝 Exam tizimi faollashtirildi (har kuni 05:00)")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())