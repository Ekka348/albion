import asyncio
import logging
import random
import json
import os
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

# ============= ДАННЫЕ ДЛЯ ТЕСТА =============

class LootItem:
    def __init__(self, name, rarity, value, emoji):
        self.name = name
        self.rarity = rarity  # common, rare, epic, legendary
        self.value = value
        self.emoji = emoji

# Таблица лута
LOOT_TABLE = {
    "крыса": [
        LootItem("Крысиный хвост", "common", 5, "🐀"),
        LootItem("Гнилое мясо", "common", 3, "🥩"),
        LootItem("Кусок шкуры", "common", 4, "🧵"),
        LootItem("Маленький клык", "rare", 15, "🦷"),
        LootItem("Крысиный король (арт)", "epic", 50, "👑"),
    ],
    "кабан": [
        LootItem("Кабаний клык", "common", 8, "🐗"),
        LootItem("Жесткая шкура", "common", 7, "🛡️"),
        LootItem("Свежее мясо", "common", 6, "🍖"),
        LootItem("Кровь кабана", "rare", 20, "🧪"),
        LootItem("Бивень древнего кабана", "legendary", 200, "💎"),
    ],
    "скелет": [
        LootItem("Ржавый меч", "common", 5, "⚔️"),
        LootItem("Кости", "common", 3, "🦴"),
        LootItem("Череп", "rare", 15, "💀"),
        LootItem("Древний амулет", "epic", 80, "📿"),
        LootItem("Проклятое кольцо", "legendary", 300, "💍"),
    ]
}

# ============= ВАРИАНТ 1: Классический пошаговый =============

async def demo_classic_battle(message: types.Message):
    """Показывает классический пошаговый бой"""
    
    hp = {"player": 50, "monster": 45}
    
    battle_msg = await message.answer(
        "⚔️ **КЛАССИЧЕСКИЙ БОЙ**\n"
        "Выбирай часть тела для атаки!\n\n"
        f"👤 Ты: ❤️ {hp['player']} HP\n"
        f"🐗 Кабан: ❤️ {hp['monster']} HP",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤜 Голова", callback_data="demo_classic_head")],
            [InlineKeyboardButton(text="🤛 Грудь", callback_data="demo_classic_chest")],
            [InlineKeyboardButton(text="👊 Живот", callback_data="demo_classic_body")],
            [InlineKeyboardButton(text="🦵 Ноги", callback_data="demo_classic_legs")],
        ])
    )
    
    return battle_msg

@dp.callback_query(lambda c: c.data.startswith('demo_classic_'))
async def demo_classic_callback(callback: types.CallbackQuery):
    part = callback.data.split('_')[2]
    
    # Урон игрока (10-20)
    player_damage = random.randint(10, 20)
    # Урон монстра (5-15)
    monster_damage = random.randint(5, 15)
    
    # Шанс крита (20%)
    if random.random() < 0.2:
        player_damage = int(player_damage * 1.5)
        crit_text = "🔥 КРИТ!"
    else:
        crit_text = ""
    
    # Результат
    await callback.message.edit_text(
        f"⚔️ **КЛАССИЧЕСКИЙ БОЙ**\n\n"
        f"Ты ударил в {part}!\n"
        f"Урон: {player_damage} {crit_text}\n"
        f"🐗 Кабан ответил: {monster_damage} урона\n\n"
        f"👤 Ты: ❤️ {50 - monster_damage} HP\n"
        f"🐗 Кабан: ❤️ {45 - player_damage} HP\n\n"
        f"_[Это одно сообщение, новые не создаются]_"
    )
    
    await callback.answer()

# ============= ВАРИАНТ 2: Авто-бой с выбором стратегии =============

async def demo_autobattle(message: types.Message):
    """Показывает авто-бой с выбором стратегии"""
    
    await message.answer(
        "⚔️ **АВТО-БОЙ**\n"
        "В подземелье 5 крыс. Выбери тактику:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤺 Агрессивная (+50% урона, +50% получ. урона)", callback_data="demo_auto_aggro")],
            [InlineKeyboardButton(text="🛡️ Осторожная (-50% получ. урона, -30% урона)", callback_data="demo_auto_def")],
            [InlineKeyboardButton(text="🎯 Фокус (убивает по одному)", callback_data="demo_auto_focus")],
        ])
    )

