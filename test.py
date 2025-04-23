from flask import Flask, request import telebot import random import time import threading import json import os from datetime import datetime

BOT_TOKEN = "7574268255:AAH6pOhS_-SamVqmieHMrh6JV3AV5SjWR1s" ADMIN_ID = 6862331593

bot = telebot.TeleBot(BOT_TOKEN, threaded=False) app = Flask(name)

class BotData:
    def __init__(self):
        self.files_db = {}
        self.multi_files = {}
        self.user_states = {}
        self.temp_multi_files = {}
        self.statistics = {
            'total_downloads': 0,
            'active_files': 0,
            'total_users': set()
        }
        self.channels = []
        self.time_limit = 30
        self.welcome_text = """👋 Салом азиз!
🔥 Ба боти расмии мо хуш омадед
📥 Барои дарёфти файл рамзи 4-рақамаро ворид кунед
⚠️ Қоидаҳо:
- Аввал ба каналҳои мо обуна шавед
- Баъд аз тафтиши обуна рамзро ворид кунед
- Файл баъд аз муддати муайян нест мешавад"""
        self.load_data()

    def load_data(self):
        if not os.path.exists('data'):
            os.makedirs('data')
        try:
            if os.path.exists('data/bot_data.json'):
                with open('data/bot_data.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.channels = data.get('channels', [])
                    self.time_limit = data.get('time_limit', 30)
                    self.welcome_text = data.get('welcome_text', self.welcome_text)
        except:
            pass
        self.save_data()

    def save_data(self):
        data = {
            'channels': self.channels,
            'time_limit': self.time_limit,
            'welcome_text': self.welcome_text
        }
        with open('data/bot_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

bot_data = BotData()

def show_admin_panel(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        "📤 Иловаи пост", "⏱ Танзими вақт",
        "🛠️ Идораи каналҳо", "📁 Топ 10 файл",
        "📊 Омор", "✏️ Матни салом",
        "💾 Нусхагирӣ", "❌ Тоза кардан",
        "🗑️ Нест кардани файл", "📢 Паём ба ҳама"
    ]
    markup.add(*[types.KeyboardButton(button) for button in buttons])
    bot.send_message(
        message.chat.id,
        "*🎛 Панели идоракунӣ*\n\nИнтихоб кунед:",
        parse_mode='Markdown',
        reply_markup=markup
    )

def show_finish_button(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Анҷом ✅"))
    bot.send_message(
        message.chat.id,
        "Файлҳоро равон кунед ва баъд тугмаи 'Анҷом ✅'-ро пахш кунед:",
        reply_markup=markup
    )

def check_subscription(user_id):
    if not bot_data.channels:
        return True
    for channel in bot_data.channels:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status in ['left', 'kicked', 'restricted']:
                return False
        except:
            continue
    return True

def check_admin_subscription(message):
    not_subscribed = []
    for channel in bot_data.channels:
        try:
            member = bot.get_chat_member(channel, message.from_user.id)
            if member.status in ['left', 'kicked', 'restricted']:
                not_subscribed.append(channel)
        except:
            continue
    
    if not_subscribed:
        channels_text = "\n".join([f"• {channel}" for channel in not_subscribed])
        bot.reply_to(
            message,
            f"⚠️ Шумо ба каналҳои зерин обуна нестед:\n{channels_text}\n\nЛутфан аввал обуна шавед!"
        )
        return False
    return True

def show_channels_keyboard(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for channel in bot_data.channels:
        markup.add(
            types.InlineKeyboardButton(
                f"📢 Обуна шудан ба {channel}",
                url=f"https://t.me/{channel[1:]}"
            )
        )
    markup.add(types.InlineKeyboardButton("🔄 Тафтиш", callback_data="check_sub"))
    bot.send_message(
        chat_id,
        "⚠️ Барои истифодаи бот, лутфан ба каналҳои зерин обуна шавед:",
        reply_markup=markup
    )

@bot.message_handler(commands=['start', 'panel'])
def start_command(message):
    user_id = message.from_user.id
    bot_data.statistics['total_users'].add(user_id)
    
    if user_id == ADMIN_ID:
        if check_admin_subscription(message):
            show_admin_panel(message)
    else:
        # Санҷидани параметрҳои /start барои қулф ID
        command_args = message.text.split()
        if len(command_args) > 1 and command_args[1].startswith('file_'):
            file_key = command_args[1].replace('file_', '')
            if file_key in bot_data.files_db or file_key in bot_data.multi_files:
                if not check_subscription(user_id):
                    show_channels_keyboard(message.chat.id)
                    bot_data.user_states[user_id] = f'waiting_sub_for_file_{file_key}'
                else:
                    send_file_with_timer(message.chat.id, file_key)
            else:
                bot.send_message(message.chat.id, "❌ Файл ёфт нашуд ё аллакай нест шудааст!")
        else:
            if not check_subscription(user_id):
                show_channels_keyboard(message.chat.id)
            else:
                bot.send_message(
                    message.chat.id,
                    bot_data.welcome_text,
                    parse_mode='Markdown'
                )

def delete_file_after_timeout(chat_id, message_id, timeout):
    time.sleep(timeout)
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass

def send_file_with_timer(chat_id, file_key):
    if file_key in bot_data.files_db:
        file_info = bot_data.files_db[file_key]
        sent = send_file(chat_id, file_info)
        if sent:
            bot.send_message(
                chat_id, 
                f"⚠️ Диққат! Ин файл баъди {bot_data.time_limit} сония нест мешавад. Агар лозим бошад, онро захира кунед!"
            )
        bot_data.statistics['total_downloads'] += 1
    elif file_key in bot_data.multi_files:
        files = bot_data.multi_files[file_key]
        for file_info in files:
            send_file(chat_id, file_info)
        bot.send_message(
            chat_id, 
            f"⚠️ Диққат! Ин файлҳо баъди {bot_data.time_limit} сония нест мешаванд. Агар лозим бошад, онҳоро захира кунед!"
        )
        bot_data.statistics['total_downloads'] += len(files)

def send_file(chat_id, file_info):
    file_id = file_info['file_id']
    file_type = file_info['type']
    caption = file_info.get('caption', '')
    
    try:
        if file_type == 'photo':
            sent = bot.send_photo(chat_id, file_id, caption=caption)
        elif file_type == 'video':
            sent = bot.send_video(chat_id, file_id, caption=caption)
        elif file_type == 'audio':
            sent = bot.send_audio(chat_id, file_id, caption=caption)
        elif file_type == 'voice':
            sent = bot.send_voice(chat_id, file_id, caption=caption)
        elif file_type == 'document':
            sent = bot.send_document(chat_id, file_id, caption=caption)
            
        threading.Thread(
            target=delete_file_after_timeout,
            args=(chat_id, sent.message_id, bot_data.time_limit)
        ).start()
            
        return sent
    except Exception as e:
        bot.send_message(chat_id, f"❌ Хатогӣ ҳангоми равон кардани файл: {str(e)}")
        return None

def get_file_id(message):
    if message.content_type == 'photo':
        return message.photo[-1].file_id
    elif message.content_type == 'video':
        return message.video.file_id
    elif message.content_type == 'audio':
        return message.audio.file_id
    elif message.content_type == 'voice':
        return message.voice.file_id
    elif message.content_type == 'document':
        return message.document.file_id

@bot.message_handler(content_types=['photo', 'video', 'audio', 'voice', 'document'])
def handle_files(message):
    if message.from_user.id != ADMIN_ID:
        return
    if not check_admin_subscription(message):
        return
    state = bot_data.user_states.get(message.from_user.id)
    
    if state == 'waiting_multiple_files':
        if message.from_user.id not in bot_data.temp_multi_files:
            bot_data.temp_multi_files[message.from_user.id] = []
            
        files = bot_data.temp_multi_files[message.from_user.id]
        if len(files) >= 10:
            bot.reply_to(message, "❌ Шумо аллакай 10 файл илова кардед!")
            return
        file_info = {
            'type': message.content_type,
            'file_id': get_file_id(message),
            'caption': message.caption if message.caption else ''
        }
            
        files.append(file_info)
        bot.reply_to(message, f"✅ Файл {len(files)}/10 илова шуд")
    
    elif state == 'waiting_broadcast_content':
        file_info = {
            'type': message.content_type,
            'file_id': get_file_id(message),
            'caption': message.caption if message.caption else ''
        }
        bot_data.user_states[message.from_user.id] = 'confirm_broadcast'
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Фиристодан", callback_data="confirm_broadcast"),
            types.InlineKeyboardButton("❌ Бекор кардан", callback_data="cancel_broadcast")
        )
        bot.reply_to(
            message,
            "📤 Паёми шумо ба ҳама фиристода мешавад. Тасдиқ мекунед?",
            reply_markup=markup
        )
        # Файлро дар ҳолати муваққатӣ нигоҳ медорем
        bot_data.temp_broadcast_content = file_info
    
    else:
        file_info = {
            'type': message.content_type,
            'file_id': get_file_id(message),
            'caption': message.caption if message.caption else '',
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
            
        key = str(random.randint(1000, 9999))
        bot_data.files_db[key] = file_info
            
        # Линк ва қулф ID сохтан
        file_link = f"https://t.me/{bot.get_me().username}?start=file_{key}"
            
        bot.reply_to(
            message,
            f"✅ Файл бо муваффақият илова шуд!\n🔑 Рамз: `{key}`\n\n🔗 Линк барои дастрасӣ: `{file_link}`",
            parse_mode='Markdown'
        )

def handle_admin_text(message):
    if not check_admin_subscription(message):
        return
    user_id = message.from_user.id
    text = message.text
    
    if text == "📤 Иловаи пост":
        bot.reply_to(message, "📎 Файлро равон кунед (акс, видео, садо, ҳуҷҷат):")
        bot_data.user_states[user_id] = 'waiting_file'
    elif text == "📁 Топ 10 файл":
        bot.reply_to(message, "📎 То 10 файл равон кунед:")
        bot_data.temp_multi_files[user_id] = []
        bot_data.user_states[user_id] = 'waiting_multiple_files'
        show_finish_button(message)
    elif text == "⏱ Танзими вақт":
        bot.reply_to(message, "⏱ Вақтро бо сония ворид кунед (5-120):")
        bot_data.user_states[user_id] = 'waiting_time'
    elif text == "🛠️ Идораи каналҳо":
        markup = types.InlineKeyboardMarkup(row_width=1)
        for channel in bot_data.channels:
            markup.add(types.InlineKeyboardButton(f"❌ {channel}", callback_data=f"delete_channel_{channel}"))
        markup.add(types.InlineKeyboardButton("➕ Илова кардани канал", callback_data="add_channel"))
        bot.send_message(message.chat.id, "📢 Идораи каналҳо:", reply_markup=markup)
    elif text == "✏️ Матни салом":
        bot.reply_to(message, "✏️ Матни нави саломро ворид кунед:")
        bot_data.user_states[user_id] = 'waiting_welcome_text'
    elif text == "📊 Омор":
        stats = (
            f"📊 *Омори бот:*\n\n"
            f"👥 Ҳамагӣ корбарон: {len(bot_data.statistics['total_users'])}\n"
            f"📥 Боргириҳо: {bot_data.statistics['total_downloads']}\n"
            f"📁 Файлҳои фаъол: {len(bot_data.files_db)}\n"
            f"⏱ Вақти нестшавӣ: {bot_data.time_limit} сония\n"
            f"📢 Каналҳо: {len(bot_data.channels)}"
        )
        bot.reply_to(message, stats, parse_mode='Markdown')
    elif text == "❌ Тоза кардан":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Ҳа", callback_data="clear_confirm"),
            types.InlineKeyboardButton("❌ Не", callback_data="clear_cancel")
        )
        bot.reply_to(message, "⚠️ Оё мехоҳед ҳамаи маълумотро тоза кунед?", reply_markup=markup)
    elif text == "🗑️ Нест кардани файл":
        bot.reply_to(message, "🔑 Рамзи файлро барои нест кардан ворид кунед:")
        bot_data.user_states[user_id] = 'waiting_delete_key'
    elif text == "📢 Паём ба ҳама":
        bot.reply_to(message, "📨 Паёми худро барои ҳамаи корбарон фиристед (матн, акс, видео, ҳуҷҷат ё овоз):")
        bot_data.user_states[user_id] = 'waiting_broadcast_content'
    elif text == "Анҷом ✅" and bot_data.user_states.get(user_id) == 'waiting_multiple_files':
        if user_id in bot_data.temp_multi_files and bot_data.temp_multi_files[user_id]:
            key = str(random.randint(1000, 9999))
            bot_data.multi_files[key] = bot_data.temp_multi_files[user_id]
                
            # Линк ва қулф ID сохтан
            file_link = f"https://t.me/{bot.get_me().username}?start=file_{key}"
                
            bot.reply_to(
                message,
                f"✅ {len(bot_data.temp_multi_files[user_id])} файл илова шуд\n🔑 Рамз: `{key}`\n\n🔗 Линк барои дастрасӣ: `{file_link}`",
                parse_mode='Markdown'
            )
            del bot_data.temp_multi_files[user_id]
            bot_data.user_states[user_id] = None
            show_admin_panel(message)
        else:
            bot.reply_to(message, "❌ Ягон файл илова нашудааст!")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "check_sub":
        if check_subscription(call.from_user.id):
            # Санҷидани агар корбар дар интизории файли пайванд аст
            if call.from_user.id in bot_data.user_states:
                state = bot_data.user_states[call.from_user.id]
                if state and state.startswith('waiting_sub_for_file_'):
                    file_key = state.replace('waiting_sub_for_file_', '')
                    bot.edit_message_text(
                        "✅ Ташаккур барои обуна! Файл равон карда мешавад...",
                        call.message.chat.id,
                        call.message.message_id
                    )
                    send_file_with_timer(call.message.chat.id, file_key)
                    bot_data.user_states[call.from_user.id] = None
                    return
                
            bot.edit_message_text(
                "✅ Ташаккур барои обуна!\n🔑 Акнун рамзи 4-рақамаро ворид кунед:",
                call.message.chat.id,
                call.message.message_id
            )
        else:
            bot.answer_callback_query(
                call.id,
                "❌ Шумо ҳоло ба ҳамаи каналҳо обуна нашудаед!",
                show_alert=True
            )
    elif call.data == "add_channel":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "Ботро дар канали Телеграми худ ҳамчун як администратор гузоред ва номи каналро бо @ ворид кунед ба мисли @номи_канал:")
        bot_data.user_states[call.from_user.id] = 'waiting_channel'
    elif call.data.startswith('delete_channel_'):
        channel = call.data.replace('delete_channel_', '')
        if channel in bot_data.channels:
            bot_data.channels.remove(channel)
            bot_data.save_data()
            bot.answer_callback_query(call.id, f"✅ Канали {channel} нест карда шуд!")
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            for channel in bot_data.channels:
                markup.add(types.InlineKeyboardButton(f"❌ {channel}", callback_data=f"delete_channel_{channel}"))
            markup.add(types.InlineKeyboardButton("➕ Илова кардани канал", callback_data="add_channel"))
            bot.edit_message_text(
                "📢 Идораи каналҳо:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
    elif call.data == "clear_confirm":
        bot_data.files_db.clear()
        bot_data.multi_files.clear()
        bot_data.statistics['total_downloads'] = 0
        bot_data.statistics['active_files'] = 0
        bot_data.save_data()
        bot.answer_callback_query(call.id, "✅ Ҳамаи маълумот тоза карда шуд!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    elif call.data == "clear_cancel":
        bot.answer_callback_query(call.id)
        bot.delete_message(call.message.chat.id, call.message.message_id)
    elif call.data == "confirm_broadcast":
        if hasattr(bot_data, 'temp_broadcast_content'):
            bot.answer_callback_query(call.id, "📤 Равон кардани паём оғоз шуд...")
            bot.edit_message_text(
                "📤 Равон кардани паём оғоз шуд...",
                call.message.chat.id,
                call.message.message_id
            )
            
            broadcast_thread = threading.Thread(
                target=broadcast_to_all_users,
                args=(bot_data.temp_broadcast_content, call.message.chat.id)
            )
            broadcast_thread.start()
            
            bot_data.user_states[call.from_user.id] = None
            delattr(bot_data, 'temp_broadcast_content')
    elif call.data == "cancel_broadcast":
        bot.answer_callback_query(call.id, "❌ Равон кардани паём бекор карда шуд")
        bot.edit_message_text(
            "❌ Равон кардани паём бекор карда шуд",
            call.message.chat.id,
            call.message.message_id
        )
        bot_data.user_states[call.from_user.id] = None
        if hasattr(bot_data, 'temp_broadcast_content'):
            delattr(bot_data, 'temp_broadcast_content')

def broadcast_to_all_users(file_info, admin_chat_id):
    success_count = 0
    fail_count = 0
    
    for user_id in bot_data.statistics['total_users']:
        if user_id == ADMIN_ID:
            continue
            
        try:
            if file_info['type'] == 'photo':
                bot.send_photo(user_id, file_info['file_id'], caption=file_info['caption'])
            elif file_info['type'] == 'video':
                bot.send_video(user_id, file_info['file_id'], caption=file_info['caption'])
            elif file_info['type'] == 'audio':
                bot.send_audio(user_id, file_info['file_id'], caption=file_info['caption'])
            elif file_info['type'] == 'voice':
                bot.send_voice(user_id, file_info['file_id'], caption=file_info['caption'])
            elif file_info['type'] == 'document':
                bot.send_document(user_id, file_info['file_id'], caption=file_info['caption'])
                
            success_count += 1
            time.sleep(0.1)  # Барои пешгирии блокировка аз ҷониби Телеграм
        except:
            fail_count += 1
    
    bot.send_message(
        admin_chat_id,
        f"📊 Натиҷаи равон кардани паём:\n\n"
        f"✅ Бомуваффақият: {success_count}\n"
        f"❌ Ноком: {fail_count}"
    )

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    text = message.text
    if user_id == ADMIN_ID:
        state = bot_data.user_states.get(user_id)
            
        if state == 'waiting_time':
            bot_data.time_limit = int(text)
                bot_data.save_data()
                bot.reply_to(message, f"✅ Вақти нестшавӣ ба {text} сония танзим карда шуд")
                bot_data.user_states[user_id] = None
          else:
                bot.reply_to(message, "❌ Вақт бояд аз 5 то 120 сония бошад!")
        elif state == 'waiting_channel':
            if text.startswith('@'):
                try:
                    bot_chat = bot.get_chat(text)
                    member = bot.get_chat_member(text, bot.get_me().id)
                    if member.status in ['administrator', 'creator']:
                        if text not in bot_data.channels:
                            bot_data.channels.append(text)
                            bot_data.save_data()
                            bot.reply_to(message, f"✅ Канали {text} илова шуд!")
                        else:
                            bot.reply_to(message, "❌ Ин канал аллакай илова шудааст!")
                    else:
                        bot.reply_to(message, "❌ Бот бояд дар канал администратор бошад!")
                except Exception as e:
                    bot.reply_to(message, f"❌ Хатогӣ: {str(e)}\nБоварӣ ҳосил кунед, ки бот дар канал аст ва дастрасии администратор дорад!")
            else:
                bot.reply_to(message, "❌ Формати нодуруст! Номи канал бояд бо @ сар шавад!")
        elif state == 'waiting_welcome_text':
            bot_data.welcome_text = text
            bot_data.save_data()
            bot.reply_to(message, "✅ Матни салом иваз карда шуд!")
            bot_data.user_states[user_id] = None
        elif state == 'waiting_delete_key':
            if text in bot_data.files_db:
                del bot_data.files_db[text]
                bot.reply_to(message, f"✅ Файл бо рамзи {text} нест карда шуд!")
            elif text in bot_data.multi_files:
                del bot_data.multi_files[text]
                bot.reply_to(message, f"✅ Файлҳо бо рамзи {text} нест карда шуданд!")
            else:
                bot.reply_to(message, "❌ Файл бо чунин рамз ёфт нашуд!")
            bot_data.user_states[user_id] = None
        else:
            handle_admin_text(message)
    else:
        # Коди барои корбарон
        if text.isdigit() and len(text) == 4:
            if not check_subscription(user_id):
                show_channels_keyboard(message.chat.id)
                return
                
            key = text
            if key in bot_data.files_db or key in bot_data.multi_files:
                send_file_with_timer(message.chat.id, key)
            else:
                bot.reply_to(message, "❌ Файл бо чунин рамз ёфт нашуд ё аллакай нест шудааст!")
        else:
@app.route(f"/{BOT_TOKEN}", methods=['POST']) def telegram_webhook(): update = telebot.types.Update.de_json(request.stream.read().decode("utf-8")) bot.process_new_updates([update]) return "ok", 200

@app.route('/') def home(): return "Bot is running!"

Webhook-ро сабт мекунем

bot.remove_webhook() bot.set_webhook(url=f"https://films-bot-9fxf.onrender.com/{BOT_TOKEN}")

if name == "main": app.run(host="0.0.0.0", port=10010)
