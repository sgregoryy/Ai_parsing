from aiogram import Router, F
from aiogram import types
from aiogram.fsm.context import FSMContext
from utils.db import get_channels
from keyboards.inline_keyboard import *
from utils.states import *
from aiogram.enums import ChatMemberStatus
from utils.db import *
from user_bot import join_channel, leave_channel
from .post_router import ai_rewriting
from loader import bot
# from post_router import escape_markdown

i_router = Router(name='i_router')

def escape_markdown(text):
    # Экранирование специальных символов для MarkdownV2
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)
async def try_delete_call(call: types.CallbackQuery):
    try:
        await call.message.delete()
    except:
        pass


async def try_edit_call(callback, text, markup):
    try:
        msg = await callback.message.edit_text(text=text, parse_mode='HTML', reply_markup=markup)
    except:
        await try_delete_call(callback)
        msg = await callback.message.answer(text=text, parse_mode='HTML', reply_markup=markup)
    return msg

import re

def escape_markdown(text):
    # Экранирование специальных символов для MarkdownV2
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

def post_text_generator(post):
    post_text = escape_markdown(post['post_text'])
    # Ссылка на источник
    if post['source'] and post['message_id']:
        source_link = f'https://t.me/c/{post["source"]}/{post["message_id"]}'
        
        text = f'''
*Номер:* _{escape_markdown(str(post["id"]))}_
*Источник:* [Ссылка]({escape_markdown(source_link)})
*Дата:* {escape_markdown(str(post["parse_date"]))}

{post_text}
'''
    else:
        text = f'''
*Номер:* _{escape_markdown(str(post["id"]))}_
*Дата:* {escape_markdown(str(post["parse_date"]))}

{post_text}
'''     
    return text

def Apost_text_generator(post):
    post_text = escape_markdown(post['post_text'])
    # Ссылка на источник
    if post['source'] and post['message_id']:
        source_link = f'https://t.me/c/{post["source"]}/{post["message_id"]}'
        
        text = f'''
*Номер:* _{escape_markdown(str(post["id"]))}_
*Источник:* [Ссылка]({escape_markdown(source_link)})
*Дата:* {escape_markdown(str(post["archivation_date"]))}

{post_text}
'''
    else:
        text = f'''
*Номер:* _{escape_markdown(str(post["id"]))}_
*Дата:* {escape_markdown(str(post["archivation_date"]))}

{post_text}
'''     
    return text


@i_router.callback_query(F.data == 'start')
async def handle_start(call: types.CallbackQuery):
    await try_edit_call(call, 'Главное меню', main_menu)
    await call.answer()

@i_router.callback_query(F.data == 'channels_editor')
async def handle_channels_editor(call: types.CallbackQuery):
    channels_list = await get_channels()
    text = 'Список каналов: \n\n'
    if channels_list:
        for record in channels_list:
            index = channels_list.index(record) + 1
            text += f'{index}. <a href="{record['link']}">{record['channel_name']}</a> \n'
        await try_edit_call(call, text, await channels_markup())
        await call.answer()
    else:
        text += 'Нет активных каналов'
        await try_edit_call(call, text, channels_markup())
        await call.answer()

@i_router.callback_query(F.data.startswith("page_"))
async def paginate_channels(call: types.CallbackQuery):
    # Извлекаем номер страницы из callback_data
    page = int(call.data.split("_")[1])
    
    # Получаем клавиатуру для нужной страницы
    markup = await channels_markup(page=page)
    
    # Обновляем сообщение с новой клавиатурой
    await call.message.edit_reply_markup(reply_markup=markup)

@i_router.callback_query(F.data == 'add_channel')
async def handle_add_channel(call: types.CallbackQuery, state: FSMContext):
    text = 'Отправьте ссылку или тег канала, с которого нужно собирать посты: '
    await try_edit_call(call, text, add_back)
    await state.set_state(AddChannel.link)
    await call.answer()

