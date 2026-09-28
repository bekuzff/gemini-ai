import os
from threading import Thread
from flask import Flask
from google import genai
import telebot

# Bot tokeni va Gemini API kaliti
TELEGRAM_BOT_TOKEN = "8838688583:AAH4lv5JIVqRG9wFSAGIvRjW8WD39F5VxbQ"
GEMINI_API_KEY = "AQ.Ab8RN6I3We6tVwHRO1Rmy9jlp3BBH06n5F5iHx7QTi_9UAED_g"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

# Render serveri to'xtab qolmasligi uchun Flask veb-server
app = Flask(__name__)


@app.route("/")
def home():
    return "Bot muvaffaqiyatli ishlamoqda!"


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


# /start komandasi
@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(
        message,
        "Assalomu alaykum! Men Gemini Sun'iy Intellekt boti bo'laman. Menga xohlagan savolingizni bering!",
    )


# Har qanday matnli xabarga AI javob beradi
@bot.message_handler(func=lambda message: True)
def handle_ai_response(message):
    bot.send_chat_action(message.chat.id, "typing")

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=message.text
        )
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(
            message,
            "Xatolik yuz berdi. Iltimos, birozdan so'ng qayta urinib ko'ring.",
        )
        print(f"Xatolik: {e}")


if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()

    print("Bot serverda ishga tushdi...")
    bot.polling(non_stop=True)