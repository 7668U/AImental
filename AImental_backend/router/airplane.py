
# AImental_backend/router/airplane.py

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional

# 1. 导入模型和数据库操作类
from model.airplane import (
    paper_airplane_table, 
    PaperAirplaneCreate, 
    PaperAirplaneResponse,
    PaperAirplaneCollect,
    PaperAirplane # Import PaperAirplane model for type hinting
)

# 2. 导入认证依赖
from .auth import get_current_user_id

# ---------------------------------------------------
# Router Setup
# ---------------------------------------------------
router = APIRouter(
    prefix="/airplane",
    tags=["Airplane - 纸飞机"],
)

# ---------------------------------------------------
# API Endpoints
# ---------------------------------------------------

@router.post("/throw", summary="扔出一个纸飞机", response_model=PaperAirplaneResponse)
def throw_paper_airplane(
    airplane_data: PaperAirplaneCreate,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    创建一个新的纸飞机。需要用户登录。
    - **message**: 纸飞机的内容。
    """
    if not airplane_data.message or not airplane_data.message.strip():
        raise HTTPException(status_code=400, detail="纸飞机的内容不能为空哦。")

    new_airplane = paper_airplane_table.throw_airplane(
        user_id=current_user_id,
        message=airplane_data.message
    )
    
    return new_airplane

@router.get(
    "/available", 
    summary="获取当前用户可捡的纸飞机列表", 
    response_model=List[PaperAirplaneResponse]
)
def get_available_airplanes(
    current_user_id: str = Depends(get_current_user_id),
    limit: int = Query(6, ge=1, le=10, description="获取纸飞机的数量，最多10个")
):
    """
    获取当前用户可以捡的纸飞机列表（非自己发布，且未捡过）。
    """
    airplanes = paper_airplane_table.get_available_airplanes(current_user_id, limit)
    return airplanes

@router.post(
    "/{airplane_id}/pickup", 
    summary="捡起一个特定纸飞机", 
    response_model=PaperAirplaneResponse
)
def pickup_specific_airplane(
    airplane_id: int,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    捡起一个特定ID的纸飞机。
    - **airplane_id**: 要捡起的纸飞机的ID。
    """
    # First, check if the airplane exists and is available for this user
    # We can reuse the logic from get_available_airplanes for validation
    available_airplanes = paper_airplane_table.get_available_airplanes(current_user_id, limit=None) # Get all available to check specific ID
    
    target_airplane: Optional[PaperAirplane] = None
    for ap in available_airplanes:
        if ap.id == airplane_id:
            target_airplane = ap
            break

    if not target_airplane:
        raise HTTPException(status_code=404, detail="这个纸飞机不存在，或者你已经捡过它了，或者这是你自己的纸飞机哦。")

    # Record the pickup
    success = paper_airplane_table.record_airplane_pickup(current_user_id, airplane_id)

    if not success:
        # This case should ideally be caught by the check above, but good for robustness
        raise HTTPException(status_code=400, detail="无法捡起纸飞机，可能你已经捡过它了。")

    return target_airplane # Return the details of the picked airplane

@router.post(
    "/{airplane_id}/collect",
    summary="把已捡起的纸飞机收进飞机篓",
    response_model=PaperAirplaneResponse
)
def collect_specific_airplane(
    airplane_id: int,
    collect_data: Optional[PaperAirplaneCollect] = None,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    将当前用户已经捡起的纸飞机收进自己的飞机篓。
    """
    collect_data = collect_data or PaperAirplaneCollect()
    collected_airplane = paper_airplane_table.collect_airplane(
        user_id=current_user_id,
        airplane_id=airplane_id,
        asset_number=collect_data.asset_number,
        asset_path=collect_data.asset_path
    )
    if not collected_airplane:
        raise HTTPException(status_code=404, detail="这个纸飞机还不能收进飞机篓哦。")

    return collected_airplane

@router.get(
    "/collected",
    summary="查看我的飞机篓",
    response_model=List[PaperAirplaneResponse]
)
def get_collected_airplanes(
    current_user_id: str = Depends(get_current_user_id),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量")
):
    """
    获取当前用户收进飞机篓的纸飞机列表，按收起时间倒序排列。
    """
    collected_airplanes = paper_airplane_table.get_collected_airplanes(
        user_id=current_user_id,
        page=page,
        page_size=page_size
    )
    return collected_airplanes

@router.delete(
    "/{airplane_id}/collect",
    summary="从飞机篓丢弃一个已收起的纸飞机"
)
def discard_collected_airplane(
    airplane_id: int,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    从当前用户的飞机篓中移除一架纸飞机，不删除原始纸飞机内容。
    """
    success = paper_airplane_table.discard_collected_airplane(
        user_id=current_user_id,
        airplane_id=airplane_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="这个纸飞机不在你的纸篓里哦。")

    return {"message": "已从飞机篓丢弃。"}

@router.get("/my-history", summary="查看我扔出的纸飞机记录", response_model=List[PaperAirplaneResponse])
def get_my_airplane_history(
    current_user_id: str = Depends(get_current_user_id),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=50, description="每页数量")
):
    """
    获取当前用户扔出的所有纸飞机的历史记录，按时间倒序排列。
    """
    history = paper_airplane_table.get_my_airplanes(
        user_id=current_user_id,
        page=page,
        page_size=page_size
    )
    return history
