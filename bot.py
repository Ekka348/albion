import asyncio
import logging
import os
import random
import string
from aiohttp import web

# Уникальный ID
INSTANCE_ID = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
PORT = int(os.getenv('PORT', 8080))

# HTTP сервер
async def handle_healthcheck(request):
    return web.Response(text=f"OK Instance: {INSTANCE_ID}", status=200)

async def handle_info(request):
    return web.json_response({
        "instance_id": INSTANCE_ID,
        "status": "running",
        "port": PORT
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
    print(f"✅ HTTP сервер запущен на порту {PORT} (Instance: {INSTANCE_ID})")
    
    # Держим сервер запущенным
    await asyncio.Event().wait()

async def main():
    logging.basicConfig(level=logging.INFO)
    print(f"🆔 Запуск инстанса: {INSTANCE_ID}")
    print(f"🚀 Запуск HTTP сервера на порту {PORT}...")
    
    await run_http_server()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Сервер остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
