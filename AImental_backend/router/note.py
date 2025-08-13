# router/note.py (彻底重构版)

from typing import List, Optional, Literal
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from model.note import note_table
from router.auth import get_current_user_id


router = APIRouter()


# ---------------------------------------------------
# 1) Pydantic Schemas (请求和响应模型已简化)
# ---------------------------------------------------

class NoteItemCreate(BaseModel):
    item_type: Literal['todo', 'note']
    title: Optional[str] = Field(None, max_length=255)
    content: str = Field("", max_length=10000)
    is_completed: Optional[bool] = False
    item_order: Optional[int] = None


class NoteItemUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = Field(None, max_length=10000)
    is_completed: Optional[bool] = None
    item_order: Optional[int] = None


class NoteItemResponse(BaseModel):
    id: int
    # --- 【移除】notebook_id 不再存在 ---
    # notebook_id: int 
    item_type: str
    title: Optional[str] = None
    content: str
    is_completed: bool
    item_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- 【移除】MyNotebookResponse 模型也不再需要 ---


# ---------------------------------------------------
# 2) API Endpoints (接口已重构)
# ---------------------------------------------------

@router.get("/notes/", response_model=List[NoteItemResponse])
def get_all_user_notes(current_user: str = Depends(get_current_user_id)):
    """
    获取当前用户的所有条目（笔记和待办）。
    """
    items = note_table.get_note_items_by_user(user_id=current_user)
    return items


@router.post("/notes/", response_model=NoteItemResponse, status_code=status.HTTP_201_CREATED)
def create_note_item(payload: NoteItemCreate, current_user: str = Depends(get_current_user_id)):
    """
    为当前用户创建一个新的条目（note 或 todo）。
    """
    note_item = note_table.create_note_item(
        user_id=current_user, # <--- 直接传入当前用户ID
        item_type=payload.item_type,
        title=payload.title,
        content=payload.content,
        is_completed=payload.is_completed or False,
        item_order=payload.item_order
    )
    if not note_item:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create note item")
    return note_item


@router.put("/notes/{note_item_id}", response_model=NoteItemResponse)
def update_note_item(note_item_id: int, payload: NoteItemUpdate, current_user: str = Depends(get_current_user_id)):
    """
    更新指定ID的条目。
    """
    ni = note_table.get_note_item_by_id(note_item_id)
    if not ni:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note item not found")

    # --- 【修改】权限校验逻辑更简单直接 ---
    if ni.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this note item")

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return ni

    updated = note_table.update_note_item(
        note_item_id=note_item_id,
        **update_data
    )
    return updated


@router.delete("/notes/{note_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note_item(note_item_id: int, current_user: str = Depends(get_current_user_id)):
    """
    删除指定ID的条目。
    """
    ni = note_table.get_note_item_by_id(note_item_id)
    if not ni:
        return

    # --- 【修改】权限校验逻辑更简单直接 ---
    if ni.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this note item")

    note_table.delete_note_item(note_item_id)
    return