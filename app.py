import os
from threading import Thread
from flask import Flask
import google.generativeai as genai
import telebot

GEMINI_API_KEY = "AQ.Ab8RN6JGl7IOngCjEaiNEMyUQDfQ8NB3qhNBfYU1EM1bjdo73A"
TELEGRAM_BOT_TOKEN = "8838688583:AAGaVcFzl46v4-QHcHXanWGsAVzqYWVFxbM"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

app = Flask("")


@app.route("/")
def home():
  return "Bot ishlamoqda!"


def run_flask():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


@bot.message_handler(func=lambda message: True)
def handle_message(message):
  try:
    response = model.generate_content(message.text)
    bot.reply_to(message, response.text)
  except Exception as e:
    # Aniq xatolikni Telegram'ning o'ziga yozib yuboradi:
    bot.reply_to(
        message, f"Xatolik kodi:\n{str(e)[:500]}"
    )  # juda uzun bo'lsa kesib ko'rsatadi


if __name__ == "__main__":
  t = Thread(target=run_flask)
  t.start()
  bot.infinity_polling()
