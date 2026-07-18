# -*- coding: utf-8 -*-
"""
KOREAN-O'ZBEK LUG'AT BOT
Yangilangan versiya - 2.1
User-based tizim
FIX: state (context) tekshiruvi endi eng birinchi bo'lib ishlaydi,
     shuning uchun so'z qo'shish/o'chirish paytida qidiruv/tahrirlash
     bilan aralashib ketmaydi.
YANGI: "rmall" - joriy savoldagi barcha so'zlarni o'chirish
YANGI: "*" - butun lug'atdan yulduzli (muhim) so'zlarni topish
"""

import telebot
import os
import re
import threading
import time

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

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from bot_tokens import DICT_BOT_TOKEN
bot = telebot.TeleBot(DICT_BOT_TOKEN)

# USER CONTEXT
user_context = {}

# ============================================
# YORDAMCHI FUNKSIYALAR
# ============================================

def get_help_text(user_id):
    """Yordam matni"""
    header = f"<b>{get_text(user_id, 'help_title')}</b>\n"
    header += "━━━━━━━━━━━━━━━━━\n\n"
    body  = f"{get_text(user_id, 'help_add')}\n\n"
    body += f"{get_text(user_id, 'help_navigate')}\n\n"
    body += f"{get_text(user_id, 'help_search')}\n\n"
    body += f"{get_text(user_id, 'help_edit')}\n\n"
    body += f"{get_text(user_id, 'help_delete')}\n\n"
    body += f"{get_text(user_id, 'help_export')}\n\n"
    body += f"{get_text(user_id, 'help_tip')}"
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
    
    # 4. Statistika tayyorlash
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
    
    # 5. FAQAT Welcome + Stats (Help ALOHIDA!)
    combined_msg = f"{get_text(uid, 'welcome')}\n\n{stats_msg}"
    
    bot.send_message(
        uid,
        combined_msg,
        parse_mode="HTML",
        reply_markup=get_main_keyboard(uid)
    )

# ============================================
# /help KOMANDASI
# ============================================

@bot.message_handler(commands=['help'])
def help_handler(message):
    """Yordam matni"""
    uid = message.from_user.id
    
    # Login tekshirish
    if not is_logged_in(uid):
        bot.send_message(uid, get_text(uid, 'enter_password'))
        return
    
    bot.send_message(uid, get_help_text(uid), parse_mode="HTML")

# ============================================
# PAROL HANDLER
# ============================================

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
# EXPORT (JSON VA PYTHON)
# ============================================

@bot.message_handler(func=lambda m: m.text in ['📥 JSON'])
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

@bot.message_handler(func=lambda m: m.text in ['🐍 PYTHON'])
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
        msg += "\n\n🗑 Barchasini o'chirish uchun: <code>rmall</code>"
        
        bot.send_message(uid, msg, parse_mode='HTML')
        
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
        
        section_names = {
            'r': 'reading',
            'w': 'writing',
            'l': 'listening'
        }
        
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
# YULDUZLI SO'ZLAR (*) - butun lug'atdan qidirish
# ============================================

def handle_starred_words(uid):
    """
    Boshida '*' bo'lgan (muhim/yulduzli) so'zlarni butun
    lug'atdan (barcha topik/bo'lim/savollardan) topib beradi.
    """
    data = load_user_data(uid)
    results = []
    
    for topic_key, topic_data in data.items():
        if not topic_key.startswith("Topik-"):
            continue
        
        topic_num = topic_key.replace("Topik-", "")
        
        for section_name, questions in topic_data.items():
            for question_key, words in questions.items():
                question_num = question_key.replace("-savol so'zlari", "")
                
                for korean, uzbek in words.items():
                    if korean.strip().startswith('*'):
                        results.append({
                            'korean': korean,
                            'uzbek': uzbek,
                            'location': f"{topic_num}>{question_num}"
                        })
    
    if results:
        msg = f"⭐ <b>Yulduzli so'zlar</b> ({len(results)} ta)\n\n"
        
        for idx, r in enumerate(results[:30], 1):
            msg += f"{idx}. <b>{r['korean']}</b> → {r['uzbek']}\n"
            msg += f"   📍 {r['location']}\n"
        
        if len(results) > 30:
            msg += f"\n... va yana {len(results) - 30} ta"
    else:
        msg = "❌ Yulduzli so'zlar topilmadi"
    
    bot.send_message(uid, msg, parse_mode='HTML')


