# -*- coding: utf-8 -*-
"""
INLINE KEYBOARDS - YANGI DIZAYN
10x5 format, ➕ADD, 🗑 So'z o'chirish
"""

from telebot.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)

from utils.language import get_user_language, get_text

# ============================================
# ASOSIY REPLY KLAVIATURA
# ============================================

def get_main_keyboard(uid):
    """Asosiy klaviatura - /help bilan"""
    lang = get_user_language(uid)
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    
    # 1-qator: /start
    markup.add(KeyboardButton("/start"))
    
    # 2-qator: BO'LIMLAR
    if lang == 'uz':
        markup.add(KeyboardButton("📂 BO'LIMLAR"))
    else:
        markup.add(KeyboardButton("📂 섹션"))
    
    # 3-qator: JSON | PYTHON
    markup.row(
        KeyboardButton("📥 JSON"),
        KeyboardButton("🐍 PYTHON")
    )
    
    # 4-qator: SOZLAMALAR
    if lang == 'uz':
        markup.add(KeyboardButton("⚙️ SOZLAMALAR"))
    else:
        markup.add(KeyboardButton("⚙️ 설정"))
    
    # 5-qator: /help (ALOHIDA!)
    markup.add(KeyboardButton("/help"))
    
    return markup

# ============================================
# TOPIKLAR INLINE (4 ustun)
# ============================================

def get_topics_inline(topics_list, uid):
    """
    Topiklar ro'yxati inline
    topics_list = [35, 36, 37, ...]
    4 ustunda
    """
    markup = InlineKeyboardMarkup(row_width=4)
    
    buttons = []
    for topic_num in sorted(topics_list):
        btn = InlineKeyboardButton(
            text=f"📖 {topic_num}",
            callback_data=f"topic_{topic_num}"
        )
        buttons.append(btn)
    
    # 4 tadan qo'shish
    for i in range(0, len(buttons), 4):
        markup.row(*buttons[i:i+4])
    
    # ADD va DELETE tugmalari
    add_btn = InlineKeyboardButton(
        text="➕ ADD",
        callback_data="add_topic"
    )
    delete_btn = InlineKeyboardButton(
        text="🗑️ DELETE",
        callback_data="delete_topic"
    )
    markup.row(add_btn, delete_btn)
    
    return markup

# ============================================
# BO'LIMLAR (Reading, Writing, Listening)
# ============================================

def get_sections_inline(topic_num, uid):
    """
    Topik ichidagi bo'limlar
    topic_num = 35
    """
    lang = get_user_language(uid)
    markup = InlineKeyboardMarkup(row_width=1)
    
    if lang == 'uz':
        sections = [
            ('📖 Reading', f'section_{topic_num}_r'),
            ('✍️ Writing', f'section_{topic_num}_w'),
            ('🎧 Listening', f'section_{topic_num}_l')
        ]
        back_text = '◀️ Ortga'
    else:
        sections = [
            ('📖 읽기', f'section_{topic_num}_r'),
            ('✍️ 쓰기', f'section_{topic_num}_w'),
            ('🎧 듣기', f'section_{topic_num}_l')
        ]
        back_text = '◀️ 뒤로'
    
    for text, callback in sections:
        markup.add(InlineKeyboardButton(text=text, callback_data=callback))
    
    # Ortga tugmasi
    markup.add(InlineKeyboardButton(text=back_text, callback_data='back_topics'))
    
    return markup

# ============================================
# SAVOLLAR INLINE
# ============================================

