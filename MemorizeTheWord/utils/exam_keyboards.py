# -*- coding: utf-8 -*-
"""
EXAM KLAVIATURALAR
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_exam_main_keyboard() -> InlineKeyboardMarkup:
    """Exam asosiy menyu (한국어)"""
    keyboard = [
        [InlineKeyboardButton(text="🎯 지정", callback_data="exam_select")],
        [InlineKeyboardButton(text="🔀 랜덤", callback_data="exam_random")]
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