import asyncio
import logging
import random
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ============= НАСТРОЙКИ =============
API_TOKEN = os.getenv('BOT_TOKEN', '8404262144:AAFhLqVbU4FpIrM6KWfU6u9L1l5Qh-FYLWk')
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ============= КЛАССЫ =============

class Weapon:
    def __init__(self, name, damage, accuracy, crit_chance, crit_multiplier):
        self.name = name
        self.damage = damage
        self.accuracy = accuracy
        self.crit_chance = crit_chance
        self.crit_multiplier = crit_multiplier

class Enemy:
    def __init__(self, name, hp, damage, accuracy, defense, exp, emoji):
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.damage = damage
        self.accuracy = accuracy
        self.defense = defense
        self.exp = exp
        self.emoji = emoji

class Player:
    def __init__(self):
        self.hp = 100
        self.max_hp = 100
        self.defense = 5
        self.damage_bonus = 0
        self.exp = 0
        self.level = 1
        self.gold = 0
        self.inventory = {"аптечка": 3}
        self.buffs = []
        self.current_node = "start"
        self.visited_nodes = set()

class MapNode:
    def __init__(self, node_id, node_type, content=None, name="", x=0, y=0):
        self.id = node_id
        self.node_type = node_type  # "start", "enemy", "boss", "chest", "altar", "empty", "exit"
        self.content = content
        self.name = name
        self.x = x
        self.y = y
        self.connections = []  # список id узлов, в которые можно перейти
        self.visited = False
        self.completed = False

# ============= ТИПЫ СОБЫТИЙ =============

ENEMY_TYPES = {
    "zombie": {"name": "🧟 Зомби", "hp": 45, "damage": (6,12), "accuracy": 65, "defense": 2, "exp": 25, "emoji": "🧟"},
    "skeleton": {"name": "💀 Скелет", "hp": 35, "damage": (8,14), "accuracy": 70, "defense": 3, "exp": 30, "emoji": "💀"},
    "ghost": {"name": "👻 Призрак", "hp": 25, "damage": (10,18), "accuracy": 80, "defense": 1, "exp": 35, "emoji": "👻"},
    "elite": {"name": "⚔️ Рыцарь", "hp": 80, "damage": (12,20), "accuracy": 75, "defense": 8, "exp": 60, "emoji": "⚔️"},
    "boss": {"name": "👹 Древний ужас", "hp": 150, "damage": (15,30), "accuracy": 80, "defense": 10, "exp": 200, "emoji": "👹"}
}

ALTAR_EFFECTS = [
    {"name": "Алтарь силы", "desc": "⚔️ +5 к урону", "effect": "damage", "value": 5, "emoji": "⚔️"},
    {"name": "Алтарь здоровья", "desc": "❤️ +10 HP", "effect": "hp", "value": 10, "emoji": "❤️"},
    {"name": "Алтарь защиты", "desc": "🛡️ +3 к защите", "effect": "defense", "value": 3, "emoji": "🛡️"},
    {"name": "Алтарь золота", "desc": "💰 +50 золота", "effect": "gold", "value": 50, "emoji": "💰"}
]

CHEST_TYPES = {
    "common": {"name": "Обычный сундук", "emoji": "📦", "value": (10,30)},
    "rare": {"name": "Редкий сундук", "emoji": "📦✨", "value": (30,60)}
}

# ============= СОЗДАНИЕ КАРТЫ =============

