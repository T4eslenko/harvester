import qrcode

@dp.message_handler(commands=['start_qr'])
async def start_via_qr_code(message: types.Message):
    user_id = message.from_user.id
    if user_id in allowed_users:
        user_state[user_id] = {
            'connected': False,
            'type': "",
            'selection': "", 
            'phone_number': "login by qr-code",  # Здесь необходимо указать правильное значение    
        }
        now_utc = datetime.now(pytz.utc)
        timezone = pytz.timezone('Europe/Moscow')
        now_local = now_utc.astimezone(timezone)
        now = now_local.strftime("%d.%m.%Y %H:%M:%S")
        user_name = allowed_users[user_id]
        user_info_message = f"Авторизованный пользователь: ({user_name}, id: {user_id}) запустил бота.\nДата и время запуска: {now}"
        for admin_chat_id in admin_chat_ids:
            await bot.send_message(admin_chat_id, user_info_message)
          
        try:
            # Создаем новый экземпляр клиента
            client = create_client()
            await client.connect()
            
            # Разлогиниваемся от предыдущего клиента, если он был авторизован
            if await client.is_user_authorized():
                await client.log_out()

            # Генерация QR-кода
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(await client.export_session_string())
            qr.make(fit=True)

            # Сохранение QR-кода в файл
            qr_filename = "telegram_qr_code.png"
            qr.make_image(fill='black', back_color='white').save(qr_filename)

            # Отправка QR-кода пользователю
            with open(qr_filename, 'rb') as qr_file:
                await message.reply_photo(qr_file, caption="Отсканируйте этот QR-код в приложении Telegram для входа")
            
            # Сохраняем состояние пользователя
            
            
            qr_login = await client.qr_login()
  

        except Exception as e:
            # Обрабатываем ошибку
            await message.reply(f"Произошла ошибка: {e}")

      
            # Разлогиниваемся и отключаемся от клиента
            if 'awaiting_password' not in user_state.get(user_id, {}):
                await client.log_out()
                await client.disconnect()

    else:
        await unauthorized(message)
