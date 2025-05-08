import telebot
import os
import requests
import json
from pydub import AudioSegment
import speech_recognition as sr

bot = telebot.TeleBot("YOUR_TELEGRAM_TOKEN_HERE")

# AudD API uchun (https://audd.io/)
AUDD_API_KEY = "YOUR_AUDD_API_KEY"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🎵 Salom! Menga musiqaning 10-15 soniyalik qismini yuboring, men uni tanib, to'liq ma'lumotini topib beraman!")

@bot.message_handler(content_types=['voice', 'audio'])
def handle_audio(message):
    try:
        # Ovozli xabarni yuklab olish
        if message.voice:
            file_info = bot.get_file(message.voice.file_id)
            file_ext = 'ogg'
        else:
            file_info = bot.get_file(message.audio.file_id)
            file_ext = message.audio.file_name.split('.')[-1]
        
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Faylga saqlash
        audio_file = f'audio.{file_ext}'
        with open(audio_file, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        # Agar OGG formatida bo'lsa, MP3 ga o'tkazamiz
        if file_ext == 'ogg':
            audio = AudioSegment.from_ogg(audio_file)
            audio.export('audio.mp3', format='mp3')
            audio_file = 'audio.mp3'
        
        # AudD API orqali musiqa tanib olish
        with open(audio_file, 'rb') as f:
            files = {'file': f}
            data = {
                'api_token': AUDD_API_KEY,
                'return': 'apple_music,spotify',
                'language': 'en,ru,uz'
            }
            response = requests.post('https://api.audd.io/', data=data, files=files)
        
        result = json.loads(response.text)
        
        if result['status'] == 'success' and result['result']:
            song = result['result']
            reply = f"🎶 Topilgan musiqa:\n\n"
            reply += f"📌 Nomi: {song['title']}\n"
            reply += f"👨‍🎤 Ijrochi: {song['artist']}\n"
            reply += f"⏳ Davomiyligi: {song['song_length']} soniya\n"
            reply += f"📅 Chiqarilgan yili: {song['release_date'] or 'Nomaʼlum'}\n\n"
            
            if 'apple_music' in song:
                reply += f"🍎 Apple Music: {song['apple_music']['url']}\n"
            if 'spotify' in song:
                reply += f"🟢 Spotify: {song['spotify']['external_urls']['spotify']}\n"
            
            # Topilgan musiqaning 10 ta versiyasini qidirish
            search_url = f"https://api.audd.io/findLyrics/?q={song['title']} {song['artist']}&api_token={AUDD_API_KEY}"
            search_response = requests.get(search_url)
            search_results = json.loads(search_response.text)
            
            if search_results['status'] == 'success' and search_results['result']:
                reply += "\n🔍 Topilgan versiyalar:\n"
                for i, version in enumerate(search_results['result'][:10], 1):  # Faqat 10 ta versiya
                    reply += f"{i}. {version['title']} - {version['artist']} ({version['album']})\n"
            
            bot.reply_to(message, reply)
        else:
            bot.reply_to(message, "❌ Musiqani tanib bo'lmadi. Iltimos, yana bir bor urinib ko'ring!")
    
    except Exception as e:
        bot.reply_to(message, f"⚠️ Xatolik yuz berdi: {str(e)}")

if __name__ == '__main__':
    bot.polling(none_stop=True)
