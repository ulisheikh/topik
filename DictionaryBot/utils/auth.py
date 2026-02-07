# -*- coding: utf-8 -*-
"""
AUTENTIFIKATSIYA TIZIMI
Parol va session boshqaruvi
"""

import json
import os
import time
from config import *

# GLOBAL VARIABLES
USER_SESSIONS = {}
LOGIN_ATTEMPTS = {}
BLOCKED_USERS = {}

def load_passwords():
    """Parollarni yuklash"""
    if os.path.exists(PASSWORDS_FILE):
        try:
            with open(PASSWORDS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_passwords(passwords):
    """Parollarni saqlash"""
    os.makedirs(os.path.dirname(PASSWORDS_FILE), exist_ok=True)
    with open(PASSWORDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(passwords, f, ensure_ascii=False, indent=4)

import json
import os

def update_password(role, new_password):
    # FAYL YO'LI ANIQLANDI:
    file_path = "database/passwords.json" 
    
    if os.path.exists(file_path):
        try:
            # 1. Asl faylni o'qiymiz
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 2. Yangilaymiz
            if role == 'user':
                data['user_password'] = str(new_password)
            elif role == 'admin':
                data['admin_password'] = str(new_password)
                
            # 3. Aynan o'sha faylga qayta yozamiz
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            print(f"✅ Parol {file_path} ichida yangilandi!")
            return True
        except Exception as e:
            print(f"❌ Faylga yozishda xato: {e}")
            return False
    else:
        print(f"❌ Xato: {file_path} topilmadi!")
        return False

def load_sessions():
    """Sessiyalarni yuklash"""
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_sessions(sessions):
    """Sessiyalarni saqlash"""
    os.makedirs(os.path.dirname(SESSIONS_FILE), exist_ok=True)
    with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, ensure_ascii=False, indent=4)

def initialize_passwords():
    """Default parollarni o'rnatish"""
    passwords = load_passwords()
    # Agar fayl bo'sh bo'lsa yoki kerakli kalitlar bo'lmasa
    if not passwords or 'user_password' not in passwords:
        passwords = {
            'user_password': DEFAULT_USER_PASSWORD,
            'admin_password': DEFAULT_ADMIN_PASSWORD
        }
        save_passwords(passwords)
    return passwords

def verify_password(user_id, password):
    passwords = load_passwords()
    
    # 1. Fayldagi parollarni olamiz
    file_admin_pwd = passwords.get('admin_password')
    file_user_pwd = passwords.get('user_password')

    # 2. ADMINni tekshirish
    # Agar faylda parol bo'lsa, faqat o'shani tekshir. Bo'lmasa Configdagini ol.
    target_admin = file_admin_pwd if file_admin_pwd else DEFAULT_ADMIN_PASSWORD
    if str(password) == str(target_admin):
        return 'admin'

    # 3. USERni tekshirish
    target_user = file_user_pwd if file_user_pwd else DEFAULT_USER_PASSWORD
    if str(password) == str(target_user):
        return 'user'

    return None

def is_user_blocked(user_id):
    """Foydalanuvchi bloklangan yoki yo'qligini tekshirish"""
    if user_id in BLOCKED_USERS:
        if time.time() < BLOCKED_USERS[user_id]:
            return True
        else:
            del BLOCKED_USERS[user_id]
            LOGIN_ATTEMPTS[user_id] = 0
    return False

def add_login_attempt(user_id):
    """Login urinishni qo'shish"""
    if user_id not in LOGIN_ATTEMPTS:
        LOGIN_ATTEMPTS[user_id] = 0
    LOGIN_ATTEMPTS[user_id] += 1
    
    if LOGIN_ATTEMPTS[user_id] >= 3:
        # 5 daqiqaga bloklash
        BLOCKED_USERS[user_id] = time.time() + 300
        return True
    return False

def login_user(user_id, role):
    """Foydalanuvchini tizimga kiritish"""
    global USER_SESSIONS
    
    # ✅ Timestamp qo'shish
    USER_SESSIONS[user_id] = {
        'role': role,
        'logged_in': True,
        'timestamp': time.time()  # ← YANGI!
    }
    
    # Sessiyani saqlash
    sessions = load_sessions()
    sessions[str(user_id)] = USER_SESSIONS[user_id]
    save_sessions(sessions)
    
    # Login urinishlarni tozalash
    if user_id in LOGIN_ATTEMPTS:
        LOGIN_ATTEMPTS[user_id] = 0
    
    print(f"✅ User {user_id}: Login qildi ({role})")

def logout_user(user_id):
    """Foydalanuvchini tizimdan chiqarish"""
    global USER_SESSIONS
    if user_id in USER_SESSIONS:
        del USER_SESSIONS[user_id]
    
    sessions = load_sessions()
    if str(user_id) in sessions:
        del sessions[str(user_id)]
    save_sessions(sessions)

def is_logged_in(user_id):
    """Foydalanuvchi tizimga kirgan yoki yo'qligini tekshirish"""
    global USER_SESSIONS
    
    uid = str(user_id)
    
    # 1. Avval global sessiyadan tekshirish
    if user_id in USER_SESSIONS:
        session = USER_SESSIONS[user_id]
        
        # Timestamp tekshirish
        if 'timestamp' in session:
            current_time = time.time()
            session_time = session['timestamp']
            
            # 24 soat = 86400 sekund
            if current_time - session_time > 86400:
                print(f"❌ User {uid}: Global session muddati tugagan")
                del USER_SESSIONS[user_id]
                
                # Fayldan ham o'chirish
                sessions = load_sessions()
                if uid in sessions:
                    del sessions[uid]
                    save_sessions(sessions)
                
                return False
        
        return session.get('logged_in', False)
    
    # 2. Fayldan yuklash
    sessions = load_sessions()
    if uid in sessions:
        session = sessions[uid]
        
        # Timestamp tekshirish
        if 'timestamp' in session:
            current_time = time.time()
            session_time = session['timestamp']
            
            # 24 soat = 86400 sekund
            if current_time - session_time > 86400:
                print(f"❌ User {uid}: Fayl session muddati tugagan")
                del sessions[uid]
                save_sessions(sessions)
                return False
        
        # Global sessiyaga qo'shish
        USER_SESSIONS[user_id] = session
        return session.get('logged_in', False)
    
    print(f"❌ User {uid}: Session topilmadi")
    return False

def get_user_role(user_id):
    """Foydalanuvchi rolini olish"""
    if user_id in USER_SESSIONS:
        return USER_SESSIONS[user_id].get('role', 'user')
    
    sessions = load_sessions()
    if str(user_id) in sessions:
        return sessions[str(user_id)].get('role', 'user')
    
    return 'user'

def is_admin(user_id):
    """Admin yoki yo'qligini tekshirish"""
    return get_user_role(user_id) == 'admin'

def change_password(role, new_password):
    """Parolni o'zgartirish"""
    passwords = load_passwords()
    passwords[role] = new_password
    save_passwords(passwords)

# Default parollarni o'rnatish
initialize_passwords()