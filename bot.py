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

# ============= КЛАССЫ ДЛЯ БОЯ =============

class Weapon:
    def __init__(self, name, damage, accuracy, crit_chance, crit_multiplier, ammo, reload_time, aoe=False):
        self.name = name
        self.damage = damage  # (min, max)
        self.accuracy = accuracy  # 0-100%
        self.crit_chance = crit_chance  # 0-100%
        self.crit_multiplier = crit_multiplier  # x урона
        self.ammo = ammo  # текущие патроны
        self.max_ammo = ammo
        self.reload_time = reload_time  # сколько ходов на перезарядку
        self.reload_progress = 0
        self.aoe = aoe  # урон по площади

class Enemy:
    def __init__(self, name, hp, damage, accuracy, defense, count=1):
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.damage = damage  # (min, max)
        self.accuracy = accuracy
        self.defense = defense
        self.count = count  # количество врагов

class Player:
    def __init__(self):
        self.hp = 100
        self.max_hp = 100
        self.defense = 5
        self.weapons = {
            "pistol": Weapon("Пистолет", (8, 15), 90, 10, 2.0, 12, 1),
            "shotgun": Weapon("Дробовик", (15, 25), 70, 5, 1.5, 6, 2, aoe=True),
            "rifle": Weapon("Винтовка", (12, 20), 85, 15, 2.5, 8, 1),
            "smg": Weapon("ПП", (5, 10), 95, 8, 1.8, 30, 1)
        }
        self.current_weapon = "pistol"
        self.inventory = {"аптечка": 3, "бинт": 2}

# ============= СОСТОЯНИЯ БОЯ =============

class BattleState(StatesGroup):
    waiting_action = State()
    waiting_target = State()
    waiting_weapon = State()

# ============= ДАННЫЕ ДЛЯ ТЕСТА =============

# Таблица лута
LOOT_TABLE = {
    "крыса": [
        {"name": "Крысиный хвост", "rarity": "common", "value": 5, "emoji": "🐀", "chance": 70},
        {"name": "Гнилое мясо", "rarity": "common", "value": 3, "emoji": "🥩", "chance": 70},
        {"name": "Кусок шкуры", "rarity": "common", "value": 4, "emoji": "🧵", "chance": 60},
        {"name": "Маленький клык", "rarity": "rare", "value": 15, "emoji": "🦷", "chance": 20},
        {"name": "Крысиный король", "rarity": "epic", "value": 50, "emoji": "👑", "chance": 8},
        {"name": "Золотой зуб", "rarity": "legendary", "value": 200, "emoji": "💎", "chance": 2}
    ],
    "кабан": [
        {"name": "Кабаний клык", "rarity": "common", "value": 8, "emoji": "🐗", "chance": 70},
        {"name": "Жесткая шкура", "rarity": "common", "value": 7, "emoji": "🛡️", "chance": 65},
        {"name": "Свежее мясо", "rarity": "common", "value": 6, "emoji": "🍖", "chance": 75},
        {"name": "Кровь кабана", "rarity": "rare", "value": 20, "emoji": "🧪", "chance": 20},
        {"name": "Крепкая кость", "rarity": "epic", "value": 45, "emoji": "🦴", "chance": 8},
        {"name": "Бивень древнего кабана", "rarity": "legendary", "value": 300, "emoji": "💎", "chance": 2}
    ],
    "скелет": [
        {"name": "Ржавый меч", "rarity": "common", "value": 5, "emoji": "⚔️", "chance": 70},
        {"name": "Кости", "rarity": "common", "value": 3, "emoji": "🦴", "chance": 80},
        {"name": "Череп", "rarity": "rare", "value": 15, "emoji": "💀", "chance": 15},
        {"name": "Древний амулет", "rarity": "epic", "value": 80, "emoji": "📿", "chance": 5},
        {"name": "Проклятое кольцо", "rarity": "legendary", "value": 500, "emoji": "💍", "chance": 2}
    ]
}

# ============= БОЕВЫЕ ФУНКЦИИ =============

