import json
import os
import random

class DictionaryHandler:
    def __init__(self, base_path):
        """
        base_path = '../DictionaryBot/user_data'
        """
        self.base_path = base_path
    
    def get_user_dict_file(self, user_id):
        """User uchun lug'at faylini olish"""
        return os.path.join(self.base_path, f"user_{user_id}.json")
    
    def load_user_data(self, user_id):
        """Foydalanuvchi lug'atini yuklash"""
        file_path = self.get_user_dict_file(user_id)
        
        if not os.path.exists(file_path):
            return {}  # Bo'sh lug'at
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def get_random_word(self, user_id, topic=None, section=None):
        """Tasodifiy so'z olish (AVTO VA ODDIY O'YIN UCHUN)"""
        data = self.load_user_data(user_id)
        all_eligible_words = []

        # Ma'lumotlarni qidirish va yig'ish
        for t_key, sections in data.items():
            # Agar muayyan topik tanlangan bo'lsa
            if topic:
                target_t_key = f"Topik-{topic.replace('-topik', '')}"
                if t_key != target_t_key:
                    continue

            for s_key, chapters in sections.items():
                # Agar muayyan bo'lim tanlangan bo'lsa
                if section and s_key != section:
                    continue

                for c_key, word_dict in chapters.items():
                    chapter_display = c_key.replace("-savol so'zlari", "") + "-savol"
                    
                    for korean, uzbek in word_dict.items():
                        all_eligible_words.append({
                            'korean': korean,
                            'uzbek': uzbek,
                            'topic': t_key.replace("Topik-", "") + "-topik",
                            'section': s_key,
                            'chapter': chapter_display
                        })

        if not all_eligible_words:
            return None

        # Tasodifiy bitta so'zni tanlab qaytarish
        return random.choice(all_eligible_words)
    
    def get_all_words(self, user_id):
        """User barcha so'zlarini olish"""
        data = self.load_user_data(user_id)
        words = []
        word_id = 1
        
        for topic_key, sections in data.items():
            for section_key, questions in sections.items():
                for question_key, word_dict in questions.items():
                    chapter = question_key.replace("-savol so'zlari", "") + "-savol"
                    for korean, uzbek in word_dict.items():
                        words.append({
                            'id': word_id,
                            'korean': korean,
                            'uzbek': uzbek,
                            'topic': topic_key,
                            'section': section_key,
                            'chapter': chapter
                        })
                        word_id += 1
        return words
    
    def get_all_topics(self, user_id):
        """User topiklar ro'yxati"""
        data = self.load_user_data(user_id)
        topics = []
        for topic_key in data.keys():
            if topic_key.startswith("Topik-"):
                topic_num = topic_key.replace("Topik-", "")
                topics.append(f"{topic_num}-topik")
        return sorted(topics, key=lambda x: int(x.replace('-topik', '')))
    
    def get_topic_sections(self, user_id, topic):
        """Topik bo'limlari"""
        data = self.load_user_data(user_id)
        topic_key = f"Topik-{topic.replace('-topik', '')}"
        if topic_key in data:
            return list(data[topic_key].keys())
        return []
    
    def get_section_chapters(self, user_id, topic, section):
        """Bo'lim savollari"""
        data = self.load_user_data(user_id)
        topic_key = f"Topik-{topic.replace('-topik', '')}"
        if topic_key in data and section in data[topic_key]:
            chapters = []
            for q_key in data[topic_key][section].keys():
                chapter = q_key.replace("-savol so'zlari", "") + "-savol"
                chapters.append(chapter)
            return sorted(chapters, key=lambda x: int(x.replace('-savol', '')))
        return []
    
    def get_chapter_words(self, user_id, topic, section, chapter):
        """Bob so'zlari (* ni olib tashlangan holda)"""
        data = self.load_user_data(user_id)
        topic_key = f"Topik-{topic.replace('-topik', '')}"
        chapter_key = chapter.replace("-savol", "") + "-savol so'zlari"
        if (topic_key in data and section in data[topic_key] and chapter_key in data[topic_key][section]):
            words = data[topic_key][section][chapter_key]
            # ⭐ * ni olib tashlash
            return {k.lstrip('*'): v.lstrip('*') for k, v in words.items()}
        return {}

    
    def get_total_words(self, user_id):
        """Jami so'zlar soni"""
        return len(self.get_all_words(user_id))
    