def create_map():
    """Создает карту с прямыми линиями, скалами и проходом"""
    nodes = {}
    
    # Главный путь (горизонтальный)
    nodes["start"] = MapNode("start", "start", name="🧝 Старт", x=2, y=2)
    nodes["cross1"] = MapNode("cross1", "empty", name="⬜ Перекресток", x=4, y=2)
    nodes["enemy1"] = MapNode("enemy1", "enemy", "zombie", name="🧟 Зомби", x=6, y=2)
    nodes["altar1"] = MapNode("altar1", "altar", 0, name="🕯️ Алтарь силы", x=8, y=2)
    
    # Верхний тупик (сундук)
    nodes["chest_top"] = MapNode("chest_top", "chest", "rare", name="📦✨ Редкий сундук", x=4, y=0)
    
    # Средний тупик (враг)
    nodes["enemy2"] = MapNode("enemy2", "enemy", "skeleton", name="💀 Скелет", x=6, y=4)
    
    # Нижний тупик (сундук)
    nodes["chest_bottom"] = MapNode("chest_bottom", "chest", "common", name="📦 Обычный сундук", x=8, y=4)
    
    # Путь к боссу
    nodes["cross2"] = MapNode("cross2", "empty", name="⬜ Развилка", x=10, y=2)
    nodes["enemy3"] = MapNode("enemy3", "enemy", "elite", name="⚔️ Элитный рыцарь", x=12, y=2)
    nodes["boss"] = MapNode("boss", "boss", "boss", name="👹 БОСС", x=14, y=2)
    nodes["exit"] = MapNode("exit", "exit", name="🚪 Выход", x=16, y=2)
    
    # ===== СОЕДИНЕНИЯ (только вверх/вниз/влево/вправо) =====
    
    # Главный путь
    nodes["start"].connections = ["cross1"]
    nodes["cross1"].connections = ["start", "enemy1", "chest_top"]
    nodes["enemy1"].connections = ["cross1", "altar1", "enemy2"]
    nodes["altar1"].connections = ["enemy1", "cross2", "chest_bottom"]
    
    # Верхний тупик
    nodes["chest_top"].connections = ["cross1"]
    
    # Средний тупик
    nodes["enemy2"].connections = ["enemy1"]
    
    # Нижний тупик
    nodes["chest_bottom"].connections = ["altar1"]
    
    # Путь к боссу
    nodes["cross2"].connections = ["altar1", "enemy3"]
    nodes["enemy3"].connections = ["cross2", "boss"]
    nodes["boss"].connections = ["enemy3", "exit"]
    nodes["exit"].connections = ["boss"]
    
    # Старт посещен
    nodes["start"].visited = True
    
    return nodes