def calculate_damage(weapon, enemy_count=1, is_aoe=False):
    """Расчет урона с учетом всех факторов"""
    weapon_obj = weapon if isinstance(weapon, Weapon) else None
    
    if not weapon_obj:
        return {"damage": 0, "crit": False, "miss": True}
    
    # Проверка на попадание
    hit_roll = random.randint(1, 100)
    if hit_roll > weapon_obj.accuracy:
        return {"damage": 0, "crit": False, "miss": True}
    
    # Базовый урон
    damage = random.randint(weapon_obj.damage[0], weapon_obj.damage[1])
    
    # Проверка на крит
    crit = False
    crit_roll = random.randint(1, 100)
    if crit_roll <= weapon_obj.crit_chance:
        damage = int(damage * weapon_obj.crit_multiplier)
        crit = True
    
    # Урон по площади (уменьшается с количеством врагов)
    if is_aoe and weapon_obj.aoe and enemy_count > 1:
        damage = int(damage * (1.5 / enemy_count))  # Чем больше врагов, тем меньше каждому
    
    return {
        "damage": damage,
        "crit": crit,
        "miss": False
    }

def enemy_attack(enemy, player_defense):
    """Атака врага"""
    if random.randint(1, 100) > enemy.accuracy:
        return {"damage": 0, "miss": True}
    
    damage = random.randint(enemy.damage[0], enemy.damage[1])
    damage = max(1, damage - player_defense // 2)  # Защита уменьшает урон
    
    return {"damage": damage, "miss": False}

def reload_weapon(weapon):
    """Перезарядка оружия"""
    weapon.reload_progress += 1
    if weapon.reload_progress >= weapon.reload_time:
        weapon.ammo = weapon.max_ammo
        weapon.reload_progress = 0
        return True
    return False

# ============= ВАРИАНТ 1: ОДИНОЧНЫЙ БОЙ =============

async def start_single_battle(message: types.Message, state: FSMContext):
    """Начало одиночного боя"""
    player = Player()
    enemy = Enemy("Кабан", 80, (8, 15), 80, 3)
    
    await state.update_data(
        player=player,
        enemy=enemy,
        battle_type="single"
    )
    
    await show_battle_status(message, state)

async def show_battle_status(message: types.Message, state: FSMContext):
    """Показывает статус боя"""
    data = await state.get_data()
    player = data['player']
    enemy = data['enemy']
    weapon = player.weapons[player.current_weapon]
    
    status = (
        f"⚔️ **ОДИНОЧНЫЙ БОЙ**\n\n"
        f"👤 **Ты**\n"
        f"❤️ HP: {player.hp}/{player.max_hp}\n"
        f"🔫 {weapon.name}: {weapon.ammo}/{weapon.max_ammo} патр.\n"
        f"Шанс попадания: {weapon.accuracy}%\n"
        f"Крит: {weapon.crit_chance}% (x{weapon.crit_multiplier})\n\n"
        f"🐗 **{enemy.name}**\n"
        f"❤️ HP: {enemy.hp}/{enemy.max_hp}\n\n"
        f"Выбери действие:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔫 Стрелять", callback_data="single_shoot")],
        [InlineKeyboardButton(text="🔄 Сменить оружие", callback_data="single_change_weapon")],
        [InlineKeyboardButton(text="💊 Аптечка", callback_data="single_heal")],
        [InlineKeyboardButton(text="🔁 Перезарядка", callback_data="single_reload")],
        [InlineKeyboardButton(text="🏃 Убежать", callback_data="single_run")]
    ])
    
    await message.edit_text(status, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith('single_'))
