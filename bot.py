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
    def __init__(self, name, hp, damage, accuracy, defense, exp, emoji, rarity):
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.damage = damage
        self.accuracy = accuracy
        self.defense = defense
        self.exp = exp
        self.emoji = emoji
        self.rarity = rarity

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
        self.current_floor = 1
        self.max_floor = 10
        self.floor_events = []

# ============= ПУЛ ПРОТИВНИКОВ (GACHA) =============

COMMON_ENEMIES = [
    {"name": "Зомби", "hp": 35, "damage": (5,10), "accuracy": 60, "defense": 2, "exp": 20, "emoji": "🧟"},
    {"name": "Скелет", "hp": 30, "damage": (6,12), "accuracy": 65, "defense": 3, "exp": 22, "emoji": "💀"},
    {"name": "Паук", "hp": 25, "damage": (7,11), "accuracy": 70, "defense": 1, "exp": 18, "emoji": "🕷️"},
    {"name": "Призрак", "hp": 28, "damage": (8,14), "accuracy": 75, "defense": 0, "exp": 25, "emoji": "👻"},
    {"name": "Кабан", "hp": 40, "damage": (6,13), "accuracy": 60, "defense": 4, "exp": 23, "emoji": "🐗"},
    {"name": "Волк", "hp": 38, "damage": (7,15), "accuracy": 70, "defense": 2, "exp": 24, "emoji": "🐺"},
    {"name": "Летучая мышь", "hp": 22, "damage": (5,9), "accuracy": 80, "defense": 1, "exp": 16, "emoji": "🦇"},
    {"name": "Крокодил", "hp": 45, "damage": (8,16), "accuracy": 55, "defense": 5, "exp": 28, "emoji": "🐊"},
    {"name": "Скорпион", "hp": 32, "damage": (7,13), "accuracy": 65, "defense": 4, "exp": 26, "emoji": "🦂"},
    {"name": "Змея", "hp": 27, "damage": (9,15), "accuracy": 75, "defense": 1, "exp": 27, "emoji": "🐍"},
    {"name": "Ящер", "hp": 42, "damage": (6,12), "accuracy": 60, "defense": 6, "exp": 25, "emoji": "🦎"},
    {"name": "Крыса", "hp": 20, "damage": (4,8), "accuracy": 70, "defense": 1, "exp": 15, "emoji": "🐀"},
    {"name": "Гарпия", "hp": 33, "damage": (7,14), "accuracy": 75, "defense": 2, "exp": 24, "emoji": "🦅"},
    {"name": "Муравей", "hp": 28, "damage": (5,10), "accuracy": 65, "defense": 5, "exp": 19, "emoji": "🐜"},
    {"name": "Комар", "hp": 18, "damage": (4,7), "accuracy": 85, "defense": 0, "exp": 14, "emoji": "🦟"},
    {"name": "Жук", "hp": 30, "damage": (5,11), "accuracy": 60, "defense": 7, "exp": 21, "emoji": "🐞"},
    {"name": "Кузнечик", "hp": 23, "damage": (5,9), "accuracy": 80, "defense": 2, "exp": 17, "emoji": "🦗"},
    {"name": "Гусеница", "hp": 25, "damage": (4,8), "accuracy": 55, "defense": 3, "exp": 16, "emoji": "🐛"},
    {"name": "Мотылек", "hp": 21, "damage": (5,10), "accuracy": 75, "defense": 1, "exp": 18, "emoji": "🦋"},
    {"name": "Слизень", "hp": 35, "damage": (3,7), "accuracy": 50, "defense": 8, "exp": 20, "emoji": "🐌"}
]

RARE_ENEMIES = [
    {"name": "Рыцарь смерти", "hp": 65, "damage": (12,20), "accuracy": 70, "defense": 8, "exp": 50, "emoji": "⚔️"},
    {"name": "Некромант", "hp": 50, "damage": (15,25), "accuracy": 80, "defense": 4, "exp": 55, "emoji": "🔮"},
    {"name": "Берсерк", "hp": 70, "damage": (14,24), "accuracy": 65, "defense": 6, "exp": 52, "emoji": "🪖"},
    {"name": "Огр", "hp": 85, "damage": (13,22), "accuracy": 55, "defense": 10, "exp": 58, "emoji": "👹"},
    {"name": "Темный маг", "hp": 45, "damage": (18,28), "accuracy": 85, "defense": 3, "exp": 60, "emoji": "🧙"},
    {"name": "Варг", "hp": 75, "damage": (12,21), "accuracy": 70, "defense": 7, "exp": 53, "emoji": "🐉"},
    {"name": "Грифон", "hp": 60, "damage": (14,23), "accuracy": 75, "defense": 5, "exp": 51, "emoji": "🦅"},
    {"name": "Вервольф", "hp": 68, "damage": (13,22), "accuracy": 72, "defense": 6, "exp": 54, "emoji": "🐺"},
    {"name": "Вампир", "hp": 55, "damage": (16,26), "accuracy": 78, "defense": 4, "exp": 57, "emoji": "🧛"},
    {"name": "Мутант", "hp": 72, "damage": (12,20), "accuracy": 68, "defense": 9, "exp": 56, "emoji": "👾"}
]