def format_map_with_borders(nodes, current_node_id):
    """Форматирует карту со скалами по краям"""
    lines = []
    
    # Верхняя граница из скал
    lines.append("⛰️" * 20)
    
    # Строка 0
    line0 = "⛰️" + " " * 18 + "⛰️"
    lines.append(line0)
    
    # Строка 1 (верхний тупик)
    line1 = "⛰️"
    for x in range(18):
        if x == 4:
            node = nodes.get("chest_top")
            if node:
                if "chest_top" == current_node_id:
                    line1 += "🧝"
                elif node.visited:
                    if node.completed:
                        line1 += "✅"
                    else:
                        line1 += "📦✨"
                else:
                    line1 += "❓"
            else:
                line1 += " "
        else:
            line1 += " "
    line1 += "⛰️"
    lines.append(line1)
    
    # Строка 2 (основной путь)
    line2 = "⛰️"
    for x in range(18):
        if x == 2:
            node = nodes.get("start")
            if "start" == current_node_id:
                line2 += "🧝"
            elif node and node.visited:
                line2 += "🚪"
            else:
                line2 += "❓"
        elif x == 3:
            line2 += "─"
        elif x == 4:
            node = nodes.get("cross1")
            if "cross1" == current_node_id:
                line2 += "🧝"
            elif node and node.visited:
                if node.completed:
                    line2 += "✅"
                else:
                    line2 += "⬜"
            else:
                line2 += "❓"
        elif x == 5:
            line2 += "─"
        elif x == 6:
            node = nodes.get("enemy1")
            if "enemy1" == current_node_id:
                line2 += "🧝"
            elif node and node.visited:
                if node.completed:
                    line2 += "✅"
                else:
                    line2 += "⚔️"
            else:
                line2 += "❓"
        elif x == 7:
            line2 += "─"
        elif x == 8:
            node = nodes.get("altar1")
            if "altar1" == current_node_id:
                line2 += "🧝"
            elif node and node.visited:
                if node.completed:
                    line2 += "✅"
                else:
                    line2 += "🕯️"
            else:
                line2 += "❓"
        elif x == 9:
            line2 += "─"
        elif x == 10:
            node = nodes.get("cross2")
            if "cross2" == current_node_id:
                line2 += "🧝"
            elif node and node.visited:
                if node.completed:
                    line2 += "✅"
                else:
                    line2 += "⬜"
            else:
                line2 += "❓"
        elif x == 11:
            line2 += "─"
        elif x == 12:
            node = nodes.get("enemy3")
            if "enemy3" == current_node_id:
                line2 += "🧝"
            elif node and node.visited:
                if node.completed:
                    line2 += "✅"
                else:
                    line2 += "⚔️✨"
            else:
                line2 += "❓"
        elif x == 13:
            line2 += "─"
        elif x == 14:
            node = nodes.get("boss")
            if "boss" == current_node_id:
                line2 += "🧝"
            elif node and node.visited:
                if node.completed:
                    line2 += "✅"
                else:
                    line2 += "👹"
            else:
                line2 += "❓"
        elif x == 15:
            line2 += "─"
        elif x == 16:
            node = nodes.get("exit")
            if "exit" == current_node_id:
                line2 += "🧝"
            elif node and node.visited:
                if node.completed:
                    line2 += "✅"
                else:
                    line2 += "🚪"
            else:
                line2 += "❓"
        else:
            line2 += " "
    line2 += "⛰️"
    lines.append(line2)
    
    # Вертикальные связи
    line_conn = "⛰️"
    for x in range(18):
        if x == 4:
            line_conn += "│"
        elif x == 6:
            line_conn += "│"
        elif x == 8:
            line_conn += "│"
        else:
            line_conn += " "
    line_conn += "⛰️"
    lines.append(line_conn)
    
    # Строка 3 (средний тупик - враг)
    line3 = "⛰️"
    for x in range(18):
        if x == 6:
            node = nodes.get("enemy2")
            if "enemy2" == current_node_id:
                line3 += "🧝"
            elif node and node.visited:
                if node.completed:
                    line3 += "✅"
                else:
                    line3 += "💀"
            else:
                line3 += "❓"
        else:
            line3 += " "
    line3 += "⛰️"
    lines.append(line3)
    
    # Еще вертикальные связи
    line_conn2 = "⛰️"
    for x in range(18):
        if x == 8:
            line_conn2 += "│"
        else:
            line_conn2 += " "
    line_conn2 += "⛰️"
    lines.append(line_conn2)
    
    # Строка 4 (нижний тупик - сундук)
    line4 = "⛰️"
    for x in range(18):
        if x == 8:
            node = nodes.get("chest_bottom")
            if "chest_bottom" == current_node_id:
                line4 += "🧝"
            elif node and node.visited:
                if node.completed:
                    line4 += "✅"
                else:
                    line4 += "📦"
            else:
                line4 += "❓"
        else:
            line4 += " "
    line4 += "⛰️"
    lines.append(line4)
    
    # Пустые строки
    for _ in range(3):
        lines.append("⛰️" + " " * 18 + "⛰️")
    
    # Нижняя граница
    lines.append("⛰️" * 20)
    
    return "\n".join(lines)

# ============= ФУНКЦИИ =============

def generate_loot(chest_type):
    """Генерирует лут из сундука"""
    if chest_type == "common":
        gold = random.randint(10, 30)
        items = []
        if random.random() < 0.5:
            items.append("аптечка")
        return gold, items
    else:
        gold = random.randint(30, 60)
        items = ["аптечка"]
        if random.random() < 0.3:
            items.append("зелье")
        return gold, items

