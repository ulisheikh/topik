# -*- coding: utf-8 -*-
"""
KOREAN-O'ZBEK LUG'AT BOT
Yangilangan versiya - 2.0
User-based tizim
"""

import telebot
import os
import re
import threading
import time
from datetime import datetime

# IMPORT CONFIG
from config import *

# IMPORT UTILS
from utils.auth import *
from utils.data_handler import *
from utils.language import *
from utils.inline_keyboards import *

# IMPORT ADMIN
from admin.monitoring import *
from admin.user_manager import *

from telebot import types
from utils.inline_keyboards import (
    get_topics_inline,
    get_sections_inline,
    get_questions_inline,
    get_question_actions_inline
)

# BOT YARATISH
bot = telebot.TeleBot(TOKEN)

# USER CONTEXT
user_context = {}

# ============================================
# YORDAMCHI FUNKSIYALAR
# ============================================

def get_help_text(user_id):
    """Yordam matni"""
    lang = get_user_language(user_id)
    
    header = f"<b>{get_text(user_id, 'help_title')}</b>\n"
    header += "<b>─────────────────────</b>\n\n"
    
    body = f"<b>{get_text(user_id, 'help_create')}</b>\n\n"
    body += f"<b>{get_text(user_id, 'help_add_word')}</b>\n\n"
    body += f"<b>{get_text(user_id, 'help_delete')}</b>\n\n"
    body += f"<b>{get_text(user_id, 'help_restore')}</b>\n\n"
    body += f"<b>{get_text(user_id, 'help_search')}</b>\n\n"
    body += f"<b>{get_text(user_id, 'help_system')}</b>\n"
    body += "<b>━━━━━━━━━━━━━━━━━</b>\n"
    body += f"<i>{get_text(user_id, 'help_tip')}</i>"
    
    return header + body

def get_location_text(user_id):
    """Hozirgi joying"""
    if user_id not in user_context:
        return "❌ Hozir hech qayerda emasmiz"
    
    ctx = user_context[user_id]
    location = []
    
    if ctx.get("topic"):
        topic_num = ctx["topic"].replace("Topik-", "")
        location.append(f"{topic_num}-topik")
    
    if ctx.get("section"):
        location.append(ctx["section"])
    
    if ctx.get("question"):
        q_info = ctx["question"].replace("-savol so'zlari", "")
        location.append(f"{q_info}-savol")
    
    if not location:
        return "❌ Hozir hech qayerda emasmiz"
    
    return "📍 " + " > ".join(location)

# ============================================
# START VA AUTENTIFIKATSIYA
# ============================================
"""
DictionaryBot main.py - START HANDLER qismi
"""

from admin.user_manager import save_user_info

@bot.message_handler(commands=['start'])
def start_handler(message):
    uid = message.from_user.id
    
    # 1. User ma'lumotlarini saqlash
    save_user_info(
        uid, 
        message.from_user.first_name, 
        message.from_user.last_name, 
        message.from_user.username
    )
    
    # 2. Bloklanganlikni tekshirish
    if is_user_blocked(uid):
        bot.send_message(uid, get_text(uid, 'password_blocked'))
        return

    # 3. Login tekshirish
    if not is_logged_in(uid):
        bot.send_message(uid, get_text(uid, 'enter_password'), parse_mode="HTML")
        bot.register_next_step_handler(message, password_handler)
        return
    
    # 4. Welcome xabari
    bot.send_message(
        uid, 
        get_text(uid, 'welcome'), 
        parse_mode="HTML", 
        reply_markup=get_main_keyboard(uid)
    )
    
    # 5. Statistika (help o'rniga)
    from admin.user_manager import get_all_users
    
    # Topiklar soni
    data = load_user_data(uid)
    topics_count = len([k for k in data.keys() if k.startswith('Topik-')])
    
    # So'zlar soni
    words_count = get_user_words_count(uid)
    
    # Barcha foydalanuvchilar
    all_users = get_all_users()
    users_count = len(all_users)
    
    stats_msg = get_text(uid, 'home_stats').format(
        users=users_count,
        topics=topics_count,
        words=words_count
        
    )
    
    bot.send_message(uid, stats_msg, parse_mode="HTML")

def password_handler(message):
    """Parol tekshirish"""
    uid = message.from_user.id
    password = message.text.strip()
    
    # Bloklangan userlarni tekshirish
    if is_user_blocked(uid):
        bot.send_message(uid, get_text(uid, 'password_blocked'))
        return
    
    # Parolni tekshirish
    role = verify_password(uid, password)
    
    if role:
        # Login qilish
        login_user(uid, role)
        
        bot.send_message(
            uid,
            get_text(uid, 'password_correct'),
            reply_markup=get_main_keyboard(uid)
        )
        
        bot.send_message(
            uid,
            get_help_text(uid),
            parse_mode="HTML"
        )
    else:
        # Noto'g'ri parol
        blocked = add_login_attempt(uid)
        
        if blocked:
            bot.send_message(uid, get_text(uid, 'password_blocked'))
        else:
            bot.send_message(uid, get_text(uid, 'password_wrong'))
            bot.register_next_step_handler(message, password_handler)

# ============================================
# SOZLAMALAR
# ============================================

# ============================================
# BO'LIMLAR - YANGI INLINE VERSIYA
# ============================================

@bot.message_handler(func=lambda m: m.text in ['📂 BO\'LIMLAR', '📂 섹션'])
def sections_handler(message):
    """BO'LIMLAR bosilsa -> Topiklar inline chiqadi"""
    uid = message.from_user.id
    
    if not is_logged_in(uid):
        bot.send_message(uid, get_text(uid, 'enter_password'))
        return
    
    data = load_user_data(uid)
    
    if not data:
        bot.send_message(uid, get_text(uid, 'no_topics'))
        return
    
    # Topiklar ro'yxati
    topics = []
    for topic_key in data.keys():
        if topic_key.startswith("Topik-"):
            topic_num = topic_key.replace("Topik-", "")
            if topic_num.isdigit():
                topics.append(int(topic_num))
    
    if not topics:
        bot.send_message(uid, get_text(uid, 'no_topics'))
        return
    
    # Inline klaviatura
    markup = get_topics_inline(topics, uid)
    
    msg = get_text(uid, 'topics_title') + '\n\n'
    msg += get_text(uid, 'topics_count').format(len(topics)) + '\n\n'
    msg += get_text(uid, 'select_topic_inline')
    
    bot.send_message(uid, msg, reply_markup=markup)


