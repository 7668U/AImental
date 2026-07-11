# model/note.py (彻底重构版)

from datetime import datetime
from typing import List, Optional

from peewee import (
    Model, CharField, TextField, DateTimeField, BooleanField, IntegerField, fn
)
from db import cabinet_db
from security.data_encryption import EncryptedTextField

# ---------------------------------------------------
# 1) Peewee Models (模型已重构)
# ---------------------------------------------------

class BaseModel(Model):
    class Meta:
        database = cabinet_db

# --- 【重要】Notebook 模型已被彻底移除 ---

class NoteItem(BaseModel):
    # --- 【修改】不再有关联到 Notebook 的外键 ---
    # notebook = ForeignKeyField(Notebook, backref="notes", on_delete="CASCADE")

    # --- 【新增】直接将 user_id 存储在每个条目上 ---
    user_id = CharField(index=True)

    # --- 其他字段保持不变 ---
    item_type = CharField()
    title = EncryptedTextField(purpose="notes.title", null=True)
    content = EncryptedTextField(purpose="notes.content")
    is_completed = BooleanField(default=False)
    item_order = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "notes"


# ---------------------------------------------------
# 2) Table Access Class (数据库操作层已重构)
# ---------------------------------------------------

class NoteTable:
    def __init__(self, db_connection):
        self.db = db_connection
        # --- 【修改】现在只创建 NoteItem 表 ---
        self.db.create_tables([NoteItem])

    # --- 【移除】所有和 Notebook 相关的方法都被移除了 ---
    # get_or_create_default_notebook, create_notebook, get_notebook_by_id 等...

    # ---------- NoteItem (所有方法都已重构，直接使用 user_id) ----------
    def create_note_item(
        self,
        user_id: str, # <--- 直接传入 user_id
        item_type: str,
        content: str,
        title: Optional[str] = None,
        is_completed: bool = False,
        item_order: Optional[int] = None
    ) -> NoteItem:

        if item_type not in ("todo", "note"):
            raise ValueError("item_type must be 'todo' or 'note'")

        if item_order is None:
            # 找到该用户下最大的 item_order
            max_order = (
                NoteItem.select(fn.MAX(NoteItem.item_order))
                .where(NoteItem.user_id == user_id) # <--- 按 user_id 查找
                .scalar()
            )
            item_order = (max_order or 0) + 1

        ni = NoteItem.create(
            user_id=user_id, # <--- 保存 user_id
            item_type=item_type,
            title=title,
            content=content,
            is_completed=is_completed,
            item_order=item_order
        )
        return ni

    def get_note_items_by_user(self, user_id: str) -> List[NoteItem]:
        """
        根据 user_id 获取所有条目。
        """
        return list(
            NoteItem.select()
            .where(NoteItem.user_id == user_id) # <--- 按 user_id 查找
            .order_by(NoteItem.updated_at.desc())
        )

    def get_note_item_by_id(self, note_item_id: int) -> Optional[NoteItem]:
        return NoteItem.get_or_none(NoteItem.id == note_item_id)

    def update_note_item(self, note_item_id: int, **update_data: dict) -> Optional[NoteItem]:
        ni = self.get_note_item_by_id(note_item_id)
        if not ni: return None

        changed = False
        for key, value in update_data.items():
            if hasattr(ni, key):
                setattr(ni, key, value)
                changed = True

        if changed:
            ni.updated_at = datetime.now()
            ni.save()
            
        # --- 【移除】不再需要更新父笔记本的时间 ---
        return ni

    def delete_note_item(self, note_item_id: int) -> bool:
        ni = self.get_note_item_by_id(note_item_id)
        if not ni:
            return False
        
        ni.delete_instance()
        # --- 【移除】不再需要更新父笔记本的时间 ---
        return True


# --- 单例实例化 ---
note_table = NoteTable(cabinet_db)