def get_questions_inline(topic_num, section_type, uid, questions_data=None):
    """
    Savollar ro'yxati
    topic_num = 35
    section_type = 'r' (reading), 'w' (writing), 'l' (listening)
    questions_data = {1: 5, 9: 1, 50: 30, ...} (savol: so'zlar_soni)
    
    Reading/Listening: 1-50 (7 ustun)
    Writing: 51-54
    """
    lang = get_user_language(uid)
    markup = InlineKeyboardMarkup()
    
    if section_type == 'w':
        # Writing: faqat 51, 52, 53, 54
        questions = [51, 52, 53, 54]
        row_width = 4
        
        buttons = []
        for q_num in questions:
            # So'zlar sonini olish
            word_count = 0
            if questions_data and q_num in questions_data:
                word_count = questions_data[q_num]
            
            btn = InlineKeyboardButton(
                text=f"{q_num}-{word_count}",
                callback_data=f"question_{topic_num}_{section_type}_{q_num}"
            )
            buttons.append(btn)
        
        markup.row(*buttons)
    
    else:
        # Reading/Listening: 1-50 (7 ustun)
        questions = list(range(1, 51))  # 1-50
        row_width = 7
        
        buttons = []
        for q_num in questions:
            # So'zlar sonini olish
            word_count = 0
            if questions_data and q_num in questions_data:
                word_count = questions_data[q_num]
            
            btn = InlineKeyboardButton(
                text=f"{q_num}-{word_count}",
                callback_data=f"question_{topic_num}_{section_type}_{q_num}"
            )
            buttons.append(btn)
        
        # 7 tadan qo'shish
        for i in range(0, len(buttons), 7):
            markup.row(*buttons[i:i+7])
    
    # Ortga tugmasi
    back_text = '◀️ Ortga' if lang == 'uz' else '◀️ 뒤로'
    markup.add(InlineKeyboardButton(
        text=back_text, 
        callback_data=f'back_sections_{topic_num}'
    ))
    
    return markup

# ============================================
# SAVOL ICHIDAGI TUGMALAR
# ============================================

def get_question_actions_inline(topic_num, section_type, question_num, has_words, uid):
    """
    Savol ichida: So'z qo'shish, O'chirish, Ortga
    has_words = True/False (so'zlar bormi)
    """
    lang = get_user_language(uid)
    markup = InlineKeyboardMarkup(row_width=1)
    
    # ➕ So'z qo'shish
    if lang == 'uz':
        add_text = '➕ So\'z qo\'shish'
        remove_text = '🗑 So\'z o\'chirish'
        back_text = '◀️ Ortga'
    else:
        add_text = '➕ 단어 추가'
        remove_text = '🗑 단어 삭제'
        back_text = '◀️ 뒤로'
    
    markup.add(InlineKeyboardButton(
        text=add_text,
        callback_data=f"add_word_{topic_num}_{section_type}_{question_num}"
    ))
    
    # 🗑 So'z o'chirish (faqat so'zlar bo'lsa)
    if has_words:
        markup.add(InlineKeyboardButton(
            text=remove_text,
            callback_data=f"remove_word_{topic_num}_{section_type}_{question_num}"
        ))
    
    # ◀️ Ortga
    markup.add(InlineKeyboardButton(
        text=back_text,
        callback_data=f"back_questions_{topic_num}_{section_type}"
    ))
    
    return markup

# ============================================
# SOZLAMALAR KLAVIATURASI
# ============================================

def get_settings_keyboard(uid, is_admin=False):
    """Sozlamalar klaviaturasi"""
    lang = get_user_language(uid)
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    if lang == 'uz':
        btn1 = KeyboardButton('🌐 TIL')
        btn2 = KeyboardButton('📥 JSON')
        btn3 = KeyboardButton('🐍 PYTHON')
        btn4 = KeyboardButton('🔙 ORQAGA')
    else:
        btn1 = KeyboardButton('🌐 언어')
        btn2 = KeyboardButton('📥 JSON')
        btn3 = KeyboardButton('🐍 PYTHON')
        btn4 = KeyboardButton('🔙 뒤로')
    
    markup.row(btn1, btn2)
    markup.row(btn3, btn4)
    
    return markup

# ============================================
# ADMIN KLAVIATURALAR (eski, o'zgarmaydi)
# ============================================

def get_admin_keyboard(uid):
    """Admin klaviaturasi"""
    lang = get_user_language(uid)
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    if lang == 'uz':
        btn1 = KeyboardButton('📂 BO\'LIMLAR')
        btn2 = KeyboardButton('⚙️ SOZLAMALAR')
        btn3 = KeyboardButton('👥 FOYDALANUVCHILAR')
        btn4 = KeyboardButton('📊 MONITORING')
    else:
        btn1 = KeyboardButton('📂 섹션')
        btn2 = KeyboardButton('⚙️ 설정')
        btn3 = KeyboardButton('👥 사용자')
        btn4 = KeyboardButton('📊 모니터링')
    
    markup.row(btn1, btn2)
    markup.row(btn3, btn4)
    
    return markup