# ============================================
# db_handler.py - YULDUZLI SO'ZLAR FUNKSIYALARI
# Faylning OXIRIGA qo'shing (get_total_words dan keyin)
# ============================================

    def get_star_words(self, user_id):
        """Barcha yulduzli so'zlarni olish"""
        data = self.load_user_data(user_id)
        star_words = []
        word_id = 1
        
        for topic_key, sections in data.items():
            for section_key, questions in sections.items():
                for question_key, word_dict in questions.items():
                    chapter = question_key.replace("-savol so'zlari", "") + "-savol"
                    for korean, uzbek in word_dict.items():
                        # Agar koreys yoki o'zbek so'z * bilan boshlansa
                        if korean.startswith('*') or uzbek.startswith('*'):
                            star_words.append({
                                'id': word_id,
                                'korean': korean.lstrip('*'),  # * ni olib tashlash
                                'uzbek': uzbek.lstrip('*'),
                                'topic': topic_key,
                                'section': section_key,
                                'chapter': chapter,
                                'original_korean': korean,  # Original (with *)
                                'original_uzbek': uzbek
                            })
                        word_id += 1
        return star_words
    
    def get_random_star_word(self, user_id):
        """Tasodifiy yulduzli so'z olish"""
        star_words = self.get_star_words(user_id)
        if not star_words:
            return None
        return random.choice(star_words)
    
    @staticmethod
    def strip_star(text):
        """So'zdan * ni olib tashlash"""
        if isinstance(text, str):
            return text.lstrip('*')
        return text
    
    # ============================================
    # BILMAYDIGAN SO'ZLAR (** bilan belgilangan)
    # ============================================
    
    def mark_as_unknown(self, user_id, korean, uzbek, topic, section, chapter):
        """So'zni bilmaydigan deb belgilash (** qo'shish)"""
        data = self.load_user_data(user_id)
        
        # Topic formatini to'g'rilash
        if not topic.startswith("Topik-"):
            topic_key = f"Topik-{topic.replace('-topik', '')}"
        else:
            topic_key = topic
        
        # Chapter formatini to'g'rilash
        chapter_key = chapter.replace("-savol", "") + "-savol so'zlari"
        
        try:
            if topic_key in data and section in data[topic_key]:
                if chapter_key in data[topic_key][section]:
                    words = data[topic_key][section][chapter_key]
                    
                    # So'zni topish (yulduz bilan yoki yuldusiz)
                    original_key = None
                    for k in words.keys():
                        if k.lstrip('*').lstrip('*') == korean.lstrip('*').lstrip('*'):
                            original_key = k
                            break
                    
                    if original_key:
                        # Agar allaqachon ** bo'lsa, o'zgartirmaymiz
                        if not original_key.startswith('**'):
                            # Eski kalitni o'chirish va ** bilan qayta qo'shish
                            old_value = words.pop(original_key)
                            new_key = '**' + korean.lstrip('*').lstrip('*')
                            words[new_key] = old_value
                            
                            # Saqlash
                            file_path = self.get_user_dict_file(user_id)
                            with open(file_path, 'w', encoding='utf-8') as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                            return True
            return False
        except Exception as e:
            print(f"mark_as_unknown error: {e}")
            return False
    
    def get_unknown_words(self, user_id):
        """Barcha bilmaydigan so'zlarni olish (** bilan boshlanganlar)"""
        data = self.load_user_data(user_id)
        unknown_words = []
        word_id = 1
        
        for topic_key, sections in data.items():
            for section_key, questions in sections.items():
                for question_key, word_dict in questions.items():
                    chapter = question_key.replace("-savol so'zlari", "") + "-savol"
                    for korean, uzbek in word_dict.items():
                        # Agar koreys yoki o'zbek so'z ** bilan boshlansa
                        if korean.startswith('**') or uzbek.startswith('**'):
                            unknown_words.append({
                                'id': word_id,
                                'korean': korean.lstrip('*'),  # ** ni olib tashlash
                                'uzbek': uzbek.lstrip('*'),
                                'topic': topic_key,
                                'section': section_key,
                                'chapter': chapter,
                                'original_korean': korean,
                                'original_uzbek': uzbek
                            })
                        word_id += 1
        return unknown_words
    
    def get_random_unknown_word(self, user_id):
        """Tasodifiy bilmaydigan so'z olish"""
        unknown_words = self.get_unknown_words(user_id)
        if not unknown_words:
            return None
        return random.choice(unknown_words)