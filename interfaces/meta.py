from pydantic import BaseModel, Field

class MetaTimeModel(BaseModel):
    date: str
    time: str
    ttamp_sec: int

class MetaTaskPeriodModel(BaseModel):
    start: MetaTimeModel
    end: MetaTimeModel

class MetaTaskCheckpointModel(BaseModel):
    name: str
    completed: bool

class MetaTaskModel(BaseModel):
    uuid: str
    periods: list[MetaTaskPeriodModel] = Field(default_factory=list)
    checklist: list[MetaTaskCheckpointModel] = Field(default_factory=list)

class MetaHabitModel(BaseModel):
    uuid: str
    real_count: int

class MetaModel(BaseModel):
    real_sleep_time: MetaTimeModel | None = None
    real_wakeup_time: MetaTimeModel | None = None
    tasks: list[MetaTaskModel] = Field(default_factory=list)
    habits: list[MetaHabitModel] = Field(default_factory=list)
