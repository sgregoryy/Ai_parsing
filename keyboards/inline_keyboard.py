from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from utils.db import *

main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text = 'Редактор каналов', callback_data='channels_editor')],
    [InlineKeyboardButton(text='Новый пост', callback_data='new_post')],
    [InlineKeyboardButton(text = 'Архив', callback_data='parse_archive_results')],
    [InlineKeyboardButton(text = 'Каналы для публикации', callback_data='pub_channels')]
])


add_back = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Назад', callback_data='pub_channels')]
])
def third_party_markup(post_id):
    third_party_post = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Редактировать', callback_data=f'np_edit_{post_id}')],
        [InlineKeyboardButton(text='Удалить', callback_data=f'np_delete_{post_id}')],
        [InlineKeyboardButton(text='Назад', callback_data='npback')]
    ])
    return third_party_post

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

ITEMS_PER_PAGE = 5  # Установите нужное количество элементов на странице

async def pub_channels_markup(page: int = 1):
    # Получаем все каналы
    channels = await get_post_channels()  # Убедитесь, что эта функция возвращает нужные каналы

    # Определяем количество страниц
    total_pages = (len(channels) - 1) // ITEMS_PER_PAGE + 1

    # Определяем диапазон каналов для текущей страницы
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    current_page_channels = channels[start_idx:end_idx]

    # Создаем клавиатуру
    markup = InlineKeyboardMarkup(inline_keyboard=[])

    # Добавляем каналы на текущей странице
    for channel in current_page_channels:
        markup.inline_keyboard.append([
            InlineKeyboardButton(text=f"{channel['title']}", callback_data=f'channel_{channel["id"]}'),
            # InlineKeyboardButton(text=f'{channel["status"]}', callback_data='nah'),
            InlineKeyboardButton(text='Удалить', callback_data=f'Pdelete_{channel["id"]}')
        ])

    # Добавляем кнопку для добавления нового канала и кнопку "Назад"
    markup.inline_keyboard.append([
        InlineKeyboardButton(text='➕Добавить канал', callback_data='Padd_channel'),
        
    ])
    markup.inline_keyboard.append([
        InlineKeyboardButton(text='Назад', callback_data='back_editor')
    ])
    # Добавляем навигационные кнопки для переключения страниц
    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f'page_{page - 1}'))
    if page < total_pages:
        navigation_buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f'page_{page + 1}'))

    # Если есть навигационные кнопки, добавляем их в клавиатуру
    if navigation_buttons:
        markup.inline_keyboard.append(navigation_buttons)

    return markup


async def for_pub_channels_markup(source: int, message_id: int, current_index: int, page: int = 1):
    # Получаем все каналы
    channels = await get_post_channels()  # Убедитесь, что эта функция возвращает нужные каналы

    # Определяем количество страниц
    total_pages = (len(channels) - 1) // ITEMS_PER_PAGE + 1

    # Определяем диапазон каналов для текущей страницы
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    current_page_channels = channels[start_idx:end_idx]

    # Создаем клавиатуру
    markup = InlineKeyboardMarkup(inline_keyboard=[])

    # Добавляем каналы на текущей странице
    for channel in current_page_channels:
        markup.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{channel['title']}",
                callback_data=f'channel_{source}_{channel["id"]}_{message_id}_{current_index}'
            )
        ])

    # Добавляем навигационные кнопки для переключения страниц
    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f'page_{source}_{message_id}_{current_index}_{page - 1}'))
    if page < total_pages:
        navigation_buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f'page_{source}_{message_id}_{current_index}_{page + 1}'))

    # Если есть навигационные кнопки, добавляем их в клавиатуру
    if navigation_buttons:
        markup.inline_keyboard.append(navigation_buttons)

    return markup

async def edit_markup(post_id, current_index=0):
    # Получаем все посты для текущего пользователя или проекта
    data = await get_new_posts()

    # Находим индекс текущего поста
    post = await get_post_by_id(post_id)
    index = data.index(post)
    print('index:', index)

    # Создаем основную клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='AI редактирование', callback_data=f'refactor_{post_id}'),
         InlineKeyboardButton(text='Удалить', callback_data=f'deletePost_{post_id}')],
        [InlineKeyboardButton(text='Опубликовать', callback_data=f'posting_{post_id}'),
         InlineKeyboardButton(text='Сохранить', callback_data=f'save_{post_id}')]
    ])

    # Добавляем кнопки "Предыдущий" и "Следующий", если есть несколько версий текста
    if current_index > 0:
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text='⬅️      ', callback_data=f'previous_{post_id}_{current_index}')]
        )
    if current_index < len(data) - 1:
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text='      ➡️', callback_data=f'next_{post_id}_{current_index}')]
        )

    return keyboard

async def refactor_markup(source: int, message_id: int, post_id:int, current_index=0):
    post_edit_data = await get_post_edit_data(post_id)
    if post_edit_data is None:
        return None

    array_of_refactors = post_edit_data.get('array_of_refactors', [])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='AI редактирование', callback_data=f'refactor_{source}_{message_id}_{post_id}'),
         InlineKeyboardButton(text='Удалить', callback_data=f'deletePost_{source}_{message_id}')],
        #  InlineKeyboardButton(text='Сохранить', callback_data=f'save_{source}_{message_id}_{current_index}')]  # Сохранить выбранную версию
    ])

    if len(array_of_refactors) > 0:
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text='Опубликовать', callback_data=f'Rposting_{source}_{message_id}_{current_index}')])
    if len(array_of_refactors) > 1:
        keyboard.inline_keyboard.append(
            # [InlineKeyboardButton(text='Опубликовать', callback_data=f'Rposting_{source}_{message_id}_{current_index}')],
        [
            InlineKeyboardButton(text='⬅️ Предыдущий', callback_data=f'Rprevious_{post_id}_{current_index}'),
            InlineKeyboardButton(text='Следующий ➡️', callback_data=f'Rnext_{post_id}_{current_index}')
        ])

    return keyboard






