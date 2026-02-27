import asyncio
import logging
import random
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from enum import Enum

# ============= НАСТРОЙКИ =============
API_TOKEN = os.getenv('BOT_TOKEN', '8404262144:AAFhLqVbU4FpIrM6KWfU6u9L1l5Qh-FYLWk')
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ============= ТИПЫ ПРЕДМЕТОВ =============

class ItemRarity(Enum):
    NORMAL = "normal"
    MAGIC = "magic"
    RARE = "rare"
    UNIQUE = "unique"

class ItemType(Enum):
    WEAPON = "weapon"
    HELMET = "helmet"
    ARMOR = "armor"
    GLOVES = "gloves"
    BOOTS = "boots"
    BELT = "belt"
    RING = "ring"
    AMULET = "amulet"
    FLASK = "flask"

class AffixType(Enum):
    PREFIX = "prefix"
    SUFFIX = "suffix"

# ============= ТИПЫ ОРУЖИЯ =============

class WeaponType(Enum):
    # Одноручное оружие
    ONE_HAND_SWORD = "one_hand_sword"        # Одноручный меч
    THRUSTING_SWORD = "thrusting_sword"      # Рапира/шпага
    ONE_HAND_AXE = "one_hand_axe"            # Одноручный топор
    ONE_HAND_MACE = "one_hand_mace"          # Одноручная булава
    CLAW = "claw"                            # Коготь
    DAGGER = "dagger"                         # Кинжал
    SCEPTRE = "sceptre"                       # Скипетр
    
    # Двуручное оружие
    TWO_HAND_SWORD = "two_hand_sword"         # Двуручный меч
    TWO_HAND_AXE = "two_hand_axe"             # Двуручный топор
    TWO_HAND_MACE = "two_hand_mace"           # Двуручная булава/молот
    STAFF = "staff"                            # Посох
    QUARTERSTAFF = "quarterstaff"              # Шест/боевой посох
    
    # Новые типы из PoE2
    SPEAR = "spear"                            # Копье
    FLAIL = "flail"                            # Цеп/кистень

# ============= АФФИКСЫ (МОДИФИКАТОРЫ) =============

PREFIXES = {
    # Оружие
    "weapon_damage": {"name": "Закаленное", "stat": "damage", "value": (5, 10), "tier": 1},
    "weapon_damage2": {"name": "Острое", "stat": "damage", "value": (10, 15), "tier": 2},
    "weapon_damage3": {"name": "Убийственное", "stat": "damage", "value": (15, 25), "tier": 3},
    "weapon_damage4": {"name": "Безжалостное", "stat": "damage", "value": (20, 35), "tier": 4},
    "weapon_damage5": {"name": "Смертоносное", "stat": "damage", "value": (30, 50), "tier": 5},
    
    # Здоровье
    "health": {"name": "Здоровое", "stat": "max_hp", "value": (10, 20), "tier": 1},
    "health2": {"name": "Крепкое", "stat": "max_hp", "value": (20, 35), "tier": 2},
    "health3": {"name": "Могучая", "stat": "max_hp", "value": (35, 50), "tier": 3},
    "health4": {"name": "Титаническое", "stat": "max_hp", "value": (50, 75), "tier": 4},
    "health5": {"name": "Бессмертное", "stat": "max_hp", "value": (75, 100), "tier": 5},
    
    # Защита
    "defense": {"name": "Прочное", "stat": "defense", "value": (3, 6), "tier": 1},
    "defense2": {"name": "Твердое", "stat": "defense", "value": (6, 10), "tier": 2},
    "defense3": {"name": "Несокрушимое", "stat": "defense", "value": (10, 15), "tier": 3},
    "defense4": {"name": "Адамантитовое", "stat": "defense", "value": (15, 22), "tier": 4},
    "defense5": {"name": "Божественное", "stat": "defense", "value": (20, 30), "tier": 5},
    
    # Скорость атаки
    "attack_speed": {"name": "Быстрое", "stat": "attack_speed", "value": (5, 10), "tier": 1},
    "attack_speed2": {"name": "Проворное", "stat": "attack_speed", "value": (10, 15), "tier": 2},
    "attack_speed3": {"name": "Вихревое", "stat": "attack_speed", "value": (15, 22), "tier": 3},
    "attack_speed4": {"name": "Неудержимое", "stat": "attack_speed", "value": (20, 30), "tier": 4},
    "attack_speed5": {"name": "Молниеносное", "stat": "attack_speed", "value": (25, 40), "tier": 5},
    
    # Точность
    "accuracy": {"name": "Точное", "stat": "accuracy", "value": (5, 10), "tier": 1},
    "accuracy2": {"name": "Меткое", "stat": "accuracy", "value": (10, 16), "tier": 2},
    "accuracy3": {"name": "Снайперское", "stat": "accuracy", "value": (16, 24), "tier": 3},
    "accuracy4": {"name": "Непревзойденное", "stat": "accuracy", "value": (20, 35), "tier": 4},
    "accuracy5": {"name": "Абсолютное", "stat": "accuracy", "value": (30, 50), "tier": 5},
}

SUFFIXES = {
    # Шанс крита
    "crit_chance": {"name": "Удачи", "stat": "crit_chance", "value": (3, 6), "tier": 1},
    "crit_chance2": {"name": "Везучего", "stat": "crit_chance", "value": (6, 10), "tier": 2},
    "crit_chance3": {"name": "Рока", "stat": "crit_chance", "value": (10, 15), "tier": 3},
    "crit_chance4": {"name": "Судьбы", "stat": "crit_chance", "value": (12, 20), "tier": 4},
    "crit_chance5": {"name": "Провидения", "stat": "crit_chance", "value": (15, 25), "tier": 5},
    
    # Множитель крита
    "crit_mult": {"name": "Боли", "stat": "crit_multiplier", "value": (10, 20), "tier": 1},
    "crit_mult2": {"name": "Агонии", "stat": "crit_multiplier", "value": (20, 30), "tier": 2},
    "crit_mult3": {"name": "Экзекуции", "stat": "crit_multiplier", "value": (30, 45), "tier": 3},
    "crit_mult4": {"name": "Мученичества", "stat": "crit_multiplier", "value": (40, 60), "tier": 4},
    "crit_mult5": {"name": "Апокалипсиса", "stat": "crit_multiplier", "value": (50, 80), "tier": 5},
    
    # Регенерация
    "life_regen": {"name": "Жизни", "stat": "life_regen", "value": (2, 4), "tier": 1},
    "life_regen2": {"name": "Возрождения", "stat": "life_regen", "value": (4, 7), "tier": 2},
    "life_regen3": {"name": "Бессмертия", "stat": "life_regen", "value": (7, 11), "tier": 3},
    "life_regen4": {"name": "Вечности", "stat": "life_regen", "value": (10, 15), "tier": 4},
    "life_regen5": {"name": "Феникса", "stat": "life_regen", "value": (12, 20), "tier": 5},
    
    # Вампиризм
    "life_leech": {"name": "Вампира", "stat": "life_on_hit", "value": (2, 5), "tier": 1},
    "life_leech2": {"name": "Кровопийцы", "stat": "life_on_hit", "value": (4, 8), "tier": 2},
    "life_leech3": {"name": "Носферату", "stat": "life_on_hit", "value": (6, 12), "tier": 3},
    "life_leech4": {"name": "Графа Дракулы", "stat": "life_on_hit", "value": (8, 16), "tier": 4},
    "life_leech5": {"name": "Бога Крови", "stat": "life_on_hit", "value": (10, 20), "tier": 5},
    
    # Оглушение
    "stun": {"name": "Грома", "stat": "stun_multiplier", "value": (10, 20), "tier": 1},
    "stun2": {"name": "Землетрясения", "stat": "stun_multiplier", "value": (15, 30), "tier": 2},
    "stun3": {"name": "Разрушителя", "stat": "stun_multiplier", "value": (20, 40), "tier": 3},
}

# ============= БАЗОВЫЕ ХАРАКТЕРИСТИКИ ОРУЖИЯ =============

