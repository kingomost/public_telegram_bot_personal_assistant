from aiogram.fsm.state import State, StatesGroup

class FsmState(StatesGroup):
    PLAN = State() # will not used because without str message
    TASK = State()
    CHECKLIST = State()
    HABIT = State()
    REMINDER = State()
    QUICK_TASK = State()
    GOAL = State()
