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

print(f"🆔 Запуск Endless Path")
print(f"🌐 Mini App URL: {WEBAPP_URL}")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ----- HTTP сервер для отдачи файлов -----
async def handle_index(request):
    """Главная страница меню"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return web.Response(text=content, content_type='text/html')
    except FileNotFoundError:
        return web.Response(text="<h1>index.html не найден</h1>", content_type='text/html', status=404)
    except Exception as e:
        return web.Response(text=f"<h1>Ошибка: {e}</h1>", content_type='text/html', status=500)

async def handle_game(request):
    """Страница игры"""
    try:
        with open('game.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return web.Response(text=content, content_type='text/html')
    except FileNotFoundError:
        # Если game.html нет, показываем заглушку
        return web.Response(text="""
            <!DOCTYPE html>
            <html>
            <head><title>Игра</title></head>
            <body style="background:#1a1a2e; color:white; text-align:center; padding:50px;">
                <h1>⚔️ Игра загружается ⚔️</h1>
                <p>Скоро здесь будет бой с кабаном!</p>
                <button onclick="window.location.href='/'" style="padding:15px 30px; background:#ff6b00; color:white; border:none; border-radius:10px;">В меню</button>
            </body>
            </html>
        """, content_type='text/html')

async def handle_assets(request):
    """Отдача картинок из папки assets"""
    filename = request.match_info['filename']
    file_path = os.path.join('assets', filename)
    
    print(f"📸 Запрос картинки: {filename}")
    print(f"📁 Путь: {file_path}")
    print(f"📂 Существует? {os.path.exists(file_path)}")
    
    try:
        if not os.path.exists(file_path):
            print(f"❌ Файл не найден: {file_path}")
            return web.Response(status=404)
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Определяем тип файла
        if filename.endswith(('.jpg', '.jpeg')):
            content_type = 'image/jpeg'
        elif filename.endswith('.png'):
            content_type = 'image/png'
        else:
            content_type = 'application/octet-stream'
        
        print(f"✅ Отдаю {filename}, размер: {len(content)} байт")
        return web.Response(body=content, content_type=content_type)
    
    except Exception as e:
        print(f"❌ Ошибка при отдаче {filename}: {e}")
        return web.Response(status=500)

async def handle_health(request):
    return web.Response(text="OK", status=200)

async def run_http_server():
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_get('/game', handle_game)
    app.router.add_get('/assets/{filename}', handle_assets)
    app.router.add_get('/health', handle_health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"✅ HTTP сервер запущен на порту {PORT}")

# ----- Команды бота -----
@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🌟 Войти в Endless Path",
        web_app=types.WebAppInfo(url=WEBAPP_URL)
    ))
    
    await message.answer(
        "🌟 **Endless Path**\n\n"
        "Пустошь ждет своего героя. Готов ли ты вступить на бесконечный путь?\n\n"
        "👇 Нажми кнопку ниже, чтобы начать",
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
        
        if data.get('action') == 'start_game':
            await message.answer("⚔️ Удачи в бою!")
        
        await message.answer(f"⚔️ Данные получены")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

async def main():
    logging.basicConfig(level=logging.INFO)
    
    await run_http_server()
    
    print("🚀 Запуск бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
