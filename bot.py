import asyncio
import logging
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor

# Настройки
API_TOKEN = 'ТВОЙ_ТОКЕН_БОТА'  # Получи у @BotFather
WEBAPP_URL = 'https://твой-проект.railway.app'  # Сюда вставим URL позже

# Инициализация
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Логирование
logging.basicConfig(level=logging.INFO)

# База данных в памяти (потом заменим на нормальную)
user_sessions = {}

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    """Отправляем приветствие и кнопку с игрой"""
    
    # Кнопка для открытия Mini App
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton(
            "🎮 Войти в Пустошь",
            web_app=types.WebAppInfo(url=WEBAPP_URL)
        )
    )
    
    await message.answer(
        "🔥 Добро пожаловать в Пустошь!\n\n"
        "Нажми кнопку ниже, чтобы начать бой с мутированным кабаном.",
        reply_markup=keyboard
    )

@dp.message_handler(content_types=['web_app_data'])
async def handle_web_app_data(message: types.Message):
    """Получаем данные из Mini App"""
    
    try:
        # Данные приходят как JSON строка
        data = json.loads(message.web_app_data.data)
        
        user_id = message.from_user.id
        
        # Сохраняем состояние игрока
        if user_id not in user_sessions:
            user_sessions[user_id] = {
                'player_hp': 100,
                'monster_hp': 80,
                'level': 1
            }
        
        # Обновляем данные из игры
        if 'monsterHp' in data:
            user_sessions[user_id]['monster_hp'] = data['monsterHp']
        if 'playerHp' in data:
            user_sessions[user_id]['player_hp'] = data['playerHp']
        
        # Отвечаем в чат
        await message.answer(
            f"⚔️ Бой продолжается!\n"
            f"Твое HP: {user_sessions[user_id]['player_hp']}\n"
            f"HP кабана: {user_sessions[user_id]['monster_hp']}"
        )
        
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

@dp.message_handler(commands=['stats'])
async def cmd_stats(message: types.Message):
    """Показываем статистику игрока"""
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

@dp.message_handler(commands=['reset'])
async def cmd_reset(message: types.Message):
    """Сброс боя"""
    user_id = message.from_user.id
    if user_id in user_sessions:
        user_sessions[user_id] = {
            'player_hp': 100,
            'monster_hp': 80,
            'level': 1
        }
    await message.answer("Бой сброшен! Начинай заново.")

if __name__ == '__main__':
    # Запуск бота
    executor.start_polling(dp, skip_updates=True)