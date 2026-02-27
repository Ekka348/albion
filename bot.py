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

# ============= АФФИКСЫ (МОДИФИКАТОРЫ) =============

PREFIXES = {
    # Оружие
    "weapon_damage": {"name": "Закаленное", "stat": "damage", "value": (2, 5), "tier": 1},
    "weapon_damage2": {"name": "Острое", "stat": "damage", "value": (5, 9), "tier": 2},
    "weapon_damage3": {"name": "Убийственное", "stat": "damage", "value": (9, 14), "tier": 3},
    
    # Здоровье
    "health": {"name": "Здоровое", "stat": "max_hp", "value": (10, 20), "tier": 1},
    "health2": {"name": "Крепкое", "stat": "max_hp", "value": (20, 35), "tier": 2},
    "health3": {"name": "Могучая", "stat": "max_hp", "value": (35, 50), "tier": 3},
    
    # Защита
    "defense": {"name": "Прочное", "stat": "defense", "value": (2, 4), "tier": 1},
    "defense2": {"name": "Твердое", "stat": "defense", "value": (4, 7), "tier": 2},
    "defense3": {"name": "Несокрушимое", "stat": "defense", "value": (7, 11), "tier": 3},
    
    # Скорость атаки
    "attack_speed": {"name": "Быстрое", "stat": "attack_speed", "value": (5, 10), "tier": 1},
    "attack_speed2": {"name": "Проворное", "stat": "attack_speed", "value": (10, 15), "tier": 2},
    "attack_speed3": {"name": "Вихревое", "stat": "attack_speed", "value": (15, 22), "tier": 3},
    
    # Точность
    "accuracy": {"name": "Точное", "stat": "accuracy", "value": (5, 10), "tier": 1},
    "accuracy2": {"name": "Меткое", "stat": "accuracy", "value": (10, 16), "tier": 2},
    "accuracy3": {"name": "Снайперское", "stat": "accuracy", "value": (16, 24), "tier": 3},
}

