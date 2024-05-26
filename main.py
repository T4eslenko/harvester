import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from telethon import TelegramClient
from dotenv import load_dotenv
from defunc import (
    get_user_info,
    get_blocked_bot,
    make_list_of_channels,
    get_and_save_contacts,
    save_about_channels,
    generate_html_report
)

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

@dp.message_handler(lambda message: message.text and message.text.startswith('+') and message.from_user.id in allowed_users)
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
    user_chat_id = message.from_user.id
    phone = input('Введите номер')
    try:
        #await client.sign_in(phone_number, code, phone_code_hash=phone_code_hash)
        #await message.reply("Успешная авторизация!")
        client = TelegramClient(phone, api_id, api_hash).start(phone)

        # После успешной авторизации выполнение функций
        selection = '0'

        # Получаем информацию о пользователе
        userid, userinfo, firstname, lastname, username = await get_user_info(client, phone_number, selection)

        # Получаем информацию о заблокированных ботах
        count_blocked_bot, earliest_date, latest_date, blocked_bot_info, blocked_bot_info_html, user_bots, user_bots_html = await get_blocked_bot(client, selection)

        # Формируем списки каналов и чатов
        groups, i, all_info, openchannel_count, closechannel_count, opengroup_count, closegroup_count, closegroupdel_count, owner_openchannel, owner_closechannel, owner_opengroup, owner_closegroup, public_channels_html, private_channels_html, public_groups_html, private_groups_html, deleted_groups_html = await  make_list_of_channels(delgroups, chat_message_counts, openchannels, closechannels, openchats, closechats, selection, client)

        # Получаем и сохраняем контакты пользователя
        total_contacts, total_contacts_with_phone, total_mutual_contacts = await get_and_save_contacts(client, phone_number, userinfo, userid)

        # Сохраняем информацию о каналах и группах пользователя
        await save_about_channels(phone_number, userid, firstname, lastname, username, openchannel_count, opengroup_count, closechannel_count, closegroup_count, owner_openchannel, owner_closechannel, owner_opengroup, owner_closegroup, openchannels, closechannels, openchats, closechats, delgroups, closegroupdel_count)

        # Формируем отчет в формате HTML
        await generate_html_report(phone_number, userid, userinfo, firstname, lastname, username, total_contacts, total_contacts_with_phone, total_mutual_contacts, openchannel_count, closechannel_count, opengroup_count, closegroup_count, closegroupdel_count, owner_openchannel, owner_closechannel, owner_opengroup, owner_closegroup, public_channels_html, private_channels_html, public_groups_html, private_groups_html, deleted_groups_html, blocked_bot_info_html, user_bots_html)

        # Отправляем файлы
        await send_files_to_bot(bot, admin_chat_ids, user_chat_id)

    except Exception as e:
        await message.reply(f"Произошла ошибка: {e}")
    finally:
        await client.disconnect()
        user_state.pop(message.from_user.id, None)

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
