# routers/checkin.py

# 1. 导入所有需要的模块
from fastapi import APIRouter, Depends, HTTPException, Body, File, UploadFile
from typing import Any, List, Optional, Dict
from pydantic import BaseModel, Field

# 2. 从项目其他文件中导入
# 【重要】确保从 model.checkin 导入了 checkin_table
from model.status import (
    MAX_CHECKIN_IMAGES,
    checkin_table,
    CheckinModel,
    CheckinBaseModel,
    model_to_dict,
)
from model.checkin_dimensions import MOOD_OPTIONS, STATUS_OPTIONS, COLOR_OPTIONS
from .auth import get_current_user_id

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

class CheckinImageUrlsPayload(BaseModel):
    image_urls: List[str] = Field(default_factory=list, max_length=MAX_CHECKIN_IMAGES)


class SeedFiveDaysPayload(BaseModel):
    year: Optional[int] = None
    month: Optional[int] = Field(default=None, ge=1, le=12)


def get_owned_checkin_or_404(checkin_id: str, current_user_id: str):
    existing_checkin = checkin_table.get_checkin_by_id(checkin_id)
    if not existing_checkin or existing_checkin.user_id != current_user_id:
        raise HTTPException(status_code=404, detail="Check-in not found or not authorized.")
    return existing_checkin