# ============= ЭКРАН КАРТЫ =============

async def show_map(message: types.Message, state: FSMContext):
    """Показывает карту со скалами"""
    data = await state.get_data()
    
    if not data or 'map_nodes' not in data:
        map_nodes = create_map()
        player = Player()
        player.visited_nodes.add("start")
        await state.update_data(
            player=player,
            map_nodes=map_nodes
        )
    else:
        player = data['player']
        map_nodes = data['map_nodes']
    
    current_node = map_nodes[player.current_node]
    current_node.visited = True
    player.visited_nodes.add(player.current_node)
    
    map_display = format_map_with_borders(map_nodes, player.current_node)
    
    # Информация о текущем узле
    node_info = f"📍 **{current_node.name}**\n"
    
    if current_node.node_type == "start":
        node_info += "🚪 Начало пути"
    elif current_node.node_type == "exit":
        node_info += "🚪 Выход из локации (пока закрыт)"
    elif current_node.node_type == "enemy" and not current_node.completed:
        enemy = ENEMY_TYPES[current_node.content]
        node_info += f"👾 **{enemy['name']}**\n❤️ HP: {enemy['hp']}"
    elif current_node.node_type == "boss" and not current_node.completed:
        node_info += f"👹 **БОСС**\n❤️ HP: 150"
    elif current_node.node_type == "chest" and not current_node.completed:
        chest = CHEST_TYPES[current_node.content]
        node_info += f"{chest['emoji']} **{chest['name']}**"
    elif current_node.node_type == "altar" and not current_node.completed:
        altar = ALTAR_EFFECTS[current_node.content]
        node_info += f"🕯️ **{altar['name']}**\n{altar['desc']}"
    elif current_node.node_type == "empty":
        node_info += "⬜ Перекресток"
    elif current_node.completed:
        node_info += "✅ Уже пройдено"
    
    # Доступные пути
    if current_node.connections:
        paths = []
        for conn_id in current_node.connections:
            conn_node = map_nodes[conn_id]
            if conn_id not in player.visited_nodes:
                paths.append(f"{conn_node.name} (❓)")
            else:
                paths.append(conn_node.name)
        node_info += f"\n\n🛤️ **Можно идти:**"
        for p in paths:
            node_info += f"\n  • {p}"
    
    # Статус игрока
    buffs_text = ""
    if player.buffs:
        buffs_text = "\n✨ Баффы: " + ", ".join(player.buffs)
    
    player_status = (
        f"\n👤 **{player.hp}/{player.max_hp} HP** | Ур. {player.level}\n"
        f"⚔️ Бонус: +{player.damage_bonus} | 🛡️ Защита: {player.defense}\n"
        f"💰 {player.gold} золота | Аптечек: {player.inventory['аптечка']}\n"
        f"✨ Опыт: {player.exp}/{player.level * 100}"
        f"{buffs_text}"
    )
    
    text = f"{map_display}\n\n{node_info}{player_status}"
    
    # Кнопки
    buttons = []
    
    # Кнопка действия
    if not current_node.completed:
        if current_node.node_type in ["enemy", "boss"]:
            buttons.append([InlineKeyboardButton(text="⚔️ Вступить в бой", callback_data="start_battle")])
        elif current_node.node_type == "chest":
            buttons.append([InlineKeyboardButton(text="📦 Открыть сундук", callback_data="open_chest")])
        elif current_node.node_type == "altar":
            buttons.append([InlineKeyboardButton(text="🕯️ Использовать алтарь", callback_data="use_altar")])
        elif current_node.node_type == "exit":
            buttons.append([InlineKeyboardButton(text="🚪 Выйти", callback_data="exit_location")])
    
    # Кнопки перемещения
    for conn_id in current_node.connections:
        conn_node = map_nodes[conn_id]
        emoji = "❓" if conn_id not in player.visited_nodes else "➡️"
        
        # Определяем направление
        if conn_node.x < current_node.x:
            direction = "⬅️"
        elif conn_node.x > current_node.x:
            direction = "➡️"
        elif conn_node.y < current_node.y:
            direction = "⬆️"
        elif conn_node.y > current_node.y:
            direction = "⬇️"
        else:
            direction = "➡️"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"{direction} Идти в {conn_node.name}", 
                callback_data=f"goto_node_{conn_id}"
            )
        ])
    
    # Кнопки меню
    buttons.append([
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="show_inventory"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await state.update_data(player=player, map_nodes=map_nodes)
    
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except:
        await message.answer(text, reply_markup=keyboard)

# ============= ПЕРЕМЕЩЕНИЕ =============

@dp.callback_query(lambda c: c.data.startswith('goto_node_'))
async def goto_node(callback: types.CallbackQuery, state: FSMContext):
    node_id = callback.data.split('_')[2]
    data = await state.get_data()
    player = data['player']
    map_nodes = data['map_nodes']
    
    if node_id in map_nodes[player.current_node].connections:
        player.current_node = node_id
        player.visited_nodes.add(node_id)
        map_nodes[node_id].visited = True
    
    await state.update_data(player=player, map_nodes=map_nodes)
    await show_map(callback.message, state)
    await callback.answer()

# ============= БОЙ =============

@dp.callback_query(lambda c: c.data == "start_battle")
async def start_battle(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    map_nodes = data['map_nodes']
    
    current_node = map_nodes[player.current_node]
    
    if current_node.node_type == "boss":
        enemy_data = ENEMY_TYPES["boss"]
    else:
        enemy_data = ENEMY_TYPES[current_node.content]
    
    enemy = Enemy(
        enemy_data["name"],
        enemy_data["hp"],
        enemy_data["damage"],
        enemy_data["accuracy"],
        enemy_data["defense"],
        enemy_data["exp"],
        enemy_data["emoji"]
    )
    
    await state.update_data(battle_enemy=enemy)
    await show_battle(callback.message, state)
    await callback.answer()

async def show_battle(message: types.Message, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    enemy = data['battle_enemy']
    
    text = (
        f"⚔️ **БОЙ!**\n\n"
        f"{enemy.emoji} **{enemy.name}**\n"
        f"❤️ HP: {enemy.hp}/{enemy.max_hp}\n\n"
        f"👤 **Ты**\n"
        f"❤️ {player.hp}/{player.max_hp} HP\n"
        f"⚔️ Бонус: +{player.damage_bonus}\n\n"
        f"Твой ход:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔪 Атаковать", callback_data="battle_attack")],
        [InlineKeyboardButton(text="💊 Лечиться", callback_data="battle_heal")],
        [InlineKeyboardButton(text="🏃 Убежать", callback_data="battle_run")]
    ])
    
    await message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith('battle_'))