@dp.callback_query(lambda c: c.data.startswith('demo_auto_'))
async def demo_auto_callback(callback: types.CallbackQuery):
    tactic = callback.data.split('_')[2]
    
    results = {
        "aggro": {
            "kills": random.randint(4, 5),
            "damage": random.randint(40, 60),
            "loot": random.randint(5, 10),
            "text": "🤺 Ты безрассудно атаковал! Быстро, но больно."
        },
        "def": {
            "kills": random.randint(2, 4),
            "damage": random.randint(10, 25),
            "loot": random.randint(3, 7),
            "text": "🛡️ Ты действовал осторожно. Мало урона, но цел."
        },
        "focus": {
            "kills": random.randint(3, 5),
            "damage": random.randint(20, 35),
            "loot": random.randint(4, 9),
            "text": "🎯 Ты методично убивал крыс одну за другой."
        }
    }
    
    r = results[tactic]
    
    await callback.message.edit_text(
        f"⚔️ **РЕЗУЛЬТАТ АВТО-БОЯ**\n\n"
        f"{r['text']}\n\n"
        f"📊 **Итоги:**\n"
        f"• Убито крыс: {r['kills']}/5\n"
        f"• Получено урона: {r['damage']} HP\n"
        f"• Найдено предметов: {r['loot']} 🎒\n\n"
        f"_[ВСЁ в одном сообщении! Никакого спама]_"
    )
    
    await callback.answer()

# ============= ВАРИАНТ 3: Несколько врагов с группировкой =============

async def demo_group_battle(message: types.Message):
    """Показывает бой с несколькими врагами"""
    
    battle_msg = await message.answer(
        "⚔️ **ГРУППОВОЙ БОЙ**\n"
        "🐀 3 Крысы | 🐀 2 Крысы | 🐗 1 Кабан\n\n"
        "👤 Ты: ❤️ 100/100 HP\n\n"
        "Выбери цель:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🐀 Крыса (3 шт)", callback_data="demo_group_rats")],
            [InlineKeyboardButton(text="🐗 Кабан (1 шт)", callback_data="demo_group_boar")],
            [InlineKeyboardButton(text="⚡ АоЕ атака", callback_data="demo_group_aoe")],
        ])
    )
    
    return battle_msg

@dp.callback_query(lambda c: c.data.startswith('demo_group_'))
async def demo_group_callback(callback: types.CallbackQuery):
    target = callback.data.split('_')[2]
    
    if target == "rats":
        # Убивает одну крысу
        await callback.message.edit_text(
            "⚔️ **ГРУППОВОЙ БОЙ**\n\n"
            "Ты атаковал крыс!\n"
            "🐀 Крыса получает 25 урона!\n"
            "🐀 Крыса погибает!\n\n"
            "🐀 Осталось: 2 крысы | 🐗 1 кабан\n\n"
            "🐀 Крысы контратакуют:\n"
            "• Крыса 1: укус - 5 HP\n"
            "• Крыса 2: укус - 7 HP\n"
            "ВСЕГО: 12 HP урона\n\n"
            "👤 Ты: ❤️ 88/100 HP\n"
            "_Группировка урона: одно число вместо двух сообщений_"
        )
    elif target == "boar":
        await callback.message.edit_text(
            "⚔️ **ГРУППОВОЙ БОЙ**\n\n"
            "Ты атаковал кабана!\n"
            "🐗 Кабан получает 18 урона!\n\n"
            "🐗 Кабан в ярости топает!\n"
            "🐀 2 крысы присоединяются к атаке!\n\n"
            "🐗 Кабан: удар - 12 HP\n"
            "🐀 Крысы: укусы - 8 HP\n"
            "ВСЕГО: 20 HP урона\n\n"
            "👤 Ты: ❤️ 80/100 HP\n"
            "_Враги атакуют группой_"
        )
    else:  # aoe
        await callback.message.edit_text(
            "⚔️ **ГРУППОВОЙ БОЙ**\n\n"
            "💥 Ты используесть Взрыв!\n"
            "Урон по всем:\n"
            "• Крысы: 15 урона каждой\n"
            "• Кабан: 10 урона\n\n"
            "Результат:\n"
            "🐀 2 крысы погибли!\n"
            "🐗 Кабан: ❤️ 40/50 HP\n"
            "🐀 Осталась 1 крыса: ❤️ 10/25 HP\n\n"
            "🐗 Кабан и крыса контратакуют:\n"
            "Совместная атака: 18 HP урона\n\n"
            "👤 Ты: ❤️ 82/100 HP\n"
            "_Всё в одном сообщении!_"
        )
    
    await callback.answer()

