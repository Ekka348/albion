import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot Token
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    
    # Albion Online API settings
    ALBION_API_BASE = "https://gameinfo.albiononline.com/api/gameinfo"
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///albion_bot.db')
    
    # Monitoring intervals
    MONITOR_INTERVAL = 30  # seconds
    RESOURCE_CHECK_INTERVAL = 300  # seconds
    
    # Resource respawn times (minutes)
    RESOURCE_RESPAWN_TIMES = {
        't4': 15,
        't5': 20,
        't6': 25,
        't7': 30,
        't8': 35
    }
