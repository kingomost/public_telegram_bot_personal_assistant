import os


def _integer_setting(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        return int(raw_value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be an integer") from error


OWNER_ID = _integer_setting("OWNER_ID", 0)
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
TIME_ZONE = os.getenv("TIME_ZONE", "UTC").strip()
BOT_TICK_INTERVAL_SEC = _integer_setting("BOT_TICK_INTERVAL_SEC", 360)

GOAL_TAG = "#goal"
RITUAL_TAG = "#ritual"
OTHER_TAG = "#other"
