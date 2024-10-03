from aiogram import Router, F
from aiogram import types
from aiogram.fsm.context import FSMContext
# from utils.db import get_channels
from keyboards.inline_keyboard import *
from utils.states import *
from utils.db import *
# from user_bot import join_channel, leave_channel
# from inline_router import try_edit_call
from config import AI_TOKEN
from openai import AsyncOpenAI
import logging
import tiktoken
from loader import bot


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

async def try_edit_call_reply(callback, text, markup, reply_id):
    try:
        msg = await callback.message.edit_text(text=text, parse_mode='HTML', reply_to_message_id=reply_id,  reply_markup=markup)
    except:
        await try_delete_call(callback)
        msg = await callback.message.answer(text=text, parse_mode='HTML', reply_to_message_id=reply_id,  reply_markup=markup)
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

post_router = Router()


async def ai_rewriting(post_text):
    client = AsyncOpenAI(api_key=AI_TOKEN)
    encoding = tiktoken.encoding_for_model('gpt-3.5-turbo-instruct')
    prompt = f'Перефразируй данный текст, сохраняя стиль: {post_text}'
    tokens = encoding.encode(prompt)
    print('Tokens: ', len(tokens))
    # client.chat.completions - 4o и т.д.
    response = await client.completions.create(
        model='gpt-3.5-turbo-instruct',
        prompt=prompt,
        max_tokens=len(tokens)*2,
        temperature=0.7
    )
    print(response)
    tokens = {
        'prompt_tokens': response.usage.prompt_tokens,
        'completion_tokens': response.usage.completion_tokens,
        'total_tokens': response.usage.total_tokens
    }
    return response.choices[0].text.strip(), tokens

@post_router.callback_query(F.data.startswith('edit_'))
async def handle_edit(call: types.CallbackQuery):
    post_id = call.data.split('_')[1]
    
    # Получение поста из базы данных по ID
    post = await get_post_by_id(post_id)
    if post is None:
        await call.answer("Пост не найден.")
        return
    
    # Извлечение текста поста
    post_text = post['post_text']
    
    # Если в post_id содержатся данные о source и message_id (например, 'source_message_id')
    source, message_id = post['source'], post['message_id']
    
    # Или если пост_id сам является комбинацией source и message_id (например, '123_456'):
    # source, message_id = post_id.split('_')

    print(f'Post ID: {post_id}, Source: {source}, Message ID: {message_id}')
    
    # Обновляем клавиатуру редактирования
    await call.message.edit_reply_markup(reply_markup=await refactor_markup(source, message_id, int(post_id)))
    await call.answer()



@post_router.callback_query(F.data.startswith('refactor_'))
async def handle_refactor(call: types.CallbackQuery):
    # Извлекаем source и message_id из callback_data
    data = call.data.split('_')
    source = int(data[1])
    message_id = int(data[2])
    post_id = int(data[3])
    
    # Очищаем клавиатуру перед обработкой
    await call.message.edit_reply_markup(reply_markup=None)
    
    # Получаем пост по source и message_id
    post = await get_post_by_id(int(post_id))
    if post is None:
        await call.answer("Пост не найден.")
        return
    
    # Сообщаем пользователю, что начинается генерация
    msg = await call.message.answer('Подождите, ответ генерируется...')
    
    # Получаем информацию о текущем посте и сгенерированных версиях из БД
    post_edit_data = await get_post_edit_data(post_id)
    if post_edit_data is None:
        await call.answer("Нет данных для редактирования.")
        return
    
    # Получаем массив рефакторов, оригинальное сообщение и ID ответа
    original_message_id = post_edit_data['original_message_id']
    array_of_refactors = post_edit_data.get('array_of_refactors', [])
    reply_message_id = post_edit_data.get('reply_message_id')

    # Генерация нового текста с помощью AI
    ai_post_text, tokens = await ai_rewriting(post['post_text'])
    
    # Удаляем сообщение "Подождите..."
    await msg.delete()

    # Вставляем данные об использовании токенов в базу данных
    await insert_token_usage(tokens['prompt_tokens'], tokens['completion_tokens'], tokens['total_tokens'])

    # Обновляем массив рефакторов и добавляем новый текст
    array_of_refactors.append(ai_post_text)
    
    # Вставляем новый рефактор в базу данных
    await insert_refactor(source, message_id, ai_post_text, call.message.message_id)

    # Если есть хотя бы один рефактор, показываем обновленный текст с навигацией по версиям
    if len(array_of_refactors) < 2:
        # Если это первый рефактор
        await call.message.answer(
            f'Измененный текст поста ({len(array_of_refactors)}/{len(array_of_refactors)}): \n' + ai_post_text,
            reply_to_message_id=reply_message_id if reply_message_id else call.message.message_id,
            reply_markup=await refactor_markup(source, message_id,post_id=int(post_id), current_index=len(array_of_refactors) - 1)
        )
    else:
        # Если уже есть несколько рефакторов, обновляем существующее сообщение
        await try_edit_call_reply(
            call, 
            f'Измененный текст поста ({len(array_of_refactors)}/{len(array_of_refactors)}): \n' + ai_post_text, 
            await refactor_markup(source, message_id,int(post_id), current_index=len(array_of_refactors) - 1), 
            reply_message_id
        )

    # Уведомляем пользователя о завершении операции
    await call.answer()


