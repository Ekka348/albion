import asyncio
import logging
import random
import json
import os
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ============= НАСТРОЙКИ =============
API_TOKEN = os.getenv('BOT_TOKEN', '8404262144:AAFhLqVbU4FpIrM6KWfU6u9L1l5Qh-FYLWk')
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ============= КЛАССЫ =============

class Weapon:
    def __init__(self, name, damage, accuracy, crit_chance, crit_multiplier, ammo, reload_time):
        self.name = name
        self.damage = damage
        self.accuracy = accuracy
        self.crit_chance = crit_chance
        self.crit_multiplier = crit_multiplier
        self.ammo = ammo
        self.max_ammo = ammo
        self.reload_time = reload_time
        self.reload_progress = 0

class Enemy:
    def __init__(self, name, hp, damage, accuracy, defense, exp, loot_table, emoji):
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.damage = damage
        self.accuracy = accuracy
        self.defense = defense
        self.exp = exp
        self.loot_table = loot_table
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
        self.debuffs = []
        self.current_node = "start"
        self.visited_nodes = set()

class MapNode:
    def __init__(self, node_id, node_type, content=None, name=""):
        self.id = node_id
        self.node_type = node_type  # "start", "enemy", "elite", "boss", "chest", "altar", "empty"
        self.content = content
        self.name = name
        self.connections = []
        self.visited = False
        self.completed = False

# ============= ТИПЫ СОБЫТИЙ =============

ENEMY_TYPES = {
    "zombie": {
        "name": "🧟 Зомби",
        "hp": 45,
        "damage": (6, 12),
        "accuracy": 65,
        "defense": 2,
        "exp": 25,
        "emoji": "🧟",
        "difficulty": "normal"
    },
    "skeleton": {
        "name": "💀 Скелет",
        "hp": 35,
        "damage": (8, 14),
        "accuracy": 70,
        "defense": 3,
        "exp": 30,
        "emoji": "💀",
        "difficulty": "normal"
    },
    "ghost": {
        "name": "👻 Призрак",
        "hp": 25,
        "damage": (10, 18),
        "accuracy": 80,
        "defense": 1,
        "exp": 35,
        "emoji": "👻",
        "difficulty": "normal"
    },
    "elite_knight": {
        "name": "⚔️ Рыцарь-мертвец",
        "hp": 80,
        "damage": (12, 20),
        "accuracy": 75,
        "defense": 8,
        "exp": 60,
        "emoji": "⚔️",
        "difficulty": "elite"
    },
    "boss": {
        "name": "👹 Древний ужас",
        "hp": 150,
        "damage": (15, 30),
        "accuracy": 80,
        "defense": 10,
        "exp": 200,
        "emoji": "👹",
        "difficulty": "boss"
    }
}

ALTAR_EFFECTS = [
    {
        "name": "Алтарь силы",
        "description": "⚔️ Навсегда +5 к урону",
        "effect": "damage_up",
        "value": 5,
        "emoji": "⚔️"
    },
    {
        "name": "Алтарь здоровья",
        "description": "❤️ Навсегда +10 к макс. HP",
        "effect": "hp_up",
        "value": 10,
        "emoji": "❤️"
    },
    {
        "name": "Алтарь защиты",
        "description": "🛡️ Навсегда +3 к защите",
        "effect": "defense_up",
        "value": 3,
        "emoji": "🛡️"
    },
    {
        "name": "Алтарь удачи",
        "description": "🍀 +50 золота",
        "effect": "gold",
        "value": 50,
        "emoji": "🍀"
    }
]

CHEST_TYPES = {
    "common": {
        "name": "Обычный сундук",
        "emoji": "📦",
        "loot_table": "chest_common",
        "color": "🟫"
    },
    "rare": {
        "name": "Редкий сундук",
        "emoji": "📦✨",
        "loot_table": "chest_rare",
        "color": "🔵"
    },
    "epic": {
        "name": "Эпический сундук",
        "emoji": "📦🌟",
        "loot_table": "chest_epic",
        "color": "🟣"
    }
}

