from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class CommandRequest(BaseModel):
    command: str


class Recommendation(BaseModel):
    date: str
    time: str
    day: str
    energy: float
    habit: bool
    controllable_devices: List[str]
    score: float
    holiday: Optional[bool] = False


class AIResponse(BaseModel):
    recommendations: List[Recommendation]
    devices: List[str]
    patterns_per_day: Dict[str, Any]
    statistics: Dict[str, Any]
    error_messages: List[str]
    bonus_threshold: float


class HistoryCommand(BaseModel):
    timestamp: str
    command: str
    devices: List[str]


class PatternDay(BaseModel):
    day: str
    hours: List[Dict[str, int]]
    total: int
