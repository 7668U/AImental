# routers/checkin.py

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List
from datetime import date

# Import the table access object and Pydantic models from your model file
from model.status import checkin_table, CheckinModel, CheckinBaseModel
# Import the authentication dependency
# Make sure the path is correct based on your project structure
from .auth import get_current_user_id

# ---------------------------------------------------
# 1. Router Setup
# ---------------------------------------------------
router = APIRouter(
    prefix="/checkin",
    tags=["Check-ins - 每日打卡"],
    # All routes in this file will depend on a valid token
    dependencies=[Depends(get_current_user_id)]
)

# ---------------------------------------------------
# 2. API Endpoints
# ---------------------------------------------------

@router.post(
    "/",
    response_model=CheckinModel,
    summary="创建新的打卡记录"
)
def create_new_checkin(
    current_user_id: str = Depends(get_current_user_id),
    checkin_data: CheckinBaseModel = Body(...)
):
    """
    为当前用户创建一条新的打卡记录。
    每天只能创建一条。如果当天已存在记录，则会返回409冲突错误。
    """
    # Check if a check-in for today already exists to prevent duplicates
    today = date.today()
    existing_checkin = checkin_table.get_checkin_by_date(user_id=current_user_id, target_date=today)
    if existing_checkin:
        raise HTTPException(
            status_code=409,
            detail="A check-in for today already exists. You can update it instead."
        )
    
    # Create the new check-in
    new_checkin = checkin_table.create_checkin(user_id=current_user_id, data=checkin_data)
    if not new_checkin:
        raise HTTPException(status_code=500, detail="Could not create the check-in record.")
    
    return new_checkin


@router.get(
    "/month/{year}/{month}",
    response_model=List[CheckinModel],
    summary="获取指定月份的打卡记录"
)
def get_checkins_for_month(
    year: int,
    month: int,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    获取当前用户在指定年、月的所有打卡记录列表。
    用于前端渲染心情日历。
    """
    checkins = checkin_table.get_checkins_by_month(
        user_id=current_user_id,
        year=year,
        month=month
    )
    return checkins


@router.get(
    "/date/{record_date}",
    response_model=CheckinModel,
    summary="获取指定日期的打卡记录"
)
def get_checkin_for_date(
    record_date: date, # FastAPI will automatically parse "YYYY-MM-DD"
    current_user_id: str = Depends(get_current_user_id)
):
    """
    获取当前用户在特定日期的打卡记录。
    如果当天没有记录，则返回404错误。
    """
    checkin = checkin_table.get_checkin_by_date(user_id=current_user_id, target_date=record_date)
    if not checkin:
        raise HTTPException(status_code=404, detail="No check-in found for the specified date.")
    return checkin


@router.put(
    "/{checkin_id}",
    response_model=CheckinModel,
    summary="更新指定的打卡记录"
)
def update_existing_checkin(
    checkin_id: str,
    checkin_data: CheckinBaseModel = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    更新一条已经存在的打卡记录。
    会验证该记录是否属于当前登录用户。
    """
    # Security check: Ensure the check-in belongs to the current user
    existing_checkin = checkin_table.get_checkin_by_id(checkin_id)
    if not existing_checkin:
        raise HTTPException(status_code=404, detail="Check-in not found.")
    if existing_checkin.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this check-in.")

    # Perform the update
    updated_checkin = checkin_table.update_checkin(checkin_id=checkin_id, data=checkin_data)
    if not updated_checkin:
        raise HTTPException(status_code=500, detail="Failed to update the check-in.")
        
    return updated_checkin


@router.delete(
    "/{checkin_id}",
    summary="删除指定的打卡记录"
)
def delete_existing_checkin(
    checkin_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    删除一条打卡记录。
    会验证该记录是否属于当前登录用户。
    """
    # Security check: Ensure the check-in belongs to the current user
    existing_checkin = checkin_table.get_checkin_by_id(checkin_id)
    if not existing_checkin:
        raise HTTPException(status_code=404, detail="Check-in not found.")
    if existing_checkin.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this check-in.")

    # Perform the deletion
    if not checkin_table.delete_checkin(checkin_id):
        raise HTTPException(status_code=500, detail="Failed to delete the check-in.")

    return {"message": "Check-in successfully deleted."}