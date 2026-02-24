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
        self.current_location = "dungeon"
        self.x = 0
        self.y = 0

class Room:
    def __init__(self, x, y, room_type):
        self.x = x
        self.y = y
        self.room_type = room_type  # "corridor", "junction", "dead_end"
        self.content = None  # None, "enemy", "chest"
        self.enemy_type = None
        self.chest_opened = False
        self.explored = False
        self.connections = []  # список направлений, куда можно идти

# ============= ДАННЫЕ ЛОКАЦИЙ =============

ROOM_TYPES = {
    "corridor": {"emoji": "⬜", "name": "коридор"},
    "junction": {"emoji": "🟨", "name": "развилка"},
    "dead_end": {"emoji": "⬛", "name": "тупик"}
}

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
    "ghost": {
        "name": "👻 Призрак",
        "hp": 25,
        "damage": (10, 18),
        "accuracy": 80,
        "defense": 1,
        "exp": 35,
        "emoji": "👻"
    },
    "spider": {
        "name": "🕷️ Паук",
        "hp": 30,
        "damage": (5, 10),
        "accuracy": 75,
        "defense": 2,
        "exp": 20,
        "emoji": "🕷️"
    }
}

# ============= ТАБЛИЦЫ ЛУТА =============

LOOT_TABLES = {
    "enemy": [
        {"name": "Монеты", "rarity": "common", "value": 10, "emoji": "💰", "chance": 80, "stack": True, "min": 5, "max": 15},
        {"name": "Кости", "rarity": "common", "value": 5, "emoji": "🦴", "chance": 70, "stack": True},
        {"name": "Аптечка", "rarity": "common", "value": 15, "emoji": "💊", "chance": 40, "stack": True},
        {"name": "Ржавый меч", "rarity": "rare", "value": 25, "emoji": "⚔️", "chance": 20, "stack": False},
        {"name": "Магический кристалл", "rarity": "epic", "value": 80, "emoji": "🔮", "chance": 8, "stack": False},
        {"name": "Легендарный амулет", "rarity": "legendary", "value": 200, "emoji": "📿", "chance": 2, "stack": False}
    ],
    "chest": [
        {"name": "Золото", "rarity": "common", "value": 30, "emoji": "💰", "chance": 90, "stack": True, "min": 10, "max": 30},
        {"name": "Аптечка", "rarity": "common", "value": 20, "emoji": "💊", "chance": 70, "stack": True},
        {"name": "Зелье лечения", "rarity": "rare", "value": 40, "emoji": "🧪", "chance": 40, "stack": True},
        {"name": "Кинжал", "rarity": "rare", "value": 35, "emoji": "🗡️", "chance": 25, "stack": False},
        {"name": "Магический посох", "rarity": "epic", "value": 120, "emoji": "🪄", "chance": 10, "stack": False},
        {"name": "Драконий глаз", "rarity": "legendary", "value": 500, "emoji": "🐉", "chance": 3, "stack": False}
    ]
}

# ============= ГЕНЕРАЦИЯ КАРТЫ =============

