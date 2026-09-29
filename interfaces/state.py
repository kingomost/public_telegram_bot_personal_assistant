from pydantic import BaseModel, Field
from enum import Enum
from typing import Any

class UserWithPlanStateBreak(BaseModel):
    pass

class UserWithPlanStateChoose(BaseModel):
    pass

class UserWithPlanStateExecTask(BaseModel):
    pass

class UserWithPlanStatePauseInsideTask(BaseModel):
    pass

class UserWithPlanStateEnum(Enum):
    BREAK = UserWithPlanStateBreak
    CHOOSE = UserWithPlanStateChoose
    EXEC_TASK = UserWithPlanStateExecTask
    PAUSE_INSIDE_TASK = UserWithPlanStatePauseInsideTask

class UserWithPlanState(BaseModel):
    state: UserWithPlanStateEnum

class UserActiveStateEnum(Enum):
    WITHOUT_PLAN = 1
    PLANNING = 2
    WITH_PLAN = UserWithPlanState

class UserActiveState(BaseModel):
    state: UserActiveStateEnum

class UserStateEnum(Enum):
    NOT_ACTIVE = 1
    IDLE = 2
    ACTIVE = 3

class UserState(BaseModel):
    state: UserStateEnum

class FullState(BaseModel):
    active_task: str | None = None
    user_state: UserStateEnum | None = None
    gui_state: str | None = None
    user_last_activity_ttamp: int | None = None
    bot_last_activity_ttamp: int | None = None
    user_last_message_id: int | None = None
    bot_menu_message_id: int | None = None
    bot_dialog_message_id: int | None = None
    bot_hint_message_id: int | None = None
    tmp: dict[str, Any] = Field(default_factory=dict)
