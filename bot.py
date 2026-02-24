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

# Настройки
API_TOKEN = os.getenv('BOT_TOKEN', '8404262144:AAFhLqVbU4FpIrM6KWfU6u9L1l5Qh-FYLWk')
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ============= КЛАССЫ =============

class Weapon:
    def __init__(self, name, damage, accuracy, crit_chance, crit_multiplier, ammo, reload_time, aoe=False):
        self.name = name
        self.damage = damage
        self.accuracy = accuracy
        self.crit_chance = crit_chance
        self.crit_multiplier = crit_multiplier
        self.ammo = ammo
        self.max_ammo = ammo
        self.reload_time = reload_time
        self.reload_progress = 0
        self.aoe = aoe

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
        self.exp = 0
        self.level = 1
        self.gold = 0
        self.inventory = {"аптечка": 3}
        self.buffs = []
        self.debuffs = []
        self.current_location = "test_map"
        self.current_node = "start"
        self.map = None

class MapNode:
    def __init__(self, node_id, node_type, content=None, x=0, y=0):
        self.id = node_id
        self.node_type = node_type
        self.content = content
        self.connections = []
        self.visited = False
        self.completed = False
        self.x = x
        self.y = y

# ============= ТИПЫ СОБЫТИЙ =============

ENEMY_TYPES = {
    "zombie": {
        "name": "🧟 Зомби",
        "hp": 45,
        "damage": (6, 12),
        "accuracy": 65,
        "defense": 2,
        "exp": 25,
        "emoji": "🧟"
    },
    "skeleton": {
        "name": "💀 Скелет",
        "hp": 35,
        "damage": (8, 14),
        "accuracy": 70,
        "defense": 3,
        "exp": 30,
        "emoji": "💀"
    },
    "elite_knight": {
        "name": "⚔️ Рыцарь-мертвец",
        "hp": 80,
        "damage": (12, 20),
        "accuracy": 75,
        "defense": 8,
        "exp": 60,
        "emoji": "⚔️"
    },
    "boss": {
        "name": "👹 Древний ужас",
        "hp": 150,
        "damage": (15, 30),
        "accuracy": 80,
        "defense": 10,
        "exp": 200,
        "emoji": "👹"
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
    }
]

CHEST_TYPES = {
    "common": {
        "name": "Обычный сундук",
        "emoji": "📦",
        "loot_table": "chest_common"
    },
    "rare": {
        "name": "Редкий сундук",
        "emoji": "📦✨",
        "loot_table": "chest_rare"
    }
}

LOOT_TABLES = {
    "enemy_normal": [
        {"name": "Монеты", "value": 10, "emoji": "💰", "chance": 80, "min": 5, "max": 15},
        {"name": "Аптечка", "value": 15, "emoji": "💊", "chance": 40}
    ],
    "enemy_elite": [
        {"name": "Золото", "value": 50, "emoji": "💰", "chance": 100, "min": 20, "max": 40},
        {"name": "Большая аптечка", "value": 30, "emoji": "💊", "chance": 80}
    ],
    "boss": [
        {"name": "Сундук с золотом", "value": 200, "emoji": "💰", "chance": 100, "min": 100, "max": 200},
        {"name": "Легендарный артефакт", "value": 500, "emoji": "🏆", "chance": 50}
    ],
    "chest_common": [
        {"name": "Золото", "value": 30, "emoji": "💰", "chance": 90, "min": 10, "max": 30},
        {"name": "Аптечка", "value": 20, "emoji": "💊", "chance": 70}
    ],
    "chest_rare": [
        {"name": "Золото", "value": 60, "emoji": "💰", "chance": 100, "min": 30, "max": 60},
        {"name": "Драгоценный камень", "value": 80, "emoji": "💎", "chance": 40}
    ]
}

# ============= ТЕСТОВАЯ КАРТА =============

