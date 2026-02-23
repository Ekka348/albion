import os
from aiohttp import web

PORT = int(os.getenv('PORT', 8080))

async def handle(request):
    return web.Response(text="OK", status=200)

app = web.Application()
app.router.add_get('/', handle)
app.router.add_get('/health', handle)

if __name__ == '__main__':
    web.run_app(app, port=PORT)