@bot.message_handler(func=lambda m: m.text in ['⚙️ SOZLAMALAR', '⚙️ 설정'])
def settings_handler(message):
    """Sozlamalar menyusi - INLINE"""
    uid = message.from_user.id
    
    if not is_logged_in(uid):
        bot.send_message(uid, get_text(uid, 'enter_password'))
        return
    
    lang = get_user_language(uid)
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if lang == 'uz':
        markup.add(types.InlineKeyboardButton('👥 users', callback_data='settings_users'))
        markup.add(types.InlineKeyboardButton('🌐 language', callback_data='settings_language'))
        markup.add(types.InlineKeyboardButton('🔐 password', callback_data='settings_password'))
        markup.add(types.InlineKeyboardButton('ℹ️ about', callback_data='settings_about'))
        markup.add(types.InlineKeyboardButton('🔙 back', callback_data='settings_back'))
    else:
        markup.add(types.InlineKeyboardButton('👥 사용자', callback_data='settings_users'))
        markup.add(types.InlineKeyboardButton('🌐 언어', callback_data='settings_language'))
        markup.add(types.InlineKeyboardButton('🔐 비밀번호', callback_data='settings_password'))
        markup.add(types.InlineKeyboardButton('ℹ️ 정보', callback_data='settings_about'))
        markup.add(types.InlineKeyboardButton('🔙 뒤로', callback_data='settings_back'))
    
    bot.send_message(
        uid,
        get_text(uid, 'settings_menu'),
        reply_markup=markup
    )

# ============================================
# BO'LIMLAR
# ============================================


# ============================================
# EXPORT (JSON VA PYTHON)
# ============================================

@bot.message_handler(func=lambda m: m.text in ['📥 JSON', '📥 JSON'])
def export_json_handler(message):
    """JSON export"""
    uid = message.from_user.id
    
    if not is_logged_in(uid):
        bot.send_message(uid, get_text(uid, 'enter_password'))
        return
    
    user_file = get_user_file(uid)
    
    if os.path.exists(user_file):
        with open(user_file, 'rb') as f:
            bot.send_document(
                uid,
                f,
                caption=get_text(uid, 'export_json_caption')
            )
    else:
        bot.send_message(uid, get_text(uid, 'export_empty'))

@bot.message_handler(func=lambda m: m.text in ['🐍 PYTHON', '🐍 PYTHON'])
def export_python_handler(message):
    """Python export"""
    uid = message.from_user.id
    
    if not is_logged_in(uid):
        bot.send_message(uid, get_text(uid, 'enter_password'))
        return
        
    data = load_user_data(uid)
    if not data:
        bot.send_message(uid, get_text(uid, 'export_empty'))
        return
        
    py_code = json_to_python(uid)
    py_file = f"dictionary_{uid}.py"
    
    with open(py_file, 'w', encoding='utf-8') as f:
        f.write(py_code)
    
    # Mana shu joyda kod ulandi
    with open(py_file, 'rb') as f:
        bot.send_document(
            uid,
            f,
            caption=get_text(uid, 'export_python_caption')
        )

    try:
        os.remove(py_file)
    except:
        pass

# ============================================
# CALLBACK HANDLER
# ============================================

from admin.user_manager import (
    get_all_users, 
    format_users_list, 
    get_user_details,
    format_user_details
)