# except Exception as e:
    # logging.log(level=logging.INFO, msg=e)
    # print(e)
    # await call.answer('Что-то пошло не так!')



@post_router.callback_query(F.data.startswith('deletePost_'))
async def handle_delete_post(call: types.CallbackQuery):
    source = int(call.data.split('_')[1])
    message_id = int(call.data.split('_')[2])
    post_id = await get_post_id(source, message_id)
    post = await get_post_by_id(post_id)
    refactors = await get_post_edit_data(post_id)
    flag = await delete_post(post_id, post['post_text'])
    if flag:
        data = await get_new_posts()
        # index = data.index(await get_post_by_id(post_id))
        
        print('ref:', refactors)
        arr_refactors = refactors['array_of_refactors']
        # print('index:', index)
        if len(arr_refactors) > 0: 
            reply_message_id = refactors['reply_message_id']
            
            # Обновляем сообщение с подтверждением
            text = post_text_generator(post)
            # await delete_post(post_id, post)
            await bot.edit_message_text(chat_id=call.message.chat.id, text=f'~{escape_markdown(text)}~', message_id=reply_message_id, parse_mode='MarkdownV2')
            await call.message.delete()
            await call.answer('Пост был успешно удален!')
        else:
            # reply_message_id = refactors['reply_message_id']
            # await delete_post(post_id, post)
            await bot.edit_message_text(chat_id=call.message.chat.id, text=f'~{escape_markdown(call.message.text)}~', message_id=call.message.message_id, parse_mode='MarkdownV2')
            await call.answer('Пост был успешно удален!')

    else:
        await call.answer('Не удалось удалить пост.')

@post_router.callback_query(F.data.startswith('save_'))
async def handle_save_edition(call: types.CallbackQuery):
    # Извлекаем source, message_id и индекс рефактора из callback_data
    data = call.data.split('_')
    source = int(data[1])
    message_id = int(data[2])
    refactor_index = int(data[3])

    # Получаем текст рефактора по индексу
    refactor_text = await get_refactor_text(source, message_id, refactor_index)

    if refactor_text:
        try:
            # Получаем post_id на основе source и message_id
            post_id = await get_post_id(source, message_id)
            
            if post_id is not None:  # Проверяем, что post_id успешно получен
                # Обновляем оригинальный пост новым текстом
                await update_post_text(post_id, refactor_text)  # Обновляем текст поста по post_id
                await call.answer('Текст поста обновлен!')
            else:
                await call.answer('Не удалось получить ID поста.', show_alert=True)
        except Exception as e:
            await call.answer(f'Ошибка при сохранении: {str(e)}', show_alert=True)
    else:
        await call.answer('Рефактор не найден.')

@post_router.callback_query(F.data.startswith('Rposting_'))
async def handle_post(call: types.CallbackQuery):
    # Извлекаем данные из callback_data
    data = call.data.split('_')
    source = int(data[1])
    message_id = int(data[2])
    current_index = int(data[3])

    try:
        # Получаем текст поста (например, из базы данных)
        # post_id = await get_post_id(source, message_id, current_index)
        # array_of_refactors = await get_post_edit_data(post_id)
        edit_text = await get_refactor_text(source, message_id, current_index)  # Добавьте свою функцию для получения текста поста

        # Обновляем сообщение с выбором канала
        await try_edit_call(call, 
            f'{edit_text}\n<b>Выберите канал, в который нужно выложить этот пост:</b>', 
            await for_pub_channels_markup(source, message_id, current_index)  # Функция для получения разметки кнопок каналов
        )
        
        await call.answer()
    except Exception as e:
        print(e)
        await call.answer('Произошла ошибка с загрузкой каналов!')