@i_router.message(F.text.startswith('https://t.me/') or F.text.startswith('@'), AddChannel.link)
async def handle_new_channel(message: types.Message, state: FSMContext):
    response, data = await join_channel(message.text)
    # print(data.chats[0].id)
    if response == 'success':
        
        channel_id = data.chats[0].id
        channel_name = data.chats[0].title
        print(channel_id, channel_name)
        # chat = await bot.get_chat(chat_id='-100'+str(channel_id))
        await insert_new_channel(channel_id, 'https://t.me/c/' + str(channel_id), channel_name, 'Активный')
        await message.answer('Бот успешно вступил в канал!', reply_markup=main_menu)
        await state.clear()

    elif response == 'request':
        # await insert_new_channel(None,  None, message.text, 'Заявка')
        await message.answer('Бот успешно отправил заявку на вступление в канал', reply_markup=main_menu)
        await state.clear()
    
    else:
        await message.answer(f'Произошла ошибка при вступлении в канал. {response}', reply_markup=main_menu)
        await state.clear()

@i_router.callback_query(F.data == 'pub_channels')
async def handle_pub_channels(call: types.CallbackQuery):
    channels_list = await get_post_channels()  # Функция для получения каналов из БД
    text = 'Список каналов для публикации:\n\n'


    await try_edit_call(call, text, await pub_channels_markup())
    await call.answer()

@i_router.callback_query(F.data.startswith('Pdelete_'))
async def handle_delete_channel(call: types.CallbackQuery):
    channel_id = int(call.data.split('_')[1])  # Извлекаем ID канала

    # Удаляем канал из базы данных
    deleted_channel_name = await delete_post_channel_by_id(channel_id)

    if deleted_channel_name:
        await try_edit_call(call, f'Канал "{deleted_channel_name}" успешно удален.', await pub_channels_markup())
    else:
        await try_edit_call(call, 'Произошла ошибка при удалении канала.', await pub_channels_markup())

    await call.answer()



@i_router.callback_query(F.data == 'Padd_channel')
async def handle_add_post_channel(call: types.CallbackQuery, state: FSMContext):
    text = 'Отправьте ссылку или тег канала, в который нужно публиковать посты: '
    await try_edit_call(call, text, add_back)
    await state.set_state(AddPostChannel.link)
    await call.answer()

@i_router.message((F.text.startswith('https://t.me/') | F.text.startswith('@')), AddPostChannel.link)
async def handle_new_post_channel(message: types.Message, state: FSMContext):
    channel_link = message.text

    try:
        # Проверяем, является ли это ссылкой на канал или тегом
        if channel_link.startswith('https://t.me/'):
            # Извлекаем тег из ссылки
            channel_username = channel_link.split('/')[-1]
        else:
            channel_username = channel_link.lstrip('@')  # Убираем '@' из начала тега

        # Получаем информацию о канале по тегу
        chat = await bot.get_chat(f'@{channel_username}')
        
        # Получаем статус бота в канале
        bot_status = await bot.get_chat_member(chat.id, bot.id)
        
        # Проверяем, является ли бот администратором
        if bot_status.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
            channel_id = chat.id
            channel_name = chat.title
            
            # Сохраняем канал в базе данных
            await insert_post_channel(channel_id, channel_name)
            await message.answer('Канал для публикации успешно добавлен!', reply_markup=await pub_channels_markup())
        else:
            await message.answer('Ошибка: Бот не является администратором в этом канале.', reply_markup=await pub_channels_markup())
    except Exception as e:
        await message.answer(f'Ошибка при проверке канала: {e}', reply_markup=await pub_channels_markup())

    await state.clear()  # Очистка состояния




@i_router.callback_query(F.data.startswith('delete_'))
async def handle_delete_channel(call: types.CallbackQuery):
    channel_id = call.data.split('_')[1]
    chat = await get_channel_by_id(int(channel_id))
    try:
        result = await leave_channel(int('-100'+str(chat['channel_id'])))
        if result == 'success':
            channel_name = await delete_channel_by_id(channel_id)
            print(channel_name)
            await try_edit_call(call, f'Канал {channel_name['channel_name']} удален', await channels_markup())
            await call.answer()
        else:
            await try_edit_call(call, f'Произошла ошибка', await channels_markup())
            await call.answer()
    except:
        channel_name = await delete_channel_by_id(channel_id)
        await try_edit_call(call, f'Канал {channel_name['channel_name']} удален', await channels_markup())
        await call.answer()

@i_router.callback_query(F.data == 'nah')
async def func_for_func(call: types.CallbackQuery):
    await call.answer()

