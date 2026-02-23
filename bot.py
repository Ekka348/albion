import asyncio
import logging
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os

# Настройки из переменных окружения
API_TOKEN = os.getenv('BOT_TOKEN', '8404262144:AAFhLqVbU4FpIrM6KWfU6u9L1l5Qh-FYLWk')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'albion-production.up.railway.app')

# Инициализация
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# База данных в памяти
user_sessions = {}

# Сбрасываем вебхук при старте
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Вебхук сброшен, бот готов к работе")

@dp.startup()
async def startup_wrapper():
    await on_startup()

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    """Отправляем приветствие и кнопку с игрой"""
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🎮 Войти в Пустошь",
        web_app=types.WebAppInfo(url=WEBAPP_URL)
    ))
    
    await message.answer(
        "🔥 Добро пожаловать в Пустошь!\n\n"
        "Нажми кнопку ниже, чтобы начать бой с мутированным кабаном.\n\n"
        f"🔗 URL приложения: {WEBAPP_URL}",
        reply_markup=builder.as_markup()
    )

@dp.message(Command('help'))
async def cmd_help(message: types.Message):
    await message.answer(
        "📖 Команды:\n"
        "/start - начать игру\n"
        "/help - эта помощь\n"
        "/stats - статистика\n"
        "/reset - сбросить бой"
    )

@dp.message(Command('stats'))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        s = user_sessions[user_id]
        await message.answer(
            f"📊 Твоя статистика:\n"
            f"❤️ HP: {s['player_hp']}\n"
            f"🐗 Кабан: {s['monster_hp']}\n"
            f"📈 Уровень: {s['level']}"
        )
    else:
        await message.answer("Ты еще не начинал бой! Нажми /start")

@dp.message(Command('reset'))
async def cmd_reset(message: types.Message):
    user_id = message.from_user.id
    user_sessions[user_id] = {
        'player_hp': 100,
        'monster_hp': 80,
        'level': 1
    }
    await message.answer("⚡ Бой сброшен! Монстр возродился.")

@dp.message(lambda message: message.web_app_data)
async def handle_web_app_data(message: types.Message):
    """Получаем данные из Mini App"""
    
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        
        # Инициализируем сессию если новая
        if user_id not in user_sessions:
            user_sessions[user_id] = {
                'player_hp': 100,
                'monster_hp': 80,
                'level': 1
            }
        
        # Обновляем данные
        if 'monsterHp' in data:
            user_sessions[user_id]['monster_hp'] = data['monsterHp']
        if 'playerHp' in data:
            user_sessions[user_id]['player_hp'] = data['playerHp']
        
        # Отвечаем
        await message.answer(
            f"⚔️ Бой продолжается!\n"
            f"Твое HP: {user_sessions[user_id]['player_hp']}\n"
            f"HP кабана: {user_sessions[user_id]['monster_hp']}"
        )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🤖 Бот запускается...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
