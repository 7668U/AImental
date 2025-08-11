# router/note.py

from typing import List, Optional, Literal
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from model.note import note_table
from router.auth import get_current_user_id


router = APIRouter()


# ---------------------------------------------------
# 1) Pydantic Schemas (已更新)
# ---------------------------------------------------

class NotebookCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    cover_image: Optional[str] = None


class NotebookUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    cover_image: Optional[str] = None


class NotebookResponse(BaseModel):
    id: int
    user_id: str
    name: str
    cover_image: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NoteItemCreate(BaseModel):
    item_type: Literal['todo', 'note']
    title: Optional[str] = Field(None, max_length=255) # <-- 已新增
    content: str = Field("", max_length=10000)
    is_completed: Optional[bool] = False
    item_order: Optional[int] = None


class NoteItemUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255) # <-- 已新增
    content: Optional[str] = Field(None, max_length=10000)
    is_completed: Optional[bool] = None
    item_order: Optional[int] = None


class NoteItemResponse(BaseModel):
    id: int
    notebook_id: int
    item_type: str
    title: Optional[str] = None # <-- 已新增
    content: str
    is_completed: bool
    item_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReorderPayload(BaseModel):
    orders: List[dict]  # [{'id': 1, 'item_order': 1}, ...]


# ---------------------------------------------------
# 2) Notebook Endpoints (保持不变)
# ---------------------------------------------------

@router.post("/notebooks/", response_model=NotebookResponse, status_code=status.HTTP_201_CREATED)
def create_notebook(notebook: NotebookCreate, current_user: str = Depends(get_current_user_id)):
    nb = note_table.create_notebook(user_id=current_user, name=notebook.name, cover_image=notebook.cover_image)
    return nb


@router.get("/notebooks/", response_model=List[NotebookResponse])
def get_user_notebooks(current_user: str = Depends(get_current_user_id)):
    nbs = note_table.get_notebooks_by_user(user_id=current_user)
    return nbs


@router.get("/notebooks/{notebook_id}", response_model=NotebookResponse)
def get_notebook(notebook_id: int, current_user: str = Depends(get_current_user_id)):
    nb = note_table.get_notebook_by_id(notebook_id)
    if not nb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    if nb.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this notebook")
    return nb


@router.put("/notebooks/{notebook_id}", response_model=NotebookResponse)
def update_notebook(notebook_id: int, payload: NotebookUpdate, current_user: str = Depends(get_current_user_id)):
    nb = note_table.get_notebook_by_id(notebook_id)
    if not nb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    if nb.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this notebook")
    
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return nb

    updated = note_table.update_notebook(notebook_id, **update_data)
    return updated


@router.delete("/notebooks/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notebook(notebook_id: int, current_user: str = Depends(get_current_user_id)):
    nb = note_table.get_notebook_by_id(notebook_id)
    if not nb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    if nb.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this notebook")

    ok = note_table.delete_notebook(notebook_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete notebook")
    return


# ---------------------------------------------------
# 3) NoteItem Endpoints (已更新)
# ---------------------------------------------------

@router.post("/notebooks/{notebook_id}/notes/", response_model=NoteItemResponse, status_code=status.HTTP_201_CREATED)
def create_note_item(notebook_id: int, payload: NoteItemCreate, current_user: str = Depends(get_current_user_id)):
    nb = note_table.get_notebook_by_id(notebook_id)
    if not nb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    if nb.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to add notes to this notebook")

    ni = note_table.create_note_item(
        notebook_id=notebook_id,
        item_type=payload.item_type,
        title=payload.title, # <-- 已传递 title
        content=payload.content,
        is_completed=payload.is_completed or False,
        item_order=payload.item_order
    )
    if not ni:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create note item")
    return ni


@router.get("/notebooks/{notebook_id}/notes/", response_model=List[NoteItemResponse])
def get_notebook_notes(notebook_id: int, current_user: str = Depends(get_current_user_id)):
    nb = note_table.get_notebook_by_id(notebook_id)
    if not nb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    if nb.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view notes in this notebook")

    items = note_table.get_note_items_by_notebook(notebook_id)
    return items


@router.put("/notes/{note_item_id}", response_model=NoteItemResponse)
def update_note_item(note_item_id: int, payload: NoteItemUpdate, current_user: str = Depends(get_current_user_id)):
    ni = note_table.get_note_item_by_id(note_item_id)
    if not ni:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note item not found")

    nb = note_table.get_notebook_by_id(ni.notebook_id)
    if not nb or nb.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this note item")

    # 使用 model_dump(exclude_unset=True) 只获取前端明确传递要更新的字段
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return ni

    updated = note_table.update_note_item(
        note_item_id=note_item_id,
        **update_data # 将字典解包作为参数传递
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update note item")
    return updated


@router.delete("/notes/{note_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note_item(note_item_id: int, current_user: str = Depends(get_current_user_id)):
    ni = note_table.get_note_item_by_id(note_item_id)
    if not ni:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note item not found")

    nb = note_table.get_notebook_by_id(ni.notebook_id)
    if not nb or nb.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this note item")

    ok = note_table.delete_note_item(note_item_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete note item")
    return


@router.put("/notebooks/{notebook_id}/notes/reorder", status_code=status.HTTP_204_NO_CONTENT)
def reorder_notes(notebook_id: int, payload: ReorderPayload, current_user: str = Depends(get_current_user_id)):
    nb = note_table.get_notebook_by_id(notebook_id)
    if not nb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    if nb.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to reorder notes in this notebook")

    note_table.reorder_notes(notebook_id, payload.orders)
    return