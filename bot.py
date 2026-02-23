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
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://albion-production.up.railway.app/')

print(f"🆔 Запуск инстанса: {INSTANCE_ID}")
print(f"🚀 Порт: {PORT}")
print(f"🤖 Токен: {API_TOKEN[:10]}...")

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

user_sessions = {}

# HTTP сервер
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
    print(f"✅ HTTP сервер запущен на порту {PORT}")

# Команды бота
@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🎮 Войти в Пустошь",
        web_app=types.WebAppInfo(url=WEBAPP_URL)
    ))
    
    await message.answer(
        f"🔥 Добро пожаловать в Пустошь!\n"
        f"🆔 Инстанс: {INSTANCE_ID}",
        reply_markup=builder.as_markup()
    )

@dp.message(Command('ping'))
async def cmd_ping(message: types.Message):
    await message.answer(f"🏓 Pong! Инстанс: {INSTANCE_ID}")

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Запускаем HTTP сервер отдельной задачей
    asyncio.create_task(run_http_server())
    
    # Сбрасываем вебхук
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Вебхук сброшен")
    
    # Запускаем бота
    print(f"🤖 Запуск бота {INSTANCE_ID}...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
