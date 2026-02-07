# -*- coding: utf-8 -*-
"""
DATA HANDLER
User ma'lumotlari bilan ishlash
"""

import json
import os
import re
from config import USER_DATA_DIR, BACKUPS_DIR
def get_user_words_count(uid):
    """User barcha so'zlarini hisoblash"""
    try:
        user_file = get_user_file(uid)
        
        if not os.path.exists(user_file):
            return 0
        
        with open(user_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        total = 0
        for topic_data in data.values():
            for section_data in topic_data.values():
                for chapter_data in section_data.values():
                    total += len(chapter_data)
        
        return total
    except:
        return 0

def create_directories():
    """Kerakli papkalarni yaratish"""
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    os.makedirs(os.path.dirname("database/"), exist_ok=True)

def get_user_file(user_id):
    """Foydalanuvchi fayl yo'lini olish"""
    return os.path.join(USER_DATA_DIR, f"user_{user_id}.json")

def create_empty_dict(user_id):
    """Bo'sh lug'at yaratish"""
    user_file = get_user_file(user_id)
    with open(user_file, 'w', encoding='utf-8') as f:
        json.dump({}, f, ensure_ascii=False, indent=4)

def load_user_data(user_id):
    user_file = get_user_file(user_id)
    
    if not os.path.exists(user_file) or os.stat(user_file).st_size == 0:
        create_empty_dict(user_id)
        return {}
    
    try:
        with open(user_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # ... qolgan eski formatni yangilash kodi ...
        return data
    except:
        return {}

def save_user_data(user_id, data):
    """Foydalanuvchi ma'lumotlarini saqlash"""
    user_file = get_user_file(user_id)
    
    try:
        # Backup yaratish
        if os.path.exists(user_file):
            backup_file = user_file + ".backup"
            with open(user_file, 'r', encoding='utf-8') as f:
                backup_data = f.read()
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(backup_data)
        
        # Yangi ma'lumotlarni saqlash
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Save error: {e}")

def is_korean(text):
    """Koreyscha matnni aniqlash"""
    return bool(re.search('[\uac00-\ud7af]', text))

def parse_multiline_words(text):
    """Ko'p qatorli so'zlarni parse qilish"""
    words = []
    lines = text.strip().splitlines()
    
    for line in lines:
        line = line.strip()
        
        if not line or line.isdigit():
            continue
        
        line_cleaned = line.replace("/", " ")
        parts = line_cleaned.split()
        
        if len(parts) < 2:
            continue
        
        korean_parts = []
        uzbek_parts = []
        
        for part in parts:
            if is_korean(part):
                korean_parts.append(part)
            else:
                uzbek_parts.append(part)
        
        if korean_parts and uzbek_parts:
            korean = ' '.join(korean_parts)
            uzbek = ' '.join(uzbek_parts)
            
            words.append({
                'korean': korean,
                'uzbek': uzbek
            })
    
    return words

def json_to_python(user_id):
    """JSON ni Python kodiga o'girish"""
    data = load_user_data(user_id)
    
    py_code = "# -*- coding: utf-8 -*-\n"
    py_code += "# LUG'AT MA'LUMOTLARI\n"
    py_code += "# Avtomatik yaratilgan fayl\n\n"
    py_code += "dictionary = {\n"
    
    for topic_key, sections in data.items():
        topic_num = topic_key.replace("Topik-", "")
        py_code += f"    # {topic_num}-TOPIK\n"
        py_code += f'    "{topic_key}": {{\n'
        
        for section_key, questions in sections.items():
            py_code += f'        "{section_key}": {{\n'
            
            for question_key, words in questions.items():
                q_num = question_key.replace("-savol so'zlari", "")
                py_code += f'            # {q_num}-savol\n'
                py_code += f'            "{question_key}": {{\n'
                
                for kr, uz in words.items():
                    py_code += f'                "{kr}": "{uz}",\n'
                
                py_code += '            },\n'
            
            py_code += '        },\n'
        
        py_code += '    },\n'
    
    py_code += '}\n'
    
    return py_code

def create_backup(user_id, backup_type, data, identifier=""):
    """Backup fayl yaratish"""
    safe_id = "".join(x for x in str(identifier) if x.isalnum() or x in ['_', '-'])
    backup_file = os.path.join(BACKUPS_DIR, f"backup_{backup_type}_{user_id}_{safe_id}.json")
    
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    return backup_file

def restore_from_backup(backup_file):
    """Backupdan tiklash"""
    if os.path.exists(backup_file):
        with open(backup_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def delete_backup(backup_file):
    """Backup faylni o'chirish"""
    try:
        if os.path.exists(backup_file):
            os.remove(backup_file)
    except:
        pass

# Papkalarni yaratish
create_directories()
