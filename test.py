from flask import Flask, request
import telebot
import json
import random
import threading
import time
import re

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

def extract_channel_username(text):
    # Санҷидани линки мустақим
    if "t.me/" in text:
        match = re.search(r't\.me/(\w+)', text)
        if match:
            return "@" + match.group(1)
    # Агар номи канал бошад, "@" илова мекунем агар набошад
    elif text.startswith("@"):
        return text
    else:
        return "@" + text

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
            
        bot.send_message(msg.chat.id, "**Хуш омадед ба боти филмҳо!**", reply_markup=markup, parse_mode="Markdown")
    else:
        markup = telebot.types.InlineKeyboardMarkup()
        for ch in db["channels"]:
            markup.add(telebot.types.InlineKeyboardButton("Обуна шудан", url=f"https://t.me/{ch.replace('@', '')}"))
        markup.add(telebot.types.InlineKeyboardButton("Санҷиш", callback_data="check_sub"))
        bot.send_message(msg.chat.id, "**Аввал ба каналҳо обуна шавед:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🔍 Ҷустуҷӯи филм")
def search_movie_handler(msg):
    if is_subscribed(msg.chat.id):
        user_states[msg.chat.id] = "waiting_for_movie_id"
        bot.send_message(msg.chat.id, "**Лутфан ID филмро равон кунед:**", parse_mode="Markdown")
    else:
        start(msg)

@bot.message_handler(func=lambda msg: msg.text == "📺 Филмҳои нав")
def new_movies(msg):
    if is_subscribed(msg.chat.id):
        # Гирифтани 5 филми охирин
        movie_ids = list(db["movies"].keys())
        if movie_ids:
            response = "**Филмҳои нав:**\n\n"
            # Гирифтани то 5 филми охирин
            for movie_id in movie_ids[-5:]:
                info = db["movies"][movie_id].get("info", "")
                response += f"**🎬 ID: {movie_id}**\n{info}\n\n"
            bot.send_message(msg.chat.id, response, parse_mode="Markdown")
        else:
            bot.send_message(msg.chat.id, "**Ҳоло ягон филм илова нашудааст.**", parse_mode="Markdown")
    else:
        start(msg)