def create_test_map():
    """Создает тестовую карту по вашему рисунку"""
    nodes = {}
    
    # Создаем узлы с координатами для визуализации
    nodes["start"] = MapNode("start", "start", x=0, y=2)
    
    # Верхняя ветка
    nodes["node1"] = MapNode("node1", "enemy", "skeleton", x=2, y=0)
    nodes["node2"] = MapNode("node2", "altar", 0, x=4, y=0)  # Алтарь силы
    nodes["node3"] = MapNode("node3", "chest", "common", x=6, y=0)
    
    # Средняя ветка (основная)
    nodes["node4"] = MapNode("node4", "empty", None, x=2, y=2)
    nodes["node5"] = MapNode("node5", "enemy", "zombie", x=4, y=2)
    nodes["node6"] = MapNode("node6", "chest", "rare", x=6, y=2)
    nodes["node7"] = MapNode("node7", "empty", None, x=8, y=2)
    
    # Нижняя ветка
    nodes["node8"] = MapNode("node8", "chest", "common", x=2, y=4)
    nodes["node9"] = MapNode("node9", "enemy", "elite_knight", x=4, y=4)
    nodes["node10"] = MapNode("node10", "enemy", "zombie", x=6, y=4)
    nodes["node11"] = MapNode("node11", "chest", "common", x=8, y=4)
    
    # Еще нижняя ветка
    nodes["node12"] = MapNode("node12", "altar", 1, x=6, y=6)  # Алтарь здоровья
    nodes["boss"] = MapNode("boss", "boss", "boss", x=8, y=6)
    
    # Соединения (пути)
    # От старта
    nodes["start"].connections = ["node1", "node4", "node8"]
    
    # Верхняя ветка
    nodes["node1"].connections = ["node2"]
    nodes["node2"].connections = ["node3"]
    
    # Средняя ветка
    nodes["node4"].connections = ["node5"]
    nodes["node5"].connections = ["node6"]
    nodes["node6"].connections = ["node7"]
    
    # Нижняя ветка
    nodes["node8"].connections = ["node9"]
    nodes["node9"].connections = ["node10", "node12"]  # Развилка
    nodes["node10"].connections = ["node11"]
    
    # Путь к боссу
    nodes["node12"].connections = ["boss"]
    
    # Стартовый узел посещен
    nodes["start"].visited = True
    
    return nodes

