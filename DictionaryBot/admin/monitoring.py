# -*- coding: utf-8 -*-
"""
MONITORING
Tizim monitoring funksiyalari
"""

import psutil
import subprocess
import json
import os
from datetime import datetime
from config import *

START_TIME = datetime.now()

def get_uptime():
    """Bot ishlash vaqti"""
    delta = datetime.now() - START_TIME
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

def get_battery():
    """Batareya holati (Termux)"""
    try:
        out = subprocess.check_output(["termux-battery-status"], timeout=5).decode()
        return json.loads(out)
    except:
        return None

def get_system_stats():
    """Tizim statistikasi"""
    stats = {}
    
    # Uptime
    stats['uptime'] = get_uptime()
    
    # Battery
    bat = get_battery()
    if bat:
        stats['battery'] = {
            'percent': bat.get('percentage', 0),
            'temperature': bat.get('temperature', 0),
            'status': bat.get('status', 'Unknown')
        }
    else:
        stats['battery'] = None
    
    # RAM
    ram = psutil.virtual_memory()
    stats['ram'] = {
        'percent': ram.percent,
        'used': ram.used // (1024**2),
        'total': ram.total // (1024**2)
    }
    
    # Dictionary size
    try:
        total_size = 0
        if os.path.exists(USER_DATA_DIR):
            for f in os.listdir(USER_DATA_DIR):
                file_path = os.path.join(USER_DATA_DIR, f)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
        
        if total_size < 1024:
            stats['dict_size'] = f"{total_size}B"
        elif total_size < 1024**2:
            stats['dict_size'] = f"{total_size / 1024:.2f}KB"
        else:
            stats['dict_size'] = f"{total_size / (1024**2):.2f}MB"
    except:
        stats['dict_size'] = "N/A"
    
    return stats

def format_system_status(user_id, stats):
    """Tizim holatini formatlab chiqarish"""
    from utils.language import get_text
    
    msg = f"<b>{get_text(user_id, 'system_status')}</b>\n"
    msg += "<b>━━━━━━━━━━━━━</b>\n\n"
    msg += f"{get_text(user_id, 'uptime', time=stats['uptime'])}\n\n"
    
    if stats['battery']:
        bat = stats['battery']
        msg += f"{get_text(user_id, 'battery', percent=bat['percent'])}\n"
        msg += f"{get_text(user_id, 'temperature', temp=bat['temperature'])}\n"
        msg += f"{get_text(user_id, 'battery_status', status=bat['status'])}\n\n"
    else:
        msg += f"{get_text(user_id, 'battery_unavailable')}\n\n"
    
    ram = stats['ram']
    msg += f"{get_text(user_id, 'ram_usage', percent=ram['percent'])}\n"
    msg += f"{get_text(user_id, 'ram_size', used=ram['used'], total=ram['total'])}\n\n"
    msg += f"{get_text(user_id, 'dict_size', size=stats['dict_size'])}"
    
    return msg

def check_battery_warning(bot, admin_id):
    """Batareya ogohlantirishini tekshirish"""
    bat = get_battery()
    if bat and bat.get('percentage', 100) <= BATTERY_WARNING_PERCENT:
        bot.send_message(admin_id, f"⚠️ Batareya {bat['percentage']}%!")

def check_ram_warning(bot, admin_id):
    """RAM ogohlantirishini tekshirish"""
    ram = psutil.virtual_memory()
    if ram.percent >= RAM_WARNING_PERCENT:
        bot.send_message(admin_id, f"⚠️ RAM {ram.percent}%!")