import telebot
from telebot.types import *
import sqlite3
import datetime
import re
from dotenv import load_dotenv
import os



# ---------------- CONFIG ----------------
load_dotenv()
BOT= os.getenv('TOKEN')
bot = telebot.TeleBot(BOT)

ADMIN_ID = 8571986159

# ---------------- DATABASE ----------------
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

# جدول کاربران
cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    phone TEXT,
    created_at TEXT
)
""")

# جدول کارت‌ها
cursor.execute("""
CREATE TABLE IF NOT EXISTS cards(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    card_number TEXT,
    card_name TEXT
)
""")

# جدول واریزی‌ها
cursor.execute("""
CREATE TABLE IF NOT EXISTS payments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    date TEXT,
    time TEXT
)
""")

# جدول اخبار
cursor.execute("""
CREATE TABLE IF NOT EXISTS news(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    category TEXT,
    title TEXT,
    date TEXT,
    time TEXT,
    text TEXT,
    media TEXT,
    created_at TEXT
)
""")

conn.commit()

# ---------------- STATE ----------------
user_state = {}
temp_data = {}

# ---------------- KEYBOARDS ----------------
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("ارسال خبر")
    markup.row("اطلاعات کارت بانکی", "واریزی‌های من")
    return markup

def card_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("ثبت کارت", "کارت‌های من")
    markup.row("برگشت")
    return markup

def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("ثبت واریزی", "لیست کاربران")
    markup.row("مدیریت اخبار")
    markup.row("برگشت")
    return markup

# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "پنل ادمین 👑", reply_markup=admin_menu())
        return

    cursor.execute("SELECT * FROM users WHERE user_id=?", (message.from_user.id,))
    user = cursor.fetchone()

    if not user:
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        btn = KeyboardButton("ثبت نام", request_contact=True)
        markup.add(btn)
        bot.send_message(message.chat.id, "برای استفاده ابتدا ثبت نام کنید", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "خوش آمدید", reply_markup=main_menu())

# ---------------- BACK ----------------
@bot.message_handler(func=lambda m: m.text == "برگشت")
def back(message):
    user_state.pop(message.from_user.id, None)
    temp_data.pop(message.from_user.id, None)

    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "بازگشت به پنل ادمین", reply_markup=admin_menu())
    else:
        bot.send_message(message.chat.id, "بازگشت به منو", reply_markup=main_menu())

# ---------------- REGISTER ----------------
@bot.message_handler(content_types=['contact'])
def register(message):
    cursor.execute("""
    INSERT OR REPLACE INTO users(user_id,username,full_name,phone,created_at)
    VALUES(?,?,?,?,?)
    """, (message.from_user.id, message.from_user.username, message.from_user.first_name, message.contact.phone_number, datetime.datetime.now()))
    conn.commit()
    bot.send_message(message.chat.id, "ثبت نام انجام شد ✅", reply_markup=main_menu())

# ---------------- CARD ----------------
@bot.message_handler(func=lambda m: m.text == "اطلاعات کارت بانکی")
def card_section(message):
    bot.send_message(message.chat.id, "مدیریت کارت:", reply_markup=card_menu())

@bot.message_handler(func=lambda m: m.text == "ثبت کارت")
def add_card(message):
    user_state[message.from_user.id] = "card_number"
    bot.send_message(message.chat.id, "شماره کارت را وارد کنید (16 رقم)")

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "card_number")
def get_card_number(message):
    if not message.text.isdigit() or len(message.text) != 16:
        bot.send_message(message.chat.id, "شماره کارت نامعتبر است ❌")
        return
    temp_data[message.from_user.id] = {"card_number": message.text}
    user_state[message.from_user.id] = "card_name"
    bot.send_message(message.chat.id, "نام صاحب کارت را وارد کنید")

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "card_name")
def save_card(message):
    card_number = temp_data[message.from_user.id]["card_number"]
    card_name = message.text
    cursor.execute("INSERT INTO cards(user_id,card_number,card_name) VALUES(?,?,?)",
                   (message.from_user.id, card_number, card_name))
    conn.commit()
    user_state.pop(message.from_user.id)
    temp_data.pop(message.from_user.id)
    bot.send_message(message.chat.id, "کارت با موفقیت ثبت شد ✅", reply_markup=card_menu())

@bot.message_handler(func=lambda m: m.text == "کارت‌های من")
def show_cards(message):
    cursor.execute("SELECT card_number, card_name FROM cards WHERE user_id=?", (message.from_user.id,))
    cards = cursor.fetchall()
    if not cards:
        bot.send_message(message.chat.id, "کارتی ثبت نشده")
    else:
        text = "کارت‌های شما:\n"
        for c in cards:
            text += f"{c[0]} - {c[1]}\n"
        bot.send_message(message.chat.id, text)

# ---------------- USER PAYMENTS ----------------
@bot.message_handler(func=lambda m: m.text == "واریزی‌های من")
def my_payments(message):
    cursor.execute("SELECT amount,date,time FROM payments WHERE user_id=?", (message.from_user.id,))
    pays = cursor.fetchall()
    if not pays:
        bot.send_message(message.chat.id, "واریزی ندارید")
        return
    total = sum([p[0] for p in pays])
    text = "".join([f"{p[0]} تومان - {p[1]} {p[2]}\n" for p in pays])
    text += f"\nمجموع کل: {total} تومان"
    bot.send_message(message.chat.id, text)

# ---------------- SEND NEWS ----------------
categories = ["اجتماعی","اقتصادی","امنیتی","جاسوسی","دینی و روحانیت","رزمایش","سایبری","سیاسی","علم و فناوری","فرهنگی","نظامی و دفاعی"]

@bot.message_handler(func=lambda m: m.text == "ارسال خبر")
def start_news(message):
    user_state[message.from_user.id] = "choose_category"
    markup = InlineKeyboardMarkup()
    for c in categories:
        markup.add(InlineKeyboardButton(c, callback_data=f"cat_{c}"))
    bot.send_message(message.chat.id, "دسته بندی خبر را انتخاب کنید:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
def choose_category(call):
    category = call.data.replace("cat_","")
    temp_data[call.from_user.id] = {"category": category, "media":[]}
    user_state[call.from_user.id] = "title"
    bot.send_message(call.message.chat.id, "عنوان خبر را وارد کنید (حداکثر 50 کاراکتر)")

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "title")
def get_title_text(message):
    if len(message.text) > 50:
        bot.send_message(message.chat.id, "عنوان طولانی است، کمتر از 50 کاراکتر بفرستید")
        return
    temp_data[message.from_user.id]["title"] = message.text
    user_state[message.from_user.id] = "date"
    bot.send_message(message.chat.id, "تاریخ وقوع را بفرستید مثال: 1404-06-01")

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "date")
def get_date(message):
    if not re.match(r"\d{4}-\d{2}-\d{2}", message.text):
        bot.send_message(message.chat.id, "فرمت تاریخ اشتباه است")
        return
    temp_data[message.from_user.id]["date"] = message.text
    user_state[message.from_user.id] = "time"
    bot.send_message(message.chat.id, "ساعت خبر را بفرستید مثال: 15:34")

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "time")
def get_time(message):
    if not re.match(r"\d{2}:\d{2}", message.text):
        bot.send_message(message.chat.id, "فرمت ساعت اشتباه است")
        return
    temp_data[message.from_user.id]["time"] = message.text
    user_state[message.from_user.id] = "text"
    bot.send_message(message.chat.id, "متن خبر را بفرستید")

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "text")
def get_text(message):
    temp_data[message.from_user.id]["text"] = message.text
    user_state[message.from_user.id] = "media"
    bot.send_message(message.chat.id, "عکس یا ویدیو خبر را بفرستید و در پایان کلمه 'تمام' را ارسال کنید")

@bot.message_handler(content_types=['photo','video'])
def get_media(message):
    if user_state.get(message.from_user.id) == "media":
        file_id = message.photo[-1].file_id if message.content_type == "photo" else message.video.file_id
        temp_data[message.from_user.id]["media"].append(file_id)

# ------------------- بعد از متن خبر -------------------
@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "media")
def handle_media_or_finish(message):
    user_id = message.from_user.id
    data = temp_data.get(user_id)
    if not data:
        return

    if message.text and message.text.lower() == "تمام":
        # ثبت خبر در دیتابیس
        media_files = ",".join(data.get("media", [])) if data.get("media") else ""
        cursor.execute("""
        INSERT INTO news(user_id,category,title,date,time,text,media,created_at)
        VALUES(?,?,?,?,?,?,?,?)
        """, (
            user_id,
            data["category"],
            data["title"],
            data["date"],
            data["time"],
            data["text"],
            media_files,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        conn.commit()

        # ارسال متن خبر به ادمین
        bot.send_message(ADMIN_ID, f"خبر جدید از {message.from_user.first_name}:\n\n"
                                   f"عنوان: {data['title']}\n"
                                   f"دسته: {data['category']}\n"
                                   f"متن: {data['text']}")

        # ارسال رسانه‌ها به ادمین (عکس یا ویدئو واقعی)
        for file_id in data.get("media", []):
            try:
                # تشخیص نوع رسانه و ارسال مناسب
                if file_id.startswith("AgAC"):  # عکس
                    bot.send_photo(ADMIN_ID, file_id)
                else:  # ویدئو
                    bot.send_video(ADMIN_ID, file_id)
            except Exception as e:
                print(f"خطا در ارسال رسانه به ادمین: {e}")

        bot.send_message(user_id, "خبر با موفقیت ثبت شد ✅", reply_markup=main_menu())

        # پاک کردن داده‌های موقت
        user_state.pop(user_id, None)
        temp_data.pop(user_id, None)

    elif message.content_type in ["photo","video"]:
        # ذخیره رسانه‌ها
        if "media" not in data:
            data["media"] = []
        file_id = message.photo[-1].file_id if message.content_type == "photo" else message.video.file_id
        data["media"].append(file_id)
        temp_data[user_id] = data
        bot.send_message(user_id, "رسانه اضافه شد، اگر تمام شد کلمه 'تمام' را بفرستید")

    else:
        bot.send_message(user_id, "لطفاً عکس یا ویدیو بفرستید یا 'تمام' را ارسال کنید")



# ---------------- ADMIN PANEL ----------------
@bot.message_handler(func=lambda m: m.text == "ثبت واریزی" and m.from_user.id == ADMIN_ID)
def admin_add_payment(message):
    user_state[message.from_user.id] = "admin_user_id"
    bot.send_message(message.chat.id, "آیدی عددی کاربر را وارد کنید")

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "admin_user_id")
def admin_get_user(message):
    temp_data[message.from_user.id] = {"user_id": int(message.text)}
    user_state[message.from_user.id] = "admin_amount"
    bot.send_message(message.chat.id, "مبلغ را وارد کنید (تومان)")

@bot.message_handler(func=lambda m: user_state.get(m.from_user.id) == "admin_amount")
def admin_save_payment(message):
    user_id = temp_data[message.from_user.id]["user_id"]
    amount = int(message.text)
    now = datetime.datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M")
    cursor.execute("INSERT INTO payments(user_id,amount,date,time) VALUES(?,?,?,?)",
                   (user_id, amount, date, time))
    conn.commit()
    try:
        bot.send_message(user_id, f"{amount} تومان در تاریخ {date} ساعت {time} به حساب شما واریز شد 💰")
    except:
        bot.send_message(ADMIN_ID, f"کاربر با آی‌دی {user_id} ربات را فعال نکرده است ⚠️")
    bot.send_message(message.chat.id, "واریزی ثبت شد ✅")
    user_state.pop(message.from_user.id)
    temp_data.pop(message.from_user.id)

@bot.message_handler(func=lambda m: m.text == "لیست کاربران" and m.from_user.id == ADMIN_ID)
def admin_users(message):
    cursor.execute("SELECT user_id,full_name FROM users")
    users = cursor.fetchall()
    if not users:
        bot.send_message(message.chat.id, "کاربری وجود ندارد")
        return
    text = "لیست کاربران:\n\n"
    for u in users:
        text += f"{u[1]} - {u[0]}\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "مدیریت اخبار" and m.from_user.id == ADMIN_ID)
def admin_manage_news(message):
    cursor.execute("SELECT id,title,user_id FROM news ORDER BY id DESC")
    news_list = cursor.fetchall()
    if not news_list:
        bot.send_message(message.chat.id, "هیچ خبری ثبت نشده")
        return
    text = "اخبار ثبت شده:\n\n"
    for n in news_list:
        text += f"{n[0]} - {n[1]} (کاربر: {n[2]})\n"
    bot.send_message(message.chat.id, text)

# ---------------- RUN ----------------
print("Bot is running...")
bot.infinity_polling()