# --- 【修改】创建接口，恢复为只接收JSON ---
@router.post(
    "/",
    response_model=CheckinModel,
    summary="创建新的此刻心情记录 (兼容旧路径，不含图片)"
)
def create_new_checkin(
    checkin_data: CheckinBaseModel = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """为当前用户创建一条新的此刻心情记录，只包含文本和选择数据。"""
    new_checkin = checkin_table.create_moment(user_id=current_user_id, data=checkin_data)
    if not new_checkin:
        raise HTTPException(status_code=500, detail="Could not create the check-in record.")
    return model_to_dict(new_checkin)


@router.post(
    "/moments",
    response_model=CheckinModel,
    summary="创建此刻心情记录"
)
def create_checkin_moment(
    checkin_data: CheckinBaseModel = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """每次提交都创建一条新的 moment，不限制一天一次。"""
    new_checkin = checkin_table.create_moment(user_id=current_user_id, data=checkin_data)
    if not new_checkin:
        raise HTTPException(status_code=500, detail="Could not create the moment record.")
    return model_to_dict(new_checkin)


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
    """为一条已经存在的打卡记录上传或更新首图，保留旧前端兼容。"""
    get_owned_checkin_or_404(checkin_id, current_user_id)

    image_url = checkin_table.save_checkin_image(user_id=current_user_id, image_file=image)
    if not image_url:
        raise HTTPException(status_code=500, detail="Failed to save image.")

    checkin_table.update_image_url(checkin_id=checkin_id, image_url=image_url)
    return model_to_dict(checkin_table.get_checkin_by_id(checkin_id))


@router.post(
    "/{checkin_id}/images",
    response_model=CheckinModel,
    summary="为指定的打卡记录追加上传多张图片"
)
def upload_checkin_images(
    checkin_id: str,
    images: List[UploadFile] = File(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """追加上传 1-3 张图片。超过 3 张时返回 400。"""
    existing_checkin = get_owned_checkin_or_404(checkin_id, current_user_id)
    existing_count = len(checkin_table.get_image_urls(existing_checkin))
    if not images:
        raise HTTPException(status_code=400, detail="No images uploaded.")
    if existing_count + len(images) > MAX_CHECKIN_IMAGES:
        raise HTTPException(status_code=400, detail=f"最多只能保留 {MAX_CHECKIN_IMAGES} 张照片。")

    image_urls = []
    for image in images:
        image_url = checkin_table.save_checkin_image(user_id=current_user_id, image_file=image)
        if not image_url:
            raise HTTPException(status_code=500, detail="Failed to save image.")
        image_urls.append(image_url)

    updated_checkin = checkin_table.append_image_urls(checkin_id, image_urls)
    if not updated_checkin:
        raise HTTPException(status_code=400, detail=f"最多只能保留 {MAX_CHECKIN_IMAGES} 张照片。")
    return model_to_dict(updated_checkin)


@router.put(
    "/{checkin_id}/images",
    response_model=CheckinModel,
    summary="设置指定打卡记录的图片列表"
)
def set_checkin_images(
    checkin_id: str,
    payload: CheckinImageUrlsPayload = Body(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """用最终图片 URL 列表覆盖保存，可用于前端删除或重排后同步。"""
    get_owned_checkin_or_404(checkin_id, current_user_id)
    if len(payload.image_urls) > MAX_CHECKIN_IMAGES:
        raise HTTPException(status_code=400, detail=f"最多只能保留 {MAX_CHECKIN_IMAGES} 张照片。")

    updated_checkin = checkin_table.set_image_urls(checkin_id, payload.image_urls)
    if not updated_checkin:
        raise HTTPException(status_code=500, detail="Failed to update images.")
    return model_to_dict(updated_checkin)


@router.put(
    "/{checkin_id}/images/{image_index}",
    response_model=CheckinModel,
    summary="替换指定位置的打卡图片"
)
@router.post(
    "/{checkin_id}/images/{image_index}",
    response_model=CheckinModel,
    summary="替换或追加指定位置的打卡图片"
)
def replace_checkin_image(
    checkin_id: str,
    image_index: int,
    image: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """替换指定下标图片；下标等于当前图片数时会追加一张。"""
    get_owned_checkin_or_404(checkin_id, current_user_id)
    image_url = checkin_table.save_checkin_image(user_id=current_user_id, image_file=image)
    if not image_url:
        raise HTTPException(status_code=500, detail="Failed to save image.")

    updated_checkin = checkin_table.replace_image_url(checkin_id, image_index, image_url)
    if not updated_checkin:
        raise HTTPException(status_code=400, detail="Invalid image index or image limit exceeded.")
    return model_to_dict(updated_checkin)


@router.delete(
    "/{checkin_id}/images/{image_index}",
    response_model=CheckinModel,
    summary="删除指定位置的打卡图片"
)
def delete_checkin_image(
    checkin_id: str,
    image_index: int,
    current_user_id: str = Depends(get_current_user_id)
):
    get_owned_checkin_or_404(checkin_id, current_user_id)
    updated_checkin = checkin_table.delete_image_url(checkin_id, image_index)
    if not updated_checkin:
        raise HTTPException(status_code=400, detail="Invalid image index.")
    return model_to_dict(updated_checkin)



# --- 【最终修改】只修改这个接口 ---
@router.get(
    "/month/{year}/{month}",
    response_model=Dict[str, Dict[str, Any]],
    summary="获取指定月份的心情记录汇总 (按天聚合)"
)
def get_checkins_for_month(year: int, month: int, current_user_id: str = Depends(get_current_user_id)):
    """
    获取一个字典，key 是天(e.g., "28")，value 是当天心情记录汇总。
    """
    return checkin_table.get_checkins_by_month(user_id=current_user_id, year=year, month=month)

@router.get("/dimensions", response_model=Dict[str, List[Dict[str, Any]]], summary="获取每日打卡维度配置")
def get_checkin_dimensions():
    """返回每日打卡 V2 的心情、状态和颜色枚举配置。"""
    return {
        "moods": MOOD_OPTIONS,
        "statuses": STATUS_OPTIONS,
        "colors": COLOR_OPTIONS,
    }


@router.post("/dev/seed-five-days", summary="【本地开发】为当前用户补 5 天打卡假数据")
def seed_five_days_for_current_user(
    payload: SeedFiveDaysPayload = Body(default_factory=SeedFiveDaysPayload),
    current_user_id: str = Depends(get_current_user_id),
):
    """创建当前月前 5 天假打卡记录，已有记录不覆盖，方便测试分析页。"""
    return checkin_table.seed_five_days_for_month(
        user_id=current_user_id,
        year=payload.year,
        month=payload.month,
    )

@router.get("/date/{record_date}/timeline", response_model=Dict[str, Any], summary="获取指定日期的心情轨迹")
def get_timeline_for_date(
    record_date: str,
    current_user_id: str = Depends(get_current_user_id)
):
    return checkin_table.get_timeline_by_date(
        user_id=current_user_id,
        target_date_str=record_date,
    )


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
    return model_to_dict(checkin)

@router.put("/{checkin_id}", response_model=CheckinModel, summary="更新指定的打卡记录")
def update_existing_checkin(checkin_id: str, checkin_data: CheckinBaseModel, current_user_id: str = Depends(get_current_user_id)):
    get_owned_checkin_or_404(checkin_id, current_user_id)
    updated_checkin = checkin_table.update_checkin(checkin_id=checkin_id, data=checkin_data)
    if not updated_checkin:
        raise HTTPException(status_code=500, detail="Failed to update the check-in.")
    return model_to_dict(updated_checkin)

@router.delete("/{checkin_id}", summary="删除指定的打卡记录")
def delete_existing_checkin(checkin_id: str, current_user_id: str = Depends(get_current_user_id)):
    get_owned_checkin_or_404(checkin_id, current_user_id)
    if not checkin_table.delete_checkin(checkin_id):
        raise HTTPException(status_code=500, detail="Failed to delete the check-in.")
    return {"message": "Check-in successfully deleted."}