EPIC_ENEMIES = [
    {"name": "Дракон", "hp": 120, "damage": (18,30), "accuracy": 75, "defense": 12, "exp": 100, "emoji": "🐲"},
    {"name": "Демон", "hp": 110, "damage": (20,32), "accuracy": 80, "defense": 10, "exp": 110, "emoji": "👹"},
    {"name": "Тролль", "hp": 140, "damage": (16,28), "accuracy": 60, "defense": 15, "exp": 105, "emoji": "🧌"},
    {"name": "Тираннозавр", "hp": 130, "damage": (19,31), "accuracy": 70, "defense": 11, "exp": 108, "emoji": "🦖"},
    {"name": "Око древних", "hp": 95, "damage": (22,35), "accuracy": 90, "defense": 5, "exp": 115, "emoji": "👁️"}
]

LEGENDARY_ENEMIES = [
    {"name": "Древний дракон", "hp": 200, "damage": (25,40), "accuracy": 85, "defense": 15, "exp": 200, "emoji": "🐉✨"},
]

BOSS_ENEMIES = [
    {"name": "Повелитель тьмы", "hp": 180, "damage": (20,35), "accuracy": 80, "defense": 12, "exp": 150, "emoji": "👹🔥"},
    {"name": "Архимаг", "hp": 150, "damage": (25,38), "accuracy": 90, "defense": 8, "exp": 160, "emoji": "🧙‍♂️✨"},
    {"name": "Король демонов", "hp": 200, "damage": (22,36), "accuracy": 75, "defense": 14, "exp": 170, "emoji": "👑👹"},
    {"name": "Саркофаг", "hp": 220, "damage": (20,34), "accuracy": 70, "defense": 18, "exp": 180, "emoji": "🦴🐉"},
    {"name": "Древний ужас", "hp": 190, "damage": (24,40), "accuracy": 82, "defense": 10, "exp": 190, "emoji": "👾💀"}
]

# ============= ПУЛ СОБЫТИЙ =============

EVENT_POOL = [
    {"type": "chest", "name": "Обычный сундук", "emoji": "📦", "rarity": "common", "chance": 40},
    {"type": "chest", "name": "Редкий сундук", "emoji": "📦✨", "rarity": "rare", "chance": 15},
    {"type": "chest", "name": "Эпический сундук", "emoji": "📦🌟", "rarity": "epic", "chance": 5},
    {"type": "altar", "name": "Алтарь силы", "emoji": "⚔️", "effect": "damage", "value": 3, "chance": 10, "desc": "+3 к урону"},
    {"type": "altar", "name": "Алтарь здоровья", "emoji": "❤️", "effect": "hp", "value": 15, "chance": 10, "desc": "+15 HP"},
    {"type": "altar", "name": "Алтарь защиты", "emoji": "🛡️", "effect": "defense", "value": 2, "chance": 10, "desc": "+2 к защите"},
    {"type": "altar", "name": "Алтарь золота", "emoji": "💰", "effect": "gold", "value": 40, "chance": 10, "desc": "+40 золота"},
    {"type": "rest", "name": "Место отдыха", "emoji": "🔥", "heal": 20, "chance": 15, "desc": "+20 HP"},
    {"type": "trap", "name": "Ловушка", "emoji": "⚠️", "damage": 15, "chance": 15, "desc": "-15 HP"}
]

# ============= GACHA СИСТЕМА =============

def roll_enemy():
    """Роляет случайного врага с шансами как в гаче"""
    roll = random.random() * 100
    
    if roll < 50:
        return random.choice(COMMON_ENEMIES), "common"
    elif roll < 75:
        return random.choice(RARE_ENEMIES), "rare"
    elif roll < 90:
        return random.choice(EPIC_ENEMIES), "epic"
    else:
        return random.choice(LEGENDARY_ENEMIES), "legendary"

