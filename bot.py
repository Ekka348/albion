import asyncio
import json
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Настройки
API_TOKEN = os.getenv('BOT_TOKEN', '8404262144:AAFhLqVbU4FpIrM6KWfU6u9L1l5Qh-FYLWk')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://albion-production.up.railway.app')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Хранилище сессий игроков
user_sessions = {}

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user_sessions[user_id] = {
        'player_hp': 100,
        'monster_hp': 100
    }
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🐗 БИТЬ КАБАНА",
        web_app=types.WebAppInfo(url=WEBAPP_URL)
    ))
    
    await message.answer(
        "🔥 Нажимай кнопку и бей кабана!\n"
        "Кабан тоже бьет в ответ!",
        reply_markup=builder.as_markup()
    )

@dp.message(Command('ping'))
async def cmd_ping(message: types.Message):
    await message.answer("🏓 pong")

@dp.message(lambda message: message.web_app_data)
async def handle_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        
        # Сохраняем данные
        user_sessions[user_id] = {
            'player_hp': data.get('player_hp', 100),
            'monster_hp': data.get('monster_hp', 100)
        }
        
        await message.answer(
            f"⚔️ Результат боя:\n"
            f"❤️ Твое HP: {user_sessions[user_id]['player_hp']}\n"
            f"🐗 HP кабана: {user_sessions[user_id]['monster_hp']}"
        )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message(Command('stats'))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        s = user_sessions[user_id]
        await message.answer(
            f"📊 Твоя статистика:\n"
            f"❤️ Твое HP: {s['player_hp']}\n"
            f"🐗 HP кабана: {s['monster_hp']}"
        )
    else:
        await message.answer("Ты еще не начинал бой! Нажми /start")

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🚀 Бот запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
