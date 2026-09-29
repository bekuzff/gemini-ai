import os
import sqlite3
import threading
from flask import Flask
import telebot
from telebot import types

TOKEN = "8854219020:AAGQfLvNosbYGPFXw6F2d3ZFg97rBxjhZPU"
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

ADMINS = [8372285180]  # O'z Telegram ID raqamingiz

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
            score INTEGER DEFAULT 0,
            is_blocked INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            channel_name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Kanal kiritishda havolani tozalash funksiyasi (https://t.me/... ni @username ga o'tkazish)
def clean_channel_input(text):
    text = text.strip()
    if "t.me/" in text:
        parts = text.split("t.me/")
        text = parts[-1].split("/")[0].split("?")[0]
    if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
        return text
    if not text.startswith("@") and not text.startswith("-"):
        text = "@" + text
    return text

# Battle kanalini bazadan olish
def get_battle_channel():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'battle_channel'")
    res = cursor.fetchone()
    conn.close()
    return clean_channel_input(res[0]) if res else None

# --- MAJBURIY OBUNANI TEKSHIRISH ---
def check_subscriptions(user_id):
    if user_id in ADMINS:
        return []

    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id FROM channels")
    channels = cursor.fetchall()
    conn.close()

    not_subscribed = []
    for ch in channels:
        ch_id = clean_channel_input(ch[0])
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

    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
    blocked_check = cursor.fetchone()
    if blocked_check and blocked_check[0] == 1:
        conn.close()
        bot.send_message(message.chat.id, "❌ Siz bot tomonidan bloklangansiz!")
        return

    args = message.text.split()
    referrer_id = None

    if len(args) > 1:
        try:
            ref_id = int(args[1])
            if ref_id != user_id:
                referrer_id = ref_id
        except ValueError:
            pass

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
                markup.add(types.InlineKeyboardButton(text=f"📢 Kanalga o'tish", url=f"https://t.me/{ch_id.replace('@', '')}"))
        markup.add(types.InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub"))
        bot.send_message(message.chat.id, "⚠️ **Botdan foydalanish uchun avval quyidagi kanal(lar)ga obuna bo'ling:**", reply_markup=markup)
        return

    show_main_menu(message.chat.id, message.from_user.first_name)

def show_main_menu(chat_id, name):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("⚔️ Battle yaratish", "🔗 Mening havolam")
    markup.add("🏆 Top Reyting", "📊 Statistika")
    if chat_id in ADMINS:
        markup.add("Admin Panel")
    
    bot.send_message(chat_id, f"Salom, <b>{name}</b>! Botga xush kelibsiz.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_check_sub(call):
    user_id = call.from_user.id
    unsubbed = check_subscriptions(user_id)
    if unsubbed:
        bot.answer_callback_query(call.id, "❌ Hamma kanallarga obuna bo'lmadingiz!", show_alert=True)
    else:
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        show_main_menu(call.message.chat.id, call.from_user.first_name)

# --- BARCHA XABARLAR VA ADMIN PANEL ---
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    text = message.text

    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
    b_check = cursor.fetchone()
    conn.close()
    if b_check and b_check[0] == 1 and user_id not in ADMINS:
        bot.send_message(user_id, "❌ Siz bot tomonidan bloklangansiz!")
        return

    if text == "Admin Panel" and user_id in ADMINS:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Kanal qo'shish", "➖ Kanalni o'chirish")
        markup.add("👥 Foydalanuvchilarni boshqarish", "📢 Xabar tarqatish")
        markup.add("🎯 Battle kanalini o'zgartirish", "🔙 Orqaga")
        bot.send_message(user_id, "⚙️ **Admin paneliga xush kelibsiz:**", reply_markup=markup)
        return

    if check_subscriptions(user_id):
        bot.send_message(user_id, "⚠️ Iltimos, avval kanallarga obuna bo'ling va /start bosing!")
        return

    if text == "⚔️ Battle yaratish":
        battle_ch = get_battle_channel()
        if not battle_ch:
            bot.send_message(user_id, "⚠️ Hozirgi vaqtda Battle kanali belgilanmagan!")
            return

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

    elif text == "🔙 Orqaga":
        show_main_menu(user_id, message.from_user.first_name)

    # --- ADMIN BUYRUQLARI ---
    elif text == "➕ Kanal qo'shish" and user_id in ADMINS:
        msg = bot.send_message(user_id, "Majburiy obuna uchun kanal username yoki havolasini yuboring (masalan: @kanal_username):")
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
        text_ch = "O'chirish uchun kanal username yoki ID sini yuboring:\n"
        for ch in channels:
            text_ch += f"• {ch[0]}\n"
        msg = bot.send_message(user_id, text_ch)
        bot.register_next_step_handler(msg, remove_channel_step)

    elif text == "👥 Foydalanuvchilarni boshqarish" and user_id in ADMINS:
        conn = db_connect()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, full_name, username FROM users LIMIT 30")
        users = cursor.fetchall()
        conn.close()

        if not users:
            bot.send_message(user_id, "❌ Hozircha botda foydalanuvchilar yo'q.")
            return

        markup = types.InlineKeyboardMarkup(row_width=1)
        for u in users:
            name_display = u[1] or "Ismsiz"
            uname_display = f" (@{u[2]})" if u[2] else ""
            markup.add(types.InlineKeyboardButton(text=f"👤 {name_display}{uname_display}", callback_data=f"adm_user_{u[0]}"))

        bot.send_message(user_id, "👥 Boshqarish uchun ro'yxatdan foydalanuvchini tanlang:", reply_markup=markup)

    elif text == "📢 Xabar tarqatish" and user_id in ADMINS:
        msg = bot.send_message(user_id, "Barcha foydalanuvchilarga yuboriladigan xabarni yuboring:")
        bot.register_next_step_handler(msg, broadcast_step)

    elif text == "🎯 Battle kanalini o'zgartirish" and user_id in ADMINS:
        current_ch = get_battle_channel() or "Belgilanmagan ❌"
        msg = bot.send_message(user_id, f"Hozirgi battle kanali: <b>{current_ch}</b>\n\nYangi kanal username yoki havolasini yuboring (masalan: @bekuzbotmaker):")
        bot.register_next_step_handler(msg, set_battle_channel_step)

# --- FOYDALANUVCHINI BOSHQARISH (CALLBACK) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_user_"))
def admin_manage_user_callback(call):
    target_id = int(call.data.split("_")[2])

    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, full_name, referrals, score, is_blocked FROM users WHERE user_id = ?", (target_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        bot.answer_callback_query(call.id, "❌ Foydalanuvchi topilmadi!", show_alert=True)
        return

    block_status = "Ha 🔴" if user[5] == 1 else "Yo'q 🟢"
    info_text = (
        f"👤 <b>Foydalanuvchi ma'lumotlari:</b>\n\n"
        f"🆔 ID: <code>{user[0]}</code>\n"
        f"👤 Ism: {user[2]}\n"
        f"🔗 Username: @{user[1] or 'yoq'}\n"
        f"👥 Takliflar: {user[3]} ta\n"
        f"⭐ Ballar: {user[4]} ball\n"
        f"🚫 Bloklangan: {block_status}"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(text="➕ Ball qo'shish", callback_data=f"add_score_{target_id}"),
        types.InlineKeyboardButton(text="➖ Ball ayirish", callback_data=f"sub_score_{target_id}")
    )
    
    if user[5] == 1:
        markup.add(types.InlineKeyboardButton(text="✅ Blokdan chiqarish", callback_data=f"unblock_user_{target_id}"))
    else:
        markup.add(types.InlineKeyboardButton(text="🚫 Bloklash", callback_data=f"block_user_{target_id}"))
        
    markup.add(types.InlineKeyboardButton(text="🗑 Bazadan o'chirish", callback_data=f"del_user_{target_id}"))

    try:
        bot.edit_message_text(info_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except:
        bot.send_message(call.message.chat.id, info_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith(("add_score_", "sub_score_", "block_user_", "unblock_user_", "del_user_")))
def user_action_callback(call):
    data = call.data.split("_")
    action = data[0]
    
    if action == "add":
        target_id = int(data[2])
        msg = bot.send_message(call.message.chat.id, f"Qancha ball qo'shmoqchisiz? (Faqat raqam yuboring):")
        bot.register_next_step_handler(msg, lambda m: update_user_score(m, target_id, plus=True))
    elif action == "sub":
        target_id = int(data[2])
        msg = bot.send_message(call.message.chat.id, f"Qancha ball ayirmoqchisiz? (Faqat raqam yuboring):")
        bot.register_next_step_handler(msg, lambda m: update_user_score(m, target_id, plus=False))
    elif action == "block":
        target_id = int(data[2])
        conn = db_connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "🚫 Foydalanuvchi bloklandi!", show_alert=True)
    elif action == "unblock":
        target_id = int(data[2])
        conn = db_connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_blocked = 0 WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "✅ Foydalanuvchi blokdan chiqarildi!", show_alert=True)
    elif action == "del":
        target_id = int(data[2])
        conn = db_connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        try:
            bot.edit_message_text("🗑 Foydalanuvchi bazadan o'chirildi.", call.message.chat.id, call.message.message_id)
        except:
            pass

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

# --- BATTLE POSTINI KANALGA YUBORISH ---
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
    
    target_channel = get_battle_channel()
    if not target_channel:
        bot.send_message(message.from_user.id, "❌ Xatolik: Battle kanali belgilanmagan.")
        return

    try:
        bot.send_message(target_channel, battle_text, reply_markup=markup)
        bot.send_message(message.from_user.id, "✅ Battle posti kanalda e'lon qilindi!", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("⚔️ Battle yaratish", "🔙 Orqaga"))
    except Exception as e:
        bot.send_message(message.from_user.id, 
            f"❌ Xatolik: Bot <b>{target_channel}</b> kanaliga yubora olmadi.\n\n"
            f"Sabab: Bot o'sha kanalga **Admin** qilinganligiga va xabar yozish huquqi borligiga ishonch hosil qiling!\n\n"
            f"Xato tafsiloti: <code>{e}</code>"
        )

@bot.callback_query_handler(func=lambda call: call.data == "battle_results")
def battle_results_callback(call):
    bot.answer_callback_query(call.id, "📊 Ovozlar hisoblanmoqda...", show_alert=True)

# --- ADMIN KANAL VA SOZLAMALAR ---
def add_channel_step(message):
    ch_id = clean_channel_input(message.text)
    conn = db_connect()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO channels (channel_id) VALUES (?)", (ch_id,))
        conn.commit()
        bot.send_message(message.from_user.id, f"✅ Majburiy obuna kanali muvaffaqiyatli qo'shildi: <b>{ch_id}</b>")
    except Exception as e:
        bot.send_message(message.from_user.id, f"❌ Xatolik: {e}")
    finally:
        conn.close()

def remove_channel_step(message):
    ch_id = clean_channel_input(message.text)
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM channels WHERE channel_id = ?", (ch_id,))
    conn.commit()
    conn.close()
    bot.send_message(message.from_user.id, f"🗑 Kanal o'chirildi: <b>{ch_id}</b>")

def set_battle_channel_step(message):
    ch_username = clean_channel_input(message.text)
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('battle_channel', ?)", (ch_username,))
    conn.commit()
    conn.close()
    bot.send_message(message.from_user.id, f"✅ Battle kanali muvaffaqiyatli <b>{ch_username}</b> etib o'zgartirildi!")

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
    
    print("Mukammal Battle Bot ishga tushdi...")
    bot.infinity_polling()