WEAPON_BASES = {
    # ============= ОДНОРУЧНЫЕ МЕЧИ =============
    "rusted_sword": {
        "name": "Ржавый меч",
        "emoji": "⚔️",
        "damage_range": (4, 8),
        "attack_speed": 1.5,
        "crit_chance": 5,
        "accuracy": 20,
        "requirements": {"str": 10, "dex": 10},
        "tier": 1,
        "type": WeaponType.ONE_HAND_SWORD
    },
    "copper_sword": {
        "name": "Медный меч",
        "emoji": "⚔️",
        "damage_range": (6, 12),
        "attack_speed": 1.45,
        "crit_chance": 5,
        "accuracy": 25,
        "requirements": {"str": 20, "dex": 20},
        "tier": 2,
        "type": WeaponType.ONE_HAND_SWORD
    },
    "saber": {
        "name": "Сабля",
        "emoji": "⚔️",
        "damage_range": (8, 16),
        "attack_speed": 1.5,
        "crit_chance": 5,
        "accuracy": 30,
        "requirements": {"str": 30, "dex": 40},
        "tier": 3,
        "type": WeaponType.ONE_HAND_SWORD
    },
    "broad_sword": {
        "name": "Широкий меч",
        "emoji": "⚔️",
        "damage_range": (12, 22),
        "attack_speed": 1.35,
        "crit_chance": 5,
        "accuracy": 35,
        "requirements": {"str": 50, "dex": 35},
        "tier": 4,
        "type": WeaponType.ONE_HAND_SWORD
    },
    "war_sword": {
        "name": "Воинский меч",
        "emoji": "⚔️",
        "damage_range": (15, 28),
        "attack_speed": 1.4,
        "crit_chance": 5,
        "accuracy": 40,
        "requirements": {"str": 68, "dex": 51},
        "tier": 5,
        "type": WeaponType.ONE_HAND_SWORD
    },
    "ancient_sword": {
        "name": "Древний меч",
        "emoji": "⚔️",
        "damage_range": (18, 32),
        "attack_speed": 1.38,
        "crit_chance": 5.5,
        "accuracy": 45,
        "requirements": {"str": 80, "dex": 60},
        "tier": 6,
        "type": WeaponType.ONE_HAND_SWORD
    },
    "elegant_sword": {
        "name": "Элегантный меч",
        "emoji": "⚔️",
        "damage_range": (22, 38),
        "attack_speed": 1.45,
        "crit_chance": 6,
        "accuracy": 50,
        "requirements": {"str": 95, "dex": 85},
        "tier": 7,
        "type": WeaponType.ONE_HAND_SWORD
    },
    "twilight_blade": {
        "name": "Закатный клинок",
        "emoji": "⚔️",
        "damage_range": (26, 44),
        "attack_speed": 1.42,
        "crit_chance": 6.5,
        "accuracy": 55,
        "requirements": {"str": 115, "dex": 100},
        "tier": 8,
        "type": WeaponType.ONE_HAND_SWORD
    },
    "gem_sword": {
        "name": "Самоцветный меч",
        "emoji": "⚔️",
        "damage_range": (30, 50),
        "attack_speed": 1.4,
        "crit_chance": 7,
        "accuracy": 60,
        "requirements": {"str": 135, "dex": 115},
        "tier": 9,
        "type": WeaponType.ONE_HAND_SWORD
    },
    "eternal_sword": {
        "name": "Меч вечного",
        "emoji": "⚔️✨",
        "damage_range": (35, 58),
        "attack_speed": 1.45,
        "crit_chance": 7.5,
        "accuracy": 70,
        "requirements": {"str": 158, "dex": 132},
        "tier": 10,
        "type": WeaponType.ONE_HAND_SWORD
    },
    
    # ============= ШПАГИ/РАПИРЫ =============
    "pirate_cutlass": {
        "name": "Пиратский тесак",
        "emoji": "⚔️",
        "damage_range": (10, 20),
        "attack_speed": 1.55,
        "crit_chance": 6,
        "accuracy": 45,
        "requirements": {"dex": 62},
        "implicit": "15% шанс кровотечения",
        "tier": 4,
        "type": WeaponType.THRUSTING_SWORD
    },
    "gladius": {
        "name": "Гладиус",
        "emoji": "⚔️",
        "damage_range": (14, 26),
        "attack_speed": 1.5,
        "crit_chance": 6.5,
        "accuracy": 50,
        "requirements": {"dex": 86},
        "implicit": "20% шанс кровотечения",
        "tier": 6,
        "type": WeaponType.THRUSTING_SWORD
    },
    "estoc": {
        "name": "Эсток",
        "emoji": "⚔️",
        "damage_range": (20, 34),
        "attack_speed": 1.48,
        "crit_chance": 7,
        "accuracy": 55,
        "requirements": {"dex": 104},
        "implicit": "+30% множитель крита",
        "tier": 8,
        "type": WeaponType.THRUSTING_SWORD
    },
    "tiger_hook": {
        "name": "Тигровый крюк",
        "emoji": "⚔️",
        "damage_range": (28, 46),
        "attack_speed": 1.52,
        "crit_chance": 7.5,
        "accuracy": 60,
        "requirements": {"dex": 142},
        "implicit": "25% шанс кровотечения",
        "tier": 10,
        "type": WeaponType.THRUSTING_SWORD
    },
    
    # ============= ОДНОРУЧНЫЕ ТОПОРЫ =============
    "rusty_hatchet": {
        "name": "Ржавый топорик",
        "emoji": "🪓",
        "damage_range": (5, 10),
        "attack_speed": 1.35,
        "crit_chance": 5,
        "requirements": {"str": 16, "dex": 10},
        "tier": 1,
        "type": WeaponType.ONE_HAND_AXE
    },
    "jade_axe": {
        "name": "Нефритовый топор",
        "emoji": "🪓",
        "damage_range": (8, 16),
        "attack_speed": 1.32,
        "crit_chance": 5,
        "requirements": {"str": 29, "dex": 17},
        "tier": 2,
        "type": WeaponType.ONE_HAND_AXE
    },
    "boarding_axe": {
        "name": "Абордажный топор",
        "emoji": "🪓",
        "damage_range": (12, 22),
        "attack_speed": 1.3,
        "crit_chance": 5,
        "requirements": {"str": 45, "dex": 26},
        "tier": 3,
        "type": WeaponType.ONE_HAND_AXE
    },
    "cleaver": {
        "name": "Секач",
        "emoji": "🪓",
        "damage_range": (16, 28),
        "attack_speed": 1.28,
        "crit_chance": 5,
        "requirements": {"str": 62, "dex": 35},
        "tier": 4,
        "type": WeaponType.ONE_HAND_AXE
    },
    "carpenter_axe": {
        "name": "Плотничий топор",
        "emoji": "🪓",
        "damage_range": (20, 34),
        "attack_speed": 1.3,
        "crit_chance": 5,
        "requirements": {"str": 80, "dex": 45},
        "tier": 5,
        "type": WeaponType.ONE_HAND_AXE
    },
    "battle_axe": {
        "name": "Боевой топор",
        "emoji": "🪓",
        "damage_range": (25, 42),
        "attack_speed": 1.25,
        "crit_chance": 5.5,
        "requirements": {"str": 98, "dex": 54},
        "tier": 6,
        "type": WeaponType.ONE_HAND_AXE
    },
    "decorative_axe": {
        "name": "Украшенный топор",
        "emoji": "🪓",
        "damage_range": (27, 50),
        "attack_speed": 1.2,
        "crit_chance": 5,
        "requirements": {"str": 80, "dex": 23},
        "tier": 7,
        "type": WeaponType.ONE_HAND_AXE
    },
    "savage_axe": {
        "name": "Жестокий топор",
        "emoji": "🪓",
        "damage_range": (35, 58),
        "attack_speed": 1.22,
        "crit_chance": 5.5,
        "requirements": {"str": 125, "dex": 70},
        "tier": 8,
        "type": WeaponType.ONE_HAND_AXE
    },
    "ghost_axe": {
        "name": "Призрачный топор",
        "emoji": "🪓👻",
        "damage_range": (42, 68),
        "attack_speed": 1.28,
        "crit_chance": 6,
        "requirements": {"str": 148, "dex": 86},
        "tier": 9,
        "type": WeaponType.ONE_HAND_AXE
    },
    "demon_axe": {
        "name": "Бесовской топор",
        "emoji": "🪓👹",
        "damage_range": (50, 80),
        "attack_speed": 1.25,
        "crit_chance": 6.5,
        "requirements": {"str": 172, "dex": 99},
        "tier": 10,
        "type": WeaponType.ONE_HAND_AXE
    },
    
    # ============= ОДНОРУЧНЫЕ БУЛАВЫ =============
    "driftwood_club": {
        "name": "Дубинка из плавника",
        "emoji": "🔨",
        "damage_range": (4, 7),
        "attack_speed": 1.45,
        "crit_chance": 5,
        "requirements": {"str": 10},
        "tier": 1,
        "type": WeaponType.ONE_HAND_MACE
    },
    "spiked_club": {
        "name": "Шипастая дубинка",
        "emoji": "🔨",
        "damage_range": (11, 19),
        "attack_speed": 1.45,
        "crit_chance": 5,
        "requirements": {"str": 16},
        "tier": 2,
        "type": WeaponType.ONE_HAND_MACE
    },
    "stone_hammer": {
        "name": "Каменный молот",
        "emoji": "🔨",
        "damage_range": (19, 30),
        "attack_speed": 1.45,
        "crit_chance": 5,
        "requirements": {"str": 29},
        "tier": 3,
        "type": WeaponType.ONE_HAND_MACE
    },
    "war_hammer": {
        "name": "Воинский молот",
        "emoji": "🔨",
        "damage_range": (25, 40),
        "attack_speed": 1.4,
        "crit_chance": 5,
        "requirements": {"str": 45},
        "tier": 4,
        "type": WeaponType.ONE_HAND_MACE
    },
    "plated_mace": {
        "name": "Булава с пластинами",
        "emoji": "🔨",
        "damage_range": (32, 50),
        "attack_speed": 1.35,
        "crit_chance": 5,
        "requirements": {"str": 62},
        "tier": 5,
        "type": WeaponType.ONE_HAND_MACE
    },
    "ceremonial_mace": {
        "name": "Церемониальная булава",
        "emoji": "🔨✨",
        "damage_range": (38, 60),
        "attack_speed": 1.38,
        "crit_chance": 5.5,
        "requirements": {"str": 80},
        "tier": 6,
        "type": WeaponType.ONE_HAND_MACE
    },
    "glimmer_mace": {
        "name": "Сверкающая булава",
        "emoji": "🔨🌟",
        "damage_range": (44, 70),
        "attack_speed": 1.4,
        "crit_chance": 6,
        "requirements": {"str": 98},
        "tier": 7,
        "type": WeaponType.ONE_HAND_MACE
    },
    "vision_mace": {
        "name": "Булава видений",
        "emoji": "🔨👁️",
        "damage_range": (52, 82),
        "attack_speed": 1.35,
        "crit_chance": 6.5,
        "requirements": {"str": 118},
        "tier": 8,
        "type": WeaponType.ONE_HAND_MACE
    },
    "worm_mace": {
        "name": "Булава червя",
        "emoji": "🔨🪱",
        "damage_range": (60, 95),
        "attack_speed": 1.3,
        "crit_chance": 6,
        "requirements": {"str": 140},
        "tier": 9,
        "type": WeaponType.ONE_HAND_MACE
    },
    "dragon_mace": {
        "name": "Булава дракона",
        "emoji": "🔨🐉",
        "damage_range": (70, 110),
        "attack_speed": 1.32,
        "crit_chance": 7,
        "requirements": {"str": 165},
        "tier": 10,
        "type": WeaponType.ONE_HAND_MACE
    },
    
    # ============= КОГТИ =============
    "nail_claw": {
        "name": "Коготь-ноготь",
        "emoji": "🐾",
        "damage_range": (5, 12),
        "attack_speed": 1.6,
        "crit_chance": 6,
        "life_on_hit": 3,
        "requirements": {"dex": 22, "int": 12},
        "tier": 1,
        "type": WeaponType.CLAW
    },
    "shark_claw": {
        "name": "Акулий коготь",
        "emoji": "🐾🦈",
        "damage_range": (12, 24),
        "attack_speed": 1.55,
        "crit_chance": 6.5,
        "life_on_hit": 6,
        "requirements": {"dex": 48, "int": 26},
        "tier": 3,
        "type": WeaponType.CLAW
    },
    "eagle_claw": {
        "name": "Орлиный коготь",
        "emoji": "🐾🦅",
        "damage_range": (20, 38),
        "attack_speed": 1.58,
        "crit_chance": 7,
        "life_on_hit": 10,
        "requirements": {"dex": 84, "int": 45},
        "tier": 5,
        "type": WeaponType.CLAW
    },
    "demon_claw": {
        "name": "Демонический коготь",
        "emoji": "🐾👹",
        "damage_range": (32, 56),
        "attack_speed": 1.52,
        "crit_chance": 7.5,
        "life_on_hit": 15,
        "requirements": {"dex": 128, "int": 68},
        "tier": 7,
        "type": WeaponType.CLAW
    },
    "void_claw": {
        "name": "Коготь пустоты",
        "emoji": "🐾🌑",
        "damage_range": (45, 75),
        "attack_speed": 1.54,
        "crit_chance": 8,
        "life_on_hit": 20,
        "requirements": {"dex": 172, "int": 92},
        "tier": 9,
        "type": WeaponType.CLAW
    },
    
    # ============= КИНЖАЛЫ =============
    "glass_dagger": {
        "name": "Стеклянный кинжал",
        "emoji": "🗡️",
        "damage_range": (4, 10),
        "attack_speed": 1.6,
        "crit_chance": 6,
        "accuracy": 60,
        "requirements": {"dex": 15, "int": 15},
        "tier": 1,
        "type": WeaponType.DAGGER
    },
    "poison_dagger": {
        "name": "Отравленный кинжал",
        "emoji": "🗡️☠️",
        "damage_range": (8, 18),
        "attack_speed": 1.55,
        "crit_chance": 6.5,
        "accuracy": 70,
        "requirements": {"dex": 34, "int": 34},
        "tier": 2,
        "type": WeaponType.DAGGER
    },
    "assassin_dagger": {
        "name": "Кинжал убийцы",
        "emoji": "🗡️🔪",
        "damage_range": (14, 28),
        "attack_speed": 1.58,
        "crit_chance": 7,
        "accuracy": 85,
        "requirements": {"dex": 62, "int": 62},
        "tier": 4,
        "type": WeaponType.DAGGER
    },
    "gut_ripper": {
        "name": "Потрошитель",
        "emoji": "🗡️💀",
        "damage_range": (22, 42),
        "attack_speed": 1.54,
        "crit_chance": 7.5,
        "accuracy": 95,
        "requirements": {"dex": 96, "int": 96},
        "tier": 6,
        "type": WeaponType.DAGGER
    },
    "imperial_dagger": {
        "name": "Имперский кинжал",
        "emoji": "🗡️👑",
        "damage_range": (32, 58),
        "attack_speed": 1.52,
        "crit_chance": 8,
        "accuracy": 110,
        "requirements": {"dex": 138, "int": 138},
        "tier": 8,
        "type": WeaponType.DAGGER
    },
    "sai": {
        "name": "Сай",
        "emoji": "🗡️⚡",
        "damage_range": (40, 70),
        "attack_speed": 1.6,
        "crit_chance": 8.5,
        "accuracy": 120,
        "requirements": {"dex": 168, "int": 168},
        "tier": 10,
        "type": WeaponType.DAGGER
    },
    
    # ============= СКИПЕТРЫ =============
    "driftwood_sceptre": {
        "name": "Скипетр из плавника",
        "emoji": "🔱",
        "damage_range": (5, 11),
        "attack_speed": 1.35,
        "crit_chance": 6,
        "elemental_damage": 8,
        "requirements": {"str": 16, "int": 16},
        "tier": 1,
        "type": WeaponType.SCEPTRE
    },
    "bronze_sceptre": {
        "name": "Бронзовый скипетр",
        "emoji": "🔱",
        "damage_range": (9, 19),
        "attack_speed": 1.32,
        "crit_chance": 6,
        "elemental_damage": 12,
        "requirements": {"str": 32, "int": 32},
        "tier": 2,
        "type": WeaponType.SCEPTRE
    },
    "iron_sceptre": {
        "name": "Железный скипетр",
        "emoji": "🔱",
        "damage_range": (14, 28),
        "attack_speed": 1.3,
        "crit_chance": 6,
        "elemental_damage": 16,
        "requirements": {"str": 54, "int": 54},
        "tier": 3,
        "type": WeaponType.SCEPTRE
    },
    "ritual_sceptre": {
        "name": "Ритуальный скипетр",
        "emoji": "🔱🕯️",
        "damage_range": (22, 40),
        "attack_speed": 1.28,
        "crit_chance": 6.5,
        "elemental_damage": 22,
        "requirements": {"str": 84, "int": 84},
        "tier": 5,
        "type": WeaponType.SCEPTRE
    },
    "crystal_sceptre": {
        "name": "Кристальный скипетр",
        "emoji": "🔱💎",
        "damage_range": (34, 60),
        "attack_speed": 1.32,
        "crit_chance": 7,
        "elemental_damage": 30,
        "requirements": {"str": 122, "int": 122},
        "tier": 7,
        "type": WeaponType.SCEPTRE
    },
    "void_sceptre": {
        "name": "Скипетр пустоты",
        "emoji": "🔱🌌",
        "damage_range": (48, 85),
        "attack_speed": 1.3,
        "crit_chance": 7.5,
        "elemental_damage": 40,
        "requirements": {"str": 168, "int": 168},
        "tier": 9,
        "type": WeaponType.SCEPTRE
    },
    "alternating_sceptre": {
        "name": "Альтернирующий скипетр",
        "emoji": "🔱⚡",
        "damage_range": (55, 100),
        "attack_speed": 1.35,
        "crit_chance": 8,
        "elemental_damage": 50,
        "requirements": {"str": 190, "int": 190},
        "tier": 10,
        "type": WeaponType.SCEPTRE
    },
    
    # ============= ДВУРУЧНЫЕ МЕЧИ =============
    "corroded_blade": {
        "name": "Проржавевший клинок",
        "emoji": "⚔️⚔️",
        "damage_range": (12, 24),
        "attack_speed": 1.25,
        "crit_chance": 5,
        "accuracy": 40,
        "requirements": {"str": 32, "dex": 25},
        "tier": 1,
        "type": WeaponType.TWO_HAND_SWORD
    },
    "bastard_sword": {
        "name": "Полуторный меч",
        "emoji": "⚔️⚔️",
        "damage_range": (20, 38),
        "attack_speed": 1.22,
        "crit_chance": 5.5,
        "accuracy": 50,
        "requirements": {"str": 58, "dex": 45},
        "tier": 3,
        "type": WeaponType.TWO_HAND_SWORD
    },
    "claymore": {
        "name": "Клеймор",
        "emoji": "⚔️⚔️",
        "damage_range": (32, 58),
        "attack_speed": 1.18,
        "crit_chance": 5.5,
        "accuracy": 60,
        "requirements": {"str": 92, "dex": 68},
        "tier": 5,
        "type": WeaponType.TWO_HAND_SWORD
    },
    "executioner_sword": {
        "name": "Меч палача",
        "emoji": "⚔️⚔️💀",
        "damage_range": (45, 80),
        "attack_speed": 1.15,
        "crit_chance": 6,
        "accuracy": 70,
        "requirements": {"str": 134, "dex": 96},
        "tier": 7,
        "type": WeaponType.TWO_HAND_SWORD
    },
    "lion_sword": {
        "name": "Львиный меч",
        "emoji": "⚔️⚔️🦁",
        "damage_range": (60, 105),
        "attack_speed": 1.2,
        "crit_chance": 6.5,
        "accuracy": 85,
        "requirements": {"str": 178, "dex": 126},
        "tier": 9,
        "type": WeaponType.TWO_HAND_SWORD
    },
    
    # ============= ДВУРУЧНЫЕ ТОПОРЫ =============
    "stone_axe": {
        "name": "Каменный топор",
        "emoji": "🪓🪓",
        "damage_range": (14, 28),
        "attack_speed": 1.2,
        "crit_chance": 5,
        "requirements": {"str": 40, "dex": 16},
        "tier": 1,
        "type": WeaponType.TWO_HAND_AXE
    },
    "jade_chopper": {
        "name": "Нефритовое рубило",
        "emoji": "🪓🪓",
        "damage_range": (24, 46),
        "attack_speed": 1.18,
        "crit_chance": 5,
        "requirements": {"str": 70, "dex": 29},
        "tier": 3,
        "type": WeaponType.TWO_HAND_AXE
    },
    "labrys": {
        "name": "Лабрис",
        "emoji": "🪓🪓",
        "damage_range": (40, 72),
        "attack_speed": 1.15,
        "crit_chance": 5,
        "requirements": {"str": 110, "dex": 45},
        "tier": 5,
        "type": WeaponType.TWO_HAND_AXE
    },
    "ezomite_axe": {
        "name": "Топор Эзомита",
        "emoji": "🪓🪓",
        "damage_range": (58, 102),
        "attack_speed": 1.12,
        "crit_chance": 5.5,
        "requirements": {"str": 158, "dex": 64},
        "tier": 7,
        "type": WeaponType.TWO_HAND_AXE
    },
    "vaal_axe": {
        "name": "Топор Ваал",
        "emoji": "🪓🪓👹",
        "damage_range": (80, 140),
        "attack_speed": 1.14,
        "crit_chance": 6,
        "requirements": {"str": 202, "dex": 82},
        "tier": 9,
        "type": WeaponType.TWO_HAND_AXE
    },
    "despot_axe": {
        "name": "Топор деспота",
        "emoji": "🪓🪓👑",
        "damage_range": (95, 165),
        "attack_speed": 1.16,
        "crit_chance": 6.5,
        "requirements": {"str": 230, "dex": 95},
        "tier": 10,
        "type": WeaponType.TWO_HAND_AXE
    },
    
    # ============= ДВУРУЧНЫЕ БУЛАВЫ/МОЛОТЫ =============
    "driftwood_maul": {
        "name": "Дубина из плавника",
        "emoji": "🔨🔨",
        "damage_range": (16, 32),
        "attack_speed": 1.15,
        "crit_chance": 5,
        "stun_multiplier": 1.3,
        "requirements": {"str": 42},
        "tier": 1,
        "type": WeaponType.TWO_HAND_MACE
    },
    "great_maul": {
        "name": "Кувалда",
        "emoji": "🔨🔨",
        "damage_range": (30, 58),
        "attack_speed": 1.12,
        "crit_chance": 5,
        "stun_multiplier": 1.4,
        "requirements": {"str": 78},
        "tier": 3,
        "type": WeaponType.TWO_HAND_MACE
    },
    "brass_hammer": {
        "name": "Латунный молот",
        "emoji": "🔨🔨",
        "damage_range": (48, 88),
        "attack_speed": 1.1,
        "crit_chance": 5,
        "stun_multiplier": 1.45,
        "requirements": {"str": 120},
        "tier": 5,
        "type": WeaponType.TWO_HAND_MACE
    },
    "gavel": {
        "name": "Молот судьи",
        "emoji": "🔨🔨⚖️",
        "damage_range": (65, 115),
        "attack_speed": 1.08,
        "crit_chance": 5.5,
        "stun_multiplier": 1.5,
        "requirements": {"str": 168},
        "tier": 7,
        "type": WeaponType.TWO_HAND_MACE
    },
    "colossus_hammer": {
        "name": "Чудовищный молот",
        "emoji": "🔨🔨👹",
        "damage_range": (88, 152),
        "attack_speed": 1.05,
        "crit_chance": 5.5,
        "stun_multiplier": 1.6,
        "requirements": {"str": 215},
        "tier": 9,
        "type": WeaponType.TWO_HAND_MACE
    },
    
    # ============= ПОСОХИ =============
    "wooden_staff": {
        "name": "Деревянный посох",
        "emoji": "🏑",
        "damage_range": (10, 22),
        "attack_speed": 1.25,
        "crit_chance": 6,
        "block_chance": 15,
        "requirements": {"str": 24, "int": 24},
        "tier": 1,
        "type": WeaponType.STAFF
    },
    "iron_staff": {
        "name": "Железный посох",
        "emoji": "🏑",
        "damage_range": (20, 40),
        "attack_speed": 1.22,
        "crit_chance": 6.5,
        "block_chance": 18,
        "requirements": {"str": 52, "int": 52},
        "tier": 3,
        "type": WeaponType.STAFF
    },
    "mystic_staff": {
        "name": "Мистический посох",
        "emoji": "🏑✨",
        "damage_range": (35, 65),
        "attack_speed": 1.2,
        "crit_chance": 7,
        "block_chance": 20,
        "requirements": {"str": 94, "int": 94},
        "tier": 5,
        "type": WeaponType.STAFF
    },
    "dragon_staff": {
        "name": "Драконий посох",
        "emoji": "🏑🐉",
        "damage_range": (55, 98),
        "attack_speed": 1.18,
        "crit_chance": 7.5,
        "block_chance": 22,
        "requirements": {"str": 148, "int": 148},
        "tier": 8,
        "type": WeaponType.STAFF
    },
    
    # ============= ШЕСТЫ/БОЕВЫЕ ПОСОХИ =============
    "bamboo_staff": {
        "name": "Бамбуковый шест",
        "emoji": "🏑🎋",
        "damage_range": (8, 18),
        "attack_speed": 1.5,
        "crit_chance": 6.5,
        "requirements": {"dex": 28, "int": 9},
        "tier": 1,
        "type": WeaponType.QUARTERSTAFF
    },
    "iron_quarterstaff": {
        "name": "Железный шест",
        "emoji": "🏑",
        "damage_range": (18, 38),
        "attack_speed": 1.42,
        "crit_chance": 7,
        "requirements": {"dex": 60, "int": 20},
        "tier": 3,
        "type": WeaponType.QUARTERSTAFF
    },
    "monk_staff": {
        "name": "Шест монаха",
        "emoji": "🏑🧘",
        "damage_range": (30, 58),
        "attack_speed": 1.45,
        "crit_chance": 7.5,
        "requirements": {"dex": 105, "int": 35},
        "tier": 5,
        "type": WeaponType.QUARTERSTAFF
    },
    "wind_staff": {
        "name": "Шест ветра",
        "emoji": "🏑🌪️",
        "damage_range": (48, 88),
        "attack_speed": 1.48,
        "crit_chance": 8,
        "requirements": {"dex": 158, "int": 52},
        "tier": 8,
        "type": WeaponType.QUARTERSTAFF
    },
    
    # ============= КОПЬЯ =============
    "wooden_spear": {
        "name": "Деревянное копье",
        "emoji": "🔱",
        "damage_range": (9, 20),
        "attack_speed": 1.35,
        "crit_chance": 5.5,
        "range_bonus": 1,
        "requirements": {"dex": 30, "str": 15},
        "tier": 1,
        "type": WeaponType.SPEAR
    },
    "iron_spear": {
        "name": "Железное копье",
        "emoji": "🔱",
        "damage_range": (20, 42),
        "attack_speed": 1.32,
        "crit_chance": 6,
        "range_bonus": 1.5,
        "requirements": {"dex": 68, "str": 34},
        "tier": 3,
        "type": WeaponType.SPEAR
    },
    "javelin": {
        "name": "Дротик",
        "emoji": "🔱⚡",
        "damage_range": (35, 68),
        "attack_speed": 1.38,
        "crit_chance": 6.5,
        "range_bonus": 2,
        "requirements": {"dex": 115, "str": 57},
        "tier": 5,
        "type": WeaponType.SPEAR
    },
    "harpoon": {
        "name": "Гарпун",
        "emoji": "🔱🐋",
        "damage_range": (52, 95),
        "attack_speed": 1.3,
        "crit_chance": 6.5,
        "range_bonus": 2.5,
        "requirements": {"dex": 165, "str": 82},
        "tier": 7,
        "type": WeaponType.SPEAR
    },
    "dragonspine_spear": {
        "name": "Копье драконьего хребта",
        "emoji": "🔱🐉",
        "damage_range": (72, 130),
        "attack_speed": 1.34,
        "crit_chance": 7,
        "range_bonus": 3,
        "requirements": {"dex": 210, "str": 105},
        "tier": 9,
        "type": WeaponType.SPEAR
    },
    
    # ============= ЦЕПЫ/КИСТЕНИ =============
    "chain_flail": {
        "name": "Цеп с шипами",
        "emoji": "⛓️🔗",
        "damage_range": (12, 28),
        "attack_speed": 1.28,
        "crit_chance": 5.5,
        "stun_multiplier": 1.2,
        "requirements": {"str": 38, "dex": 13},
        "tier": 2,
        "type": WeaponType.FLAIL
    },
    "war_flail": {
        "name": "Боевой цеп",
        "emoji": "⛓️⚔️",
        "damage_range": (28, 58),
        "attack_speed": 1.24,
        "crit_chance": 6,
        "stun_multiplier": 1.3,
        "requirements": {"str": 85, "dex": 28},
        "tier": 4,
        "type": WeaponType.FLAIL
    },
    "morning_star": {
        "name": "Моргенштерн",
        "emoji": "⛓️⭐",
        "damage_range": (45, 88),
        "attack_speed": 1.2,
        "crit_chance": 6,
        "stun_multiplier": 1.4,
        "requirements": {"str": 140, "dex": 46},
        "tier": 6,
        "type": WeaponType.FLAIL
    },
    "holy_flail": {
        "name": "Священный цеп",
        "emoji": "⛓️✨",
        "damage_range": (62, 115),
        "attack_speed": 1.26,
        "crit_chance": 6.5,
        "stun_multiplier": 1.45,
        "requirements": {"str": 185, "dex": 62},
        "tier": 8,
        "type": WeaponType.FLAIL
    },
}