LOOT_TABLES = {
    "enemy_normal": [
        {"name": "Монеты", "value": 10, "emoji": "💰", "chance": 80, "min": 5, "max": 15},
        {"name": "Аптечка", "value": 15, "emoji": "💊", "chance": 40},
        {"name": "Ржавый меч", "value": 25, "emoji": "⚔️", "chance": 20}
    ],
    "enemy_elite": [
        {"name": "Золото", "value": 50, "emoji": "💰", "chance": 100, "min": 20, "max": 40},
        {"name": "Большая аптечка", "value": 30, "emoji": "💊", "chance": 80},
        {"name": "Драгоценный камень", "value": 100, "emoji": "💎", "chance": 50},
        {"name": "Магический посох", "value": 150, "emoji": "🪄", "chance": 30}
    ],
    "boss": [
        {"name": "Сундук с золотом", "value": 200, "emoji": "💰", "chance": 100, "min": 100, "max": 200},
        {"name": "Редкий самоцвет", "value": 300, "emoji": "💎", "chance": 80},
        {"name": "Легендарный артефакт", "value": 500, "emoji": "🏆", "chance": 50}
    ],
    "chest_common": [
        {"name": "Золото", "value": 30, "emoji": "💰", "chance": 90, "min": 10, "max": 30},
        {"name": "Аптечка", "value": 20, "emoji": "💊", "chance": 70},
        {"name": "Зелье лечения", "value": 40, "emoji": "🧪", "chance": 40}
    ],
    "chest_rare": [
        {"name": "Золото", "value": 60, "emoji": "💰", "chance": 100, "min": 30, "max": 60},
        {"name": "Большая аптечка", "value": 40, "emoji": "💊", "chance": 80},
        {"name": "Драгоценный камень", "value": 80, "emoji": "💎", "chance": 40}
    ],
    "chest_epic": [
        {"name": "Золото", "value": 120, "emoji": "💰", "chance": 100, "min": 60, "max": 120},
        {"name": "Легендарный меч", "value": 200, "emoji": "⚔️✨", "chance": 60},
        {"name": "Магический кристалл", "value": 150, "emoji": "🔮", "chance": 50}
    ]
}

# ============= МОЯ КАРТА "ЗАБЫТЫЙ ЛЕС" =============

def create_forgotten_forest():
    """Создает карту Забытый лес"""
    nodes = {}
    
    # Старт
    nodes["start"] = MapNode("start", "start", name="🪵 Вход в лес")
    
    # Первый ряд (начальные пути)
    nodes["node1"] = MapNode("node1", "enemy", "zombie", name="🧟 Поляна мертвецов")
    nodes["node2"] = MapNode("node2", "chest", "common", name="📦 Старый пень")
    nodes["node3"] = MapNode("node3", "empty", None, name="⬜ Тихая поляна")
    
    # Второй ряд (развилки)
    nodes["node4"] = MapNode("node4", "altar", 0, name="🕯️ Алтарь силы")
    nodes["node5"] = MapNode("node5", "enemy", "skeleton", name="💀 Кладбище")
    nodes["node6"] = MapNode("node6", "empty", None, name="⬜ Лесная тропа")
    nodes["node7"] = MapNode("node7", "enemy", "zombie", name="🧟 Заброшенная деревня")
    nodes["node8"] = MapNode("node8", "chest", "rare", name="📦✨ Дупло древнего дуба")
    
    # Третий ряд
    nodes["node9"] = MapNode("node9", "chest", "common", name="📦 Спрятанный тайник")
    nodes["node10"] = MapNode("node10", "enemy", "elite_knight", name="⚔️ Оскверненный храм")
    nodes["node11"] = MapNode("node11", "altar", 1, name="🕯️ Алтарь здоровья")
    nodes["node12"] = MapNode("node12", "chest", "common", name="📦 Корни дерева")
    nodes["node13"] = MapNode("node13", "altar", 2, name="🕯️ Алтарь защиты")
    nodes["node14"] = MapNode("node14", "enemy", "ghost", name="👻 Туманная долина")
    
    # Босс
    nodes["boss"] = MapNode("boss", "boss", "boss", name="👹 Логово древнего ужаса")
    
    # ===== СОЕДИНЕНИЯ (ПУТИ) =====
    
    # От старта
    nodes["start"].connections = ["node1", "node2", "node3"]
    
    # Первый ряд → второй
    nodes["node1"].connections = ["node4", "node5"]
    nodes["node2"].connections = ["node5", "node6"]
    nodes["node3"].connections = ["node7", "node8"]
    
    # Второй ряд → третий
    nodes["node4"].connections = ["node9", "node10"]
    nodes["node5"].connections = ["node10", "node11"]
    nodes["node6"].connections = ["node11", "node12"]
    nodes["node7"].connections = ["node12", "node13"]
    nodes["node8"].connections = ["node13", "node14"]
    
    # Третий ряд → босс (множество путей)
    nodes["node9"].connections = ["boss"]
    nodes["node10"].connections = ["boss"]
    nodes["node11"].connections = ["boss"]
    nodes["node12"].connections = ["boss"]
    nodes["node13"].connections = ["boss"]
    nodes["node14"].connections = ["boss"]
    
    # Старт посещен
    nodes["start"].visited = True
    
    return nodes