# ============= ВАРИАНТ 4: Очки действий (Action Points) =============

async def demo_ap_battle(message: types.Message):
    """Показывает бой с очками действий"""
    
    await message.answer(
        "⚔️ **СИСТЕМА ОЧКОВ ДЕЙСТВИЙ (AP)**\n"
        "🐗 Кабан (50 HP) | 🐀 Крыса (30 HP) | 🐀 Крыса (25 HP)\n\n"
        "Твои ОД: 3/3\n\n"
        "Выбери действие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Удар (1 ОД) - 10-15 урона", callback_data="demo_ap_attack")],
            [InlineKeyboardButton(text="💥 Сильный удар (2 ОД) - 20-30 урона", callback_data="demo_ap_heavy")],
            [InlineKeyboardButton(text="🛡️ Защита (1 ОД) - -50% урона в этом ходу", callback_data="demo_ap_defend")],
            [InlineKeyboardButton(text="⚡ Ураган (3 ОД) - атака по всем", callback_data="demo_ap_aoe")],
        ])
    )

@dp.callback_query(lambda c: c.data.startswith('demo_ap_'))
async def demo_ap_callback(callback: types.CallbackQuery):
    action = callback.data.split('_')[2]
    
    results = {
        "attack": {
            "damage": random.randint(10, 15),
            "target": "кабана",
            "ap": 1,
            "text": "Ты ударил кабана!"
        },
        "heavy": {
            "damage": random.randint(20, 30),
            "target": "кабана",
            "ap": 2,
            "text": "💥 МОЩНЫЙ УДАР!"
        },
        "defend": {
            "damage": random.randint(5, 10),
            "target": "себя",
            "ap": 1,
            "text": "🛡️ Ты встал в защитную стойку"
        },
        "aoe": {
            "damage": 15,
            "target": "всех",
            "ap": 3,
            "text": "⚡ ВИХРЬ КЛИНКОВ!"
        }
    }
    
    r = results[action]
    
    # Считаем урон от врагов
    enemy_damage = random.randint(8, 12) if action != "defend" else random.randint(3, 6)
    
    await callback.message.edit_text(
        f"⚔️ **ОЧКИ ДЕЙСТВИЙ**\n\n"
        f"{r['text']}\n"
        f"Урон по {r['target']}: {r['damage']} HP\n"
        f"Потрачено ОД: {r['ap']}\n\n"
        f"🐗 Враги контратакуют:\n"
        f"Нанесено урона: {enemy_damage} HP\n\n"
        f"👤 Осталось ОД: {3 - r['ap']}/3\n"
        f"👤 Ты: ❤️ {100 - enemy_damage} HP\n\n"
        f"_[Можно сделать несколько действий за ход, тратя ОД]_"
    )
    
    await callback.answer()

# ============= ДЕМО ЛУТА =============