# ============================================
# CALLBACK HANDLERS
# ============================================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Barcha inline tugmalar uchun"""
    uid = call.from_user.id
    data_str = call.data
    
    # ============================================
    # TOPIK TANLASH: topic_35
    # ============================================
    if data_str.startswith('topic_'):
        topic_num = data_str.replace('topic_', '')
        
        # Bo'limlar inline
        markup = get_sections_inline(topic_num, uid)
        
        msg = get_text(uid, 'topic_header').format(topic_num) + '\n\n'
        msg += get_text(uid, 'select_section_inline')
        
        bot.edit_message_text(
            msg,
            uid,
            call.message.id,
            reply_markup=markup
        )
    
    # ============================================
    # BO'LIM TANLASH: section_35_r (SO'ZLAR SONI BILAN)
    # ============================================
    elif data_str.startswith('section_'):
        parts = data_str.split('_')  # ['section', '35', 'r']
        topic_num = parts[1]
        section_type = parts[2]  # r/w/l
        
        # Savol turi nomi
        section_names = {
            'r': 'READING',
            'w': 'WRITING',
            'l': 'LISTENING'
        }
        section_name = section_names[section_type]
        
        # Ma'lumotlarni yuklash
        data = load_user_data(uid)
        topic_key = f'Topik-{topic_num}'
        
        # Bo'lim nomi
        section_map = {
            'r': 'reading',
            'w': 'writing',
            'l': 'listening'
        }
        section = section_map[section_type]
        
        # So'zlar sonini hisoblash har bir savol uchun
        questions_data = {}
        
        if topic_key in data and section in data[topic_key]:
            questions = data[topic_key][section]
            
            # Savol raqamlarini aniqlash
            if section_type == 'w':
                question_range = range(51, 55)  # 51-54
            else:
                question_range = range(1, 51)   # 1-50
            
            for q_num in question_range:
                q_key = f"{q_num}-savol so'zlari"
                if q_key in questions:
                    questions_data[q_num] = len(questions[q_key])
                else:
                    questions_data[q_num] = 0
        
        # Savollar inline - so'zlar soni bilan
        markup = get_questions_inline(topic_num, section_type, uid, questions_data)
        
        # Statistika
        total_questions = len([q for q in questions_data.values() if q > 0])
        total_words = sum(questions_data.values())
        
        msg = f"📖 <b>{topic_num}-TOPIK > {section_name}</b>\n"
        msg += "━━━━━━━━━━━━━━━━━\n\n"
        msg += f"📊 So'zli savollar: {total_questions} ta\n"
        msg += f"📚 Jami so'zlar: {total_words} ta\n\n"
        msg += get_text(uid, 'select_question')
        
        bot.edit_message_text(
            msg,
            uid,
            call.message.id,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    # ============================================
    # SAVOL TANLASH: question_35_r_13
    # ============================================
    elif data_str.startswith('question_'):
        parts = data_str.split('_')  # ['question', '35', 'r', '13']
        topic_num = parts[1]
        section_type = parts[2]
        question_num = parts[3]
        
        # Ma'lumotlarni yuklash
        data = load_user_data(uid)
        topic_key = f'Topik-{topic_num}'
        
        # Bo'lim nomi
        section_map = {
            'r': 'reading',
            'w': 'writing',
            'l': 'listening'
        }
        section_name = section_map[section_type]
        
        # Savol kaliti
        question_key = f'{question_num}-savol so\'zlari'
        
        # So'zlarni olish
        words = {}
        if topic_key in data:
            if section_name in data[topic_key]:
                if question_key in data[topic_key][section_name]:
                    words = data[topic_key][section_name][question_key]
        
        # Xabar tayyorlash
        section_display = {
            'r': 'Reading',
            'w': 'Writing',
            'l': 'Listening'
        }
        
        msg = get_text(uid, 'question_location').format(
            topic_num, 
            section_display[section_type], 
            question_num
        ) + '\n\n'
        
        if words:
            msg += get_text(uid, 'words_title') + '\n'
            for idx, (kr, uz) in enumerate(words.items(), 1):
                msg += f'{idx}. {kr} → {uz}\n'
            msg += '\n' + get_text(uid, 'words_count').format(len(words))
        else:
            msg += get_text(uid, 'words_empty')
        
        # Inline tugmalar
        markup = get_question_actions_inline(
            topic_num, 
            section_type, 
            question_num, 
            bool(words), 
            uid
        )
        
        bot.edit_message_text(
            msg,
            uid,
            call.message.id,
            reply_markup=markup
        )
    
    # ============================================
    # SO'Z QO'SHISH: add_word_35_r_13
    # ============================================
    elif data_str.startswith('add_word_'):
        parts = data_str.split('_')  # ['add', 'word', '35', 'r', '13']
        topic_num = parts[2]
        section_type = parts[3]
        question_num = parts[4]
        
        section_display = {
            'r': 'Reading',
            'w': 'Writing',
            'l': 'Listening'
        }
        
        msg = get_text(uid, 'enter_words').format(
            topic_num,
            section_display[section_type],
            question_num
        )
        
        bot.send_message(uid, msg, parse_mode='HTML')
        
        # Context saqlash
        user_context[uid] = {
            'action': 'add_word',
            'topic': topic_num,
            'section': section_type,
            'question': question_num
        }
        
        bot.answer_callback_query(call.id)
    
    # ============================================
    # SO'Z O'CHIRISH: remove_word_35_r_13
    # ============================================
    elif data_str.startswith('remove_word_'):
        parts = data_str.split('_')  # ['remove', 'word', '35', 'r', '13']
        topic_num = parts[2]
        section_type = parts[3]
        question_num = parts[4]
        
        section_display = {
            'r': 'Reading',
            'w': 'Writing',
            'l': 'Listening'
        }
        
        msg = get_text(uid, 'enter_word_to_remove').format(
            topic_num,
            section_display[section_type],
            question_num
        )
        
        bot.send_message(uid, msg)
        
        # Context saqlash
        user_context[uid] = {
            'action': 'remove_word',
            'topic': topic_num,
            'section': section_type,
            'question': question_num
        }
        
        bot.answer_callback_query(call.id)
    
    # ============================================
    # YANGI TOPIK QO'SHISH: add_topic
    # ============================================
    elif data_str == 'add_topic':
        msg = get_text(uid, 'enter_topic_number')
        bot.send_message(uid, msg)
        
        user_context[uid] = {
            'action': 'create_topic'
        }
        
        bot.answer_callback_query(call.id)
    
    # ============================================
    # TOPIKNI O'CHIRISH: delete_topic
    # ============================================
    elif data_str == 'delete_topic':
        msg = "🗑️ <b>TOPIKNI O'CHIRISH</b>\n\n"
        msg += "Qaysi topikni o'chirmoqchisiz?\n\n"
        msg += "Topik raqamini kiriting:\n"
        msg += "Masalan: <code>45</code>"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            text="◀️ Bekor qilish",
            callback_data="back_topics"
        ))
        
        bot.edit_message_text(
            msg,
            uid,
            call.message.id,
            parse_mode="HTML",
            reply_markup=markup
        )
        
        # State saqlash
        user_context[uid] = {
            'action': 'deleting_topic',
            'message_id': call.message.id
        }
        
        bot.answer_callback_query(call.id)
    
    # ============================================
    # TOPIK O'CHIRISHNI TASDIQLASH: confirm_delete_45
    # ============================================
    elif data_str.startswith('confirm_delete_'):
        topic_num = int(data_str.replace('confirm_delete_', ''))
        topic_key = f"Topik-{topic_num}"
        
        # Ma'lumotlarni yuklash
        data = load_user_data(uid)
        
        if topic_key not in data:
            bot.answer_callback_query(call.id, "❌ Topik topilmadi!")
            return
        
        # Backup yaratish
        backup_data = {
            'type': 'topic',
            'topic': topic_key,
            'content': data[topic_key]
        }
        create_backup(uid, 'topic', backup_data, f"{topic_num}")
        
        # O'chirish
        del data[topic_key]
        save_user_data(uid, data)
        
        # Xabar
        msg = f"✅ <b>{topic_num}-topik o'chirildi!</b>\n\n"
        msg += "🔄 Tiklash uchun:\n"
        msg += f"<code>rs.{topic_num}</code>"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            text="◀️ Topiklar ro'yxatiga qaytish",
            callback_data="back_topics"
        ))
        
        bot.edit_message_text(
            msg,
            uid,
            call.message.id,
            parse_mode="HTML",
            reply_markup=markup
        )
        
        bot.answer_callback_query(call.id, "✅ O'chirildi!")
    
    # ============================================
    # ORTGA TUGMALARI
    # ============================================
    
    # Topiklarqa qaytish
    elif data_str == 'back_topics':
        data = load_user_data(uid)
        topics = []
        for topic_key in data.keys():
            if topic_key.startswith("Topik-"):
                topic_num = topic_key.replace("Topik-", "")
                if topic_num.isdigit():
                    topics.append(int(topic_num))
        
        markup = get_topics_inline(topics, uid)
        
        msg = get_text(uid, 'topics_title') + '\n\n'
        msg += get_text(uid, 'topics_count').format(len(topics)) + '\n\n'
        msg += get_text(uid, 'select_topic_inline')
        
        bot.edit_message_text(
            msg,
            uid,
            call.message.id,
            reply_markup=markup
        )
    
    # Bo'limlarga qaytish
    elif data_str.startswith('back_sections_'):
        topic_num = data_str.replace('back_sections_', '')
        
        markup = get_sections_inline(topic_num, uid)
        
        msg = get_text(uid, 'topic_header').format(topic_num) + '\n\n'
        msg += get_text(uid, 'select_section_inline')
        
        bot.edit_message_text(
            msg,
            uid,
            call.message.id,
            reply_markup=markup
        )
    
    # Savollarga qaytish
    elif data_str.startswith('back_questions_'):
        parts = data_str.replace('back_questions_', '').split('_')
        topic_num = parts[0]
        section_type = parts[1]
        
        # Context tozalash (savol sahifasidan chiqayotganda)
        if uid in user_context:
            del user_context[uid]
        
        section_names = {
            'r': 'reading',
            'w': 'writing',
            'l': 'listening'
        }
        
        markup = get_questions_inline(topic_num, section_type, uid)
        
        msg = get_text(uid, f'questions_header_{section_names[section_type]}').format(topic_num) + '\n\n'
        msg += get_text(uid, 'select_question')
        
        bot.edit_message_text(
            msg,
            uid,
            call.message.id,
            reply_markup=markup
        )
    
    # ============================================
    # SOZLAMALAR CALLBACKS
    # ============================================
    elif data_str == 'settings_language':
        lang = get_user_language(uid)
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        markup.add(
            types.InlineKeyboardButton('🇺🇿 O\'zbek', callback_data='set_lang_uz'),
            types.InlineKeyboardButton('🇰🇷 한국어', callback_data='set_lang_ko')
        )
        markup.add(types.InlineKeyboardButton('◀️ Ortga' if lang == 'uz' else '◀️ 뒤로', callback_data='settings_back'))
        
        bot.edit_message_text(
            get_text(uid, 'select_language'),
            uid,
            call.message.id,
            reply_markup=markup
        )
    
    elif data_str.startswith('set_lang_'):
        new_lang = data_str.replace('set_lang_', '')
        set_user_language(uid, new_lang)
        
        bot.answer_callback_query(call.id, get_text(uid, 'language_changed'))
        
        # Sozlamalarga qaytish
        lang = get_user_language(uid)
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        if lang == 'uz':
            markup.add(types.InlineKeyboardButton('👥 users', callback_data='settings_users'))
            markup.add(types.InlineKeyboardButton('🌐 language', callback_data='settings_language'))
            markup.add(types.InlineKeyboardButton('🔐 password', callback_data='settings_password'))
            markup.add(types.InlineKeyboardButton('ℹ️ about', callback_data='settings_about'))
            markup.add(types.InlineKeyboardButton('🔙 back', callback_data='settings_back'))
        else:
            markup.add(types.InlineKeyboardButton('👥 사용자', callback_data='settings_users'))
            markup.add(types.InlineKeyboardButton('🌐 언어', callback_data='settings_language'))
            markup.add(types.InlineKeyboardButton('🔐 비밀번호', callback_data='settings_password'))
            markup.add(types.InlineKeyboardButton('ℹ️ 정보', callback_data='settings_about'))
            markup.add(types.InlineKeyboardButton('🔙 뒤로', callback_data='settings_back'))
        
        bot.edit_message_text(
            get_text(uid, 'settings_menu'),
            uid,
            call.message.id,
            reply_markup=markup
        )
    
    elif data_str == 'settings_about':
        lang = get_user_language(uid)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('◀️ Ortga' if lang == 'uz' else '◀️ 뒤로', callback_data='settings_back'))
        
        bot.edit_message_text(
            get_text(uid, 'about_bot'),
            uid,
            call.message.id,
            reply_markup=markup
        )
    
    elif data_str == 'settings_password':
        lang = get_user_language(uid)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('◀️ Ortga' if lang == 'uz' else '◀️ 뒤로', callback_data='settings_back'))
        
        msg = "🔐 Parolni o'zgartirish:\n\n/newpass_user YANGI_PAROL\n/newpass_admin YANGI_PAROL" if lang == 'uz' else "🔐 비밀번호 변경:\n\n/newpass_user NEW_PASSWORD\n/newpass_admin NEW_PASSWORD"
        
        bot.edit_message_text(
            msg,
            uid,
            call.message.id,
            reply_markup=markup
        )
    
    elif data_str == 'settings_users':
        if not is_admin(uid):
            bot.answer_callback_query(call.id, "❌ Admin emas!")
            return
        
        users = get_all_users()
        lang = get_user_language(uid)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('◀️ Ortga' if lang == 'uz' else '◀️ 뒤로', callback_data='settings_back'))
        
        msg = format_users_list(uid, users)
        
        bot.edit_message_text(
            msg,
            uid,
            call.message.id,
            parse_mode='HTML',
            reply_markup=markup
        )
    
    elif data_str == 'settings_back':
        # Xabarni o'chirish
        try:
            bot.delete_message(uid, call.message.id)
        except:
            pass
        
        bot.answer_callback_query(call.id)
        return
    
    bot.answer_callback_query(call.id)
