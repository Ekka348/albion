async def show_dungeon(message: types.Message, state: FSMContext):
    """Показывает текущее состояние подземелья"""
    data = await state.get_data()
    
    if not data or 'floors' not in data:
        floors = [generate_floor(i) for i in range(1, 11)]
        player = Player()
        await state.update_data(player=player, floors=floors)
    else:
        player = data['player']
        floors = data['floors']
    
    current_event = floors[player.current_floor - 1]
    
    # Визуализация подземелья
    dungeon_view = f"""
🟫🟫🟫🟫🟫🟫

👨‍🦱
{current_event['emoji']} 

🟫🟫🟫🟫🟫🟫
"""
    
    # Информация о текущем этаже
    floor_info = f"📍 **Этаж {player.current_floor}/10**\n\n"
    
    if current_event["type"] in ["battle", "boss"]:
        enemy = current_event["enemy"]
        rarity_text = {
            "common": "🟢 Обычный",
            "magic": "🟣 Магический",
            "rare": "🟡 Редкий",
            "epic": "🔴 Эпический",
            "boss": "⚫ БОСС"
        }.get(current_event.get("rarity"), "")
        floor_info += f"**{enemy['emoji']} {enemy['name']}**\n{rarity_text}\n❤️ HP: {enemy['hp']}"
    else:
        event = current_event["event"]
        floor_info += f"**{event['emoji']} {event['name']}**"
    
    # Статус игрока
    flask_status = []
    if player.flasks:
        for i, flask in enumerate(player.flasks):
            marker = "👉" if i == player.active_flask else "  "
            flask_status.append(f"{marker} {flask.get_name_colored()} [{flask.current_uses}/{flask.flask_data['uses']}]")
    flask_text = "\n".join(flask_status) if flask_status else "Нет фласок"
    
    player_status = (
        f"\n\n👤 **Уровень {player.level}**\n"
        f"❤️ {player.hp}/{player.max_hp} HP\n"
        f"⚔️ Урон: 15-30\n"
        f"🛡️ Защита: {player.defense}\n"
        f"🎯 Точность: {player.accuracy}%\n"
        f"🔥 Крит: {player.crit_chance}% x{player.crit_multiplier}%\n"
        f"💰 Золото: {player.gold}\n"
        f"✨ Опыт: {player.exp}/{player.level * 100}\n\n"
        f"🧪 **Фласки ({len(player.flasks)}/{player.max_flasks}):**\n{flask_text}"
    )
    
    text = f"{dungeon_view}\n\n{floor_info}{player_status}"
    
    # Кнопки
    buttons = []
    
    if current_event["type"] in ["battle", "boss"]:
        buttons.append([InlineKeyboardButton(text="⚔️ Вступить в бой", callback_data="start_battle")])
    elif current_event["type"] == "chest":
        buttons.append([InlineKeyboardButton(text="📦 Открыть сундук", callback_data="open_chest")])
    elif current_event["type"] == "rest":
        buttons.append([InlineKeyboardButton(text="🔥 Отдохнуть", callback_data="take_rest")])
    elif current_event["type"] == "trap":
        buttons.append([InlineKeyboardButton(text="⚠️ Пройти ловушку", callback_data="trigger_trap")])
    
    if player.current_floor < player.max_floor:
        buttons.append([InlineKeyboardButton(text="⬇️ Спуститься ниже", callback_data="next_floor")])
    
    buttons.append([
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="show_inventory"),
        InlineKeyboardButton(text="📊 Экипировка", callback_data="show_equipment")
    ])
    
    if player.flasks:
        buttons.append([InlineKeyboardButton(text="🧪 Переключить фласку", callback_data="switch_flask")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await state.update_data(player=player, floors=floors)
    
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except:
        await message.answer(text, reply_markup=keyboard)

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
