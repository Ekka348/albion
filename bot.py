import asyncio
import json
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

# Настройки
API_TOKEN = os.getenv('BOT_TOKEN', '8404262144:AAFhLqVbU4FpIrM6KWfU6u9L1l5Qh-FYLWk')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://albion-production.up.railway.app')
PORT = int(os.getenv('PORT', 8080))

print(f"🆔 Запуск с портом {PORT}")
print(f"🌐 Mini App URL: {WEBAPP_URL}")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

user_sessions = {}

# ---------- HTTP сервер для Mini App ----------
async def handle_index(request):
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return web.Response(text=content, content_type='text/html')
    except FileNotFoundError:
        return web.Response(text="<h1>index.html не найден</h1>", content_type='text/html', status=404)

async def handle_health(request):
    return web.Response(text="OK", status=200)

async def run_http_server():
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_get('/health', handle_health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"✅ HTTP сервер запущен на порту {PORT}")

# ---------- Команды бота ----------
@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🐗 БИТЬ КАБАНА",
        web_app=types.WebAppInfo(url=WEBAPP_URL)
    ))
    
    await message.answer(
        "🔥 Нажимай кнопку и бей кабана!",
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
        
        user_sessions[user_id] = {
            'player_hp': data.get('player_hp', 100),
            'monster_hp': data.get('monster_hp', 100)
        }
        
        await message.answer(
            f"⚔️ Результат:\n"
            f"❤️ Ты: {user_sessions[user_id]['player_hp']} HP\n"
            f"🐗 Кабан: {user_sessions[user_id]['monster_hp']} HP"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

# ---------- Запуск ----------
async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Запускаем HTTP сервер
    await run_http_server()
    
    # Запускаем бота
    print("🚀 Запуск бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