# ============================================
# /STATUS KOMANDASI
# ============================================

@bot.message_handler(commands=['status'])
def status_command_handler(message):
    uid = message.from_user.id
    
    # 1. Login tekshirish
    if not is_logged_in(uid):
        bot.send_message(uid, get_text(uid, 'enter_password'))
        return
    
    # 2. Admin tekshirish
    if not is_admin(uid):
        bot.send_message(uid, "❌ Bu buyruq faqat admin uchun!")
        return
    
    # 3. Status yuborish
    try:
        stats = get_system_stats()
        status_text = format_system_status(uid, stats)
        bot.send_message(
            uid, 
            f"📊 <b>Tizim holati:</b>\n\n{status_text}", 
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"❌ Status xatolik: {e}")
        bot.send_message(uid, f"❌ Xatolik: {e}")

# ============================================
# PAROL O'ZGARTIRISH BUYRUQLARI
# ============================================
@bot.message_handler(commands=['newpass_user', 'newpass_admin'])
def change_password_handlers(message):
    uid = message.from_user.id
    text = message.text
    
    if not is_logged_in(uid):
        bot.reply_to(message, "⚠️ Avval botga kiring!")
        return

    parts = text.split()
    if len(parts) < 2:
        cmd = parts[0]
        bot.reply_to(message, f"⚠️ Xato! Parolni ham yozing.\nMisol: `{cmd} 8888`", parse_mode="Markdown")
        return

    new_pwd = parts[1]
    
    # Qaysi parolni o'zgartirishni aniqlaymiz
    role = 'user' if 'newpass_user' in text else 'admin'
    
    # FAYLGA SAQLASH (Tepada yozgan funksiyamiz)
    if update_password(role, new_pwd):
        bot.reply_to(message, f"✅ {role.capitalize()} paroli muvaffaqiyatli o'zgartirildi: `{new_pwd}`", parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ Xatolik yuz berdi. passwords.json faylini tekshiring.")
# ============================================
# TEXT MESSAGE HANDLER (Context asosida)
# ============================================

@bot.message_handler(func=lambda m: True, content_types=['text'])
def text_handler(message):
    """Barcha text xabarlar uchun"""
    uid = message.from_user.id
    text = message.text.strip()
    
    # Context borligini tekshirish
    if uid not in user_context:
        return
    
    ctx = user_context[uid]
    action = ctx.get('action')
    
    # ============================================
    # YANGI TOPIK YARATISH
    # ============================================
    if action == 'create_topic':
        # Raqam tekshirish
        if not text.isdigit():
            bot.send_message(uid, get_text(uid, 'invalid_topic_number'))
            return
        
        topic_num = int(text)
        topic_key = f'Topik-{topic_num}'
        
        # Mavjudligini tekshirish
        data = load_user_data(uid)
        if topic_key in data:
            bot.send_message(uid, get_text(uid, 'topic_exists').format(topic_num))
            return
        
        # Yangi topik yaratish
        data[topic_key] = {
            'reading': {},
            'writing': {},
            'listening': {}
        }
        
        # Reading: 1-50
        for i in range(1, 51):
            data[topic_key]['reading'][f'{i}-savol so\'zlari'] = {}
        
        # Writing: 51-54
        for i in range(51, 55):
            data[topic_key]['writing'][f'{i}-savol so\'zlari'] = {}
        
        # Listening: 1-50
        for i in range(1, 51):
            data[topic_key]['listening'][f'{i}-savol so\'zlari'] = {}
        
        # Saqlash
        save_user_data(uid, data)
        
        # Xabar
        bot.send_message(uid, get_text(uid, 'topic_created').format(topic_num))
        
        # Context tozalash
        del user_context[uid]
    
    # ============================================
    # TOPIKNI O'CHIRISH - Raqam kiritish
    # ============================================
    elif action == 'deleting_topic':
        try:
            topic_num = int(text)
            topic_key = f"Topik-{topic_num}"
            
            # Ma'lumotlarni yuklash
            data = load_user_data(uid)
            
            if topic_key not in data:
                bot.send_message(uid, f"❌ {topic_num}-topik topilmadi!")
                return
            
            # Statistikani hisoblash
            stats = {}
            total_words = 0
            
            for section, questions in data[topic_key].items():
                section_words = 0
                for q_key, words in questions.items():
                    section_words += len(words)
                stats[section] = section_words
                total_words += section_words
            
            # Tasdiqlash xabari
            msg = f"⚠️ <b>TASDIQLASH</b>\n\n"
            msg += f"<b>{topic_num}-topikni</b> o'chirmoqchimisiz?\n\n"
            msg += "📊 <b>Statistika:</b>\n"
            
            if 'reading' in stats:
                msg += f"📖 Reading: {stats['reading']} ta so'z\n"
            if 'writing' in stats:
                msg += f"✍️ Writing: {stats['writing']} ta so'z\n"
            if 'listening' in stats:
                msg += f"🎧 Listening: {stats['listening']} ta so'z\n"
            
            msg += f"\n<b>JAMI: {total_words} ta so'z</b>\n\n"
            msg += "❗ Barcha ma'lumotlar o'chib ketadi!"
            
            # Inline tugmalar
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton(
                    text="✅ Ha, o'chirish",
                    callback_data=f"confirm_delete_{topic_num}"
                ),
                types.InlineKeyboardButton(
                    text="❌ Yo'q",
                    callback_data="back_topics"
                )
            )
            
            # Eski xabarni tahrirlash
            message_id = ctx.get('message_id')
            if message_id:
                try:
                    bot.edit_message_text(
                        msg,
                        uid,
                        message_id,
                        parse_mode="HTML",
                        reply_markup=markup
                    )
                except:
                    bot.send_message(uid, msg, parse_mode="HTML", reply_markup=markup)
            else:
                bot.send_message(uid, msg, parse_mode="HTML", reply_markup=markup)
            
            # User xabarini o'chirish
            try:
                bot.delete_message(uid, message.message_id)
            except:
                pass
            
            # State tozalash
            user_context[uid]['action'] = None
            
        except ValueError:
            bot.send_message(uid, "❌ Noto'g'ri format! Raqam kiriting.")
        except Exception as e:
            bot.send_message(uid, f"❌ Xatolik: {e}")
            user_context[uid]['action'] = None
    
    # ============================================
    # SO'Z QO'SHISH
    # ============================================
    elif action == 'add_word':
        topic_num = ctx['topic']
        section_type = ctx['section']
        question_num = ctx['question']
        
        topic_key = f'Topik-{topic_num}'
        section_map = {'r': 'reading', 'w': 'writing', 'l': 'listening'}
        section_name = section_map[section_type]
        question_key = f'{question_num}-savol so\'zlari'
        
        # So'zlarni parse qilish (hozirgi funksiya)
        words = parse_multiline_words(text)
        
        if not words:
            bot.send_message(uid, get_text(uid, 'no_words_parsed'))
            return
        
        # Ma'lumotlarni yuklash
        data = load_user_data(uid)
        
        # Topik/bo'lim/savol yaratish (agar yo'q bo'lsa)
        if topic_key not in data:
            data[topic_key] = {}
        if section_name not in data[topic_key]:
            data[topic_key][section_name] = {}
        if question_key not in data[topic_key][section_name]:
            data[topic_key][section_name][question_key] = {}
        
        # So'zlarni qo'shish
        for word in words:
            data[topic_key][section_name][question_key][word['korean']] = word['uzbek']
        
        # Saqlash
        save_user_data(uid, data)
        
        # Yangilangan so'zlarni olish
        all_words = data[topic_key][section_name][question_key]
        
        # Xabar tayyorlash
        section_display = {
            'r': 'Reading',
            'w': 'Writing',
            'l': 'Listening'
        }
        
        msg = f"📍 <b>{topic_num}-topik > {section_display[section_type]} > {question_num}-savol</b>\n"
        msg += "━━━━━━━━━━━━━━━━━\n\n"
        msg += f"✅ <b>{len(words)} ta so'z qo'shildi!</b>\n\n"
        msg += "<b>📝 BARCHA SO'ZLAR:</b>\n"
        
        for idx, (kr, uz) in enumerate(all_words.items(), 1):
            msg += f'{idx}. {kr} → {uz}\n'
        
        msg += '\n' + get_text(uid, 'words_count').format(len(all_words))
        
        # Inline tugmalar
        markup = get_question_actions_inline(
            topic_num, 
            section_type, 
            question_num, 
            True,  # so'zlar bor
            uid
        )
        
        bot.send_message(uid, msg, parse_mode='HTML', reply_markup=markup)
        
        # Context SAQLANADI - ortga bosilmaguncha
        # del user_context[uid]  # BU QATORNI O'CHIRDIM
    
    
    # ============================================
    # SO'Z O'CHIRISH
    # ============================================
    elif action == 'remove_word':
        topic_num = ctx['topic']
        section_type = ctx['section']
        question_num = ctx['question']
        
        topic_key = f'Topik-{topic_num}'
        section_map = {'r': 'reading', 'w': 'writing', 'l': 'listening'}
        section_name = section_map[section_type]
        question_key = f'{question_num}-savol so\'zlari'
        
        # Ma'lumotlarni yuklash
        data = load_user_data(uid)
        
        # So'zlarni vergul bilan ajratish
        words_to_remove = [w.strip() for w in text.split(',')]
        
        removed_list = []
        not_found_list = []
        
        if (topic_key in data and 
            section_name in data[topic_key] and 
            question_key in data[topic_key][section_name]):
            
            all_words = data[topic_key][section_name][question_key]
            
            for word in words_to_remove:
                found = False
                
                # Koreys so'z sifatida qidirish (kalit)
                if word in all_words:
                    removed_translation = all_words[word]
                    del all_words[word]
                    removed_list.append(f"{word} → {removed_translation}")
                    found = True
                else:
                    # O'zbek so'z sifatida qidirish (qiymat)
                    for kr, uz in list(all_words.items()):
                        if uz == word:
                            del all_words[kr]
                            removed_list.append(f"{kr} → {uz}")
                            found = True
                            break
                
                if not found:
                    not_found_list.append(word)
            
            # Saqlash
            if removed_list:
                save_user_data(uid, data)
            
            # Yangilangan so'zlarni olish
            remaining_words = data[topic_key][section_name][question_key]
            
            # Xabar tayyorlash
            section_display = {
                'r': 'Reading',
                'w': 'Writing',
                'l': 'Listening'
            }
            
            msg = f"📍 <b>{topic_num}-topik > {section_display[section_type]} > {question_num}-savol</b>\n"
            msg += "━━━━━━━━━━━━━━━━━\n\n"
            
            if removed_list:
                msg += f"✅ <b>O'chirildi ({len(removed_list)} ta):</b>\n"
                for item in removed_list:
                    msg += f"• {item}\n"
                msg += "\n"
            
            if not_found_list:
                msg += f"❌ <b>Topilmadi ({len(not_found_list)} ta):</b>\n"
                for item in not_found_list:
                    msg += f"• {item}\n"
                msg += "\n"
            
            if remaining_words:
                msg += "<b>📝 QOLGAN SO'ZLAR:</b>\n"
                for idx, (kr, uz) in enumerate(remaining_words.items(), 1):
                    msg += f'{idx}. {kr} → {uz}\n'
                msg += '\n' + get_text(uid, 'words_count').format(len(remaining_words))
            else:
                msg += get_text(uid, 'words_empty')
            
            # Inline tugmalar
            markup = get_question_actions_inline(
                topic_num, 
                section_type, 
                question_num, 
                bool(remaining_words),
                uid
            )
            
            bot.send_message(uid, msg, parse_mode='HTML', reply_markup=markup)
        else:
            msg = get_text(uid, 'word_not_found').format(", ".join(words_to_remove))
            bot.send_message(uid, msg)
        
        # Context SAQLANADI - ortga bosilmaguncha
        # del user_context[uid]  # BU QATORNI O'CHIRDIM



