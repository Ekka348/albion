import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

API_TOKEN = os.getenv('BOT_TOKEN', '8404262144:AAFhLqVbU4FpIrM6KWfU6u9L1l5Qh-FYLWk')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@dp.message(Command('ping'))
async def cmd_ping(message: types.Message):
    print(f"✅ Получен ping от {message.from_user.id}")
    await message.answer("🏓 pong")

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    print(f"✅ Получен start от {message.from_user.id}")
    await message.answer("Привет! Я живой!")

async def main():
    print("🚀 Запуск бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