async def single_battle_callback(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split('_')[1]
    data = await state.get_data()
    
    if not data:
        await callback.message.edit_text("❌ Бой не найден. Начни заново.")
        return
    
    player = data['player']
    enemy = data['enemy']
    weapon = player.weapons[player.current_weapon]
    
    result = []
    
    if action == "shoot":
        # Проверка патронов
        if weapon.ammo <= 0:
            result.append("❌ Патронов нет! Нужно перезарядиться.")
        else:
            weapon.ammo -= 1
            attack_result = calculate_damage(weapon, 1)
            
            if attack_result['miss']:
                result.append("😫 Промах!")
            else:
                damage = attack_result['damage']
                enemy.hp -= damage
                crit_text = "🔥 КРИТ! " if attack_result['crit'] else ""
                result.append(f"{crit_text}Попадание! {damage} урона.")
            
            # Контратака врага
            if enemy.hp > 0:
                enemy_attack_result = enemy_attack(enemy, player.defense)
                if enemy_attack_result['miss']:
                    result.append("🐗 Враг промахнулся.")
                else:
                    player.hp -= enemy_attack_result['damage']
                    result.append(f"🐗 Враг атакует: {enemy_attack_result['damage']} урона.")
    
    elif action == "reload":
        result.append(f"🔁 Перезарядка...")
        if reload_weapon(weapon):
            result.append(f"✅ Оружие перезаряжено! {weapon.max_ammo} патронов.")
    
    elif action == "heal":
        if player.inventory.get("аптечка", 0) > 0:
            heal = random.randint(20, 30)
            player.hp = min(player.max_hp, player.hp + heal)
            player.inventory["аптечка"] -= 1
            result.append(f"💊 Аптечка: +{heal} HP. Осталось: {player.inventory['аптечка']}")
        else:
            result.append("❌ Нет аптечек!")
    
    elif action == "change_weapon":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔫 Пистолет", callback_data="weapon_pistol")],
            [InlineKeyboardButton(text="🔫 Дробовик", callback_data="weapon_shotgun")],
            [InlineKeyboardButton(text="🔫 Винтовка", callback_data="weapon_rifle")],
            [InlineKeyboardButton(text="🔫 ПП", callback_data="weapon_smg")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="single_back")]
        ])
        await callback.message.edit_text("Выбери оружие:", reply_markup=keyboard)
        await callback.answer()
        return
    
    elif action == "run":
        if random.random() < 0.5:
            await callback.message.edit_text("🏃 Ты сбежал с поля боя!")
            await state.clear()
            await callback.answer()
            return
        else:
            result.append("❌ Не удалось сбежать!")
            # Контратака
            enemy_attack_result = enemy_attack(enemy, player.defense)
            player.hp -= enemy_attack_result['damage']
            result.append(f"🐗 Враг атакует в спину: {enemy_attack_result['damage']} урона.")
    
    # Проверка окончания боя
    if enemy.hp <= 0:
        await callback.message.edit_text(
            f"🎉 **ПОБЕДА!**\n\n" +
            "\n".join(result) +
            f"\n\nПолучено опыта: 50\n"
            f"💰 Найдено монет: {random.randint(20, 50)}"
        )
        await state.clear()
        await callback.answer()
        return
    
    if player.hp <= 0:
        await callback.message.edit_text("💀 **ТЫ ПОГИБ...**")
        await state.clear()
        await callback.answer()
        return
    
    # Обновляем состояние
    await state.update_data(player=player, enemy=enemy)
    
    # Показываем обновленный статус
    await show_battle_status(callback.message, state)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith('weapon_'))
async def change_weapon_callback(callback: types.CallbackQuery, state: FSMContext):
    weapon = callback.data.split('_')[1]
    data = await state.get_data()
    
    if data:
        player = data['player']
        player.current_weapon = weapon
        await state.update_data(player=player)
        
        await show_battle_status(callback.message, state)
    
    await callback.answer()

# ============= ВАРИАНТ 2: ГРУППОВОЙ БОЙ =============

async def start_group_battle(message: types.Message, state: FSMContext):
    """Начало группового боя"""
    player = Player()
    enemies = [
        Enemy("Крыса", 25, (3, 6), 70, 1, count=3),
        Enemy("Крыса", 25, (3, 6), 70, 1, count=2),
        Enemy("Кабан", 60, (8, 12), 75, 3, count=1)
    ]
    
    await state.update_data(
        player=player,
        enemies=enemies,
        battle_type="group",
        current_target=0
    )
    
    await show_group_battle_status(message, state)