def format_test_map(nodes, current_node_id):
    """Форматирует тестовую карту для отображения"""
    lines = []
    
    # Верхняя строка
    line1 = "         "
    if "node1" in nodes and nodes["node1"].visited:
        if nodes["node1"].id == current_node_id:
            line1 += "🧍"
        elif nodes["node1"].completed:
            line1 += "✅"
        else:
            line1 += "⚔️"
    else:
        line1 += "❓"
    line1 += "-------"
    
    if "node2" in nodes and nodes["node2"].visited:
        if nodes["node2"].id == current_node_id:
            line1 += "🧍"
        elif nodes["node2"].completed:
            line1 += "✅"
        else:
            line1 += "🕯️"
    else:
        line1 += "❓"
    line1 += "----"
    
    if "node3" in nodes and nodes["node3"].visited:
        if nodes["node3"].id == current_node_id:
            line1 += "🧍"
        elif nodes["node3"].completed:
            line1 += "✅"
        else:
            line1 += "📦"
    else:
        line1 += "❓"
    
    lines.append(line1)
    
    # Вертикальные линии
    lines.append("           |                          |")
    
    # Средняя строка (основная)
    line3 = ""
    if "start" in nodes and nodes["start"].visited:
        if nodes["start"].id == current_node_id:
            line3 += "🧍"
        else:
            line3 += "🚪"
    else:
        line3 += "❓"
    line3 += "╌╌"
    
    if "node4" in nodes and nodes["node4"].visited:
        if nodes["node4"].id == current_node_id:
            line3 += "🧍"
        elif nodes["node4"].completed:
            line3 += "✅"
        else:
            line3 += "⬜"
    else:
        line3 += "❓"
    line3 += "------"
    
    if "node5" in nodes and nodes["node5"].visited:
        if nodes["node5"].id == current_node_id:
            line3 += "🧍"
        elif nodes["node5"].completed:
            line3 += "✅"
        else:
            line3 += "🧟"
    else:
        line3 += "❓"
    line3 += "-----"
    
    if "node6" in nodes and nodes["node6"].visited:
        if nodes["node6"].id == current_node_id:
            line3 += "🧍"
        elif nodes["node6"].completed:
            line3 += "✅"
        else:
            line3 += "📦✨"
    else:
        line3 += "❓"
    line3 += "-------"
    
    if "node7" in nodes and nodes["node7"].visited:
        if nodes["node7"].id == current_node_id:
            line3 += "🧍"
        elif nodes["node7"].completed:
            line3 += "✅"
        else:
            line3 += "⬜"
    else:
        line3 += "❓"
    
    lines.append(line3)
    
    # Вертикальные линии
    lines.append("           |                         |                           |")
    
    # Нижняя строка
    line5 = "         "
    if "node8" in nodes and nodes["node8"].visited:
        if nodes["node8"].id == current_node_id:
            line5 += "🧍"
        elif nodes["node8"].completed:
            line5 += "✅"
        else:
            line5 += "📦"
    else:
        line5 += "❓"
    line5 += " -------- "
    
    if "node9" in nodes and nodes["node9"].visited:
        if nodes["node9"].id == current_node_id:
            line5 += "🧍"
        elif nodes["node9"].completed:
            line5 += "✅"
        else:
            line5 += "⚔️"
    else:
        line5 += "❓"
    line5 += "------ ------"
    
    if "node10" in nodes and nodes["node10"].visited:
        if nodes["node10"].id == current_node_id:
            line5 += "🧍"
        elif nodes["node10"].completed:
            line5 += "✅"
        else:
            line5 += "🧟"
    else:
        line5 += "❓"
    line5 += "----"
    
    if "node11" in nodes and nodes["node11"].visited:
        if nodes["node11"].id == current_node_id:
            line5 += "🧍"
        elif nodes["node11"].completed:
            line5 += "✅"
        else:
            line5 += "📦"
    else:
        line5 += "❓"
    
    lines.append(line5)
    
    # Вертикальные линии к боссу
    lines.append("                                          |                       |")
    
    # Строка с алтарем и боссом
    line7 = "                                           "
    if "node12" in nodes and nodes["node12"].visited:
        if nodes["node12"].id == current_node_id:
            line7 += "🧍"
        elif nodes["node12"].completed:
            line7 += "✅"
        else:
            line7 += "🕯️"
    else:
        line7 += "❓"
    line7 += "----- "
    
    if "boss" in nodes and nodes["boss"].visited:
        if nodes["boss"].id == current_node_id:
            line7 += "🧍"
        elif nodes["boss"].completed:
            line7 += "✅"
        else:
            line7 += "👹"
    else:
        line7 += "❓"
    
    lines.append(line7)
    
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
    """Показывает тестовую карту"""
    data = await state.get_data()
    
    if not data or 'test_map' not in data:
        # Создаем тестовую карту
        test_map = create_test_map()
        player = Player()
        player.map = test_map
        player.current_node = "start"
        await state.update_data(
            player=player,
            test_map=test_map
        )
    else:
        player = data['player']
        test_map = data['test_map']
    
    current_node = test_map[player.current_node]
    current_node.visited = True
    
    # Отображаем карту
    map_display = format_test_map(test_map, player.current_node)
    
    # Информация о текущем узле
    node_info = f"📍 **Узел: {player.current_node}**\n"
    
    if current_node.node_type == "start":
        node_info += "🚪 **Стартовая точка**"
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
        node_info += "⬜ **Пустой узел**"
    elif current_node.completed:
        node_info += "✅ **Пройдено**"
    
    # Доступные пути
    if current_node.connections:
        paths = ", ".join(current_node.connections)
        node_info += f"\n\n🛤️ **Доступно:** {paths}"
    
    # Статус игрока
    buffs_text = ""
    if player.buffs:
        buffs_text = "\n✨ Баффы: " + ", ".join(player.buffs)
    
    debuffs_text = ""
    if player.debuffs:
        debuffs_text = "\n💢 Дебаффы: " + ", ".join(player.debuffs)
    
    player_status = (
        f"👤 **{player.hp}/{player.max_hp} HP** | Ур. {player.level}\n"
        f"💰 {player.gold} золота | Аптечек: {player.inventory.get('аптечка', 0)}\n"
        f"✨ Опыт: {player.exp}/{player.level * 100}"
        f"{buffs_text}{debuffs_text}"
    )
    
    text = (
        f"🗺️ **Тестовая карта**\n"
        f"🧍 - ты | ❓ - не разведано | ✅ - пройдено\n\n"
        f"{map_display}\n\n"
        f"{node_info}\n\n"
        f"{player_status}"
    )
    
    # Кнопки
    buttons = []
    
    # Кнопка действия в зависимости от узла
    if current_node.node_type in ["enemy", "boss"] and not current_node.completed:
        buttons.append([InlineKeyboardButton(text="⚔️ Вступить в бой", callback_data="start_battle")])
    elif current_node.node_type == "chest" and not current_node.completed:
        buttons.append([InlineKeyboardButton(text="📦 Открыть сундук", callback_data="open_chest")])
    elif current_node.node_type == "altar" and not current_node.completed:
        buttons.append([InlineKeyboardButton(text="🕯️ Использовать алтарь", callback_data="use_altar")])
    
    # Кнопки для перехода в следующие узлы
    for conn_id in current_node.connections:
        buttons.append([
            InlineKeyboardButton(
                text=f"➡️ Идти в {conn_id}", 
                callback_data=f"goto_node_{conn_id}"
            )
        ])
    
    # Кнопки меню
    buttons.append([
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="show_inventory"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await state.update_data(player=player, test_map=test_map)
    
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
    test_map = data['test_map']
    
    # Проверяем, доступен ли этот узел
    if node_id in test_map[player.current_node].connections:
        player.current_node = node_id
        test_map[node_id].visited = True
    
    await state.update_data(player=player, test_map=test_map)
    await show_map(callback.message, state)
    await callback.answer()

# ============= БОЙ =============

@dp.callback_query(lambda c: c.data == "start_battle")
async def start_battle(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    test_map = data['test_map']
    
    current_node = test_map[player.current_node]
    
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
    
    weapon = Weapon("Кинжал", (5, 12), 75, 10, 2.0, 999, 0)
    
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
    
    text = (
        f"⚔️ **БОЙ!**\n\n"
        f"{enemy.emoji} **{enemy.name}**\n"
        f"❤️ HP: {enemy.hp}/{enemy.max_hp}\n\n"
        f"👤 **Ты**\n"
        f"❤️ {player.hp}/{player.max_hp} HP\n"
        f"🔪 {weapon.name}\n\n"
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
    test_map = data.get('test_map')
    
    result = []
    
    if action == "attack":
        if random.randint(1, 100) <= weapon.accuracy:
            damage = random.randint(weapon.damage[0], weapon.damage[1])
            if random.randint(1, 100) <= weapon.crit_chance:
                damage = int(damage * weapon.crit_multiplier)
                result.append(f"🔥 КРИТ! {damage} урона")
            else:
                result.append(f"⚔️ {damage} урона")
            enemy.hp -= damage
        else:
            result.append("😫 Промах!")
        
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
    
    if enemy.hp <= 0:
        player.exp += enemy.exp
        if player.exp >= player.level * 100:
            player.level += 1
            player.max_hp += 10
            player.hp = player.max_hp
            result.append(f"✨ **УРОВЕНЬ {player.level}!**")
        
        loot, gold = generate_loot(enemy.loot_table)
        player.gold += gold
        
        if test_map:
            current_node = test_map[player.current_node]
            current_node.completed = True
        
        loot_text = "\n".join([f"{item['emoji']} {item['name']} x{item['amount']}" for item in loot])
        
        await callback.message.edit_text(
            f"🎉 **ПОБЕДА!**\n\n" +
            "\n".join(result) +
            f"\n\n✨ Опыт: +{enemy.exp}\n"
            f"💰 Золото: +{gold}\n"
            f"🎒 Добыча:\n{loot_text}"
        )
        
        await state.update_data(player=player, test_map=test_map)
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
    test_map = data['test_map']
    
    current_node = test_map[player.current_node]
    
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
    
    await state.update_data(player=player, test_map=test_map)
    
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
    test_map = data['test_map']
    
    current_node = test_map[player.current_node]
    
    if current_node.node_type != "altar" or current_node.completed:
        await callback.answer("❌ Здесь нет алтаря!")
        return
    
    altar = ALTAR_EFFECTS[current_node.content]
    
    effect_text = ""
    if altar["effect"] == "damage_up":
        player.buffs.append("⚔️ Сила +5")
        effect_text = "⚔️ Твоя сила увеличилась на 5!"
    elif altar["effect"] == "hp_up":
        player.max_hp += 10
        player.hp += 10
        effect_text = "❤️ Твое здоровье увеличилось на 10!"
    
    current_node.completed = True
    
    await state.update_data(player=player, test_map=test_map)
    
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
    
    debuffs_text = ""
    if player.debuffs:
        debuffs_text = "\n💢 Дебаффы: " + ", ".join(player.debuffs)
    
    text = (
        f"📊 **СТАТИСТИКА**\n\n"
        f"👤 Уровень: {player.level}\n"
        f"✨ Опыт: {player.exp}/{player.level * 100}\n"
        f"❤️ HP: {player.hp}/{player.max_hp}\n"
        f"🛡️ Защита: {player.defense}\n"
        f"💰 Золото: {player.gold}"
        f"{buffs_text}{debuffs_text}"
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
    test_map = create_test_map()
    player = Player()
    player.map = test_map
    player.current_node = "start"
    await state.update_data(
        player=player,
        test_map=test_map
    )
    await show_map(message, state)

@dp.message(Command('ping'))
async def cmd_ping(message: types.Message):
    await message.answer("🏓 pong")

# ============= ЗАПУСК =============

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🗺️ Тестовая карта запущена!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
