from telethon.sync import  TelegramClient, events
from telethon.types import Updates
from telethon.tl.types import PeerUser
from telethon.tl.functions.channels import JoinChannelRequest, GetFullChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from config import API_HASH, API_ID, PHONE_NUMBER
# from ..bot.utils.db import get_updated_channel_list
from loader import bot
from utils.db import add_new_channel, check_channel_exists, insert_new_post
from handlers.post_router import post_text_generator
from keyboards.inline_keyboard import group_markup
from telethon.errors.rpcerrorlist import InviteRequestSentError
import asyncio

client = TelegramClient('parser_session', API_ID, API_HASH)

def add_prefix_to_channels(channel_ids):
    return [f"-100{channel_id}" for channel_id in channel_ids]

  # Обновляем список каналов
async def telethon_task():
    # Создаем клиента Telethon
    client = TelegramClient('your_session_name', API_ID, API_HASH)
    await client.start(phone=PHONE_NUMBER)

    # Слушаем все новые сообщения, независимо от чатов
    @client.on(events.NewMessage())
    async def handler(event: events.NewMessage.Event):

        # Проверка на наличие текста сообщения
        if event.message.text:
            chat = await event.get_chat()  # Получаем объект чата
            channel_name = chat.title if hasattr(chat, 'title') else 'Личный чат'  # Название канала или чата

            # Определение ID канала/группы
            if hasattr(event.message.peer_id, 'channel_id'):
                channel_id = event.message.peer_id.channel_id
            elif hasattr(event.message.peer_id, 'chat_id'):
                channel_id = event.message.peer_id.chat_id
            elif hasattr(event.message.peer_id, 'user_id'):
                channel_id = event.message.peer_id.user_id
            else:
                channel_id = None  # Если ID не определен

            # Если ID канала найден, проверяем его в базе данных
            if channel_id:
                channel_exists = await check_channel_exists(channel_id)
                if not channel_exists:
                    await add_new_channel(channel_name, channel_id)

            post_text = event.message.message  # Текст поста
            message_id = event.message.id  # ID сообщения
            chat_entity = '-4591729465'  # ID чата для отправки сообщений

            # Вставляем новый пост в базу данных
            post = await insert_new_post(post_text, source=channel_id, message_id=message_id)
            print(f"Пост сохранен в БД: {post}")

            # Генерируем текст для отправки
            parse_moded_text = post_text_generator(post)

            # Отправляем сообщение через бота
            await bot.send_message(
                chat_id=chat_entity,
                text=parse_moded_text,
                parse_mode='MarkdownV2',
                reply_markup=group_markup(post['id'], channel_id, message_id)  # Генерируем клавиатуру для сообщения
            )

    # Поддерживаем Telethon активным
    await client.run_until_disconnected()



async def join_channel(channel: str):
  await client.start(phone=PHONE_NUMBER)
  try:
    if '+' in channel:
      hash = channel.split('+')[1]
      print(hash)
      # req = await client(GetFullChannelRequest(hash))
      # print(req)
      data = await client(ImportChatInviteRequest(hash))
      
      # print(data)
      return 'success', data
    elif '@' in channel:
      name = channel.removeprefix('@')
      data = await client(JoinChannelRequest(name))
      return 'success', data
    else:
      name  = channel.split('/')[3]
      data = await client(JoinChannelRequest(name))
      # print(data)
      return 'success', data
  except InviteRequestSentError as e:
    print(e)
    return 'request', None
  except Exception as e:
    print(e)
    return None, e

async def leave_channel(channel):
  await client.start(phone=PHONE_NUMBER)
  try:
    print(channel)
    await client.delete_dialog(channel)
    return 'success'
  except Exception as e:
    print('exc: ', e)
    return 'exception'

async def test():
  url = 'https://t.me/+ZF6ejixpdeZmYzBi'
  # https://t.me/pars11111111
  print(await join_channel(url))