async def demo_loot(message: types.Message):
    """Показывает разные варианты выпадения лута"""
    
    await message.answer(
        "🎒 **ДЕМОНСТРАЦИЯ ЛУТА**\n\n"
        "Выбери монстра:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🐀 Крыса", callback_data="demo_loot_rat")],
            [InlineKeyboardButton(text="🐗 Кабан", callback_data="demo_loot_boar")],
            [InlineKeyboardButton(text="💀 Скелет", callback_data="demo_loot_skeleton")],
            [InlineKeyboardButton(text="🎲 Рандомный лут", callback_data="demo_loot_random")],
        ])
    )

@dp.callback_query(lambda c: c.data.startswith('demo_loot_'))
async def demo_loot_callback(callback: types.CallbackQuery):
    monster = callback.data.split('_')[2]
    
    if monster == "random":
        monster = random.choice(["крыса", "кабан", "скелет"])
    
    # Выбор случайного лута
    items = LOOT_TABLE[monster]
    
    # 70% шанс получить 1 предмет, 20% - 2, 10% - 3
    count = random.choices([1, 2, 3], weights=[70, 20, 10])[0]
    
    # Выбираем предметы
    loot = random.sample(items, min(count, len(items)))
    
    # Форматируем результат
    loot_text = []
    for item in loot:
        rarity_color = {
            "common": "обычный",
            "rare": "🔵 редкий",
            "epic": "🟣 эпический",
            "legendary": "🟠 легендарный"
        }
        loot_text.append(f"{item.emoji} {item.name} [{rarity_color[item.rarity]}] +{item.value}💰")
    
    total_value = sum(item.value for item in loot)
    
    # Проверка на редкий дроп (10% шанс)
    rare_drop = random.random() < 0.1
    if rare_drop and monster == "крыса":
        loot_text.append("👑 **Крысиный король** [🔴 уникальный] +500💰")
        total_value += 500
    
    await callback.message.edit_text(
        f"🎒 **ЛУТ С {monster.upper()}**\n\n"
        f"Найдено предметов: {len(loot_text)}\n\n" +
        "\n".join(loot_text) +
        f"\n\n💰 Общая стоимость: {total_value} монет\n"
        f"💎 Шанс редкой находки: 10%\n"
        f"_[Система редкости: обычный → 🔵 редкий → 🟣 эпический → 🟠 легендарный]_"
    )
    
    await callback.answer()

# ============= ГЛАВНОЕ МЕНЮ =============

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    """Главное меню тестового бота"""
    
    await message.answer(
        "⚔️ **ARPG ДЕМОНСТРАЦИЯ** ⚔️\n\n"
        "Я покажу тебе 4 варианта боя и систему лута.\n"
        "Нажимай на кнопки и смотри, как выглядит каждый вариант!\n\n"
        "**Проблема:** обычный бой = тонна текста\n"
        "**Решение:** разные подходы к компактности\n\n"
        "👇 Выбери вариант:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ 1. Классический (угадай часть тела)", callback_data="demo_classic")],
            [InlineKeyboardButton(text="🤺 2. Авто-бой (стратегия + итог)", callback_data="demo_auto")],
            [InlineKeyboardButton(text="🐀 3. Групповой бой (5+ врагов)", callback_data="demo_group")],
            [InlineKeyboardButton(text="⚡ 4. Очки действий (AP система)", callback_data="demo_ap")],
            [InlineKeyboardButton(text="🎒 5. ДЕМО ЛУТА", callback_data="demo_loot_menu")],
        ])
    )

@dp.callback_query(lambda c: c.data == "demo_classic")
async def demo_classic_menu(callback: types.CallbackQuery):
    await demo_classic_battle(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "demo_auto")
async def demo_auto_menu(callback: types.CallbackQuery):
    await demo_autobattle(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "demo_group")
async def demo_group_menu(callback: types.CallbackQuery):
    await demo_group_battle(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "demo_ap")
async def demo_ap_menu(callback: types.CallbackQuery):
    await demo_ap_battle(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "demo_loot_menu")
async def demo_loot_menu(callback: types.CallbackQuery):
    await demo_loot(callback.message)
    await callback.answer()

@dp.message(Command('ping'))
async def cmd_ping(message: types.Message):
    await message.answer("🏓 pong")

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🚀 Тестовый бот ARPG запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