# ============================================
# MONITORING (AUTO)
# ============================================
def auto_monitor():
    """Avtomatik monitoring"""
    while True:
        try:
            if ADMIN_ID:
                check_battery_warning(bot, ADMIN_ID)
        except:
            pass
        time.sleep(600)

def clean_old_backups():
    """Eski backuplarni tozalash"""
    while True:
        try:
            now = time.time()
            cutoff = now - (BACKUP_CLEANUP_HOURS * 3600)

            if os.path.exists(BACKUPS_DIR):
                deleted_count = 0
                for f in os.listdir(BACKUPS_DIR):
                    if f.startswith("backup_") and f.endswith(".json"):
                        file_path = os.path.join(BACKUPS_DIR, f)
                        if os.path.getmtime(file_path) < cutoff:
                            os.remove(file_path)
                            deleted_count += 1
                
                if deleted_count > 0:
                    print(f"🧹 Tozalash: {deleted_count} ta eski backup o'chirildi.")
        except Exception as e:
            print(f"❌ Tozalashda xato: {e}")
        
        time.sleep(3600)

# ============================================
# ISHGA TUSHIRISH
# ============================================

# -*- coding: utf-8 -*-
"""
CALLBACK HANDLERS - Inline tugmalar uchun
Bu kodlarni main.py ga qo'shish kerak
"""

