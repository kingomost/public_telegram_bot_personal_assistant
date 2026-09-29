__all__ = ("router",)

from aiogram import Router

from .commands import router as commands
from .planning import router as planning
from .planning_callbacks import router as planning_callbacks
from .backlog import router as backlog
from .habits_rituals import router as habits_rituals
from .habit_tracker import router as habit_tracker
from .goals import router as goals
from .execution import router as execution
from .dashboard import router as dashboard
from .echo import router as echo

router = Router(name=__name__)

router.include_router(commands)
# ALL MAIN ROUTERS START
router.include_router(planning)
router.include_router(planning_callbacks)
router.include_router(backlog)
router.include_router(habits_rituals)
router.include_router(habit_tracker)
router.include_router(goals)
router.include_router(execution)
router.include_router(dashboard)
# ALL MAIN ROUTERS END
router.include_router(echo)
