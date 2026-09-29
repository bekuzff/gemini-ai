import os
from threading import Thread
from flask import Flask
from google import genai
import telebot

GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY", "AQ.Ab8RN6JwyrnbWF0sSI_Dfilmd2KJ50aRbOdn6yF6RZ_ittP8xQ"
)
TELEGRAM_BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN", "8838688583:AAGaVcFzl46v4-QHcHXanWGsAVzqYWVFxbM"
)

client = genai.Client(api_key=GEMINI_API_KEY)
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
    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=message.text
    )
    bot.reply_to(message, response.text)
  except Exception as e:
    bot.reply_to(message, f"Xatolik:\n{e}")


if __name__ == "__main__":
  t = Thread(target=run_flask)
  t.start()
  bot.infinity_polling(skip_pending=True)