# ============= УНИКАЛЬНОЕ ОРУЖИЕ =============

UNIQUE_WEAPONS = {
    "frost_breath": {
        "name": "Ледяное дыхание",
        "base": "two_hand_mace",
        "emoji": "🔨❄️",
        "damage_range": (80, 140),
        "attack_speed": 1.1,
        "crit_chance": 7,
        "fixed_mods": {
            "damage": 50,
            "cold_damage": 30,
            "freeze_chance": 15
        },
        "requirements": {"str": 150},
        "description": "Коснись врага - и он станет льдом"
    },
    "soul_ripper": {
        "name": "Потрошитель душ",
        "base": "claw",
        "emoji": "🐾💀",
        "damage_range": (45, 80),
        "attack_speed": 1.6,
        "crit_chance": 9,
        "fixed_mods": {
            "damage": 40,
            "life_on_hit": 25,
            "crit_chance": 10
        },
        "requirements": {"dex": 120, "int": 80},
        "description": "Каждый удар крадет не только жизнь, но и душу"
    },
    "dragonfang": {
        "name": "Клык дракона",
        "base": "spear",
        "emoji": "🔱🐉",
        "damage_range": (70, 130),
        "attack_speed": 1.3,
        "crit_chance": 8,
        "fixed_mods": {
            "damage": 60,
            "fire_damage": 40,
            "range_bonus": 4
        },
        "requirements": {"str": 100, "dex": 150},
        "description": "Копье, выкованное из зуба древнего дракона"
    },
    "thunderstorm": {
        "name": "Грозовой шторм",
        "base": "quarterstaff",
        "emoji": "🏑⚡",
        "damage_range": (50, 95),
        "attack_speed": 1.6,
        "crit_chance": 8.5,
        "fixed_mods": {
            "damage": 35,
            "lightning_damage": 50,
            "attack_speed": 0.3
        },
        "requirements": {"dex": 140, "int": 100},
        "description": "Каждый удар сопровождается раскатом грома"
    },
    "executioner": {
        "name": "Палач",
        "base": "two_hand_axe",
        "emoji": "🪓⚔️",
        "damage_range": (100, 180),
        "attack_speed": 1.1,
        "crit_chance": 7.5,
        "fixed_mods": {
            "damage": 80,
            "crit_multiplier": 50,
            "stun_multiplier": 1.8
        },
        "requirements": {"str": 200},
        "description": "Одно движение - одна голова"
    }
}