@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Дар бораи мо")
def about_us(msg):
    if is_subscribed(msg.chat.id):
        bot.send_message(msg.chat.id, "**Ин бот барои тамошои филмҳо бо сифати баланд тайёр шудааст.**\n\n**Барои дастрасӣ ба филмҳо, ID-и филмро ворид кунед.**", parse_mode="Markdown")
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
            
        bot.send_message(call.message.chat.id, "**Офарин! Шумо метавонед ботро истифода баред.**", reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(call.message.chat.id, "**Лутфан аввал обуна шавед.**", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "👨‍💻 Панели админ" and is_admin(msg.from_user.id))
def panel(msg):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Иловаи Филм", "➕ Иловаи Канал")
    markup.add("❌ Нест кардани Филм", "❌ Нест кардани Канал")
    markup.add("📚 Маҷмӯаи филмҳо")
    markup.add("👨‍💼 Идоракунии админҳо")
    markup.add("⏱ Танзимоти вақт", "📊 Статистика")
    markup.add("🗑 Тозакунии кэш", "🔄 Барқароркунӣ")
    markup.add("🔙 Бозгашт")
    bot.send_message(msg.chat.id, "**Панели админ:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "👨‍💼 Идоракунии админҳо" and is_admin(msg.from_user.id))
def admin_management(msg):
    if msg.from_user.id == ADMIN_ID:  # Фақат админи аслӣ метавонад админҳоро идора кунад
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Иловаи админ", "❌ Нест кардани админ")
        markup.add("🔙 Бозгашт ба панел")
        bot.send_message(msg.chat.id, "**Идоракунии админҳо:**", reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(msg.chat.id, "**Шумо иҷозат надоред.**", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "➕ Иловаи админ" and msg.from_user.id == ADMIN_ID)
def add_admin(msg):
    user_states[msg.chat.id] = "waiting_for_admin_id"
    bot.send_message(msg.chat.id, "**ID-и админи навро равон кунед:**", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "❌ Нест кардани админ" and msg.from_user.id == ADMIN_ID)
def delete_admin(msg):
    if len(db["admins"]) > 1:
        # Сохтани кнопкаҳои шишагин барои ҳар як админ
        markup = telebot.types.InlineKeyboardMarkup()
        for admin_id in db["admins"]:
            if admin_id != ADMIN_ID:  # Админи аслиро нишон намедиҳем
                markup.add(telebot.types.InlineKeyboardButton(
                    f"🗑 Admin ID: {admin_id}", 
                    callback_data=f"del_admin_{admin_id}"
                ))
        
        markup.add(telebot.types.InlineKeyboardButton("🔙 Бозгашт", callback_data="back_to_admin_panel"))
        bot.send_message(msg.chat.id, "**Админро барои нест кардан интихоб кунед:**", reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(msg.chat.id, "**Дар система танҳо як админ мавҷуд аст.**", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_admin_"))
def callback_delete_admin(call):
    if call.from_user.id == ADMIN_ID:
        admin_id = int(call.data.split("_")[2])
        if admin_id in db["admins"] and admin_id != ADMIN_ID:
            db["admins"].remove(admin_id)
            save_db()
            bot.answer_callback_query(call.id, f"Админ бо ID {admin_id} нест карда шуд")
            bot.edit_message_text(
                chat_id=call.message.chat.id, 
                message_id=call.message.message_id,
                text=f"**Админ бо ID {admin_id} нест карда шуд.**",
                parse_mode="Markdown"
            )
        else:
            bot.answer_callback_query(call.id, "Хатогӣ ҳангоми нест кардани админ")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_admin_panel")
def callback_back_to_admin(call):
    if call.from_user.id == ADMIN_ID:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        admin_management(call.message)

@bot.message_handler(func=lambda msg: msg.text == "📚 Маҷмӯаи филмҳо" and is_admin(msg.from_user.id))
def collection_menu(msg):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Сохтани маҷмӯа", "❌ Нест кардани маҷмӯа")
    markup.add("📋 Рӯйхати маҷмӯаҳо")
    markup.add("🔙 Бозгашт ба панел")
    bot.send_message(msg.chat.id, "**Идоракунии маҷмӯаҳои филм:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "➕ Сохтани маҷмӯа" and is_admin(msg.from_user.id))
def create_collection(msg):
    collection_temp[msg.chat.id] = {"movies": []}
    user_states[msg.chat.id] = "waiting_for_collection_movie"
    
    # Кнопкаи [ анҷом ] дар поён 
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("[ анҷом ]")
    
    bot.send_message(
        msg.chat.id, 
        "**Филми якумро равон кунед (то 10 филм метавонед).**\n**Барои анҷом кнопкаи [ анҷом ] пахш кунед:**", 
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: msg.text == "❌ Нест кардани маҷмӯа" and is_admin(msg.from_user.id))
def delete_collection(msg):
    if db["collections"]:
        markup = telebot.types.InlineKeyboardMarkup()
        for coll_id, info in db["collections"].items():
            markup.add(telebot.types.InlineKeyboardButton(
                f"🗑 ID: {coll_id} ({len(info['movies'])} филм)", 
                callback_data=f"del_coll_{coll_id}"
            ))
        
        markup.add(telebot.types.InlineKeyboardButton("🔙 Бозгашт", callback_data="back_to_collection_menu"))
        bot.send_message(msg.chat.id, "**Маҷмӯаро барои нест кардан интихоб кунед:**", reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(msg.chat.id, "**Ягон маҷмӯа мавҷуд нест.**", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_coll_"))
def callback_delete_collection(call):
    if is_admin(call.from_user.id):
        coll_id = call.data.split("_")[2]
        if coll_id in db["collections"]:
            del db["collections"][coll_id]
            save_db()
            bot.answer_callback_query(call.id, f"Маҷмӯа бо ID {coll_id} нест карда шуд")
            bot.edit_message_text(
                chat_id=call.message.chat.id, 
                message_id=call.message.message_id,
                text=f"**Маҷмӯа бо ID {coll_id} нест карда шуд.**",
                parse_mode="Markdown"
            )
        else:
            bot.answer_callback_query(call.id, "Хатогӣ ҳангоми нест кардани маҷмӯа")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_collection_menu")
def callback_back_to_collection(call):
    if is_admin(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        collection_menu(call.message)

@bot.message_handler(func=lambda msg: msg.text == "📋 Рӯйхати маҷмӯаҳо" and is_admin(msg.from_user.id))
def list_collections(msg):
    if db["collections"]:
        collections = "\n\n".join([f"**🎬 ID: {coll_id}**\n**Шумораи филмҳо: {len(info['movies'])}**" 
                                 for coll_id, info in db["collections"].items()])
        bot.send_message(msg.chat.id, f"**Рӯйхати маҷмӯаҳо:**\n\n{collections}", parse_mode="Markdown")
    else:
        bot.send_message(msg.chat.id, "**Ягон маҷмӯа мавҷуд нест.**", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_collection_movie")
def add_movie_to_collection(msg):
    if msg.text == "анҷом" or msg.text == "[ анҷом ]":
        if collection_temp[msg.chat.id]["movies"]:
            collection_id = str(random.randint(1000, 9999))
            while collection_id in db["collections"]:
                collection_id = str(random.randint(1000, 9999))
                
            db["collections"][collection_id] = collection_temp[msg.chat.id]
            save_db()
            
            # Барқарор кардани клавиатураи админ
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("➕ Сохтани маҷмӯа", "❌ Нест кардани маҷмӯа")
            markup.add("📋 Рӯйхати маҷмӯаҳо")
            markup.add("🔙 Бозгашт ба панел")
            
            bot.send_message(
                msg.chat.id, 
                f"**Маҷмӯа сохта шуд. ID маҷмӯа: {collection_id}**", 
                reply_markup=markup,
                parse_mode="Markdown"
            )
            del collection_temp[msg.chat.id]
            user_states.pop(msg.chat.id)
        else:
            bot.send_message(msg.chat.id, "**Шумо бояд ҳадди ақал як филм илова кунед.**", parse_mode="Markdown")
    elif msg.content_type == 'video':
        if len(collection_temp[msg.chat.id]["movies"]) >= 10:
            bot.send_message(msg.chat.id, "**Шумо аллакай 10 филм илова кардед. Барои анҷом [ анҷом ] пахш кунед.**", parse_mode="Markdown")
        else:
            movie_data = {"file_id": msg.video.file_id}
            collection_temp[msg.chat.id]["movies"].append(movie_data)
            movie_count = len(collection_temp[msg.chat.id]["movies"])
            bot.send_message(msg.chat.id, f"**Филми {movie_count} илова шуд. Филми навбатиро равон кунед ё [ анҷом ] пахш кунед:**", parse_mode="Markdown")
    else:
        bot.send_message(msg.chat.id, "**Лутфан филм равон кунед ё [ анҷом ] пахш кунед.**", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_admin_id")
def process_add_admin(msg):
    try:
        admin_id = int(msg.text)
        if admin_id not in db["admins"]:
            db["admins"].append(admin_id)
            save_db()
            bot.send_message(msg.chat.id, f"**Админ бо ID {admin_id} илова шуд.**", parse_mode="Markdown")
        else:
            bot.send_message(msg.chat.id, "**Ин ID аллакай дар рӯйхати админҳо мавҷуд аст.**", parse_mode="Markdown")
    except ValueError:
        bot.send_message(msg.chat.id, "**Лутфан танҳо рақам ворид кунед.**", parse_mode="Markdown")
    user_states.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: msg.text == "➕ Иловаи Филм" and is_admin(msg.from_user.id))
def add_movie(msg):
    user_states[msg.chat.id] = "waiting_for_movie"
    bot.send_message(msg.chat.id, "**Филмро равон кунед:**", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "➕ Иловаи Канал" and is_admin(msg.from_user.id))
def add_channel(msg):
    user_states[msg.chat.id] = "waiting_for_channel"
    bot.send_message(msg.chat.id, "**Номи канал ё линки мустақими онро равон кунед:**\n**(мисол: @kanal ё t.me/kanal)**", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "❌ Нест кардани Филм" and is_admin(msg.from_user.id))
def delete_movie(msg):
    user_states[msg.chat.id] = "waiting_for_delete_movie"
    bot.send_message(msg.chat.id, "**ID-и филмро нависед барои нест кардан:**", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "❌ Нест кардани Канал" and is_admin(msg.from_user.id))
def delete_channel(msg):
    if db["channels"]:
        markup = telebot.types.InlineKeyboardMarkup()
        for ch in db["channels"]:
            markup.add(telebot.types.InlineKeyboardButton(f"🗑 {ch}", callback_data=f"del_ch_{db['channels'].index(ch)}"))
        
        markup.add(telebot.types.InlineKeyboardButton("🔙 Бозгашт", callback_data="back_to_panel"))
        bot.send_message(msg.chat.id, "**Каналро барои нест кардан интихоб кунед:**", reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(msg.chat.id, "**Канал ёфт нашуд.**", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_ch_"))
def callback_delete_channel(call):
    if is_admin(call.from_user.id):
        try:
            index = int(call.data.split("_")[2])
            if 0 <= index < len(db["channels"]):
                ch = db["channels"].pop(index)
                save_db()
                bot.answer_callback_query(call.id, f"Канал {ch} нест карда шуд")
                bot.edit_message_text(
                    chat_id=call.message.chat.id, 
                    message_id=call.message.message_id,
                    text=f"**Канал {ch} нест карда шуд.**",
                    parse_mode="Markdown"
                )
            else:
                bot.answer_callback_query(call.id, "Хатогӣ ҳангоми нест кардани канал")
        except Exception as e:
            bot.answer_callback_query(call.id, f"Хатогӣ: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_panel")
def callback_back_to_panel(call):
    if is_admin(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        panel(call.message)

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
        bot.send_message(msg.chat.id, "**Маълумоти филмро равон кунед ё /skip нависед:**", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_movie_info")
def add_movie_info(msg):
    movie_info = "" if msg.text == "/skip" else msg.text
    movie_id = movie_info_temp[msg.chat.id]["id"]
    file_id = movie_info_temp[msg.chat.id]["file_id"]

    db["movies"][movie_id] = {"file_id": file_id, "info": movie_info}
    save_db()
    bot.send_message(msg.chat.id, f"**Сабт шуд. ID филм: {movie_id}**", parse_mode="Markdown")
    user_states.pop(msg.chat.id)
    movie_info_temp.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_channel")
def save_channel(msg):
    if is_admin(msg.from_user.id):
        channel = extract_channel_username(msg.text)
        
        # Санҷиш барои канали мавҷуд
        if channel in db["channels"]:
            bot.send_message(msg.chat.id, "**Ин канал аллакай дар бот мавҷуд аст.**", parse_mode="Markdown")
            return
        
        # Санҷидани дурустии канал
        try:
            bot.get_chat(channel)
            db["channels"].append(channel)
            save_db()
            bot.send_message(msg.chat.id, f"**Канал {channel} сабт шуд.**", parse_mode="Markdown")
        except Exception as e:
            bot.send_message(msg.chat.id, f"**Хатогӣ ҳангоми сабти канал: {e}**\n**Боварӣ ҳосил кунед, ки номи канал ё линк дуруст аст.**", parse_mode="Markdown")
        user_states.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_delete_movie")
def process_delete_movie(msg):
    if is_admin(msg.from_user.id):
        movie_id = msg.text
        if movie_id in db["movies"]:
            db["movies"].pop(movie_id)
            save_db()
            bot.send_message(msg.chat.id, "**Филм нест шуд.**", parse_mode="Markdown")
        else:
            bot.send_message(msg.chat.id, "**Филм ёфт нашуд.**", parse_mode="Markdown")
        user_states.pop(msg.chat.id)

def schedule_delete_message(chat_id, message_id, delete_time):
    """Функсия барои нест кардани автоматии паём баъд аз вақти муайян"""
    time.sleep(delete_time)
    try:
        bot.delete_message(chat_id, message_id)
    except Exception as e:
        print(f"Хатогӣ ҳангоми нест кардани паём: {e}")

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_movie_id")
def serve_movie(msg):
    if is_subscribed(msg.chat.id):
        # Санҷиш барои ID филм
        movie_id = msg.text
        
        # Санҷиш барои маҷмӯа
        if movie_id in db["collections"]:
            # Равон кардани ҳамаи филмҳои маҷмӯа
            bot.send_message(msg.chat.id, "**Маҷмӯаи филмҳо бо ID " + movie_id + ":**", parse_mode="Markdown")
            for movie in db["collections"][movie_id]["movies"]:
                sent_movie = bot.send_video(msg.chat.id, movie["file_id"])
                # Нест кардани филмҳо баъд аз вақти муайян
                threading.Thread(target=schedule_delete_message, args=(msg.chat.id, sent_movie.message_id, db["delete_time"])).start()
        elif movie_id in db["movies"]:
            # Равон кардани як филм
            movie_data = db["movies"][movie_id]
            info_text = movie_data.get("info", "")
            caption = f"**🎬 ID: {movie_id}**\n{info_text}" if info_text else f"**🎬 ID: {movie_id}**"
            
            # Равон кардани филм
            sent_movie = bot.send_video(msg.chat.id, movie_data["file_id"], caption=caption, parse_mode="Markdown")
            
            # Нест кардани филм баъд аз вақти муайян
            threading.Thread(target=schedule_delete_message, args=(msg.chat.id, sent_movie.message_id, db["delete_time"])).start()
        else:
            bot.send_message(msg.chat.id, "**Филм ё маҷмӯа бо чунин ID ёфт нашуд.**", parse_mode="Markdown")
            
        user_states.pop(msg.chat.id)
    else:
        start(msg)

@bot.message_handler(func=lambda msg: msg.text == "⏱ Танзимоти вақт" and is_admin(msg.from_user.id))
def delete_time_settings(msg):
    user_states[msg.chat.id] = "waiting_for_delete_time"
    bot.send_message(
        msg.chat.id, 
        f"**Вақти ҷорӣ барои нест кардани филмҳо: {db['delete_time']} сония.**\n**Вақти навро бо сония ворид кунед:**",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_delete_time")
def set_delete_time(msg):
    if is_admin(msg.from_user.id):
        try:
            new_time = int(msg.text)
            if new_time > 0:
                db["delete_time"] = new_time
                save_db()
                bot.send_message(msg.chat.id, f"**Вақти нави нест кардани филмҳо: {new_time} сония.**", parse_mode="Markdown")
            else:
                bot.send_message(msg.chat.id, "**Вақт бояд бештар аз 0 бошад.**", parse_mode="Markdown")
        except ValueError:
            bot.send_message(msg.chat.id, "**Лутфан танҳо рақам ворид кунед.**", parse_mode="Markdown")
        user_states.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: msg.text == "📊 Статистика" and is_admin(msg.from_user.id))
def statistics(msg):
    movies_count = len(db["movies"])
    collections_count = len(db["collections"])
    channels_count = len(db["channels"])
    admins_count = len(db["admins"])
    
    stats = f"**📊 Статистика:**\n\n"
    stats += f"**📽 Шумораи филмҳо: {movies_count}**\n"
    stats += f"**📚 Шумораи маҷмӯаҳо: {collections_count}**\n"
    stats += f"**📢 Шумораи каналҳо: {channels_count}**\n"
    stats += f"**👨‍💼 Шумораи админҳо: {admins_count}**\n"
    
    bot.send_message(msg.chat.id, stats, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🗑 Тозакунии кэш" and is_admin(msg.from_user.id))
def clear_cache(msg):
    # Тозакунии ҳамаи мутағайирҳои муваққатӣ
    user_states.clear()
    movie_info_temp.clear()
    collection_temp.clear()
    
    bot.send_message(msg.chat.id, "**Кэш тоза карда шуд.**", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🔄 Барқароркунӣ" and is_admin(msg.from_user.id))
def reboot_bot(msg):
    bot.send_message(msg.chat.id, "**Бот аз нав сар карда шуд.**", parse_mode="Markdown")
    # Барқарор кардани ҳамаи мутағайирҳои муваққатӣ
    user_states.clear()
    movie_info_temp.clear()
    collection_temp.clear()
    
    # Аз нав хондани маълумот аз файл
    try:
        with open("data.json", "r") as f:
            global db
            db = json.load(f)
    except:
        pass

@bot.message_handler(func=lambda msg: True)
def handle_all_messages(msg):
    # Агар паём ID-и филм бошад
    if msg.text.isdigit() and msg.text in db["movies"]:
        if is_subscribed(msg.chat.id):
            movie_data = db["movies"][msg.text]
            info_text = movie_data.get("info", "")
            caption = f"**🎬 ID: {msg.text}**\n{info_text}" if info_text else f"**🎬 ID: {msg.text}**"
            
            # Равон кардани филм
            sent_movie = bot.send_video(msg.chat.id, movie_data["file_id"], caption=caption, parse_mode="Markdown")
            
            # Нест кардани филм баъд аз вақти муайян
            threading.Thread(target=schedule_delete_message, args=(msg.chat.id, sent_movie.message_id, db["delete_time"])).start()
        else:
            start(msg)
    # Агар паём ID-и маҷмӯа бошад
    elif msg.text in db["collections"]:
        if is_subscribed(msg.chat.id):
            # Равон кардани ҳамаи филмҳои маҷмӯа
            bot.send_message(msg.chat.id, "**Маҷмӯаи филмҳо бо ID " + msg.text + ":**", parse_mode="Markdown")
            for movie in db["collections"][msg.text]["movies"]:
                sent_movie = bot.send_video(msg.chat.id, movie["file_id"])
                # Нест кардани филмҳо баъд аз вақти муайян
                threading.Thread(target=schedule_delete_message, args=(msg.chat.id, sent_movie.message_id, db["delete_time"])).start()
        else:
            start(msg)
    else:
        # Агар админ аст, нишон додани панели админ
        if is_admin(msg.from_user.id) and msg.text == "/admin":
            panel(msg)

# Оғози бот
if __name__ == "__main__":
    # Барқарор кардани вебхук
    bot.remove_webhook()
    bot.set_webhook(url=f"https://films-bot-9fxf.onrender.com/7947429084:AAECl4VTgRdgv53IAixvZ5qgDMvABI8_d0o")
    
    # Оғози сервер Flask
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 11000)))
