import json
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states import MealFlow
from keyboards import grams_keyboard, confirm_keyboard, main_keyboard
from gemini import analyze_food_photo, analyze_food_text
from database import add_meal, get_today, get_week, delete_last_meal, set_goal, get_goal

router = Router()

# ──────────────────────────────────────────────
# /start
# ──────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(
        "👋 Привет! Я считаю калории.\n\n"
        "📸 *Отправь фото еды* — я определю блюдо и КБЖУ\n"
        "✏️ *Или напиши* — например: «200г гречки с курицей»\n\n"
        "Используй кнопки внизу для статистики.",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

# ──────────────────────────────────────────────
# Photo handler
# ──────────────────────────────────────────────
@router.message(F.photo)
async def handle_photo(msg: Message, state: FSMContext, bot: Bot):
    await state.clear()
    thinking = await msg.answer("🔍 Анализирую фото...")

    photo = msg.photo[-1]
    file = await bot.get_file(photo.file_id)
    image_bytes = await bot.download_file(file.file_path)
    image_data = image_bytes.read()

    try:
        result = await analyze_food_photo(image_data)
    except Exception as e:
        await thinking.delete()
        await msg.answer(f"❌ Не удалось распознать. Попробуй описать текстом.\n\n`{e}`", parse_mode="Markdown")
        return

    await thinking.delete()

    conf_emoji = {"high": "✅", "medium": "🟡", "low": "🔴"}.get(result.get("confidence", "low"), "🟡")
    g = result["estimated_grams"]
    kcal = round(result["kcal_per_100g"] * g / 100)

    text = (
        f"{conf_emoji} *{result['name']}*\n"
        f"Оценка порции: **{g}г** → ~{kcal} ккал\n\n"
        f"На 100г: {result['kcal_per_100g']} ккал | "
        f"Б {result['protein_per_100g']}г | "
        f"Ж {result['fat_per_100g']}г | "
        f"У {result['carbs_per_100g']}г"
    )
    if result.get("note"):
        text += f"\n\n💬 {result['note']}"

    text += "\n\n*Выбери граммовку или введи своё:*"

    await state.set_state(MealFlow.waiting_grams)
    await state.update_data(result=result)

    await msg.answer(text, parse_mode="Markdown", reply_markup=grams_keyboard(g))

# ──────────────────────────────────────────────
# Grams callback
# ──────────────────────────────────────────────
@router.callback_query(MealFlow.waiting_grams, F.data.startswith("grams:"))
async def on_grams(cb: CallbackQuery, state: FSMContext):
    value = cb.data.split(":")[1]

    if value == "custom":
        await state.set_state(MealFlow.waiting_grams)
        await state.update_data(awaiting_custom=True)
        await cb.message.answer("✏️ Введи граммы числом:")
        await cb.answer()
        return

    grams = int(value)
    data = await state.get_data()
    result = data["result"]
    await _show_confirm(cb.message, state, result, grams)
    await cb.answer()