async def show_group_battle_status(message: types.Message, state: FSMContext):
    """Показывает статус группового боя"""
    data = await state.get_data()
    player = data['player']
    enemies = data['enemies']
    weapon = player.weapons[player.current_weapon]
    
    # Формируем список врагов
    enemies_text = []
    for i, enemy in enumerate(enemies):
        if enemy.hp > 0:
            enemies_text.append(f"{i+1}. {enemy.name} (x{enemy.count}) ❤️ {enemy.hp}/{enemy.max_hp}")
    
    status = (
        f"⚔️ **ГРУППОВОЙ БОЙ**\n\n"
        f"👤 **Ты**\n"
        f"❤️ HP: {player.hp}/{player.max_hp}\n"
        f"🔫 {weapon.name}: {weapon.ammo}/{weapon.max_ammo} патр.\n\n"
        f"👥 **Враги**\n" + "\n".join(enemies_text) + "\n\n"
        f"Выбери цель:"
    )
    
    # Кнопки для выбора цели
    buttons = []
    for i, enemy in enumerate(enemies):
        if enemy.hp > 0:
            buttons.append([InlineKeyboardButton(
                text=f"{i+1}. {enemy.name} (x{enemy.count})",
                callback_data=f"group_target_{i}"
            )])
    
    # Кнопки действий
    buttons.append([
        InlineKeyboardButton(text="🔫 АоЕ выстрел", callback_data="group_aoe"),
        InlineKeyboardButton(text="🔄 Сменить оружие", callback_data="group_change_weapon"),
        InlineKeyboardButton(text="💊 Лечиться", callback_data="group_heal"),
        InlineKeyboardButton(text="🔁 Перезарядка", callback_data="group_reload")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.edit_text(status, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith('group_'))
async def group_battle_callback(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split('_')[1]
    data = await state.get_data()
    
    if not data:
        await callback.message.edit_text("❌ Бой не найден.")
        return
    
    player = data['player']
    enemies = data['enemies']
    weapon = player.weapons[player.current_weapon]
    
    result = []
    
    if action == "aoe":
        # АоЕ атака по всем врагам
        if weapon.ammo <= 0:
            result.append("❌ Нет патронов!")
        else:
            weapon.ammo -= 1
            total_damage = 0
            for enemy in enemies:
                if enemy.hp > 0:
                    attack_result = calculate_damage(weapon, len([e for e in enemies if e.hp > 0]), is_aoe=True)
                    if not attack_result['miss']:
                        damage = attack_result['damage']
                        enemy.hp -= damage * enemy.count
                        total_damage += damage
                        result.append(f"💥 {enemy.name}: {damage} урона (x{enemy.count})")
            
            result.insert(0, f"🔫 **АоЕ ВЫСТРЕЛ!** Всего урона: {total_damage}")
    
    elif action.startswith("target"):
        # Атака по конкретной цели
        target_idx = int(action.split('_')[1])
        target = enemies[target_idx]
        
        if weapon.ammo <= 0:
            result.append("❌ Нет патронов!")
        else:
            weapon.ammo -= 1
            attack_result = calculate_damage(weapon, 1)
            
            if attack_result['miss']:
                result.append(f"😫 Промах по {target.name}!")
            else:
                damage = attack_result['damage']
                target.hp -= damage
                crit_text = "🔥 КРИТ! " if attack_result['crit'] else ""
                result.append(f"{crit_text}{target.name}: {damage} урона")
    
    elif action == "heal":
        if player.inventory.get("аптечка", 0) > 0:
            heal = random.randint(20, 30)
            player.hp = min(player.max_hp, player.hp + heal)
            player.inventory["аптечка"] -= 1
            result.append(f"💊 Аптечка: +{heal} HP")
        else:
            result.append("❌ Нет аптечек!")
    
    elif action == "reload":
        result.append(f"🔁 Перезарядка...")
        if reload_weapon(weapon):
            result.append(f"✅ Оружие перезаряжено!")
    
    # Атака всех живых врагов
    alive_enemies = [e for e in enemies if e.hp > 0]
    enemy_damage_total = 0
    for enemy in alive_enemies:
        for _ in range(enemy.count):
            attack = enemy_attack(enemy, player.defense)
            if not attack['miss']:
                player.hp -= attack['damage']
                enemy_damage_total += attack['damage']
    
    if enemy_damage_total > 0:
        result.append(f"👥 Враги атакуют: всего {enemy_damage_total} урона")
    
    # Проверка окончания боя
    alive_enemies = [e for e in enemies if e.hp > 0]
    
    if not alive_enemies:
        # Генерация лута
        loot_result = generate_loot("группа")
        await callback.message.edit_text(
            f"🎉 **ПОБЕДА!**\n\n" +
            "\n".join(result) +
            f"\n\n{loot_result}"
        )
        await state.clear()
        await callback.answer()
        return
    
    if player.hp <= 0:
        await callback.message.edit_text("💀 **ТЫ ПОГИБ...**")
        await state.clear()
        await callback.answer()
        return
    
    # Обновляем состояние
    await state.update_data(player=player, enemies=enemies)
    
    # Показываем обновленный статус
    await show_group_battle_status(callback.message, state)
    await callback.answer()

# ============= ВАРИАНТ 3: ДЕМО ЛУТА =============

def generate_loot(monster_type):
    """Генерирует лут для демонстрации"""
    if monster_type == "группа":
        monster_type = random.choice(["крыса", "кабан", "скелет"])
    
    items = LOOT_TABLE.get(monster_type, LOOT_TABLE["крыса"])
    
    # Симуляция выпадения
    loot = []
    total_value = 0
    
    for item in items:
        if random.randint(1, 100) <= item["chance"]:
            loot.append(item)
            total_value += item["value"]
    
    if not loot:
        common = [i for i in items if i["rarity"] == "common"]
        if common:
            item = random.choice(common)
            loot.append(item)
            total_value += item["value"]
    
    # Цвета редкости
    rarity_colors = {
        "common": "🟢 Обычный",
        "rare": "🔵 Редкий",
        "epic": "🟣 Эпический",
        "legendary": "🟠 Легендарный"
    }
    
    loot_text = []
    for item in loot:
        loot_text.append(f"{item['emoji']} **{item['name']}** - {rarity_colors[item['rarity']]} +{item['value']}💰")
    
    return (
        f"🎒 **ДОБЫЧА**\n" +
        "\n".join(loot_text) +
        f"\n\n💰 Всего: {total_value} монет"
    )

@dp.message(Command('loot'))
async def cmd_loot(message: types.Message):
    """Демонстрация лута"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🐀 Крыса", callback_data="loot_rat")],
        [InlineKeyboardButton(text="🐗 Кабан", callback_data="loot_boar")],
        [InlineKeyboardButton(text="💀 Скелет", callback_data="loot_skeleton")],
        [InlineKeyboardButton(text="🎲 Рандом", callback_data="loot_random")]
    ])
    
    await message.answer(
        "🎒 **ДЕМОНСТРАЦИЯ ЛУТА**\n\n"
        "Выбери монстра для проверки дропа:",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data.startswith('loot_'))
async def loot_callback(callback: types.CallbackQuery):
    monster = callback.data.split('_')[1]
    
    monster_map = {
        "rat": "крыса",
        "boar": "кабан",
        "skeleton": "скелет",
        "random": random.choice(["крыса", "кабан", "скелет"])
    }
    
    monster_type = monster_map.get(monster, "крыса")
    result = generate_loot(monster_type)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Еще раз", callback_data=f"loot_{monster}")],
        [InlineKeyboardButton(text="◀ В меню", callback_data="back_to_loot")]
    ])
    
    await callback.message.edit_text(
        f"📦 **Лут с {monster_type.upper()}**\n\n{result}",
        reply_markup=keyboard
    )
    await callback.answer()

# ============= ГЛАВНОЕ МЕНЮ =============

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    """Главное меню"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Одиночный бой", callback_data="menu_single")],
        [InlineKeyboardButton(text="👥 Групповой бой", callback_data="menu_group")],
        [InlineKeyboardButton(text="🎒 Демо лута", callback_data="menu_loot")]
    ])
    
    await message.answer(
        "⚔️ **ARPG БОЕВАЯ СИСТЕМА** ⚔️\n\n"
        "Выбери режим для тестирования:\n\n"
        "• **Одиночный бой** - классический 1 на 1\n"
        "• **Групповой бой** - против нескольких врагов\n"
        "• **Демо лута** - система выпадения предметов\n\n"
        "В бою доступны:\n"
        "✅ Шанс попадания\n"
        "✅ Критические удары\n"
        "✅ Перезарядка оружия\n"
        "✅ Урон по площади\n"
        "✅ Разное оружие",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data.startswith('menu_'))
async def menu_callback(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split('_')[1]
    
    if action == "single":
        await start_single_battle(callback.message, state)
    elif action == "group":
        await start_group_battle(callback.message, state)
    elif action == "loot":
        await cmd_loot(callback.message)
    
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_loot")
async def back_to_loot(callback: types.CallbackQuery):
    await cmd_loot(callback.message)
    await callback.answer()

@dp.message(Command('ping'))
async def cmd_ping(message: types.Message):
    await message.answer("🏓 pong")

# ============= ЗАПУСК =============

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🚀 ARPG Бот запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
