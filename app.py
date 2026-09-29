import os
import sqlite3
from threading import Thread
from flask import Flask
import telebot
from telebot import types

TOKEN = "8975900358:AAHXIncD_ZCXFeNzw3rVTH-JYrzl8CoSkG4"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- ASOSIY SOZLAMALAR ---
ADMIN_ID = 8268380280  # Egasi / Asosiy Admin ID


# --- BAZANI SOZLASH ---
def init_db():
  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  # Foydalanuvchilar
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            phone_number TEXT,
            points INTEGER DEFAULT 0
        )
    """)
  # Ovozlar
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS voices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            file_id TEXT,
            votes INTEGER DEFAULT 0
        )
    """)
  # Foydalanuvchilarning o'z kanallari
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            channel_username TEXT
        )
    """)
  # Majburiy obuna kanallari jadvali
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS required_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_username TEXT UNIQUE
        )
    """)
  # Bot sozlamalari (Majburiy obuna holati: on / off)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
  cursor.execute(
      "INSERT OR IGNORE INTO settings (key, value) VALUES ('sub_status',"
      " 'off')"
  )
  conn.commit()
  conn.close()


init_db()


# --- SOZLAMALARNI TEKSHIRISH ---
def get_sub_status():
  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute("SELECT value FROM settings WHERE key = 'sub_status'")
  res = cursor.fetchone()
  conn.close()
  return res[0] if res else "off"


def set_sub_status(status):
  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute(
      "UPDATE settings SET value = ? WHERE key = 'sub_status'", (status,)
  )
  conn.commit()
  conn.close()


def get_required_channels():
  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute("SELECT channel_username FROM required_channels")
  channels = [row[0] for row in cursor.fetchall()]
  conn.close()
  return channels


def check_sub(user_id):
  if get_sub_status() == "off":
    return True
  channels = get_required_channels()
  if not channels:
    return True
  for channel in channels:
    try:
      member = bot.get_chat_member(channel, user_id)
      if member.status in ["left", "kicked"]:
        return False
    except Exception:
      continue
  return True


def send_sub_message(chat_id):
  channels = get_required_channels()
  if not channels:
    return
  markup = types.InlineKeyboardMarkup()
  for channel in channels:
    btn = types.InlineKeyboardButton(
        text=f"A'zo bo'lish 📢 {channel}",
        url=f"https://t.me/{channel.replace('@', '')}",
    )
    markup.add(btn)
  markup.add(
      types.InlineKeyboardButton(
          text="✅ Tekshirish", callback_data="check_subscription"
      )
  )

  bot.send_message(
      chat_id,
      "⚠️ **Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:**",
      parse_mode="Markdown",
      reply_markup=markup,
  )


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

  # Start orqali ovoz berish uchun kelgan bo'lsa
  if len(message.text.split()) > 1:
    param = message.text.split()[1]
    if param.startswith("vote_"):
      voice_id = int(param.split("_")[1])
      if not check_sub(user_id):
        send_sub_message(message.chat.id)
        return

      conn = sqlite3.connect("battle.db")
      cursor = conn.cursor()
      cursor.execute(
          "UPDATE voices SET votes = votes + 1 WHERE id = ?", (voice_id,)
      )
      cursor.execute(
          "SELECT user_id FROM voices WHERE id = ?", (voice_id,)
      )
      res = cursor.fetchone()
      if res:
        cursor.execute(
            "UPDATE users SET points = points + 10 WHERE user_id = ?",
            (res[0],),
        )
      conn.commit()
      conn.close()

      bot.send_message(
          message.chat.id,
          "✅ **Ovozingiz muvaffaqiyatli qabul qilindi!** (+10 ball)",
          parse_mode="Markdown",
      )
      return

  if not check_sub(user_id):
    send_sub_message(message.chat.id)
    return

  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT full_name, phone_number FROM users WHERE user_id = ?", (user_id,)
  )
  user = cursor.fetchone()
  conn.close()

  if user and user[0] and user[1]:
    show_main_menu(message)
  else:
    user_states[user_id] = "waiting_for_name"
    bot.send_message(
        message.chat.id,
        "Assalomu alaykum! Ovoz Battle botiga xush kelibsiz.\n\n"
        "Iltimos, **Ism va Familiyangizni** kiriting:",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove(),
    )


