import telebot
from pytube import YouTube
import speech_recognition as sr
import os

bot = telebot.TeleBot("TOKENNI_SHUVIRGA_YOZING")

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with open('voice.ogg', 'wb') as new_file:
            new_file.write(downloaded_file)
        
        r = sr.Recognizer()
        with sr.AudioFile('voice.ogg') as source:
            audio = r.record(source)
            text = r.recognize_google(audio, language='uz-UZ')
        
        search_music(message, text)
        os.remove('voice.ogg')
        
    except Exception as e:
        bot.reply_to(message, f"Xato: {str(e)}")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    search_music(message, message.text)

def search_music(message, query):
    try:
        yt = YouTube(f"https://youtube.com/results?search_query={query}")
        stream = yt.streams.filter(only_audio=True).first()
        bot.send_audio(message.chat.id, stream.url, title=yt.title)
    except Exception as e:
        bot.reply_to(message, f"Musiqa topilmadi: {str(e)}")

print("Bot ishga tushdi...")
bot.polling()
