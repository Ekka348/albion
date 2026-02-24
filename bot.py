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
        self.position = 0

class Chest:
    def __init__(self, position, loot_table):
        self.position = position
        self.loot_table = loot_table
        self.opened = False

# ============= ДАННЫЕ ЛОКАЦИЙ =============

LOCATIONS = {
    "beach": {
        "name": "🏖️ Проклятый пляж",
        "description": "Мрачный пляж, усыпанный костями и обломками кораблей.",
        "background": "🏝️🌊🌴",
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
        "chests": [
            Chest(3, "beach_chest"),
            Chest(7, "beach_chest"),
            Chest(10, "beach_boss_chest")
        ]
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
    ],
    "beach_boss_chest": [
        {"name": "Золото", "rarity": "common", "value": 100, "emoji": "💰", "chance": 100, "stack": True, "min": 50, "max": 150},
        {"name": "Алмаз", "rarity": "rare", "value": 200, "emoji": "💎", "chance": 50, "stack": True},
        {"name": "Рубин", "rarity": "epic", "value": 300, "emoji": "🔴", "chance": 30, "stack": True},
        {"name": "Легендарный меч", "rarity": "legendary", "value": 800, "emoji": "⚔️✨", "chance": 15, "stack": False},
        {"name": "Корона затонувшего короля", "rarity": "legendary", "value": 1000, "emoji": "👑", "chance": 5, "stack": False}
    ]
}

# ============= СОСТОЯНИЯ =============

class GameStates(StatesGroup):
    exploring = State()
    battling = State()

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
    if not data or 'player' not in data:
        player = Player()
        await state.update_data(player=player)
    else:
        player = data['player']
    
    location = LOCATIONS[player.current_location]
    
    # Создаем карту пляжа
    map_line = []
    for i in range(11):
        if i == player.position:
            map_line.append("🔴")
        else:
            chest_found = False
            for chest in location["chests"]:
                if chest.position == i and not chest.opened:
                    map_line.append("📦")
                    chest_found = True
                    break
            if not chest_found:
                map_line.append("⬜")
    
    map_str = "".join(map_line)
    
    # Определяем, что на текущей клетке
    cell_info = "Пусто"
    cell_action = None
    
    # Проверяем сундуки
    for chest in location["chests"]:
        if chest.position == player.position and not chest.opened:
            cell_info = "📦 Закрытый сундук"
            cell_action = "open_chest"
            break
    
    # Если не сундук, проверяем врага (случайно)
    if not cell_action:
        # 30% шанс встретить врага на пустой клетке
        if random.random() < 0.3:
            enemy_type = random.choice(["zombie", "crab"])
            enemy = location["enemies"][enemy_type]
            cell_info = f"⚠️ {enemy.emoji} {enemy.name}"
            cell_action = "start_battle"
            # Сохраняем врага для боя
            await state.update_data(encounter_enemy=enemy_type)
    
    # Статус игрока
    player_status = (
        f"👤 **{player.hp}/{player.max_hp} HP** | Ур. {player.level}\n"
        f"💰 {player.gold} золота | Аптечек: {player.inventory.get('аптечка', 0)}\n"
        f"✨ Опыт: {player.exp}/{player.level * 100}"
    )
    
    text = (
        f"🏖️ **{location['name']}**\n"
        f"{location['background']}\n\n"
        f"{map_str}\n"
        f"⬜ пусто | 📦 сундук | 🔴 ты\n\n"
        f"📍 **Позиция:** {player.position}/10\n"
        f"🔍 **Здесь:** {cell_info}\n\n"
        f"{player_status}"
    )
    
    # Кнопки
    buttons = []
    
    # Кнопки перемещения
    move_buttons = []
    if player.position > 0:
        move_buttons.append(InlineKeyboardButton(text="◀ Влево", callback_data="move_left"))
    if player.position < 10:
        move_buttons.append(InlineKeyboardButton(text="Вправо ▶", callback_data="move_right"))
    
    if move_buttons:
        buttons.append(move_buttons)
    
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

@dp.callback_query(lambda c: c.data in ["move_left", "move_right"])
async def move_callback(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data.get('player', Player())
    
    if callback.data == "move_left":
        player.position = max(0, player.position - 1)
    else:
        player.position = min(10, player.position + 1)
    
    await state.update_data(player=player)
    await show_location(callback.message, state)
    await callback.answer()

# ============= БОЙ =============

@dp.callback_query(lambda c: c.data == "start_battle")
async def start_battle(callback: types.CallbackQuery, state: FSMContext):
    """Начинает бой"""
    data = await state.get_data()
    player = data['player']
    
    # Получаем тип врага из сохраненного или выбираем случайно
    enemy_type = data.get('encounter_enemy', random.choice(["zombie", "crab"]))
    enemy_data = LOCATIONS["beach"]["enemies"][enemy_type]
    
    # Создаем врага для боя
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
    
    # Простое оружие для теста
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
        # Атака игрока
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
        
        # Атака врага (если жив)
        if enemy.hp > 0:
            if random.randint(1, 100) <= enemy.accuracy:
                enemy_damage = random.randint(enemy.damage[0], enemy.damage[1])
                # Защита уменьшает урон
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
            
            # Враг атакует во время лечения
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
            # Враг атакует
            if random.randint(1, 100) <= enemy.accuracy:
                enemy_damage = random.randint(enemy.damage[0], enemy.damage[1])
                enemy_damage = max(1, enemy_damage - player.defense // 2)
                player.hp -= enemy_damage
                result.append(f"💥 {enemy.name} атакует: {enemy_damage} урона")
    
    # Проверка окончания боя
    if enemy.hp <= 0:
        # Победа
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
    
    # Обновляем состояние
    await state.update_data(player=player, battle_enemy=enemy)
    
    # Показываем следующий раунд
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
    location = LOCATIONS[player.current_location]
    
    # Находим сундук на текущей позиции
    chest = None
    for c in location["chests"]:
        if c.position == player.position and not c.opened:
            chest = c
            break
    
    if not chest:
        await callback.answer("❌ Здесь нет сундука!")
        return
    
    # Открываем сундук
    chest.opened = True
    loot, gold = generate_loot(chest.loot_table)
    player.gold += gold
    
    loot_text = []
    for item in loot:
        loot_text.append(f"{item['emoji']} {item['name']} x{item['amount']} - {item['value']}💰")
    
    # Обновляем сундук в локации
    for i, c in enumerate(location["chests"]):
        if c.position == player.position:
            location["chests"][i] = chest
            break
    
    LOCATIONS[player.current_location] = location
    
    await state.update_data(player=player)
    
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
        f"📌 Позиция: {player.position}/10"
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
    player = Player()
    await state.update_data(player=player)
    await show_location(message, state)

@dp.message(Command('ping'))
async def cmd_ping(message: types.Message):
    await message.answer("🏓 pong")

# ============= ЗАПУСК =============

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🏖️ Пляжное приключение запущено!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
