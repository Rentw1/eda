from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def grams_keyboard(suggested: int) -> InlineKeyboardMarkup:
    options = [
        max(50, suggested - 100),
        max(50, suggested - 50),
        suggested,
        suggested + 50,
        suggested + 100,
    ]
    # deduplicate preserving order
    seen = set()
    unique = []
    for v in options:
        if v not in seen:
            seen.add(v)
            unique.append(v)

    buttons = [
        InlineKeyboardButton(text=f"{g}г", callback_data=f"grams:{g}")
        for g in unique
    ]
    buttons.append(InlineKeyboardButton(text="✏️ Своё", callback_data="grams:custom"))

    rows = [buttons[:3], buttons[3:]]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Сохранить", callback_data="save"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
    ]])

def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Сегодня"), KeyboardButton(text="📅 Неделя")],
            [KeyboardButton(text="✏️ Добавить вручную"), KeyboardButton(text="↩️ Отменить последнее")],
            [KeyboardButton(text="🎯 Цель")],
        ],
        resize_keyboard=True,
    )
