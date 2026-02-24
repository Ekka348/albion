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
        self.current_path = 2  # начинаем со среднего пути
        self.current_pos = 0   # позиция 0-7 (всего 8 позиций)
        self.visited = set()

class MapNode:
    def __init__(self, path, pos, node_type, content=None, name=""):
        self.path = path      # 1, 2, 3
        self.pos = pos        # 0-7
        self.node_type = node_type  # "start", "enemy", "elite", "boss", "chest", "altar", "empty"
        self.content = content
        self.name = name
        self.completed = False
        self.visible = False

# ============= ТИПЫ СОБЫТИЙ =============

ENEMY_TYPES = {
    "zombie": {"name": "🧟 Зомби", "hp": 45, "damage": (6,12), "accuracy": 65, "defense": 2, "exp": 25, "emoji": "🧟"},
    "skeleton": {"name": "💀 Скелет", "hp": 35, "damage": (8,14), "accuracy": 70, "defense": 3, "exp": 30, "emoji": "💀"},
    "ghost": {"name": "👻 Призрак", "hp": 25, "damage": (10,18), "accuracy": 80, "defense": 1, "exp": 35, "emoji": "👻"},
    "elite": {"name": "⚔️ Рыцарь", "hp": 80, "damage": (12,20), "accuracy": 75, "defense": 8, "exp": 60, "emoji": "⚔️"},
    "boss": {"name": "👹 Древний ужас", "hp": 150, "damage": (15,30), "accuracy": 80, "defense": 10, "exp": 200, "emoji": "👹"}
}

ALTAR_EFFECTS = [
    {"name": "Алтарь силы", "desc": "⚔️ +5 урона", "effect": "damage", "value": 5, "emoji": "⚔️"},
    {"name": "Алтарь здоровья", "desc": "❤️ +10 HP", "effect": "hp", "value": 10, "emoji": "❤️"},
    {"name": "Алтарь защиты", "desc": "🛡️ +3 защиты", "effect": "defense", "value": 3, "emoji": "🛡️"},
    {"name": "Алтарь золота", "desc": "💰 +50 золота", "effect": "gold", "value": 50, "emoji": "💰"}
]

CHEST_TYPES = {
    "common": {"name": "Обычный сундук", "emoji": "📦", "value": (10,30)},
    "rare": {"name": "Редкий сундук", "emoji": "📦✨", "value": (30,60)}
}

# ============= СОЗДАНИЕ КАРТЫ =============

def create_map():
    """Создает карту с тремя путями"""
    nodes = {}
    
    # Позиции: 0=старт, 1-6=события, 7=босс
    # Верхний путь (path=1)
    nodes[(1,0)] = MapNode(1, 0, "start", name="🚪 Вход")
    nodes[(1,1)] = MapNode(1, 1, "enemy", "zombie", name="🧟 Лес")
    nodes[(1,2)] = MapNode(1, 2, "altar", 0, name="🕯️ Алтарь")
    nodes[(1,3)] = MapNode(1, 3, "chest", "common", name="📦 Тайник")
    nodes[(1,4)] = MapNode(1, 4, "empty", None, name="⬜ Поляна")
    nodes[(1,5)] = MapNode(1, 5, "enemy", "skeleton", name="💀 Кладбище")
    nodes[(1,6)] = MapNode(1, 6, "empty", None, name="⬜ Перекресток")
    nodes[(1,7)] = MapNode(1, 7, "boss", "boss", name="👹 Логово")
    
    # Средний путь (path=2)
    nodes[(2,0)] = MapNode(2, 0, "start", name="🚪 Вход")
    nodes[(2,1)] = MapNode(2, 1, "chest", "common", name="📦 Дупло")
    nodes[(2,2)] = MapNode(2, 2, "enemy", "ghost", name="👻 Туман")
    nodes[(2,3)] = MapNode(2, 3, "altar", 1, name="🕯️ Алтарь")
    nodes[(2,4)] = MapNode(2, 4, "chest", "rare", name="📦✨ Сокровище")
    nodes[(2,5)] = MapNode(2, 5, "enemy", "elite", name="⚔️ Элита")
    nodes[(2,6)] = MapNode(2, 6, "empty", None, name="⬜ Развилка")
    nodes[(2,7)] = MapNode(2, 7, "boss", "boss", name="👹 Логово")
    
    # Нижний путь (path=3)
    nodes[(3,0)] = MapNode(3, 0, "start", name="🚪 Вход")
    nodes[(3,1)] = MapNode(3, 1, "altar", 2, name="🕯️ Алтарь")
    nodes[(3,2)] = MapNode(3, 2, "chest", "common", name="📦 Корни")
    nodes[(3,3)] = MapNode(3, 3, "enemy", "zombie", name="🧟 Болото")
    nodes[(3,4)] = MapNode(3, 4, "empty", None, name="⬜ Поляна")
    nodes[(3,5)] = MapNode(3, 5, "chest", "rare", name="📦✨ Пещера")
    nodes[(3,6)] = MapNode(3, 6, "enemy", "skeleton", name="💀 Стражи")
    nodes[(3,7)] = MapNode(3, 7, "boss", "boss", name="👹 Логово")
    
    # Делаем стартовые узлы видимыми
    nodes[(1,0)].visible = True
    nodes[(2,0)].visible = True
    nodes[(3,0)].visible = True
    
    return nodes

