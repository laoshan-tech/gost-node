from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class EventStatsModel(BaseModel):
    totalConns: int
    currentConns: int
    inputBytes: int
    outputBytes: int
    totalErrs: int


class EventStatusModel(BaseModel):
    msg: str
    state: str


class EventModel(BaseModel):
    kind: str
    service: str
    client: Optional[str] = ""
    type: str
    status: Optional[EventStatusModel] = None
    stats: Optional[EventStatsModel] = None


class ObserveModel(BaseModel):
    events: List[EventModel]


@router.post("")
def index(events: ObserveModel):
    return {"success": True, "msg": "Hello World"}
