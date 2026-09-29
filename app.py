import os
import sqlite3
import threading
from flask import Flask
import telebot
from telebot import types

TOKEN = "8854219020:AAGQfLvNosbYGPFXw6F2d3ZFg97rBxjhZPU"
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

ADMINS = [8372285180]

# --- RENDER UCHUN FLASK SERVER ---
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
            referrals INTEGER DEFAULT 0,
            score INTEGER DEFAULT 0
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
            cursor.execute("UPDATE users SET referrals = referrals + 1, score = score + 1 WHERE user_id = ?", (referrer_id,))
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
    markup.add("⚔️ Battle yaratish", "🔗 Mening havolam")
    markup.add("🏆 Top Reyting", "📊 Statistika")
    if chat_id in ADMINS:
        markup.add("⚙️️ Admin Panel")
    
    bot.send_message(chat_id, f"Salom, <b>{name}</b>! Botga xush kelibsiz.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_check_sub(call):
    user_id = call.from_user.id
    unsubbed = check_subscriptions(user_id)
    if unsubbed:
        bot.answer_callback_query(call.id, "❌ Hamma kanallarga obuna bo'lmadingiz!", show_alert=True)
    else:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message.chat.id, call.from_user.first_name)

# --- ASOSIY MENYU VA BATTLE ---
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    
    if check_subscriptions(user_id):
        bot.send_message(user_id, "⚠️ Iltimos, avval kanallarga obuna bo'ling va /start bosing!")
        return

    text = message.text

    if text == "⚔️ Battle yaratish":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔙 Orqaga")
        msg = bot.send_message(user_id, "📢 Kanalga tashlamoqchi bo'lgan <b>#nft</b> postini yoki ishtirokchi matnini yuboring:", reply_markup=markup)
        bot.register_next_step_handler(msg, create_battle_step)

    elif text == "🔗 Mening havolam":
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        conn = db_connect()
        cursor = conn.cursor()
        cursor.execute("SELECT referrals, score FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        conn.close()
        bot.send_message(user_id, f"🔗 Sizning taklif havolangiz:\n{ref_link}\n\n👥 Takliflar: <b>{res[0]} ta</b>\n⭐ Ballaringiz: <b>{res[1]} ta</b>")

    elif text == "🏆 Top Reyting":
        conn = db_connect()
        cursor = conn.cursor()
        cursor.execute("SELECT full_name, score FROM users ORDER BY score DESC LIMIT 10")
        top_users = cursor.fetchall()
        conn.close()
        
        text_top = "🏆 <b>TOP 10 BATTLE REYTINGI</b>\n\n"
        for i, u in enumerate(top_users, 1):
            text_top += f"{i}. {u[0]} — {u[1]} ball\n"
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
        markup.add("👥 Foydalanuvchini boshqarish", "📢 Xabar tarqatish")
        markup.add("🔙 Orqaga")
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

    elif text == "👥 Foydalanuvchini boshqarish" and user_id in ADMINS:
        msg = bot.send_message(user_id, "Boshqarish uchun foydalanuvchining **Telegram ID** raqamini yuboring:")
        bot.register_next_step_handler(msg, manage_user_step)

    elif text == "📢 Xabar tarqatish" and user_id in ADMINS:
        msg = bot.send_message(user_id, "Barcha foydalanuvchilarga yuboriladigan xabarni yuboring:")
        bot.register_next_step_handler(msg, broadcast_step)

# --- BATTLE YARATISH ---
def create_battle_step(message):
    if message.text == "🔙 Orqaga":
        show_main_menu(message.from_user.id, message.from_user.first_name)
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(text="🔥 Qatnashish", url=f"https://t.me/{bot.get_me().username}?start={message.from_user.id}"),
        types.InlineKeyboardButton(text="📊 Natijalar", callback_data="battle_results")
    )

    battle_text = f"<b>3 ➔ N F T B A T L 👑</b>\n\nIshtirokchi: {message.from_user.first_name} (@{message.from_user.username or 'yoq'})\n\n{message.text}"
    
    try:
        target_channel = "@dark_vip_nft"  # O'z kanalingiz username'ini yozing
        bot.send_message(target_channel, battle_text, reply_markup=markup)
        bot.send_message(message.from_user.id, "✅ Battle posti kanalda e'lon qilindi!", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("⚔️ Battle yaratish", "🔙 Orqaga"))
    except Exception as e:
        bot.send_message(message.from_user.id, f"❌ Xatolik (Kanalga yozib bo'lmadi, bot adminligini tekshiring): {e}")

