import os
import sqlite3
from threading import Thread
from flask import Flask
import telebot
from telebot import types

TOKEN = "8838688583:AAGaVcFzl46v4-QHcHXanWGsAVzqYWVFxbM"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)


# --- BAZANI SOZLASH ---
def init_db():
  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            phone_number TEXT,
            points INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS voices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            file_id TEXT,
            votes INTEGER DEFAULT 0
        )
    """)
  conn.commit()
  conn.close()


init_db()


# --- FLASK SERVER (Render uchun) ---
@app.route("/")
def home():
  return "Ovoz Battle Bot Ishlamoqda!"


def run_flask():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


# --- START VA RO'YXATDAN O'TISH ---
user_states = {}


@bot.message_handler(commands=["start"])
def start_cmd(message):
  user_id = message.from_user.id

  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT full_name, phone_number FROM users WHERE user_id = ?", (user_id,)
  )
  user = cursor.fetchone()
  conn.close()

  # Agar foydalanuvchi to'liq ro'yxatdan o'tgan bo'lsa
  if user and user[0] and user[1]:
    show_main_menu(message)
  else:
    # Ro'yxatdan o'tish bosqichi
    user_states[user_id] = "waiting_for_name"
    bot.send_message(
        message.chat.id,
        "Assalomu alaykum! Ovoz Battle botiga xush kelibsiz.\n\n"
        "Botdan foydalanish uchun ro'yxatdan o me'tosiz.\n"
        "Iltimos, **Ism va Familiyangizni** kiriting:",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove(),
    )


# Ism qabul qilish
@bot.message_handler(
    func=lambda msg: user_states.get(msg.from_user.id) == "waiting_for_name"
)
def get_name(message):
  user_id = message.from_user.id
  full_name = message.text.strip()

  user_states[user_id] = {"name": full_name, "state": "waiting_for_phone"}

  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
  btn_phone = types.KeyboardButton(
      "📱 Telefon raqamni yuborish", request_contact=True
  )
  markup.add(btn_phone)

  bot.send_message(
      message.chat.id,
      f"Rahmat, {full_name}!\nEndi pastdagi tugmani bosib **telefon raqamingizni** yuboring:",
      parse_mode="Markdown",
      reply_markup=markup,
  )


# Kontakt qabul qilish
@bot.message_handler(
    content_types=["contact"],
    func=lambda msg: isinstance(user_states.get(msg.from_user.id), dict)
    and user_states[msg.from_user.id].get("state") == "waiting_for_phone",
)
def get_contact(message):
  user_id = message.from_user.id
  full_name = user_states[user_id]["name"]
  phone_number = message.contact.phone_number
  username = (
      message.from_user.username
      or message.from_user.first_name
      or f"User_{user_id}"
  )

  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT INTO users (user_id, username, full_name, phone_number)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,
            full_name=excluded.full_name,
            phone_number=excluded.phone_number
    """,
      (user_id, username, full_name, phone_number),
  )
  conn.commit()
  conn.close()

  del user_states[user_id]

  bot.send_message(
      message.chat.id,
      "✅ **Ro'yxatdan muvaffaqiyatli o'tdingiz!**",
      parse_mode="Markdown",
  )
  show_main_menu(message)


# Asosiy menyu
def show_main_menu(message):
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
  markup.add("🎤 Ovoz yuborish", "🥊 Battle'ga kirish")
  markup.add("🏆 Top 10 Reyting", "👤 Profilim")

  bot.send_message(
      message.chat.id, "Kerakli bo'limni tanlang:", reply_markup=markup
  )


# --- BOT FUNKSIYALARI ---


# Ovozli xabar qabul qilish
@bot.message_handler(content_types=["voice", "audio"])
def handle_voice(message):
  user_id = message.from_user.id
  file_id = (
      message.voice.file_id
      if message.content_type == "voice"
      else message.audio.file_id
  )

  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO voices (user_id, file_id) VALUES (?, ?)", (user_id, file_id)
  )
  conn.commit()
  conn.close()

  bot.reply_to(
      message,
      "✅ Ovozli xabaringiz qabul qilindi va battle ro'yxatiga qo'shildi!",
  )


@bot.message_handler(func=lambda msg: msg.text == "🎤 Ovoz yuborish")
def send_voice_info(message):
  bot.send_message(
      message.chat.id,
      "Ashula aytgan yoki ovozli xabaringizni (Voice) ushbu chatga yuboring.",
  )


