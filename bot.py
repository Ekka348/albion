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
    def __init__(self, name, hp, damage, accuracy, defense, exp, loot_table, emoji, difficulty="normal"):
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.damage = damage
        self.accuracy = accuracy
        self.defense = defense
        self.exp = exp
        self.loot_table = loot_table
        self.emoji = emoji
        self.difficulty = difficulty

class Player:
    def __init__(self):
        self.hp = 100
        self.max_hp = 100
        self.defense = 5
        self.exp = 0
        self.level = 1
        self.gold = 0
        self.inventory = {"аптечка": 3}
        self.current_location = "path"
        self.current_node = 0  # индекс текущего узла
        self.path = None  # будет заполнено позже

class PathNode:
    def __init__(self, node_id, depth, content_type, content=None, connections=None):
        self.id = node_id
        self.depth = depth  # глубина от начала (0 = старт)
        self.content_type = content_type  # "enemy", "chest", "elite", "boss", "rest", "shop", "empty"
        self.content = content
        self.connections = connections or []  # список id узлов, в которые можно перейти
        self.visited = False
        self.completed = False  # враг убит / сундук открыт

# ============= ДАННЫЕ =============

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
    "spider": {
        "name": "🕷️ Паук",
        "hp": 30,
        "damage": (5, 10),
        "accuracy": 75,
        "defense": 2,
        "exp": 20,
        "emoji": "🕷️",
        "difficulty": "normal"
    },
    "elite_zombie": {
        "name": "🧟‍♂️ Элитный зомби",
        "hp": 80,
        "damage": (10, 18),
        "accuracy": 70,
        "defense": 5,
        "exp": 60,
        "emoji": "🧟‍♂️",
        "difficulty": "elite"
    },
    "elite_skeleton": {
        "name": "💀‍♂️ Элитный скелет",
        "hp": 65,
        "damage": (12, 20),
        "accuracy": 75,
        "defense": 6,
        "exp": 70,
        "emoji": "💀‍♂️",
        "difficulty": "elite"
    },
    "boss": {
        "name": "👹 Древний ужас",
        "hp": 150,
        "damage": (15, 25),
        "accuracy": 80,
        "defense": 8,
        "exp": 200,
        "emoji": "👹",
        "difficulty": "boss"
    }
}

LOOT_TABLES = {
    "enemy": [
        {"name": "Монеты", "rarity": "common", "value": 10, "emoji": "💰", "chance": 80, "stack": True, "min": 5, "max": 15},
        {"name": "Кости", "rarity": "common", "value": 5, "emoji": "🦴", "chance": 70, "stack": True},
        {"name": "Аптечка", "rarity": "common", "value": 15, "emoji": "💊", "chance": 40, "stack": True},
        {"name": "Ржавый меч", "rarity": "rare", "value": 25, "emoji": "⚔️", "chance": 20, "stack": False},
        {"name": "Магический кристалл", "rarity": "epic", "value": 80, "emoji": "🔮", "chance": 8, "stack": False}
    ],
    "elite": [
        {"name": "Золото", "rarity": "common", "value": 50, "emoji": "💰", "chance": 100, "stack": True, "min": 20, "max": 40},
        {"name": "Большая аптечка", "rarity": "common", "value": 30, "emoji": "💊", "chance": 80, "stack": True},
        {"name": "Драгоценный камень", "rarity": "rare", "value": 100, "emoji": "💎", "chance": 50, "stack": True},
        {"name": "Магический посох", "rarity": "epic", "value": 150, "emoji": "🪄", "chance": 30, "stack": False},
        {"name": "Легендарный меч", "rarity": "legendary", "value": 300, "emoji": "⚔️✨", "chance": 10, "stack": False}
    ],
    "boss": [
        {"name": "Сундук с золотом", "rarity": "common", "value": 200, "emoji": "💰", "chance": 100, "stack": True, "min": 100, "max": 200},
        {"name": "Редкий самоцвет", "rarity": "rare", "value": 300, "emoji": "💎", "chance": 80, "stack": True},
        {"name": "Легендарный артефакт", "rarity": "legendary", "value": 500, "emoji": "🏆", "chance": 50, "stack": False},
        {"name": "Душа босса", "rarity": "legendary", "value": 1000, "emoji": "👹", "chance": 30, "stack": False}
    ],
    "chest": [
        {"name": "Золото", "rarity": "common", "value": 30, "emoji": "💰", "chance": 90, "stack": True, "min": 10, "max": 30},
        {"name": "Аптечка", "rarity": "common", "value": 20, "emoji": "💊", "chance": 70, "stack": True},
        {"name": "Зелье лечения", "rarity": "rare", "value": 40, "emoji": "🧪", "chance": 40, "stack": True},
        {"name": "Кинжал", "rarity": "rare", "value": 35, "emoji": "🗡️", "chance": 25, "stack": False},
        {"name": "Магический свиток", "rarity": "epic", "value": 80, "emoji": "📜", "chance": 15, "stack": False}
    ],
    "rest": [
        {"name": "Отдых", "rarity": "common", "value": 20, "emoji": "🔥", "chance": 100, "stack": False}
    ]
}

