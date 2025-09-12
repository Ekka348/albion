import os
import asyncio
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, MessageHandler, filters
)
import aiohttp
import pytz

import config

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class AlbionGathererBot:
    def __init__(self):
        self.application = None
        self.current_zone = None
        self.last_clear_time = None
        self.last_danger_level = None
        self.respawn_timers = {}
        self.last_processed_kills = set()
        self.is_monitoring = False
        self.monitoring_task = None

    async def initialize(self):
        """Инициализация бота"""
        self.application = (
            Application.builder()
            .token(config.TELEGRAM_BOT_TOKEN)
            .build()
        )
        self.setup_handlers()
        
    def setup_handlers(self):
        """Настройка обработчиков"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("menu", self.show_main_menu))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_button_click))
        
        # Обработчик текстовых сообщений для установки зоны
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        await self.show_main_menu(update, context)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        if not self.current_zone:
            await update.message.reply_text("❌ Сначала установите зону через меню")
            return
        
        status = await self.get_zone_status()
        await update.message.reply_text(status, parse_mode='Markdown')

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает главное меню"""
        keyboard = [
            [InlineKeyboardButton(config.BUTTONS_CONFIG["main_menu"]["set_zone"], callback_data="set_zone")],
            [InlineKeyboardButton(config.BUTTONS_CONFIG["main_menu"]["current_status"], callback_data="current_status")],
            [InlineKeyboardButton(config.BUTTONS_CONFIG["main_menu"]["respawn_info"], callback_data="respawn_info")],
            [InlineKeyboardButton(config.BUTTONS_CONFIG["main_menu"]["safe_spots"], callback_data="safe_spots")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(
                "🎮 **Главное меню Albion Gatherer Guard**\n\nВыберите действие:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.callback_query.edit_message_text(
                "🎮 **Главное меню Albion Gatherer Guard**\n\nВыберите действие:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    async def show_zone_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает меню выбора зоны"""
        keyboard = []
        for zone_key, zone_name in config.BUTTONS_CONFIG["zone_buttons"].items():
            keyboard.append([InlineKeyboardButton(zone_name, callback_data=f"zone_{zone_key}")])
        
        keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="back_to_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            "📍 **Выберите вашу текущую зону:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def show_zone_actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает меню действий для зоны"""
        keyboard = [
            [InlineKeyboardButton("✅ Зона очищена", callback_data="zone_cleared")],
            [InlineKeyboardButton("⚠️ Проверить опасность", callback_data="check_danger")],
            [InlineKeyboardButton("⏰ Статус респауна", callback_data="check_respawn")],
            [InlineKeyboardButton("↩️ На главную", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            f"📍 **Текущая зона: {self.current_zone}**\n\nВыберите действие:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий кнопок"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        try:
            if data == "set_zone":
                await self.show_zone_menu(update, context)
                
            elif data.startswith("zone_"):
                zone_key = data.split("_")[1]
                self.current_zone = config.BUTTONS_CONFIG["zone_buttons"][zone_key]
                await self.show_zone_actions(update, context)
                
            elif data == "current_status":
                status = await self.get_zone_status()
                await query.edit_message_text(status, parse_mode='Markdown')
                
            elif data == "zone_cleared":
                await self.handle_zone_cleared(update, context)
                
            elif data == "check_danger":
                danger_info = await self.check_current_danger()
                await query.edit_message_text(danger_info, parse_mode='Markdown')
                
            elif data == "check_respawn":
                respawn_info = await self.get_respawn_info()
                await query.edit_message_text(respawn_info, parse_mode='Markdown')
                
            elif data == "safe_spots":
                safe_spots = await self.find_safe_spots()
                await query.edit_message_text(safe_spots, parse_mode='Markdown')
                
            elif data == "back_to_main":
                await self.show_main_menu(update, context)
                
        except Exception as e:
            logger.error(f"Error handling button click: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте снова.")

    async def handle_zone_cleared(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик очистки зоны"""
        self.last_clear_time = datetime.now(pytz.UTC)
        biome = config.ALL_T7_RED_ZONES.get(self.current_zone, "")
        
        if biome:
            t7_respawn_minutes = config.RESPAWN_TIMERS.get(f"{biome}_T7", 90)
            respawn_time = self.last_clear_time + timedelta(minutes=t7_respawn_minutes)
            
            self.respawn_timers = {
                'clear_time': self.last_clear_time,
                'zone': self.current_zone,
                'biome': biome,
                'T7_respawn': respawn_time
            }
            
            message = (
                f"✅ **{self.current_zone} очищена!**\n\n"
                f"⏰ T7 респаун: {respawn_time.strftime('%H:%M MSK')}\n"
                f"📊 Биом: {biome}\n\n"
                f"Бот будет отслеживать опасность автоматически."
            )
        else:
            message = "✅ Время очистки зафиксировано, но биом не определен"
        
        await update.callback_query.edit_message_text(message, parse_mode='Markdown')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        text = update.message.text.strip()
        
        if text.lower() in ['мурквеалд', 'murkweald']:
            self.current_zone = "Murkweald (Red Zone)"
        elif text.lower() in ['шифтшадоу', 'shiftshadow']:
            self.current_zone = "Shiftshadow Expanse (Red Zone)"
        elif text.lower() in ['руннел', 'runnel']:
            self.current_zone = "Runnel Sink (Red Zone)"
        elif text.lower() in ['камланн', 'camlann']:
            self.current_zone = "Camlann (Red Zone)"
        elif text.lower() in ['домхайн', 'domhain']:
            self.current_zone = "Domhain Chasm (Red Zone)"
            
        if self.current_zone:
            await update.message.reply_text(
                f"📍 Зона установлена: {self.current_zone}\n"
                f"Используйте /menu для управления"
            )
        else:
            await update.message.reply_text(
                "Используйте /menu для выбора зоны или напишите её название"
            )

    async def get_recent_kills(self) -> List[Dict]:
        """Получает последние убийства"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    config.MURDER_LEDGER_API, 
                    params={'limit': config.KILLS_LIMIT},
                    timeout=aiohttp.ClientTimeout(total=config.API_TIMEOUT)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('kills', [])
                    else:
                        logger.error(f"API error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error fetching kills: {e}")
            return []

    async def calculate_danger_level(self, kills_data: List[Dict]) -> Tuple[str, float, List[str]]:
        """Вычисляет уровень опасности"""
        if not self.current_zone:
            return "UNKNOWN", 0, []
            
        danger_score = 0
        details = []
        
        # Анализ вашей зоны
        your_zone_kills = [k for k in kills_data if k.get('location') == self.current_zone]
        if your_zone_kills:
            danger_score += len(your_zone_kills) * config.KILL_WEIGHTS["same_zone"]
            details.append(f"• {len(your_zone_kills)} убийств в вашей зоне")
        
        # Анализ соседних зон
        neighbor_zones = config.ZONE_NEIGHBORS.get(self.current_zone, [])
        for neighbor in neighbor_zones:
            neighbor_kills = [k for k in kills_data if k.get('location') == neighbor]
            if neighbor_kills:
                danger_score += len(neighbor_kills) * config.KILL_WEIGHTS["neighbor_zone"]
                details.append(f"• {len(neighbor_kills)} убийств в {neighbor}")
        
        # Определение уровня опасности
        if danger_score >= config.DANGER_THRESHOLDS["leave_zone"]:
            return "LEAVE", danger_score, details
        elif danger_score >= config.DANGER_THRESHOLDS["be_cautious"]:
            return "CAUTIOUS", danger_score, details
        else:
            return "SAFE", danger_score, details

    async def get_zone_status(self) -> str:
        """Возвращает статус зоны"""
        if not self.current_zone:
            return "❌ Зона не установлена. Используйте /menu"
            
        kills = await self.get_recent_kills()
        danger_level, score, details = await self.calculate_danger_level(kills)
        
        status_messages = {
            "LEAVE": "🚨 ОПАСНО - УХОДИТЕ!",
            "CAUTIOUS": "⚠️ ОСТОРОЖНО - БУДЬТЕ ГОТОВЫ",
            "SAFE": "🟢 БЕЗОПАСНО - МОЖНО ФАРМИТЬ",
            "UNKNOWN": "❓ НЕИЗВЕСТНО"
        }
        
        message = (
            f"📍 **Статус: {self.current_zone}**\n"
            f"**{status_messages[danger_level]}**\n\n"
        )
        
        if details:
            message += "**Детали:**\n" + "\n".join(details) + "\n\n"
        
        # Добавляем рекомендацию
        if danger_level == "LEAVE":
            message += "🚨 **Немедленно уходите из зоны!**"
        elif danger_level == "CAUTIOUS":
            message += "⚠️ **Будьте осторожны, не отходите далеко от выхода**"
        else:
            message += "🟢 **Можно спокойно фармить**"
            
        return message

    async def check_current_danger(self) -> str:
        """Проверяет текущую опасность"""
        kills = await self.get_recent_kills()
        danger_level, score, details = await self.calculate_danger_level(kills)
        
        return await self.get_zone_status()

    async def get_respawn_info(self) -> str:
        """Информация о респауне"""
        if not self.respawn_timers or self.respawn_timers.get('zone') != self.current_zone:
            return "❌ Нет данных о времени очистки этой зоны"
            
        now = datetime.now(pytz.UTC)
        t7_respawn = self.respawn_timers['T7_respawn']
        time_left = t7_respawn - now
        
        if time_left.total_seconds() <= 0:
            status = "🟢 T7 ресурсы должны были появиться"
        else:
            hours = time_left.seconds // 3600
            minutes = (time_left.seconds % 3600) // 60
            status = f"🟡 T7 респаун через: {hours}ч {minutes}м"
        
        return (
            f"⏰ **Респаун ресурсов**\n"
            f"📍 {self.current_zone}\n"
            f"📊 {self.respawn_timers['biome']}\n\n"
            f"{status}\n"
            f"🕒 Время респауна: {t7_respawn.strftime('%H:%M MSK')}"
        )

    async def find_safe_spots(self) -> str:
        """Находит безопасные зоны"""
        kills = await self.get_recent_kills()
        safe_zones = []
        
        for zone in config.ALL_T7_RED_ZONES.keys():
            zone_kills = [k for k in kills if k.get('location') == zone]
            if len(zone_kills) == 0:
                safe_zones.append(zone)
        
        if safe_zones:
            message = "🎯 **Безопасные зоны для фарма:**\n\n" + "\n".join(f"• {zone}" for zone in safe_zones[:3])
        else:
            message = "❌ Нет полностью безопасных зон. Рекомендуется подождать."
            
        return message

    async def monitoring_job(self):
        """Фоновая задача мониторинга"""
        while self.is_monitoring:
            try:
                if not self.current_zone:
                    await asyncio.sleep(config.CHECK_INTERVAL_MINUTES * 60)
                    continue
                    
                kills = await self.get_recent_kills()
                danger_level, score, details = await self.calculate_danger_level(kills)
                
                # Отправляем оповещение при изменении уровня опасности
                if self.last_danger_level != danger_level:
                    status = await self.get_zone_status()
                    await self.send_alert(status)
                    self.last_danger_level = danger_level
                    
                await asyncio.sleep(config.CHECK_INTERVAL_MINUTES * 60)
                
            except Exception as e:
                logger.error(f"Monitoring job error: {e}")
                await asyncio.sleep(60)  # Пауза при ошибке

    async def send_alert(self, message: str):
        """Отправляет оповещение"""
        try:
            await self.application.bot.send_message(
                chat_id=config.TELEGRAM_CHAT_ID,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error sending alert: {e}")

    async def start_monitoring(self):
        """Запускает мониторинг"""
        self.is_monitoring = True
        logger.info("Monitoring started")
        await self.monitoring_job()

    async def stop_monitoring(self):
        """Останавливает мониторинг"""
        self.is_monitoring = False
        logger.info("Monitoring stopped")

    async def run(self):
        """Запускает бота"""
        await self.initialize()
        logger.info("Bot is starting...")
        
        # Запускаем мониторинг в фоне
        self.monitoring_task = asyncio.create_task(self.start_monitoring())
        
        try:
            await self.application.run_polling()
        except asyncio.CancelledError:
            logger.info("Bot stopped")
        finally:
            await self.stop_monitoring()
            if self.monitoring_task:
                self.monitoring_task.cancel()

async def main():
    """Основная функция"""
    bot = AlbionGathererBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
