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
        self.position = 0  # позиция на линии (0 = старт)
        self.max_position = 7  # всего 8 позиций (0-7)

class MapNode:
    def __init__(self, pos, node_type, content=None, name=""):
        self.pos = pos
        self.node_type = node_type  # "start", "enemy", "boss", "chest", "empty", "exit"
        self.content = content
        self.name = name
        self.visited = False
        self.completed = False

# ============= ТИПЫ СОБЫТИЙ =============

ENEMY_TYPES = {
    "zombie": {"name": "🧟 Зомби", "hp": 45, "damage": (6,12), "accuracy": 65, "defense": 2, "exp": 25, "emoji": "🧟"},
    "boss_minor": {"name": "👹 Страж", "hp": 80, "damage": (10,18), "accuracy": 70, "defense": 5, "exp": 60, "emoji": "👹"},
    "boss_final": {"name": "👹 Финальный босс", "hp": 150, "damage": (15,25), "accuracy": 75, "defense": 10, "exp": 150, "emoji": "👹"}
}

ALTAR_EFFECTS = [
    {"name": "Алтарь силы", "desc": "⚔️ +5 к урону", "effect": "damage", "value": 5, "emoji": "⚔️"},
    {"name": "Алтарь здоровья", "desc": "❤️ +10 HP", "effect": "hp", "value": 10, "emoji": "❤️"},
    {"name": "Алтарь защиты", "desc": "🛡️ +3 к защите", "effect": "defense", "value": 3, "emoji": "🛡️"},
    {"name": "Алтарь золота", "desc": "💰 +50 золота", "effect": "gold", "value": 50, "emoji": "💰"}
]

# ============= СОЗДАНИЕ КАРТЫ =============

def create_line_map():
    """Создает карту в виде прямой линии как в примере"""
    nodes = []
    
    # Позиция 0: Старт
    nodes.append(MapNode(0, "start", name="🧝 Старт"))
    
    # Позиция 1: ❓ (пусто)
    nodes.append(MapNode(1, "empty", name="⬜ Путь"))
    
    # Позиция 2: ⚔️ (первый враг)
    nodes.append(MapNode(2, "enemy", "zombie", name="🧟 Зомби"))
    
    # Позиция 3: 👹 (первый босс/страж)
    nodes.append(MapNode(3, "boss", "boss_minor", name="👹 Страж"))
    
    # Позиция 4: ❓ (пусто)
    nodes.append(MapNode(4, "empty", name="⬜ Путь"))
    
    # Позиция 5: ❓ (пусто)
    nodes.append(MapNode(5, "empty", name="⬜ Путь"))
    
    # Позиция 6: 📦 (сундук)
    nodes.append(MapNode(6, "chest", "common", name="📦 Сундук"))
    
    # Позиция 7: 👹🚪 (финальный босс с выходом)
    nodes.append(MapNode(7, "boss_exit", "boss_final", name="👹 Финальный босс (выход)"))
    
    # Старт посещен
    nodes[0].visited = True
    
    return nodes

def format_line_map(nodes, player_pos):
    """Форматирует карту в виде прямой линии"""
    lines = []
    
    # Верхняя граница из скал
    lines.append("🗻" * 11)
    lines.append("")
    
    # Основная линия
    line = ""
    for i, node in enumerate(nodes):
        if i == player_pos:
            line += "🧝"
        elif node.visited:
            if node.completed:
                line += "✅"
            elif node.node_type == "enemy":
                line += "⚔️"
            elif node.node_type == "boss":
                line += "👹"
            elif node.node_type == "boss_exit":
                line += "👹🚪"
            elif node.node_type == "chest":
                line += "📦"
            elif node.node_type == "empty":
                line += "❓"
            else:
                line += "⬜"
        else:
            line += "❓"
        
        if i < len(nodes) - 1:
            line += "──"
    
    lines.append(line)
    lines.append("")
    
    # Нижняя граница из скал
    lines.append("🗻" * 11)
    
    # Легенда
    lines.append("")
    lines.append("🧝 ты | ❓ не разведано | ✅ пройдено")
    lines.append("⚔️ враг | 👹 босс | 👹🚪 финальный босс+выход | 📦 сундук")
    
    return "\n".join(lines)

# ============= ФУНКЦИИ =============

def generate_loot(chest_type):
    """Генерирует лут из сундука"""
    gold = random.randint(10, 30)
    items = []
    if random.random() < 0.5:
        items.append("аптечка")
    return gold, items

# ============= ЭКРАН КАРТЫ =============

