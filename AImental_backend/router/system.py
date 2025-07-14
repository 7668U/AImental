# routers/system.py

from fastapi import APIRouter
from datetime import datetime
from pydantic import BaseModel

router = APIRouter(
    prefix="/system",
    tags=["System - 系统工具"],
)

class ServerTimeResponse(BaseModel):
    server_date: str # 格式 YYYY-MM-DD
    server_timestamp: int

@router.get("/time", response_model=ServerTimeResponse, summary="获取服务器当前日期和时间戳")
def get_server_time():
    """
    返回服务器当前的日期和Unix时间戳。
    前端应以此为标准来判断“今天”是哪一天。
    """
    now = datetime.now()
    return {
        "server_date": now.strftime('%Y-%m-%d'),
        "server_timestamp": int(now.timestamp())
    }