def format_forest_map(nodes, current_node_id):
    """Форматирует карту леса для отображения"""
    lines = []
    
    # Строка 0 (Старт)
    line0 = "                     🧍"
    lines.append(line0)
    
    # Соединительная линия
    line1 = "                    / | \\"
    lines.append(line1)
    
    # Строка 1 (первые узлы)
    line2 = "              "
    node1 = nodes.get("node1")
    node2 = nodes.get("node2")
    node3 = nodes.get("node3")
    
    # Узел 1
    if node1 and node1.visited:
        if "node1" == current_node_id:
            line2 += "🧍"
        elif node1.completed:
            line2 += "✅"
        else:
            line2 += "⚔️"
    else:
        line2 += "❓"
    line2 += "     "
    
    # Узел 2
    if node2 and node2.visited:
        if "node2" == current_node_id:
            line2 += "🧍"
        elif node2.completed:
            line2 += "✅"
        else:
            line2 += "📦"
    else:
        line2 += "❓"
    line2 += "     "
    
    # Узел 3
    if node3 and node3.visited:
        if "node3" == current_node_id:
            line2 += "🧍"
        elif node3.completed:
            line2 += "✅"
        else:
            line2 += "⬜"
    else:
        line2 += "❓"
    
    lines.append(line2)
    
    # Соединительные линии
    line3 = "                 / | \\    / | \\    / | \\"
    lines.append(line3)
    
    # Строка 2 (второй ряд)
    line4 = "            "
    node4 = nodes.get("node4")
    node5 = nodes.get("node5")
    node6 = nodes.get("node6")
    node7 = nodes.get("node7")
    node8 = nodes.get("node8")
    
    # Узел 4
    if node4 and node4.visited:
        if "node4" == current_node_id:
            line4 += "🧍"
        elif node4.completed:
            line4 += "✅"
        else:
            line4 += "🕯️"
    else:
        line4 += "❓"
    line4 += "   "
    
    # Узел 5
    if node5 and node5.visited:
        if "node5" == current_node_id:
            line4 += "🧍"
        elif node5.completed:
            line4 += "✅"
        else:
            line4 += "💀"
    else:
        line4 += "❓"
    line4 += "   "
    
    # Узел 6
    if node6 and node6.visited:
        if "node6" == current_node_id:
            line4 += "🧍"
        elif node6.completed:
            line4 += "✅"
        else:
            line4 += "⬜"
    else:
        line4 += "❓"
    line4 += "   "
    
    # Узел 7
    if node7 and node7.visited:
        if "node7" == current_node_id:
            line4 += "🧍"
        elif node7.completed:
            line4 += "✅"
        else:
            line4 += "🧟"
    else:
        line4 += "❓"
    line4 += "   "
    
    # Узел 8
    if node8 and node8.visited:
        if "node8" == current_node_id:
            line4 += "🧍"
        elif node8.completed:
            line4 += "✅"
        else:
            line4 += "📦✨"
    else:
        line4 += "❓"
    
    lines.append(line4)
    
    # Соединительные линии
    line5 = "               / | \\    / | \\    / | \\    / | \\    / | \\"
    lines.append(line5)
    
    # Строка 3 (третий ряд)
    line6 = "        "
    node9 = nodes.get("node9")
    node10 = nodes.get("node10")
    node11 = nodes.get("node11")
    node12 = nodes.get("node12")
    node13 = nodes.get("node13")
    node14 = nodes.get("node14")
    
    # Узел 9
    if node9 and node9.visited:
        if "node9" == current_node_id:
            line6 += "🧍"
        elif node9.completed:
            line6 += "✅"
        else:
            line6 += "📦"
    else:
        line6 += "❓"
    line6 += "   "
    
    # Узел 10
    if node10 and node10.visited:
        if "node10" == current_node_id:
            line6 += "🧍"
        elif node10.completed:
            line6 += "✅"
        else:
            line6 += "⚔️"
    else:
        line6 += "❓"
    line6 += "   "
    
    # Узел 11
    if node11 and node11.visited:
        if "node11" == current_node_id:
            line6 += "🧍"
        elif node11.completed:
            line6 += "✅"
        else:
            line6 += "🕯️"
    else:
        line6 += "❓"
    line6 += "   "
    
    # Узел 12
    if node12 and node12.visited:
        if "node12" == current_node_id:
            line6 += "🧍"
        elif node12.completed:
            line6 += "✅"
        else:
            line6 += "📦"
    else:
        line6 += "❓"
    line6 += "   "
    
    # Узел 13
    if node13 and node13.visited:
        if "node13" == current_node_id:
            line6 += "🧍"
        elif node13.completed:
            line6 += "✅"
        else:
            line6 += "🕯️"
    else:
        line6 += "❓"
    line6 += "   "
    
    # Узел 14
    if node14 and node14.visited:
        if "node14" == current_node_id:
            line6 += "🧍"
        elif node14.completed:
            line6 += "✅"
        else:
            line6 += "👻"
    else:
        line6 += "❓"
    
    lines.append(line6)
    
    # Соединительные линии к боссу
    line7 = "                     \\ | / | / | / | /"
    lines.append(line7)
    
    # Босс
    boss = nodes.get("boss")
    line8 = "                       "
    if boss and boss.visited:
        if "boss" == current_node_id:
            line8 += "🧍"
        elif boss.completed:
            line8 += "✅"
        else:
            line8 += "👹"
    else:
        line8 += "❓"
    
    lines.append(line8)
    
    return "\n".join(lines)