# ============= ГЕНЕРАЦИЯ ПУТИ =============

def generate_path(depth=5, branch_factor=2):
    """Генерирует ветвящийся путь как в рогаликах"""
    nodes = {}
    node_counter = 0
    
    # Стартовый узел (всегда пустой)
    start_node = PathNode(node_counter, 0, "empty")
    nodes[node_counter] = start_node
    node_counter += 1
    
    # Рекурсивно генерируем ветки
    def generate_branch(current_depth, parent_id, branch_num):
        nonlocal node_counter
        
        if current_depth >= depth:
            return
        
        # Количество ответвлений от этого узла
        num_branches = random.randint(1, branch_factor)
        
        for _ in range(num_branches):
            # Создаем новый узел
            new_node = PathNode(node_counter, current_depth, "empty")
            
            # Определяем тип контента (кроме последнего уровня)
            if current_depth == depth - 1:
                # Последний уровень - босс или элитный враг
                if random.random() < 0.7:
                    new_node.content_type = "boss"
                    new_node.content = "boss"
                else:
                    new_node.content_type = "elite"
                    new_node.content = random.choice(["elite_zombie", "elite_skeleton"])
            else:
                # Промежуточные уровни
                roll = random.random()
                if roll < 0.5:  # 50% враг
                    new_node.content_type = "enemy"
                    new_node.content = random.choice(["zombie", "skeleton", "ghost", "spider"])
                elif roll < 0.7:  # 20% сундук
                    new_node.content_type = "chest"
                elif roll < 0.85:  # 15% отдых
                    new_node.content_type = "rest"
                else:  # 15% пусто
                    new_node.content_type = "empty"
            
            nodes[node_counter] = new_node
            
            # Добавляем связь от родителя
            nodes[parent_id].connections.append(node_counter)
            
            # Рекурсивно генерируем следующую ветку
            generate_branch(current_depth + 1, node_counter, branch_factor)
            
            node_counter += 1
    
    # Генерируем ветки от старта
    generate_branch(1, 0, branch_factor)
    
    return nodes

def format_path_display(nodes, current_node_id):
    """Форматирует отображение пути"""
    # Группируем узлы по глубине
    depth_groups = {}
    for node_id, node in nodes.items():
        if node.depth not in depth_groups:
            depth_groups[node.depth] = []
        depth_groups[node.depth].append(node)
    
    # Сортируем узлы в каждой группе
    for depth in depth_groups:
        depth_groups[depth].sort(key=lambda n: n.id)
    
    # Строим отображение
    display_lines = []
    max_depth = max(depth_groups.keys())
    
    for depth in range(max_depth + 1):
        if depth not in depth_groups:
            continue
        
        line = ""
        for node in depth_groups[depth]:
            if node.id == current_node_id:
                line += "🧍"  # текущая позиция
            elif node.visited:
                if node.content_type == "enemy" and not node.completed:
                    line += ENEMY_TYPES[node.content]["emoji"]
                elif node.content_type == "elite" and not node.completed:
                    line += ENEMY_TYPES[node.content]["emoji"]
                elif node.content_type == "boss" and not node.completed:
                    line += "👹"
                elif node.content_type == "chest" and not node.completed:
                    line += "📦"
                elif node.content_type == "rest":
                    line += "🔥"
                elif node.completed:
                    line += "✅"
                else:
                    line += "⬜"
            else:
                line += "❓"
            
            # Добавляем соединительные линии
            if node.connections and depth < max_depth:
                line += "═" * 2
            else:
                line += "  "
        
        display_lines.append(line)
    
    return "\n".join(display_lines)

