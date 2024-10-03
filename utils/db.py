from loader import dp
from datetime import datetime
from pytz import timezone

async def get_updated_channel_list():
    async with dp['db_pool'].acquire() as connection:
        return await connection.fetch("SELECT * FROM ")
    
async def get_channels():
    async with dp['db_pool'].acquire() as connection:
        return await connection.fetch('SELECT * FROM active_channels')
    
async def get_channel_by_id(id):
    async with dp['db_pool'].acquire() as connection:
        data = await connection.fetch('SELECT * FROM active_channels WHERE id = $1', id)
        return data[0]
    
async def delete_channel_by_id(channel_id):
    async with dp['db_pool'].acquire() as conn:
        data = await conn.fetch('DELETE FROM active_channels WHERE id = $1 RETURNING channel_name', int(channel_id))
        return data[0]
async def get_new_posts():
    async with dp['db_pool'].acquire() as conn:
        return await conn.fetch('SELECT * FROM new_posts ORDER BY parse_date DESC')
    
async def insert_new_channel(id, link, channel_name, status):
    async with dp['db_pool'].acquire() as conn:
        await conn.fetch('INSERT INTO active_channels(channel_id, channel_name, link, status) VALUES($1, $2, $3, $4)', id, channel_name, link, status)

async def insert_new_post(post_text, source, message_id):
    async with dp['db_pool'].acquire() as conn:
        tz = timezone('Europe/Moscow')
        now = datetime.now(tz=tz)
        now = now.replace(tzinfo=None)
        data = await conn.fetchrow('INSERT INTO new_posts(post_text, source, message_id, parse_date) VALUES($1, $2, $3, $4) RETURNING *', post_text, source, message_id, now)
        return data
async def get_post_by_id(post_id):
    async with dp['db_pool'].acquire() as conn:
        try:
            data = await conn.fetch('SELECT * FROM new_posts WHERE id = $1', int(post_id))
            return data[0]
        except Exception as e:
            print(e)
            return None
        
async def insert_token_usage(tokens_input, tokens_output, tokens_sum):
    async with dp['db_pool'].acquire() as conn:
        tz = timezone('Europe/Moscow')
        now = datetime.now(tz=tz)
        now = now.replace(tzinfo=None)
        await conn.fetch('INSERT INTO tokens_usage (tokens_input, tokens_output, tokens_sum, date) VALUES($1, $2, $3, $4)', tokens_input, tokens_output, tokens_sum, now)

async def delete_post(post_id, ref_text):
    async with dp['db_pool'].acquire() as connection:
        async with connection.transaction():
            try:
                # Шаг 1: Извлекаем пост из new_posts
                post_query = "SELECT post_text, source, message_id FROM public.new_posts WHERE id = $1"
                post = await connection.fetchrow(post_query, int(post_id))
                
                if post is None:
                    print(f"Пост с ID {post_id} не найден в таблице новых постов.")
                    return False  # Пост не найден

                # Шаг 2: Вставляем пост в archive_posts
                archive_query = """
                    INSERT INTO public.archive_posts (post_text, source, message_id, archivation_date)
                    VALUES ($1, $2, $3, $4)
                """
                result = await connection.execute(
                    archive_query, ref_text, post['source'], post['message_id'], datetime.now()
                )

                if result != "INSERT 0 1":
                    print(f"Ошибка при вставке поста с ID {post_id} в архив.")
                    return False  # Ошибка при архивировании

                # Шаг 3: Удаляем пост из new_posts
                delete_query = "DELETE FROM public.new_posts WHERE id = $1"
                delete_result = await connection.execute(delete_query, int(post_id))

                if delete_result != "DELETE 1":
                    print(f"Ошибка при удалении поста с ID {post_id} из таблицы новых постов.")
                    return False  # Ошибка при удалении

                print(f"Пост с ID {post_id} успешно перемещён в архив.")
                return True  # Успешно перемещён

            except Exception as e:
                print(f"Ошибка при перемещении поста с ID {post_id}: {e}")
                return False  # Ошибка при перемещении поста

        
async def update_post_text(post_id, post_text):
    async with dp['db_pool'].acquire() as connection:
        await connection.fetch('UPDATE new_posts SET post_text = $1 WHERE id = $2', post_text, post_id)

async def get_channels_for_posting():
    async with dp['db_pool'].acquire() as connection:
        return await connection.fetch('SELECT * FROM post_channels')
    
async def insert_refactor(source, message_id, post_text, reply_message_id):
    # Установка временной зоны Europe/Moscow
    moscow_tz = timezone('Europe/Moscow')
    
    # Получение текущего времени без временной зоны
    current_time_naive = datetime.now()
    
    # Привязка к временной зоне
    current_time = moscow_tz.localize(current_time_naive)

    query = """
        INSERT INTO public.refactors (text, dt, source, message_id, reply_message_id)
        VALUES ($1, $2, $3, $4, $5) RETURNING id
    """
    id = await dp['db_pool'].execute(query, post_text, current_time.replace(tzinfo=None), source, int(message_id), reply_message_id)
    return id[0]
