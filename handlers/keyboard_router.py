from aiogram import Router, F
from aiogram import types
from aiogram.filters.command import CommandStart
from keyboards.inline_keyboard import main_menu
from loader import dp
from datetime import datetime
import pytz

k_router = Router()
@k_router.message(CommandStart())
async def handle_start(message: types.Message):
    await message.answer('Главное меню', reply_markup=main_menu)

@k_router.message(F.text == '/start')
async def handle_start(message: types.Message):
    await message.answer('Главное меню', reply_markup=main_menu)

@k_router.message(F.text == '/tokens')
async def handle_tokens_stats(message: types.Message):
    try:
        # Московская временная зона
        moscow_tz = pytz.timezone('Europe/Moscow')
        now_moscow = datetime.now(moscow_tz)

        # Общий расход за последние 30 дней
        total_usage_30_days_query = """
        SELECT SUM(tokens_sum) AS total_tokens
        FROM tokens_usage
        WHERE date >= $1::timestamp without time zone - INTERVAL '30 days';
        """
        total_usage_30_days = await dp['db_pool'].fetchval(total_usage_30_days_query, now_moscow.replace(tzinfo=None)) or 0

        # Вычисляем средний расход за каждый день за последние 30 дней
        day_avg_query = """
        SELECT AVG(daily_tokens) AS avg_day_tokens
        FROM (
            SELECT SUM(tokens_sum) AS daily_tokens
            FROM tokens_usage
            WHERE date >= $1::timestamp without time zone - INTERVAL '30 days'
            GROUP BY DATE(date)
        ) AS daily_totals;
        """
        daily_totals = await dp['db_pool'].fetch(day_avg_query, now_moscow.replace(tzinfo=None))

        # Считаем общее количество дней с расходом
        total_days = len(daily_totals)
        day_avg = (sum(row['avg_day_tokens'] for row in daily_totals) / total_days) if total_days > 0 else 0

        # Общий расход за последние 12 месяцев
        total_usage_12_months_query = """
        SELECT SUM(tokens_sum) AS total_tokens
        FROM tokens_usage
        WHERE date >= $1::timestamp without time zone - INTERVAL '12 months';
        """
        total_usage_12_months = await dp['db_pool'].fetchval(total_usage_12_months_query, now_moscow.replace(tzinfo=None)) or 0

        # Вычисляем средний расход за каждый месяц за последние 12 месяцев
        month_avg_query = """
        SELECT AVG(monthly_tokens) AS avg_month_tokens
        FROM (
            SELECT SUM(tokens_sum) AS monthly_tokens
            FROM tokens_usage
            WHERE date >= $1::timestamp without time zone - INTERVAL '12 months'
            GROUP BY DATE_TRUNC('month', date)
        ) AS monthly_totals;
        """
        monthly_totals = await dp['db_pool'].fetch(month_avg_query, now_moscow.replace(tzinfo=None))

        # Считаем общее количество месяцев с расходом
        total_months = len(monthly_totals)
        month_avg = (sum(row['avg_month_tokens'] for row in monthly_totals) / total_months) if total_months > 0 else 0

        # Формируем ответное сообщение
        response_text = f"Статистика по расходу токенов:\n" \
                        f"Общий расход за последние 30 дней: {total_usage_30_days}\n" \
                        f"За день (среднее по последним 30 дням): {day_avg:.2f}\n" \
                        f"Общий расход за последние 12 месяцев: {total_usage_12_months}\n" \
                        f"За месяц (среднее по последним 12 месяцам): {month_avg:.2f}"

        # Отправляем ответ пользователю
        await message.answer(response_text)

    except Exception as e:
        print(f"Ошибка в handle_tokens_stats: {e}")
        await message.answer("Произошла ошибка при получении статистики по токенам.")
