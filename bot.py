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
        self.current_location = "beach"
        self.x = 10  # начальная позиция по центру
        self.y = 10

class Chest:
    def __init__(self, x, y, loot_table):
        self.x = x
        self.y = y
        self.loot_table = loot_table
        self.opened = False

class MapCell:
    def __init__(self, x, y, terrain):
        self.x = x
        self.y = y
        self.terrain = terrain  # "sand", "water", "rock", "tree"
        self.enemy = None
        self.chest = None
        self.explored = False

# ============= ДАННЫЕ ЛОКАЦИЙ =============

TERRAIN_TYPES = {
    "sand": {"emoji": "🟨", "name": "песок", "passable": True},
    "water": {"emoji": "🟦", "name": "вода", "passable": False},
    "rock": {"emoji": "⛰️", "name": "скала", "passable": False},
    "tree": {"emoji": "🌲", "name": "дерево", "passable": True},
    "swamp": {"emoji": "🟫", "name": "болото", "passable": True, "damage": 2}
}

BORDER_EMOJIS = ["⛰️", "🌲", "🌴", "🗻", "🏔️"]

LOCATIONS = {
    "beach": {
        "name": "🏖️ Дикий пляж",
        "description": "Огромный пляж, уходящий в глубь острова.",
        "size": 20,  # 20x20
        "terrain_weights": {
            "sand": 50,
            "water": 15,
            "rock": 10,
            "tree": 15,
            "swamp": 10
        },
        "enemies": {
            "zombie": Enemy(
                name="🧟 Зомби матрос",
                hp=45,
                damage=(6, 12),
                accuracy=65,
                defense=2,
                exp=25,
                loot_table="zombie",
                emoji="🧟"
            ),
            "crab": Enemy(
                name="🦀 Мутировавший краб",
                hp=30,
                damage=(4, 8),
                accuracy=70,
                defense=5,
                exp=20,
                loot_table="crab",
                emoji="🦀"
            )
        },
        "chest_count": 8  # количество сундуков
    }
}

# ============= ТАБЛИЦЫ ЛУТА =============

LOOT_TABLES = {
    "zombie": [
        {"name": "Гнилая плоть", "rarity": "common", "value": 5, "emoji": "🧟", "chance": 80, "stack": True},
        {"name": "Ржавая сабля", "rarity": "common", "value": 8, "emoji": "⚔️", "chance": 40, "stack": False},
        {"name": "Проржавевший пистолет", "rarity": "rare", "value": 25, "emoji": "🔫", "chance": 20, "stack": False},
        {"name": "Золотая монета", "rarity": "rare", "value": 15, "emoji": "💰", "chance": 30, "stack": True},
        {"name": "Амулет капитана", "rarity": "epic", "value": 80, "emoji": "📿", "chance": 8, "stack": False},
        {"name": "Карта сокровищ", "rarity": "legendary", "value": 200, "emoji": "🗺️", "chance": 2, "stack": False}
    ],
    "crab": [
        {"name": "Клешня краба", "rarity": "common", "value": 4, "emoji": "🦀", "chance": 85, "stack": True},
        {"name": "Кусок панциря", "rarity": "common", "value": 6, "emoji": "🛡️", "chance": 60, "stack": True},
        {"name": "Черная жемчужина", "rarity": "rare", "value": 30, "emoji": "⚫", "chance": 15, "stack": True},
        {"name": "Крабовые глаза", "rarity": "epic", "value": 45, "emoji": "👀", "chance": 7, "stack": True},
        {"name": "Золотой краб", "rarity": "legendary", "value": 300, "emoji": "🦀✨", "chance": 1, "stack": False}
    ],
    "beach_chest": [
        {"name": "Монеты", "rarity": "common", "value": 20, "emoji": "💰", "chance": 90, "stack": True, "min": 5, "max": 20},
        {"name": "Аптечка", "rarity": "common", "value": 15, "emoji": "💊", "chance": 70, "stack": True},
        {"name": "Патроны", "rarity": "common", "value": 10, "emoji": "🔫", "chance": 60, "stack": True},
        {"name": "Старинная монета", "rarity": "rare", "value": 50, "emoji": "🪙", "chance": 30, "stack": True},
        {"name": "Кинжал русалки", "rarity": "epic", "value": 120, "emoji": "🗡️", "chance": 10, "stack": False},
        {"name": "Трезубец Посейдона", "rarity": "legendary", "value": 500, "emoji": "🔱", "chance": 2, "stack": False}
    ]
}