@post_router.callback_query(F.data.startswith('change_page_'))
async def change_page(call: types.CallbackQuery):
    # Извлекаем информацию из callback_data
    data = call.data.split('_')
    source = int(data[1])  # Получаем source
    message_id = int(data[2])  # Получаем message_id
    current_index = int(data[3])  # Получаем current_index
    page = int(data[4])  # Получаем номер страницы
    
    # Обновляем клавиатуру с учетом дополнительных параметров
    keyboard = await for_pub_channels_markup(source, message_id, current_index, page)
    
    await call.message.edit_reply_markup(reply_markup=keyboard)
    await call.answer()


@post_router.callback_query(F.data.startswith('channel_'))
async def handle_channel_selection(call: types.CallbackQuery):
    # Извлекаем данные из callback_data
    data = call.data.split('_')
    channel_id = int(data[2])  # Получаем ID выбранного канала
    source = int(data[1])       # Получаем source
    message_id = int(data[3])   # Получаем message_id
    current_index = int(data[4])  # Получаем текущий индекс рефактора

    try:
        # Получаем post_id
        post_id = await get_post_id(source, message_id)
        print(f"Полученный post_id: {post_id}")  # Логируем post_id

        # Получаем массив рефакторов
        refactor_data = await get_post_edit_data(post_id)
        print(f"Массив рефакторов: {refactor_data}")  # Логируем массив рефакторов
        reply_message_id = refactor_data['reply_message_id']
        # Извлекаем array_of_refactors из словаря
        array_of_refactors = refactor_data.get('array_of_refactors', [])
        
        # Проверяем, есть ли рефакторы и действителен ли индекс
        if not array_of_refactors or current_index < 0 or current_index >= len(array_of_refactors):
            await call.answer('Рефактор не найден или индекс вне диапазона.', show_alert=True)
            return

        # Получаем текст рефактора по индексу
        refactor_text = array_of_refactors[current_index]
        print(f"Текст рефактора: {refactor_text}")  # Логируем текст рефактора

        # Отправляем сообщение в выбранный канал

        await bot.send_message(chat_id=channel_id, text=refactor_text)
        
        post = await get_post_by_id(post_id)
        # Обновляем сообщение с подтверждением
        text = post_text_generator(post)
        await delete_post(post_id, refactor_text)
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=reply_message_id, text=escape_markdown('✅ Пост был успешно выложен!\n') + f'~{text}~', parse_mode='MarkdownV2')
        await call.message.delete()
        await call.answer()
    except Exception as e:
        print(f"Ошибка в handle_channel_selection: {e}")
        await call.answer('Что-то пошло не так!')




@post_router.callback_query(F.data.startswith('Rnext_') | F.data.startswith('Rprevious_'))
async def handle_switch(call: types.CallbackQuery):
    action, post_id, current_index = call.data.split('_')
    current_index = int(current_index)  # Преобразуем индекс в число

    # Получаем текущее состояние данных
    # data = await state.get_data()
    
    # Получение информации о посте и версиях рефакторов из БД
    post_edit_data = await get_post_edit_data(int(post_id))
    post = await get_post_by_id(int(post_id))
    if post_edit_data is None:
        await call.answer("Данные для редактирования не найдены.")
        return

    # Получаем массив версий поста
    array_of_refactors = post_edit_data.get('array_of_refactors', [])

    # Обработка действий переключения
    if action == 'Rnext':
        new_index = (current_index + 1) % len(array_of_refactors)  # Круговое переключение
    elif action == 'Rprevious':
        new_index = (current_index - 1) % len(array_of_refactors)  # Круговое переключение
    else:
        return

    # Получаем новый текст для отображения
    new_text = array_of_refactors[new_index]
    
    # Обновляем сообщение с новой версией текста
    await try_edit_call(call,
        f'Измененный текст поста ({new_index + 1}/{len(array_of_refactors)}):\n{new_text}',
        await refactor_markup(post['source'], post['message_id'], int(post_id), new_index)  # Обновляем разметку для текущего индекса
    )
    
    # Обновляем индекс в состоянии FSM
    # await state.update_data({'current_index': new_index})

    await call.answer()

