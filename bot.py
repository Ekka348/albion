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
PORT = int(os.getenv('PORT', 8080))

# Настройки (замени на свои!)
API_TOKEN = os.getenv('BOT_TOKEN', '8404262144:AAFhLqVbU4FpIrM6KWfU6u9L1l5Qh-FYLWk')
WEBAPP_URL = os.getenv('WEBAPP_URL', '<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Пустошь: Бой</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body {
            background: #1a1a1a;
            color: #fff;
            font-family: Arial;
            text-align: center;
            padding: 20px;
        }
        .monster {
            font-size: 100px;
            margin: 30px;
        }
        .hp-bar {
            width: 100%;
            height: 30px;
            background: #333;
            border-radius: 15px;
            margin: 20px 0;
        }
        .hp-fill {
            height: 100%;
            width: 80%;
            background: #ff4444;
            border-radius: 15px;
            line-height: 30px;
            color: white;
        }
        button {
            background: #ff6b00;
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 20px;
            border-radius: 30px;
            margin: 10px;
            cursor: pointer;
        }
        button:active {
            background: #ff4500;
        }
        .log {
            background: #333;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <h1>🐗 МУТИРОВАННЫЙ КАБАН</h1>
    <div class="hp-bar">
        <div class="hp-fill" id="monsterHpBar">80%</div>
    </div>
    <div class="monster">🐗</div>
    <button onclick="attack()">⚔️ АТАКОВАТЬ</button>
    <div class="log" id="log">Нажми атаку, чтобы начать бой!</div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        tg.ready();

        let monsterHp = 80;
        let playerHp = 100;
        const maxMonsterHp = 80;

        function updateDisplay() {
            const percent = (monsterHp / maxMonsterHp) * 100;
            document.getElementById('monsterHpBar').style.width = percent + '%';
            document.getElementById('monsterHpBar').innerText = Math.floor(percent) + '%';
        }

        function attack() {
            if (monsterHp <= 0) {
                document.getElementById('log').innerHTML = '💀 Монстр уже мертв! Начни новый бой.';
                return;
            }

            // Урон игрока
            const damage = Math.floor(Math.random() * 20) + 10;
            monsterHp -= damage;
            
            // Урон монстра
            const monsterDamage = Math.floor(Math.random() * 15) + 5;
            playerHp -= monsterDamage;

            // Лог
            const log = document.getElementById('log');
            log.innerHTML = `⚔️ Ты нанес ${damage} урона!<br>`;
            log.innerHTML += `🐗 Кабан ударил на ${monsterDamage}!<br>`;
            
            if (monsterHp <= 0) {
                log.innerHTML += '🎉 ПОБЕДА! Монстр повержен!';
                monsterHp = 0;
            } else if (playerHp <= 0) {
                log.innerHTML += '💀 Ты погиб...';
            } else {
                log.innerHTML += `❤️ Твое HP: ${playerHp}`;
            }

            updateDisplay();

            // Отправляем боту
            tg.sendData(JSON.stringify({
                monsterHp: monsterHp,
                playerHp: playerHp
            }));
        }

        updateDisplay();
    </script>
</body>
</html>')

print(f"🆔 Запуск инстанса: {INSTANCE_ID}")
print(f"🚀 Порт: {PORT}")
print(f"🤖 Токен: {API_TOKEN[:10]}...")
print(f"🌐 WebApp URL: {WEBAPP_URL}")

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

user_sessions = {}

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
    print(f"✅ HTTP сервер запущен на порту {PORT}")

# Команды бота
@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    print(f"🔥 /start от {message.from_user.id}")
    
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
            f"🐗 Кабан: {s['monster_hp']} HP"
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

