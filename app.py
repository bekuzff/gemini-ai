import os
from threading import Thread
from flask import Flask
from google import genai
import telebot

# 1. Gemini va Telegram Tokenlari
GEMINI_API_KEY = "AQ.Ab8RN6JGl7IOngCjEaiNEMyUQDfQ8NB3qhNBfYU1EM1bjdo73A"
TELEGRAM_BOT_TOKEN = "8838688583:AAGN_uMCIJDIzEasTyWQyrcUofSQlCBh3n8"

# Gemini mijozini ishga tushirish
client = genai.Client(api_key=GEMINI_API_KEY)

# Telegram botni ishga tushirish
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Flask veb-server (Render uchun)
app = Flask("")


@app.route("/")
def home():
  return "Bot muvaffaqiyatli ishlamoqda!"


def run_flask():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


# Telegram xabarlarini qayta ishlash
@bot.message_handler(func=lambda message: True)
def handle_message(message):
  try:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=message.text,
    )
    bot.reply_to(message, response.text)
  except Exception as e:
    bot.reply_to(message, "Xatolik yuz berdi. Qaytadan urinib ko'ring.")


if __name__ == "__main__":
  t = Thread(target=run_flask)
  t.start()
  bot.infinity_polling()