@bot.callback_query_handler(func=lambda call: call.data == "battle_results")
def battle_results_callback(call):
    bot.answer_callback_query(call.id, "📊 Ovozlar hisoblanmoqda...", show_alert=True)

# --- FOYDALANUVCHINI BOSHQARISH FUNKSIYALARI ---
def manage_user_step(message):
    try:
        target_id = int(message.text.strip())
    except ValueError:
        bot.send_message(message.from_user.id, "❌ Noto'g'ri ID kiritildi. Faqat raqam yuboring.")
        return

    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, full_name, referrals, score FROM users WHERE user_id = ?", (target_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        bot.send_message(message.from_user.id, "❌ Bunday ID raqamidagi foydalanuvchi topilmadi.")
        return

    info_text = (
        f"👤 <b>Foydalanuvchi ma'lumotlari:</b>\n\n"
        f"🆔 ID: <code>{user[0]}</code>\n"
        f"👤 Ism: {user[2]}\n"
        f"🔗 Username: @{user[1] or 'yoq'}\n"
        f"👥 Takliflar: {user[3]} ta\n"
        f"⭐ Ballar: {user[4]} ball"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(text="➕ Ball qo'shish", callback_data=f"add_score_{target_id}"),
        types.InlineKeyboardButton(text="➖ Ball ayirish", callback_data=f"sub_score_{target_id}")
    )
    markup.add(types.InlineKeyboardButton(text="🗑 Bazadan o'chirish", callback_data=f"del_user_{target_id}"))

    bot.send_message(message.from_user.id, info_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith(("add_score_", "sub_score_", "del_user_")))
def user_action_callback(call):
    data = call.data.split("_")
    action = data[0]
    target_id = int(data[2])

    if action == "add":
        msg = bot.send_message(call.message.chat.id, f"Qancha ball qo'shmoqchisiz? (Faqat raqam yuboring):")
        bot.register_next_step_handler(msg, lambda m: update_user_score(m, target_id, plus=True))
    elif action == "sub":
        msg = bot.send_message(call.message.chat.id, f"Qancha ball ayirmoqchisiz? (Faqat raqam yuboring):")
        bot.register_next_step_handler(msg, lambda m: update_user_score(m, target_id, plus=False))
    elif action == "del":
        conn = db_connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        bot.edit_message_text("🗑 Foydalanuvchi bazadan o'chirildi.", call.message.chat.id, call.message.message_id)

def update_user_score(message, target_id, plus):
    try:
        amount = int(message.text.strip())
    except ValueError:
        bot.send_message(message.from_user.id, "❌ Faqat raqam kiriting!")
        return

    conn = db_connect()
    cursor = conn.cursor()
    if plus:
        cursor.execute("UPDATE users SET score = score + ? WHERE user_id = ?", (amount, target_id))
    else:
        cursor.execute("UPDATE users SET score = score - ? WHERE user_id = ?", (amount, target_id))
    conn.commit()
    conn.close()

    bot.send_message(message.from_user.id, f"✅ Muvaffaqiyatli bajarildi! Foydalanuvchi ballari yangilandi.")

# --- ADMIN KANAL VA XABAR FUNKSIYALARI ---
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
    t = threading.Thread(target=run_flask)
    t.start()
    
    print("Mukammal Battle & User Control Bot Render uchun ishga tushdi...")
    bot.infinity_polling()