from telebot import types

# ============================================
# CALLBACK QUERY HANDLERS
# ============================================

@bot.callback_query_handler(func=lambda call: call.data.startswith('topic_'))
def topic_callback_handler(call):
    """Topik tanlanganda bo'limlarni ko'rsatish"""
    uid = call.from_user.id
    
    try:
        topic_num = call.data.replace('topic_', '')
        topic_key = f"Topik-{topic_num}"
        
        data = load_user_data(uid)
        
        if not data or topic_key not in data:
            bot.answer_callback_query(call.id, "❌ Topik topilmadi")
            return
        
        # Bo'limlar inline klaviaturasi
        markup = types.InlineKeyboardMarkup(row_width=3)
        
        sections_info = []
        buttons = []
        
        for section in ['reading', 'writing', 'listening']:
            if section in data[topic_key]:
                # So'zlar sonini hisoblash
                section_words = 0
                for question, words in data[topic_key][section].items():
                    section_words += len(words)
                
                if section_words > 0:
                    section_name = section.upper()
                    sections_info.append(f"📚 {section_name}: {section_words} ta so'z")
                    
                    # Inline tugma
                    button = types.InlineKeyboardButton(
                        text=f"📖 {section_name}",
                        callback_data=f"section_{topic_num}_{section}"
                    )
                    buttons.append(button)
        
        # Tugmalarni 3 tadan qo'shish
        for i in range(0, len(buttons), 3):
            markup.row(*buttons[i:i+3])
        
        # Orqaga tugmasi
        markup.row(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back_to_topics"))
        
        # Xabar
        msg = f"📖 <b>{topic_num}-TOPIK</b>\n"
        msg += "━━━━━━━━━━━━━━━━━\n\n"
        msg += "\n".join(sections_info)
        msg += "\n\n<b>Bo'limni tanlang:</b>"
        
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Xatolik: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('section_'))
def section_callback_handler(call):
    """Bo'lim tanlanganda savollarni ko'rsatish"""
    uid = call.from_user.id
    
    try:
        # section_35_reading
        parts = call.data.split('_')
        topic_num = parts[1]
        section = parts[2]
        
        topic_key = f"Topik-{topic_num}"
        data = load_user_data(uid)
        
        if not data or topic_key not in data or section not in data[topic_key]:
            bot.answer_callback_query(call.id, "❌ Bo'lim topilmadi")
            return
        
        # Savollarni olish
        questions = data[topic_key][section]
        
        # Inline klaviatura - 4 ustun
        markup = types.InlineKeyboardMarkup(row_width=4)
        
        # ALL tugmasi (birinchi qatorda alohida)
        all_button = types.InlineKeyboardButton(
            text="📚 ALL",
            callback_data=f"question_{topic_num}_{section}_all"
        )
        markup.row(all_button)
        
        # Savol raqamlari
        question_buttons = []
        question_nums = []
        
        for q_key in questions.keys():
            # "9-savol so'zlari" → "9"
            q_num = q_key.replace("-savol so'zlari", "")
            if q_num.isdigit():
                question_nums.append(int(q_num))
        
        # Tartibga solish
        question_nums.sort()
        
        # Tugmalar yaratish
        for q_num in question_nums:
            q_key = f"{q_num}-savol so'zlari"
            if q_key in questions and len(questions[q_key]) > 0:
                button = types.InlineKeyboardButton(
                    text=str(q_num),
                    callback_data=f"question_{topic_num}_{section}_{q_num}"
                )
                question_buttons.append(button)
        
        # 4 tadan qo'shish
        for i in range(0, len(question_buttons), 4):
            markup.row(*question_buttons[i:i+4])
        
        # Orqaga tugmasi
        markup.row(types.InlineKeyboardButton("◀️ Orqaga", callback_data=f"topic_{topic_num}"))
        
        # Xabar
        msg = f"📖 <b>{topic_num}-TOPIK > {section.upper()}</b>\n"
        msg += "━━━━━━━━━━━━━━━━━\n\n"
        msg += f"📊 Jami savollar: {len(question_buttons)} ta\n\n"
        msg += "<b>Savolni tanlang:</b>"
        
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Xatolik: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('question_'))
def question_callback_handler(call):
    """Savol tanlanganda so'zlarni ko'rsatish"""
    uid = call.from_user.id
    
    try:
        # question_35_reading_9 yoki question_35_reading_all
        parts = call.data.split('_')
        topic_num = parts[1]
        section = parts[2]
        q_identifier = parts[3]  # "9" yoki "all"
        
        topic_key = f"Topik-{topic_num}"
        data = load_user_data(uid)
        
        if not data or topic_key not in data or section not in data[topic_key]:
            bot.answer_callback_query(call.id, "❌ Ma'lumot topilmadi")
            return
        
        questions = data[topic_key][section]
        
        # So'zlarni to'plash
        words_list = []
        
        if q_identifier == "all":
            # Barcha savollarni ko'rsatish
            question_nums = []
            for q_key in questions.keys():
                q_num = q_key.replace("-savol so'zlari", "")
                if q_num.isdigit():
                    question_nums.append(int(q_num))
            
            question_nums.sort()
            
            for q_num in question_nums:
                q_key = f"{q_num}-savol so'zlari"
                if q_key in questions:
                    words = questions[q_key]
                    if words:
                        words_list.append(f"\n📝 <b>{q_num}-savol:</b>")
                        for idx, (korean, uzbek) in enumerate(words.items(), 1):
                            words_list.append(f"{idx}. {korean} → {uzbek}")
        else:
            # Bitta savolni ko'rsatish
            q_key = f"{q_identifier}-savol so'zlari"
            if q_key in questions:
                words = questions[q_key]
                for idx, (korean, uzbek) in enumerate(words.items(), 1):
                    words_list.append(f"{idx}. {korean} → {uzbek}")
        
        # Xabar tayyorlash
        if q_identifier == "all":
            header = f"📖 <b>{topic_num}-TOPIK > {section.upper()} > ALL</b>\n"
        else:
            header = f"📖 <b>{topic_num}-TOPIK > {section.upper()} > {q_identifier}-savol</b>\n"
        
        header += "━━━━━━━━━━━━━━━━━\n"
        
        msg = header + "\n".join(words_list)
        
        # Xabar juda uzun bo'lsa, bo'lib yuborish
        MAX_LENGTH = 4000
        
        if len(msg) > MAX_LENGTH:
            # Bo'limlab yuborish
            chunks = []
            current_chunk = header
            
            for line in words_list:
                if len(current_chunk) + len(line) + 1 > MAX_LENGTH:
                    chunks.append(current_chunk)
                    current_chunk = line + "\n"
                else:
                    current_chunk += line + "\n"
            
            if current_chunk:
                chunks.append(current_chunk)
            
            # Birinchi qismni edit qilish
            markup = types.InlineKeyboardMarkup()
            markup.row(types.InlineKeyboardButton("◀️ Orqaga", callback_data=f"section_{topic_num}_{section}"))
            
            bot.edit_message_text(
                chunks[0],
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=markup
            )
            
            # Qolganlarini yuborish
            for chunk in chunks[1:]:
                bot.send_message(uid, chunk, parse_mode="HTML")
            
        else:
            # Oddiy holat
            markup = types.InlineKeyboardMarkup()
            markup.row(types.InlineKeyboardButton("◀️ Orqaga", callback_data=f"section_{topic_num}_{section}"))
            
            bot.edit_message_text(
                msg,
                call.message.chat.id,
                call.message.message_id,
                parse_mode="HTML",
                reply_markup=markup
            )
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Xatolik: {e}")