ITEMS_PER_PAGE = 10

def group_markup(post_id, source, message_id):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Удалить', callback_data=f'deletePost_{source}_{message_id}')],
        [InlineKeyboardButton(text='Редактировать', callback_data=f'edit_{post_id}')],
        # [prev_button, next_button]
    ])
    return markup

async def channels_markup(page: int = 1):
    # Получаем все каналы
    channels = await get_channels()
    
    # Определяем количество страниц
    total_pages = (len(channels) - 1) // ITEMS_PER_PAGE + 1

    # Определяем диапазон каналов для текущей страницы
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    current_page_channels = channels[start_idx:end_idx]

    # Создаем клавиатуру
    markup = InlineKeyboardMarkup(inline_keyboard=[])

    # Добавляем каналы на текущей странице
    for channel in current_page_channels:
        markup.inline_keyboard.append([
            InlineKeyboardButton(text=f"{channel['channel_name']}", callback_data='nah'),
            InlineKeyboardButton(text=f'{channel["status"]}', callback_data='nah'),
            InlineKeyboardButton(text='Удалить', callback_data=f'delete_{channel["id"]}')
        ])

    # Добавляем навигационные кнопки для переключения страниц
    navigation_buttons = []
    markup.inline_keyboard.append([InlineKeyboardButton(text = '➕Добавить канал', callback_data='add_channel')])
    markup.inline_keyboard.append([InlineKeyboardButton(text='Назад', callback_data='back_editor')])
    if page > 1:
        navigation_buttons.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f'page_{page - 1}'))
    if page < total_pages:
        navigation_buttons.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f'page_{page + 1}'))

    # Если есть навигационные кнопки, добавляем их в клавиатуру
    if navigation_buttons:
        markup.inline_keyboard.append(navigation_buttons)

    return markup

def create_navigation_keyboard(current_index: int, total_posts: int, post_id: int) -> InlineKeyboardMarkup:
    # Кнопка "Предыдущий" (неактивна, если текущий индекс равен 0)
    prev_button = InlineKeyboardButton(
        text="Предыдущий", 
        callback_data=f"previous_post:{current_index - 1}" if current_index > 0 else f"previous_post:{total_posts - 1}"
    )
    
    # Кнопка "Следующий" (неактивна, если текущий индекс равен последнему посту)
    next_button = InlineKeyboardButton(
        text="Следующий", 
        callback_data=f"next_post:{current_index + 1}" if current_index < total_posts - 1 else "next_post:0"
    )

    # Создание клавиатуры с двумя кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Удалить', callback_data=f'deletePost_{post_id}')],
        [InlineKeyboardButton(text='Редактировать', callback_data=f'edit_{post_id}')],
        [prev_button, next_button]
    ])

    return keyboard


def after_delete_markup(post_id, type_):

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='AI редактирование', callback_data=f'refactor_{post_id}')],
        [InlineKeyboardButton(text='Опубликовать', callback_data=f'posting_{post_id}')],
        [InlineKeyboardButton(text='Назад', callback_data=f'next_post:{post_id}')]
    ])
    return keyboard


CHANNELS_PER_PAGE = 5

async def posting_channels_list_markup(page: int = 1):
    channels = await get_channels_for_posting()
    
    # Рассчитываем количество страниц
    total_channels = len(channels)
    total_pages = (total_channels + CHANNELS_PER_PAGE - 1) // CHANNELS_PER_PAGE

    # Определяем диапазон каналов для текущей страницы
    start_index = (page - 1) * CHANNELS_PER_PAGE
    end_index = min(start_index + CHANNELS_PER_PAGE, total_channels)

    # Создаем клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    # Добавляем каналы в клавиатуру
    for i in range(start_index, end_index):
        channel = channels[i]
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=channel['name'],  # Название канала
                callback_data=f"channel_select_{channel['id']}"  # Данные для обработки нажатия
            )]
        )
    
    # Кнопки переключения страниц (если страниц больше 1)
    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"change_page_{page - 1}"
            )
        )
    
    if page < total_pages:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=f"change_page_{page + 1}"
            )
        )
    
    if navigation_buttons:
        keyboard.inline_keyboard.append(*navigation_buttons)

    return keyboard

def Acreate_navigation_keyboard(current_index: int, total_posts: int, post_id: int):
    prev_button = InlineKeyboardButton(
        text="Предыдущий", 
        callback_data=f"previous_archive_post:{current_index - 1}" if current_index > 0 else f"previous_archive_post:{total_posts - 1}"
    )
    
    # Кнопка "Следующий" (неактивна, если текущий индекс равен последнему посту)
    next_button = InlineKeyboardButton(
        text="Следующий", 
        callback_data=f"next_archive_post:{current_index + 1}" if current_index < total_posts - 1 else "next_archive_post:0"
    )

    # Создание клавиатуры с двумя кнопками
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [prev_button, next_button]
    ])

    return keyboard
