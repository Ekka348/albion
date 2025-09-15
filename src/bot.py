from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from config import Config
from database import db
from albion_api import albion_api
from datetime import datetime, timedelta
import asyncio
import re

class AlbionMonitorBot:
    def __init__(self):
        self.application = Application.builder().token(Config.TELEGRAM_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("setname", self.set_name_command))
        self.application.add_handler(CommandHandler("monitor", self.monitor_command))
        self.application.add_handler(CommandHandler("stop", self.stop_command))
        self.application.add_handler(CommandHandler("resource", self.resource_command))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        db.add_user(user_id)
        
        welcome_text = """
        🎮 Добро пожаловать в Albion Online Monitor Bot!
        
        Я помогу вам:
        • Следить за опасными игроками в вашей локации
        • Отслеживать респаун ресурсов
        • Получать уведомления о PvP активности
        
        Основные команды:
        /setname [Ваш ник] - Установить ваш игровой никнейм
        /monitor [Локация] - Начать мониторинг локации
        /stop - Остановить мониторинг
        /resource [тип] [уровень] - Добавить таймер ресурса
        /help - Показать справку
        """
        
        await update.message.reply_text(welcome_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
        📖 Справка по командам:
        
        /setname [Никнейм] - Установить ваш игровой ник
        Пример: /setname BestHarvester
        
        /monitor [Локация] - Начать мониторинг локации
        Пример: /monitor Deadspring T7
        
        /stop - Остановить мониторинг
        
        /resource [тип] [уровень] - Добавить таймер ресурса
        Пример: /resource ore 7
        
        Бот будет автоматически:
        • Предупреждать о опасных игроках
        • Сообщать о сборе ресурсов
        • Напоминать о респауне ресурсов
        """
        
        await update.message.reply_text(help_text)
    
    async def set_name_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажите ваш никнейм: /setname ВашНик")
            return
        
        user_id = update.effective_user.id
        albion_nickname = ' '.join(context.args)
        db.add_user(user_id, albion_nickname)
        
        await update.message.reply_text(f"✅ Никнейм установлен: {albion_nickname}")
    
    async def monitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Укажите локацию: /monitor НазваниеЛокации")
            return
        
        user_id = update.effective_user.id
        location = ' '.join(context.args)
        
        # Start monitoring session
        session_id = db.start_monitoring_session(user_id, location)
        
        await update.message.reply_text(
            f"✅ Начинаю мониторинг локации: {location}\n"
            f"📡 Бот будет проверять активность каждые {Config.MONITOR_INTERVAL} секунд"
        )
        
        # Start background monitoring task
        asyncio.create_task(self.monitor_location(session_id, user_id, location))
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        db.stop_monitoring_session(user_id)
        await update.message.reply_text("⏹️ Мониторинг остановлен")
    
    async def resource_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("❌ Используйте: /resource [тип] [уровень]\nПример: /resource ore 7")
            return
        
        user_id = update.effective_user.id
        resource_type = context.args[0].lower()
        resource_tier = context.args[1]
        
        # Get current monitoring location
        sessions = db.get_active_monitoring_sessions()
        user_session = next((s for s in sessions if s[1] == user_id), None)
        
        if not user_session:
            await update.message.reply_text("❌ Сначала запустите мониторинг локации: /monitor Локация")
            return
        
        location = user_session[2]
        harvested_at = datetime.now()
        respawn_minutes = Config.RESOURCE_RESPAWN_TIMES.get(f't{resource_tier}', 30)
        expected_respawn = harvested_at + timedelta(minutes=respawn_minutes)
        
        db.add_resource_timer(user_id, location, resource_type, resource_tier, harvested_at, expected_respawn)
        
        await update.message.reply_text(
            f"✅ Таймер ресурса добавлен:\n"
            f"📍 Локация: {location}\n"
            f"⛏️ Ресурс: {resource_type.upper()} T{resource_tier}\n"
            f"⏰ Ориентировочный респаун: {expected_respawn.strftime('%H:%M')}"
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        user_id = update.effective_user.id
        
        # Check if message looks like a location
        if re.match(r'.*[Tt][0-9].*', text) or re.match(r'.*[0-9].*', text):
            await update.message.reply_text(
                f"📍 Похоже на название локации!\n"
                f"Для мониторинга используйте: /monitor {text}"
            )
    
    async def monitor_location(self, session_id, user_id, location):
        """Background task to monitor location"""
        known_players = db.get_known_players(session_id)
        user_nickname = db.get_user_albion_nickname(user_id)
        
        while True:
            try:
                events = await albion_api.get_events(location)
                current_players = set()
                
                for event in events:
                    # Extract players from event
                    players = self.extract_players_from_event(event, user_nickname)
                    current_players.update(players)
                    
                    # Check for new players
                    new_players = current_players - known_players
                    
                    for player_name in new_players:
                        await self.check_and_alert_player(user_id, player_name, location, event)
                
                # Update known players
                known_players.update(current_players)
                db.update_known_players(session_id, known_players)
                
                # Check for resource events involving the user
                if user_nickname:
                    await self.check_user_resource_events(events, user_nickname, user_id, location)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
            
            await asyncio.sleep(Config.MONITOR_INTERVAL)
    
    def extract_players_from_event(self, event, user_nickname):
        """Extract player names from event, excluding the user"""
        players = set()
        
        # Check participants
        for participant in event.get('Participants', []):
            if participant.get('Name') and participant['Name'] != user_nickname:
                players.add(participant['Name'])
        
        # Check killer
        if event.get('Killer') and event['Killer'].get('Name') and event['Killer']['Name'] != user_nickname:
            players.add(event['Killer']['Name'])
        
        # Check victim
        if event.get('Victim') and event['Victim'].get('Name') and event['Victim']['Name'] != user_nickname:
            players.add(event['Victim']['Name'])
        
        return players
    
    async def check_and_alert_player(self, user_id, player_name, location, event):
        """Check player stats and send alert if dangerous"""
        try:
            # Search for player
            search_results = await albion_api.search_player(player_name)
            if not search_results:
                return
            
            player_id = search_results[0]['Id']
            player_info = await albion_api.get_player_info(player_id)
            
            if not player_info:
                return
            
            kill_count, recent_kills = await albion_api.get_player_kill_stats(player_id)
            kill_fame = player_info.get('KillFame', 0)
            
            # Cache player info
            db.cache_player_info(
                player_name, kill_fame, kill_count,
                player_info.get('GuildName'), player_info.get('AllianceName')
            )
            
            # Determine threat level
            threat_level = self.assess_threat_level(kill_fame, kill_count)
            
            if threat_level == 'high':
                message = (
                    f"🚨 ОПАСНОСТЬ В {location}!\n"
                    f"Игрок: {player_name}\n"
                    f"Убийств: {kill_count}\n"
                    f"PvP Слава: {kill_fame:,}\n"
                    f"Гильдия: {player_info.get('GuildName', 'Нет')}\n"
                    f"Будьте осторожны!"
                )
                await self.send_message(user_id, message)
            
            elif threat_level == 'medium':
                message = (
                    f"⚠️ Игрок в {location}\n"
                    f"Игрок: {player_name}\n"
                    f"Убийств: {kill_count}\n"
                    f"PvP Слава: {kill_fame:,}\n"
                    f"Рекомендуется проявить осторожность"
                )
                await self.send_message(user_id, message)
                
        except Exception as e:
            print(f"Error checking player: {e}")
    
    async def check_user_resource_events(self, events, user_nickname, user_id, location):
        """Check if user gathered resources"""
        for event in events:
            if not albion_api.is_resource_event(event):
                continue
            
            # Check if user is involved
            participants = [p.get('Name') for p in event.get('Participants', [])]
            killer = event.get('Killer', {}).get('Name')
            
            if user_nickname in participants or user_nickname == killer:
                victim_name = event.get('Victim', {}).get('Name', '')
                resource_info = self.parse_resource_name(victim_name)
                
                if resource_info:
                    resource_type, resource_tier = resource_info
                    harvested_at = datetime.now()
                    respawn_minutes = Config.RESOURCE_RESPAWN_TIMES.get(f't{resource_tier}', 30)
                    expected_respawn = harvested_at + timedelta(minutes=respawn_minutes)
                    
                    db.add_resource_timer(user_id, location, resource_type, resource_tier, harvested_at, expected_respawn)
                    
                    message = (
                        f"✅ Зафиксирован сбор ресурса!\n"
                        f"📍 Локация: {location}\n"
                        f"⛏️ Ресурс: {resource_type.upper()} T{resource_tier}\n"
                        f"⏰ Ориентировочный респаун: {expected_respawn.strftime('%H:%M')}"
                    )
                    await self.send_message(user_id, message)
    
    def parse_resource_name(self, victim_name):
        """Parse resource type and tier from victim name"""
        victim_name = victim_name.lower()
        
        resource_types = {
            'ore': 'ore',
            'rock': 'rock',
            'stone': 'rock',
            'wood': 'wood',
            'tree': 'wood',
            'fiber': 'fiber',
            'hide': 'hide',
            'skin': 'hide'
        }
        
        for keyword, resource_type in resource_types.items():
            if keyword in victim_name:
                # Extract tier (look for T4, T5, T6, T7, T8)
                tier_match = re.search(r't([0-9])', victim_name)
                tier = tier_match.group(1) if tier_match else '4'
                return resource_type, tier
        
        return None
    
    def assess_threat_level(self, kill_fame, kill_count):
        """Assess player threat level based on stats"""
        if kill_fame > 1000000 or kill_count > 10:
            return 'high'
        elif kill_fame > 100000 or kill_count > 3:
            return 'medium'
        return 'low'
    
    async def send_message(self, user_id, message):
        """Send message to user"""
        try:
            await self.application.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            print(f"Error sending message: {e}")
    
    async def check_resource_timers(self):
        """Background task to check resource timers"""
        while True:
            try:
                notifications = db.get_pending_resource_notifications()
                for notification in notifications:
                    user_id = notification[7]
                    message = (
                        f"⏰ Ресурс готов к сбору!\n"
                        f"📍 Локация: {notification[3]}\n"
                        f"⛏️ Ресурс: {notification[4].upper()} T{notification[5]}\n"
                        f"🕒 Пора проверять!"
                    )
                    await self.send_message(user_id, message)
                    db.mark_resource_notified(notification[0])
                
            except Exception as e:
                print(f"Resource timer error: {e}")
            
            await asyncio.sleep(Config.RESOURCE_CHECK_INTERVAL)
    
    def run(self):
        """Start the bot"""
        # Start resource timer checker
        asyncio.create_task(self.check_resource_timers())
        
        print("Bot started...")
        self.application.run_polling()

# Global bot instance
bot = AlbionMonitorBot()