# ============= БУТЫЛКИ (ФЛАСКИ) =============

FLASKS = {
    "small_life": {
        "name": "Малая бутылка здоровья",
        "emoji": "🧪",
        "heal": 40,
        "uses": 3,
        "rarity": ItemRarity.NORMAL
    },
    "medium_life": {
        "name": "Средняя бутылка здоровья",
        "emoji": "🧪✨",
        "heal": 65,
        "uses": 3,
        "rarity": ItemRarity.MAGIC
    },
    "large_life": {
        "name": "Большая бутылка здоровья",
        "emoji": "🧪🌟",
        "heal": 90,
        "uses": 3,
        "rarity": ItemRarity.RARE
    },
    "divine_life": {
        "name": "Божественная бутылка",
        "emoji": "🧪💫",
        "heal": 120,
        "uses": 3,
        "rarity": ItemRarity.UNIQUE
    }
}

# ============= КЛАССЫ ПРЕДМЕТОВ =============

class Item:
    def __init__(self, name, item_type, rarity=ItemRarity.NORMAL):
        self.name = name
        self.item_type = item_type
        self.rarity = rarity
        self.emoji = self._get_emoji()
        self.affixes = []
        self.stats = {}
        self.flask_data = None
        
    def _get_emoji(self):
        emoji_map = {
            ItemType.WEAPON: "⚔️",
            ItemType.HELMET: "⛑️",
            ItemType.ARMOR: "🛡️",
            ItemType.GLOVES: "🧤",
            ItemType.BOOTS: "👢",
            ItemType.BELT: "🔗",
            ItemType.RING: "💍",
            ItemType.AMULET: "📿",
            ItemType.FLASK: "🧪"
        }
        return emoji_map.get(self.item_type, "📦")
    
    def add_affix(self, affix_data, affix_type):
        self.affixes.append((affix_type, affix_data))
        value = random.randint(affix_data["value"][0], affix_data["value"][1])
        self.stats[affix_data["stat"]] = self.stats.get(affix_data["stat"], 0) + value
    
    def get_rarity_emoji(self):
        rarity_emojis = {
            ItemRarity.NORMAL: "⚪",
            ItemRarity.MAGIC: "🔵",
            ItemRarity.RARE: "🟡",
            ItemRarity.UNIQUE: "🔴"
        }
        return rarity_emojis.get(self.rarity, "⚪")
    
    def get_rarity_name(self):
        rarity_names = {
            ItemRarity.NORMAL: "Обычный",
            ItemRarity.MAGIC: "Магический",
            ItemRarity.RARE: "Редкий",
            ItemRarity.UNIQUE: "Уникальный"
        }
        return rarity_names.get(self.rarity, "Обычный")
    
    def get_type_name(self):
        type_names = {
            ItemType.WEAPON: "Оружие",
            ItemType.HELMET: "Шлем",
            ItemType.ARMOR: "Броня",
            ItemType.GLOVES: "Перчатки",
            ItemType.BOOTS: "Сапоги",
            ItemType.BELT: "Пояс",
            ItemType.RING: "Кольцо",
            ItemType.AMULET: "Амулет",
            ItemType.FLASK: "Фласка"
        }
        return type_names.get(self.item_type, "Предмет")
    
    def get_name_colored(self):
        return f"{self.get_rarity_emoji()}{self.emoji} {self.name}"
    
    def get_detailed_info(self):
        lines = []
        lines.append(f"{self.get_rarity_emoji()} **{self.name}**")
        lines.append(f"└ {self.get_rarity_name()} {self.emoji} {self.get_type_name()}")
        lines.append("")
        
        if self.affixes:
            lines.append("**Модификаторы:**")
            for affix_type, affix_data in self.affixes:
                prefix_suffix = "🔺 Префикс" if affix_type == AffixType.PREFIX else "🔻 Суффикс"
                value = self.stats.get(affix_data["stat"], 0)
                
                stat_names = {
                    "damage": "⚔️ Урон",
                    "max_hp": "❤️ Здоровье",
                    "defense": "🛡️ Защита",
                    "attack_speed": "⚡ Скорость атаки",
                    "accuracy": "🎯 Точность",
                    "crit_chance": "🔥 Шанс крита",
                    "crit_multiplier": "💥 Множитель крита",
                    "life_regen": "🌿 Регенерация",
                    "life_on_hit": "🩸 Вампиризм",
                    "stun_multiplier": "😵 Оглушение",
                    "fire_res": "🔥 Сопротивление огню",
                    "cold_res": "❄️ Сопротивление холоду",
                    "lightning_res": "⚡ Сопротивление молнии"
                }
                
                stat_name = stat_names.get(affix_data["stat"], affix_data["stat"])
                lines.append(f"  {prefix_suffix}: {affix_data['name']}")
                lines.append(f"    {stat_name}: +{value}")
        else:
            lines.append("**Модификаторы:** Отсутствуют")
        
        return "\n".join(lines)


# ============= КЛАСС ОРУЖИЯ =============