# ============= ФУНКЦИИ =============

def generate_loot(table_name):
    """Генерирует лут из таблицы"""
    table = LOOT_TABLES[table_name]
    loot = []
    total_value = 0
    
    for item in table:
        if random.randint(1, 100) <= item["chance"]:
            if item.get("stack", False):
                amount = random.randint(item.get("min", 1), item.get("max", 5))
                value = item["value"] * amount
                loot.append({
                    "name": item["name"],
                    "amount": amount,
                    "value": value,
                    "emoji": item["emoji"],
                    "rarity": item["rarity"]
                })
                total_value += value
            else:
                loot.append({
                    "name": item["name"],
                    "amount": 1,
                    "value": item["value"],
                    "emoji": item["emoji"],
                    "rarity": item["rarity"]
                })
                total_value += item["value"]
    
    return loot, total_value

# ============= ЭКРАН ПУТИ =============

async def show_path(message: types.Message, state: FSMContext):
    """Показывает ветвящийся путь"""
    data = await state.get_data()
    
    if not data or 'path_nodes' not in data:
        # Генерируем новый путь
        path_nodes = generate_path(depth=5, branch_factor=2)
        player = Player()
        player.path = path_nodes
        player.current_node = 0
        path_nodes[0].visited = True
        await state.update_data(
            player=player,
            path_nodes=path_nodes
        )
    else:
        player = data['player']
        path_nodes = data['path_nodes']
    
    current_node = path_nodes[player.current_node]
    current_node.visited = True
    
    # Отображаем путь
    path_display = format_path_display(path_nodes, player.current_node)
    
    # Информация о текущем узле
    node_info = f"📍 **Узел {player.current_node}** (глубина {current_node.depth})\n"
    
    if current_node.content_type == "enemy" and not current_node.completed:
        enemy = ENEMY_TYPES[current_node.content]
        node_info += f"👾 **{enemy['name']}**\n❤️ HP: {enemy['hp']}"
    elif current_node.content_type == "elite" and not current_node.completed:
        enemy = ENEMY_TYPES[current_node.content]
        node_info += f"⚔️ **ЭЛИТНЫЙ {enemy['name']}**\n❤️ HP: {enemy['hp']}"
    elif current_node.content_type == "boss" and not current_node.completed:
        node_info += f"👹 **БОСС: Древний ужас**\n❤️ HP: 150"
    elif current_node.content_type == "chest" and not current_node.completed:
        node_info += "📦 **Закрытый сундук**"
    elif current_node.content_type == "rest" and not current_node.completed:
        node_info += "🔥 **Место отдыха** (можно восстановить здоровье)"
    elif current_node.completed:
        node_info += "✅ **Пройдено**"
    else:
        node_info += "⬜ **Пусто**"
    
    # Статус игрока
    player_status = (
        f"👤 **{player.hp}/{player.max_hp} HP** | Ур. {player.level}\n"
        f"💰 {player.gold} золота | Аптечек: {player.inventory.get('аптечка', 0)}\n"
        f"✨ Опыт: {player.exp}/{player.level * 100}"
    )
    
    text = (
        f"🗺️ **Ветвящийся путь**\n"
        f"🧍 - ты | ❓ - не разведано | ✅ - пройдено\n\n"
        f"{path_display}\n\n"
        f"{node_info}\n\n"
        f"{player_status}"
    )
    
    # Кнопки
    buttons = []
    
    # Кнопка действия в зависимости от содержимого узла
    if current_node.content_type in ["enemy", "elite", "boss"] and not current_node.completed:
        buttons.append([InlineKeyboardButton(text="⚔️ Вступить в бой", callback_data="start_battle")])
    elif current_node.content_type == "chest" and not current_node.completed:
        buttons.append([InlineKeyboardButton(text="📦 Открыть сундук", callback_data="open_chest")])
    elif current_node.content_type == "rest" and not current_node.completed:
        buttons.append([InlineKeyboardButton(text="🔥 Отдохнуть (+20 HP)", callback_data="take_rest")])
    
    # Кнопки для перехода в следующие узлы
    if current_node.connections:
        conn_buttons = []
        for i, conn_id in enumerate(current_node.connections):
            conn_buttons.append(
                InlineKeyboardButton(
                    text=f"➡️ Путь {i+1}", 
                    callback_data=f"goto_node_{conn_id}"
                )
            )
        buttons.append(conn_buttons)
    
    # Кнопки меню
    buttons.append([
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="show_inventory"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await state.update_data(player=player, path_nodes=path_nodes)
    
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except:
        await message.answer(text, reply_markup=keyboard)

# ============= ПЕРЕМЕЩЕНИЕ =============

@dp.callback_query(lambda c: c.data.startswith('goto_node_'))
async def goto_node_callback(callback: types.CallbackQuery, state: FSMContext):
    node_id = int(callback.data.split('_')[2])
    data = await state.get_data()
    player = data['player']
    path_nodes = data['path_nodes']
    
    # Проверяем, доступен ли этот узел
    if node_id in path_nodes[player.current_node].connections:
        player.current_node = node_id
        path_nodes[node_id].visited = True
    
    await state.update_data(player=player, path_nodes=path_nodes)
    await show_path(callback.message, state)
    await callback.answer()

# ============= БОЙ =============

@dp.callback_query(lambda c: c.data == "start_battle")
async def start_battle(callback: types.CallbackQuery, state: FSMContext):
    """Начинает бой"""
    data = await state.get_data()
    player = data['player']
    path_nodes = data['path_nodes']
    
    current_node = path_nodes[player.current_node]
    
    if current_node.content_type == "boss":
        enemy_data = ENEMY_TYPES["boss"]
    elif current_node.content_type == "elite":
        enemy_data = ENEMY_TYPES[current_node.content]
    else:
        enemy_data = ENEMY_TYPES[current_node.content]
    
    battle_enemy = Enemy(
        enemy_data["name"],
        enemy_data["hp"],
        enemy_data["damage"],
        enemy_data["accuracy"],
        enemy_data["defense"],
        enemy_data["exp"],
        current_node.content_type,  # loot table
        enemy_data["emoji"],
        enemy_data["difficulty"]
    )
    
    weapon = Weapon("Кинжал", (5, 12), 75, 10, 2.0, 999, 0)
    
    await state.update_data(
        battle_enemy=battle_enemy,
        battle_weapon=weapon
    )
    
    await show_battle(callback.message, state)
    await callback.answer()

async def show_battle(message: types.Message, state: FSMContext):
    """Показывает экран боя"""
    data = await state.get_data()
    player = data['player']
    enemy = data['battle_enemy']
    weapon = data['battle_weapon']
    
    difficulty_color = {
        "normal": "",
        "elite": "⚔️ ЭЛИТНЫЙ ",
        "boss": "👹 БОСС "
    }
    
    text = (
        f"⚔️ **{difficulty_color[enemy.difficulty]}БОЙ!**\n\n"
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
    
    if 'player' not in data or 'battle_enemy' not in data:
        await callback.message.edit_text("❌ Бой не найден. Начни заново.")
        await callback.answer()
        return
    
    player = data['player']
    enemy = data['battle_enemy']
    weapon = data['battle_weapon']
    path_nodes = data.get('path_nodes')
    
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
            await show_path(callback.message, state)
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
        
        # Выбираем таблицу лута в зависимости от типа врага
        loot_table = enemy.loot_table
        loot, gold = generate_loot(loot_table)
        player.gold += gold
        
        # Отмечаем узел как пройденный
        if path_nodes:
            current_node = path_nodes[player.current_node]
            current_node.completed = True
        
        loot_text = "\n".join([f"{item['emoji']} {item['name']} x{item['amount']}" for item in loot])
        
        await callback.message.edit_text(
            f"🎉 **ПОБЕДА!**\n\n" +
            "\n".join(result) +
            f"\n\n✨ Опыт: +{enemy.exp}\n"
            f"💰 Золото: +{gold}\n"
            f"🎒 Добыча:\n{loot_text}"
        )
        
        await state.update_data(player=player, path_nodes=path_nodes)
        await asyncio.sleep(3)
        await show_path(callback.message, state)
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
    path_nodes = data['path_nodes']
    
    current_node = path_nodes[player.current_node]
    
    if current_node.content_type != "chest" or current_node.completed:
        await callback.answer("❌ Здесь нет сундука!")
        return
    
    loot, gold = generate_loot("chest")
    player.gold += gold
    current_node.completed = True
    
    loot_text = []
    for item in loot:
        loot_text.append(f"{item['emoji']} {item['name']} x{item['amount']} - {item['value']}💰")
    
    await state.update_data(player=player, path_nodes=path_nodes)
    
    text = (
        f"📦 **СУНДУК ОТКРЫТ!**\n\n"
        f"💰 Найдено золота: {gold}\n"
        f"🎒 Добыча:\n" + "\n".join(loot_text)
    )
    
    await callback.message.edit_text(text)
    await asyncio.sleep(3)
    await show_path(callback.message, state)
    await callback.answer()

# ============= ОТДЫХ =============

@dp.callback_query(lambda c: c.data == "take_rest")
async def take_rest_callback(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    path_nodes = data['path_nodes']
    
    current_node = path_nodes[player.current_node]
    
    if current_node.content_type != "rest" or current_node.completed:
        await callback.answer("❌ Здесь нельзя отдохнуть!")
        return
    
    heal = 20
    player.hp = min(player.max_hp, player.hp + heal)
    current_node.completed = True
    
    await state.update_data(player=player, path_nodes=path_nodes)
    
    text = (
        f"🔥 **ОТДЫХ**\n\n"
        f"Ты развел костер и отдохнул.\n"
        f"❤️ Восстановлено {heal} HP\n"
        f"Текущее HP: {player.hp}/{player.max_hp}"
    )
    
    await callback.message.edit_text(text)
    await asyncio.sleep(3)
    await show_path(callback.message, state)
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
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_path")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "show_stats")
async def show_stats(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    
    text = (
        f"📊 **СТАТИСТИКА**\n\n"
        f"👤 Уровень: {player.level}\n"
        f"✨ Опыт: {player.exp}/{player.level * 100}\n"
        f"❤️ HP: {player.hp}/{player.max_hp}\n"
        f"🛡️ Защита: {player.defense}\n"
        f"💰 Золото: {player.gold}\n"
        f"📍 Узел: {player.current_node}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_path")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_path")
async def back_to_path(callback: types.CallbackQuery, state: FSMContext):
    await show_path(callback.message, state)
    await callback.answer()

# ============= СТАРТ =============

@dp.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    """Начало игры"""
    path_nodes = generate_path(depth=5, branch_factor=2)
    player = Player()
    player.path = path_nodes
    player.current_node = 0
    path_nodes[0].visited = True
    await state.update_data(
        player=player,
        path_nodes=path_nodes
    )
    await show_path(message, state)

@dp.message(Command('ping'))
async def cmd_ping(message: types.Message):
    await message.answer("🏓 pong")

# ============= ЗАПУСК =============

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🗺️ Ветвящийся путь как в Darkest Dungeon запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