# ============= ГЕНЕРАЦИЯ КАРТЫ =============

def generate_map(location_name):
    """Генерирует случайную карту"""
    location = LOCATIONS[location_name]
    size = location["size"]
    weights = location["terrain_weights"]
    
    # Создаем пустую карту
    game_map = []
    for y in range(size):
        row = []
        for x in range(size):
            # Выбираем тип местности по весам
            terrain = random.choices(
                list(weights.keys()),
                weights=list(weights.values())
            )[0]
            row.append(MapCell(x, y, terrain))
        game_map.append(row)
    
    # Добавляем границы (непроходимые)
    for y in range(size):
        for x in range(size):
            if x == 0 or x == size-1 or y == 0 or y == size-1:
                game_map[y][x].terrain = random.choice(["rock", "tree"])
                game_map[y][x].explored = True  # границы видны всегда
    
    # Расставляем сундуки случайно
    chests = []
    for _ in range(location["chest_count"]):
        attempts = 0
        while attempts < 100:
            x = random.randint(1, size-2)
            y = random.randint(1, size-2)
            # Не ставим сундуки на воду и на границы
            if game_map[y][x].terrain not in ["water", "rock"] and game_map[y][x].chest is None:
                chest = Chest(x, y, "beach_chest")
                game_map[y][x].chest = chest
                chests.append(chest)
                break
            attempts += 1
    
    return game_map, chests

def get_visible_area(game_map, player_x, player_y, vision_range=2):
    """Возвращает видимую область карты"""
    size = len(game_map)
    visible = []
    
    for y in range(size):
        row = []
        for x in range(size):
            dist = abs(x - player_x) + abs(y - player_y)
            cell = game_map[y][x]
            
            # Отмечаем клетку как исследованную
            if dist <= vision_range:
                cell.explored = True
            
            # Определяем, что показывать
            if cell.explored:
                # Показываем реальный террейн
                if x == player_x and y == player_y:
                    row.append("🧍")  # игрок
                elif cell.chest and not cell.chest.opened:
                    row.append("📦")  # сундук
                elif cell.enemy:
                    row.append(cell.enemy.emoji)  # враг
                else:
                    row.append(TERRAIN_TYPES[cell.terrain]["emoji"])
            else:
                row.append("⬛")  # неизведанно
        
        visible.append(row)
    
    return visible

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

# ============= ЭКРАН ЛОКАЦИИ =============

