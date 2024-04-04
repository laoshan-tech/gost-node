import logging
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from . import RespModel

router = APIRouter()
logger = logging.getLogger(__name__)


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
async def observer(request: ObserveModel) -> RespModel:
    """
    Observer for GOST.
    :param request:
    :return:
    """
    for e in request.events:
        logger.info(e)

    return RespModel(success=True, message="Hello World!")
