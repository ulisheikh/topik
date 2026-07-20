"""
DictionaryBot - User boshqaruv moduli
Userlar haqida to'liq ma'lumot
YANGI: Bloklash/Blokdan chiqarish, faqat lug'atni o'chirish
       (akkaunt ma'lumotlari saqlanib qoladi), himoyalangan userlar
"""

import os
import json
from datetime import datetime
from config import USER_DATA_DIR, DATABASE_DIR, USERS_INFO_FILE
from utils.auth import is_protected_user, is_user_admin_blocked


def ensure_users_info_file():
    """users_info.json faylini yaratish"""
    if not os.path.exists(USERS_INFO_FILE):
        with open(USERS_INFO_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)


def save_user_info(user_id, first_name, last_name, username):
    # USERS_INFO_FILE o'zgaruvchisidan foydalanamiz (config.py dagi)
    file_path = USERS_INFO_FILE 
    users = {}

    # 1. Faylni xavfsiz o'qish
    if os.path.exists(file_path) and os.stat(file_path).st_size > 0:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                users = json.load(f)
        except:
            users = {}

    uid = str(user_id)

    # Mavjud "blocked" va "joined_at" qiymatlarini SAQLAB QOLAMIZ -
    # har safar /start bosilganda ular qayta yozilib ketmasligi kerak
    existing = users.get(uid, {})
    existing_blocked = existing.get('blocked', False)
    existing_joined = existing.get('joined_at')

    # 2. Ma'lumot qo'shish
    users[uid] = {
        "first_name": first_name if first_name else "",
        "last_name": last_name if last_name else "",
        "username": username if username else "",
        "joined_at": existing_joined if existing_joined else datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "blocked": existing_blocked
    }

    # 3. Faylga yozish
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

def get_user_info(user_id):
    """User ma'lumotlarini xavfsiz olish"""
    file_path = USERS_INFO_FILE
    
    if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
        return {"first_name": "User", "last_name": "", "username": "", "joined_at": "Noma'lum", "blocked": False}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            users = json.load(f)
            return users.get(str(user_id), {"first_name": "User", "last_name": "", "username": "", "joined_at": "Noma'lum", "blocked": False})
    except:
        return {"first_name": "User", "last_name": "", "username": "", "joined_at": "Noma'lum", "blocked": False}


