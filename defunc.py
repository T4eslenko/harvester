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
from PIL import Image, ImageDraw, ImageFont


async def get_user_info(client, phone):
    """Функция для получения информации о пользователе и его ID."""
    me = await client.get_me()
    userid = me.id
    firstname = me.first_name
    username = f"@{me.username}" if me.username is not None else ""
    lastname = me.last_name if me.last_name is not None else ""
    userinfo = f"(Номер телефона: +{phone}, ID: {userid}, ({firstname} {lastname}) {username})"
    photos_user_html = ''
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



async def get_type_of_chats(client):
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
    
    for chat in chats:   
        # Получаем данные о ботах
        if isinstance(chat.entity, User) and chat.entity.bot: 
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

        # Работаем с групповыми чатами
        if isinstance(chat.entity, Channel) or isinstance(chat.entity, Chat):  
            # Определяем открытый канал
            if isinstance(chat.entity, Channel) and hasattr(chat.entity, 'broadcast') and chat.entity.participants_count is not None:
                if chat.entity.broadcast and chat.entity.username:
                        openchannels.append(chat.entity)
                        all_chats_ids.append(chat.entity.id)
                        if chat.entity.admin_rights or chat.entity.creator:
                            admin_id.append(chat.entity.id)

            # Определяем закрытый канал
            if isinstance(chat.entity, Channel) and hasattr(chat.entity, 'broadcast'):
                if chat.entity.broadcast and chat.entity.username is None and chat.entity.title != 'Unsupported Chat':
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

            # Определяем удаленные группы   
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
   
    if isinstance(chat.entity, Channel) or isinstance(chat.entity, Chat): 
          for current_deleted_chat in deactivated_chats:
                 ID_migrated_values = current_deleted_chat['ID_migrated']
                 if ID_migrated_values not in all_chats_ids:
                      delgroups.append(current_deleted_chat)


    return delgroups, chat_message_counts, openchannels, closechannels, openchats, closechats, admin_id, user_bots, user_bots_html



async def get_blocked_bot(client):
    blocked_bot_info = []
    blocked_bot_info_html = []
    count_blocked_bot = 0
    earliest_date = None
    latest_date = None
    image_data_url = " "
    
    delgroups, chat_message_counts, openchannels, closechannels, openchats, closechats, admin_id, user_bots, user_bots_html = await get_type_of_chats(client)
    result_blocked = await client(GetBlockedRequest(offset=0, limit=200))
    for peer in result_blocked.blocked:
        if peer.peer_id.__class__.__name__ == 'PeerUser':
            user = await client.get_entity(peer.peer_id.user_id)
            if user.bot:
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

    return count_blocked_bot, earliest_date, latest_date, blocked_bot_info, blocked_bot_info_html, user_bots, user_bots_html


