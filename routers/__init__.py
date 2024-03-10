from typing import Union

from pydantic import BaseModel


class RespModel(BaseModel):
    success: bool = True
    msg: str = "success"
    data: Union[dict, list] = None