def get_all_users():
    """
    Barcha (botdan foydalangan) foydalanuvchilar ro'yxati.
    YANGI: endi users_info.json asosida olinadi - shunda lug'ati
    o'chirilgan userlar ham (akkaunt ma'lumoti saqlangani uchun)
    ro'yxatda ko'rinib turaveradi.
    """
    ensure_users_info_file()
    
    if not os.path.exists(USERS_INFO_FILE) or os.stat(USERS_INFO_FILE).st_size == 0:
        return []
    
    try:
        with open(USERS_INFO_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
        return list(users.keys())
    except:
        return []


def get_user_file(user_id):
    """User fayl yo'li"""
    return os.path.join(USER_DATA_DIR, f"user_{user_id}.json")


def get_user_stats(user_id):
    """User statistikasi"""
    user_file = get_user_file(user_id)
    
    if not os.path.exists(user_file):
        return {
            'topics': 0,
            'words': 0,
            'size': '0 B'
        }
    
    # Fayl hajmi
    size_bytes = os.path.getsize(user_file)
    if size_bytes < 1024:
        size = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        size = f"{size_bytes / 1024:.1f} KB"
    else:
        size = f"{size_bytes / (1024 * 1024):.1f} MB"
    
    # Topik va so'zlar soni
    try:
        with open(user_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        topics = len([k for k in data.keys() if k.startswith('Topik-')])
        
        words = 0
        for topic in data.values():
            for section in topic.values():
                for question in section.values():
                    words += len(question)
        
        return {
            'topics': topics,
            'words': words,
            'size': size
        }
    except:
        return {
            'topics': 0,
            'words': 0,
            'size': size
        }


def get_user_details(user_id):
    """User to'liq ma'lumotlari (blok holati va himoyalanganligi bilan)"""
    info = get_user_info(user_id)
    stats = get_user_stats(user_id)
    
    return {
        'user_id': user_id,
        'first_name': info['first_name'],
        'last_name': info['last_name'],
        'username': info['username'],
        'joined_at': info['joined_at'],
        'topics': stats['topics'],
        'words': stats['words'],
        'size': stats['size'],
        'blocked': is_user_admin_blocked(user_id),
        'protected': is_protected_user(user_id)
    }


def format_user_details(current_user_id, details):
    """User ma'lumotlarini formatlash"""
    full_name = f"{details['first_name']} {details['last_name']}".strip()
    username = f"@{details['username']}" if details['username'] else "Username yo'q"
    
    if details.get('protected'):
        status = "👑 Admin / Bot egasi (himoyalangan)"
    elif details.get('blocked'):
        status = "🔒 Bloklangan"
    else:
        status = "✅ Faol"
    
    msg = f"📊 <b>Foydalanuvchi ma'lumotlari</b>\n\n"
    msg += f"👤 <b>Ism:</b> {full_name}\n"
    msg += f"🆔 <b>Username:</b> {username}\n"
    msg += f"📱 <b>ID:</b> <code>{details['user_id']}</code>\n"
    msg += f"📅 <b>Qo'shilgan:</b> {details['joined_at']}\n"
    msg += f"📌 <b>Holat:</b> {status}\n\n"
    msg += f"📚 <b>Topiklar:</b> {details['topics']} ta\n"
    msg += f"📝 <b>So'zlar:</b> {details['words']} ta\n"
    msg += f"💾 <b>Fayl hajmi:</b> {details['size']}\n"
    
    return msg


def format_users_list(current_user_id, users_list):
    """Userlar ro'yxatini formatlash (matn ko'rinishida, zaxira uchun)"""
    if not users_list:
        msg = "❌ Hech qanday foydalanuvchi topilmadi."
        return msg
    
    msg = f"👥 <b>Foydalanuvchilar ro'yxati</b> ({len(users_list)} ta)\n\n"
    
    for idx, user_id in enumerate(users_list, 1):
        details = get_user_details(user_id)
        
        full_name = f"{details['first_name']} {details['last_name']}".strip()
        username = f"@{details['username']}" if details['username'] else "❌"
        
        if details.get('protected'):
            status_icon = "👑"
        elif details.get('blocked'):
            status_icon = "🔒"
        else:
            status_icon = "✅"
        
        msg += f"📊 <b>#{idx}</b> {status_icon}\n"
        msg += f"├ 👤 {full_name}\n"
        msg += f"├ 🆔 {username}\n"
        msg += f"├ 📱 ID: <code>{user_id}</code>\n"
        msg += f"├ 📚 Topiklar: {details['topics']}\n"
        msg += f"├ 📝 So'zlar: {details['words']}\n"
        msg += f"└ 💾 Hajm: {details['size']}\n\n"
    
    return msg


# ============================================
# YANGI: BLOKLASH / BLOKDAN CHIQARISH
# ============================================

def set_user_blocked(user_id, blocked):
    """
    Foydalanuvchini DOIMIY bloklash yoki blokdan chiqarish
    (users_info.json orqali saqlanadi).
    
    DIQQAT: Himoyalangan foydalanuvchilarni (admin / bot egasi)
    bloklash SO'ZSIZ rad etiladi - hech qanday holatda ular
    bloklanmaydi.
    """
    if blocked and is_protected_user(user_id):
        return False
    
    ensure_users_info_file()
    
    with open(USERS_INFO_FILE, 'r', encoding='utf-8') as f:
        users = json.load(f)
    
    uid = str(user_id)
    if uid not in users:
        return False
    
    users[uid]['blocked'] = blocked
    
    with open(USERS_INFO_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    
    return True


# ============================================
# YANGI: FAQAT LUG'ATNI O'CHIRISH (akkaunt saqlanadi)
# ============================================

def delete_user_dictionary_only(user_id):
    """
    Foydalanuvchining FAQAT lug'at ma'lumotlarini butunlay o'chiradi
    (user_data/user_X.json va uning .backup fayli).
    
    Akkaunt ma'lumotlari (users_info.json dagi ism, username,
    qo'shilgan sana, blok holati) SAQLANIB QOLADI.
    
    DIQQAT: Himoyalangan foydalanuvchilarning (admin / bot egasi)
    ma'lumotlari HECH QACHON o'chirilmaydi.
    """
    if is_protected_user(user_id):
        return False
    
    user_file = get_user_file(user_id)
    backup_file = f"{user_file}.backup"
    
    deleted = False
    
    if os.path.exists(user_file):
        os.remove(user_file)
        deleted = True
    
    if os.path.exists(backup_file):
        os.remove(backup_file)
    
    return deleted


def delete_user_data(user_id):
    """
    ESKI FUNKSIYA (endi ishlatilmaydi, orqaga moslik uchun qoldirilgan).
    Bu funksiya akkaunt ma'lumotini ham o'chiradi - buning o'rniga
    delete_user_dictionary_only() dan foydalaning.
    """
    if is_protected_user(user_id):
        return False
    
    user_file = get_user_file(user_id)
    backup_file = f"{user_file}.backup"
    
    deleted = False
    
    # Asosiy faylni o'chirish
    if os.path.exists(user_file):
        os.remove(user_file)
        deleted = True
    
    # Backup faylni o'chirish
    if os.path.exists(backup_file):
        os.remove(backup_file)
    
    # users_info.json dan o'chirish
    ensure_users_info_file()
    
    with open(USERS_INFO_FILE, 'r', encoding='utf-8') as f:
        users = json.load(f)
    
    uid = str(user_id)
    if uid in users:
        del users[uid]
        
        with open(USERS_INFO_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    
    return deleted

def get_user_words_count(user_id):
    """User so'zlari sonini hisoblash"""
    user_file = get_user_file(user_id)
    
    if not os.path.exists(user_file):
        return 0
    
    try:
        with open(user_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        words = 0
        for topic in data.values():
            for section in topic.values():
                for question in section.values():
                    words += len(question)
        
        return words
    except:
        return 0