@bot.callback_query_handler(func=lambda call: call.data == 'back_to_topics')
def back_to_topics_handler(call):
    """Topiklar ro'yxatiga qaytish"""
    uid = call.from_user.id
    
    try:
        data = load_user_data(uid)
        
        if not data:
            bot.answer_callback_query(call.id, "❌ Ma'lumot yo'q")
            return
        
        # Topiklar ro'yxati
        topics = []
        for topic_key in data.keys():
            if topic_key.startswith("Topik-"):
                topic_num = topic_key.replace("Topik-", "")
                if topic_num.isdigit():
                    topics.append(int(topic_num))
        
        topics_sorted = sorted(topics)
        
        # Inline klaviatura - 4 ustun
        markup = types.InlineKeyboardMarkup(row_width=4)
        
        buttons = []
        for topic_num in topics_sorted:
            button = types.InlineKeyboardButton(
                text=f"📖 {topic_num}",
                callback_data=f"topic_{topic_num}"
            )
            buttons.append(button)
        
        # 4 tadan qo'shish
        for i in range(0, len(buttons), 4):
            markup.row(*buttons[i:i+4])
        
        msg = "📚 <b>TOPIKLAR RO'YXATI</b>\n\n"
        msg += f"Jami: {len(topics_sorted)} ta topik\n\n"
        msg += "Topikni tanlang:"
        
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
        
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Xatolik: {e}")


