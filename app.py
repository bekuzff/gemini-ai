import os
from threading import Thread
from flask import Flask
import requests
import telebot

TELEGRAM_BOT_TOKEN = (
    os.environ.get("TELEGRAM_BOT_TOKEN")
    or "8838688583:AAGaVcFzl46v4-QHcHXanWGsAVzqYWVFxbM"
)
GEMINI_API_KEY = (
    os.environ.get("GEMINI_API_KEY")
    or "AQ.Ab8RN6KvSU0Tuj6_2Ss5xxnZ5ULaSlTdOjaqPU3Ye4bti7_a7w"
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
      "Assalomu alaykum! Men AI botiman. Savolingizni yuboring!",
  )


@bot.message_handler(func=lambda message: True)
def handle_message(message):
  try:
    # Direct REST API request using Bearer authentication
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {"contents": [{"parts": [{"text": message.text}]}]}

    response = requests.post(url, headers=headers, json=payload)
    res_data = response.json()

    if response.status_code == 200:
      text_response = res_data["candidates"][0]["content"]["parts"][0]["text"]
      bot.reply_to(message, text_response)
    else:
      # If Bearer fails, fallback to query param
      url_alt = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
      response_alt = requests.post(
          url_alt, json=payload, headers={"Content-Type": "application/json"}
      )
      res_alt_data = response_alt.json()

      if response_alt.status_code == 200:
        text_response = res_alt_data["candidates"][0]["content"]["parts"][0][
            "text"
        ]
        bot.reply_to(message, text_response)
      else:
        err_msg = res_data.get("error", {}).get(
            "message", response_alt.text
        )
        bot.reply_to(message, f"Xatolik: {err_msg}")

  except Exception as e:
    bot.reply_to(message, f"Xatolik yuz berdi: {e}")


if __name__ == "__main__":
  t = Thread(target=run_flask)
  t.daemon = True
  t.start()

  bot.infinity_polling(skip_pending=True)
