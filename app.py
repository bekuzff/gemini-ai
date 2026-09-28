import os
from threading import Thread
from flask import Flask
import google.generativeai as genai
import telebot

# 1. API va Tokenlar
GEMINI_API_KEY = "AQ.Ab8RN6JGl7IOngCjEaiNEMyUQDfQ8NB3qhNBfYU1EM1bjdo73A"
TELEGRAM_BOT_TOKEN = "8838688583:AAGN_uMCIJDIzEasTyWQyrcUofSQlCBh3n8"

# 2. Sozlamalar
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# 3. Render uchun Flask server
app = Flask("")


@app.route("/")
def home():
  return "Bot muvaffaqiyatli ishlamoqda!"


def run_flask():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


# 4. Telegram xabarlariga javob berish
@bot.message_handler(func=lambda message: True)
def handle_message(message):
  try:
    response = model.generate_content(message.text)
    bot.reply_to(message, response.text)
  except Exception as e:
    print(f"Xatolik: {e}")
    bot.reply_to(message, "Xatolik yuz berdi. Qaytadan urinib ko'ring.")


if __name__ == "__main__":
  t = Thread(target=run_flask)
  t.start()
  bot.infinity_polling()
