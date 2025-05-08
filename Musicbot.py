import os
import logging
from io import BytesIO
from typing import Dict
import sqlite3
import datetime

import requests
from pydub import AudioSegment
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, 
    CommandHandler, 
    MessageHandler, 
    Filters, 
    CallbackContext,
    CallbackQueryHandler,
    PicklePersistence
)

# Log konfiguratsiyasi
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot konfiguratsiyasi
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
LANGUAGES = {
    'uz': {'name': 'Oʻzbekcha', 'flag': '🇺🇿'},
    'ru': {'name': 'Русский', 'flag': '🇷🇺'},
    'en': {'name': 'English', 'flag': '🇬🇧'}
}
DEFAULT_LANGUAGE = 'uz'

class MusicSearchBot:
    def __init__(self):
        # SQLite bazasini ishga tushirish
        self.conn = sqlite3.connect('music_bot.db', check_same_thread=False)
        self.create_tables()
        
        # Foydalanuvchi ma'lumotlarini saqlash uchun
        self.persistence = PicklePersistence(filename='music_bot_persistence')
        
    def create_tables(self):
        """Bazada jadvallarni yaratish"""
        cursor = self.conn.cursor()
        
        # Foydalanuvchilar jadvali
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            language TEXT DEFAULT 'uz',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # So'rovlar tarixi jadvali
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            request_type TEXT,
            query TEXT,
            response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        self.conn.commit()
    
    def get_user_language(self, user_id: int) -> str:
        """Foydalanuvchi tilini olish"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else DEFAULT_LANGUAGE
    
    def set_user_language(self, user_id: int, language: str) -> None:
        """Foydalanuvchi tilini o'rnatish"""
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO users (user_id, language) VALUES (?, ?)',
            (user_id, language)
        )
        self.conn.commit()
    
    def log_request(self, user_id: int, request_type: str, query: str, response: str) -> None:
        """So'rovlarni log qilish"""
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO requests (user_id, request_type, query, response) VALUES (?, ?, ?, ?)',
            (user_id, request_type, query, response)
        self.conn.commit()
    
    def start(self, update: Update, context: CallbackContext) -> None:
        """Boshlash xabarini yuborish va tilni tanlash"""
        user_id = update.effective_user.id
        
        # Foydalanuvchini bazaga qo'shish
        self.set_user_language(user_id, DEFAULT_LANGUAGE)
        
        keyboard = [
            [
                InlineKeyboardButton(f"{LANGUAGES['uz']['flag']} Oʻzbekcha", callback_data='setlang_uz'),
                InlineKeyboardButton(f"{LANGUAGES['ru']['flag']} Русский", callback_data='setlang_ru'),
                InlineKeyboardButton(f"{LANGUAGES['en']['flag']} English", callback_data='setlang_en'),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            "Assalomu alaykum! Tilni tanlang / Здравствуйте! Выберите язык / Hello! Choose a language:",
            reply_markup=reply_markup
        )
    
    def set_language(self, update: Update, context: CallbackContext) -> None:
        """Foydalanuvchi tilini o'rnatish"""
        query = update.callback_query
        query.answer()
        
        language_code = query.data.split('_')[1]
        user_id = query.from_user.id
        self.set_user_language(user_id, language_code)
        
        # Tilga mos javob
        responses = {
            'uz': "Til oʻzgartirildi! Endi sizga Oʻzbekcha xabarlar yuboriladi.",
            'ru': "Язык изменён! Теперь вам будут приходить сообщения на русском.",
            'en': "Language changed! You'll now receive messages in English."
        }
        
        query.edit_message_text(text=responses.get(language_code, responses['uz']))
    
    def get_response(self, user_id: int, key: str) -> str:
        """Tilga mos javob olish"""
        language = self.get_user_language(user_id)
        
        responses = {
            'help': {
                'uz': "Yordam:\n\nMatn yuboring - qoʻshiqni izlash\nOvozli xabar yuboring - Shazam kabi qoʻshiqni aniqlash",
                'ru': "Помощь:\n\nОтправьте текст - поиск песни\nОтправьте голосовое сообщение - распознать песню как Shazam",
                'en': "Help:\n\nSend text - search for a song\nSend voice message - identify song like Shazam"
            },
            'search_prompt': {
                'uz': "Qoʻshiq nomi yoki ijrochini yuboring:",
                'ru': "Отправьте название песни или исполнителя:",
                'en': "Send song title or artist:"
            },
            'voice_prompt': {
                'uz': "Ovozli xabaringizni yuboring (qoʻshiqni Shazam kabi aniqlash uchun):",
                'ru': "Отправьте голосовое сообщение (для распознавания песни как Shazam):",
                'en': "Send a voice message (to identify song like Shazam):"
            },
            'searching': {
                'uz': "Qidirilmoqda...",
                'ru': "Идёт поиск...",
                'en': "Searching..."
            },
            'no_results': {
                'uz': "Hech narsa topilmadi. Boshqa soʻzlar bilan qayta urinib