class MeleeWeapon(Item):
    def __init__(self, weapon_id, rarity=ItemRarity.NORMAL, quality=0):
        base = WEAPON_BASES[weapon_id]
        
        super().__init__(base["name"], ItemType.WEAPON, rarity)
        self.weapon_id = weapon_id
        self.weapon_type = base["type"]
        self.quality = quality
        self.tier = base.get("tier", 1)
        
        # Боевые характеристики
        self.base_damage_min = base["damage_range"][0]
        self.base_damage_max = base["damage_range"][1]
        self.attack_speed = base.get("attack_speed", 1.2)
        self.crit_chance = base.get("crit_chance", 5)
        self.accuracy = base.get("accuracy", 0)
        self.life_on_hit = base.get("life_on_hit", 0)
        self.stun_multiplier = base.get("stun_multiplier", 1.0)
        self.range_bonus = base.get("range_bonus", 0)
        self.elemental_damage = base.get("elemental_damage", 0)
        self.block_chance = base.get("block_chance", 0)
        
        # Требования
        self.requirements = base.get("requirements", {})
        
        # Неявные модификаторы
        self.implicit = base.get("implicit", "")
        
        # Уникальные модификаторы
        self.fixed_mods = {}
        
        self.emoji = base.get("emoji", "⚔️")
    
    def get_damage_range(self):
        quality_bonus = 1 + (self.quality / 100 * 0.5)
        damage_bonus = self.stats.get("damage", 0) / 100
        
        min_damage = int(self.base_damage_min * (1 + damage_bonus) * quality_bonus)
        max_damage = int(self.base_damage_max * (1 + damage_bonus) * quality_bonus)
        
        # Учитываем фиксированные моды уникального оружия
        if "damage" in self.fixed_mods:
            min_damage += self.fixed_mods["damage"]
            max_damage += self.fixed_mods["damage"]
        
        return min_damage, max_damage
    
    def get_detailed_info(self):
        lines = []
        
        # Заголовок с редкостью
        lines.append(f"{self.get_rarity_emoji()} **{self.name}**")
        weapon_type_names = {
            WeaponType.ONE_HAND_SWORD: "Одноручный меч",
            WeaponType.THRUSTING_SWORD: "Шпага",
            WeaponType.ONE_HAND_AXE: "Одноручный топор",
            WeaponType.ONE_HAND_MACE: "Одноручная булава",
            WeaponType.CLAW: "Коготь",
            WeaponType.DAGGER: "Кинжал",
            WeaponType.SCEPTRE: "Скипетр",
            WeaponType.TWO_HAND_SWORD: "Двуручный меч",
            WeaponType.TWO_HAND_AXE: "Двуручный топор",
            WeaponType.TWO_HAND_MACE: "Двуручная булава",
            WeaponType.STAFF: "Посох",
            WeaponType.QUARTERSTAFF: "Боевой шест",
            WeaponType.SPEAR: "Копье",
            WeaponType.FLAIL: "Цеп"
        }
        weapon_type_name = weapon_type_names.get(self.weapon_type, "Оружие")
        lines.append(f"└ {self.get_rarity_name()} {self.emoji} {weapon_type_name} (Тир {self.tier})")
        lines.append("")
        
        # Основные характеристики
        min_dmg, max_dmg = self.get_damage_range()
        avg_dmg = (min_dmg + max_dmg) // 2
        dps = int(avg_dmg * self.attack_speed)
        
        lines.append(f"**Характеристики:**")
        lines.append(f"  ⚔️ Урон: {min_dmg}-{max_dmg} (ср. {avg_dmg})")
        lines.append(f"  ⚡ Скорость: {self.attack_speed:.2f} атак/сек")
        lines.append(f"  💥 Шанс крита: {self.crit_chance + self.stats.get('crit_chance', 0)}%")
        lines.append(f"  📊 DPS: {dps}")
        
        if self.accuracy:
            lines.append(f"  🎯 Точность: +{self.accuracy + self.stats.get('accuracy', 0)}")
        if self.life_on_hit or 'life_on_hit' in self.stats:
            total_loh = self.life_on_hit + self.stats.get('life_on_hit', 0)
            lines.append(f"  🩸 Вампиризм: {total_loh} HP/удар")
        if self.stun_multiplier > 1 or 'stun_multiplier' in self.stats:
            mult = self.stun_multiplier * (1 + self.stats.get('stun_multiplier', 0) / 100)
            lines.append(f"  😵 Оглушение: x{mult:.1f}")
        if self.range_bonus:
            lines.append(f"  📏 Дальность: +{self.range_bonus}")
        if self.elemental_damage:
            lines.append(f"  🔥 Стихийный урон: +{self.elemental_damage}%")
        if self.block_chance:
            lines.append(f"  🛡️ Шанс блока: {self.block_chance}%")
        
        # Неявный модификатор
        if self.implicit:
            lines.append(f"  ✨ Особое: {self.implicit}")
        
        lines.append("")
        
        # Требования
        if self.requirements:
            req_text = "**Требования:** "
            req_parts = []
            if "str" in self.requirements:
                req_parts.append(f"💪 {self.requirements['str']}")
            if "dex" in self.requirements:
                req_parts.append(f"🏹 {self.requirements['dex']}")
            if "int" in self.requirements:
                req_parts.append(f"📚 {self.requirements['int']}")
            lines.append(" | ".join(req_parts))
            lines.append("")
        
        # Качество
        if self.quality > 0:
            lines.append(f"✨ Качество: +{self.quality}%")
        
        # Уникальное описание
        if self.rarity == ItemRarity.UNIQUE and hasattr(self, 'description'):
            lines.append(f"*{self.description}*")
            lines.append("")
        
        # Аффиксы
        if self.affixes:
            lines.append("**Модификаторы:**")
            for affix_type, affix_data in self.affixes:
                prefix_suffix = "🔺 Префикс" if affix_type == AffixType.PREFIX else "🔻 Суффикс"
                value = self.stats.get(affix_data["stat"], 0)
                
                stat_names = {
                    "damage": "⚔️ Урон",
                    "max_hp": "❤️ Здоровье",
                    "defense": "🛡️ Защита",
                    "attack_speed": "⚡ Скорость атаки",
                    "accuracy": "🎯 Точность",
                    "crit_chance": "🔥 Шанс крита",
                    "crit_multiplier": "💥 Множитель крита",
                    "life_regen": "🌿 Регенерация",
                    "life_on_hit": "🩸 Вампиризм",
                    "stun_multiplier": "😵 Оглушение"
                }
                
                stat_name = stat_names.get(affix_data["stat"], affix_data["stat"])
                lines.append(f"  {prefix_suffix}: {affix_data['name']}")
                lines.append(f"    {stat_name}: +{value}")
        
        return "\n".join(lines)


class UniqueWeapon(MeleeWeapon):
    def __init__(self, unique_id):
        data = UNIQUE_WEAPONS[unique_id]
        base_data = WEAPON_BASES[data["base"]]
        
        super().__init__(data["base"], ItemRarity.UNIQUE)
        
        self.name = data["name"]
        self.emoji = data.get("emoji", base_data.get("emoji", "⚔️"))
        self.description = data["description"]
        self.fixed_mods = data["fixed_mods"]
        
        # Переопределяем базовые характеристики
        self.base_damage_min = data["damage_range"][0]
        self.base_damage_max = data["damage_range"][1]
        self.attack_speed = data.get("attack_speed", base_data.get("attack_speed", 1.2))
        self.crit_chance = data.get("crit_chance", base_data.get("crit_chance", 5))
        
        # Добавляем фиксированные моды как аффиксы
        for stat, value in self.fixed_mods.items():
            self.stats[stat] = self.stats.get(stat, 0) + value


class Flask(Item):
    def __init__(self, flask_type):
        flask_data = FLASKS[flask_type]
        super().__init__(flask_data["name"], ItemType.FLASK, flask_data["rarity"])
        self.flask_data = flask_data
        self.current_uses = flask_data["uses"]
        
    def use(self):
        if self.current_uses > 0:
            self.current_uses -= 1
            return self.flask_data["heal"]
        return 0
    
    def get_detailed_info(self):
        lines = []
        lines.append(f"{self.get_rarity_emoji()} **{self.name}**")
        lines.append(f"└ {self.get_rarity_name()} {self.emoji} Фласка")
        lines.append("")
        lines.append("**Параметры:**")
        heal_emoji = "💚" if self.flask_data["heal"] < 50 else "💛" if self.flask_data["heal"] < 100 else "❤️"
        lines.append(f"  {heal_emoji} Лечение: +{self.flask_data['heal']} HP")
        charges_emoji = "🔋" * self.current_uses + "⚪" * (self.flask_data["uses"] - self.current_uses)
        lines.append(f"  {charges_emoji} Заряды: {self.current_uses}/{self.flask_data['uses']}")
        return "\n".join(lines)
    
    def get_status(self):
        charges = "█" * self.current_uses + "░" * (self.flask_data["uses"] - self.current_uses)
        return f"{self.get_rarity_emoji()}{self.emoji} {self.flask_data['heal']}HP [{charges}]"


# ============= ИГРОК =============

class Player:
    def __init__(self):
        # Базовые статы
        self.hp = 150
        self.max_hp = 150
        self.defense = 5
        self.damage = 15
        self.accuracy = 85
        self.crit_chance = 5
        self.crit_multiplier = 125
        self.attack_speed = 100
        self.life_on_hit = 0
        self.stun_multiplier = 1.0
        
        self.exp = 0
        self.level = 1
        self.gold = 0
        
        # Атрибуты
        self.strength = 10
        self.dexterity = 10
        self.intelligence = 10
        
        # Инвентарь
        self.inventory = []
        self.equipped = {
            ItemType.WEAPON: None,
            ItemType.HELMET: None,
            ItemType.ARMOR: None,
            ItemType.GLOVES: None,
            ItemType.BOOTS: None,
            ItemType.BELT: None,
            ItemType.RING: None,
            ItemType.AMULET: None
        }
        
        # Фласки - максимум 3, начинаем с 1
        self.flasks = []
        self.max_flasks = 3
        self.active_flask = 0
        
        # Даем стартовую фласку
        starter_flask = Flask("small_life")
        self.flasks.append(starter_flask)
        
        # Даем стартовое оружие
        starter_weapon = generate_melee_weapon("common", force_tier=1)
        self.inventory.append(starter_weapon)
        
        # Текущая позиция в подземелье
        self.current_position = 0
        self.visited_positions = set()
    
    def get_total_damage(self):
        if self.equipped[ItemType.WEAPON]:
            weapon = self.equipped[ItemType.WEAPON]
            min_dmg, max_dmg = weapon.get_damage_range()
            damage = random.randint(min_dmg, max_dmg)
            
            # Бонус от силы для некоторых типов оружия
            if weapon.weapon_type in [WeaponType.ONE_HAND_MACE, WeaponType.TWO_HAND_MACE, 
                                       WeaponType.ONE_HAND_AXE, WeaponType.TWO_HAND_AXE]:
                damage = int(damage * (1 + self.strength / 200))
            
            # Бонус от ловкости для некоторых типов оружия
            if weapon.weapon_type in [WeaponType.DAGGER, WeaponType.CLAW, WeaponType.THRUSTING_SWORD]:
                damage = int(damage * (1 + self.dexterity / 200))
                self.crit_chance += self.dexterity // 20
            
            return damage
        else:
            # Без оружия
            return random.randint(5, 10)
    
    def add_flask_charge(self):
        charges_added = 0
        for flask in self.flasks:
            if flask.current_uses < flask.flask_data["uses"]:
                flask.current_uses = min(flask.flask_data["uses"], flask.current_uses + 1)
                charges_added += 1
        return charges_added
    
    def apply_item_stats(self, item):
        for stat, value in item.stats.items():
            if hasattr(self, stat):
                setattr(self, stat, getattr(self, stat) + value)
    
    def remove_item_stats(self, item):
        for stat, value in item.stats.items():
            if hasattr(self, stat):
                setattr(self, stat, getattr(self, stat) - value)
    
    def equip(self, item, slot):
        if self.equipped[slot]:
            self.remove_item_stats(self.equipped[slot])
            self.inventory.append(self.equipped[slot])
        
        self.equipped[slot] = item
        self.apply_item_stats(item)
        if item in self.inventory:
            self.inventory.remove(item)
    
    def can_equip(self, item):
        if isinstance(item, MeleeWeapon):
            req = item.requirements
            if req.get("str", 0) > self.strength:
                return False, f"Требуется сила: {req['str']}"
            if req.get("dex", 0) > self.dexterity:
                return False, f"Требуется ловкость: {req['dex']}"
            if req.get("int", 0) > self.intelligence:
                return False, f"Требуется интеллект: {req['int']}"
        return True, ""


# ============= КЛАССЫ ВРАГОВ =============

class Enemy:
    def __init__(self, name, hp, damage, accuracy, defense, exp, emoji, rarity, image_path=None):
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.damage = damage
        self.accuracy = accuracy
        self.defense = defense
        self.exp = exp
        self.emoji = emoji
        self.rarity = rarity
        self.image_path = image_path


# ============= ПУЛ ПРОТИВНИКОВ =============

COMMON_ENEMIES = [
    {"name": "Огромный червь", "hp": 40, "damage": (6,12), "accuracy": 65, "defense": 3, "exp": 22, "emoji": "🪱", "image": "images/monsters/worm.jpg"},
    {"name": "Жуткий кадавр", "hp": 45, "damage": (7,13), "accuracy": 60, "defense": 4, "exp": 24, "emoji": "🧟", "image": "images/monsters/cadaver.jpg"},
    {"name": "Гниющий зомби", "hp": 35, "damage": (5,10), "accuracy": 55, "defense": 2, "exp": 20, "emoji": "🧟‍♂️", "image": "images/monsters/zombie.jpg"},
    {"name": "Костяной скелет", "hp": 30, "damage": (6,12), "accuracy": 70, "defense": 2, "exp": 21, "emoji": "💀", "image": "images/monsters/skeleton.jpg"},
    {"name": "Пещерный паук", "hp": 28, "damage": (7,11), "accuracy": 75, "defense": 1, "exp": 19, "emoji": "🕷️", "image": "images/monsters/spider.jpg"},
    {"name": "Блуждающий призрак", "hp": 32, "damage": (8,14), "accuracy": 80, "defense": 0, "exp": 26, "emoji": "👻", "image": "images/monsters/ghost.jpg"},
]