SUFFIXES = {
    # Шанс крита
    "crit_chance": {"name": "Удачи", "stat": "crit_chance", "value": (3, 6), "tier": 1},
    "crit_chance2": {"name": "Везучего", "stat": "crit_chance", "value": (6, 10), "tier": 2},
    "crit_chance3": {"name": "Рока", "stat": "crit_chance", "value": (10, 15), "tier": 3},
    
    # Множитель крита
    "crit_mult": {"name": "Боли", "stat": "crit_multiplier", "value": (10, 20), "tier": 1},
    "crit_mult2": {"name": "Агонии", "stat": "crit_multiplier", "value": (20, 30), "tier": 2},
    "crit_mult3": {"name": "Экзекуции", "stat": "crit_multiplier", "value": (30, 45), "tier": 3},
    
    # Регенерация
    "life_regen": {"name": "Жизни", "stat": "life_regen", "value": (2, 4), "tier": 1},
    "life_regen2": {"name": "Возрождения", "stat": "life_regen", "value": (4, 7), "tier": 2},
    "life_regen3": {"name": "Бессмертия", "stat": "life_regen", "value": (7, 11), "tier": 3},
    
    # Сопротивления
    "fire_res": {"name": "Пламени", "stat": "fire_res", "value": (5, 10), "tier": 1},
    "cold_res": {"name": "Льда", "stat": "cold_res", "value": (5, 10), "tier": 1},
    "lightning_res": {"name": "Молнии", "stat": "lightning_res", "value": (5, 10), "tier": 1},
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

# ============= КЛАССЫ ПРЕДМЕТОВ (УЛУЧШЕННОЕ ОТОБРАЖЕНИЕ) =============

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
            ItemRarity.NORMAL: "⚪",  # Белый
            ItemRarity.MAGIC: "🔵",   # Синий
            ItemRarity.RARE: "🟡",     # Желтый
            ItemRarity.UNIQUE: "🔴"    # Красный
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
        """Короткое отображение для инвентаря"""
        return f"{self.get_rarity_emoji()}{self.emoji} {self.name}"
    
    def get_detailed_info(self):
        """Подробное отображение со всеми параметрами"""
        lines = []
        
        # Заголовок с редкостью и типом
        lines.append(f"{self.get_rarity_emoji()} **{self.name}**")
        lines.append(f"└ {self.get_rarity_name()} {self.emoji} {self.get_type_name()}")
        lines.append("")
        
        # Аффиксы (префиксы и суффиксы)
        if self.affixes:
            lines.append("**Модификаторы:**")
            for affix_type, affix_data in self.affixes:
                prefix_suffix = "🔺 Префикс" if affix_type == AffixType.PREFIX else "🔻 Суффикс"
                value = self.stats.get(affix_data["stat"], 0)
                
                # Красивое название стата
                stat_names = {
                    "damage": "⚔️ Урон",
                    "max_hp": "❤️ Здоровье",
                    "defense": "🛡️ Защита",
                    "attack_speed": "⚡ Скорость атаки",
                    "accuracy": "🎯 Точность",
                    "crit_chance": "🔥 Шанс крита",
                    "crit_multiplier": "💥 Множитель крита",
                    "life_regen": "🌿 Регенерация",
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

class Flask(Item):
    def __init__(self, flask_type):
        flask_data = FLASKS[flask_type]
        super().__init__(flask_data["name"], ItemType.FLASK, flask_data["rarity"])
        self.flask_data = flask_data
        self.current_uses = flask_data["uses"]
        
    def use(self):
        """Использовать фласку"""
        if self.current_uses > 0:
            self.current_uses -= 1
            return self.flask_data["heal"]
        return 0
    
    def get_detailed_info(self):
        """Подробное отображение фласки"""
        lines = []
        
        # Заголовок с редкостью
        lines.append(f"{self.get_rarity_emoji()} **{self.name}**")
        lines.append(f"└ {self.get_rarity_name()} {self.emoji} Фласка")
        lines.append("")
        
        # Параметры фласки
        lines.append("**Параметры:**")
        
        # Цвет лечения в зависимости от величины
        heal_emoji = "💚" if self.flask_data["heal"] < 50 else "💛" if self.flask_data["heal"] < 100 else "❤️"
        lines.append(f"  {heal_emoji} Лечение: +{self.flask_data['heal']} HP")
        
        # Заряды
        charges_emoji = "🔋" * self.current_uses + "⚪" * (self.flask_data["uses"] - self.current_uses)
        lines.append(f"  {charges_emoji} Заряды: {self.current_uses}/{self.flask_data['uses']}")
        
        return "\n".join(lines)
    
    def get_status(self):
        """Короткий статус для боя"""
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
        
        self.exp = 0
        self.level = 1
        self.gold = 0
        
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
        
        # Текущая позиция в подземелье
        self.current_position = 0  # Индекс текущего события
        self.max_position = 20  # Всего 20 событий до выхода
        self.visited_positions = set()  # Посещенные позиции
    
    def get_total_damage(self):
        """Рассчитывает урон со случайным разбросом 15-30"""
        return random.randint(15, 30)
    
    def add_flask_charge(self):
        """Восстанавливает 1 заряд всем фласкам после убийства"""
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
        self.image_path = image_path  # Путь к изображению монстра

# ============= ПУЛ ПРОТИВНИКОВ ПОДЗЕМЕЛЬЯ =============
# Только подходящие для подземелья монстры с изображениями

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
    {"type": "rest", "name": "Место привала", "emoji": "🔥", "heal": 30, "chance": 25, "desc": "+30 HP"},
    {"type": "trap", "name": "Ловушка", "emoji": "⚠️", "damage": 20, "chance": 15, "desc": "-20 HP"},
    {"type": "altar", "name": "Древний алтарь", "emoji": "🪦", "effect": "random", "chance": 7, "desc": "Загадочный эффект"},
]

# ============= СИСТЕМА ГЕНЕРАЦИИ ПРЕДМЕТОВ =============

def generate_item(enemy_rarity):
    """Генерирует предмет экипировки на основе редкости врага"""
    
    # Шансы выпадения
    drop_chance = {
        "common": 15,
        "magic": 30,
        "rare": 50,
        "epic": 75,
        "legendary": 90,
        "boss": 100
    }.get(enemy_rarity, 15)
    
    if random.randint(1, 100) > drop_chance:
        return None
    
    # Определяем тип предмета
    item_type = random.choice([
        ItemType.WEAPON, ItemType.HELMET, ItemType.ARMOR, 
        ItemType.GLOVES, ItemType.BOOTS, ItemType.BELT,
        ItemType.RING, ItemType.AMULET
    ])
    
    # Определяем редкость предмета
    rarity_roll = random.random() * 100
    
    if rarity_roll < 60:
        item_rarity = ItemRarity.NORMAL
    elif rarity_roll < 85:
        item_rarity = ItemRarity.MAGIC
    elif rarity_roll < 98:
        item_rarity = ItemRarity.RARE
    else:
        item_rarity = ItemRarity.UNIQUE
    
    # Базовое имя
    base_names = {
        ItemType.WEAPON: "Оружие",
        ItemType.HELMET: "Шлем",
        ItemType.ARMOR: "Броня",
        ItemType.GLOVES: "Перчатки",
        ItemType.BOOTS: "Сапоги",
        ItemType.BELT: "Пояс",
        ItemType.RING: "Кольцо",
        ItemType.AMULET: "Амулет"
    }
    
    item = Item(base_names[item_type], item_type, item_rarity)
    
    # Добавляем аффиксы в зависимости от редкости
    if item_rarity == ItemRarity.MAGIC:
        # Магические: 1 префикс или 1 суффикс
        if random.choice([True, False]):
            affix = random.choice(list(PREFIXES.values()))
            item.add_affix(affix, AffixType.PREFIX)
        else:
            affix = random.choice(list(SUFFIXES.values()))
            item.add_affix(affix, AffixType.SUFFIX)
            
    elif item_rarity == ItemRarity.RARE:
        # Редкие: 2-3 аффикса
        num_affixes = random.randint(2, 3)
        for _ in range(num_affixes):
            if random.choice([True, False]):
                affix = random.choice(list(PREFIXES.values()))
            else:
                affix = random.choice(list(SUFFIXES.values()))
            item.add_affix(affix, random.choice([AffixType.PREFIX, AffixType.SUFFIX]))
            
    elif item_rarity == ItemRarity.UNIQUE:
        # Уникальные: 3-4 сильных аффикса
        num_affixes = random.randint(3, 4)
        for _ in range(num_affixes):
            high_tier_affixes = [a for a in list(PREFIXES.values()) + list(SUFFIXES.values()) 
                                if a["tier"] >= 2]
            affix = random.choice(high_tier_affixes)
            item.add_affix(affix, random.choice([AffixType.PREFIX, AffixType.SUFFIX]))
    
    # Генерируем имя на основе аффиксов
    if item.affixes:
        prefixes = [a for t, a in item.affixes if t == AffixType.PREFIX]
        suffixes = [a for t, a in item.affixes if t == AffixType.SUFFIX]
        
        name_parts = []
        if prefixes:
            name_parts.append(random.choice(prefixes)["name"])
        name_parts.append(base_names[item_type])
        if suffixes:
            name_parts.append(random.choice(suffixes)["name"])
        
        item.name = " ".join(name_parts)
    
    return item

def generate_flask():
    """Генерирует бутылку здоровья с шансом"""
    roll = random.random() * 100
    
    if roll < 60:  # 60% малая
        flask_type = "small_life"
    elif roll < 85:  # 25% средняя
        flask_type = "medium_life"
    elif roll < 97:  # 12% большая
        flask_type = "large_life"
    else:  # 3% божественная
        flask_type = "divine_life"
    
    return Flask(flask_type)

def generate_loot(enemy_rarity):
    """Генерирует полный лут с врага"""
    loot = []
    
    # Шанс на предмет экипировки
    drop_chance = {
        "common": 15,
        "magic": 30,
        "rare": 50,
        "epic": 75,
        "legendary": 90,
        "boss": 100
    }.get(enemy_rarity, 15)
    
    if random.randint(1, 100) <= drop_chance:
        item = generate_item(enemy_rarity)
        if item:
            loot.append(item)
    
    # Шанс на фласку
    flask_chance = {
        "common": 15,
        "magic": 25,
        "rare": 40,
        "epic": 60,
        "legendary": 80,
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
        "legendary": 200,
        "boss": 300
    }.get(enemy_rarity, 10)
    
    gold = random.randint(gold_base, gold_base * 2)
    loot.append({"type": "gold", "amount": gold})
    
    return loot

# ============= GACHA СИСТЕМА =============

def roll_enemy():
    """Роляет случайного врага"""
    roll = random.random() * 100
    
    if roll < 70:  # 70% обычные
        return random.choice(COMMON_ENEMIES), "common"
    elif roll < 95:  # 25% магические
        return random.choice(MAGIC_ENEMIES), "magic"
    elif roll < 99:  # 4% редкие
        return random.choice(RARE_ENEMIES), "rare"
    else:  # 1% боссы (редкие враги)
        return random.choice(BOSS_ENEMIES), "boss"

def roll_event():
    """Роляет случайное событие"""
    roll = random.random() * 100
    cumulative = 0
    
    for event in EVENT_POOL:
        cumulative += event["chance"]
        if roll < cumulative:
            return event
    
    return EVENT_POOL[0]

def generate_dungeon():
    """Генерирует подземелье из 20 событий"""
    dungeon = []
    
    # Гарантированно добавляем босса в конец
    for i in range(19):  # 19 случайных событий
        if random.random() < 0.6:  # 60% шанс на битву
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
        else:  # 40% шанс на событие
            event = roll_event()
            dungeon.append({
                "type": event["type"],
                "event": event,
                "name": event["name"],
                "emoji": event["emoji"],
                "completed": False
            })
    
    # Добавляем босса в конец
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
    """Показывает текущее состояние подземелья"""
    data = await state.get_data()
    
    if not data or 'dungeon' not in data:
        dungeon = generate_dungeon()
        player = Player()
        await state.update_data(player=player, dungeon=dungeon)
    else:
        player = data['player']
        dungeon = data['dungeon']
    
    current_event = dungeon[player.current_position]
    
    # Визуализация прогресса
    progress = []
    for i, event in enumerate(dungeon):
        if i < player.current_position:
            progress.append("✅")  # Пройдено
        elif i == player.current_position:
            if event["type"] in ["battle", "boss"]:
                progress.append(event["enemy"]["emoji"])  # Текущий монстр
            else:
                progress.append(event["emoji"])  # Текущее событие
        else:
            progress.append("⬜")  # Не пройдено
    
    progress_bar = " ".join(progress)
    
    # Информация о текущем событии
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
    
    # Статус фласок
    flask_status = []
    if player.flasks:
        active_flask = player.flasks[player.active_flask]
        flask_status.append(f"👉 {active_flask.get_status()}")
    flask_text = "\n".join(flask_status) if flask_status else "Нет фласок"
    
    # Статус игрока
    player_status = (
        f"👤 {player.hp}/{player.max_hp} ❤️ | Ур. {player.level}\n"
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
    
    # Кнопки
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
    
    # Кнопка "Идти дальше" появляется только если текущее событие пройдено
    if current_event.get("completed", False) and player.current_position < len(dungeon) - 1:
        buttons.append([InlineKeyboardButton(text="➡️ Идти дальше", callback_data="next_step")])
    
    # Кнопка "Выход" если дошли до конца
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
    """Идти дальше по подземелью"""
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
    """Выйти из подземелья (победа)"""
    data = await state.get_data()
    player = data['player']
    
    # Начисляем бонус за прохождение
    bonus_exp = player.level * 50
    bonus_gold = player.level * 100
    player.exp += bonus_exp
    player.gold += bonus_gold
    
    # Проверка на повышение уровня
    while player.exp >= player.level * 100:
        player.level += 1
        player.max_hp += 10
        player.hp = player.max_hp
    
    await callback.message.edit_text(
        f"🎉 **ПОДЗЕМЕЛЬЕ ПРОЙДЕНО!**\n\n"
        f"Ты нашел выход из темницы!\n\n"
        f"💰 Бонус: +{bonus_gold} золота\n"
        f"✨ Бонус: +{bonus_exp} опыта\n"
        f"👤 Новый уровень: {player.level}\n\n"
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
    """Показывает экран боя с изображением монстра"""
    data = await state.get_data()
    player = data['player']
    enemy = data['battle_enemy']
    
    rarity_color = {
        "common": "🟢",
        "magic": "🟣",
        "rare": "🟡",
        "boss": "⚫"
    }.get(enemy.rarity, "")
    
    # Информация о враге
    enemy_info = f"**{enemy.emoji} {enemy.name}** {rarity_color}\n❤️ {enemy.hp}/{enemy.max_hp} HP"
    
    # Статус фласок
    flask_status = []
    if player.flasks:
        active_flask = player.flasks[player.active_flask]
        flask_status.append(f"👉 {active_flask.get_status()}")
    flask_text = "\n".join(flask_status) if flask_status else "Нет фласок"
    
    # Статус игрока
    player_status = f"👤 {player.hp}/{player.max_hp} ❤️"
    
    text = (
        f"{enemy_info}\n\n"
        f"{player_status}\n"
        f"🧪 {flask_text}\n\n"
        f"Твой ход:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔪 Атаковать", callback_data="battle_attack")],
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
            # Текстовая версия без изображения
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
        # Fallback
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
        if random.randint(1, 100) <= player.accuracy:
            # Урон от 15 до 30
            base_damage = player.get_total_damage()
            
            # Проверка на крит (5% шанс)
            is_crit = random.randint(1, 100) <= player.crit_chance
            if is_crit:
                total_damage = int(base_damage * (player.crit_multiplier / 100))
                result.append(f"🔥 КРИТ! {total_damage} урона")
            else:
                total_damage = base_damage
                result.append(f"⚔️ {total_damage} урона")
            
            # Учитываем защиту врага
            damage_reduction = max(0, enemy.defense - player.defense) // 3
            final_damage = max(3, total_damage - damage_reduction)
            enemy.hp -= final_damage
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
                
                # Автоматическое переключение на следующую фласку
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
        # Победа
        player.exp += enemy.exp
        while player.exp >= player.level * 100:
            player.level += 1
            player.max_hp += 10
            player.hp = player.max_hp
            result.append(f"✨ **УРОВЕНЬ {player.level}!**")
        
        # Восстанавливаем заряды фласок
        charges = player.add_flask_charge()
        if charges > 0:
            result.append(f"🧪 Восстановлено {charges} зарядов фласок")
        
        # Генерируем лут
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
        
        # Отмечаем событие как пройденное
        dungeon[player.current_position]["completed"] = True
        
        # Удаляем сообщение с боем
        await callback.message.delete()
        
        # Отправляем сообщение о победе
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
                item = generate_item("magic")
                if item:
                    items.append(item)
        elif event.get("rarity") == "rare":
            gold = random.randint(70, 120)
            if random.random() < 0.6:
                item = generate_item("rare")
                if item:
                    items.append(item)
        else:
            gold = random.randint(15, 35)
            if random.random() < 0.1:
                item = generate_item("common")
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
        # Случайный эффект алтаря
        effects = [
            {"name": "Силы", "effect": "damage", "value": 3, "text": "⚔️ Урон увеличен на 3"},
            {"name": "Здоровья", "effect": "max_hp", "value": 20, "text": "❤️ Макс. здоровье +20"},
            {"name": "Защиты", "effect": "defense", "value": 3, "text": "🛡️ Защита +3"},
            {"name": "Золота", "effect": "gold", "value": 60, "text": "💰 +60 золота"},
            {"name": "Крита", "effect": "crit_chance", "value": 3, "text": "🔥 Шанс крита +3%"},
        ]
        
        effect = random.choice(effects)
        
        if effect["effect"] == "damage":
            player.damage += effect["value"]
        elif effect["effect"] == "max_hp":
            player.max_hp += effect["value"]
            player.hp += effect["value"]
        elif effect["effect"] == "defense":
            player.defense += effect["value"]
        elif effect["effect"] == "gold":
            player.gold += effect["value"]
        elif effect["effect"] == "crit_chance":
            player.crit_chance += effect["value"]
        
        result_text = f"🪦 **АЛТАРЬ {effect['name']}**\n\n{effect['text']}"
    
    # Отмечаем событие как пройденное
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
            text += "**⚔️ Экипировка:**\n"
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
            keyboard_buttons.append([
                InlineKeyboardButton(text="⚔️ Экипировать", callback_data=f"equip_from_inspect_{item_index}")
            ])
        
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
        
        player.equip(item, item.item_type)
        await callback.answer(f"✅ Экипировано: {item.name}")
    
    await show_inventory(callback.message, state)

@dp.callback_query(lambda c: c.data == "show_equipment")
async def show_equipment(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    player = data['player']
    
    text = "📊 **ЭКИПИРОВКА**\n\n"
    
    slot_names = {
        ItemType.WEAPON: "⚔️ Оружие",
        ItemType.HELMET: "⛑️ Шлем",
        ItemType.ARMOR: "🛡️ Броня",
        ItemType.GLOVES: "🧤 Перчатки",
        ItemType.BOOTS: "👢 Сапоги",
        ItemType.BELT: "🔗 Пояс",
        ItemType.RING: "💍 Кольцо",
        ItemType.AMULET: "📿 Амулет"
    }
    
    for slot_type, item in player.equipped.items():
        if item:
            text += f"**{slot_names[slot_type]}:**\n"
            text += f"└ {item.get_name_colored()}\n"
            
            for affix_type, affix_data in item.affixes:
                value = item.stats.get(affix_data["stat"], 0)
                stat_names = {
                    "damage": "⚔️ Урон",
                    "max_hp": "❤️ Здоровье",
                    "defense": "🛡️ Защита",
                    "attack_speed": "⚡ Скорость атаки",
                    "accuracy": "🎯 Точность",
                    "crit_chance": "🔥 Шанс крита",
                    "crit_multiplier": "💥 Множитель крита"
                }
                stat_name = stat_names.get(affix_data["stat"], affix_data["stat"])
                text += f"  {affix_data['name']}: {stat_name} +{value}\n"
            text += "\n"
        else:
            text += f"**{slot_names[slot_type]}:** Пусто\n\n"
    
    text += f"\n📊 **ИТОГОВЫЕ СТАТЫ:**\n"
    text += f"❤️ HP: {player.hp}/{player.max_hp}\n"
    text += f"⚔️ Урон: {player.get_total_damage()}\n"
    text += f"🛡️ Защита: {player.defense}\n"
    text += f"🎯 Точность: {player.accuracy}%\n"
    text += f"🔥 Крит: {player.crit_chance}% x{player.crit_multiplier}%"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="show_inventory")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_dungeon")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "switch_flask")
async def switch_flask(callback: types.CallbackQuery, state: FSMContext):
    """Переключение активной фласки"""
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
    print("🗺️ Dungeon Crawler запущено!")
    print("\n👤 **Новая механика:**")
    print("- Игрок идет по подземелью из 20 событий")
    print("- Каждое событие можно пройти только один раз")
    print("- После победы над монстром он исчезает")
    print("- В конце подземелья ждет босс")
    print("\n👾 **Монстры подземелья:**")
    print("- Огромный червь 🪱 (worm.jpg)")
    print("- Жуткий кадавр 🧟 (cadaver.jpg)")
    print("- Гниющий зомби 🧟‍♂️ (zombie.jpg)")
    print("- Костяной скелет 💀 (skeleton.jpg)")
    print("- Пещерный паук 🕷️ (spider.jpg)")
    print("- Блуждающий призрак 👻 (ghost.jpg)")
    print("\n✨ **Магические монстры:**")
    print("- Проклятый кадавр 🧟⚡ (cursed_cadaver.jpg)")
    print("- Призрачный страж 👻⚔️ (ghost_guardian.jpg)")
    print("- Огненный червь 🪱🔥 (fire_worm.jpg)")
    print("- Ледяной скелет 💀❄️ (ice_skeleton.jpg)")
    print("\n🔥 **Редкие монстры:**")
    print("- Культист смерти 🧙💀 (death_cultist.jpg)")
    print("- Демонический червь 🪱👹 (demon_worm.jpg)")
    print("- Костяной голем 🦴🗿 (bone_golem.jpg)")
    print("\n👑 **Боссы:**")
    print("- Повелитель червей 🪱👑 (worm_lord.jpg)")
    print("- Архилич 🧙‍♂️💀 (archlich.jpg)")
    print("- Король кадавров 👑🧟 (cadaver_king.jpg)")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