# ============= ФУНКЦИИ =============

def generate_loot(table_name):
    """Генерирует лут из таблицы"""
    table = LOOT_TABLES[table_name]
    loot = []
    total_value = 0
    
    for item in table:
        if random.randint(1, 100) <= item["chance"]:
            if "min" in item:
                amount = random.randint(item["min"], item.get("max", item["min"]))
                value = item["value"] * amount
                loot.append({
                    "name": item["name"],
                    "amount": amount,
                    "value": value,
                    "emoji": item["emoji"]
                })
                total_value += value
            else:
                loot.append({
                    "name": item["name"],
                    "amount": 1,
                    "value": item["value"],
                    "emoji": item["emoji"]
                })
                total_value += item["value"]
    
    return loot, total_value

# ============= ЭКРАН КАРТЫ =============

async def show_map(message: types.Message, state: FSMContext):
    """Показывает карту леса"""
    data = await state.get_data()
    
    if not data or 'forest_map' not in data:
        forest_map = create_forgotten_forest()
        player = Player()
        player.visited_nodes.add("start")
        await state.update_data(
            player=player,
            forest_map=forest_map
        )
    else:
        player = data['player']
        forest_map = data['forest_map']
    
    current_node = forest_map[player.current_node]
    current_node.visited = True
    player.visited_nodes.add(player.current_node)
    
    map_display = format_forest_map(forest_map, player.current_node)
    
    # Информация о текущем узле
    node_info = f"📍 **{current_node.name}**\n"
    
    if current_node.node_type == "start":
        node_info += "🚪 Начало твоего пути"
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
        node_info += f"🕯️ **{altar['name']}**\n{altar['description']}"
    elif current_node.node_type == "empty":
        node_info += "⬜ Здесь ничего нет"
    elif current_node.completed:
        node_info += "✅ Уже пройдено"
    
    # Доступные пути
    if current_node.connections:
        paths = []
        for conn_id in current_node.connections:
            if conn_id not in player.visited_nodes:
                paths.append(f"{conn_id} (❓)")
            else:
                paths.append(conn_id)
        node_info += f"\n\n🛤️ **Можно идти:** {', '.join(paths)}"
    
    # Статус игрока
    buffs_text = ""
    if player.buffs:
        buffs_text = "\n✨ Баффы: " + ", ".join(player.buffs)
    
    player_status = (
        f"👤 **{player.hp}/{player.max_hp} HP** | Ур. {player.level}\n"
        f"⚔️ Урон: базовый + {player.damage_bonus}\n"
        f"🛡️ Защита: {player.defense}\n"
        f"💰 {player.gold} золота | Аптечек: {player.inventory.get('аптечка', 0)}\n"
        f"✨ Опыт: {player.exp}/{player.level * 100}"
        f"{buffs_text}"
    )
    
    text = (
        f"🌲 **Забытый лес**\n"
        f"🧍 - ты | ❓ - скрыто | ✅ - пройдено\n\n"
        f"{map_display}\n\n"
        f"{node_info}\n\n"
        f"{player_status}"
    )
    
    # Кнопки
    buttons = []
    
    # Кнопка действия
    if current_node.node_type in ["enemy", "boss"] and not current_node.completed:
        buttons.append([InlineKeyboardButton(text="⚔️ Вступить в бой", callback_data="start_battle")])
    elif current_node.node_type == "chest" and not current_node.completed:
        buttons.append([InlineKeyboardButton(text="📦 Открыть сундук", callback_data="open_chest")])
    elif current_node.node_type == "altar" and not current_node.completed:
        buttons.append([InlineKeyboardButton(text="🕯️ Использовать алтарь", callback_data="use_altar")])
    
    # Кнопки перемещения
    for conn_id in current_node.connections:
        emoji = "❓" if conn_id not in player.visited_nodes else "➡️"
        buttons.append([
            InlineKeyboardButton(
                text=f"{emoji} Идти в {conn_id}", 
                callback_data=f"goto_node_{conn_id}"
            )
        ])
    
    # Кнопки меню
    buttons.append([
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="show_inventory"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await state.update_data(player=player, forest_map=forest_map)
    
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except:
        await message.answer(text, reply_markup=keyboard)

# ============= ПЕРЕМЕЩЕНИЕ =============

@dp.callback_query(lambda c: c.data.startswith('goto_node_'))
async def goto_node_callback(callback: types.CallbackQuery, state: FSMContext):
    node_id = callback.data.split('_')[2]
    data = await state.get_data()
    player = data['player']
    forest_map = data['forest_map']
    
    if node_id in forest_map[player.current_node].connections:
        player.current_node = node_id
        player.visited_nodes.add(node_id)
        forest_map[node_id].visited = True
    
    await state.update_data(player=player, forest_map=forest_map)
    await show_map(callback.message, state)
    await callback.answer()

# ============= БОЙ =============

@dp.callback_query(lambda c: c.data == "start_battle")
async def start_battle(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    forest_map = data['forest_map']
    
    current_node = forest_map[player.current_node]
    
    if current_node.node_type == "boss":
        enemy_data = ENEMY_TYPES["boss"]
        loot_table = "boss"
    elif current_node.content == "elite_knight":
        enemy_data = ENEMY_TYPES["elite_knight"]
        loot_table = "enemy_elite"
    else:
        enemy_data = ENEMY_TYPES[current_node.content]
        loot_table = "enemy_normal"
    
    battle_enemy = Enemy(
        enemy_data["name"],
        enemy_data["hp"],
        enemy_data["damage"],
        enemy_data["accuracy"],
        enemy_data["defense"],
        enemy_data["exp"],
        loot_table,
        enemy_data["emoji"]
    )
    
    weapon = Weapon("Деревянный меч", (5, 12), 75, 10, 2.0, 999, 0)
    
    await state.update_data(
        battle_enemy=battle_enemy,
        battle_weapon=weapon
    )
    
    await show_battle(callback.message, state)
    await callback.answer()

async def show_battle(message: types.Message, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    enemy = data['battle_enemy']
    weapon = data['battle_weapon']
    
    difficulty_prefix = ""
    if enemy.loot_table == "enemy_elite":
        difficulty_prefix = "⚔️ ЭЛИТНЫЙ "
    elif enemy.loot_table == "boss":
        difficulty_prefix = "👹 БОСС "
    
    # Урон с учетом баффов
    total_damage_bonus = player.damage_bonus
    
    text = (
        f"⚔️ **{difficulty_prefix}БОЙ!**\n\n"
        f"{enemy.emoji} **{enemy.name}**\n"
        f"❤️ HP: {enemy.hp}/{enemy.max_hp}\n\n"
        f"👤 **Ты**\n"
        f"❤️ {player.hp}/{player.max_hp} HP\n"
        f"🔪 {weapon.name} (базовый урон {weapon.damage[0]}-{weapon.damage[1]})\n"
        f"⚔️ Бонус урона: +{player.damage_bonus}\n\n"
        f"Твой ход:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔪 Атаковать", callback_data="battle_attack")],
        [InlineKeyboardButton(text="💊 Лечиться", callback_data="battle_heal")],
        [InlineKeyboardButton(text="🏃 Убежать", callback_data="battle_run")]
    ])
    
    await message.edit_text(text, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith('battle_'))
async def battle_callback(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split('_')[1]
    data = await state.get_data()
    
    player = data['player']
    enemy = data['battle_enemy']
    weapon = data['battle_weapon']
    forest_map = data.get('forest_map')
    
    result = []
    
    if action == "attack":
        # Атака с учетом баффов
        if random.randint(1, 100) <= weapon.accuracy:
            base_damage = random.randint(weapon.damage[0], weapon.damage[1])
            total_damage = base_damage + player.damage_bonus
            
            if random.randint(1, 100) <= weapon.crit_chance:
                total_damage = int(total_damage * 2.0)
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
        if player.inventory.get("аптечка", 0) > 0:
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
        if random.random() < 0.6:
            result.append("🏃 Ты сбежал!")
            await state.update_data(player=player)
            await show_map(callback.message, state)
            await callback.answer()
            return
        else:
            result.append("❌ Не удалось сбежать!")
            if random.randint(1, 100) <= enemy.accuracy:
                enemy_damage = random.randint(enemy.damage[0], enemy.damage[1])
                enemy_damage = max(1, enemy_damage - player.defense // 2)
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
        
        loot, gold = generate_loot(enemy.loot_table)
        player.gold += gold
        
        if forest_map:
            current_node = forest_map[player.current_node]
            current_node.completed = True
        
        loot_text = "\n".join([f"{item['emoji']} {item['name']} x{item['amount']}" for item in loot])
        
        await callback.message.edit_text(
            f"🎉 **ПОБЕДА!**\n\n" +
            "\n".join(result) +
            f"\n\n✨ Опыт: +{enemy.exp}\n"
            f"💰 Золото: +{gold}\n"
            f"🎒 Добыча:\n{loot_text}"
        )
        
        await state.update_data(player=player, forest_map=forest_map)
        await asyncio.sleep(3)
        await show_map(callback.message, state)
        await callback.answer()
        return
    
    if player.hp <= 0:
        await callback.message.edit_text("💀 **ТЫ ПОГИБ...**")
        await state.clear()
        await callback.answer()
        return
    
    await state.update_data(player=player, battle_enemy=enemy)
    
    text = (
        f"⚔️ **БОЙ!**\n\n"
        f"{enemy.emoji} **{enemy.name}**\n"
        f"❤️ HP: {enemy.hp}/{enemy.max_hp}\n\n"
        f"👤 **Ты**\n"
        f"❤️ {player.hp}/{player.max_hp} HP\n\n"
        f"**Последний ход:**\n" + "\n".join(result) +
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
async def open_chest_callback(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    forest_map = data['forest_map']
    
    current_node = forest_map[player.current_node]
    
    if current_node.node_type != "chest" or current_node.completed:
        await callback.answer("❌ Здесь нет сундука!")
        return
    
    chest = CHEST_TYPES[current_node.content]
    loot, gold = generate_loot(chest["loot_table"])
    player.gold += gold
    current_node.completed = True
    
    loot_text = []
    for item in loot:
        loot_text.append(f"{item['emoji']} {item['name']} x{item['amount']} - {item['value']}💰")
    
    await state.update_data(player=player, forest_map=forest_map)
    
    text = (
        f"{chest['emoji']} **{chest['name']} ОТКРЫТ!**\n\n"
        f"💰 Найдено золота: {gold}\n"
        f"🎒 Добыча:\n" + "\n".join(loot_text)
    )
    
    await callback.message.edit_text(text)
    await asyncio.sleep(3)
    await show_map(callback.message, state)
    await callback.answer()

# ============= АЛТАРИ =============

@dp.callback_query(lambda c: c.data == "use_altar")
async def use_altar_callback(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    forest_map = data['forest_map']
    
    current_node = forest_map[player.current_node]
    
    if current_node.node_type != "altar" or current_node.completed:
        await callback.answer("❌ Здесь нет алтаря!")
        return
    
    altar = ALTAR_EFFECTS[current_node.content]
    
    effect_text = ""
    if altar["effect"] == "damage_up":
        player.damage_bonus += 5
        player.buffs.append("⚔️ Сила +5")
        effect_text = "⚔️ Твоя сила увеличилась на 5!"
    elif altar["effect"] == "hp_up":
        player.max_hp += 10
        player.hp += 10
        player.buffs.append("❤️ Здоровье +10")
        effect_text = "❤️ Твое здоровье увеличилось на 10!"
    elif altar["effect"] == "defense_up":
        player.defense += 3
        player.buffs.append("🛡️ Защита +3")
        effect_text = "🛡️ Твоя защита увеличилась на 3!"
    elif altar["effect"] == "gold":
        player.gold += 50
        player.buffs.append("🍀 Удача")
        effect_text = "🍀 Ты нашел 50 золота!"
    
    current_node.completed = True
    
    await state.update_data(player=player, forest_map=forest_map)
    
    text = (
        f"🕯️ **{altar['name']}**\n\n"
        f"{altar['description']}\n\n"
        f"{effect_text}\n\n"
        f"❤️ HP: {player.hp}/{player.max_hp}"
    )
    
    await callback.message.edit_text(text)
    await asyncio.sleep(3)
    await show_map(callback.message, state)
    await callback.answer()

# ============= ИНВЕНТАРЬ И СТАТИСТИКА =============

@dp.callback_query(lambda c: c.data == "show_inventory")
async def show_inventory(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    
    inv_text = "\n".join([f"• {item}: {count}" for item, count in player.inventory.items()])
    
    text = (
        f"🎒 **ИНВЕНТАРЬ**\n\n"
        f"{inv_text if inv_text else 'Пусто'}\n\n"
        f"💰 Золото: {player.gold}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_map")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "show_stats")
async def show_stats(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    
    buffs_text = ""
    if player.buffs:
        buffs_text = "\n✨ Баффы: " + ", ".join(player.buffs)
    
    text = (
        f"📊 **СТАТИСТИКА**\n\n"
        f"👤 Уровень: {player.level}\n"
        f"✨ Опыт: {player.exp}/{player.level * 100}\n"
        f"❤️ HP: {player.hp}/{player.max_hp}\n"
        f"⚔️ Бонус урона: +{player.damage_bonus}\n"
        f"🛡️ Защита: {player.defense}\n"
        f"💰 Золото: {player.gold}"
        f"{buffs_text}"
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
    """Начало игры"""
    forest_map = create_forgotten_forest()
    player = Player()
    player.visited_nodes.add("start")
    await state.update_data(
        player=player,
        forest_map=forest_map
    )
    await show_map(message, state)

@dp.message(Command('ping'))
async def cmd_ping(message: types.Message):
    await message.answer("🏓 pong")

# ============= ЗАПУСК =============

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🌲 Забытый лес запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