@router.message(MealFlow.waiting_grams, F.text.regexp(r"^\d+$"))
async def on_custom_grams(msg: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("awaiting_custom"):
        return
    grams = int(msg.text)
    result = data["result"]
    await _show_confirm(msg, state, result, grams)

async def _show_confirm(msg_or_cb, state: FSMContext, result: dict, grams: int):
    kcal    = round(result["kcal_per_100g"]    * grams / 100, 1)
    protein = round(result["protein_per_100g"] * grams / 100, 1)
    fat     = round(result["fat_per_100g"]     * grams / 100, 1)
    carbs   = round(result["carbs_per_100g"]   * grams / 100, 1)

    text = (
        f"📝 *{result['name']}* — {grams}г\n"
        f"🔥 {kcal} ккал\n"
        f"Б {protein}г · Ж {fat}г · У {carbs}г\n\n"
        "Сохранить?"
    )

    await state.update_data(final_grams=grams, final_kcal=kcal,
                            final_protein=protein, final_fat=fat, final_carbs=carbs)
    await state.set_state(MealFlow.waiting_grams)

    await msg_or_cb.answer(text, parse_mode="Markdown", reply_markup=confirm_keyboard())

# ──────────────────────────────────────────────
# Save / Cancel callbacks
# ──────────────────────────────────────────────
@router.callback_query(F.data == "save")
async def on_save(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    result = data.get("result", {})

    await add_meal(
        user_id=cb.from_user.id,
        name=result.get("name", "Блюдо"),
        grams=data["final_grams"],
        kcal=data["final_kcal"],
        protein=data["final_protein"],
        fat=data["final_fat"],
        carbs=data["final_carbs"],
    )
    await state.clear()

    goal = await get_goal(cb.from_user.id)
    today = await get_today(cb.from_user.id)
    total_kcal = sum(m["kcal"] for m in today)
    remaining = goal - total_kcal
    bar = _progress_bar(total_kcal, goal)

    await cb.message.edit_text(
        f"✅ Сохранено!\n\n"
        f"Сегодня: {total_kcal:.0f} / {goal} ккал\n"
        f"{bar}\n"
        f"Осталось: {max(0, remaining):.0f} ккал",
        parse_mode="Markdown"
    )
    await cb.answer()

@router.callback_query(F.data == "cancel")
async def on_cancel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("❌ Отменено.")
    await cb.answer()

# ──────────────────────────────────────────────
# Manual text add
# ──────────────────────────────────────────────
@router.message(F.text == "✏️ Добавить вручную")
async def manual_start(msg: Message, state: FSMContext):
    await state.clear()
    await state.set_state(MealFlow.waiting_manual)
    await msg.answer(
        "✏️ Напиши что съел, например:\n"
        "• 200г гречки с курицей\n"
        "• тарелка борща\n"
        "• банан и стакан кефира"
    )

@router.message(MealFlow.waiting_manual, F.text)
async def manual_analyze(msg: Message, state: FSMContext):
    thinking = await msg.answer("🔍 Анализирую...")
    try:
        result = await analyze_food_text(msg.text)
    except Exception as e:
        await thinking.delete()
        await msg.answer(f"❌ Ошибка: {e}")
        return

    await thinking.delete()
    await state.set_state(MealFlow.waiting_grams)
    await state.update_data(result=result, awaiting_custom=False)

    g = result["estimated_grams"]
    kcal = round(result["kcal_per_100g"] * g / 100)

    text = (
        f"✅ *{result['name']}*\n"
        f"Оценка: {g}г → ~{kcal} ккал\n"
        f"На 100г: Б {result['protein_per_100g']} · Ж {result['fat_per_100g']} · У {result['carbs_per_100g']}\n\n"
        "*Уточни граммовку:*"
    )
    await msg.answer(text, parse_mode="Markdown", reply_markup=grams_keyboard(g))

# ──────────────────────────────────────────────
# Today stats
# ──────────────────────────────────────────────
@router.message(F.text == "📊 Сегодня")
async def today_stats(msg: Message):
    meals = await get_today(msg.from_user.id)
    goal  = await get_goal(msg.from_user.id)

    if not meals:
        await msg.answer("Сегодня ничего не записано. Отправь фото или добавь вручную 📸")
        return

    total_k = sum(m["kcal"] for m in meals)
    total_p = sum(m["protein"] for m in meals)
    total_f = sum(m["fat"] for m in meals)
    total_c = sum(m["carbs"] for m in meals)

    lines = ["*Сегодня:*\n"]
    for i, m in enumerate(meals, 1):
        lines.append(f"{i}. {m['name']} ({m['grams']:.0f}г) — {m['kcal']:.0f} ккал")

    bar = _progress_bar(total_k, goal)
    lines.append(f"\n🔥 Итого: *{total_k:.0f}* / {goal} ккал")
    lines.append(bar)
    lines.append(f"Б {total_p:.1f}г · Ж {total_f:.1f}г · У {total_c:.1f}г")

    remain = goal - total_k
    if remain > 0:
        lines.append(f"\nОсталось: {remain:.0f} ккал")
    else:
        lines.append(f"\n⚠️ Превышение на {abs(remain):.0f} ккал")

    await msg.answer("\n".join(lines), parse_mode="Markdown")

# ──────────────────────────────────────────────
# Week stats
# ──────────────────────────────────────────────
@router.message(F.text == "📅 Неделя")
async def week_stats(msg: Message):
    rows = await get_week(msg.from_user.id)
    goal = await get_goal(msg.from_user.id)

    if not rows:
        await msg.answer("Нет данных за последние 7 дней.")
        return

    lines = ["*За 7 дней:*\n"]
    for r in rows:
        d = r["date"][5:]  # MM-DD
        bar = _progress_bar(r["kcal"], goal, width=10)
        lines.append(f"`{d}` {bar} {r['kcal']:.0f} ккал")

    avg = sum(r["kcal"] for r in rows) / len(rows)
    lines.append(f"\nСреднее: *{avg:.0f}* ккал/день")

    await msg.answer("\n".join(lines), parse_mode="Markdown")

# ──────────────────────────────────────────────
# Undo last meal
# ──────────────────────────────────────────────
@router.message(F.text == "↩️ Отменить последнее")
async def undo_last(msg: Message):
    deleted = await delete_last_meal(msg.from_user.id)
    if deleted:
        await msg.answer("↩️ Последний приём пищи удалён.")
    else:
        await msg.answer("Нечего отменять — сегодня пусто.")

# ──────────────────────────────────────────────
# Goal
# ──────────────────────────────────────────────
@router.message(F.text == "🎯 Цель")
async def goal_show(msg: Message, state: FSMContext):
    await state.clear()
    goal = await get_goal(msg.from_user.id)
    await state.set_state(MealFlow.waiting_goal)
    await msg.answer(
        f"Текущая цель: *{goal} ккал/день*\n\n"
        "Отправь новое число чтобы изменить (например: `1800`):",
        parse_mode="Markdown"
    )

@router.message(MealFlow.waiting_goal, F.text.regexp(r"^\d+$"))
async def goal_set(msg: Message, state: FSMContext):
    kcal = int(msg.text)
    if kcal < 500 or kcal > 10000:
        await msg.answer("Введи число от 500 до 10000.")
        return
    await set_goal(msg.from_user.id, kcal)
    await state.clear()
    await msg.answer(f"✅ Цель установлена: *{kcal} ккал/день*", parse_mode="Markdown")

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def _progress_bar(current: float, goal: float, width: int = 12) -> str:
    ratio = min(current / goal, 1.0) if goal > 0 else 0
    filled = round(ratio * width)
    color = "🟩" if ratio < 0.85 else ("🟨" if ratio < 1.0 else "🟥")
    return color * filled + "⬜" * (width - filled)
