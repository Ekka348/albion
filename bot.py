import asyncio
import logging
import json
import os
import random
import string
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

# Уникальный ID
INSTANCE_ID = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
PORT = int(os.getenv('PORT', 8080))

# Настройки
API_TOKEN = os.getenv('BOT_TOKEN', '8404262144:AAFhLqVbU4FpIrM6KWfU6u9L1l5Qh-FYLWk')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://твой-проект.railway.app')

print(f"🆔 Запуск инстанса: {INSTANCE_ID}")
print(f"🚀 Порт: {PORT}")
print(f"🤖 Токен: {API_TOKEN[:10]}...")

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

user_sessions = {}

# HTTP сервер
async def handle_healthcheck(request):
    """Для healthcheck Railway"""
    return web.Response(text=f"OK {INSTANCE_ID}", status=200)

async def handle_info(request):
    """Информация о сервере"""
    return web.json_response({
        "instance_id": INSTANCE_ID,
        "status": "running",
        "bot": "active"
    })

async def run_http_server():
    app = web.Application()
    app.router.add_get('/', handle_healthcheck)
    app.router.add_get('/health', handle_healthcheck)
    app.router.add_get('/info', handle_info)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"✅ HTTP сервер запущен на порту {PORT}")

# Команды бота
@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user_sessions[user_id] = user_sessions.get(user_id, {
        'player_hp': 100,
        'monster_hp': 80,
        'level': 1
    })
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🎮 Войти в Пустошь",
        web_app=types.WebAppInfo(url=WEBAPP_URL)
    ))
    
    await message.answer(
        f"🔥 Добро пожаловать в Пустошь!\n"
        f"🆔 Инстанс: {INSTANCE_ID}\n\n"
        f"Нажми кнопку ниже, чтобы начать бой.",
        reply_markup=builder.as_markup()
    )

@dp.message(Command('ping'))
async def cmd_ping(message: types.Message):
    await message.answer(f"🏓 Pong! Инстанс: {INSTANCE_ID}")

@dp.message(Command('stats'))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        s = user_sessions[user_id]
        await message.answer(
            f"📊 Статистика (инстанс: {INSTANCE_ID}):\n"
            f"❤️ Ты: {s['player_hp']} HP\n"
            f"🐗 Кабан: {s['monster_hp']} HP\n"
            f"📈 Уровень: {s['level']}"
        )
    else:
        await message.answer("Нет данных. Напиши /start")

@dp.message(Command('reset'))
async def cmd_reset(message: types.Message):
    user_id = message.from_user.id
    user_sessions[user_id] = {
        'player_hp': 100,
        'monster_hp': 80,
        'level': 1
    }
    await message.answer(f"⚡ Бой сброшен! (инстанс: {INSTANCE_ID})")

@dp.message(lambda message: message.web_app_data)
async def handle_web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        user_id = message.from_user.id
        
        if user_id not in user_sessions:
            user_sessions[user_id] = {
                'player_hp': 100,
                'monster_hp': 80,
                'level': 1
            }
        
        if 'monsterHp' in data:
            user_sessions[user_id]['monster_hp'] = data['monsterHp']
        if 'playerHp' in data:
            user_sessions[user_id]['player_hp'] = data['playerHp']
        
        await message.answer(
            f"⚔️ Бой (инстанс: {INSTANCE_ID}):\n"
            f"Ты: {user_sessions[user_id]['player_hp']} HP\n"
            f"Кабан: {user_sessions[user_id]['monster_hp']} HP"
        )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Запускаем HTTP сервер
    await run_http_server()
    
    # Сбрасываем вебхук
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Вебхук сброшен")
    
    # Запускаем бота
    print(f"🤖 Запуск бота {INSTANCE_ID}...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Бот остановлен")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