# ============================================
# STATE (CONTEXT) GA BOG'LIQ AMALLAR
# Bu funksiya endi text_handler ichida ENG BIRINCHI chaqiriladi,
# shuning uchun qidiruv/tahrirlash bilan hech qachon aralashib
# ketmaydi.
# ============================================

def handle_stateful_text(message, uid, text):
    """User biror action (context) ichida bo'lganda ishlaydigan handler"""
    ctx = user_context[uid]
    action = ctx.get('action')
    
    # ============================================
    # YANGI TOPIK YARATISH
    # ============================================
    if action == 'create_topic':
        if not text.isdigit():
            bot.send_message(uid, get_text(uid, 'invalid_topic_number'))
            return
        
        topic_num = int(text)
        topic_key = f'Topik-{topic_num}'
        
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
        
        save_user_data(uid, data)
        bot.send_message(uid, get_text(uid, 'topic_created').format(topic_num))
        del user_context[uid]
    
    # ============================================
    # TOPIKNI O'CHIRISH
    # ============================================
    elif action == 'deleting_topic':
        try:
            topic_num = int(text)
            topic_key = f"Topik-{topic_num}"
            
            data = load_user_data(uid)
            
            if topic_key not in data:
                bot.send_message(uid, f"❌ {topic_num}-topik topilmadi!")
                return
            
            # Statistika
            stats = {}
            total_words = 0
            
            for section, questions in data[topic_key].items():
                section_words = 0
                for q_key, words in questions.items():
                    section_words += len(words)
                stats[section] = section_words
                total_words += section_words
            
            # Tasdiqlash
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
            
            message_id = ctx.get('message_id')
            if message_id:
                try:
                    bot.edit_message_text(msg, uid, message_id, parse_mode="HTML", reply_markup=markup)
                except:
                    bot.send_message(uid, msg, parse_mode="HTML", reply_markup=markup)
            else:
                bot.send_message(uid, msg, parse_mode="HTML", reply_markup=markup)
            
            try:
                bot.delete_message(uid, message.message_id)
            except:
                pass
            
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
        
        # So'zlarni parse qilish
        words = parse_multiline_words(text)
        
        if not words:
            bot.send_message(uid, get_text(uid, 'no_words_parsed'))
            return
        
        # Ma'lumotlarni yuklash
        data = load_user_data(uid)
        
        # Yaratish
        if topic_key not in data:
            data[topic_key] = {}
        if section_name not in data[topic_key]:
            data[topic_key][section_name] = {}
        if question_key not in data[topic_key][section_name]:
            data[topic_key][section_name][question_key] = {}
        
        # So'zlarni qo'shish
        for word in words:
            data[topic_key][section_name][question_key][word['korean']] = word['uzbek']
        
        save_user_data(uid, data)
        
        # Xabar
        all_words = data[topic_key][section_name][question_key]
        
        section_display = {'r': 'Reading', 'w': 'Writing', 'l': 'Listening'}
        
        msg = f"📍 <b>{topic_num}-topik > {section_display[section_type]} > {question_num}-savol</b>\n"
        msg += "━━━━━━━━━━━━━━━━━\n\n"
        msg += f"✅ <b>{len(words)} ta so'z qo'shildi!</b>\n\n"
        msg += "<b>📝 BARCHA SO'ZLAR:</b>\n"
        
        for idx, (kr, uz) in enumerate(all_words.items(), 1):
            msg += f'{idx}. {kr} → {uz}\n'
        
        msg += '\n' + get_text(uid, 'words_count').format(len(all_words))
        
        markup = get_question_actions_inline(topic_num, section_type, question_num, True, uid)
        bot.send_message(uid, msg, parse_mode='HTML', reply_markup=markup)
    
    # ============================================
    # SO'Z O'CHIRISH (+ rmall = barchasini o'chirish)
    # ============================================
    elif action == 'remove_word':
        topic_num = ctx['topic']
        section_type = ctx['section']
        question_num = ctx['question']
        
        topic_key = f'Topik-{topic_num}'
        section_map = {'r': 'reading', 'w': 'writing', 'l': 'listening'}
        section_name = section_map[section_type]
        question_key = f'{question_num}-savol so\'zlari'
        
        data = load_user_data(uid)
        
        if not (topic_key in data and section_name in data[topic_key] and question_key in data[topic_key][section_name]):
            bot.send_message(uid, "❌ So'zlar topilmadi!")
            return
        
        all_words = data[topic_key][section_name][question_key]
        section_display = {'r': 'Reading', 'w': 'Writing', 'l': 'Listening'}
        
        # ------------------------------------------------------
        # RMALL: FAQAT joriy savol/bo'limdagi barcha so'zlarni o'chirish
        # ------------------------------------------------------
        if text.strip().lower() == 'rmall':
            removed_count = len(all_words)
            
            if removed_count == 0:
                bot.send_message(uid, "❌ Bu savolda so'zlar yo'q!")
                return
            
            # Backup (tiklash uchun)
            create_backup(uid, 'question_words', dict(all_words), f"{topic_num}_{section_type}_{question_num}")
            
            data[topic_key][section_name][question_key] = {}
            save_user_data(uid, data)
            
            msg = f"📍 <b>{topic_num}-topik > {section_display[section_type]} > {question_num}-savol</b>\n"
            msg += "━━━━━━━━━━━━━━━━━\n\n"
            msg += f"🗑 <b>Barcha so'zlar o'chirildi! ({removed_count} ta)</b>\n\n"
            msg += get_text(uid, 'words_empty')
            
            markup = get_question_actions_inline(topic_num, section_type, question_num, False, uid)
            bot.send_message(uid, msg, parse_mode='HTML', reply_markup=markup)
            return
        
        # ------------------------------------------------------
        # ESKI FUNKSIYA: raqam yoki so'z bo'yicha o'chirish (o'zgarmagan)
        # ------------------------------------------------------
        words_list = list(all_words.items())
        
        words_to_remove = [w.strip() for w in text.split(',')]
        
        removed_list = []
        not_found_list = []
        
        for word in words_to_remove:
            found = False
            
            # Raqam bo'lsa
            if word.isdigit():
                index = int(word) - 1
                if 0 <= index < len(words_list):
                    kr, uz = words_list[index]
                    if kr in all_words:
                        del all_words[kr]
                        removed_list.append(f"{word}. {kr} → {uz}")
                        found = True
                else:
                    not_found_list.append(f"{word} (raqam xato)")
            else:
                # Kalit bo'yicha
                if word in all_words:
                    removed_translation = all_words[word]
                    del all_words[word]
                    removed_list.append(f"{word} → {removed_translation}")
                    found = True
                else:
                    # Qiymat bo'yicha
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
        
        # Xabar
        remaining_words = data[topic_key][section_name][question_key]
        
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
        
        markup = get_question_actions_inline(topic_num, section_type, question_num, bool(remaining_words), uid)
        bot.send_message(uid, msg, parse_mode='HTML', reply_markup=markup)