async def make_list_of_channels(delgroups, chat_message_counts, openchannels, closechannels, openchats, closechats, client):
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
        messages_count = f" / [{chat_message_counts.get(openchannel.id, 0)}]" if chat_message_counts else ""
        all_info.append(f"{count_row} - {openchannel.title} \033[93m[{openchannel.participants_count}]{messages_count}\033[0m\033[91m {owner} {admin}\033[0m ID:{openchannel.id} \033[94m@{openchannel.username}\033[0m")
        public_channels_html.append(
        f"{openchannel_count}. <img src='{image_data_url}' alt=' ' style='width:50px;height:50px;vertical-align:middle;margin-right:10px;'>" 
        f"<span style='color:#556B2F;'>{openchannel.title}</span> <span style='color:#8B4513;'>[{openchannel.participants_count}]</span> "
        f"<span style='color:#FF0000;'>{owner} {admin}</span> ID:{openchannel.id} "
        f'<a href="https://t.me/{openchannel.username}" style="color:#0000FF; text-decoration: none;">@{openchannel.username}</a>'
        )
        openchannel_count += 1
        groups.append(openchannel)
        i +=1
        if owner != "" or admin != "":
            owner_openchannel += 1

    closechannels_name = 'Закрытые КАНАЛЫ:' if closechannels else ''
    all_info.append(f"\033[95m{closechannels_name}\033[0m")  
    closechannel_count = 1
    private_channels_html = []
    image_data_url = ''
    for closechannel in closechannels:
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
        count_row = closechannel_count
        owner = " (Владелец)" if closechannel.creator else ""
        admin = " (Администратор)" if closechannel.admin_rights is not None else ""
        messages_count = f" / [{chat_message_counts.get(closechannel.id, 0)}]" if chat_message_counts else ""
        all_info.append(f"{count_row} - {closechannel.title} \033[93m[{closechannel.participants_count}]{messages_count}\033[0m \033[91m{owner} {admin}\033[0m ID:{closechannel.id}")
        private_channels_html.append(
            f'{closechannel_count}. <img src="{image_data_url}" alt=" " style="width:50px;height:50px;vertical-align:middle;margin-right:10px;">'
            f"<span style='color:#556B2F;'>{closechannel.title}</span> <span style='color:#8B4513;'>[{closechannel.participants_count}]</span> <span style='color:#FF0000;'>{owner} {admin}</span> ID:{closechannel.id}"
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
        count_row = opengroup_count
        owner = " (Владелец)" if openchat.creator else ""
        admin = " (Администратор)" if openchat.admin_rights is not None else ""
        messages_count = f" / [{chat_message_counts.get(openchat.id, 0)}]" if chat_message_counts else ""
        all_info.append(f"{count_row} - {openchat.title} \033[93m[{openchat.participants_count}]{messages_count}\033[0m\033[91m {owner} {admin}\033[0m ID:{openchat.id} \033[94m@{openchat.username}\033[0m")
        public_groups_html.append(
            f'{opengroup_count}. <img src="{image_data_url}" alt=" " style="width:50px;height:50px;vertical-align:middle;margin-right:10px;">'
            f"<span style='color:#556B2F;'>{openchat.title}</span> <span style='color:#8B4513;'>[{openchat.participants_count}]</span> "
            f"<span style='color:#FF0000;'>{owner} {admin}</span> ID:{openchat.id} "
            f'<a href="https://t.me/{openchat.username}" style="color:#0000FF; text-decoration: none;">@{openchat.username}</a>'
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
        count_row = closegroup_count
        owner = " (Владелец)" if closechat.creator else ""
        admin = " (Администратор)" if closechat.admin_rights is not None else ""
        messages_count = f" / [{chat_message_counts.get(closechat.id, 0)}]" if chat_message_counts else ""
        all_info.append(f"{count_row} - {closechat.title} \033[93m[{closechat.participants_count}]{messages_count}\033[0m \033[91m{owner} {admin}\033[0m ID:{closechat.id}")
        #private_groups_html.append(f"{closegroup_count} - <span style='color:#556B2F;'>{closechat.title}</span> <span style='color:#8B4513;'>[{closechat.participants_count}]</span> <span style='color:#FF0000;'>{owner} {admin}</span> ID:{closechat.id}")
        private_groups_html.append(
            f'{closegroup_count}. <img src="{image_data_url}" alt=" " style="width:50px;height:50px;vertical-align:middle;margin-right:10px;">'
            f"<span style='color:#556B2F;'>{closechat.title}</span> <span style='color:#8B4513;'>[{closechat.participants_count}]</span> <span style='color:#FF0000;'>{owner} {admin}</span> ID:{closechat.id}"
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
        try:
            count_row = closegroupdel_count
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
        except Exception:
            pass 
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



#  Формируем отчет HTML
async def generate_html_report(phone, userid, userinfo, firstname, lastname, username, total_contacts, total_contacts_with_phone, total_mutual_contacts, openchannel_count, closechannel_count, opengroup_count, closegroup_count, closegroupdel_count, owner_openchannel, owner_closechannel, owner_opengroup, owner_closegroup, public_channels_html, private_channels_html, public_groups_html, private_groups_html, deleted_groups_html, blocked_bot_info_html, user_bots_html, user_chat_id, photos_user_html):
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
        photos_user_html=photos_user_html
    )

    # Сохраняем результат в HTML файл
    report_filename = f"{phone}_report.html"
    with open(report_filename, 'w', encoding='utf-8') as file:
        file.write(html_content)    
