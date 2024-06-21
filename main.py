import logging
import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PasswordHashInvalidError
from dotenv import load_dotenv
from datetime import datetime
from defunc import *
import pytz
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from allowed_users import ALLOWED_USERS  # Импортируем словарь из отдельного файла
from aiogram.types import InlineKeyboardMarkup as AiogramInlineKeyboardMarkup, \
                          InlineKeyboardButton as AiogramInlineKeyboardButton, \
                          CallbackQuery as AiogramCallbackQuery, \
                          Message as AiogramMessage

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение значений из переменных окружения
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
#allowed_users_str = os.getenv("ALLOWED_USERS")
admin_chat_ids_str = os.getenv("ADMIN_CHAT_IDS")
#allowed_users = [int(user_id) for user_id in allowed_users_str.split(",")]
admin_chat_ids = [int(chat_id) for chat_id in admin_chat_ids_str.split(",")]
allowed_users = ALLOWED_USERS

# Создаем Bot, Dispatcher и FSM Storage
bot = Bot(token=bot_token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())


# Логирование
logging.basicConfig(level=logging.INFO)

# Словарь для хранения состояния пользователя
user_state = {}

# Определение состояний
class Form(StatesGroup):
    awaiting_selection = State()

@dp.callback_query_handler(lambda c: True)
async def handle_callback_query(callback_query: AiogramCallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    if user_id not in allowed_users:
        await callback_query.answer("Не авторизован")
        return

    if callback_query.data == 'analytics':
        await callback_query.answer("Сбор аналитики по аккаунту")
        await send_files_to_bot(bot, admin_chat_ids, user_id)
    elif callback_query.data == 'personal_chats':
        await callback_query.answer("Выгрузка личных чатов")
        await send_files_to_bot(bot, admin_chat_ids, user_id)
    elif callback_query.data == 'group_chats':
        await callback_query.answer("Выгрузка групповых чатов")
        await send_files_to_bot(bot, admin_chat_ids, user_id)
    await state.finish()


# Функция для отображения клавиатуры
async def show_keyboard(user_id):
    keyboard = InlineKeyboardMarkup(row_width=1)
    buttons = [
        InlineKeyboardButton(text="Сбор аналитики по аккаунту", callback_data='analytics'),
        InlineKeyboardButton(text="Выгрузка личных чатов", callback_data='personal_chats'),
        InlineKeyboardButton(text="Выгрузка групповых чатов", callback_data='group_chats')
    ]
    keyboard.add(buttons[0])
    keyboard.add(buttons[1], buttons[2])

    await bot.send_message(user_id, "Выберите направление поиска", reply_markup=keyboard)
    # Устанавливаем состояние "awaiting_selection"
    await Form.awaiting_selection.set()

# Функция what_to_do для отображения клавиатуры при выполнении условий
async def what_to_do(message: types.Message, conditions_met: bool):
    if conditions_met:
        await message.answer("Подключено!")
        await show_keyboard(message.from_user.id)
    else:
        await message.answer("Выбери, что будешь делать!")

# Функция для отправки файлов
async def send_files_to_bot(bot, admin_chat_ids, user_chat_id):
    file_extensions = ['_contacts.xlsx', '_report.html']
    now_utc = datetime.now(pytz.utc)
    timezone = pytz.timezone('Europe/Moscow')
    now_local = now_utc.astimezone(timezone)
    # Форматирование даты и времени
    now = now_local.strftime("%Y-%m-%d %H:%M:%S")
    user_id=user_chat_id
    user_name = ALLOWED_USERS[user_id]

    user_info_message = f"Дата и время выгрузки: {now} \nВыгрузка осуществлена: ({user_name}, {user_id}):"

    # Отправка сообщения с информацией о пользователе админам
    for admin_chat_id in admin_chat_ids:
        await bot.send_message(admin_chat_id, user_info_message)


    # Отправка файлов с информацией пользователю и админам
    for file_extension in file_extensions:
        files_to_send = [file_name for file_name in os.listdir('.') if file_name.endswith(file_extension) and os.path.getsize(file_name) > 0]
    
        for file_to_send in files_to_send:
            for chat_id in [user_chat_id] + admin_chat_ids:
                with open(file_to_send, "rb") as file:
                    await bot.send_document(chat_id, file)
            os.remove(file_to_send)


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

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    if user_id in allowed_users:
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

#Введен номер
@dp.message_handler(lambda message: message.text and 
                    len(re.sub(r'\D', '', message.text)) > 9 and 
                    message.from_user.id in allowed_users)
async def get_phone_number(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
   
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
            'client': client
        }
        await message.reply("Код отправлен на телефон клиента. Введите полученный ПИН")
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")

@dp.message_handler(lambda message: message.text and 
                    'phone_code_hash' in user_state.get(message.from_user.id, {}) and
                    'awaiting_password' not in user_state.get(message.from_user.id, {}))
async def get_code(message: types.Message):
    code = message.text
    phone_number = user_state[message.from_user.id]['phone_number']
    phone_code_hash = user_state[message.from_user.id]['phone_code_hash']

    client = user_state[message.from_user.id].get('client', create_client())  # Используем существующий клиент или создаем новый

    try:
        await client.connect()
        await client.sign_in(phone_number, code, phone_code_hash=str(phone_code_hash))
        #await message.answer("Подключено! Формирую отчет")
        conditions_met = True
        await what_to_do(message, conditions_met)
        #await process_user_data(client, phone_number, message.from_user.id)
        await client.log_out()
        await client.disconnect()
        
        user_state.pop(message.from_user.id, None)  # Удаляем состояние пользователя после успешной обработки
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
                

@dp.message_handler(lambda message: 'awaiting_password' in user_state.get(message.from_user.id, {}))
async def process_password(message: types.Message):
    password = message.text
    client = user_state[message.from_user.id]['client']

    try:
        await client.connect()
        await client.sign_in(password=password)
        
        #await message.answer("Подключено! Формирую отчет")
        phone_number = user_state[message.from_user.id]['phone_number']
        conditions_met = True
        await what_to_do(message, conditions_met)
        #await process_user_data(client, phone_number, message.from_user.id)
        user_state.pop(message.from_user.id, None)  # Удаляем состояние пользователя после успешной обработки
    except PasswordHashInvalidError:
        user_state[message.from_user.id]['password_attempts'] += 1
        if user_state[message.from_user.id]['password_attempts'] >= 3:
            await message.answer("Превышено количество попыток ввода пароля. Перезапусти меня")
            user_state.pop(message.from_user.id, None)
            await client.log_out()
            await client.disconnect()
        else:
            await message.answer(f"Неверный пароль. Попробуйте снова. Попытка {user_state[message.from_user.id]['password_attempts']} из 3.")
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}")
    finally:
        if 'awaiting_password' not in user_state.get(message.from_user.id, {}):
            await client.log_out()
            await client.disconnect()

