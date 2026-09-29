import os
import sqlite3
import threading
from flask import Flask
import telebot
from telebot import types

TOKEN = "8854219020:AAGQfLvNosbYGPFXw6F2d3ZFg97rBxjhZPU"
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

ADMINS = [8372285180]

# --- RENDER UCHUN FLASK SERVER (Portni band qilish uchun) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- BAZA BILAN ISHLASH ---
def db_connect():
    conn = sqlite3.connect("battle_bot.db", check_same_thread=False)
    return conn

def init_db():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            referrer_id INTEGER,
            referrals INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            channel_name TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- MAJBURIY OBUNANI TEKSHIRISH ---
def check_subscriptions(user_id):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id FROM channels")
    channels = cursor.fetchall()
    conn.close()

    not_subscribed = []
    for ch in channels:
        ch_id = ch[0]
        try:
            member = bot.get_chat_member(ch_id, user_id)
            if member.status in ['left', 'kicked']:
                not_subscribed.append(ch_id)
        except Exception:
            pass
    return not_subscribed

# --- /START BUYRUG'I ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    args = message.text.split()
    referrer_id = None

    if len(args) > 1:
        try:
            ref_id = int(args[1])
            if ref_id != user_id:
                referrer_id = ref_id
        except ValueError:
            pass

    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (user_id, username, full_name, referrer_id) VALUES (?, ?, ?, ?)",
                       (user_id, message.from_user.username, message.from_user.first_name, referrer_id))
        if referrer_id:
            cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (referrer_id,))
        conn.commit()
    conn.close()

    unsubbed = check_subscriptions(user_id)
    if unsubbed:
        markup = types.InlineKeyboardMarkup()
        for ch_id in unsubbed:
            try:
                chat = bot.get_chat(ch_id)
                markup.add(types.InlineKeyboardButton(text=f"📢 {chat.title}", url=chat.invite_link or f"https://t.me/{chat.username}"))
            except:
                pass
        markup.add(types.InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub"))
        bot.send_message(message.chat.id, "⚠️ **Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:**", reply_markup=markup)
        return

    show_main_menu(message.chat.id, message.from_user.first_name)

def show_main_menu(chat_id, name):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔗 Mening havolam", "🏆 Top Reyting")
    markup.add("📊 Statistika")
    if chat_id in ADMINS:
        markup.add("⚙️ Admin Panel")
    
    bot.send_message(chat_id, f"Salom, <b>{name}</b>! Botga xush kelibsiz.", reply_markup=markup)

# --- OBUNANI QAYTA TEKSHIRISH CALLBACK ---
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_check_sub(call):
    user_id = call.from_user.id
    unsubbed = check_subscriptions(user_id)
    if unsubbed:
        bot.answer_callback_query(call.id, "❌ Hamma kanallarga obuna bo'lmadingiz!", show_alert=True)
    else:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message.chat.id, call.from_user.first_name)

# --- ASOSIY MENYU TUGMALARI ---
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    
    if check_subscriptions(user_id):
        bot.send_message(user_id, "⚠️ Iltimos, avval kanallarga obuna bo'ling va /start bosing!")
        return

    text = message.text

    if text == "🔗 Mening havolam":
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        conn = db_connect()
        cursor = conn.cursor()
        cursor.execute("SELECT referrals FROM users WHERE user_id = ?", (user_id,))
        refs = cursor.fetchone()[0]
        conn.close()
        bot.send_message(user_id, f"🔗 Sizning taklif havolangiz:\n{ref_link}\n\n👥 Taklif qilgan do'stlaringiz: <b>{refs} ta</b>")

    elif text == "🏆 Top Reyting":
        conn = db_connect()
        cursor = conn.cursor()
        cursor.execute("SELECT full_name, referrals FROM users ORDER BY referrals DESC LIMIT 10")
        top_users = cursor.fetchall()
        conn.close()
        
        text_top = "🏆 <b>TOP 10 REFERAL</b>\n\n"
        for i, u in enumerate(top_users, 1):
            text_top += f"{i}. {u[0]} — {u[1]} ta\n"
        bot.send_message(user_id, text_top)

    elif text == "📊 Statistika":
        conn = db_connect()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        bot.send_message(user_id, f"📊 Botdagi jami foydalanuvchilar: <b>{count} ta</b>")

    elif text == "⚙️ Admin Panel" and user_id in ADMINS:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Kanal qo'shish", "➖ Kanalni o'chirish")
        markup.add("📢 Xabar tarqatish", "🔙 Orqaga")
        bot.send_message(user_id, "⚙️ Admin paneliga xush kelibsiz:", reply_markup=markup)

    elif text == "🔙 Orqaga":
        show_main_menu(user_id, message.from_user.first_name)

    elif text == "➕ Kanal qo'shish" and user_id in ADMINS:
        msg = bot.send_message(user_id, "Kanal username yoki ID sini yuboring (masalan: @kanal_username):")
        bot.register_next_step_handler(msg, add_channel_step)

    elif text == "➖ Kanalni o'chirish" and user_id in ADMINS:
        conn = db_connect()
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id FROM channels")
        channels = cursor.fetchall()
        conn.close()
        if not channels:
            bot.send_message(user_id, "Hozircha majburiy kanallar yo'q.")
            return
        text_ch = "O'chirish uchun kanal ID sini yuboring:\n"
        for ch in channels:
            text_ch += f"• {ch[0]}\n"
        msg = bot.send_message(user_id, text_ch)
        bot.register_next_step_handler(msg, remove_channel_step)

    elif text == "📢 Xabar tarqatish" and user_id in ADMINS:
        msg = bot.send_message(user_id, "Barcha foydalanuvchilarga yuboriladigan xabarni yuboring:")
        bot.register_next_step_handler(msg, broadcast_step)

# --- ADMIN FUNKSIYALARI ---
def add_channel_step(message):
    ch_id = message.text.strip()
    conn = db_connect()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO channels (channel_id) VALUES (?)", (ch_id,))
        conn.commit()
        bot.send_message(message.from_user.id, "✅ Kanal muvaffaqiyatli qo'shildi!")
    except Exception as e:
        bot.send_message(message.from_user.id, f"❌ Xatolik: {e}")
    finally:
        conn.close()

def remove_channel_step(message):
    ch_id = message.text.strip()
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM channels WHERE channel_id = ?", (ch_id,))
    conn.commit()
    conn.close()
    bot.send_message(message.from_user.id, "🗑 Kanal o'chirildi!")

def broadcast_step(message):
    text = message.text
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()

    success = 0
    for u in users:
        try:
            bot.send_message(u[0], text)
            success += 1
        except:
            pass
    bot.send_message(message.from_user.id, f"📢 Xabar {success} ta foydalanuvchiga yuborildi.")

if __name__ == "__main__":
    # Flask serverini alohida oqimda (thread) ishga tushiramiz (Render talabi uchun)
    t = threading.Thread(target=run_flask)
    t.start()
    
    print("Bot Render uchun ishga tushdi...")
    bot.infinity_polling()