@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def callback_check_sub(call):
  if check_sub(call.from_user.id):
    bot.answer_callback_query(call.id, "✅ Rahmat! Kanallarga a'zo bo'ldingiz.")
    try:
      bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
      pass
    show_main_menu(call.message)
  else:
    bot.answer_callback_query(
        call.id, "❌ Hamma kanalga a'zo bo'lmadingiz!", show_alert=True
    )


@bot.message_handler(
    func=lambda msg: user_states.get(msg.from_user.id) == "waiting_for_name"
)
def get_name(message):
  user_id = message.from_user.id
  user_states[user_id] = {"name": message.text.strip(), "state": "phone"}

  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
  markup.add(
      types.KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)
  )
  bot.send_message(
      message.chat.id, "Endi telefon raqamingizni yuboring:", reply_markup=markup
  )


@bot.message_handler(
    content_types=["contact"],
    func=lambda msg: isinstance(user_states.get(msg.from_user.id), dict),
)
def get_contact(message):
  user_id = message.from_user.id
  full_name = user_states[user_id]["name"]
  phone = message.contact.phone_number
  username = message.from_user.username or f"User_{user_id}"

  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT INTO users (user_id, username, full_name, phone_number)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET full_name=excluded.full_name, phone_number=excluded.phone_number
    """,
      (user_id, username, full_name, phone),
  )
  conn.commit()
  conn.close()

  del user_states[user_id]
  bot.send_message(
      message.chat.id, "✅ Muvaffaqiyatli ro'yxatdan o'tdingiz!"
  )
  show_main_menu(message)


def show_main_menu(message):
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  markup.add("🎤 Ovoz yuborish", "🥊 Battle'ga kirish")
  markup.add("🏆 Top 10 Reyting", "👤 Profilim")
  markup.add("📢 Mening Kanalimni Ulash", "🚀 Kanalga Battle Chiqarish")

  if message.from_user.id == ADMIN_ID:
    markup.add("👑 Admin Panel")

  bot.send_message(message.chat.id, "Asosiy menyu:", reply_markup=markup)


# --- FOYDALANUVCHINING O'Z KANALINI ULASHI ---
@bot.message_handler(func=lambda msg: msg.text == "📢 Mening Kanalimni Ulash")
def ask_user_channel(message):
  user_states[message.from_user.id] = "waiting_to_add_channel"
  bot.send_message(
      message.chat.id,
      "📢 Kanalingiz usernamesini yuboring (Masalan: `@kanal_nomi`).\n\n"
      "⚠️ *Eslatma:* Botni kanalingizga **Administrator** qilib qo'shgan bo'lishingiz shart!",
      parse_mode="Markdown",
      reply_markup=types.ReplyKeyboardRemove(),
  )


@bot.message_handler(
    func=lambda msg: user_states.get(msg.from_user.id)
    == "waiting_to_add_channel"
)
def save_user_channel(message):
  user_id = message.from_user.id
  channel_username = message.text.strip()
  del user_states[user_id]

  try:
    chat_member = bot.get_chat_member(channel_username, bot.get_me().id)
    if chat_member.status not in ["administrator", "creator"]:
      bot.send_message(
          message.chat.id,
          "❌ Xatolik! Bot ko'rsatilgan kanalda **Administrator emas**.\n"
          "Iltimos, botni kanalga admin qilib, qaytadan urinib ko'ring.",
      )
      show_main_menu(message)
      return
  except Exception as e:
    bot.send_message(
        message.chat.id,
        f"❌ Kanal topilmadi yoki xatolik yuz berdi: {e}\n"
        "Kanal username to'g'riligini va bot adminligini tekshiring.",
    )
    show_main_menu(message)
    return

  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO user_channels (user_id, channel_username) VALUES (?, ?)",
      (user_id, channel_username),
  )
  conn.commit()
  conn.close()

  bot.send_message(
      message.chat.id,
      f"✅ Kanal muvaffaqiyatli ulandi: **{channel_username}**",
      parse_mode="Markdown",
  )
  show_main_menu(message)


# --- KANALGA BATTLE CHIQARISH ---
@bot.message_handler(func=lambda msg: msg.text == "🚀 Kanalga Battle Chiqarish")
def select_channel_for_battle(message):
  user_id = message.from_user.id
  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT channel_username FROM user_channels WHERE user_id = ?",
      (user_id,),
  )
  channels = cursor.fetchall()
  conn.close()

  if not channels and user_id != ADMIN_ID:
    bot.send_message(
        message.chat.id,
        "⚠️ Siz hali botga hech qanday kanal ulamagansiz!\n"
        "Avval **'📢 Mening Kanalimni Ulash'** tugmasini bosing.",
    )
    return

  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
  for ch in channels:
    markup.add(ch[0])
  markup.add("🔙 Orqaga")

  user_states[user_id] = "selecting_channel_for_battle"
  bot.send_message(
      message.chat.id,
      "Qaysi kanalingizga battle chiqarishni xohlaysiz? Kanalni tanlang:",
      reply_markup=markup,
  )


@bot.message_handler(
    func=lambda msg: user_states.get(msg.from_user.id)
    == "selecting_channel_for_battle"
)
def post_battle_to_user_channel(message):
  user_id = message.from_user.id
  if message.text == "🔙 Orqaga":
    del user_states[user_id]
    show_main_menu(message)
    return

  target_channel = message.text.strip()
  del user_states[user_id]

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
        "⚠️ Bazada battle uchun ovozlar yetarli emas (kamida 2 ta kerak)!",
    )
    show_main_menu(message)
    return

  voice1, voice2 = battle_data[0], battle_data[1]
  bot_username = bot.get_me().username

  caption_text = (
      "3️⃣〰️🔠🔠🔠🔠🔠🔠🔠👑\n\n"
      "👑👑👑👑⚡👑👑👑👑\n\n"
      "<b>TOP 1 = 1 NFT / G'ALABA!</b> 🔥\n\n"
      "🗣 <b>Eshiting va o'zingizga yoqqan ishtirokchiga ovoz bering!</b>\n\n"
      "👇 Qatnashish va ovoz berish uchun pastdagi tugmani bosing:"
  )

  markup = types.InlineKeyboardMarkup()
  btn = types.InlineKeyboardButton(
      "📝 Qatnashish",
      url=f"https://t.me/{bot_username}?start=vote_{voice1[0]}",
  )
  markup.add(btn)

  try:
    bot.send_message(
        target_channel, caption_text, parse_mode="HTML", reply_markup=markup
    )
    bot.send_message(
        message.chat.id,
        f"✅ Battle muvaffaqiyatli **{target_channel}** kanalingizga chiqarildi!",
        parse_mode="Markdown",
    )
  except Exception as e:
    bot.send_message(
        message.chat.id,
        f"❌ Xatolik! Bot ko'rsatilgan kanalda admin emas yoki xato kiritildi.\nXato: {e}",
    )

  show_main_menu(message)


# --- ADMIN PANEL ---
@bot.message_handler(func=lambda msg: msg.text == "👑 Admin Panel")
def admin_panel_menu(message):
  if message.from_user.id != ADMIN_ID:
    return
  sub_status = "🟢 Yoqilgan" if get_sub_status() == "on" else "🔴 O'chirilgan"

  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  markup.add(f"Majburiy obuna: {sub_status}")
  markup.add("📊 Statistika", "📢 Hammaga xabar yuborish")
  markup.add("➕ Majburiy kanal qo'shish", "➖ Majburiy kanalni o'chirish")
  markup.add("📋 Obuna kanallari ro'yxati", "👥 Foydalanuvchilarni boshqarish")
  markup.add("🔙 Asosiy menyu")
  bot.send_message(
      message.chat.id, "👑 Admin panel (Boshqaruv):", reply_markup=markup
  )


@bot.message_handler(
    func=lambda msg: msg.text
    in ["Majburiy obuna: 🟢 Yoqilgan", "Majburiy obuna: 🔴 O'chirilgan"]
)
def toggle_sub_status(message):
  if message.from_user.id != ADMIN_ID:
    return
  current = get_sub_status()
  if current == "on":
    set_sub_status("off")
    bot.send_message(message.chat.id, "🔴 Majburiy obuna o'chirildi!")
  else:
    set_sub_status("on")
    bot.send_message(message.chat.id, "🟢 Majburiy obuna yoqildi!")
  admin_panel_menu(message)


@bot.message_handler(func=lambda msg: msg.text == "📊 Statistika")
def bot_stats(message):
  if message.from_user.id != ADMIN_ID:
    return
  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute("SELECT COUNT(*) FROM users")
  users_count = cursor.fetchone()[0]
  cursor.execute("SELECT COUNT(*) FROM voices")
  voices_count = cursor.fetchone()[0]
  conn.close()
  bot.send_message(
      message.chat.id,
      f"📊 **Bot statistikasi:**\n\n👥 Foydalanuvchilar: {users_count} ta\n🎤 Yuklangan ovozlar: {voices_count} ta",
      parse_mode="Markdown",
  )


# Majburiy kanallarni qo'shish va o'chirish
@bot.message_handler(func=lambda msg: msg.text == "➕ Majburiy kanal qo'shish")
def add_sub_channel_cmd(message):
  if message.from_user.id != ADMIN_ID:
    return
  user_states[ADMIN_ID] = "waiting_for_add_sub_channel"
  bot.send_message(
      message.chat.id,
      "📢 Majburiy obuna uchun kanal username'ini yuboring (Masalan:"
      " `@kanal_nomi`):",
      reply_markup=types.ReplyKeyboardRemove(),
  )


@bot.message_handler(
    func=lambda msg: user_states.get(msg.from_user.id)
    == "waiting_for_add_sub_channel"
)
def save_sub_channel(message):
  if message.from_user.id != ADMIN_ID:
    return
  ch = message.text.strip()
  del user_states[ADMIN_ID]

  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  try:
    cursor.execute(
        "INSERT INTO required_channels (channel_username) VALUES (?)", (ch,)
    )
    conn.commit()
    bot.send_message(message.chat.id, f"✅ Majburiy kanal qo'shildi: {ch}")
  except Exception as e:
    bot.send_message(
        message.chat.id, f"❌ Xatolik (balki kanal oldindan bordir): {e}"
    )
  conn.close()
  admin_panel_menu(message)


@bot.message_handler(func=lambda msg: msg.text == "➖ Majburiy kanalni o'chirish")
def remove_sub_channel_cmd(message):
  if message.from_user.id != ADMIN_ID:
    return
  channels = get_required_channels()
  if not channels:
    bot.send_message(message.chat.id, "⚠️ Hozircha majburiy kanallar yo'q.")
    return
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
  for ch in channels:
    markup.add(ch)
  markup.add("🔙 Orqaga")
  user_states[ADMIN_ID] = "waiting_for_remove_sub_channel"
  bot.send_message(
      message.chat.id,
      "O'chirmoqchi bo'lgan majburiy kanalni tanlang:",
      reply_markup=markup,
  )


@bot.message_handler(
    func=lambda msg: user_states.get(msg.from_user.id)
    == "waiting_for_remove_sub_channel"
)
def delete_sub_channel(message):
  if message.from_user.id != ADMIN_ID:
    return
  ch = message.text.strip()
  del user_states[ADMIN_ID]
  if ch == "🔙 Orqaga":
    admin_panel_menu(message)
    return

  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute(
      "DELETE FROM required_channels WHERE channel_username = ?", (ch,)
  )
  conn.commit()
  conn.close()
  bot.send_message(message.chat.id, f"✅ Kanal o'chirildi: {ch}")
  admin_panel_menu(message)


@bot.message_handler(func=lambda msg: msg.text == "📋 Obuna kanallari ro'yxati")
def list_sub_channels(message):
  if message.from_user.id != ADMIN_ID:
    return
  channels = get_required_channels()
  if not channels:
    text = "⚠️ Hozircha majburiy obuna kanallari kiritilmagan."
  else:
    text = "📋 **Majburiy obuna kanallari ro'yxati:**\n\n" + "\n".join(
        [f"• {c}" for c in channels]
    )
  bot.send_message(message.chat.id, text, parse_mode="Markdown")


# Foydalanuvchilarni boshqarish
@bot.message_handler(func=lambda msg: msg.text == "👥 Foydalanuvchilarni boshqarish")
def manage_users_cmd(message):
  if message.from_user.id != ADMIN_ID:
    return
  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT COUNT(*), SUM(points) FROM users"
  )
  count, total_points = cursor.fetchone()
  total_points = total_points or 0

  cursor.execute(
      "SELECT full_name, phone_number, points FROM users ORDER BY user_id DESC"
      " LIMIT 5"
  )
  last_users = cursor.fetchall()
  conn.close()

  text = (
      f"👥 **Foydalanuvchilar ma'lumoti:**\n\n"
      f"• Jami foydalanuvchilar: {count} ta\n"
      f"• Umumiy to'plangan ballar: {total_points}\n\n"
      f"📌 **So'nggi ro'yxatdan o'tganlar:**\n"
  )
  for u in last_users:
    text += f"👤 {u[0]} | 📞 {u[1]} | ⭐ {u[2]} ball\n"

  bot.send_message(message.chat.id, text, parse_mode="Markdown")


# Hammaga xabar yuborish (Rassilka)
@bot.message_handler(func=lambda msg: msg.text == "📢 Hammaga xabar yuborish")
def broadcast_cmd(message):
  if message.from_user.id != ADMIN_ID:
    return
  user_states[ADMIN_ID] = "waiting_for_broadcast"
  bot.send_message(
      message.chat.id,
      "Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring"
      " (Matn, rasm yoki video):",
      reply_markup=types.ReplyKeyboardRemove(),
  )


@bot.message_handler(
    content_types=["text", "photo", "video", "document", "audio", "voice"],
    func=lambda msg: user_states.get(msg.from_user.id)
    == "waiting_for_broadcast",
)
def send_broadcast(message):
  if message.from_user.id != ADMIN_ID:
    return
  del user_states[ADMIN_ID]

  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute("SELECT user_id FROM users")
  users = cursor.fetchall()
  conn.close()

  success = 0
  failed = 0

  bot.send_message(
      message.chat.id,
      "⏳ Xabar yuborish boshlandi, iltimos kuting...",
      reply_markup=types.ReplyKeyboardRemove(),
  )

  for u in users:
    try:
      bot.copy_message(chat_id=u[0], from_chat_id=message.chat.id, message_id=message.message_id)
      success += 1
    except Exception:
      failed += 1

  bot.send_message(
      message.chat.id,
      f"✅ Xabar yuborildi!\n\n• Yetib bordi: {success} ta\n• Bloklaganlar: {failed} ta",
  )
  admin_panel_menu(message)


# --- OVOZ YUBORISH VA BOSHQA BO'LIMLAR ---
@bot.message_handler(content_types=["voice", "audio"])
def handle_voice(message):
  if not check_sub(message.from_user.id):
    send_sub_message(message.chat.id)
    return

  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO voices (user_id, file_id) VALUES (?, ?)",
      (message.from_user.id, message.voice.file_id if message.voice else message.audio.file_id),
  )
  conn.commit()
  conn.close()
  bot.reply_to(message, "✅ Ovozingiz batlega qo'shildi!")


@bot.message_handler(func=lambda msg: msg.text == "🎤 Ovoz yuborish")
def send_voice_info(message):
  bot.send_message(
      message.chat.id, "Ovozli xabaringizni (Voice) yoki audio yuboring."
  )


@bot.message_handler(func=lambda msg: msg.text == "👤 Profilim")
def show_profile(message):
  user_id = message.from_user.id
  conn = sqlite3.connect("battle.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT full_name, phone_number, points FROM users WHERE user_id = ?",
      (user_id,),
  )
  user = cursor.fetchone()
  conn.close()

  if user:
    full_name, phone, points = user
    text = f"👤 **Sizning profilingiz:**\n\n👤 Ism: {full_name}\n📞 Tel: {phone}\n⭐ Ballaringiz: {points}"
  else:
    text = "Siz ro'yxatdan o'tmagansiz. /start bosing."
  bot.send_message(message.chat.id, text, parse_mode="Markdown")


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

  text = "🏆 **TOP 10 REYTING** 🏆\n\n"
  for i, (name, pts) in enumerate(top_users, 1):
    text += f"{i}. {name} — {pts} ball\n"
  bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(func=lambda msg: msg.text == "🔙 Asosiy menyu")
def back_to_menu(message):
  show_main_menu(message)


if __name__ == "__main__":
  t = Thread(target=run_flask)
  t.daemon = True
  t.start()
  bot.infinity_polling(skip_pending=True)