# ============================================
# YANGILANGAN SECTIONS HANDLER
# ============================================

@bot.message_handler(func=lambda m: m.text in ['📂 BO\'LIMLAR', '📂 섹션'])
def sections_handler(message):
    """Bo'limlar menyusi"""
    uid = message.from_user.id
    
    if not is_logged_in(uid):
        bot.send_message(uid, get_text(uid, 'enter_password'))
        return
    
    data = load_user_data(uid)
    
    if not data:
        bot.send_message(uid, get_text(uid, 'no_topics'))
        return
    
    # Topiklar ro'yxati
    topics = []
    for topic_key in data.keys():
        if topic_key.startswith("Topik-"):
            topic_num = topic_key.replace("Topik-", "")
            if topic_num.isdigit():
                topics.append(int(topic_num))
    
    topics_sorted = sorted(topics)
    
    if not topics_sorted:
        bot.send_message(uid, get_text(uid, 'no_topics'))
        return
    
    # Inline klaviatura - 4 ustun
    markup = types.InlineKeyboardMarkup(row_width=4)
    
    buttons = []
    for topic_num in topics_sorted:
        button = types.InlineKeyboardButton(
            text=f"📖 {topic_num}",
            callback_data=f"topic_{topic_num}"
        )
        buttons.append(button)
    
    # 4 tadan qo'shish
    for i in range(0, len(buttons), 4):
        markup.row(*buttons[i:i+4])
    
    msg = "📚 <b>TOPIKLAR RO'YXATI</b>\n\n"
    msg += f"Jami: {len(topics_sorted)} ta topik\n\n"
    msg += "Topikni tanlang:"
    
    bot.send_message(
        uid,
        msg,
        parse_mode="HTML",
        reply_markup=markup
    )


if __name__ == "__main__":
    # Threading - Monitoringni alohida oqimda ishga tushirish
    threading.Thread(target=clean_old_backups, daemon=True).start()

    try:
        me = bot.get_me()
        print(f"\n{'='*40}")
        print(f"BOT: @{me.username}")
        print(f"STATUS: RUNNING ✅")
        print(f"{'='*40}\n")
        bot.infinity_polling()
    except Exception as e:
        print(f"ERROR: {e}")