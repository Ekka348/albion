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

# Уникальный ID инстанса
INSTANCE_ID = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
print(f"🆔 Запуск инстанса: {INSTANCE_ID}")

# Настройки
API_TOKEN = os.getenv('BOT_TOKEN', '8404262144:AAFhLqVbU4FpIrM6KWfU6u9L1l5Qh-FYLWk')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://твой-проект.railway.app')
PORT = int(os.getenv('PORT', 8080))

# Инициализация
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

user_sessions = {}

# Принудительный сброс при старте
async def on_startup():
    print("🔄 Сброс вебхука...")
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Вебхук сброшен")
    
    # Проверяем подключения
    webhook_info = await bot.get_webhook_info()
    print(f"📊 Инфо вебхука: {webhook_info}")

@dp.startup()
async def startup_wrapper():
    await on_startup()

# HTTP сервер для healthcheck
async def handle_healthcheck(request):
    return web.Response(text=f"OK {INSTANCE_ID}", status=200)

async def run_http_server():
    app = web.Application()
    app.router.add_get('/', handle_healthcheck)
    app.router.add_get('/health', handle_healthcheck)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"✅ HTTP сервер на порту {PORT}")

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
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

@dp.message(Command('help'))
async def cmd_help(message: types.Message):
    await message.answer("Команды: /start, /help, /stats, /reset")

@dp.message(Command('stats'))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        s = user_sessions[user_id]
        await message.answer(
            f"📊 Статистика (инстанс: {INSTANCE_ID}):\n"
            f"❤️ Ты: {s['player_hp']} HP\n"
            f"🐗 Кабан: {s['monster_hp']} HP"
        )
    else:
        await message.answer("Нет данных. Начни бой через /start")

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
            user_sessions[user_id] = {'player_hp': 100, 'monster_hp': 80, 'level': 1}
        
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
    
    # Запускаем HTTP
    asyncio.create_task(run_http_server())
    
    print(f"🤖 Запуск бота {INSTANCE_ID}...")
    
    # Запускаем с обработкой ошибок
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await asyncio.sleep(5)
        await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Бот остановлен")
