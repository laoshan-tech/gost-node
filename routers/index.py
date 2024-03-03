from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def index():
    return {"success": True, "msg": "Hello World"}
