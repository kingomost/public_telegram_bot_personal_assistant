from typing import Iterable

from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButtonPollType,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder

class MainMenu:
    PROGRESS = "Progress"
    # START_TASK OR ACTIVE_TASK
    START_TASK = "Start task"
    ACTIVE_TASK = "⏲ Active task"
    REPORT = "Reports"
    PLANNING = "Planning"
    HABITS = "Habits"
    HABIT_TRACKER = "Habit Tracker"
    RITUALS = "Rituals"
    GOAL = "Goal"
    BACKLOG = "Inbox/Backlog"
    SILENT_MODE = "⨉ Set Silent Mode"
    UNSILENT_MODE = "✔️ Set Active Mode"

class ExitMenu:
    GO_TO_MAIN_MENU = "➫ BACK TO MAIN MENU"

def get_main_menu(active_task: bool, silent_mode: bool) -> ReplyKeyboardMarkup:
    btn = KeyboardButton
    keyboard = []
    if active_task:
        keyboard.append([
            btn(text = MainMenu.HABIT_TRACKER),
            btn(text = MainMenu.ACTIVE_TASK)
        ])
    else:
        keyboard.append([
            btn(text = MainMenu.HABIT_TRACKER),
            btn(text = MainMenu.START_TASK)
        ])
    keyboard.append([
        btn(text = MainMenu.REPORT),
        btn(text = MainMenu.PROGRESS)
    ])
    keyboard.append([
        btn(text = MainMenu.BACKLOG),
        btn(text = MainMenu.PLANNING)
    ])
    keyboard.append([
        btn(text = MainMenu.HABITS), 
        btn(text = MainMenu.RITUALS)
    ])
    if silent_mode:
        keyboard.append([
            btn(text = MainMenu.GOAL),
            btn(text = MainMenu.UNSILENT_MODE)
        ])
    else:
        keyboard.append([
            btn(text = MainMenu.GOAL),
            btn(text = MainMenu.SILENT_MODE)
        ])

    markup = ReplyKeyboardMarkup(
        keyboard = keyboard,
        resize_keyboard = True,
    )
    return markup

def get_exit_menu() -> ReplyKeyboardMarkup:
    btn = KeyboardButton
    keyboard = [
        [btn(text = ExitMenu.GO_TO_MAIN_MENU)]
    ]
    markup = ReplyKeyboardMarkup(
        keyboard = keyboard,
        resize_keyboard = True,
    )
    return markup
