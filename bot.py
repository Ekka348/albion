import os
from aiohttp import web

PORT = int(os.getenv('PORT', 8080))

async def handle_index(request):
    # Пробуем прочитать файл index.html
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return web.Response(text=content, content_type='text/html')
    except FileNotFoundError:
        return web.Response(text="index.html not found", status=404)
    except Exception as e:
        return web.Response(text=f"Server Error: {e}", status=500)

async def handle_health(request):
    return web.Response(text="OK", status=200)

app = web.Application()
app.router.add_get('/', handle_index)
app.router.add_get('/health', handle_health)

if __name__ == '__main__':
    web.run_app(app, port=PORT)
