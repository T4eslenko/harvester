import asyncio  
import os
import time
import openpyxl
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.contacts import GetContactsRequest, GetBlockedRequest
from telethon.tl.functions.messages import GetDialogsRequest, ImportChatInviteRequest
from telethon.tl.types import InputChannel, InputPhoneContact, User, Chat, Channel, Message, MessageFwdHeader, MessageMediaDocument, PeerChannel, DocumentAttributeFilename
from telethon.sync import TelegramClient, types
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from datetime import datetime
from telethon.errors.rpcerrorlist import PeerFloodError, UserPrivacyRestrictedError
from datetime import datetime
from typing import Optional
import re
from jinja2 import Template
import base64
from io import BytesIO
from PIL import Image #, ImageDraw, ImageFont
from telethon.sync import TelegramClient
from telethon import functions, types
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.messages import SearchRequest as MessageSearchRequest
from telethon.tl.types import InputMessagesFilterEmpty

# Получение информации о пользователе
async def get_bot_from_search(client, phone_number, selection, list_botblocked, list_botexisted):
    bot_from_search = []
    bot_from_search_html = []
    try:
        keyword = 'bot'
        entities = await client(SearchRequest(
            q=keyword,
            limit=1000  # Максимальное количество сущностей, которые нужно получить
        ))
        for user in entities.users:
            if user.id not in list_botblocked and user.id not in list_botexisted:

                if user.photo:
                    user_info = await client.get_entity(user.id)
                    #if user_info.photo:
                    photo_path = await client.download_profile_photo(user, file=BytesIO())
                    if photo_path:
                            encoded_image = base64.b64encode(photo_path.getvalue()).decode('utf-8')
                            image_data_url = f"data:image/jpeg;base64,{encoded_image}"
                    else:
                            with open("no_image.png", "rb") as img_file:
                                img_data = img_file.read()
                                img_str = base64.b64encode(img_data).decode('utf-8')
                                image_data_url = f"data:image/png;base64,{img_str}"
                    bot_from_search_html.append(
                            f'<img src="{image_data_url}" alt=" " style="width:50px;height:50px;vertical-align:middle;margin-right:10px;">'
                            f'<a href="https://t.me/{user.username}" style="color:#0000FF; text-decoration: none;vertical-align:middle;">@{user.username}</a> '
                            f'<span style="color:#556B2F;vertical-align:middle;">{user.first_name}</span>'
                    )
                        
                    bot_from_search.append(f"{user.first_name}, @{user.username}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return bot_from_search, bot_from_search_html
    
async def get_user_info(client, phone, selection):
    """Функция для получения информации о пользователе и его ID."""
    me = await client.get_me()
    userid = me.id
    firstname = me.first_name
    username = f"@{me.username}" if me.username is not None else ""
    lastname = me.last_name if me.last_name is not None else ""
    userinfo = f"(Номер телефона: +{phone}, ID: {userid}, ({firstname} {lastname}) {username})"
    photos_user_html = ''
    if selection == '0':
        try:
            user_photo = await client.get_profile_photos(userid)
            if user_photo:
                for i in range(len(user_photo)):
                    file_name = f"{phone}_{i}"
                    await client.download_media(user_photo[i], file=file_name)
                    jpg_path = f"{file_name}.jpg"
                    mp4_path = f"{file_name}.mp4"
                    if os.path.exists(jpg_path):
                        with open(jpg_path, "rb") as img_file:
                            img_data = open(jpg_path, "rb").read()
                            img_str = base64.b64encode(img_data).decode('utf-8')
                            photos_user_html += f'<img src="data:image/jpeg;base64,{img_str}" alt="User photo {i+1}" style="width:100px;height:100px;vertical-align:middle;margin-right:10px;">'
                        os.remove(jpg_path)
                    elif os.path.exists(mp4_path):
                        with open(mp4_path, "rb") as video_file:
                            video_data = video_file.read()
                            video_str = base64.b64encode(video_data).decode('utf-8')
                            photos_user_html += f'<video width="100" height="100" controls><source src="data:video/mp4;base64,{video_str}" type="video/mp4">Your browser does not support the video tag.</video>'
                        os.remove(mp4_path)
            else:
                with open("no_image.png", "rb") as img_file:
                    img_data = img_file.read()
                    img_str = base64.b64encode(img_data).decode('utf-8')
                    image_data_url = f"data:image/png;base64,{img_str}"
        
                    photos_user_html +=f'<img src="data:image/png;base64,{img_str}" alt=" " style="width:100px;height:100px;vertical-align:middle;margin-right:10px;">'
        except Exception as e:
            print(f"An error occurred: {e}")
    return userid, userinfo, firstname, lastname, username, photos_user_html



async def get_type_of_chats(client, selection):
    """Функция для подсчета количества сообщений в чатах и определения типов чатов."""
    chat_message_counts = {}
    openchannels = []
    closechannels = []
    openchats = []
    closechats = []
    count_messages = 0
    deactivated_chats = []
    all_chats_ids = []
    delgroups = []
    chats = await client.get_dialogs()
    admin_id = [] 
    user_bots = []
    user_bots_html = []
    image_data_url = ''
    list_botexisted =[]
    
    for chat in chats:   
        # Получаем данные о ботах
        if isinstance(chat.entity, User) and chat.entity.bot: 
            if selection == '0':
                try:
                    photo_bytes = await client.download_profile_photo(chat.entity, file=BytesIO())
                    if photo_bytes:
                        encoded_image = base64.b64encode(photo_bytes.getvalue()).decode('utf-8')
                        image_data_url = f"data:image/jpeg;base64,{encoded_image}"
                    else:
                        with open("no_image.png", "rb") as img_file:
                            img_data = img_file.read()
                            img_str = base64.b64encode(img_data).decode('utf-8')
                            image_data_url = f"data:image/png;base64,{img_str}"
                except Exception:
                    pass
            user_bots_html.append(
                f'<img src="{image_data_url}" alt=" " style="width:50px;height:50px;vertical-align:middle;margin-right:10px;">'
                f'<a href="https://t.me/{chat.entity.username}" style="color:#0000FF; text-decoration: none;vertical-align:middle;">@{chat.entity.username}</a> '
                f'<span style="color:#556B2F;vertical-align:middle;">{chat.entity.first_name}</span>'
            )
            
            user_bots.append(f"{chat.entity.first_name}, @{chat.entity.username}")
            list_botexisted.append(chat.entity.id)

        # Работаем с групповыми чатами
        if isinstance(chat.entity, Channel) or isinstance(chat.entity, Chat):  
            # Выгружаем количество сообщений при выборе опции выгрузить сообщение
            if selection == '7': 
                messages = await client.get_messages(chat.entity, limit=0)
                count_messages = messages.total
                chat_message_counts[chat.entity.id] = count_messages

            # Определяем открытый канал
            if isinstance(chat.entity, Channel) and hasattr(chat.entity, 'broadcast') and chat.entity.participants_count is not None:
                if chat.entity.broadcast and chat.entity.username:
                    if selection == '6':
                        if chat.entity.admin_rights or chat.entity.creator:
                            openchannels.append(chat.entity)
                            all_chats_ids.append(chat.entity.id)
                            admin_id.append(chat.entity.id)
                    
                    if selection != '6':
                        openchannels.append(chat.entity)
                        all_chats_ids.append(chat.entity.id)
                        if chat.entity.admin_rights or chat.entity.creator:
                            admin_id.append(chat.entity.id)

            # Определяем закрытый канал
            if isinstance(chat.entity, Channel) and hasattr(chat.entity, 'broadcast'):
                if chat.entity.broadcast and chat.entity.username is None and chat.entity.title != 'Unsupported Chat':
                    if selection == '6':
                        if chat.entity.admin_rights or chat.entity.creator:
                            closechannels.append(chat.entity)
                            all_chats_ids.append(chat.entity.id)
                            admin_id.append(chat.entity.id)
                    
                    if selection != '6':
                        closechannels.append(chat.entity)
                        all_chats_ids.append(chat.entity.id)
                        if chat.entity.admin_rights or chat.entity.creator:
                            admin_id.append(chat.entity.id)

            # Определяем открытый чат
            if isinstance(chat.entity, Channel) and hasattr(chat.entity, 'broadcast'):
                if not chat.entity.broadcast and chat.entity.username:
                    openchats.append(chat.entity)
                    all_chats_ids.append(chat.entity.id)
                    admin_id.append(chat.entity.id)

            # Определяем закрытый чат
            if isinstance(chat.entity, Channel) and hasattr(chat.entity, 'broadcast'):
               if chat.entity.broadcast == False and chat.entity.username == None:
                  closechats.append(chat.entity)
                  all_chats_ids.append(chat.entity.id)
                  admin_id.append(chat.entity.id)

            if isinstance(chat.entity, Chat) and chat.entity.migrated_to is None:
               closechats.append(chat.entity)
               all_chats_ids.append(chat.entity.id)
               admin_id.append(chat.entity.id)

                
            if selection == '5' or selection == '0': # Добавляем нулевые чаты только для общей информации
                if isinstance(chat.entity, Chat) and hasattr(chat.entity, 'participants_count') and chat.entity.participants_count == 0:
                   if chat.entity.migrated_to is not None and isinstance(chat.entity.migrated_to, InputChannel):
                      deactivated_chats_all = {
                         'ID_migrated': chat.entity.migrated_to.channel_id,
                         'ID': chat.entity.id,
                         'title': chat.entity.title,
                         'creator': chat.entity.creator,
                         'admin_rights': chat.entity.admin_rights,
                      }
                      deactivated_chats.append(deactivated_chats_all)
   
    if selection == '5' or selection == '0': # Добавляем нулевые чаты для общей информации
       if isinstance(chat.entity, Channel) or isinstance(chat.entity, Chat): # Проверяем, является ли чат групповым
          for current_deleted_chat in deactivated_chats:
                 ID_migrated_values = current_deleted_chat['ID_migrated']
                 if ID_migrated_values not in all_chats_ids:
                      delgroups.append(current_deleted_chat)


    return delgroups, chat_message_counts, openchannels, closechannels, openchats, closechats, admin_id, user_bots, user_bots_html, list_botexisted



async def get_blocked_bot(client, selection):
    blocked_bot_info = []
    blocked_bot_info_html = []
    count_blocked_bot = 0
    earliest_date = None
    latest_date = None
    image_data_url = " "
    list_botblocked =[]
    
    delgroups, chat_message_counts, openchannels, closechannels, openchats, closechats, admin_id, user_bots, user_bots_html, list_botexisted = await get_type_of_chats(client, selection)
    result_blocked = await client(GetBlockedRequest(offset=0, limit=200))
    for peer in result_blocked.blocked:
        if peer.peer_id.__class__.__name__ == 'PeerUser':
            user = await client.get_entity(peer.peer_id.user_id)
            if user.bot:
                if selection == '0':
                    try:
                        photo_path = await client.download_profile_photo(user, file=BytesIO())
                        if photo_path:
                            encoded_image = base64.b64encode(photo_path.getvalue()).decode('utf-8')
                            image_data_url = f"data:image/jpeg;base64,{encoded_image}"
                        else:
                            with open("no_image.png", "rb") as img_file:
                                img_data = img_file.read()
                                img_str = base64.b64encode(img_data).decode('utf-8')
                                image_data_url = f"data:image/png;base64,{img_str}"
                    except Exception:
                        pass    
                blocked_bot_info.append(f"\033[36m@{user.username}\033[0m \033[93m'{user.first_name}'\033[0m заблокирован: {peer.date.strftime('%d/%m/%Y')}")
                
                blocked_bot_info_html.append(
                    f'<img src="{image_data_url}" alt=" " style="width:50px;height:50px;vertical-align:middle;margin-right:10px;">'
                    f'<a href="https://t.me/{user.username}" style="color:#0000FF; text-decoration: none;vertical-align:middle;">@{user.username}</a> '
                    f'<span style="color:#556B2F;vertical-align:middle;">{user.first_name}</span> заблокирован: {peer.date.strftime("%d/%m/%Y")}'
                )

                list_botblocked.append(peer.peer_id.user_id)

    return count_blocked_bot, earliest_date, latest_date, blocked_bot_info, blocked_bot_info_html, user_bots, user_bots_html, list_botblocked

# Функция для получения списка прав администратора в канале
def get_admin_rights_channel_list(admin_rights):
    rights = ['<span style="color:maroon; font-weight:bold; font-style:italic;">Права, как администратора канала:</span>']
    possible_rights = {
        'Изменение профиля канала': admin_rights.change_info if admin_rights else False,
        'Публикация сообщений': admin_rights.post_messages if admin_rights else False,
        'Изменение публикаций': admin_rights.edit_messages if admin_rights else False,
        'Удаление публикаций': admin_rights.delete_messages if admin_rights else False,
        'Публикация историй': admin_rights.post_stories if admin_rights else False,
        'Изменение историй': admin_rights.edit_stories if admin_rights else False,
        'Удаление историй': admin_rights.delete_stories if admin_rights else False,
        'Пригласительные ссылки': admin_rights.invite_users if admin_rights else False,
        'Управление трансляциями': admin_rights.manage_call if admin_rights else False,
        '<b>Назначение администраторов</b>': admin_rights.add_admins if admin_rights else False,
    }
    has_any_rights = any(possible_rights.values())
    for right, has_right in possible_rights.items():
        status = '<b><span style="color:red; font-weight:bold;">да</span></b>' if has_right else '<b>нет</b>'
        rights.append(f"{right} - {status}")
    return rights if has_any_rights else []

def get_admin_rights_chat_list(admin_rights):
    rights = ['<span style="color:maroon; font-weight:bold; font-style:italic;">Права, как администратора группы:</span>']
    possible_rights = {
        'Удаление сообщений': admin_rights.delete_messages if admin_rights else False,
        'Блокировка пользователей': admin_rights.ban_users if admin_rights else False,
        'Пригласительные ссылки': admin_rights.invite_users if admin_rights else False,
        'Закрепление сообщений': admin_rights.pin_messages if admin_rights else False,
        'Публикация историй': admin_rights.post_stories if admin_rights else False,
        'Изменение историй': admin_rights.edit_stories if admin_rights else False,
        'Удаление историй': admin_rights.delete_stories if admin_rights else False,
        'Управление трансляциями': admin_rights.manage_call if admin_rights else False,
        '<b>Назначение администраторов</b>': admin_rights.add_admins if admin_rights else False,
        'Анонимность': admin_rights.anonymous if admin_rights else False
    }
    has_any_rights = any(possible_rights.values())
    for right, has_right in possible_rights.items():
        status = '<b><span style="color:red; font-weight:bold;">да</span></b>' if has_right else '<b>нет</b>'
        rights.append(f"{right} - {status}")
    return rights if has_any_rights else []

async def make_list_of_channels(delgroups, chat_message_counts, openchannels, closechannels, openchats, closechats, selection, client):
    """Функция для формирования списков групп и каналов"""
    owner_openchannel = 0
    owner_opengroup = 0
    owner_closegroup = 0
    owner_closechannel = 0
    all_info = []
    groups = []
    i=0


    openchannels_name = 'Открытые КАНАЛЫ:' if openchannels else ''
    all_info.append(f"\033[95m{openchannels_name}\033[0m")  
    openchannel_count = 1  
    public_channels_html = []
    image_data_url = ''
    for openchannel in openchannels:
        try:
            photo_bytes = await client.download_profile_photo(openchannel, file=BytesIO())
            if photo_bytes:
                encoded_image = base64.b64encode(photo_bytes.getvalue()).decode('utf-8')
                image_data_url = f"data:image/jpeg;base64,{encoded_image}"
            else:
                with open("no_image.png", "rb") as img_file:
                    img_data = img_file.read()
                    img_str = base64.b64encode(img_data).decode('utf-8')
                    image_data_url = f"data:image/png;base64,{img_str}"
        except Exception:
            pass 
        count_row = openchannel_count
        owner = " (Владелец)" if openchannel.creator else ""
        admin = " (Администратор)" if openchannel.admin_rights is not None else ""
        
        # Получение списка прав администратора
        admin_rights_list = get_admin_rights_channel_list(openchannel.admin_rights)
        admin_rights_html = ""
        if admin_rights_list:
            admin_rights_html = "<ul style='font-size:14px; font-style:italic;'>" + "".join([f"<li style='margin-left:50px;'>{right}</li>" for right in admin_rights_list]) + "</ul>"
        
        messages_count = f" / [{chat_message_counts.get(openchannel.id, 0)}]" if chat_message_counts else ""
        all_info.append(f"{count_row} - {openchannel.title} \033[93m[{openchannel.participants_count}]{messages_count}\033[0m\033[91m {owner} {admin}\033[0m ID:{openchannel.id} \033[94m@{openchannel.username}\033[0m")
        
        public_channels_html.append(
            f"{openchannel_count}. <img src='{image_data_url}' alt=' ' style='width:50px;height:50px;vertical-align:middle;margin-right:10px;'>"
            f"<span style='color:#556B2F;'>{openchannel.title}</span> <span style='color:#8B4513;'>[{openchannel.participants_count}]</span> "
            f"<span style='color:#FF0000;'>{owner} {admin}</span> ID:{openchannel.id} "
            f'<a href="https://t.me/{openchannel.username}" style="color:#0000FF; text-decoration: none;">@{openchannel.username}</a>'
            f"{admin_rights_html}"
        )
        
        openchannel_count += 1
        groups.append(openchannel)
        i += 1
        if owner != "" or admin != "":
            owner_openchannel += 1

    

    closechannels_name = 'Закрытые КАНАЛЫ:' if closechannels else ''
    all_info.append(f"\033[95m{closechannels_name}\033[0m")  
    closechannel_count = 1
    private_channels_html = []
    image_data_url = ''
    for closechannel in closechannels:
        if selection == '0':
            try:
                photo_bytes = await client.download_profile_photo(closechannel, file=BytesIO())
                if photo_bytes:
                        encoded_image = base64.b64encode(photo_bytes.getvalue()).decode('utf-8')
                        image_data_url = f"data:image/jpeg;base64,{encoded_image}"
                else:
                        with open("no_image.png", "rb") as img_file:
                            img_data = img_file.read()
                            img_str = base64.b64encode(img_data).decode('utf-8')
                            image_data_url = f"data:image/png;base64,{img_str}"
            except Exception:
                pass 
        count_row = closechannel_count if selection == '5' or selection == '0' else i
        owner = " (Владелец)" if closechannel.creator else ""
        admin = " (Администратор)" if closechannel.admin_rights is not None else ""

        # Получение списка прав администратора
        admin_rights_list = get_admin_rights_channel_list(closechannel.admin_rights)
        admin_rights_html = ""
        if admin_rights_list:
            admin_rights_html = "<ul style='font-size:14px; font-style:italic;'>" + "".join([f"<li style='margin-left:50px;'>{right}</li>" for right in admin_rights_list]) + "</ul>"
        
        messages_count = f" / [{chat_message_counts.get(closechannel.id, 0)}]" if chat_message_counts else ""
        all_info.append(f"{count_row} - {closechannel.title} \033[93m[{closechannel.participants_count}]{messages_count}\033[0m \033[91m{owner} {admin}\033[0m ID:{closechannel.id}")
        private_channels_html.append(
            f'{closechannel_count}. <img src="{image_data_url}" alt=" " style="width:50px;height:50px;vertical-align:middle;margin-right:10px;">'
            f"<span style='color:#556B2F;'>{closechannel.title}</span> <span style='color:#8B4513;'>[{closechannel.participants_count}]</span> <span style='color:#FF0000;'>{owner} {admin}</span> ID:{closechannel.id}"
            f"{admin_rights_html}"
        )
        closechannel_count += 1
        groups.append(closechannel)
        i +=1
        if owner != "" or admin != "":
            owner_closechannel += 1

    openchats_name = 'Открытые ГРУППЫ:' if openchats else ''
    all_info.append(f"\033[95m{openchats_name}\033[0m")
    opengroup_count = 1
    public_groups_html = []
    image_data_url = ''
    for openchat in openchats:
        if selection == '0':
            try:
                photo_bytes = await client.download_profile_photo(openchat, file=BytesIO())
                if photo_bytes:
                        encoded_image = base64.b64encode(photo_bytes.getvalue()).decode('utf-8')
                        image_data_url = f"data:image/jpeg;base64,{encoded_image}"
                else:
                        with open("no_image.png", "rb") as img_file:
                            img_data = img_file.read()
                            img_str = base64.b64encode(img_data).decode('utf-8')
                            image_data_url = f"data:image/png;base64,{img_str}"
            except Exception:
                pass 
        count_row = opengroup_count if selection == '5' or selection == '0' else i
        owner = " (Владелец)" if openchat.creator else ""
        admin = " (Администратор)" if openchat.admin_rights is not None else ""
        admin_rights_list = get_admin_rights_chat_list(openchat.admin_rights)
        admin_rights_html = ""
        if admin_rights_list:
            admin_rights_html = "<ul style='font-size:14px; font-style:italic;'>" + "".join([f"<li style='margin-left:50px;'>{right}</li>" for right in admin_rights_list]) + "</ul>"
        
        messages_count = f" / [{chat_message_counts.get(openchat.id, 0)}]" if chat_message_counts else ""
        all_info.append(f"{count_row} - {openchat.title} \033[93m[{openchat.participants_count}]{messages_count}\033[0m\033[91m {owner} {admin}\033[0m ID:{openchat.id} \033[94m@{openchat.username}\033[0m")
        public_groups_html.append(
            f'{opengroup_count}. <img src="{image_data_url}" alt=" " style="width:50px;height:50px;vertical-align:middle;margin-right:10px;">'
            f"<span style='color:#556B2F;'>{openchat.title}</span> <span style='color:#8B4513;'>[{openchat.participants_count}]</span> "
            f"<span style='color:#FF0000;'>{owner} {admin}</span> ID:{openchat.id} "
            f'<a href="https://t.me/{openchat.username}" style="color:#0000FF; text-decoration: none;">@{openchat.username}</a>'
            f"{admin_rights_html}"
        )
        opengroup_count += 1
        groups.append(openchat)
        i +=1
        if owner != "" or admin != "":
            owner_opengroup += 1

    closechats_name = 'Закрытые ГРУППЫ:' if closechats else ''
    all_info.append(f"\033[95m{closechats_name}\033[0m")
    closegroup_count = 1
    private_groups_html = []
    image_data_url = ''
    for closechat in closechats:
        if selection == '0':
            try:
                photo_bytes = await client.download_profile_photo(closechat, file=BytesIO())
                if photo_bytes:
                        encoded_image = base64.b64encode(photo_bytes.getvalue()).decode('utf-8')
                        image_data_url = f"data:image/jpeg;base64,{encoded_image}"
                else:
                        with open("no_image.png", "rb") as img_file:
                            img_data = img_file.read()
                            img_str = base64.b64encode(img_data).decode('utf-8')
                            image_data_url = f"data:image/png;base64,{img_str}"
            except Exception:
                pass 
        count_row = closegroup_count if selection == '5' or selection == '0' else i
        owner = " (Владелец)" if closechat.creator else ""
        admin = " (Администратор)" if closechat.admin_rights is not None else ""
        admin_rights_list = get_admin_rights_chat_list(closechat.admin_rights)
        admin_rights_html = ""
        if admin_rights_list:
            admin_rights_html = "<ul style='font-size:14px; font-style:italic;'>" + "".join([f"<li style='margin-left:50px;'>{right}</li>" for right in admin_rights_list]) + "</ul>"
        
        messages_count = f" / [{chat_message_counts.get(closechat.id, 0)}]" if chat_message_counts else ""
        all_info.append(f"{count_row} - {closechat.title} \033[93m[{closechat.participants_count}]{messages_count}\033[0m \033[91m{owner} {admin}\033[0m ID:{closechat.id}")
        private_groups_html.append(
            f'{closegroup_count}. <img src="{image_data_url}" alt=" " style="width:50px;height:50px;vertical-align:middle;margin-right:10px;">'
            f"<span style='color:#556B2F;'>{closechat.title}</span> <span style='color:#8B4513;'>[{closechat.participants_count}]</span> <span style='color:#FF0000;'>{owner} {admin}</span> ID:{closechat.id}"
            f"{admin_rights_html}"
        )
        closegroup_count += 1
        groups.append(closechat)
        i +=1
        if owner != "" or admin != "":
            owner_closegroup += 1

    
    delgroups_name = 'Удаленные ГРУППЫ:' if delgroups else ''
    all_info.append(f"\033[95m{delgroups_name}\033[0m")
    closegroupdel_count = 1
    deleted_groups_html = []
    for delgroup in delgroups:
        count_row = closegroupdel_count if selection == '5' or selection == '0' else i
        owner_value = delgroup['creator']
        admin_value = delgroup['admin_rights']
        id_value = delgroup['ID']
        title_value = delgroup['title']
        owner = " (Владелец)" if owner_value else ""
        admin = " (Администратор)" if admin_value is not None else ""
        all_info.append(f"{count_row} - {title_value} \033[91m{owner} {admin}\033[0m ID:{id_value}")
        deleted_groups_html.append(f"{closegroupdel_count} - <span style='color:#556B2F;'>{title_value}</span> <span style='color:#FF0000;'>{owner} {admin}</span> ID:{id_value}")
        closegroupdel_count += 1
        i +=1
        if owner != "" or admin != "":
            owner_closegroup += 1

    return groups, i, all_info, openchannel_count, closechannel_count, opengroup_count, closegroup_count, closegroupdel_count, owner_openchannel, owner_closechannel, owner_opengroup, owner_closegroup, public_channels_html, private_channels_html, public_groups_html, private_groups_html, deleted_groups_html

async def get_and_save_contacts(client, phone_user, userid_user, userinfo, firstname_user, lastname_user, username_user):
    result = await client(GetContactsRequest(0))
    contacts = result.users
    total_contacts = len(contacts)
    total_contacts_with_phone = sum(bool(getattr(contact, 'phone', None)) for contact in contacts)
    total_mutual_contacts = sum(bool(getattr(contact, 'mutual_contact', None)) for contact in contacts)

    
    # Сохраняем информацию о контактах
    new_phone_user = phone_user[1:]  # "1234567890"
    contacts_file_name = f'{phone_user}_contacts.xlsx'
    print(f"Контакты сохранены в файл {phone_user}_contacts.xlsx")

    wb = openpyxl.Workbook()
    sheet = wb.active
    headers = ['ID контакта', 'First name контакта', 'Last name контакта', 'Username контакта', 'Телефон контакта', 'Взаимный контакт', 'Дата внесения в базу', 'First name объекта', 'Last name объекта', 'Username объекта', 'Телефон объекта', 'ID_объекта']
    for col, header in enumerate(headers, start=1):
        sheet.cell(row=1, column=col, value=header)
        
    row_num = 2
    for contact in contacts:
        if hasattr(contact, 'id'):
            sheet.cell(row=row_num, column=1, value=contact.id)
        if hasattr(contact, 'first_name'):
            sheet.cell(row=row_num, column=2, value=contact.first_name)
        if hasattr(contact, 'last_name'):
            sheet.cell(row=row_num, column=3, value=contact.last_name)
        if hasattr(contact, 'username') and contact.username is not None:
            username_with_at = f"@{contact.username}"
            sheet.cell(row=row_num, column=4, value=username_with_at)
        if hasattr(contact, 'phone'):
            sheet.cell(row=row_num, column=5, value=contact.phone)
        if hasattr(contact, 'mutual_contact') and contact.mutual_contact:
            sheet.cell(row=row_num, column=6, value='взаимный')
        sheet.cell(row=row_num, column=7, value=datetime.now().strftime('%d.%m.%Y %H:%M:%S'))
        sheet.cell(row=row_num, column=8, value=firstname_user)
        sheet.cell(row=row_num, column=9, value=lastname_user)
        sheet.cell(row=row_num, column=10, value=username_user)
        sheet.cell(row=row_num, column=11, value=new_phone_user)
        sheet.cell(row=row_num, column=12, value=userid_user)
     
        row_num += 1

    wb.save(contacts_file_name)
    return total_contacts, total_contacts_with_phone, total_mutual_contacts

async def save_about_channels(phone, userid, firstname, lastname, username, openchannel_count, opengroup_count, closechannel_count, closegroup_count, owner_openchannel, owner_closechannel, owner_opengroup, owner_closegroup, openchannels, closechannels, openchats, closechats, delgroups, closegroupdel_count):
    
    async def write_data(sheet, data):
        sheet.append(["Название", "Количество участников", "Владелец", "Администратор", "ID", "Ссылка"])
        for item in data:
          owner = " (Владелец)" if item.creator else ""
          admin = " (Администратор)" if item.admin_rights is not None else ""
          usernameadd = f"@{item.username}" if hasattr(item, 'username') and item.username is not None else ""
          sheet.append([item.title, item.participants_count, owner, admin, item.id, usernameadd])
    
    async def write_data_del(sheet, data):
        sheet.append(["Название", "Владелец", "Администратор", "ID"])
        for item in data:
          owner_value = item['creator']
          admin_value = item['admin_rights']
          id_value = item['ID']
          title_value = item['title']
          owner = " (Владелец)" if owner_value else ""
          admin = " (Администратор)" if admin_value is not None else ""
          sheet.append([title_value, owner, admin, id_value])
            
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws_summury = wb.create_sheet("Сводная информация")
    ws_summury.append([f"Номер телефона: +{phone}, ID: {userid}, ({firstname}{lastname}) {username}"])
    if openchannel_count > 1:
        ws_summury.append([f"Открытые каналы: {openchannel_count-1}"])
        ws_open_channels = wb.create_sheet("Открытые каналы")
        await write_data(ws_open_channels, openchannels)
    if closechannel_count > 1:
        ws_summury.append([f"Закрытые каналы: {closechannel_count-1}"])
        ws_closed_channels = wb.create_sheet("Закрытые каналы")
        await write_data(ws_closed_channels, closechannels)
    if owner_openchannel > 1:
        ws_summury.append([f"Имеет права владельца или админа в открытых каналах: {owner_openchannel}"])
    if owner_closechannel > 1:
        ws_summury.append([f"Имеет права владельца или админа в закрытых каналах: {owner_closechannel}"])
    if opengroup_count > 1:
        ws_summury.append([f"Открытые группы: {opengroup_count-1}"])
        ws_open_groups = wb.create_sheet("Открытые группы")
        await write_data(ws_open_groups, openchats)
    if closegroup_count > 1:
        ws_summury.append([f"Закрытые группы: {closegroup_count-1}"])
        ws_closed_groups = wb.create_sheet("Закрытые группы")
        await write_data(ws_closed_groups, closechats)
    if closegroupdel_count > 1:
        ws_summury.append([f"Удаленные группы: {closegroupdel_count-1}"])
        ws_closed_groups_del = wb.create_sheet("Удаленные группы")
        await write_data_del(ws_closed_groups_del, delgroups)
    if owner_opengroup > 11:
        ws_summury.append([f"Имеет права владельца или админа в открытых группах: {owner_opengroup}"])
    if owner_closegroup > 1:
        ws_summury.append([f"Имеет права владельца или админа в закрытых группах: {owner_closegroup}"])
    
    wb.save(f"{phone}_about.xlsx")

#  Формируем отчет HTML
async def generate_html_report(phone, userid, userinfo, firstname, lastname, username, total_contacts, total_contacts_with_phone, total_mutual_contacts, openchannel_count, closechannel_count,
                               opengroup_count, closegroup_count, closegroupdel_count, owner_openchannel, owner_closechannel, owner_opengroup, owner_closegroup, public_channels_html,
                               private_channels_html, public_groups_html, private_groups_html, deleted_groups_html, blocked_bot_info_html, user_bots_html, user_chat_id,
                               photos_user_html, bot_from_search_html):
    
    # Открываем HTML шаблон
    with open('template.html', 'r', encoding='utf-8') as file:
        template = Template(file.read())

    # Заполняем шаблон данными
    html_content = template.render(
        phone=phone,
        userid=userid,
        firstname=firstname,
        lastname=lastname,
        username=username,
        total_contacts=total_contacts,
        total_contacts_with_phone=total_contacts_with_phone,
        total_mutual_contacts=total_mutual_contacts,
        openchannel_count=openchannel_count,
        closechannel_count=closechannel_count,
        opengroup_count=opengroup_count,
        closegroup_count=closegroup_count,
        closegroupdel_count=closegroupdel_count,
        owner_openchannel=owner_openchannel,
        owner_closechannel=owner_closechannel,
        owner_opengroup=owner_opengroup,
        owner_closegroup=owner_closegroup,
        blocked_bot_info_html=blocked_bot_info_html,
        user_bots_html=user_bots_html,
        public_channels_html=public_channels_html,
        private_channels_html=private_channels_html,
        public_groups_html=public_groups_html,
        private_groups_html=private_groups_html,
        deleted_groups_html=deleted_groups_html,
        user_chat_id=user_chat_id,
        photos_user_html=photos_user_html,
        bot_from_search_html=bot_from_search_html
    )

    # Сохраняем результат в HTML файл
    report_filename = f"{phone}_report.html"
    with open(report_filename, 'w', encoding='utf-8') as file:
        file.write(html_content)    