MAGIC_ENEMIES = [
    {"name": "Проклятый кадавр", "hp": 60, "damage": (9,15), "accuracy": 65, "defense": 5, "exp": 42, "emoji": "🧟⚡", "image": "images/monsters/cursed_cadaver.jpg"},
    {"name": "Призрачный страж", "hp": 55, "damage": (10,17), "accuracy": 75, "defense": 4, "exp": 45, "emoji": "👻⚔️", "image": "images/monsters/ghost_guardian.jpg"},
    {"name": "Огненный червь", "hp": 50, "damage": (12,18), "accuracy": 70, "defense": 3, "exp": 44, "emoji": "🪱🔥", "image": "images/monsters/fire_worm.jpg"},
    {"name": "Ледяной скелет", "hp": 48, "damage": (9,16), "accuracy": 72, "defense": 5, "exp": 43, "emoji": "💀❄️", "image": "images/monsters/ice_skeleton.jpg"},
]

RARE_ENEMIES = [
    {"name": "Культист смерти", "hp": 85, "damage": (16,26), "accuracy": 75, "defense": 8, "exp": 85, "emoji": "🧙💀", "image": "images/monsters/death_cultist.jpg"},
    {"name": "Демонический червь", "hp": 90, "damage": (18,28), "accuracy": 70, "defense": 9, "exp": 88, "emoji": "🪱👹", "image": "images/monsters/demon_worm.jpg"},
    {"name": "Костяной голем", "hp": 100, "damage": (14,24), "accuracy": 65, "defense": 12, "exp": 90, "emoji": "🦴🗿", "image": "images/monsters/bone_golem.jpg"},
]

BOSS_ENEMIES = [
    {"name": "Повелитель червей", "hp": 220, "damage": (26,42), "accuracy": 80, "defense": 15, "exp": 220, "emoji": "🪱👑", "image": "images/monsters/worm_lord.jpg"},
    {"name": "Архилич", "hp": 200, "damage": (28,45), "accuracy": 90, "defense": 12, "exp": 240, "emoji": "🧙‍♂️💀", "image": "images/monsters/archlich.jpg"},
    {"name": "Король кадавров", "hp": 240, "damage": (24,40), "accuracy": 75, "defense": 18, "exp": 250, "emoji": "👑🧟", "image": "images/monsters/cadaver_king.jpg"},
]

# ============= ПУЛ СОБЫТИЙ =============

EVENT_POOL = [
    {"type": "chest", "name": "Забытый сундук", "emoji": "📦", "rarity": "common", "chance": 30},
    {"type": "chest", "name": "Магический сундук", "emoji": "📦✨", "rarity": "magic", "chance": 15},
    {"type": "chest", "name": "Древний сундук", "emoji": "📦🌟", "rarity": "rare", "chance": 8},
    {"type": "rest", "name": "Место привала", "emoji": "🔥", "heal": 30, "chance": 25},
    {"type": "trap", "name": "Ловушка", "emoji": "⚠️", "damage": 20, "chance": 15},
    {"type": "altar", "name": "Древний алтарь", "emoji": "🪦", "effect": "random", "chance": 7},
]

# ============= СИСТЕМА ГЕНЕРАЦИИ ПРЕДМЕТОВ =============

def generate_melee_weapon(enemy_rarity, force_tier=None):
    """Генерирует случайное оружие ближнего боя"""
    
    tier_weapons = {
        1: ["rusted_sword", "driftwood_club", "rusty_hatchet", "nail_claw", 
            "glass_dagger", "driftwood_sceptre", "driftwood_maul", "wooden_staff",
            "bamboo_staff", "wooden_spear", "corroded_blade", "stone_axe"],
        2: ["copper_sword", "spiked_club", "jade_axe", "chain_flail",
            "stone_hammer", "poison_dagger"],
        3: ["saber", "boarding_axe", "shark_claw", "bronze_sceptre", 
            "bastard_sword", "jade_chopper", "great_maul", "iron_staff",
            "iron_quarterstaff", "iron_spear", "stone_hammer"],
        4: ["broad_sword", "pirate_cutlass", "cleaver", "war_hammer",
            "assassin_dagger", "iron_sceptre", "war_flail"],
        5: ["war_sword", "plated_mace", "carpenter_axe", "eagle_claw",
            "ritual_sceptre", "claymore", "labrys", "brass_hammer", 
            "mystic_staff", "monk_staff", "javelin"],
        6: ["ancient_sword", "gladius", "ceremonial_mace", "battle_axe",
            "gut_ripper", "morning_star"],
        7: ["elegant_sword", "decorative_axe", "glimmer_mace", "demon_claw",
            "crystal_sceptre", "executioner_sword", "ezomite_axe", "gavel",
            "harpoon"],
        8: ["twilight_blade", "estoc", "savage_axe", "vision_mace",
            "imperial_dagger", "dragon_staff", "wind_staff", "holy_flail"],
        9: ["gem_sword", "worm_mace", "ghost_axe", "void_claw",
            "void_sceptre", "lion_sword", "vaal_axe", "colossus_hammer",
            "dragonspine_spear"],
        10: ["eternal_sword", "tiger_hook", "demon_axe", "dragon_mace",
             "sai", "alternating_sceptre", "despot_axe"]
    }
    
    # Определяем тир на основе редкости врага
    tier_map = {
        "common": 1,
        "magic": 3,
        "rare": 5,
        "epic": 7,
        "boss": 9
    }
    
    if force_tier:
        tier = force_tier
    else:
        base_tier = tier_map.get(enemy_rarity, 1)
        tier = base_tier + random.randint(-1, 1)
        tier = max(1, min(10, tier))
    
    # Выбираем случайное оружие этого тира
    weapons_of_tier = tier_weapons.get(tier, tier_weapons[1])
    weapon_id = random.choice(weapons_of_tier)
    
    # Определяем редкость предмета
    rarity_roll = random.random() * 100
    
    if rarity_roll < 50:
        item_rarity = ItemRarity.NORMAL
    elif rarity_roll < 80:
        item_rarity = ItemRarity.MAGIC
    elif rarity_roll < 95:
        item_rarity = ItemRarity.RARE
    else:
        # Шанс на уникальное оружие
        if random.random() < 0.3:  # 30% от шанса 5% = 1.5% общий шанс
            unique_id = random.choice(list(UNIQUE_WEAPONS.keys()))
            return UniqueWeapon(unique_id)
        else:
            item_rarity = ItemRarity.RARE
    
    weapon = MeleeWeapon(weapon_id, item_rarity)
    
    # Добавляем качество (0-20%)
    if random.random() < 0.3:
        weapon.quality = random.randint(5, 20)
    
    # Добавляем аффиксы для магических и редких предметов
    if item_rarity == ItemRarity.MAGIC:
        if random.choice([True, False]):
            affix = random.choice(list(PREFIXES.values()))
            weapon.add_affix(affix, AffixType.PREFIX)
        else:
            affix = random.choice(list(SUFFIXES.values()))
            weapon.add_affix(affix, AffixType.SUFFIX)
    
    elif item_rarity == ItemRarity.RARE:
        num_affixes = random.randint(2, 4)
        for _ in range(num_affixes):
            if random.choice([True, False]):
                affix = random.choice(list(PREFIXES.values()))
            else:
                affix = random.choice(list(SUFFIXES.values()))
            weapon.add_affix(affix, random.choice([AffixType.PREFIX, AffixType.SUFFIX]))
    
    # Генерируем имя на основе аффиксов
    if weapon.affixes:
        prefixes = [a for t, a in weapon.affixes if t == AffixType.PREFIX]
        suffixes = [a for t, a in weapon.affixes if t == AffixType.SUFFIX]
        
        name_parts = []
        if prefixes:
            name_parts.append(random.choice(prefixes)["name"])
        name_parts.append(WEAPON_BASES[weapon_id]["name"])
        if suffixes:
            name_parts.append(random.choice(suffixes)["name"])
        
        weapon.name = " ".join(name_parts)
    
    return weapon


def generate_flask():
    roll = random.random() * 100
    
    if roll < 60:
        flask_type = "small_life"
    elif roll < 85:
        flask_type = "medium_life"
    elif roll < 97:
        flask_type = "large_life"
    else:
        flask_type = "divine_life"
    
    return Flask(flask_type)


def generate_loot(enemy_rarity):
    loot = []
    
    # Шанс на предмет экипировки
    drop_chance = {
        "common": 20,
        "magic": 40,
        "rare": 60,
        "epic": 80,
        "boss": 100
    }.get(enemy_rarity, 20)
    
    if random.randint(1, 100) <= drop_chance:
        # 70% шанс на оружие, 30% на другое (для простоты пока только оружие)
        if random.random() < 0.7:
            item = generate_melee_weapon(enemy_rarity)
            if item:
                loot.append(item)
    
    # Шанс на фласку
    flask_chance = {
        "common": 15,
        "magic": 25,
        "rare": 40,
        "epic": 60,
        "boss": 100
    }.get(enemy_rarity, 15)
    
    if random.randint(1, 100) <= flask_chance:
        flask = generate_flask()
        loot.append(flask)
    
    # Золото
    gold_base = {
        "common": 10,
        "magic": 25,
        "rare": 50,
        "epic": 100,
        "boss": 300
    }.get(enemy_rarity, 10)
    
    gold = random.randint(gold_base, gold_base * 2)
    loot.append({"type": "gold", "amount": gold})
    
    return loot


# ============= GACHA СИСТЕМА =============

def roll_enemy():
    roll = random.random() * 100
    
    if roll < 70:
        return random.choice(COMMON_ENEMIES), "common"
    elif roll < 95:
        return random.choice(MAGIC_ENEMIES), "magic"
    elif roll < 99:
        return random.choice(RARE_ENEMIES), "rare"
    else:
        return random.choice(BOSS_ENEMIES), "boss"


def roll_event():
    roll = random.random() * 100
    cumulative = 0
    
    for event in EVENT_POOL:
        cumulative += event["chance"]
        if roll < cumulative:
            return event
    
    return EVENT_POOL[0]


def generate_dungeon():
    dungeon = []
    
    for i in range(19):
        if random.random() < 0.6:
            enemy, rarity = roll_enemy()
            dungeon.append({
                "type": "battle",
                "enemy": enemy,
                "name": enemy["name"],
                "emoji": enemy["emoji"],
                "rarity": rarity,
                "image": enemy.get("image"),
                "completed": False
            })
        else:
            event = roll_event()
            dungeon.append({
                "type": event["type"],
                "event": event,
                "name": event["name"],
                "emoji": event["emoji"],
                "completed": False
            })
    
    boss = random.choice(BOSS_ENEMIES)
    dungeon.append({
        "type": "boss",
        "enemy": boss,
        "name": boss["name"],
        "emoji": boss["emoji"],
        "rarity": "boss",
        "image": boss.get("image"),
        "completed": False
    })
    
    return dungeon


# ============= ОСНОВНЫЕ ФУНКЦИИ =============

