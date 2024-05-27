import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from telethon import TelegramClient
from dotenv import load_dotenv
from defunc import *
from telethon.errors import SessionPasswordNeededError
from datetime import datetime

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение значений из переменных окружения
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
allowed_users_str = os.getenv("ALLOWED_USERS")
admin_chat_ids_str = os.getenv("ADMIN_CHAT_IDS")
allowed_users = [int(user_id) for user_id in allowed_users_str.split(",")]
admin_chat_ids = [int(chat_id) for chat_id in admin_chat_ids_str.split(",")]

# Создаем TelegramClient и Bot
client = TelegramClient('session_name', api_id, api_hash)
bot = Bot(token=bot_token)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Логирование
logging.basicConfig(level=logging.INFO)

# Словарь для хранения состояния пользователя
user_state = {}

# Функция для отправки файлов
async def send_files_to_bot(bot, admin_chat_ids, user_chat_id):
    file_extensions = ['_messages.xlsx', '_participants.xlsx', '_contacts.xlsx', '_about.xlsx', '_report.html', '_report.pdf']
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_info_message = f"Выгрузка осуществлена пользователем ID: {user_chat_id} \nДата и время выгрузки: {now}"

    for file_extension in file_extensions:
        files_to_send = [file_name for file_name in os.listdir('.') if file_name.endswith(file_extension) and os.path.getsize(file_name) > 0]

        for file_to_send in files_to_send:
            for admin_chat_id in admin_chat_ids:
                with open(file_to_send, "rb") as file:
                    await bot.send_document(admin_chat_id, file)
            if user_chat_id:
                with open(file_to_send, "rb") as file:
                    await bot.send_document(user_chat_id, file)
            os.remove(file_to_send)

    # Отправка сообщения с информацией о пользователе админам
    for admin_chat_id in admin_chat_ids:
        await bot.send_message(admin_chat_id, user_info_message)

# Обработчики сообщений
@dp.message_handler(lambda message: message.from_user.id not in allowed_users)
async def unauthorized(message: types.Message):
    await message.reply("Извините, вы не авторизованы для использования этого бота.")

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    if message.from_user.id in allowed_users:
        await message.reply("Добро пожаловать! Пожалуйста, введите ваш номер телефона в международном формате.")
    else:
        await unauthorized(message)

@dp.message_handler(lambda message: message.text and 
                    message.text.startswith('+') and 
                    message.text[1:].isdigit() and 
                    len(message.text) > 10 and 
                    message.from_user.id in allowed_users)
async def get_phone_number(message: types.Message):
    phone_number = message.text
    
    user_state[message.from_user.id] = {'phone_number': phone_number}
    
    try:
        await client.connect()
        
        # Проверка, авторизован ли пользователь
        if await client.is_user_authorized():
            await message.reply("Вы уже авторизованы.")
            return
        
        phone_code_hash = await client.send_code_request(phone_number)
        user_state[message.from_user.id]['phone_code_hash'] = phone_code_hash
        await message.reply("Код отправлен на ваш номер. Пожалуйста, введите код, который вы получили.")
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")

@dp.message_handler(lambda message: message.text and 
                    'phone_code_hash' in user_state.get(message.from_user.id, {}) and
                    'awaiting_password' not in user_state.get(message.from_user.id, {}))
async def get_code(message: types.Message):
    code = message.text
    phone_number = user_state[message.from_user.id]['phone_number']
    phone_code_hash = user_state[message.from_user.id]['phone_code_hash']

    try:
        await client.connect()
        
        # Проверяем, что пин-код состоит из 5 цифр
        if len(code) != 5 or not code.isdigit():
            raise ValueError("Пин-код должен состоять из 5 цифр.")
                
        await client.sign_in(phone_number, code, phone_code_hash=phone_code_hash.phone_code_hash)
        
        await message.reply("Успешная авторизация!")
        await process_user_data(client, phone_number, message.from_user.id)
    except SessionPasswordNeededError:
        await message.reply("Необходим пароль двухфакторной аутентификации. Пожалуйста, введите ваш пароль.")
        user_state[message.from_user.id]['awaiting_password'] = True
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")
    finally:
        await client.log_out()
        await client.disconnect()

@dp.message_handler(lambda message: 'awaiting_password' in user_state.get(message.from_user.id, {}))
async def process_password(message: types.Message):
    password = message.text
    phone_number = user_state[message.from_user.id]['phone_number']
    phone_code_hash = user_state[message.from_user.id]['phone_code_hash']

    try:
        await client.connect()
        await client.sign_in(phone_number=phone_number, password=password, phone_code_hash=phone_code_hash.phone_code_hash)
        await message.reply("Успешная авторизация!")
        await process_user_data(client, phone_number, message.from_user.id)
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")
    finally:
        await client.log_out()
        await client.disconnect()
        user_state.pop(message.from_user.id, None)

# Функция для создания нового экземпляра клиента
def create_client():
    return TelegramClient('session_name', api_id, api_hash)

# Функция для обработки данных пользователя
async def process_user_data(client, phone_number, user_id):
    # Здесь можно добавить логику обработки данных пользователя
    pass

# Запуск бота
if __name__ == '__main__':
    executor.start_poll