def roll_event():
    """Роляет случайное событие"""
    roll = random.random() * 100
    
    for event in EVENT_POOL:
        if roll < event["chance"]:
            return event
        roll -= event["chance"]
    
    return {"type": "empty", "name": "Пустота", "emoji": "⬜"}

def generate_floor(floor_num):
    """Генерирует событие для конкретного этажа"""
    if floor_num == 10:
        boss = random.choice(BOSS_ENEMIES)
        return {
            "type": "boss",
            "enemy": boss,
            "name": boss["name"],
            "emoji": boss["emoji"],
            "rarity": "boss"
        }
    else:
        if random.random() < 0.7:
            enemy, rarity = roll_enemy()
            return {
                "type": "battle",
                "enemy": enemy,
                "name": enemy["name"],
                "emoji": enemy["emoji"],
                "rarity": rarity
            }
        else:
            event = roll_event()
            return {
                "type": event["type"],
                "event": event,
                "name": event["name"],
                "emoji": event["emoji"]
            }

# ============= ВИЗУАЛИЗАЦИЯ =============

def format_dungeon_view(player, current_event):
    """Форматирует вид подземелья как в примере"""
    lines = []
    
    # Верхняя стена
    lines.append("🟫🟫🟫🟫🟫🟫")
    lines.append("")
    
    # Ряд с игроком и монстром
    if current_event and current_event["type"] in ["battle", "boss"]:
        # Если есть враг - показываем справа
        enemy_emoji = current_event["emoji"]
        spaces = " " * (20 - len(enemy_emoji))
        lines.append(f"👨‍🦱{spaces}{enemy_emoji}")
    else:
        # Если нет врага - только игрок
        lines.append("👨‍🦱")
    
    lines.append("")
    
    # Нижняя стена
    lines.append("🟫🟫🟫🟫🟫🟫")
    
    return "\n".join(lines)

# ============= ФУНКЦИИ =============

def generate_dungeon():
    """Генерирует подземелье из 10 этажей"""
    floors = []
    for i in range(1, 11):
        floor = generate_floor(i)
        floors.append(floor)
    return floors

# ============= ЭКРАН ПОДЗЕМЕЛЬЯ =============