def generate_dungeon():
    """Генерирует коридорную карту 10x10"""
    size = 10
    dungeon = []
    
    # Создаем пустую карту
    for y in range(size):
        row = []
        for x in range(size):
            row.append(Room(x, y, "corridor"))
        dungeon.append(row)
    
    # Генерируем коридоры (основной путь)
    for y in range(size):
        for x in range(size):
            # Основной путь - по центру
            if x == size//2:
                dungeon[y][x].room_type = "corridor"
                # Добавляем соединения
                if y > 0:
                    dungeon[y][x].connections.append("up")
                if y < size-1:
                    dungeon[y][x].connections.append("down")
    
    # Добавляем ответвления (тупики)
    for y in range(1, size-1, 2):  # Каждый второй ряд
        # Левое ответвление
        if random.random() < 0.7:
            x = size//2 - random.randint(1, 3)
            if x >= 0:
                dungeon[y][x].room_type = "dead_end"
                dungeon[y][x].connections = ["right"]
                # Соединяем с основным коридором
                for i in range(x+1, size//2):
                    dungeon[y][i].room_type = "corridor"
                    dungeon[y][i].connections = ["left", "right"]
        
        # Правое ответвление
        if random.random() < 0.7:
            x = size//2 + random.randint(1, 3)
            if x < size:
                dungeon[y][x].room_type = "dead_end"
                dungeon[y][x].connections = ["left"]
                # Соединяем с основным коридором
                for i in range(size//2, x):
                    dungeon[y][i].room_type = "corridor"
                    dungeon[y][i].connections = ["left", "right"]
    
    # Добавляем развилки
    for y in range(2, size-1, 3):
        if random.random() < 0.5:
            dungeon[y][size//2].room_type = "junction"
            # Добавляем дополнительные направления
            if random.random() < 0.5:
                dungeon[y][size//2].connections.append("left")
            if random.random() < 0.5:
                dungeon[y][size//2].connections.append("right")
    
    # Добавляем контент в тупики
    for y in range(size):
        for x in range(size):
            if dungeon[y][x].room_type == "dead_end":
                # 50% враг, 50% сундук
                if random.random() < 0.5:
                    dungeon[y][x].content = "enemy"
                    dungeon[y][x].enemy_type = random.choice(list(ENEMY_TYPES.keys()))
                else:
                    dungeon[y][x].content = "chest"
    
    # Стартовая комната
    dungeon[0][size//2].explored = True
    
    return dungeon

def get_room_display(room, player_x, player_y):
    """Возвращает emoji для отображения комнаты"""
    if room.x == player_x and room.y == player_y:
        return "🧍"  # игрок
    
    if not room.explored:
        return "❓"  # неисследовано
    
    if room.content == "enemy" and not room.explored:
        return ENEMY_TYPES[room.enemy_type]["emoji"]
    
    if room.content == "chest" and not room.chest_opened:
        return "📦"
    
    return ROOM_TYPES[room.room_type]["emoji"]

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
    """Показывает карту подземелья"""
    data = await state.get_data()
    
    if not data or 'dungeon' not in data:
        dungeon = generate_dungeon()
        player = Player()
        await state.update_data(
            player=player,
            dungeon=dungeon
        )
    else:
        player = data['player']
        dungeon = data['dungeon']
    
    size = 10
    
    # Формируем карту
    map_lines = []
    for y in range(size):
        line = ""
        for x in range(size):
            line += get_room_display(dungeon[y][x], player.x, player.y)
        map_lines.append(line)
    
    map_str = "\n".join(map_lines)
    
    # Текущая комната
    current_room = dungeon[player.y][player.x]
    current_room.explored = True
    
    room_info = f"{ROOM_TYPES[current_room.room_type]['emoji']} {ROOM_TYPES[current_room.room_type]['name']}"
    
    if current_room.content == "enemy" and current_room.enemy_type:
        enemy = ENEMY_TYPES[current_room.enemy_type]
        room_info += f"\n👾 Здесь: {enemy['emoji']} {enemy['name']}"
    elif current_room.content == "chest" and not current_room.chest_opened:
        room_info += "\n📦 Здесь: закрытый сундук"
    
    # Доступные направления
    available_dirs = []
    dir_emojis = {
        "up": "⬆️", "down": "⬇️", "left": "⬅️", "right": "➡️"
    }
    
    if player.y > 0 and dungeon[player.y-1][player.x].room_type != "junction":
        available_dirs.append("up")
    if player.y < size-1 and dungeon[player.y+1][player.x].room_type != "junction":
        available_dirs.append("down")
    if player.x > 0 and dungeon[player.y][player.x-1].room_type != "junction":
        available_dirs.append("left")
    if player.x < size-1 and dungeon[player.y][player.x+1].room_type != "junction":
        available_dirs.append("right")
    
    # Статус игрока
    player_status = (
        f"👤 **{player.hp}/{player.max_hp} HP** | Ур. {player.level}\n"
        f"💰 {player.gold} золота | Аптечек: {player.inventory.get('аптечка', 0)}\n"
        f"✨ Опыт: {player.exp}/{player.level * 100}"
    )
    
    text = (
        f"🏰 **Подземелье**\n"
        f"❓ - неисследовано | 🧍 - ты\n\n"
        f"{map_str}\n\n"
        f"📍 **Комната:** ({player.x}, {player.y})\n"
        f"{room_info}\n\n"
        f"{player_status}"
    )
    
    # Кнопки перемещения
    buttons = []
    
    # Верхний ряд (только вверх)
    if "up" in available_dirs:
        buttons.append([InlineKeyboardButton(text="⬆️ Вверх", callback_data="move_up")])
    
    # Средний ряд (влево и вправо)
    mid_row = []
    if "left" in available_dirs:
        mid_row.append(InlineKeyboardButton(text="⬅️ Влево", callback_data="move_left"))
    if "right" in available_dirs:
        mid_row.append(InlineKeyboardButton(text="➡️ Вправо", callback_data="move_right"))
    if mid_row:
        buttons.append(mid_row)
    
    # Нижний ряд (только вниз)
    if "down" in available_dirs:
        buttons.append([InlineKeyboardButton(text="⬇️ Вниз", callback_data="move_down")])
    
    # Кнопка действия
    if current_room.content == "enemy" and current_room.enemy_type:
        buttons.append([InlineKeyboardButton(text="⚔️ Вступить в бой", callback_data="start_battle")])
    elif current_room.content == "chest" and not current_room.chest_opened:
        buttons.append([InlineKeyboardButton(text="📦 Открыть сундук", callback_data="open_chest")])
    
    # Кнопки меню
    buttons.append([
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="show_inventory"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await state.update_data(player=player, dungeon=dungeon)
    
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except:
        await message.answer(text, reply_markup=keyboard)

# ============= ПЕРЕМЕЩЕНИЕ =============

@dp.callback_query(lambda c: c.data.startswith('move_'))
async def move_callback(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    dungeon = data['dungeon']
    
    dirs = {
        "up": (0, -1),
        "down": (0, 1),
        "left": (-1, 0),
        "right": (1, 0)
    }
    
    move_dir = callback.data.split('_')[1]
    if move_dir in dirs:
        dx, dy = dirs[move_dir]
        new_x = player.x + dx
        new_y = player.y + dy
        
        # Проверяем границы
        if 0 <= new_x < 10 and 0 <= new_y < 10:
            player.x = new_x
            player.y = new_y
            dungeon[new_y][new_x].explored = True
    
    await state.update_data(player=player, dungeon=dungeon)
    await show_location(callback.message, state)
    await callback.answer()

# ============= БОЙ =============

@dp.callback_query(lambda c: c.data == "start_battle")
async def start_battle(callback: types.CallbackQuery, state: FSMContext):
    """Начинает бой"""
    data = await state.get_data()
    player = data['player']
    dungeon = data['dungeon']
    
    current_room = dungeon[player.y][player.x]
    enemy_data = ENEMY_TYPES[current_room.enemy_type]
    
    battle_enemy = Enemy(
        enemy_data["name"],
        enemy_data["hp"],
        enemy_data["damage"],
        enemy_data["accuracy"],
        enemy_data["defense"],
        enemy_data["exp"],
        "enemy",
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
    dungeon = data.get('dungeon')
    
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
        
        loot, gold = generate_loot("enemy")
        player.gold += gold
        
        # Убираем врага из комнаты
        if dungeon:
            current_room = dungeon[player.y][player.x]
            current_room.content = None
        
        loot_text = "\n".join([f"{item['emoji']} {item['name']} x{item['amount']}" for item in loot])
        
        await callback.message.edit_text(
            f"🎉 **ПОБЕДА!**\n\n" +
            "\n".join(result) +
            f"\n\n✨ Опыт: +{enemy.exp}\n"
            f"💰 Золото: +{gold}\n"
            f"🎒 Добыча:\n{loot_text}"
        )
        
        await state.update_data(player=player, dungeon=dungeon)
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
    dungeon = data['dungeon']
    
    current_room = dungeon[player.y][player.x]
    
    if current_room.content != "chest" or current_room.chest_opened:
        await callback.answer("❌ Здесь нет сундука!")
        return
    
    loot, gold = generate_loot("chest")
    player.gold += gold
    current_room.chest_opened = True
    current_room.content = None
    
    loot_text = []
    for item in loot:
        loot_text.append(f"{item['emoji']} {item['name']} x{item['amount']} - {item['value']}💰")
    
    await state.update_data(player=player, dungeon=dungeon)
    
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
        f"📍 Позиция: ({player.x}, {player.y})"
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
    dungeon = generate_dungeon()
    player = Player()
    await state.update_data(
        player=player,
        dungeon=dungeon
    )
    await show_location(message, state)

@dp.message(Command('ping'))
async def cmd_ping(message: types.Message):
    await message.answer("🏓 pong")

# ============= ЗАПУСК =============

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🏰 Коридорное подземелье 10x10 с ветвлениями запущено!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