async def show_dungeon(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    if not data or 'dungeon' not in data:
        dungeon = generate_dungeon()
        player = Player()
        await state.update_data(player=player, dungeon=dungeon)
    else:
        player = data['player']
        dungeon = data['dungeon']
    
    current_event = dungeon[player.current_position]
    
    progress = []
    for i, event in enumerate(dungeon):
        if i < player.current_position:
            progress.append("✅")
        elif i == player.current_position:
            if event["type"] in ["battle", "boss"]:
                progress.append(event["enemy"]["emoji"])
            else:
                progress.append(event["emoji"])
        else:
            progress.append("⬜")
    
    progress_bar = " ".join(progress)
    
    if current_event["type"] in ["battle", "boss"]:
        enemy = current_event["enemy"]
        rarity_text = {
            "common": "🟢",
            "magic": "🟣",
            "rare": "🟡",
            "boss": "⚫"
        }.get(current_event.get("rarity"), "")
        
        event_info = f"**{enemy['emoji']} {enemy['name']}** {rarity_text}\n"
        if not current_event.get("completed", False):
            event_info += f"❤️ {enemy['hp']} HP"
        else:
            event_info += "✅ Уже побежден"
    else:
        event = current_event["event"]
        event_info = f"**{event['emoji']} {event['name']}**"
        if current_event.get("completed", False):
            event_info += " ✅ Пройдено"
    
    flask_status = []
    if player.flasks:
        active_flask = player.flasks[player.active_flask]
        flask_status.append(f"👉 {active_flask.get_status()}")
    flask_text = "\n".join(flask_status) if flask_status else "Нет фласок"
    
    # Информация об оружии
    weapon_info = ""
    if player.equipped[ItemType.WEAPON]:
        weapon = player.equipped[ItemType.WEAPON]
        weapon_info = f"\n{weapon.get_name_colored()}"
    
    player_status = (
        f"👤 {player.hp}/{player.max_hp} ❤️ | Ур. {player.level}\n"
        f"💪 {player.strength} 🏹 {player.dexterity} 📚 {player.intelligence}\n"
        f"⚔️ {weapon_info}\n"
        f"🧪 {flask_text}\n"
        f"💰 {player.gold} золота | ✨ {player.exp}/{player.level * 100}"
    )
    
    text = (
        f"🗺️ **ПОДЗЕМЕЛЬЕ**\n\n"
        f"{progress_bar}\n\n"
        f"📍 **Текущая позиция:** {player.current_position + 1}/{len(dungeon)}\n\n"
        f"{event_info}\n\n"
        f"{player_status}"
    )
    
    buttons = []
    
    if current_event["type"] in ["battle", "boss"] and not current_event.get("completed", False):
        buttons.append([InlineKeyboardButton(text="⚔️ Вступить в бой", callback_data="start_battle")])
    elif current_event["type"] in ["chest", "rest", "trap", "altar"] and not current_event.get("completed", False):
        action_text = {
            "chest": "📦 Открыть",
            "rest": "🔥 Отдохнуть",
            "trap": "⚠️ Пройти",
            "altar": "🪦 Использовать"
        }.get(current_event["type"], "👆 Взаимодействовать")
        buttons.append([InlineKeyboardButton(text=action_text, callback_data=f"do_{current_event['type']}")])
    
    if current_event.get("completed", False) and player.current_position < len(dungeon) - 1:
        buttons.append([InlineKeyboardButton(text="➡️ Идти дальше", callback_data="next_step")])
    
    if player.current_position == len(dungeon) - 1 and current_event.get("completed", False):
        if current_event["type"] == "boss" and current_event.get("completed", False):
            buttons.append([InlineKeyboardButton(text="🚪 Выйти из подземелья", callback_data="exit_dungeon")])
    
    buttons.append([
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="show_inventory"),
        InlineKeyboardButton(text="📊 Экипировка", callback_data="show_equipment")
    ])
    
    if len(player.flasks) > 1:
        buttons.append([InlineKeyboardButton(text="🧪 Переключить фласку", callback_data="switch_flask")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await state.update_data(player=player, dungeon=dungeon)
    
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except:
        await message.answer(text, reply_markup=keyboard)


# ============= ПЕРЕМЕЩЕНИЕ =============

@dp.callback_query(lambda c: c.data == "next_step")
async def next_step(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    dungeon = data['dungeon']
    
    if player.current_position < len(dungeon) - 1:
        player.current_position += 1
    
    await state.update_data(player=player, dungeon=dungeon)
    await show_dungeon(callback.message, state)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "exit_dungeon")
async def exit_dungeon(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    
    bonus_exp = player.level * 50
    bonus_gold = player.level * 100
    player.exp += bonus_exp
    player.gold += bonus_gold
    
    while player.exp >= player.level * 100:
        player.level += 1
        player.max_hp += 10
        player.hp = player.max_hp
        
        # Повышение атрибутов с каждым уровнем
        player.strength += 2
        player.dexterity += 2
        player.intelligence += 2
    
    await callback.message.edit_text(
        f"🎉 **ПОДЗЕМЕЛЬЕ ПРОЙДЕНО!**\n\n"
        f"Ты нашел выход из темницы!\n\n"
        f"💰 Бонус: +{bonus_gold} золота\n"
        f"✨ Бонус: +{bonus_exp} опыта\n"
        f"👤 Новый уровень: {player.level}\n\n"
        f"💪 Сила: {player.strength}\n"
        f"🏹 Ловкость: {player.dexterity}\n"
        f"📚 Интеллект: {player.intelligence}\n\n"
        f"Хочешь начать новое подземелье? Отправь /start"
    )
    
    await state.clear()
    await callback.answer()


# ============= БОЙ =============

@dp.callback_query(lambda c: c.data == "start_battle")
async def start_battle(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    dungeon = data['dungeon']
    
    current_event = dungeon[player.current_position]
    enemy_data = current_event["enemy"]
    
    enemy = Enemy(
        enemy_data["name"],
        enemy_data["hp"],
        enemy_data["damage"],
        enemy_data["accuracy"],
        enemy_data["defense"],
        enemy_data["exp"],
        enemy_data["emoji"],
        current_event.get("rarity", "common"),
        enemy_data.get("image")
    )
    
    await state.update_data(battle_enemy=enemy)
    await show_battle(callback, state, is_callback=True)
    await callback.answer()


async def show_battle(callback_or_message, state: FSMContext, is_callback=True):
    data = await state.get_data()
    player = data['player']
    enemy = data['battle_enemy']
    
    rarity_color = {
        "common": "🟢",
        "magic": "🟣",
        "rare": "🟡",
        "boss": "⚫"
    }.get(enemy.rarity, "")
    
    enemy_info = f"**{enemy.emoji} {enemy.name}** {rarity_color}\n❤️ {enemy.hp}/{enemy.max_hp} HP"
    
    flask_status = []
    if player.flasks:
        active_flask = player.flasks[player.active_flask]
        flask_status.append(f"👉 {active_flask.get_status()}")
    flask_text = "\n".join(flask_status) if flask_status else "Нет фласок"
    
    # Информация об оружии
    weapon_info = ""
    if player.equipped[ItemType.WEAPON]:
        weapon = player.equipped[ItemType.WEAPON]
        min_dmg, max_dmg = weapon.get_damage_range()
        weapon_info = f"\n{weapon.get_name_colored()} [{min_dmg}-{max_dmg}]"
    
    player_status = f"👤 {player.hp}/{player.max_hp} ❤️{weapon_info}"
    
    text = (
        f"{enemy_info}\n\n"
        f"{player_status}\n"
        f"🧪 {flask_text}\n\n"
        f"Твой ход:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Атаковать", callback_data="battle_attack")],
        [InlineKeyboardButton(text="🧪 Фласка", callback_data="battle_flask")],
        [InlineKeyboardButton(text="🏃 Убежать", callback_data="battle_run")]
    ])
    
    try:
        if is_callback:
            message = callback_or_message.message
        else:
            message = callback_or_message
        
        if enemy.image_path and os.path.exists(enemy.image_path):
            photo = FSInputFile(enemy.image_path)
            
            if is_callback:
                if hasattr(message, 'photo') and message.photo:
                    await message.edit_caption(caption=text, reply_markup=keyboard)
                else:
                    await message.delete()
                    await message.answer_photo(photo=photo, caption=text, reply_markup=keyboard)
            else:
                try:
                    await message.delete()
                except:
                    pass
                await message.answer_photo(photo=photo, caption=text, reply_markup=keyboard)
        else:
            battle_view = f"""
🟫🟫🟫🟫🟫🟫

    👨‍🦱            {enemy.emoji}

🟫🟫🟫🟫🟫🟫
"""
            full_text = f"{battle_view}\n\n{text}"
            
            if is_callback:
                await message.edit_text(full_text, reply_markup=keyboard)
            else:
                await message.answer(full_text, reply_markup=keyboard)
    except Exception as e:
        print(f"Ошибка при показе боя: {e}")
        battle_view = f"""
🟫🟫🟫🟫🟫🟫

    👨‍🦱            {enemy.emoji}

🟫🟫🟫🟫🟫🟫
"""
        full_text = f"{battle_view}\n\n{text}"
        if is_callback:
            await message.edit_text(full_text, reply_markup=keyboard)
        else:
            await message.answer(full_text, reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith('battle_'))
async def battle_action(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split('_')[1]
    data = await state.get_data()
    player = data['player']
    enemy = data['battle_enemy']
    dungeon = data['dungeon']
    
    result = []
    
    if action == "attack":
        # Проверка на попадание
        hit_chance = player.accuracy
        if player.equipped[ItemType.WEAPON]:
            weapon = player.equipped[ItemType.WEAPON]
            hit_chance += weapon.accuracy
        
        if random.randint(1, 100) <= hit_chance:
            base_damage = player.get_total_damage()
            
            # Проверка на крит
            crit = player.crit_chance
            if player.equipped[ItemType.WEAPON]:
                crit += player.equipped[ItemType.WEAPON].crit_chance
            
            is_crit = random.randint(1, 100) <= crit
            if is_crit:
                crit_mult = player.crit_multiplier
                if player.equipped[ItemType.WEAPON]:
                    crit_mult += player.equipped[ItemType.WEAPON].stats.get('crit_multiplier', 0)
                total_damage = int(base_damage * (crit_mult / 100))
                result.append(f"🔥 КРИТ! {total_damage} урона")
            else:
                total_damage = base_damage
                result.append(f"⚔️ {total_damage} урона")
            
            damage_reduction = max(0, enemy.defense - player.defense) // 3
            final_damage = max(1, total_damage - damage_reduction)
            enemy.hp -= final_damage
            
            # Вампиризм
            if player.equipped[ItemType.WEAPON]:
                life_on_hit = player.equipped[ItemType.WEAPON].life_on_hit + player.equipped[ItemType.WEAPON].stats.get('life_on_hit', 0)
                if life_on_hit > 0:
                    heal = min(player.max_hp - player.hp, life_on_hit)
                    player.hp += heal
                    result.append(f"🩸 Вампиризм: +{heal} HP")
        else:
            result.append("😫 Промах!")
        
        # Ответная атака врага
        if enemy.hp > 0:
            if random.randint(1, 100) <= enemy.accuracy:
                enemy_damage = random.randint(enemy.damage[0], enemy.damage[1])
                damage_block = max(0, player.defense) // 2
                final_enemy_damage = max(1, enemy_damage - damage_block)
                player.hp -= final_enemy_damage
                result.append(f"💥 {enemy.name} атакует: {final_enemy_damage}")
            else:
                result.append(f"🙏 {enemy.name} промахнулся")
    
    elif action == "flask":
        if player.flasks and player.active_flask is not None:
            flask = player.flasks[player.active_flask]
            heal = flask.use()
            if heal > 0:
                player.hp = min(player.max_hp, player.hp + heal)
                result.append(f"🧪 {flask.name}: +{heal} HP [{flask.current_uses}/{flask.flask_data['uses']}]")
                
                if flask.current_uses == 0:
                    for i, f in enumerate(player.flasks):
                        if f.current_uses > 0:
                            player.active_flask = i
                            break
            else:
                result.append("❌ Фласка пуста!")
                for i, f in enumerate(player.flasks):
                    if f.current_uses > 0:
                        player.active_flask = i
                        result.append(f"🔄 Переключено на {f.name}")
                        break
        else:
            result.append("❌ Нет фласок!")
    
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
                result.append(f"💥 {enemy.name} атакует: {enemy_damage}")
    
    if enemy.hp <= 0:
        player.exp += enemy.exp
        while player.exp >= player.level * 100:
            player.level += 1
            player.max_hp += 10
            player.hp = player.max_hp
            player.strength += 2
            player.dexterity += 2
            player.intelligence += 2
            result.append(f"✨ **УРОВЕНЬ {player.level}!**")
        
        charges = player.add_flask_charge()
        if charges > 0:
            result.append(f"🧪 Восстановлено {charges} зарядов фласок")
        
        loot_items = generate_loot(enemy.rarity)
        
        loot_text = []
        gold_total = 0
        
        for item in loot_items:
            if isinstance(item, dict) and item["type"] == "gold":
                gold_total += item["amount"]
                player.gold += item["amount"]
                loot_text.append(f"💰 {item['amount']} золота")
            elif isinstance(item, Item):
                if item.item_type == ItemType.FLASK:
                    if len(player.flasks) < player.max_flasks:
                        player.flasks.append(item)
                        loot_text.append(f"🧪 Новая фласка: {item.get_name_colored()} [{item.current_uses}/{item.flask_data['uses']}]")
                    else:
                        player.inventory.append(item)
                        loot_text.append(f"🧪 {item.get_name_colored()} (в инвентаре)")
                else:
                    player.inventory.append(item)
                    loot_text.append(item.get_name_colored())
        
        dungeon[player.current_position]["completed"] = True
        
        await callback.message.delete()
        
        victory_text = f"🎉 **ПОБЕДА!**\n\n" + "\n".join(result)
        if loot_text:
            victory_text += f"\n\n💰 **Добыча:**\n" + "\n".join(f"   {text}" for text in loot_text)
        
        await callback.message.answer(victory_text)
        
        await state.update_data(player=player, dungeon=dungeon)
        await asyncio.sleep(2)
        await show_dungeon(callback.message, state)
        await callback.answer()
        return
    
    if player.hp <= 0:
        await callback.message.edit_text("💀 **ТЫ ПОГИБ...**")
        await callback.answer()
        return
    
    await state.update_data(player=player, battle_enemy=enemy)
    await show_battle(callback, state, is_callback=True)
    await callback.answer()


# ============= СОБЫТИЯ =============

@dp.callback_query(lambda c: c.data.startswith('do_'))
async def do_event(callback: types.CallbackQuery, state: FSMContext):
    event_type = callback.data.split('_')[1]
    data = await state.get_data()
    player = data['player']
    dungeon = data['dungeon']
    
    current_event = dungeon[player.current_position]
    event = current_event["event"]
    
    result_text = ""
    
    if event_type == "chest":
        gold = 0
        items = []
        
        if event.get("rarity") == "magic":
            gold = random.randint(40, 70)
            if random.random() < 0.3:
                item = generate_melee_weapon("magic")
                if item:
                    items.append(item)
        elif event.get("rarity") == "rare":
            gold = random.randint(70, 120)
            if random.random() < 0.6:
                item = generate_melee_weapon("rare")
                if item:
                    items.append(item)
        else:
            gold = random.randint(15, 35)
            if random.random() < 0.1:
                item = generate_melee_weapon("common")
                if item:
                    items.append(item)
        
        player.gold += gold
        
        items_text = []
        for item in items:
            player.inventory.append(item)
            items_text.append(item.get_name_colored())
        
        items_str = "\n".join(items_text) if items_text else "ничего"
        result_text = f"📦 **СУНДУК ОТКРЫТ!**\n\n💰 Найдено: {gold} золота\n🎒 Предметы:\n{items_str}"
    
    elif event_type == "rest":
        heal = event["heal"]
        player.hp = min(player.max_hp, player.hp + heal)
        result_text = f"🔥 **ОТДЫХ**\n\nТы восстановил {heal} HP\n❤️ {player.hp}/{player.max_hp}"
    
    elif event_type == "trap":
        damage = event["damage"]
        damage = max(1, damage - player.defense // 4)
        player.hp -= damage
        
        if player.hp <= 0:
            await callback.message.edit_text("💀 **ТЫ ПОГИБ В ЛОВУШКЕ...**")
            await callback.answer()
            return
        
        result_text = f"⚠️ **ЛОВУШКА**\n\nТы потерял {damage} HP\n❤️ {player.hp}/{player.max_hp}"
    
    elif event_type == "altar":
        effects = [
            {"name": "Силы", "stat": "strength", "value": 3, "text": "💪 Сила +3"},
            {"name": "Ловкости", "stat": "dexterity", "value": 3, "text": "🏹 Ловкость +3"},
            {"name": "Интеллекта", "stat": "intelligence", "value": 3, "text": "📚 Интеллект +3"},
            {"name": "Здоровья", "stat": "max_hp", "value": 20, "text": "❤️ Макс. здоровье +20"},
            {"name": "Золота", "stat": "gold", "value": 60, "text": "💰 +60 золота"},
        ]
        
        effect = random.choice(effects)
        
        if effect["stat"] == "strength":
            player.strength += effect["value"]
        elif effect["stat"] == "dexterity":
            player.dexterity += effect["value"]
        elif effect["stat"] == "intelligence":
            player.intelligence += effect["value"]
        elif effect["stat"] == "max_hp":
            player.max_hp += effect["value"]
            player.hp += effect["value"]
        elif effect["stat"] == "gold":
            player.gold += effect["value"]
        
        result_text = f"🪦 **АЛТАРЬ {effect['name']}**\n\n{effect['text']}"
    
    dungeon[player.current_position]["completed"] = True
    
    await callback.message.edit_text(result_text)
    await state.update_data(player=player, dungeon=dungeon)
    await asyncio.sleep(2)
    await show_dungeon(callback.message, state)
    await callback.answer()


# ============= ИНВЕНТАРЬ И ЭКИПИРОВКА =============

@dp.callback_query(lambda c: c.data == "show_inventory")
async def show_inventory(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    
    if not player.inventory:
        text = "🎒 **ИНВЕНТАРЬ ПУСТ**"
    else:
        text = "🎒 **ИНВЕНТАРЬ**\n\n"
        
        equipment = []
        flasks = []
        
        for item in player.inventory:
            if item.item_type == ItemType.FLASK:
                flasks.append(item)
            else:
                equipment.append(item)
        
        if equipment:
            text += "**⚔️ Оружие:**\n"
            for i, item in enumerate(equipment):
                text += f"{i+1}. {item.get_name_colored()}\n"
        
        if flasks:
            text += "\n**🧪 Фласки:**\n"
            for i, item in enumerate(flasks, start=len(equipment)):
                text += f"{i+1}. {item.get_name_colored()} [{item.current_uses}/{item.flask_data['uses']}]\n"
    
    text += f"\n💰 Золото: {player.gold}"
    
    keyboard_buttons = []
    if player.inventory:
        row = []
        for i, item in enumerate(player.inventory[:5]):
            row.append(InlineKeyboardButton(text=f"🔍 {i+1}", callback_data=f"inspect_{i}"))
        if row:
            keyboard_buttons.append(row)
    
    keyboard_buttons.append([
        InlineKeyboardButton(text="📊 Экипировка", callback_data="show_equipment"),
        InlineKeyboardButton(text="◀ Назад", callback_data="back_to_dungeon")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('inspect_'))
async def inspect_item(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    
    item_index = int(callback.data.split('_')[1])
    
    if item_index < len(player.inventory):
        item = player.inventory[item_index]
        
        text = item.get_detailed_info()
        
        keyboard_buttons = []
        
        if item.item_type != ItemType.FLASK:
            can_equip, reason = player.can_equip(item)
            if can_equip:
                keyboard_buttons.append([
                    InlineKeyboardButton(text="⚔️ Экипировать", callback_data=f"equip_from_inspect_{item_index}")
                ])
            else:
                text += f"\n\n❌ Нельзя экипировать: {reason}"
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="◀ Назад", callback_data="show_inventory")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith('equip_from_inspect_'))
async def equip_from_inspect(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    
    item_index = int(callback.data.split('_')[3])
    
    if item_index < len(player.inventory):
        item = player.inventory[item_index]
        
        if item.item_type == ItemType.FLASK:
            await callback.answer("❌ Фласки нельзя экипировать!")
            return
        
        can_equip, reason = player.can_equip(item)
        if not can_equip:
            await callback.answer(f"❌ {reason}")
            return
        
        player.equip(item, ItemType.WEAPON)
        await callback.answer(f"✅ Экипировано: {item.name}")
    
    await show_inventory(callback.message, state)


@dp.callback_query(lambda c: c.data == "show_equipment")
async def show_equipment(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    
    text = "📊 **ЭКИПИРОВКА**\n\n"
    
    if player.equipped[ItemType.WEAPON]:
        weapon = player.equipped[ItemType.WEAPON]
        text += f"**⚔️ Оружие:**\n"
        text += f"└ {weapon.get_name_colored()}\n"
        
        min_dmg, max_dmg = weapon.get_damage_range()
        text += f"   Урон: {min_dmg}-{max_dmg}\n"
        text += f"   Скорость: {weapon.attack_speed:.2f}\n"
        text += f"   Крит: {weapon.crit_chance + weapon.stats.get('crit_chance', 0)}%\n"
        
        if weapon.affixes:
            text += f"\n   **Модификаторы:**\n"
            for affix_type, affix_data in weapon.affixes:
                value = weapon.stats.get(affix_data["stat"], 0)
                stat_names = {
                    "damage": "⚔️ Урон",
                    "max_hp": "❤️ Здоровье",
                    "defense": "🛡️ Защита",
                    "attack_speed": "⚡ Скорость",
                    "accuracy": "🎯 Точность",
                    "crit_chance": "🔥 Шанс крита",
                    "crit_multiplier": "💥 Множитель",
                    "life_on_hit": "🩸 Вампиризм"
                }
                stat_name = stat_names.get(affix_data["stat"], affix_data["stat"])
                text += f"   • {affix_data['name']}: {stat_name} +{value}\n"
    else:
        text += f"**⚔️ Оружие:** Пусто\n"
    
    text += f"\n📊 **ИТОГОВЫЕ СТАТЫ:**\n"
    text += f"❤️ HP: {player.hp}/{player.max_hp}\n"
    text += f"⚔️ Урон: {player.get_total_damage()}\n"
    text += f"🛡️ Защита: {player.defense}\n"
    text += f"🎯 Точность: {player.accuracy}%\n"
    text += f"🔥 Крит: {player.crit_chance}% x{player.crit_multiplier}%\n"
    text += f"💪 Сила: {player.strength}\n"
    text += f"🏹 Ловкость: {player.dexterity}\n"
    text += f"📚 Интеллект: {player.intelligence}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="show_inventory")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_dungeon")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "switch_flask")
async def switch_flask(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    
    if len(player.flasks) > 1:
        player.active_flask = (player.active_flask + 1) % len(player.flasks)
        flask = player.flasks[player.active_flask]
        await callback.answer(f"🔄 Активная фласка: {flask.name}")
    else:
        await callback.answer("❌ Только одна фласка")
    
    await state.update_data(player=player)
    await show_dungeon(callback.message, state)


@dp.callback_query(lambda c: c.data == "back_to_dungeon")
async def back_to_dungeon(callback: types.CallbackQuery, state: FSMContext):
    await show_dungeon(callback.message, state)
    await callback.answer()


# ============= СТАРТ =============

@dp.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    dungeon = generate_dungeon()
    player = Player()
    await state.update_data(player=player, dungeon=dungeon)
    await show_dungeon(message, state)


@dp.message(Command('ping'))
async def cmd_ping(message: types.Message):
    await message.answer("🏓 pong")


# ============= ЗАПУСК =============

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🗡️ **DUNGEON CRAWLER: PATH OF EXILE EDITION**")
    print("=" * 50)
    print("\n⚔️ **СИСТЕМА ОРУЖИЯ:**")
    print("- 14 типов оружия ближнего боя")
    print("- Более 100 уникальных моделей")
    print("- 5 уровней редкости (⚪🔵🟡🔴)")
    print("- Система требований (сила/ловкость/интеллект)")
    print("- Аффиксы с разными тирами")
    print("- Уникальное легендарное оружие")
    print("\n👤 **НОВАЯ МЕХАНИКА:**")
    print("- Игрок идет по подземелью из 20 событий")
    print("- Каждое событие можно пройти только один раз")
    print("- В конце подземелья ждет босс")
    print("\n👾 **МОНСТРЫ ПОДЗЕМЕЛЬЯ:**")
    print("- Огромный червь 🪱")
    print("- Жуткий кадавр 🧟")
    print("- И другие...")
    print("\n" + "=" * 50)
    print("\n🚀 Бот запущен! Отправь /start чтобы начать")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