async def battle_action(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split('_')[1]
    data = await state.get_data()
    player = data['player']
    enemy = data['battle_enemy']
    map_nodes = data['map_nodes']
    
    result = []
    
    if action == "attack":
        # Атака игрока
        if random.randint(1, 100) <= 75:
            base_damage = random.randint(5, 12)
            total_damage = base_damage + player.damage_bonus
            
            if random.randint(1, 100) <= 10:
                total_damage = int(total_damage * 2)
                result.append(f"🔥 КРИТ! {total_damage} урона")
            else:
                result.append(f"⚔️ {total_damage} урона")
            enemy.hp -= total_damage
        else:
            result.append("😫 Промах!")
        
        # Ответ врага
        if enemy.hp > 0:
            if random.randint(1, 100) <= enemy.accuracy:
                enemy_damage = random.randint(enemy.damage[0], enemy.damage[1])
                enemy_damage = max(1, enemy_damage - player.defense // 2)
                player.hp -= enemy_damage
                result.append(f"💥 {enemy.name} атакует: {enemy_damage} урона")
            else:
                result.append(f"🙏 {enemy.name} промахнулся")
    
    elif action == "heal":
        if player.inventory["аптечка"] > 0:
            heal = random.randint(15, 25)
            player.hp = min(player.max_hp, player.hp + heal)
            player.inventory["аптечка"] -= 1
            result.append(f"💊 +{heal} HP")
            
            if random.randint(1, 100) <= enemy.accuracy:
                enemy_damage = random.randint(enemy.damage[0], enemy.damage[1])
                enemy_damage = max(1, enemy_damage - player.defense // 2)
                player.hp -= enemy_damage
                result.append(f"💥 {enemy.name} атакует: {enemy_damage} урона")
        else:
            result.append("❌ Нет аптечек!")
    
    elif action == "run":
        if random.random() < 0.5:
            result.append("🏃 Ты сбежал!")
            await state.update_data(player=player)
            await show_map(callback.message, state)
            await callback.answer()
            return
        else:
            result.append("❌ Не удалось сбежать!")
            if random.randint(1, 100) <= enemy.accuracy:
                enemy_damage = random.randint(enemy.damage[0], enemy.damage[1])
                player.hp -= enemy_damage
                result.append(f"💥 {enemy.name} атакует: {enemy_damage} урона")
    
    # Проверка победы
    if enemy.hp <= 0:
        player.exp += enemy.exp
        if player.exp >= player.level * 100:
            player.level += 1
            player.max_hp += 10
            player.hp = player.max_hp
            result.append(f"✨ **УРОВЕНЬ {player.level}!**")
        
        gold = random.randint(10, 30)
        player.gold += gold
        
        current_node = map_nodes[player.current_node]
        current_node.completed = True
        
        await callback.message.edit_text(
            f"🎉 **ПОБЕДА!**\n\n" +
            "\n".join(result) +
            f"\n\n✨ Опыт: +{enemy.exp}\n💰 Золото: +{gold}"
        )
        
        await state.update_data(player=player, map_nodes=map_nodes)
        await asyncio.sleep(2)
        await show_map(callback.message, state)
        await callback.answer()
        return
    
    if player.hp <= 0:
        await callback.message.edit_text("💀 **ТЫ ПОГИБ...**")
        await callback.answer()
        return
    
    await state.update_data(player=player, battle_enemy=enemy)
    
    text = (
        f"⚔️ **БОЙ!**\n\n"
        f"{enemy.emoji} **{enemy.name}**\n"
        f"❤️ HP: {enemy.hp}/{enemy.max_hp}\n\n"
        f"👤 **Ты**\n"
        f"❤️ {player.hp}/{player.max_hp} HP\n\n"
        f"**Ход:**\n" + "\n".join(result) +
        f"\n\nТвой ход:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔪 Атаковать", callback_data="battle_attack")],
        [InlineKeyboardButton(text="💊 Лечиться", callback_data="battle_heal")],
        [InlineKeyboardButton(text="🏃 Убежать", callback_data="battle_run")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

# ============= СУНДУКИ =============

@dp.callback_query(lambda c: c.data == "open_chest")
async def open_chest(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    map_nodes = data['map_nodes']
    
    current_node = map_nodes[player.current_node]
    
    if current_node.completed:
        await callback.answer("❌ Сундук уже открыт!")
        return
    
    gold, items = generate_loot(current_node.content)
    player.gold += gold
    
    for item in items:
        if item in player.inventory:
            player.inventory[item] += 1
        else:
            player.inventory[item] = 1
    
    current_node.completed = True
    
    items_text = ", ".join(items) if items else "ничего"
    await callback.message.edit_text(
        f"📦 **СУНДУК ОТКРЫТ!**\n\n"
        f"💰 Найдено: {gold} золота\n"
        f"🎒 Предметы: {items_text}"
    )
    
    await state.update_data(player=player, map_nodes=map_nodes)
    await asyncio.sleep(2)
    await show_map(callback.message, state)
    await callback.answer()

# ============= АЛТАРИ =============

@dp.callback_query(lambda c: c.data == "use_altar")
async def use_altar(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    map_nodes = data['map_nodes']
    
    current_node = map_nodes[player.current_node]
    altar = ALTAR_EFFECTS[current_node.content]
    
    if current_node.completed:
        await callback.answer("❌ Алтарь уже использован!")
        return
    
    effect_text = ""
    if altar["effect"] == "damage":
        player.damage_bonus += altar["value"]
        effect_text = f"⚔️ Твой урон увеличился на {altar['value']}!"
    elif altar["effect"] == "hp":
        player.max_hp += altar["value"]
        player.hp += altar["value"]
        effect_text = f"❤️ Твое здоровье увеличилось на {altar['value']}!"
    elif altar["effect"] == "defense":
        player.defense += altar["value"]
        effect_text = f"🛡️ Твоя защита увеличилась на {altar['value']}!"
    elif altar["effect"] == "gold":
        player.gold += altar["value"]
        effect_text = f"💰 Ты нашел {altar['value']} золота!"
    
    current_node.completed = True
    
    await callback.message.edit_text(
        f"🕯️ **{altar['name']}**\n\n"
        f"{effect_text}"
    )
    
    await state.update_data(player=player, map_nodes=map_nodes)
    await asyncio.sleep(2)
    await show_map(callback.message, state)
    await callback.answer()

# ============= ВЫХОД =============

@dp.callback_query(lambda c: c.data == "exit_location")
async def exit_location(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    map_nodes = data['map_nodes']
    
    current_node = map_nodes[player.current_node]
    
    if current_node.node_type != "exit":
        await callback.answer("❌ Здесь нет выхода!")
        return
    
    await callback.message.edit_text(
        "🚪 **ТЫ ВЫШЕЛ ИЗ ЛОКАЦИИ!**\n\n"
        "Поздравляю с завершением тестовой карты!\n\n"
        "Напиши /start чтобы начать заново."
    )
    await callback.answer()

# ============= ИНВЕНТАРЬ И СТАТИСТИКА =============

@dp.callback_query(lambda c: c.data == "show_inventory")
async def show_inventory(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    
    inv = "\n".join([f"• {item}: {count}" for item, count in player.inventory.items()])
    
    text = f"🎒 **ИНВЕНТАРЬ**\n\n{inv}\n\n💰 Золото: {player.gold}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_map")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "show_stats")
async def show_stats(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    
    buffs = ", ".join(player.buffs) if player.buffs else "нет"
    
    text = (
        f"📊 **СТАТИСТИКА**\n\n"
        f"👤 Уровень: {player.level}\n"
        f"✨ Опыт: {player.exp}/{player.level * 100}\n"
        f"❤️ HP: {player.hp}/{player.max_hp}\n"
        f"⚔️ Бонус урона: +{player.damage_bonus}\n"
        f"🛡️ Защита: {player.defense}\n"
        f"💰 Золото: {player.gold}\n"
        f"✨ Баффы: {buffs}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_map")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_map")
async def back_to_map(callback: types.CallbackQuery, state: FSMContext):
    await show_map(callback.message, state)
    await callback.answer()

# ============= СТАРТ =============

@dp.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    map_nodes = create_map()
    player = Player()
    player.visited_nodes.add("start")
    await state.update_data(
        player=player,
        map_nodes=map_nodes
    )
    await show_map(message, state)

@dp.message(Command('ping'))
async def cmd_ping(message: types.Message):
    await message.answer("🏓 pong")

# ============= ЗАПУСК =============

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🗺️ Карта со скалами запущена!")
    print("⛰️ Скалы обрамляют карту")
    print("🧝 Игрок-воин ходит по черточкам")
    print("🚪 Выход за боссом")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
