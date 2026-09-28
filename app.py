import os
from threading import Thread
from flask import Flask
from google import genai
import telebot

# 1. Gemini va Telegram Tokenlarini kiriting
GEMINI_API_KEY = "AQ.Ab8RN6I3We6tVwHRO1Rmy9jlp3BBH06n5F5iHx7QTi_9UAED_g"
TELEGRAM_BOT_TOKEN = "8838688583:AAH4lv5JIVqRG9wFSAGIvRjW8WD39F5VxbQ"

# Gemini mijozini ishga tushirish
client = genai.Client(api_key=GEMINI_API_KEY)

# Telegram botni ishga tushirish
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Flask veb-server (Render o'chib qolmasligi uchun)
app = Flask('')


@app.route('/')
def home():
  return "Bot muvaffaqiyatli ishlamoqda!"


def run_flask():
  # Render avtomatik beradigan PORT da ishlaydi
  port = int(os.environ.get("PORT", 8080))
  app.run(host='0.0.0.0', port=port)


# Telegram xabarlarini qayta ishlash
@bot.message_handler(func=lambda message: True)
def handle_message(message):
  try:
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=message.text,
    )
    bot.reply_to(message, response.text)
  except Exception as e:
    bot.reply_to(message, "Xatolik yuz berdi. Qaytadan urinib ko'ring.")


if __name__ == "__main__":
  # Flask serverni alohida oqimda ishga tushiramiz
  t = Thread(target=run_flask)
  t.start()

  # Botni uzluksiz eshitish rejimiga tushiramiz
  bot.infinity_polling()