# ============================================
# TEXT MESSAGE HANDLER (Context asosida)
# ============================================

@bot.message_handler(func=lambda m: True, content_types=['text'])
def text_handler(message):
    """Barcha text xabarlar uchun"""
    uid = message.from_user.id
    text = message.text.strip()
    
    # ============================================
    # 1) STATE (CONTEXT) BOR-YO'QLIGINI TEKSHIRISH — ENG BIRINCHI!
    # Muhim: agar user biror action ichida bo'lsa (so'z qo'shish,
    # so'z o'chirish, topik yaratish/o'chirish va h.k.), o'sha action
    # DARHOL bajariladi va pastdagi qidiruv/tahrirlash bloklariga
    # umuman kirmaydi. Aynan shu joy bo'lmagani sababli oldin
    # "so'z o'chirish" state'i qidiruv bilan aralashib ketardi.
    # ============================================
    if uid in user_context and user_context[uid].get('action'):
        handle_stateful_text(message, uid, text)
        return
    
    # ============================================
    # 2) YULDUZLI SO'ZLAR: hohlagan joydan aynan "*" yuborilsa
    # ============================================
    if text == '*':
        handle_starred_words(uid)
        return
    
    # ============================================
    # 3) SO'Z QIDIRISH - oddiy matn yoki s.matn
    # ============================================
    # Agar = yo'q va / bilan boshlanmasa
    if '=' not in text and not text.startswith('/') and len(text) >= 2:
        # s. ni olib tashlash (agar bor bo'lsa)
        search_word = text[2:].strip() if text.lower().startswith('s.') else text.strip()
        
        # Ma'lumotlarni yuklash
        data = load_user_data(uid)
        results = []
        
        # Barcha joylardan qidirish
        for topic_key, topic_data in data.items():
            if not topic_key.startswith("Topik-"):
                continue
            
            topic_num = topic_key.replace("Topik-", "")
            
            for section_name, questions in topic_data.items():
                for question_key, words in questions.items():
                    question_num = question_key.replace("-savol so'zlari", "")
                    
                    # So'zlarni qidirish
                    for korean, uzbek in words.items():
                        if search_word.lower() in korean.lower() or search_word.lower() in uzbek.lower():
                            results.append({
                                'korean': korean,
                                'uzbek': uzbek,
                                'location': f"{topic_num}>{question_num}"
                            })
        
        # Natijalarni ko'rsatish
        if results:
            msg = f"🔍 <b>{search_word}</b> ({len(results)} ta)\n\n"
            
            for idx, r in enumerate(results[:20], 1):
                msg += f"{idx}. <b>{r['korean']}</b> → {r['uzbek']}\n"
                msg += f"   📍 {r['location']}\n"
            
            if len(results) > 20:
                msg += f"\n... va yana {len(results) - 20} ta"
            
            bot.send_message(uid, msg, parse_mode='HTML')
            return
        # Agar topilmasa - keyingi bloklarga o'tish
    
    # ============================================
    # 4) SO'Z TAHRIRLASH - salom=안녕 yoki 안녕=salom
    # ============================================
    if '=' in text and len(text) > 3:
        parts = text.split('=', 1)
        
        if len(parts) == 2:
            left = parts[0].strip()
            right = parts[1].strip()
            
            if left and right:
                # Ma'lumotlarni yuklash
                data = load_user_data(uid)
                
                if not data:
                    bot.send_message(uid, "❌ Lug'atingiz bo'sh!")
                    return
                
                # Qidirish
                found = []
                
                for topic_key, topic_data in data.items():
                    if not topic_key.startswith("Topik-"):
                        continue
                    
                    for section_name, questions in topic_data.items():
                        for question_key, words in questions.items():
                            for kr, uz in words.items():
                                if left.lower() == kr.lower() or left.lower() == uz.lower():
                                    found.append({
                                        'topic_key': topic_key,
                                        'section': section_name,
                                        'question': question_key,
                                        'old_kr': kr,
                                        'old_uz': uz
                                    })
                
                if not found:
                    bot.send_message(uid, f"❌ <b>{left}</b> topilmadi", parse_mode='HTML')
                    return
                
                if len(found) > 1:
                    msg = f"❌ Ko'p natija: {len(found)} ta\n\n"
                    msg += "Aniqroq kiriting yoki savol ichida tahrirlang"
                    bot.send_message(uid, msg)
                    return
                
                # Bitta natija - TAHRIRLASH
                item = found[0]
                
                # Eski so'zni o'chirish
                del data[item['topic_key']][item['section']][item['question']][item['old_kr']]
                
                # Yangi so'zni aniqlash
                if is_korean(left):
                    new_kr = left
                    new_uz = right
                elif is_korean(right):
                    new_kr = right
                    new_uz = left
                else:
                    # Ikkala tomon ham koreys emas
                    new_kr = right if is_korean(item['old_kr']) else left
                    new_uz = left if is_korean(item['old_kr']) else right
                
                # Yangi so'zni qo'shish
                data[item['topic_key']][item['section']][item['question']][new_kr] = new_uz
                
                # Saqlash
                save_user_data(uid, data)
                
                bot.send_message(
                    uid,
                    f"✅ Tahrirlandi!\n\n"
                    f"<s>{item['old_kr']} → {item['old_uz']}</s>\n"
                    f"<b>{new_kr} → {new_uz}</b>",
                    parse_mode='HTML'
                )
                return
    
    # Hech biriga to'g'ri kelmadi - hech narsa qilmaymiz


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
# ==================== ISHGA TUSHIRISH (YANGILANGAN) ====================

if __name__ == "__main__":
    # 1. Monitoringni fonda ishga tushirish
    threading.Thread(target=clean_old_backups, daemon=True).start()

    try:
        # 2. MENU BUYRUQLARINI O'RNATISH (YANGI!)
        bot.set_my_commands([
            types.BotCommand("start", "🏠 Botni qayta ishga tushirish"),
            types.BotCommand("help", "❓ Yordam va yo'riqnoma"),
            types.BotCommand("status", "📊 Tizim holati (Admin)")
        ])

        me = bot.get_me()
        print(f"\n{'='*40}")
        print(f"BOT: @{me.username}")
        print(f"STATUS: RUNNING ✅")
        print(f"MENU: COMMANDS SET SUCCESSFULLY ✅")
        print(f"{'='*40}\n")
        
        # 3. Pollingni boshlash
        bot.infinity_polling()
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")