async def show_dungeon(message: types.Message, state: FSMContext):
    """Показывает текущее состояние подземелья"""
    data = await state.get_data()
    
    if not data or 'floors' not in data:
        floors = generate_dungeon()
        player = Player()
        await state.update_data(
            player=player,
            floors=floors
        )
    else:
        player = data['player']
        floors = data['floors']
    
    current_event = floors[player.current_floor - 1]
    dungeon_view = format_dungeon_view(player, current_event)
    
    # Информация о текущем этаже
    floor_info = f"📍 **Этаж {player.current_floor}/10**\n\n"
    
    if current_event["type"] in ["battle", "boss"]:
        enemy = current_event["enemy"]
        rarity_text = {
            "common": "🟢 Обычный",
            "rare": "🔵 Редкий",
            "epic": "🟣 Эпический",
            "legendary": "🟠 Легендарный",
            "boss": "🔴 БОСС"
        }.get(current_event.get("rarity"), "")
        floor_info += f"**{enemy['emoji']} {enemy['name']}**\n{rarity_text}\n❤️ HP: {enemy['hp']}"
    else:
        event = current_event["event"]
        floor_info += f"**{event['emoji']} {event['name']}**"
        if event["type"] == "altar":
            floor_info += f"\n{event.get('desc', '')}"
        elif event["type"] == "trap":
            floor_info += f"\n⚠️ Потеряешь {event['damage']} HP"
        elif event["type"] == "rest":
            floor_info += f"\n🔥 Восстановит {event['heal']} HP"
    
    # Статус игрока
    buffs_text = ""
    if player.buffs:
        buffs_text = "\n✨ Баффы: " + ", ".join(player.buffs)
    
    player_status = (
        f"\n\n👤 **{player.hp}/{player.max_hp} HP** | Ур. {player.level}\n"
        f"⚔️ Бонус: +{player.damage_bonus} | 🛡️ Защита: {player.defense}\n"
        f"💰 {player.gold} золота | Аптечек: {player.inventory['аптечка']}\n"
        f"✨ Опыт: {player.exp}/{player.level * 100}"
        f"{buffs_text}"
    )
    
    text = f"{dungeon_view}\n\n{floor_info}{player_status}"
    
    # Кнопки
    buttons = []
    
    # Кнопка действия
    if current_event["type"] in ["battle", "boss"]:
        buttons.append([InlineKeyboardButton(text="⚔️ Вступить в бой", callback_data="start_battle")])
    elif current_event["type"] == "chest":
        buttons.append([InlineKeyboardButton(text="📦 Открыть сундук", callback_data="open_chest")])
    elif current_event["type"] == "altar":
        buttons.append([InlineKeyboardButton(text="🕯️ Использовать алтарь", callback_data="use_altar")])
    elif current_event["type"] == "rest":
        buttons.append([InlineKeyboardButton(text="🔥 Отдохнуть", callback_data="take_rest")])
    elif current_event["type"] == "trap":
        buttons.append([InlineKeyboardButton(text="⚠️ Пройти ловушку", callback_data="trigger_trap")])
    
    # Кнопка перехода
    if player.current_floor < player.max_floor:
        buttons.append([InlineKeyboardButton(text="⬇️ Спуститься ниже", callback_data="next_floor")])
    
    # Кнопки меню
    buttons.append([
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="show_inventory"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await state.update_data(player=player, floors=floors)
    
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except:
        await message.answer(text, reply_markup=keyboard)

# ============= ПЕРЕМЕЩЕНИЕ =============

@dp.callback_query(lambda c: c.data == "next_floor")
async def next_floor(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    floors = data['floors']
    
    if player.current_floor < player.max_floor:
        player.current_floor += 1
    
    await state.update_data(player=player, floors=floors)
    await show_dungeon(callback.message, state)
    await callback.answer()

# ============= БОЙ =============

@dp.callback_query(lambda c: c.data == "start_battle")
async def start_battle(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    floors = data['floors']
    
    current_floor = floors[player.current_floor - 1]
    enemy_data = current_floor["enemy"]
    
    enemy = Enemy(
        enemy_data["name"],
        enemy_data["hp"],
        enemy_data["damage"],
        enemy_data["accuracy"],
        enemy_data["defense"],
        enemy_data["exp"],
        enemy_data["emoji"],
        current_floor.get("rarity", "common")
    )
    
    await state.update_data(battle_enemy=enemy)
    await show_battle(callback.message, state)
    await callback.answer()

async def show_battle(message: types.Message, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    enemy = data['battle_enemy']
    
    rarity_color = {
        "common": "🟢",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟠",
        "boss": "🔴"
    }.get(enemy.rarity, "")
    
    text = (
        f"⚔️ **БОЙ!** {rarity_color}\n\n"
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
    floors = data['floors']
    
    result = []
    
    if action == "attack":
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
            await show_dungeon(callback.message, state)
            await callback.answer()
            return
        else:
            result.append("❌ Не удалось сбежать!")
            if random.randint(1, 100) <= enemy.accuracy:
                enemy_damage = random.randint(enemy.damage[0], enemy.damage[1])
                player.hp -= enemy_damage
                result.append(f"💥 {enemy.name} атакует: {enemy_damage} урона")
    
    if enemy.hp <= 0:
        player.exp += enemy.exp
        if player.exp >= player.level * 100:
            player.level += 1
            player.max_hp += 10
            player.hp = player.max_hp
            result.append(f"✨ **УРОВЕНЬ {player.level}!**")
        
        gold_mult = {
            "common": 1,
            "rare": 2,
            "epic": 4,
            "legendary": 8,
            "boss": 10
        }.get(enemy.rarity, 1)
        
        gold = random.randint(10, 20) * gold_mult
        player.gold += gold
        
        current_floor = floors[player.current_floor - 1]
        
        await callback.message.edit_text(
            f"🎉 **ПОБЕДА!**\n\n" +
            "\n".join(result) +
            f"\n\n✨ Опыт: +{enemy.exp}\n💰 Золото: +{gold}"
        )
        
        await state.update_data(player=player, floors=floors)
        await asyncio.sleep(2)
        await show_dungeon(callback.message, state)
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

# ============= СОБЫТИЯ =============

@dp.callback_query(lambda c: c.data == "open_chest")
async def open_chest(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    floors = data['floors']
    
    current_floor = floors[player.current_floor - 1]
    event = current_floor["event"]
    
    gold = 0
    items = []
    
    if event.get("rarity") == "rare":
        gold = random.randint(30, 60)
        items = ["аптечка"]
    elif event.get("rarity") == "epic":
        gold = random.randint(60, 100)
        items = ["аптечка", "зелье силы"]
    else:
        gold = random.randint(10, 30)
        if random.random() < 0.5:
            items = ["аптечка"]
    
    player.gold += gold
    for item in items:
        player.inventory[item] = player.inventory.get(item, 0) + 1
    
    items_text = ", ".join(items) if items else "ничего"
    await callback.message.edit_text(
        f"📦 **СУНДУК ОТКРЫТ!**\n\n"
        f"💰 Найдено: {gold} золота\n"
        f"🎒 Предметы: {items_text}"
    )
    
    await state.update_data(player=player, floors=floors)
    await asyncio.sleep(2)
    await show_dungeon(callback.message, state)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "use_altar")
async def use_altar(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    floors = data['floors']
    
    current_floor = floors[player.current_floor - 1]
    event = current_floor["event"]
    
    effect_text = ""
    if event["effect"] == "damage":
        player.damage_bonus += event["value"]
        player.buffs.append(f"⚔️ Сила +{event['value']}")
        effect_text = f"⚔️ Твой урон увеличился на {event['value']}!"
    elif event["effect"] == "hp":
        player.max_hp += event["value"]
        player.hp += event["value"]
        player.buffs.append(f"❤️ Здоровье +{event['value']}")
        effect_text = f"❤️ Твое здоровье увеличилось на {event['value']}!"
    elif event["effect"] == "defense":
        player.defense += event["value"]
        player.buffs.append(f"🛡️ Защита +{event['value']}")
        effect_text = f"🛡️ Твоя защита увеличилась на {event['value']}!"
    elif event["effect"] == "gold":
        player.gold += event["value"]
        effect_text = f"💰 Ты нашел {event['value']} золота!"
    
    await callback.message.edit_text(
        f"🕯️ **АЛТАРЬ**\n\n"
        f"{effect_text}"
    )
    
    await state.update_data(player=player, floors=floors)
    await asyncio.sleep(2)
    await show_dungeon(callback.message, state)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "take_rest")
async def take_rest(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    floors = data['floors']
    
    current_floor = floors[player.current_floor - 1]
    event = current_floor["event"]
    
    heal = event["heal"]
    player.hp = min(player.max_hp, player.hp + heal)
    
    await callback.message.edit_text(
        f"🔥 **ОТДЫХ**\n\n"
        f"Ты восстановил {heal} HP\n"
        f"❤️ {player.hp}/{player.max_hp}"
    )
    
    await state.update_data(player=player, floors=floors)
    await asyncio.sleep(2)
    await show_dungeon(callback.message, state)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "trigger_trap")
async def trigger_trap(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    floors = data['floors']
    
    current_floor = floors[player.current_floor - 1]
    event = current_floor["event"]
    
    damage = event["damage"]
    player.hp -= damage
    
    if player.hp <= 0:
        await callback.message.edit_text("💀 **ТЫ ПОГИБ В ЛОВУШКЕ...**")
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"⚠️ **ЛОВУШКА**\n\n"
        f"Ты потерял {damage} HP\n"
        f"❤️ {player.hp}/{player.max_hp}"
    )
    
    await state.update_data(player=player, floors=floors)
    await asyncio.sleep(2)
    await show_dungeon(callback.message, state)
    await callback.answer()

# ============= ИНВЕНТАРЬ И СТАТИСТИКА =============

@dp.callback_query(lambda c: c.data == "show_inventory")
async def show_inventory(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    
    inv = "\n".join([f"• {item}: {count}" for item, count in player.inventory.items()])
    
    text = f"🎒 **ИНВЕНТАРЬ**\n\n{inv}\n\n💰 Золото: {player.gold}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_dungeon")]
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
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_dungeon")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_dungeon")
async def back_to_dungeon(callback: types.CallbackQuery, state: FSMContext):
    await show_dungeon(callback.message, state)
    await callback.answer()

# ============= СТАРТ =============

@dp.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    floors = generate_dungeon()
    player = Player()
    await state.update_data(
        player=player,
        floors=floors
    )
    await show_dungeon(message, state)

@dp.message(Command('ping'))
async def cmd_ping(message: types.Message):
    await message.answer("🏓 pong")

# ============= ЗАПУСК =============

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🗺️ Вертикальное подземелье запущено!")
    print("🟫🟫🟫🟫🟫🟫")
    print("👨‍🦱                    🐍")
    print("🟫🟫🟫🟫🟫🟫")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
