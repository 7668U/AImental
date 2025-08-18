# routers/checkin.py

# 1. 导入所有需要的模块
from fastapi import APIRouter, Depends, HTTPException, Body, File, UploadFile
from typing import List, Optional,Dict 
from datetime import date

# 2. 从项目其他文件中导入
# 【重要】确保从 model.checkin 导入了 checkin_table
from model.status import checkin_table, CheckinModel, CheckinBaseModel
from .auth import get_current_user_id

# --- 心情中英文翻译地图 (请确保它在这里) ---
MOOD_TRANSLATION_MAP = {
    '开心': 'happy',
    '平静': 'calm',
    '难过': 'sad',
    '生气': 'angry',
    '放松': 'relaxed',
    '迷茫': 'confused',
    '尴尬': 'embarass',
    '疲惫': 'tired',
    '兴奋': 'excited',
}
# ---------------------------------------------------
# Router Setup
# ---------------------------------------------------
router = APIRouter(
    prefix="/checkin",
    tags=["Check-ins - 每日打卡"],
    dependencies=[Depends(get_current_user_id)]
)

# ---------------------------------------------------
# API Endpoints
# ---------------------------------------------------
# --- 【修改】创建接口，恢复为只接收JSON ---
@router.post(
    "/",
    response_model=CheckinModel,
    summary="创建新的打卡记录 (不含图片)"
)
def create_new_checkin(
    checkin_data: CheckinBaseModel = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """为当前用户创建一条新的打卡记录，只包含文本和选择数据。"""
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    if checkin_table.get_checkin_by_date(user_id=current_user_id, target_date_str=today_str):
        raise HTTPException(status_code=409, detail="A check-in for today already exists.")
    
    new_checkin = checkin_table.create_checkin(user_id=current_user_id, data=checkin_data)
    if not new_checkin:
        raise HTTPException(status_code=500, detail="Could not create the check-in record.")
    return new_checkin


# --- 【新增】为已创建的记录上传图片的接口 ---
@router.post(
    "/{checkin_id}/image",
    response_model=CheckinModel,
    summary="为指定的打卡记录上传图片"
)
def upload_checkin_image(
    checkin_id: str,
    image: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """为一条已经存在的打卡记录上传或更新图片。"""
    # 1. 验证记录是否存在且属于当前用户
    existing_checkin = checkin_table.get_checkin_by_id(checkin_id)
    if not existing_checkin or existing_checkin.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="Check-in not found or not authorized.")

    # 2. 保存图片文件
    image_url = checkin_table.save_checkin_image(user_id=current_user_id, image_file=image)
    if not image_url:
        raise HTTPException(status_code=500, detail="Failed to save image.")
        
    # 3. 更新数据库中的 image_url 字段
    checkin_table.update_image_url(checkin_id=checkin_id, image_url=image_url)
    
    # 4. 返回更新后的完整记录
    return checkin_table.get_checkin_by_id(checkin_id)



# --- 【最终修改】只修改这个接口 ---
@router.get(
    "/month/{year}/{month}", 
    response_model=Dict[str, CheckinModel], 
    summary="获取指定月份的打卡记录 (按天聚合)"
)
def get_checkins_for_month(year: int, month: int, current_user_id: str = Depends(get_current_user_id)):
    """
    获取一个字典，key是天(e.g., "28")，value是当天的打卡记录。
    【动态翻译】返回前，mood 字段会从中文翻译为英文icon名。
    """
    # 1. 从数据库获取原始数据（mood 字段此时是中文）
    checkins_map = checkin_table.get_checkins_by_month(user_id=current_user_id, year=year, month=month)

    # 2. 遍历字典的每一个值（即每一天的打卡记录），进行翻译
    for day_key in checkins_map:
        # 获取当前记录的中文心情
        mood_chinese = checkins_map[day_key].get('mood')

        # 如果存在中文心情，则进行翻译
        if mood_chinese:
            # 使用翻译地图查找对应的英文名，如果找不到则保留原文
            english_mood = MOOD_TRANSLATION_MAP.get(mood_chinese, mood_chinese)
            # 更新当前记录的 mood 字段为翻译后的英文名
            checkins_map[day_key]['mood'] = english_mood
            
    # 3. 返回被动态修改过的、包含英文 mood 的字典
    return checkins_map

# Find the get_checkin_for_date endpoint and modify the signature
@router.get("/date/{record_date}", response_model=CheckinModel, summary="获取指定日期的打卡记录")
def get_checkin_for_date(
    record_date: str, # <-- Change type hint from `date` to `str`
    current_user_id: str = Depends(get_current_user_id)
):
    # The function body now passes the string directly to the model method
    checkin = checkin_table.get_checkin_by_date(user_id=current_user_id, target_date_str=record_date)
    if not checkin:
        raise HTTPException(status_code=404, detail="No check-in found for the specified date.")
    return checkin

@router.put("/{checkin_id}", response_model=CheckinModel, summary="更新指定的打卡记录")
def update_existing_checkin(checkin_id: str, checkin_data: CheckinBaseModel, current_user_id: str = Depends(get_current_user_id)):
    existing_checkin = checkin_table.get_checkin_by_id(checkin_id)
    if not existing_checkin or existing_checkin.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="Check-in not found or not authorized.")
    updated_checkin = checkin_table.update_checkin(checkin_id=checkin_id, data=checkin_data)
    if not updated_checkin:
        raise HTTPException(status_code=500, detail="Failed to update the check-in.")
    return updated_checkin

@router.delete("/{checkin_id}", summary="删除指定的打卡记录")
def delete_existing_checkin(checkin_id: str, current_user_id: str = Depends(get_current_user_id)):
    existing_checkin = checkin_table.get_checkin_by_id(checkin_id)
    if not existing_checkin or existing_checkin.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="Check-in not found or not authorized.")
    if not checkin_table.delete_checkin(checkin_id):
        raise HTTPException(status_code=500, detail="Failed to delete the check-in.")
    return {"message": "Check-in successfully deleted."}