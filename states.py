from aiogram.fsm.state import StatesGroup, State

class MealFlow(StatesGroup):
    waiting_grams    = State()   # after photo — user adjusts grams
    waiting_manual   = State()   # user types manual meal text
    waiting_goal     = State()   # user sets kcal goal