async def show_location(message: types.Message, state: FSMContext):
    """Показывает карту локации"""
    data = await state.get_data()
    
    if not data or 'game_map' not in data:
        # Генерируем новую карту
        game_map, chests = generate_map("beach")
        player = Player()
        await state.update_data(
            player=player,
            game_map=game_map,
            chests=chests
        )
    else:
        player = data['player']
        game_map = data['game_map']
    
    location = LOCATIONS[player.current_location]
    visible_map = get_visible_area(game_map, player.x, player.y)
    
    # Формируем строки карты
    map_lines = []
    for y, row in enumerate(visible_map):
        # Добавляем границы слева и справа
        if y == 0 or y == len(visible_map)-1:
            border = random.choice(BORDER_EMOJIS) * 2
        else:
            border = random.choice(BORDER_EMOJIS)
        
        line = border + "".join(row) + border
        map_lines.append(line)
    
    map_str = "\n".join(map_lines)
    
    # Что на текущей клетке
    current_cell = game_map[player.y][player.x]
    cell_info = f"{TERRAIN_TYPES[current_cell.terrain]['emoji']} {TERRAIN_TYPES[current_cell.terrain]['name']}"
    cell_action = None
    
    if current_cell.chest and not current_cell.chest.opened:
        cell_info += " + 📦 сундук"
        cell_action = "open_chest"
    
    # Шанс встретить врага
    if not cell_action and random.random() < 0.2:
        enemy_type = random.choice(["zombie", "crab"])
        enemy = location["enemies"][enemy_type]
        cell_info += f" + ⚠️ {enemy.emoji} {enemy.name}"
        cell_action = "start_battle"
        await state.update_data(encounter_enemy=enemy_type)
    
    # Статус игрока
    player_status = (
        f"👤 **{player.hp}/{player.max_hp} HP** | Ур. {player.level}\n"
        f"💰 {player.gold} золота | Аптечек: {player.inventory.get('аптечка', 0)}\n"
        f"✨ Опыт: {player.exp}/{player.level * 100}"
    )
    
    text = (
        f"🏝️ **{location['name']}**\n"
        f"{location['description']}\n\n"
        f"{map_str}\n"
        f"🧍 ты | 📦 сундук | ⬛ туман\n\n"
        f"📍 **Позиция:** ({player.x}, {player.y})\n"
        f"🔍 **Здесь:** {cell_info}\n\n"
        f"{player_status}"
    )
    
    # Кнопки перемещения (8 направлений)
    buttons = []
    
    move_row1 = []
    if player.y > 0:
        if player.x > 0:
            move_row1.append(InlineKeyboardButton(text="↖️", callback_data="move_nw"))
        move_row1.append(InlineKeyboardButton(text="⬆️", callback_data="move_n"))
        if player.x < location["size"] - 1:
            move_row1.append(InlineKeyboardButton(text="↗️", callback_data="move_ne"))
    
    if move_row1:
        buttons.append(move_row1)
    
    move_row2 = []
    if player.x > 0:
        move_row2.append(InlineKeyboardButton(text="⬅️", callback_data="move_w"))
    move_row2.append(InlineKeyboardButton(text="⏺️", callback_data="center"))
    if player.x < location["size"] - 1:
        move_row2.append(InlineKeyboardButton(text="➡️", callback_data="move_e"))
    
    buttons.append(move_row2)
    
    move_row3 = []
    if player.y < location["size"] - 1:
        if player.x > 0:
            move_row3.append(InlineKeyboardButton(text="↙️", callback_data="move_sw"))
        move_row3.append(InlineKeyboardButton(text="⬇️", callback_data="move_s"))
        if player.x < location["size"] - 1:
            move_row3.append(InlineKeyboardButton(text="↘️", callback_data="move_se"))
    
    if move_row3:
        buttons.append(move_row3)
    
    # Кнопка действия
    if cell_action:
        if cell_action == "open_chest":
            buttons.append([InlineKeyboardButton(text="📦 Открыть сундук", callback_data="open_chest")])
        elif cell_action == "start_battle":
            buttons.append([InlineKeyboardButton(text="⚔️ Вступить в бой", callback_data="start_battle")])
    
    # Кнопки меню
    buttons.append([
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="show_inventory"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except:
        await message.answer(text, reply_markup=keyboard)

# ============= ПЕРЕМЕЩЕНИЕ =============

@dp.callback_query(lambda c: c.data.startswith('move_'))
async def move_callback(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    game_map = data['game_map']
    location = LOCATIONS[player.current_location]
    size = location["size"]
    
    dirs = {
        "n": (0, -1), "s": (0, 1), "w": (-1, 0), "e": (1, 0),
        "nw": (-1, -1), "ne": (1, -1), "sw": (-1, 1), "se": (1, 1)
    }
    
    move_dir = callback.data.split('_')[1]
    if move_dir in dirs:
        dx, dy = dirs[move_dir]
        new_x = player.x + dx
        new_y = player.y + dy
        
        # Проверяем границы и проходимость
        if 0 <= new_x < size and 0 <= new_y < size:
            cell = game_map[new_y][new_x]
            if TERRAIN_TYPES[cell.terrain]["passable"]:
                player.x = new_x
                player.y = new_y
                
                # Урон от болота
                if cell.terrain == "swamp":
                    damage = TERRAIN_TYPES["swamp"]["damage"]
                    player.hp -= damage
                    await callback.answer(f"🌫️ Болото наносит {damage} урона!")
    
    await state.update_data(player=player)
    await show_location(callback.message, state)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "center")
async def center_callback(callback: types.CallbackQuery, state: FSMContext):
    await show_location(callback.message, state)
    await callback.answer()

# ============= БОЙ =============

@dp.callback_query(lambda c: c.data == "start_battle")
async def start_battle(callback: types.CallbackQuery, state: FSMContext):
    """Начинает бой"""
    data = await state.get_data()
    player = data['player']
    
    enemy_type = data.get('encounter_enemy', random.choice(["zombie", "crab"]))
    enemy_data = LOCATIONS["beach"]["enemies"][enemy_type]
    
    battle_enemy = Enemy(
        enemy_data.name,
        enemy_data.hp,
        enemy_data.damage,
        enemy_data.accuracy,
        enemy_data.defense,
        enemy_data.exp,
        enemy_data.loot_table,
        enemy_data.emoji
    )
    
    weapon = Weapon("Пляжный нож", (5, 12), 75, 10, 2.0, 999, 0)
    
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
    
    if 'player' not in data or 'battle_enemy' not in data:
        await callback.message.edit_text("❌ Бой не найден. Начни заново.")
        await callback.answer()
        return
    
    player = data['player']
    enemy = data['battle_enemy']
    weapon = data['battle_weapon']
    
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
            await show_location(callback.message, state)
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
        
        loot_text = "\n".join([f"{item['emoji']} {item['name']} x{item['amount']}" for item in loot])
        
        await callback.message.edit_text(
            f"🎉 **ПОБЕДА!**\n\n" +
            "\n".join(result) +
            f"\n\n✨ Опыт: +{enemy.exp}\n"
            f"💰 Золото: +{gold}\n"
            f"🎒 Добыча:\n{loot_text}"
        )
        
        await state.update_data(player=player)
        await asyncio.sleep(3)
        await show_location(callback.message, state)
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
    game_map = data['game_map']
    
    current_cell = game_map[player.y][player.x]
    
    if not current_cell.chest or current_cell.chest.opened:
        await callback.answer("❌ Здесь нет сундука!")
        return
    
    chest = current_cell.chest
    chest.opened = True
    
    loot, gold = generate_loot(chest.loot_table)
    player.gold += gold
    
    loot_text = []
    for item in loot:
        loot_text.append(f"{item['emoji']} {item['name']} x{item['amount']} - {item['value']}💰")
    
    await state.update_data(player=player, game_map=game_map)
    
    text = (
        f"📦 **СУНДУК ОТКРЫТ!**\n\n"
        f"💰 Найдено золота: {gold}\n"
        f"🎒 Добыча:\n" + "\n".join(loot_text)
    )
    
    await callback.message.edit_text(text)
    await asyncio.sleep(3)
    await show_location(callback.message, state)
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
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_location")]
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
        f"📍 Локация: {LOCATIONS[player.current_location]['name']}\n"
        f"📌 Позиция: ({player.x}, {player.y})"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_location")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_location")
async def back_to_location(callback: types.CallbackQuery, state: FSMContext):
    await show_location(callback.message, state)
    await callback.answer()

# ============= СТАРТ =============

@dp.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    """Начало игры"""
    # Генерируем новую карту при старте
    game_map, chests = generate_map("beach")
    player = Player()
    await state.update_data(
        player=player,
        game_map=game_map,
        chests=chests
    )
    await show_location(message, state)

@dp.message(Command('ping'))
async def cmd_ping(message: types.Message):
    await message.answer("🏓 pong")

# ============= ЗАПУСК =============

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🏝️ Рандомная карта 20x20 с туманом войны запущена!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