def format_map_display(nodes, player):
    """Форматирует карту для отображения"""
    lines = []
    lines.append("╔══════════════════════════════════════════════════════════╗")
    lines.append("║                     🗺️ ТРИ ПУТИ 🗺️                       ║")
    lines.append("╚══════════════════════════════════════════════════════════╝")
    lines.append("")
    
    # Верхний путь
    top = "🔹 ВЕРХНИЙ: "
    for pos in range(0, 8):
        node = nodes.get((1, pos))
        if node:
            if player.current_path == 1 and player.current_pos == pos:
                top += "🧍"
            elif node.visible:
                if node.completed:
                    top += "✅"
                elif node.node_type == "enemy":
                    top += "⚔️"
                elif node.node_type == "elite":
                    top += "⚔️✨"
                elif node.node_type == "boss":
                    top += "👹"
                elif node.node_type == "chest":
                    top += "📦"
                elif node.node_type == "altar":
                    top += "🕯️"
                else:
                    top += "⬜"
            else:
                top += "❓"
            
            if pos < 7:
                top += "────"  # 4 черточки
    
    lines.append(top)
    
    # Соединительные линии с переходами
    conn_line = "          "
    for pos in range(0, 8):
        # Проверяем, есть ли переходы на этой позиции
        has_transition = False
        for path in [1,2,3]:
            node = nodes.get((path, pos))
            if node and node.visible:
                # Переходы возможны на позициях 2,4,6
                if pos in [2,4,6]:
                    has_transition = True
        
        if has_transition:
            conn_line += "│    "
        else:
            conn_line += "     "
    
    lines.append(conn_line)
    
    # Средний путь
    mid = "🔸 СРЕДНИЙ: "
    for pos in range(0, 8):
        node = nodes.get((2, pos))
        if node:
            if player.current_path == 2 and player.current_pos == pos:
                mid += "🧍"
            elif node.visible:
                if node.completed:
                    mid += "✅"
                elif node.node_type == "enemy":
                    mid += "⚔️"
                elif node.node_type == "elite":
                    mid += "⚔️✨"
                elif node.node_type == "boss":
                    mid += "👹"
                elif node.node_type == "chest":
                    mid += "📦"
                elif node.node_type == "altar":
                    mid += "🕯️"
                else:
                    mid += "⬜"
            else:
                mid += "❓"
            
            if pos < 7:
                mid += "────"
    
    lines.append(mid)
    lines.append(conn_line)
    
    # Нижний путь
    bot = "🔹 НИЖНИЙ:  "
    for pos in range(0, 8):
        node = nodes.get((3, pos))
        if node:
            if player.current_path == 3 and player.current_pos == pos:
                bot += "🧍"
            elif node.visible:
                if node.completed:
                    bot += "✅"
                elif node.node_type == "enemy":
                    bot += "⚔️"
                elif node.node_type == "elite":
                    bot += "⚔️✨"
                elif node.node_type == "boss":
                    bot += "👹"
                elif node.node_type == "chest":
                    bot += "📦"
                elif node.node_type == "altar":
                    bot += "🕯️"
                else:
                    bot += "⬜"
            else:
                bot += "❓"
            
            if pos < 7:
                bot += "────"
    
    lines.append(bot)
    lines.append("")
    lines.append("🧍 ты | ❓ скрыто | ✅ пройдено")
    lines.append("⚔️ враг | ⚔️✨ элита | 👹 босс")
    lines.append("📦 сундук | 🕯️ алтарь | ⬜ пусто")
    lines.append("│ - переход между путями")
    
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
    """Показывает карту"""
    data = await state.get_data()
    
    if not data or 'map_nodes' not in data:
        map_nodes = create_map()
        player = Player()
        # Делаем видимым стартовый узел
        map_nodes[(player.current_path, player.current_pos)].visible = True
        player.visited.add((player.current_path, player.current_pos))
        await state.update_data(player=player, map_nodes=map_nodes)
    else:
        player = data['player']
        map_nodes = data['map_nodes']
    
    # Делаем текущий узел видимым
    current_node = map_nodes.get((player.current_path, player.current_pos))
    if current_node:
        current_node.visible = True
        player.visited.add((player.current_path, player.current_pos))
    
    map_display = format_map_display(map_nodes, player)
    
    # Информация о текущем узле
    node_info = f"📍 **Позиция {player.current_pos} на пути {player.current_path}**\n"
    
    if current_node:
        node_info += f"**{current_node.name}**\n"
        
        if current_node.node_type == "enemy" and not current_node.completed:
            enemy = ENEMY_TYPES[current_node.content]
            node_info += f"👾 {enemy['name']} | ❤️ {enemy['hp']} HP"
        elif current_node.node_type == "elite" and not current_node.completed:
            enemy = ENEMY_TYPES["elite"]
            node_info += f"⚔️ ЭЛИТНЫЙ {enemy['name']} | ❤️ {enemy['hp']} HP"
        elif current_node.node_type == "boss" and not current_node.completed:
            node_info += f"👹 БОСС | ❤️ 150 HP"
        elif current_node.node_type == "chest" and not current_node.completed:
            chest = CHEST_TYPES[current_node.content]
            node_info += f"{chest['emoji']} {chest['name']}"
        elif current_node.node_type == "altar" and not current_node.completed:
            altar = ALTAR_EFFECTS[current_node.content]
            node_info += f"🕯️ {altar['name']}\n{altar['desc']}"
        elif current_node.completed:
            node_info += "✅ Уже пройдено"
    
    # Статус игрока
    player_status = (
        f"\n👤 **{player.hp}/{player.max_hp} HP** | Ур. {player.level}\n"
        f"⚔️ Бонус: +{player.damage_bonus} | 🛡️ Защита: {player.defense}\n"
        f"💰 {player.gold} золота | Аптечек: {player.inventory['аптечка']}\n"
        f"✨ Опыт: {player.exp}/{player.level * 100}"
    )
    
    text = f"{map_display}\n\n{node_info}{player_status}"
    
    # Кнопки
    buttons = []
    
    # Кнопка действия
    if current_node and not current_node.completed:
        if current_node.node_type in ["enemy", "elite", "boss"]:
            buttons.append([InlineKeyboardButton(text="⚔️ Вступить в бой", callback_data="start_battle")])
        elif current_node.node_type == "chest":
            buttons.append([InlineKeyboardButton(text="📦 Открыть сундук", callback_data="open_chest")])
        elif current_node.node_type == "altar":
            buttons.append([InlineKeyboardButton(text="🕯️ Использовать алтарь", callback_data="use_altar")])
    
    # Кнопка движения вперед
    if player.current_pos < 7:
        next_node = map_nodes.get((player.current_path, player.current_pos + 1))
        if next_node:
            emoji = "❓" if not next_node.visible else "➡️"
            buttons.append([
                InlineKeyboardButton(
                    text=f"{emoji} Вперед", 
                    callback_data="move_forward"
                )
            ])
    
    # Кнопки смены пути (доступны на позициях 2,4,6)
    if player.current_pos in [2,4,6]:
        # Вверх
        if player.current_path > 1:
            up_node = map_nodes.get((player.current_path - 1, player.current_pos))
            if up_node:
                emoji = "❓" if not up_node.visible else "⬆️"
                buttons.append([
                    InlineKeyboardButton(
                        text=f"{emoji} Перейти вверх", 
                        callback_data="move_up"
                    )
                ])
        
        # Вниз
        if player.current_path < 3:
            down_node = map_nodes.get((player.current_path + 1, player.current_pos))
            if down_node:
                emoji = "❓" if not down_node.visible else "⬇️"
                buttons.append([
                    InlineKeyboardButton(
                        text=f"{emoji} Перейти вниз", 
                        callback_data="move_down"
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

@dp.callback_query(lambda c: c.data == "move_forward")
async def move_forward(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    map_nodes = data['map_nodes']
    
    if player.current_pos < 7:
        player.current_pos += 1
        # Делаем новый узел видимым
        new_node = map_nodes.get((player.current_path, player.current_pos))
        if new_node:
            new_node.visible = True
    
    await state.update_data(player=player, map_nodes=map_nodes)
    await show_map(callback.message, state)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "move_up")
async def move_up(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    map_nodes = data['map_nodes']
    
    if player.current_path > 1 and player.current_pos in [2,4,6]:
        player.current_path -= 1
        new_node = map_nodes.get((player.current_path, player.current_pos))
        if new_node:
            new_node.visible = True
    
    await state.update_data(player=player, map_nodes=map_nodes)
    await show_map(callback.message, state)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "move_down")
async def move_down(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    map_nodes = data['map_nodes']
    
    if player.current_path < 3 and player.current_pos in [2,4,6]:
        player.current_path += 1
        new_node = map_nodes.get((player.current_path, player.current_pos))
        if new_node:
            new_node.visible = True
    
    await state.update_data(player=player, map_nodes=map_nodes)
    await show_map(callback.message, state)
    await callback.answer()

# ============= БОЙ =============

@dp.callback_query(lambda c: c.data == "start_battle")
async def start_battle(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    map_nodes = data['map_nodes']
    
    current_node = map_nodes.get((player.current_path, player.current_pos))
    
    if current_node.node_type == "boss":
        enemy_data = ENEMY_TYPES["boss"]
    elif current_node.node_type == "elite":
        enemy_data = ENEMY_TYPES["elite"]
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
        if random.randint(1, 100) <= 75:  # базовый шанс попадания
            damage = random.randint(5, 12) + player.damage_bonus
            if random.randint(1, 100) <= 10:  # шанс крита
                damage = int(damage * 2)
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
        
        current_node = map_nodes.get((player.current_path, player.current_pos))
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
    
    current_node = map_nodes.get((player.current_path, player.current_pos))
    
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
    
    current_node = map_nodes.get((player.current_path, player.current_pos))
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
    await state.update_data(player=player, map_nodes=map_nodes)
    await show_map(message, state)

@dp.message(Command('ping'))
async def cmd_ping(message: types.Message):
    await message.answer("🏓 pong")

# ============= ЗАПУСК =============

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🗺️ Карта с тремя путями запущена!")
    print("📌 8 позиций, 4 черточки между нодами")
    print("🔄 Переходы на позициях 2, 4, 6")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
