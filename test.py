from flask import Flask, request
import telebot
import json
import random
import threading
import time

TOKEN = '7947429084:AAECl4VTgRdgv53IAixvZ5qgDMvABI8_d0o'
ADMIN_ID = 6862331593  # Telegram ID-и админи аслӣ

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Базаи маълумот
try:
    with open("data.json", "r") as f:
        db = json.load(f)
except:
    db = {"movies": {}, "channels": [], "admins": [ADMIN_ID], "collections": {}, "delete_time": 30}

if "admins" not in db:
    db["admins"] = [ADMIN_ID]

if "collections" not in db:
    db["collections"] = {}

if "delete_time" not in db:
    db["delete_time"] = 30  # Вақти стандартӣ барои нест кардани филмҳо (30 сония)

def save_db():
    with open("data.json", "w") as f:
        json.dump(db, f)

def is_subscribed(user_id):
    for channel in db["channels"]:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status in ['member', 'administrator', 'creator']:
                continue
            else:
                return False
        except:
            return False
    return True

def is_admin(user_id):
    return user_id in db["admins"]

user_states = {}
movie_info_temp = {}
collection_temp = {}

# Роут барои webhook
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return 'ok', 200

@app.route('/')
def index():
    return "Bot is running!", 200

# Хандлерҳо
@bot.message_handler(commands=["start"])
def start(msg):
    if is_subscribed(msg.chat.id):
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔍 Ҷустуҷӯи филм", "📺 Филмҳои нав")
        markup.add("ℹ️ Дар бораи мо")
        
        if is_admin(msg.from_user.id):
            markup.add("👨‍💻 Панели админ")
            
        bot.send_message(msg.chat.id, "Хуш омадед ба боти филмҳо!", reply_markup=markup)
    else:
        markup = telebot.types.InlineKeyboardMarkup()
        for ch in db["channels"]:
            markup.add(telebot.types.InlineKeyboardButton("Обуна шудан", url=f"https://t.me/{ch.replace('@', '')}"))
        markup.add(telebot.types.InlineKeyboardButton("Санҷиш", callback_data="check_sub"))
        bot.send_message(msg.chat.id, "Аввал ба каналҳо обуна шавед:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "🔍 Ҷустуҷӯи филм")
def search_movie_handler(msg):
    if is_subscribed(msg.chat.id):
        user_states[msg.chat.id] = "waiting_for_movie_id"
        bot.send_message(msg.chat.id, "Лутфан ID филмро равон кунед:")
    else:
        start(msg)

@bot.message_handler(func=lambda msg: msg.text == "📺 Филмҳои нав")
def new_movies(msg):
    if is_subscribed(msg.chat.id):
        # Гирифтани 5 филми охирин
        movie_ids = list(db["movies"].keys())
        if movie_ids:
            response = "Филмҳои нав:\n\n"
            # Гирифтани то 5 филми охирин
            for movie_id in movie_ids[-5:]:
                info = db["movies"][movie_id].get("info", "")
                response += f"🎬 ID: {movie_id}\n{info}\n\n"
            bot.send_message(msg.chat.id, response)
        else:
            bot.send_message(msg.chat.id, "Ҳоло ягон филм илова нашудааст.")
    else:
        start(msg)

@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Дар бораи мо")
def about_us(msg):
    if is_subscribed(msg.chat.id):
        bot.send_message(msg.chat.id, "Ин бот барои тамошои филмҳо бо сифати баланд тайёр шудааст.\n\nБарои дастрасӣ ба филмҳо, ID-и филмро ворид кунед.")
    else:
        start(msg)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub(call):
    if is_subscribed(call.message.chat.id):
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔍 Ҷустуҷӯи филм", "📺 Филмҳои нав")
        markup.add("ℹ️ Дар бораи мо")
        
        if is_admin(call.message.chat.id):
            markup.add("👨‍💻 Панели админ")
            
        bot.send_message(call.message.chat.id, "Офарин! Шумо метавонед ботро истифода баред.", reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, "Лутфан аввал обуна шавед.")

@bot.message_handler(func=lambda msg: msg.text == "👨‍💻 Панели админ" and is_admin(msg.from_user.id))
def panel(msg):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Иловаи Филм", "➕ Иловаи Канал")
    markup.add("❌ Нест кардани Филм", "❌ Нест кардани Канал")
    markup.add("📚 Маҷмӯаи филмҳо")
    markup.add("👨‍💼 Идоракунии админҳо")
    markup.add("⏱ Танзимоти вақт")
    markup.add("🔙 Бозгашт")
    bot.send_message(msg.chat.id, "Панели админ:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "👨‍💼 Идоракунии админҳо" and is_admin(msg.from_user.id))
def admin_management(msg):
    if msg.from_user.id == ADMIN_ID:  # Фақат админи аслӣ метавонад админҳоро идора кунад
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Иловаи админ", "❌ Нест кардани админ")
        markup.add("🔙 Бозгашт ба панел")
        bot.send_message(msg.chat.id, "Идоракунии админҳо:", reply_markup=markup)
    else:
        bot.send_message(msg.chat.id, "Шумо иҷозат надоред.")

@bot.message_handler(func=lambda msg: msg.text == "➕ Иловаи админ" and msg.from_user.id == ADMIN_ID)
def add_admin(msg):
    user_states[msg.chat.id] = "waiting_for_admin_id"
    bot.send_message(msg.chat.id, "ID-и админи навро равон кунед:")

@bot.message_handler(func=lambda msg: msg.text == "❌ Нест кардани админ" and msg.from_user.id == ADMIN_ID)
def delete_admin(msg):
    if len(db["admins"]) > 1:
        user_states[msg.chat.id] = "waiting_for_delete_admin"
        admins = "\n".join([f"{i+1}. {admin_id}" for i, admin_id in enumerate(db["admins"]) if admin_id != ADMIN_ID])
        bot.send_message(msg.chat.id, f"Рақами админро барои нест кардан интихоб кунед:\n{admins}")
    else:
        bot.send_message(msg.chat.id, "Дар система танҳо як админ мавҷуд аст.")

@bot.message_handler(func=lambda msg: msg.text == "📚 Маҷмӯаи филмҳо" and is_admin(msg.from_user.id))
def collection_menu(msg):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Сохтани маҷмӯа", "❌ Нест кардани маҷмӯа")
    markup.add("📋 Рӯйхати маҷмӯаҳо")
    markup.add("🔙 Бозгашт ба панел")
    bot.send_message(msg.chat.id, "Идоракунии маҷмӯаҳои филм:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "➕ Сохтани маҷмӯа" and is_admin(msg.from_user.id))
def create_collection(msg):
    collection_temp[msg.chat.id] = {"movies": []}
    user_states[msg.chat.id] = "waiting_for_collection_movie"
    bot.send_message(msg.chat.id, "Филми якумро равон кунед (то 10 филм метавонед). Барои анҷом [анҷом] пахш кунед:")

@bot.message_handler(func=lambda msg: msg.text == "❌ Нест кардани маҷмӯа" and is_admin(msg.from_user.id))
def delete_collection(msg):
    if db["collections"]:
        user_states[msg.chat.id] = "waiting_for_delete_collection"
        collections = "\n".join([f"{i+1}. ID: {coll_id}, Шумораи филмҳо: {len(info['movies'])}" 
                               for i, (coll_id, info) in enumerate(db["collections"].items())])
        bot.send_message(msg.chat.id, f"Рақами маҷмӯаро барои нест кардан интихоб кунед:\n{collections}")
    else:
        bot.send_message(msg.chat.id, "Ягон маҷмӯа мавҷуд нест.")

@bot.message_handler(func=lambda msg: msg.text == "📋 Рӯйхати маҷмӯаҳо" and is_admin(msg.from_user.id))
def list_collections(msg):
    if db["collections"]:
        collections = "\n\n".join([f"🎬 ID: {coll_id}\nШумораи филмҳо: {len(info['movies'])}" 
                                 for coll_id, info in db["collections"].items()])
        bot.send_message(msg.chat.id, f"Рӯйхати маҷмӯаҳо:\n\n{collections}")
    else:
        bot.send_message(msg.chat.id, "Ягон маҷмӯа мавҷуд нест.")

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_collection_movie")
def add_movie_to_collection(msg):
    if msg.text == "анҷом" or msg.text == "[анҷом]":
        if collection_temp[msg.chat.id]["movies"]:
            collection_id = str(random.randint(1000, 9999))
            while collection_id in db["collections"]:
                collection_id = str(random.randint(1000, 9999))
                
            db["collections"][collection_id] = collection_temp[msg.chat.id]
            save_db()
            bot.send_message(msg.chat.id, f"Маҷмӯа сохта шуд. ID маҷмӯа: {collection_id}")
            del collection_temp[msg.chat.id]
            user_states.pop(msg.chat.id)
        else:
            bot.send_message(msg.chat.id, "Шумо бояд ҳадди ақал як филм илова кунед.")
    elif msg.content_type == 'video':
        if len(collection_temp[msg.chat.id]["movies"]) >= 10:
            bot.send_message(msg.chat.id, "Шумо аллакай 10 филм илова кардед. Барои анҷом [анҷом] пахш кунед.")
        else:
            movie_data = {"file_id": msg.video.file_id}
            collection_temp[msg.chat.id]["movies"].append(movie_data)
            movie_count = len(collection_temp[msg.chat.id]["movies"])
            bot.send_message(msg.chat.id, f"Филми {movie_count} илова шуд. Филми навбатиро равон кунед ё [анҷом] пахш кунед:")
    else:
        bot.send_message(msg.chat.id, "Лутфан филм равон кунед ё [анҷом] пахш кунед.")

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_admin_id")
def process_add_admin(msg):
    try:
        admin_id = int(msg.text)
        if admin_id not in db["admins"]:
            db["admins"].append(admin_id)
            save_db()
            bot.send_message(msg.chat.id, f"Админ бо ID {admin_id} илова шуд.")
        else:
            bot.send_message(msg.chat.id, "Ин ID аллакай дар рӯйхати админҳо мавҷуд аст.")
    except ValueError:
        bot.send_message(msg.chat.id, "Лутфан танҳо рақам ворид кунед.")
    user_states.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_delete_admin")
def process_delete_admin(msg):
    try:
        index = int(msg.text) - 1
        admin_ids = [admin_id for admin_id in db["admins"] if admin_id != ADMIN_ID]
        if 0 <= index < len(admin_ids):
            admin_to_delete = admin_ids[index]
            db["admins"].remove(admin_to_delete)
            save_db()
            bot.send_message(msg.chat.id, f"Админ бо ID {admin_to_delete} нест карда шуд.")
        else:
            bot.send_message(msg.chat.id, "Рақам нодуруст.")
    except ValueError:
        bot.send_message(msg.chat.id, "Лутфан танҳо рақам ворид кунед.")
    user_states.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_delete_collection")
def process_delete_collection(msg):
    try:
        index = int(msg.text) - 1
        collections = list(db["collections"].keys())
        if 0 <= index < len(collections):
            collection_id = collections[index]
            del db["collections"][collection_id]
            save_db()
            bot.send_message(msg.chat.id, f"Маҷмӯа бо ID {collection_id} нест карда шуд.")
        else:
            bot.send_message(msg.chat.id, "Рақам нодуруст.")
    except ValueError:
        bot.send_message(msg.chat.id, "Лутфан танҳо рақам ворид кунед.")
    user_states.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: msg.text == "➕ Иловаи Филм" and is_admin(msg.from_user.id))
def add_movie(msg):
    user_states[msg.chat.id] = "waiting_for_movie"
    bot.send_message(msg.chat.id, "Филмро равон кунед:")

@bot.message_handler(func=lambda msg: msg.text == "➕ Иловаи Канал" and is_admin(msg.from_user.id))
def add_channel(msg):
    user_states[msg.chat.id] = "waiting_for_channel"
    bot.send_message(msg.chat.id, "Номи каналро равон кунед (мисол: @kanal):")

@bot.message_handler(func=lambda msg: msg.text == "❌ Нест кардани Филм" and is_admin(msg.from_user.id))
def delete_movie(msg):
    user_states[msg.chat.id] = "waiting_for_delete_movie"
    bot.send_message(msg.chat.id, "ID-и филмро нависед барои нест кардан:")

@bot.message_handler(func=lambda msg: msg.text == "❌ Нест кардани Канал" and is_admin(msg.from_user.id))
def delete_channel(msg):
    if db["channels"]:
        user_states[msg.chat.id] = "waiting_for_delete_channel"
        chs = "\n".join([f"{i+1}. {ch}" for i, ch in enumerate(db["channels"])])
        bot.send_message(msg.chat.id, f"Ин рақамро нависед:\n{chs}")
    else:
        bot.send_message(msg.chat.id, "Канал ёфт нашуд.")

@bot.message_handler(func=lambda msg: msg.text == "🔙 Бозгашт" and is_admin(msg.from_user.id))
def back_to_main(msg):
    start(msg)

@bot.message_handler(func=lambda msg: msg.text == "🔙 Бозгашт ба панел" and is_admin(msg.from_user.id))
def back_to_panel(msg):
    panel(msg)

@bot.message_handler(content_types=["video"])
def save_movie(msg):
    if user_states.get(msg.chat.id) == "waiting_for_movie" and is_admin(msg.from_user.id):
        movie_id = str(random.randint(1000, 9999))
        while movie_id in db["movies"]:
            movie_id = str(random.randint(1000, 9999))
            
        movie_info_temp[msg.chat.id] = {"id": movie_id, "file_id": msg.video.file_id}
        user_states[msg.chat.id] = "waiting_for_movie_info"
        bot.send_message(msg.chat.id, "Маълумоти филмро равон кунед ё /skip нависед:")

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_movie_info")
def add_movie_info(msg):
    movie_info = "" if msg.text == "/skip" else msg.text
    movie_id = movie_info_temp[msg.chat.id]["id"]
    file_id = movie_info_temp[msg.chat.id]["file_id"]

    db["movies"][movie_id] = {"file_id": file_id, "info": movie_info}
    save_db()
    bot.send_message(msg.chat.id, f"Сабт шуд. Қулф ID: {movie_id}")
    user_states.pop(msg.chat.id)
    movie_info_temp.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_channel")
def save_channel(msg):
    if is_admin(msg.from_user.id):
        db["channels"].append(msg.text)
        save_db()
        bot.send_message(msg.chat.id, f"Канал {msg.text} сабт шуд.")
        user_states.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_delete_movie")
def process_delete_movie(msg):
    if is_admin(msg.from_user.id):
        movie_id = msg.text
        if movie_id in db["movies"]:
            db["movies"].pop(movie_id)
            save_db()
            bot.send_message(msg.chat.id, "Филм нест шуд.")
        else:
            bot.send_message(msg.chat.id, "Филм ёфт нашуд.")
        user_states.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_delete_channel")
def process_delete_channel(msg):
    if is_admin(msg.from_user.id):
        try:
            index = int(msg.text) - 1
            if 0 <= index < len(db["channels"]):
                ch = db["channels"].pop(index)
                save_db()
                bot.send_message(msg.chat.id, f"{ch} нест шуд.")
            else:
                bot.send_message(msg.chat.id, "Рақам нодуруст.")
        except:
            bot.send_message(msg.chat.id, "Лутфан рақам нависед.")
        user_states.pop(msg.chat.id)

def schedule_delete_message(chat_id, message_id, delete_time):
    """Функсия барои нест кардани автоматии паёмҳо дар вақти муайян"""
    def delete_message():
        try:
            time.sleep(delete_time)
            bot.delete_message(chat_id, message_id)
        except Exception as e:
            print(f"Хатогӣ ҳангоми нест кардани паём: {e}")
    
    thread = threading.Thread(target=delete_message)
    thread.daemon = True
    thread.start()

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_movie_id")
def process_search_movie(msg):
    movie_id = msg.text
    if is_subscribed(msg.chat.id):
        delete_time = db.get("delete_time", 30)  # Вақти нест кардан (стандартӣ 30 сония)
        
        # Санҷиш барои маҷмӯа
        if movie_id in db["collections"]:
            warning_msg = bot.send_message(msg.chat.id, f"⚠️ Диққат! Филмҳо баъд аз {delete_time} сония нест мешаванд. Агар лозим бошад, нусхаи онҳоро захира кунед.")
            
            sent_messages = []
            for movie in db["collections"][movie_id]["movies"]:
                sent = bot.send_video(msg.chat.id, movie["file_id"])
                sent_messages.append(sent.message_id)
            
            info_msg = bot.send_message(msg.chat.id, f"Маҷмӯаи филмҳо бо ID {movie_id} равон карда шуд.")
            sent_messages.append(info_msg.message_id)
            sent_messages.append(warning_msg.message_id)
            
            # Банақшагирии нест кардани ҳамаи паёмҳо
            for message_id in sent_messages:
                schedule_delete_message(msg.chat.id, message_id, delete_time)
                
        # Санҷиш барои як филм
        elif movie_id in db["movies"]:
            warning_msg = bot.send_message(msg.chat.id, f"⚠️ Диққат! Филм баъд аз {delete_time} сония нест мешавад. Агар лозим бошад, нусхаи онро захира кунед.")
            
            data = db["movies"][movie_id]
            video_msg = bot.send_video(msg.chat.id, data["file_id"])
            
            sent_messages = [video_msg.message_id, warning_msg.message_id]
            
            if data["info"]:
                info_msg = bot.send_message(msg.chat.id, data["info"])
                sent_messages.append(info_msg.message_id)
            
            # Банақшагирии нест кардани ҳамаи паёмҳо
            for message_id in sent_messages:
                schedule_delete_message(msg.chat.id, message_id, delete_time)
        else:
            bot.send_message(msg.chat.id, "Филм ё маҷмӯа бо чунин ID ёфт нашуд.")
    else:
        start(msg)
    user_states.pop(msg.chat.id, None)

@bot.message_handler(func=lambda msg: msg.text.isdigit() and len(msg.text) == 4)
def send_movie(msg):
    movie_id = msg.text
    if is_subscribed(msg.chat.id):
        delete_time = db.get("delete_time", 30)  # Вақти нест кардан (стандартӣ 30 сония)
        
        # Санҷиш барои маҷмӯа
        if movie_id in db["collections"]:
            warning_msg = bot.send_message(msg.chat.id, f"⚠️ Диққат! Филмҳо баъд аз {delete_time} сония нест мешаванд. Агар лозим бошад, нусхаи онҳоро захира кунед.")
            
            sent_messages = []
            for movie in db["collections"][movie_id]["movies"]:
                sent = bot.send_video(msg.chat.id, movie["file_id"])
                sent_messages.append(sent.message_id)
            
            info_msg = bot.send_message(msg.chat.id, f"Маҷмӯаи филмҳо бо ID {movie_id} равон карда шуд.")
            sent_messages.append(info_msg.message_id)
            sent_messages.append(warning_msg.message_id)
            
            # Банақшагирии нест кардани ҳамаи паёмҳо
            for message_id in sent_messages:
                schedule_delete_message(msg.chat.id, message_id, delete_time)
                
        # Санҷиш барои як филм
        elif movie_id in db["movies"]:
            warning_msg = bot.send_message(msg.chat.id, f"⚠️ Диққат! Филм баъд аз {delete_time} сония нест мешавад. Агар лозим бошад, нусхаи онро захира кунед.")
            
            data = db["movies"][movie_id]
            video_msg = bot.send_video(msg.chat.id, data["file_id"])
            
            sent_messages = [video_msg.message_id, warning_msg.message_id]
            
            if data["info"]:
                info_msg = bot.send_message(msg.chat.id, data["info"])
                sent_messages.append(info_msg.message_id)
            
            # Банақшагирии нест кардани ҳамаи паёмҳо
            for message_id in sent_messages:
                schedule_delete_message(msg.chat.id, message_id, delete_time)
        else:
            bot.send_message(msg.chat.id, "Филм ё маҷмӯа бо чунин ID ёфт нашуд.")
    else:
       start(msg)

# Танзимоти вақт
@bot.message_handler(func=lambda msg: msg.text == "⏱ Танзимоти вақт" and is_admin(msg.from_user.id))
def set_delete_time(msg):
    user_states[msg.chat.id] = "waiting_for_delete_time"
    bot.send_message(msg.chat.id, "Лутфан вақти нест кардани филмҳоро бо сония ворид кунед (аз 5 то 120 сония):")

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_delete_time")
def process_delete_time(msg):
    if is_admin(msg.from_user.id):
        try:
            delete_time = int(msg.text)
            if 5 <= delete_time <= 120:
                db["delete_time"] = delete_time
                save_db()
                bot.send_message(msg.chat.id, f"Вақти нест кардани автоматии филмҳо ба {delete_time} сония танзим шуд.")
            else:
                bot.send_message(msg.chat.id, "Вақт бояд аз 5 то 120 сония бошад. Лутфан дубора кӯшиш кунед.")
        except ValueError:
            bot.send_message(msg.chat.id, "Лутфан танҳо рақам ворид кунед.")
        user_states.pop(msg.chat.id)

# Webhook-ро насб мекунем
bot.remove_webhook()
bot.set_webhook(url=f"https://films-bot-9fxf.onrender.com/7947429084:AAECl4VTgRdgv53IAixvZ5qgDMvABI8_d0o")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=11000)
