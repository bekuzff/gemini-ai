import os
from threading import Thread
from flask import Flask
from google import genai
import telebot

# 1. Yangi API kalitingiz va Telegram Bot Tokeningiz
GEMINI_API_KEY = "AQ.Ab8RN6LQOYs-rvffz2U2bmZNPQdAsfNINMbbc2eahLI1T7jHXw"
TELEGRAM_BOT_TOKEN = "8838688583:AAGaVcFzl46v4-QHcHXanWGsAVzqYWVFxbM"

# 2. Yangi SDK bo'yicha Gemini mijozini yaratish
client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# 3. Render o'chib qolmasligi uchun Flask server
app = Flask("")


@app.route("/")
def home():
  return "Bot ishlamoqda!"


def run_flask():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


# 4. Telegram xabarini Gemini AI'ga yuborish
@bot.message_handler(func=lambda message: True)
def handle_message(message):
  try:
    response = client.models.generate_content(
        model="gemini-1.5-flash", contents=message.text
    )
    bot.reply_to(message, response.text)
  except Exception as e:
    bot.reply_to(message, f"Xatolik:\n{e}")


if __name__ == "__main__":
  t = Thread(target=run_flask)
  t.start()
  bot.infinity_polling(skip_pending=True)
