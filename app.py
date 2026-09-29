import os
from threading import Thread
from flask import Flask
from google import genai
import telebot

TELEGRAM_BOT_TOKEN = (
    os.environ.get("TELEGRAM_BOT_TOKEN")
    or "8838688583:AAGaVcFzl46v4-QHcHXanWGsAVzqYWVFxbM"
)
GEMINI_API_KEY = (
    os.environ.get("GEMINI_API_KEY")
    or "AQ.Ab8RN6KvSU0Tuj6_2Ss5xxnZ5ULaSlTdOjaqPU3Ye4bti7_a7w"
)

# Vertex AI SDK orqali Client yaratish
client = genai.Client(
    vertexai=True,
    project="215236478784",
    location="us-central1",
)

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask("")


@app.route("/")
def home():
  return "Bot ishlamoqda!"


def run_flask():
  port = int(os.environ.get("PORT", 8080))
  app.run(host="0.0.0.0", port=port)


@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
  bot.reply_to(
      message,
      "Assalomu alaykum! Men Gemini AI botiman. Savolingizni yuboring!",
  )


@bot.message_handler(func=lambda message: True)
def handle_message(message):
  try:
    response = client.models.generate_content(
        model="gemini-1.5-flash", contents=message.text
    )
    if response.text:
      bot.reply_to(message, response.text)
    else:
      bot.reply_to(message, "Javob olib bo'lmadi.")
  except Exception as e:
    bot.reply_to(message, f"Xatolik yuz berdi:\n{e}")


if __name__ == "__main__":
  t = Thread(target=run_flask)
  t.daemon = True
  t.start()

  bot.infinity_polling(skip_pending=True)
