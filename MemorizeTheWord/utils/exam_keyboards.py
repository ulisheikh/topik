# -*- coding: utf-8 -*-
"""
EXAM KLAVIATURALAR - TOZALANGAN (RANDOMSIZ)
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_exam_main_keyboard() -> InlineKeyboardMarkup:
    """Exam asosiy menyu (한국어) - TASODIFIY (RANDOM) TUGMASI OLIB TASHLANDI"""
    keyboard = [
        [InlineKeyboardButton(text="🎯 지정 (Bo'lim tanlash)", callback_data="exam_select")],
        [InlineKeyboardButton(text="⭐ 별표 단어 (Yulduzli so'zlar)", callback_data="exam_star")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_exam_star_direction_keyboard() -> InlineKeyboardMarkup:
    """Yulduzli so'zlar yo'nalishi"""
    keyboard = [
        [InlineKeyboardButton(text="🇺🇿 Uz → 🇰🇷 Ko", callback_data="exam_star_uz_ko")],
        [InlineKeyboardButton(text="🇰🇷 Ko → 🇺🇿 Uz", callback_data="exam_star_ko_uz")],
        [InlineKeyboardButton(text="🇰🇷 + 🇺🇿 Tarjima bilan (ikki tilda)", callback_data="exam_star_both")],
        [InlineKeyboardButton(text="🔙 뒤로", callback_data="exam_back_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_exam_topics_keyboard(topics: list) -> InlineKeyboardMarkup:
    """Topiklar (한국어)"""
    keyboard = []
    for topic in topics:
        topic_num = topic.replace('-topik', '')
        keyboard.append([
            InlineKeyboardButton(
                text=f"📚 {topic_num}-주제",
                callback_data=f"exam_topic_{topic_num}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(text="🔙 뒤로", callback_data="exam_back_main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_exam_sections_keyboard(topic_num: str) -> InlineKeyboardMarkup:
    """Bo'limlar (한국어)"""
    keyboard = [
        [InlineKeyboardButton(text="📖 읽기", callback_data=f"exam_sec_{topic_num}_reading")],
        [InlineKeyboardButton(text="✍️ 쓰기", callback_data=f"exam_sec_{topic_num}_writing")],
        [InlineKeyboardButton(text="🎧 듣기", callback_data=f"exam_sec_{topic_num}_listening")],
        [InlineKeyboardButton(text="🔙 뒤로", callback_data="exam_select")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)