@i_router.callback_query(F.data == 'parse_results')
async def handle_parse_results(call: types.CallbackQuery):
    new_posts = await get_new_posts()
    
    if not new_posts:
        await call.message.edit_text("Нет новых постов.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Назад', callback_data='start')]
        ]))
        return
    
    # Показываем первый пост
    current_index = 0
    post = new_posts[current_index]
    text = post_text_generator(post)
    keyboard = create_navigation_keyboard(current_index, len(new_posts), post['id'])
    
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="MarkdownV2")

@i_router.callback_query(F.data.startswith("previous_post:") | F.data.startswith("next_post:"))
async def navigate_posts(call: types.CallbackQuery):
    new_posts = await get_new_posts()
    total_posts = len(new_posts)
    
    # Получаем текущий индекс из callback_data
    current_index = int(call.data.split(':')[1])
    post = new_posts[current_index]
    
    # Генерируем текст поста и обновляем кнопки навигации
    text = post_text_generator(post)
    keyboard = create_navigation_keyboard(current_index, total_posts, new_posts[current_index]['id'])
    
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="MarkdownV2")

@i_router.callback_query(F.data == 'back_editor')
async def handle_back_editor(call: types.CallbackQuery):
    await try_edit_call(call, 'Главное меню', main_menu)
    await call.answer()

@i_router.callback_query(F.data == 'new_post')
async def handle_new_post(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text('Введите текст поста: ', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Отмена', callback_data='back_editor')]
    ]))
    await state.set_state(ThirdPartyPost.post_text)
    await state.update_data({ 'msg_id': call.message.message_id })
    await state.update_data()
    await call.answer()

@i_router.message(ThirdPartyPost.post_text)
async def handle_third_party_post(message: types.Message, state: FSMContext):
    post_text = message.text
    data = await state.get_data()
    # await state.update_data({'post_text': message.text})
    post_id = await insert_new_third_post(post_text)
    msg_id = data['msg_id']
    # await bot.delete_message(chat_id=message.chat.id, )
    await message.delete()
    await bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
    # post = await insert_new_post(post_text, None, None)
    # msg_txt = post_text_generator(post)
    await message.answer(text=escape_markdown(post_text), reply_markup=third_party_markup(post_id), parse_mode='MarkdownV2')
    await state.clear()

@i_router.callback_query(F.data.startswith('np_edit_'))
async def handle_edit_third_party_post(call: types.CallbackQuery):
    post_id = int(call.data.split('_')[2])
    post = await get_third_party_post(post_id)
    edited_text, tokens = await ai_rewriting(post['text'])
    await insert_token_usage(tokens['prompt_tokens'], tokens['completion_tokens'], tokens['total_tokens'])
    await insert_third_rewrite(post_id, edited_text)
    refactors = await get_third_refactors(post_id)
    if len(refactors) < 2:
        await call.message.edit_reply_markup(reply_markup=None)
        await call.message.reply(text=edited_text, reply_markup=third_party_markup(post_id))
    else:
        await call.message.edit_text(text=edited_text, reply_markup=third_party_markup(post_id))

    await call.answer()


@i_router.callback_query(F.data == 'parse_archive_results')
async def handle_parse_archive_results(call: types.CallbackQuery):
    archive_posts = await get_archive_posts()
    
    if not archive_posts:
        await call.message.edit_text("Нет архивных постов.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Назад', callback_data='start')]
        ]))
        return
    
    # Показываем первый архивный пост
    current_index = 0
    post = archive_posts[current_index]
    text = Apost_text_generator(post)
    keyboard = Acreate_navigation_keyboard(current_index, len(archive_posts), post['id'])
    
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="MarkdownV2")

@i_router.callback_query(F.data.startswith("previous_archive_post:") | F.data.startswith("next_archive_post:"))
async def navigate_archive_posts(call: types.CallbackQuery):
    archive_posts = await get_archive_posts()
    total_posts = len(archive_posts)
    
    # Получаем текущий индекс из callback_data
    current_index = int(call.data.split(':')[1])
    post = archive_posts[current_index]
    
    # Генерируем текст поста и обновляем кнопки навигации
    text = Apost_text_generator(post)
    keyboard = Acreate_navigation_keyboard(current_index, total_posts, archive_posts[current_index]['id'])
    
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="MarkdownV2")

