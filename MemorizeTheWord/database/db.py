import aiosqlite
import os
from datetime import datetime
from typing import Optional, List, Tuple

class UserDatabase:
    """Foydalanuvchilar statistikasi uchun SQLite database"""
    async def get_word_statistics(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT category, sub_category, korean, asked_count
                FROM words
                ORDER BY asked_count ASC
            """) as cursor:
                return await cursor.fetchall()


    async def get_all_users(self):
        query = """
        SELECT 
            u.user_id,
            u.username,
            u.first_name,
            s.correct_answers,
            s.wrong_answers,
            u.is_blocked
        FROM users u
        LEFT JOIN statistics s ON u.user_id = s.user_id
        ORDER BY s.correct_answers DESC
        """

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query) as cursor:
                rows = await cursor.fetchall()

        users = []
        for row in rows:
            users.append({
                "user_id": row[0],
                "username": row[1],
                "first_name": row[2],
                "correct": row[3] or 0,
                "wrong": row[4] or 0,
                "is_blocked": bool(row[5]),
            })

        return users


    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    async def init_db(self):
        """Database jadvallarini yaratish"""
        async with aiosqlite.connect(self.db_path) as db:
            # 1. Users jadvali
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    language TEXT DEFAULT 'uz',
                    is_blocked INTEGER DEFAULT 0,
                    block_reason TEXT,
                    created_at TEXT,
                    last_active TEXT
                )
            ''')
            
            # 2. Statistics jadvali
            await db.execute('''
                CREATE TABLE IF NOT EXISTS statistics (
                    user_id INTEGER PRIMARY KEY,
                    correct_answers INTEGER DEFAULT 0,
                    wrong_answers INTEGER DEFAULT 0,
                    active_time INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

            # 3. Words jadvali (So'zlar bazasi va Global statistika)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    korean TEXT NOT NULL,
                    uzbek TEXT NOT NULL,
                    category TEXT,
                    sub_category TEXT,
                    asked_count INTEGER DEFAULT 0
                )
            ''')
            
            # 4. Word tracking jadvali (Userlar uchun takrorlanish nazorati)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS word_tracking (
                    user_id INTEGER,
                    word_id INTEGER,
                    times_asked INTEGER DEFAULT 0,
                    last_asked TEXT,
                    PRIMARY KEY (user_id, word_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # 5. Admin jadvali
            await db.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    added_at TEXT
                )
            ''')

            # Mavjud bazaga asked_count ustunini qo'shish (agar bo'lmasa)
            try:
                await db.execute('ALTER TABLE words ADD COLUMN asked_count INTEGER DEFAULT 0')
            except aiosqlite.OperationalError:
                pass
            
            await db.commit()
        

    async def increment_word_count(self, word_id: int):
        """So'z so'ralganda uning global hisoblagichini +1 qiladi"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE words SET asked_count = asked_count + 1 WHERE id = ?",
                (word_id,)
            )
            await db.commit()

    async def get_words_sorted_by_usage(self):
        """So'zlarni so'ralish soni bo'yicha kamdan ko'pga saralab olish"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM words ORDER BY asked_count ASC") as cursor:
                return await cursor.fetchall()

    async def add_user(self, user_id: int, username: str, first_name: str):
        """Yangi foydalanuvchi qo'shish"""
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now().isoformat()
            await db.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, created_at, last_active)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, now, now))
            
            await db.execute('''
                INSERT OR IGNORE INTO statistics (user_id)
                VALUES (?)
            ''', (user_id,))
            await db.commit()

    async def update_last_active(self, user_id: int):
        """Oxirgi faollik vaqtini yangilash"""
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now().isoformat()
            await db.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (now, user_id))
            await db.commit()

    async def set_language(self, user_id: int, language: str):
        """Foydalanuvchi tilini o'zgartirish"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
            await db.commit()

    async def get_language(self, user_id: int) -> str:
        """Foydalanuvchi tilini olish"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT language FROM users WHERE user_id = ?', (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 'uz'

    async def is_blocked(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """Foydalanuvchi bloklanganmi?"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT is_blocked, block_reason FROM users WHERE user_id = ?', (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return bool(row[0]), row[1]
                return False, None

    async def block_user(self, user_id: int, reason: str = None):
        """Foydalanuvchini bloklash"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('UPDATE users SET is_blocked = 1, block_reason = ? WHERE user_id = ?', (reason, user_id))
            await db.commit()

    async def unblock_user(self, user_id: int):
        """Foydalanuvchini blokdan chiqarish"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('UPDATE users SET is_blocked = 0, block_reason = NULL WHERE user_id = ?', (user_id,))
            await db.commit()

    async def update_statistics(self, user_id: int, is_correct: bool, time_spent: int):
        """Statistikani yangilash"""
        async with aiosqlite.connect(self.db_path) as db:
            if is_correct:
                await db.execute('UPDATE statistics SET correct_answers = correct_answers + 1, active_time = active_time + ? WHERE user_id = ?', (time_spent, user_id))
            else:
                await db.execute('UPDATE statistics SET wrong_answers = wrong_answers + 1, active_time = active_time + ? WHERE user_id = ?', (time_spent, user_id))
            await db.commit()

    async def get_statistics(self, user_id: int) -> dict:
        """Foydalanuvchi statistikasini olish"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT correct_answers, wrong_answers, active_time FROM statistics WHERE user_id = ?', (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {'correct': row[0], 'wrong': row[1], 'active_time': row[2]}
                return {'correct': 0, 'wrong': 0, 'active_time': 0}

    async def get_ranking(self, user_id: int) -> Tuple[int, int]:
        """Reytingni olish"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT COUNT(*) FROM users') as cursor:
                total = (await cursor.fetchone())[0]
            
            async with db.execute('''
                SELECT COUNT(*) + 1 FROM statistics 
                WHERE correct_answers > (SELECT correct_answers FROM statistics WHERE user_id = ?)
            ''', (user_id,)) as cursor:
                rank = (await cursor.fetchone())[0]
            return rank, total

    async def track_word(self, user_id: int, word_id: int):
        """User uchun so'zni track qilish"""
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now().isoformat()
            await db.execute('''
                INSERT INTO word_tracking (user_id, word_id, times_asked, last_asked)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(user_id, word_id) DO UPDATE SET
                    times_asked = times_asked + 1,
                    last_asked = ?
            ''', (user_id, word_id, now, now))
            await db.commit()

    async def get_least_asked_words(self, user_id: int, limit: int = 10) -> List[int]:
        """User uchun eng kam so'ralgan so'zlar"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT word_id FROM word_tracking 
                WHERE user_id = ? 
                ORDER BY times_asked ASC, last_asked ASC 
                LIMIT ?
            ''', (user_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def get_total_users(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT COUNT(*) FROM users') as cursor:
                return (await cursor.fetchone())[0]

    async def is_admin(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT 1 FROM admins WHERE user_id = ?', (user_id,)) as cursor:
                return await cursor.fetchone() is not None

    async def add_admin(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now().isoformat()
            await db.execute('INSERT OR IGNORE INTO admins (user_id, added_at) VALUES (?, ?)', (user_id, now))
            await db.commit()
            
    