async def show_map(message: types.Message, state: FSMContext):
    """Показывает карту"""
    data = await state.get_data()
    
    if not data or 'nodes' not in data:
        nodes = create_line_map()
        player = Player()
        await state.update_data(
            player=player,
            nodes=nodes
        )
    else:
        player = data['player']
        nodes = data['nodes']
    
    current_node = nodes[player.position]
    current_node.visited = True
    
    map_display = format_line_map(nodes, player.position)
    
    # Информация о текущей позиции
    node_info = f"📍 **Позиция {player.position}**\n"
    node_info += f"**{current_node.name}**\n"
    
    if current_node.node_type == "start":
        node_info += "Начало твоего пути"
    elif current_node.node_type == "enemy" and not current_node.completed:
        enemy = ENEMY_TYPES[current_node.content]
        node_info += f"👾 **{enemy['name']}**\n❤️ HP: {enemy['hp']}"
    elif current_node.node_type in ["boss", "boss_exit"] and not current_node.completed:
        enemy = ENEMY_TYPES[current_node.content]
        node_info += f"👹 **{enemy['name']}**\n❤️ HP: {enemy['hp']}"
    elif current_node.node_type == "chest" and not current_node.completed:
        node_info += f"📦 **Сундук**"
    elif current_node.node_type == "empty":
        node_info += f"⬜ Пустой участок пути"
    elif current_node.completed:
        node_info += "✅ Уже пройдено"
    
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
        if current_node.node_type in ["enemy", "boss", "boss_exit"]:
            buttons.append([InlineKeyboardButton(text="⚔️ Вступить в бой", callback_data="start_battle")])
        elif current_node.node_type == "chest":
            buttons.append([InlineKeyboardButton(text="📦 Открыть сундук", callback_data="open_chest")])
    
    # Кнопки перемещения
    if player.position > 0:
        buttons.append([InlineKeyboardButton(text="⬅️ Налево", callback_data="move_left")])
    
    if player.position < player.max_position:
        # Проверяем, можно ли идти направо (всегда можно, кроме особых случаев)
        buttons.append([InlineKeyboardButton(text="➡️ Направо", callback_data="move_right")])
    
    # Кнопка выхода (только если на позиции финального босса и он побежден)
    if player.position == 7 and nodes[7].completed:
        buttons.append([InlineKeyboardButton(text="🚪 Выйти", callback_data="exit_location")])
    
    # Кнопки меню
    buttons.append([
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="show_inventory"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await state.update_data(player=player, nodes=nodes)
    
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except:
        await message.answer(text, reply_markup=keyboard)

# ============= ПЕРЕМЕЩЕНИЕ =============

@dp.callback_query(lambda c: c.data == "move_left")
async def move_left(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    
    if player.position > 0:
        player.position -= 1
    
    await state.update_data(player=player)
    await show_map(callback.message, state)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "move_right")
async def move_right(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    nodes = data['nodes']
    
    if player.position < player.max_position:
        player.position += 1
        nodes[player.position].visited = True
    
    await state.update_data(player=player, nodes=nodes)
    await show_map(callback.message, state)
    await callback.answer()

# ============= БОЙ =============

@dp.callback_query(lambda c: c.data == "start_battle")
async def start_battle(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    nodes = data['nodes']
    
    current_node = nodes[player.position]
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
    nodes = data['nodes']
    
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
        
        current_node = nodes[player.position]
        current_node.completed = True
        
        await callback.message.edit_text(
            f"🎉 **ПОБЕДА!**\n\n" +
            "\n".join(result) +
            f"\n\n✨ Опыт: +{enemy.exp}\n💰 Золото: +{gold}"
        )
        
        await state.update_data(player=player, nodes=nodes)
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
    nodes = data['nodes']
    
    current_node = nodes[player.position]
    
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
    
    await state.update_data(player=player, nodes=nodes)
    await asyncio.sleep(2)
    await show_map(callback.message, state)
    await callback.answer()

# ============= ВЫХОД =============

@dp.callback_query(lambda c: c.data == "exit_location")
async def exit_location(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    nodes = data['nodes']
    
    if player.position != 7 or not nodes[7].completed:
        await callback.answer("❌ Здесь нет выхода или босс не побежден!")
        return
    
    await callback.message.edit_text(
        "🚪 **ТЫ ВЫШЕЛ ИЗ ЛОКАЦИИ!**\n\n"
        "Поздравляю с завершением пути!\n\n"
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
    nodes = create_line_map()
    player = Player()
    await state.update_data(
        player=player,
        nodes=nodes
    )
    await show_map(message, state)

@dp.message(Command('ping'))
async def cmd_ping(message: types.Message):
    await message.answer("🏓 pong")

# ============= ЗАПУСК =============

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🗺️ Прямая линия со скалами запущена!")
    print("🧝──❓──⚔️──👹──❓──❓──📦──👹🚪")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
