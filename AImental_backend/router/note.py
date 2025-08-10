from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from model import note as note_model
from router.auth import get_current_user_id

router = APIRouter()

# Pydantic Models for Request/Response
class NotebookBase(BaseModel):
    name: str
    cover_image: Optional[str] = None

class NotebookCreate(NotebookBase):
    pass

class NotebookUpdate(NotebookBase):
    name: Optional[str] = None
    cover_image: Optional[str] = None

class NotebookResponse(NotebookBase):
    id: int
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True # Enable ORM mode for Peewee models

class NoteItemBase(BaseModel):
    item_type: str # 'todo' or 'note'
    content: str
    is_completed: Optional[bool] = False
    item_order: Optional[int] = None

class NoteItemCreate(NoteItemBase):
    pass

class NoteItemUpdate(NoteItemBase):
    item_type: Optional[str] = None
    content: Optional[str] = None

class NoteItemResponse(NoteItemBase):
    id: int
    notebook_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# --- Notebook Endpoints ---

@router.post("/notebooks/", response_model=NotebookResponse, status_code=status.HTTP_201_CREATED)
def create_notebook(notebook: NotebookCreate, current_user: str = Depends(get_current_user_id)):
    """Create a new notebook for the current user."""
    new_notebook = note_model.create_notebook(user_id=current_user, name=notebook.name, cover_image=notebook.cover_image)
    return new_notebook

@router.get("/notebooks/", response_model=List[NotebookResponse])
def get_user_notebooks(current_user: str = Depends(get_current_user_id)):
    """Retrieve all notebooks for the current user."""
    notebooks = note_model.get_notebooks_by_user(user_id=current_user)
    return notebooks

@router.get("/notebooks/{notebook_id}", response_model=NotebookResponse)
def get_notebook(notebook_id: int, current_user: str = Depends(get_current_user_id)):
    """Retrieve a specific notebook by ID."""
    notebook = note_model.get_notebook_by_id(notebook_id)
    if not notebook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    if notebook.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this notebook")
    return notebook

@router.put("/notebooks/{notebook_id}", response_model=NotebookResponse)
def update_notebook(notebook_id: int, notebook_update: NotebookUpdate, current_user: str = Depends(get_current_user_id)):
    """Update an existing notebook."""
    notebook = note_model.get_notebook_by_id(notebook_id)
    if not notebook:
        raise HTTPException(status_code=status.HTTP_404_NOT_NOT_FOUND, detail="Notebook not found")
    if notebook.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this notebook")

    updated_notebook = note_model.update_notebook(
        notebook_id=notebook_id,
        name=notebook_update.name,
        cover_image=notebook_update.cover_image
    )
    return updated_notebook

@router.delete("/notebooks/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notebook(notebook_id: int, current_user: str = Depends(get_current_user_id)):
    """Delete a notebook."""
    notebook = note_model.get_notebook_by_id(notebook_id)
    if not notebook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    if notebook.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this notebook")

    if not note_model.delete_notebook(notebook_id):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete notebook")
    return

# --- Note Item Endpoints ---

@router.post("/notebooks/{notebook_id}/notes/", response_model=NoteItemResponse, status_code=status.HTTP_201_CREATED)
def create_note_item(notebook_id: int, note_item: NoteItemCreate, current_user: str = Depends(get_current_user_id)):
    """Create a new note item within a specific notebook."""
    notebook = note_model.get_notebook_by_id(notebook_id)
    if not notebook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    if notebook.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to add notes to this notebook")

    new_note_item = note_model.create_note_item(
        notebook_id=notebook_id,
        item_type=note_item.item_type,
        content=note_item.content,
        is_completed=note_item.is_completed,
        item_order=note_item.item_order
    )
    if not new_note_item:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create note item")
    return new_note_item

@router.get("/notebooks/{notebook_id}/notes/", response_model=List[NoteItemResponse])
def get_notebook_notes(notebook_id: int, current_user: str = Depends(get_current_user_id)):
    """Retrieve all note items for a specific notebook."""
    notebook = note_model.get_notebook_by_id(notebook_id)
    if not notebook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    if notebook.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view notes in this notebook")

    note_items = note_model.get_note_items_by_notebook(notebook_id)
    return note_items

@router.put("/notes/{note_item_id}", response_model=NoteItemResponse)
def update_note_item(note_item_id: int, note_item_update: NoteItemUpdate, current_user: str = Depends(get_current_user_id)):
    """Update an existing note item."""
    note_item = note_model.get_note_item_by_id(note_item_id)
    if not note_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note item not found")
    
    # Verify user ownership of the notebook associated with the note item
    notebook = note_model.get_notebook_by_id(note_item.notebook.id)
    if not notebook or notebook.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this note item")

    updated_note_item = note_model.update_note_item(
        note_item_id=note_item_id,
        item_type=note_item_update.item_type,
        content=note_item_update.content,
        is_completed=note_item_update.is_completed,
        item_order=note_item_update.item_order
    )
    if not updated_note_item:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update note item")
    return updated_note_item

@router.delete("/notes/{note_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note_item(note_item_id: int, current_user: str = Depends(get_current_user_id)):
    """Delete a note item."""
    note_item = note_model.get_note_item_by_id(note_item_id)
    if not note_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note item not found")

    # Verify user ownership of the notebook associated with the note item
    notebook = note_model.get_notebook_by_id(note_item.notebook.id)
    if not notebook or notebook.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this note item")

    if not note_model.delete_note_item(note_item_id):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete note item")
    return