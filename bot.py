import asyncio
import logging
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os
from aiohttp import web

# Настройки
API_TOKEN = os.getenv('BOT_TOKEN', '8404262144:AAFhLqVbU4FpIrM6KWfU6u9L1l5Qh-FYLWk')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://твой-проект.railway.app')
PORT = int(os.getenv('PORT', 8080))

# Инициализация
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

user_sessions = {}

# Жесткий сброс ВСЕГО
async def on_startup():
    # Сбрасываем вебхук и удаляем все ожидающие обновления
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Вебхук сброшен")
    
    # Дополнительно: получаем информацию о вебхуке для проверки
    webhook_info = await bot.get_webhook_info()
    print(f"📊 Инфо вебхука: {webhook_info}")
    
    # Закрываем все сессии (на всякий случай)
    await bot.session.close()
    print("✅ Сессии закрыты")

@dp.startup()
async def startup_wrapper():
    await on_startup()

# HTTP сервер
async def handle_healthcheck(request):
    return web.Response(text="OK", status=200)

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
        "🔥 Добро пожаловать в Пустошь!\n\n"
        "Нажми кнопку ниже, чтобы начать бой.\n\n"
        f"🔗 URL: {WEBAPP_URL}",
        reply_markup=builder.as_markup()
    )

@dp.message(Command('help'))
async def cmd_help(message: types.Message):
    await message.answer(
        "📖 Команды:\n"
        "/start - начать игру\n"
        "/help - помощь\n"
        "/stats - статистика\n"
        "/reset - сброс боя"
    )

@dp.message(Command('stats'))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_sessions:
        s = user_sessions[user_id]
        await message.answer(
            f"📊 Статистика:\n"
            f"❤️ Ты: {s['player_hp']} HP\n"
            f"🐗 Кабан: {s['monster_hp']} HP\n"
            f"📈 Уровень: {s['level']}"
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
    await message.answer("⚡ Бой сброшен!")

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
            f"⚔️ Бой:\n"
            f"Ты: {user_sessions[user_id]['player_hp']} HP\n"
            f"Кабан: {user_sessions[user_id]['monster_hp']} HP"
        )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Запускаем HTTP
    asyncio.create_task(run_http_server())
    
    print("🤖 Запуск бота...")
    
    # Пробуем запустить polling
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Ошибка polling: {e}")
        # Если ошибка - пробуем еще раз с задержкой
        await asyncio.sleep(5)
        await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