# Функция для создания нового экземпляра клиента
def create_client():
    return TelegramClient('session_name', api_id, api_hash)






  
# Пример функции для выгрузки личных чатов
async def export_personal_chats(message: Message):
    await message.answer("Выгрузка личных чатов...")

# Пример функции для выгрузки групповых чатов
async def export_group_chats(message: Message):
    await message.answer("Выгрузка групповых чатов...")

# Функция для обработки данных пользователя
async def process_user_data(client, phone_number, user_id):
    await bot.send_message(user_id, "Зашел в функцию")
    selection = '0'
    try:
        userid, userinfo, firstname, lastname, username, photos_user_html = await get_user_info(client, phone_number, selection)
        count_blocked_bot, earliest_date, latest_date, blocked_bot_info, blocked_bot_info_html, user_bots, user_bots_html, list_botblocked = await get_blocked_bot(client, selection)
        delgroups, chat_message_counts, openchannels, closechannels, openchats, closechats, admin_id, user_bots, user_bots_html, list_botexisted = await get_type_of_chats(client, selection)
        groups, i, all_info, openchannel_count, closechannel_count, opengroup_count, closegroup_count, closegroupdel_count, owner_openchannel, owner_closechannel, owner_opengroup, owner_closegroup, public_channels_html, private_channels_html, public_groups_html, private_groups_html, deleted_groups_html = await make_list_of_channels(delgroups, chat_message_counts, openchannels, closechannels, openchats, closechats, selection, client)
        total_contacts, total_contacts_with_phone, total_mutual_contacts = await get_and_save_contacts(client, phone_number, userid, userinfo, firstname, lastname, username)
        #await save_about_channels(phone_number, userid, firstname, lastname, username, openchannel_count, opengroup_count, closechannel_count, closegroup_count, owner_openchannel, owner_closechannel, owner_opengroup, owner_closegroup, openchannels, closechannels, openchats, closechats, delgroups, closegroupdel_count)
        bot_from_search, bot_from_search_html = await get_bot_from_search(client, phone_number, selection, list_botblocked, list_botexisted)
        await generate_html_report(phone_number, userid, userinfo, firstname, lastname, username, total_contacts, total_contacts_with_phone, total_mutual_contacts, openchannel_count, closechannel_count, opengroup_count, closegroup_count, closegroupdel_count, owner_openchannel, owner_closechannel, owner_opengroup, owner_closegroup, public_channels_html, private_channels_html, public_groups_html, private_groups_html, deleted_groups_html, blocked_bot_info_html, user_bots_html, user_id, photos_user_html, bot_from_search_html)
        await send_files_to_bot(bot, admin_chat_ids, user_id)
    except Exception as e:
        logging.error(f"Error processing user data: {e}")

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
