from handlers.inline_router import i_router
import logging
from aiogram import Dispatcher
from config import username, password, host, database
from loader import bot, dp
from handlers import inline_router, keyboard_router, post_router
import asyncpg
from user_bot import telethon_task  # Импортируем задачу user-бота
import asyncio

# Функция запуска всех процессов и интеграция
async def on_startup(dp: Dispatcher):
    dp.include_routers(inline_router.i_router, keyboard_router.k_router, post_router.post_router) # + , post_router.post_router для нормальных людей
    
    # Создаем пул базы данных
    await create_db_pool(dp)

    # Запускаем Telethon user-бот в отдельной задаче
    asyncio.create_task(telethon_task())  # Запуск user-бота через Telethon

# Функция создания пула соединений с базой данных
async def create_db_pool(dp):
    dp['db_pool'] = await asyncpg.create_pool(
        user=username,
        password=password,
        host=host,
        database=database,
    )

# Закрытие пула базы данных
async def close_db_pool(dp):
    await dp['db_pool'].close()

# Завершение работы, закрытие ресурсов
async def on_shutdown(dp):
    await close_db_pool(dp)

# Главная функция
if __name__ == '__main__':
    # Основной цикл событий
    loop = asyncio.get_event_loop()

    try:
        # Логирование
        logging.basicConfig(level=logging.INFO, filename="logs.txt")

        # Запускаем startup процедуры и обработку событий aiogram
        loop.run_until_complete(on_startup(dp))
        loop.run_until_complete(dp.start_polling(bot))
    
    except KeyboardInterrupt:
        pass

    finally:
        # Завершение всех процессов
        loop.run_until_complete(on_shutdown(dp))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
