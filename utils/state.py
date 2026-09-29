from typing import Any, cast
from collections.abc import Mapping
from interfaces.state import FullState, UserStateEnum
from memory.memory import Memory

_UNSET = object()


def is_silent_mode(state: FullState) -> bool:
    return state.user_state == UserStateEnum.NOT_ACTIVE


def deep_merge(dst: dict[str, Any], src: Mapping[str, Any]) -> dict[str, Any]:
    for key, value in src.items():
        if (
            key in dst
            and isinstance(dst[key], dict)
            and isinstance(value, Mapping)
        ):
            deep_merge(
                cast(dict[str, Any], dst[key]),
                cast(dict[str, Any], value),
            )
        else:
            dst[key] = value

    return dst

async def update_state(
    active_task: str | None | object = _UNSET,
    user_state: UserStateEnum | None | object = _UNSET,
    gui_state: str | None | object = _UNSET,
    user_last_activity_ttamp: int | None | object = _UNSET,
    bot_last_activity_ttamp: int | None | object = _UNSET,
    user_last_message_id: int | None | object = _UNSET,
    bot_menu_message_id: int | None | object = _UNSET,
    bot_dialog_message_id: int | None | object = _UNSET,
    bot_hint_message_id: int | None | object = _UNSET,
    tmp: Mapping[str, Any] | None = None,
    replace_tmp: bool = False,
) -> FullState:
    state = Memory(path="./state.json", model=FullState)
    changes = {
        "active_task": active_task,
        "user_state": user_state,
        "gui_state": gui_state,
        "user_last_activity_ttamp": user_last_activity_ttamp,
        "bot_last_activity_ttamp": bot_last_activity_ttamp,
        "user_last_message_id": user_last_message_id,
        "bot_menu_message_id": bot_menu_message_id,
        "bot_dialog_message_id": bot_dialog_message_id,
        "bot_hint_message_id": bot_hint_message_id,
    }
    for field, value in changes.items():
        if value is not _UNSET:
            setattr(state.data, field, value)

    if tmp is not None:
        state.data.tmp = (
            dict(tmp) if replace_tmp else deep_merge(dict(state.data.tmp), tmp)
        )
    state.save()
    return state.data
