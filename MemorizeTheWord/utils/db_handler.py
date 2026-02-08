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
        """Bob so'zlari"""
        data = self.load_user_data(user_id)
        topic_key = f"Topik-{topic.replace('-topik', '')}"
        chapter_key = chapter.replace("-savol", "") + "-savol so'zlari"
        if (topic_key in data and section in data[topic_key] and chapter_key in data[topic_key][section]):
            return data[topic_key][section][chapter_key]
        return {}
    
    def get_total_words(self, user_id):
        """Jami so'zlar soni"""
        return len(self.get_all_words(user_id))