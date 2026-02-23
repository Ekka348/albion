import asyncio
import os
import random
import string
from aiohttp import web

# Уникальный ID
INSTANCE_ID = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
PORT = int(os.getenv('PORT', 8080))

print(f"🆔 Запуск инстанса: {INSTANCE_ID}")
print(f"🚀 Порт: {PORT}")

# HTTP сервер
async def handle(request):
    return web.Response(text=f"OK {INSTANCE_ID}", status=200)

async def main():
    app = web.Application()
    app.router.add_get('/', handle)
    app.router.add_get('/health', handle)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    
    print(f"✅ HTTP сервер запущен на порту {PORT}")
    
    # Держим сервер запущенным
    await asyncio.Event().wait()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Ошибка: {e}")
