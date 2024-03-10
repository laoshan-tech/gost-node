from fastapi import APIRouter

from . import RespModel

router = APIRouter()


@router.get("/")
async def index() -> RespModel:
    """
    Index.
    :return:
    """
    return RespModel(success=True, message="Hello World!")