# Battle jarayoni
@bot.message_handler(func=lambda msg: msg.text == "🥊 Battle'ga kirish")
def start_battle(message):
  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT id, file_id, votes FROM voices ORDER BY RANDOM() LIMIT 2"
  )
  battle_data = cursor.fetchall()
  conn.close()

  if len(battle_data) < 2:
    bot.send_message(
        message.chat.id,
        "⚠️ Battle boshlash uchun bazada kamida 2 ta ovoz bo'lishi kerak. Avval 'Ovoz yuborish' tugmasi orqali ovoz yuklang!",
    )
    return

  voice1, voice2 = battle_data[0], battle_data[1]

  bot.send_message(
      message.chat.id,
      "🔥 **Qaysi ovoz ijrosi yaxshiroq? Eshiting va munosibiga ovoz bering!**",
      parse_mode="Markdown",
  )

  bot.send_voice(message.chat.id, voice1[1], caption="🔊 1-Ishtirokchi")
  bot.send_voice(message.chat.id, voice2[1], caption="🔊 2-Ishtirokchi")

  markup = types.InlineKeyboardMarkup()
  btn1 = types.InlineKeyboardButton(
      f"🔴 1-Ishtirokchiga ({voice1[2]} ball)", callback_data=f"vote_{voice1[0]}"
  )
  btn2 = types.InlineKeyboardButton(
      f"🔵 2-Ishtirokchiga ({voice2[2]} ball)", callback_data=f"vote_{voice2[0]}"
  )
  markup.add(btn1, btn2)

  bot.send_message(
      message.chat.id, "Ovozingizni tanlang:", reply_markup=markup
  )


# Ovoz berish tugmasi
@bot.callback_query_handler(func=lambda call: call.data.startswith("vote_"))
def handle_vote(call):
  voice_id = int(call.data.split("_")[1])

  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute(
      "UPDATE voices SET votes = votes + 1 WHERE id = ?", (voice_id,)
  )

  cursor.execute("SELECT user_id FROM voices WHERE id = ?", (voice_id,))
  user_res = cursor.fetchone()
  if user_res:
    cursor.execute(
        "UPDATE users SET points = points + 10 WHERE user_id = ?",
        (user_res[0],),
    )

  conn.commit()
  conn.close()

  bot.answer_callback_query(call.id, "✅ Ovozingiz hisobga olindi (+10 ball)!")
  bot.edit_message_text(
      "Rahmat! Ovozingiz muvaffaqiyatli qabul qilindi.",
      call.message.chat.id,
      call.message.message_id,
  )


# Profil statistikasi
@bot.message_handler(func=lambda msg: msg.text == "👤 Profilim")
def show_profile(message):
  user_id = message.from_user.id
  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT full_name, phone_number, points, wins FROM users WHERE user_id ="
      " ?",
      (user_id,),
  )
  user = cursor.fetchone()
  conn.close()

  if user:
    full_name, phone, points, wins = user
    text = (
        f"👤 **Sizning profilingiz:**\n\n"
        f"👤 Ism: {full_name}\n"
        f"📞 Tel: {phone}\n"
        f"⭐ Ballaringiz: {points}\n"
        f"🏆 G'alabalar: {wins}"
    )
  else:
    text = "Siz hali ro'yxatdan o'tmagansiz. /start tugmasini bosing."

  bot.send_message(message.chat.id, text, parse_mode="Markdown")


# Reyting
@bot.message_handler(func=lambda msg: msg.text == "🏆 Top 10 Reyting")
def show_leaderboard(message):
  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT full_name, points FROM users WHERE full_name IS NOT NULL ORDER BY"
      " points DESC LIMIT 10"
  )
  top_users = cursor.fetchall()
  conn.close()

  text = "🏆 **ENG YAXSHI OVOZ EGALARI (TOP 10)** 🏆\n\n"
  for i, (full_name, points) in enumerate(top_users, 1):
    text += f"{i}. {full_name} — {points} ball\n"

  bot.send_message(message.chat.id, text, parse_mode="Markdown")


if __name__ == "__main__":
  t = Thread(target=run_flask)
  t.daemon = True
  t.start()

  bot.infinity_polling(skip_pending=True)