async def get_post_edit_data(post_id):
    # Сначала получаем source и message_id из new_posts
    post_query = """
        SELECT source, message_id 
        FROM public.new_posts 
        WHERE id = $1
    """
    post_data = await dp['db_pool'].fetchrow(post_query, post_id)
    
    if post_data is None:
        return None  # Пост не найден в new_posts

    source = post_data['source']
    message_id = post_data['message_id']

    # Теперь получаем данные из refactors по source и message_id
    refactor_query = """
        SELECT text, dt, reply_message_id
        FROM public.refactors 
        WHERE source = $1 AND message_id = $2
    """
    refactors = await dp['db_pool'].fetch(refactor_query, source, message_id)

    # Формируем результат
    if refactors:
        array_of_refactors = [refactor['text'] for refactor in refactors]
        # original_post_text = await get_original_post_text(source, message_id)  # Опционально, если нужно получить оригинальный текст
        return {
            # 'original_post_text': original_post_text,
            'original_message_id': message_id,
            'array_of_refactors': array_of_refactors,
            'reply_message_id': refactors[0]['reply_message_id']
        }
    
    return {
        'original_post_text': None,
        'original_message_id': message_id,
        'reply_message_id': None,
        'array_of_refactors': []
    }


async def update_post_refactors(post_id, array_of_refactors, current_index):
    query = """
        UPDATE post_edits SET array_of_refactors = $2, current_index = $3
        WHERE post_id = $1
    """
    await dp['db_pool'].execute(query, post_id, array_of_refactors, current_index)


async def insert_post_channel(channel_id: int, channel_name: str):
    query = """
    INSERT INTO public.post_channels (id, title)
    VALUES ($1, $2)
    ON CONFLICT (id) DO NOTHING;
    """
    await dp['db_pool'].execute(query, channel_id, channel_name)


async def get_post_channels():
    async with dp['db_pool'].acquire() as connection:
        query = "SELECT id, title FROM public.post_channels;"
        result = await connection.fetch(query)
        return [{'id': record['id'], 'title': record['title']} for record in result]
    

async def delete_post_channel_by_id(channel_id):
    async with dp['db_pool'].acquire() as connection:
        query = "DELETE FROM public.post_channels WHERE id = $1 RETURNING title;"
        result = await connection.fetchrow(query, channel_id)
        return result['title'] if result else None

async def get_refactor_text(source: int, message_id: int, index: int):
    async with dp['db_pool'].acquire() as connection:
        # Запрос для получения всех рефакторов для поста
        query = """
        SELECT text 
        FROM refactors
        WHERE source = $1 AND message_id = $2
        ORDER BY dt ASC
        """
        
        # Выполняем запрос
        results = await connection.fetch(query, source, message_id)
        
        # Проверяем, есть ли результаты и валиден ли индекс
        if results and 0 <= index < len(results):
            return results[index]['text']  # Возвращаем текст рефактора по индексу
        else:
            return None  # Если индекс невалиден или рефакторы отсутствуют

async def get_post_by_source_and_message_id(source: int, message_id: int):
    query = """
        SELECT * FROM new_posts
        WHERE source = $1 AND message_id = $2
    """
    async with dp['db_pool'].acquire() as conn:
        post = await conn.fetchrow(query, source, message_id)
    return post

async def get_post_id(source: int, message_id: int) -> int:
    # Предположим, что в таблице posts есть связь между рефакторами и постами
    query = """
        SELECT id 
        FROM new_posts 
        WHERE source = $1 AND message_id = $2
    """

    async with dp['db_pool'].acquire() as connection:
        # Получаем post_id для указанного source и message_id
        post_id = await connection.fetchval(query, source, message_id)

    # Вернем post_id или None, если не найдено
    return post_id

async def get_channel_ids_from_db():
    async with dp['db_pool'].acquire() as conn:
        query = "SELECT channel_id FROM post_channels"
        records = await conn.fetch(query)
        return [record['channel_id'] for record in records]
    
# Функция проверки наличия канала в базе данных
async def check_channel_exists(channel_id: int):
    query = """
        SELECT EXISTS(SELECT 1 FROM active_channels WHERE channel_id = $1)
    """
    async with dp['db_pool'].acquire() as conn:
        exists = await conn.fetchval(query, channel_id)
    return exists

# Функция добавления нового канала в базу данных
async def add_new_channel(channel_name: str, channel_id: int):
    query = """
        INSERT INTO active_channels (channel_name, link, status, channel_id)
        VALUES ($1, $2, $3, $4)
    """
    channel_link = f"https://t.me/{channel_id}"  # Создание ссылки на канал
    async with dp['db_pool'].acquire() as conn:
        await conn.execute(query, channel_name, channel_link, 'Активный', channel_id)
    print(f"Новый канал добавлен в БД: {channel_name} (ID: {channel_id})")

# Получение архивных постов из базы данных
async def get_archive_posts():
    query = """
        SELECT * FROM archive_posts
    """
    async with dp['db_pool'].acquire() as conn:
        posts = await conn.fetch(query)
    return posts


async def insert_new_third_post(post_text):
    async with dp['db_pool'].acquire() as conn:
        post_id = await conn.fetchval('INSERT INTO third_posts(text) VALUES($1) RETURNING id', post_text)
        return post_id
    
async def get_third_party_post(post_id):
    async with dp['db_pool'].acquire() as conn:
        post = await conn.fetch('SELECT * FROM third_posts WHERE id = $1', post_id)
        return post[0]
    
async def insert_third_rewrite(post_id, text):
    async with dp['db_pool'].acquire() as conn:
        await conn.fetch('INSERT INTO third_refactor (post_id, text) VALUES ($1, $2)', post_id, text)

async def get_third_refactors(post_id):
    async with dp['db_pool'].acquire() as conn:
        return await conn.fetch('SELECT * FROM third_refactor WHERE post_id = $1', post_id)