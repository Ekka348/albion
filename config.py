import os
from datetime import timedelta

# Только токен бота
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()

# Проверка токена
if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN.startswith('ВАШ_'):
    raise ValueError("❌ TELEGRAM_BOT_TOKEN не установлен! Добавьте в переменные окружения.")

if not TELEGRAM_BOT_TOKEN.count(':') == 1:
    raise ValueError("❌ Неверный формат токена. Должен быть: '123456789:ABCdefGHIjklMNopqRSTuvwxyz'")

# Настройки мониторинга
CHECK_INTERVAL_MINUTES = 3
KILLS_LIMIT = 150
API_TIMEOUT = 15

# Ваши T7 красные зоны
ALL_T7_RED_ZONES = {
    "Murkweald (Red Zone)": "Forest",
    "Shiftshadow Expanse (Red Zone)": "Swamp",
    "Runnel Sink (Red Zone)": "Swamp",
    "Camlann (Red Zone)": "Highland",
    "Domhain Chasm (Red Zone)": "Highland"
}

# Соседние зоны
ZONE_NEIGHBORS = {
    "Murkweald (Red Zone)": [
        "Flimmerair Steppe (Red Zone)",
        "Wyre Forest (Red Zone)",
        "Highbole Glen (Red Zone)",
        "Goldshimmer Plain (Red Zone)"
    ],
    "Shiftshadow Expanse (Red Zone)": [
        "Astolat (Red Zone)",
        "Deadvein Gully (Red Zone)",
        "Flatriver Trough (Red Zone)",
        "Broken Fell (Red Zone)"
    ],
    "Runnel Sink (Red Zone)": [
        "Garrow Fell (Red Zone)",
        "Mardale (Red Zone)",
        "Stumprot Swamp (Red Zone)",
        "Bowscale Fell (Red Zone)"
    ],
    "Camlann (Red Zone)": [
        "Stumprot Swamp (Red Zone)",
        "Malag Crevasse (Red Zone)",
        "Dusktree Swamp (Red Zone)",
        "Anklesnag Mire (Red Zone)"
    ],
    "Domhain Chasm (Red Zone)": [
        "Creag Garr (Red Zone)",
        "Creag Meagir (Red Zone)",
        "Nightbloom Forest (Red Zone)"
    ]
}

# Настройки опасности
DANGER_THRESHOLDS = {
    "continue_farming": 1,
    "be_cautious": 2,
    "leave_zone": 3,
    "neighbor_danger": 2
}

KILL_WEIGHTS = {
    "same_zone": 3.0,
    "neighbor_zone": 1.5,
    "same_guild_multiple": 2.0
}

# Таймеры респауна
RESPAWN_TIMERS = {
    "Forest_T6": 85,
    "Forest_T7": 105,
    "Swamp_T6": 80,
    "Swamp_T7": 100,
    "Highland_T6": 90,
    "Highland_T7": 110
}

# Настройки кнопок
BUTTONS_CONFIG = {
    "main_menu": {
        "set_zone": "📍 Установить зону",
        "current_status": "📊 Текущий статус",
        "respawn_info": "⏰ Респаун ресурсов",
        "safe_spots": "🎯 Безопасные зоны"
    },
    "zone_buttons": {
        "Murkweald": "Murkweald (Red Zone)",
        "Shiftshadow": "Shiftshadow Expanse (Red Zone)",
        "Runnel": "Runnel Sink (Red Zone)",
        "Camlann": "Camlann (Red Zone)",
        "Domhain": "Domhain Chasm (Red Zone)"
    }
}

# URL API
MURDER_LEDGER_API = "https://murderledger.com/api/recent/kills"
