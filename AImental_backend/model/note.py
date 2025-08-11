# model/note.py

from datetime import datetime
from typing import List, Optional

from peewee import (
    Model, CharField, TextField, DateTimeField, BooleanField,
    ForeignKeyField, IntegerField, fn
)
from playhouse.shortcuts import model_to_dict

from db import cabinet_db


# ---------------------------------------------------
# 1) Peewee Models
# ---------------------------------------------------

class BaseModel(Model):
    class Meta:
        database = cabinet_db


class Notebook(BaseModel):
    user_id = CharField()
    name = CharField(max_length=100) # 建议为 CharField 加上最大长度
    cover_image = CharField(null=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "notebooks"


class NoteItem(BaseModel):
    """
    既承载 todo，也承载分标题和内容的长文 note
    """
    notebook = ForeignKeyField(Notebook, backref="notes", on_delete="CASCADE")
    item_type = CharField()          # 'todo' 或 'note'
    
    # --- 已新增 title 字段 ---
    title = CharField(max_length=255, null=True) # 允许为空，因为 todo 不需要 title

    content = TextField()
    is_completed = BooleanField(default=False)
    item_order = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = "notes"


# ---------------------------------------------------
# 2) Table Access Class
# ---------------------------------------------------

class NoteTable:
    """
    封装所有 notebook / note_item 的数据库操作
    """
    def __init__(self, db_connection):
        self.db = db_connection
        # 启动时自动创建表
        self.db.create_tables([Notebook, NoteItem])

    # ---------- Notebook (以下方法保持不变) ----------
    def create_notebook(self, user_id: str, name: str, cover_image: Optional[str] = None) -> Notebook:
        nb = Notebook.create(user_id=user_id, name=name, cover_image=cover_image)
        return nb

    def get_notebooks_by_user(self, user_id: str) -> List[Notebook]:
        return list(
            Notebook.select()
            .where(Notebook.user_id == user_id)
            .order_by(Notebook.updated_at.desc())
        )

    def get_notebook_by_id(self, notebook_id: int) -> Optional[Notebook]:
        return Notebook.get_or_none(Notebook.id == notebook_id)

    def update_notebook(self, notebook_id: int, name: Optional[str] = None, cover_image: Optional[str] = None) -> Optional[Notebook]:
        nb = self.get_notebook_by_id(notebook_id)
        if not nb:
            return None
        if name is not None:
            nb.name = name
        if cover_image is not None:
            nb.cover_image = cover_image
        nb.updated_at = datetime.now()
        nb.save()
        return nb

    def delete_notebook(self, notebook_id: int) -> bool:
        nb = self.get_notebook_by_id(notebook_id)
        if not nb:
            return False
        # 级联删除 notes
        nb.delete_instance(recursive=True)
        return True

    # ---------- NoteItem (以下方法已修改) ----------
    def create_note_item(
        self,
        notebook_id: int,
        item_type: str,
        content: str,
        title: Optional[str] = None, # <-- 已增加 title 参数
        is_completed: bool = False,
        item_order: Optional[int] = None
    ) -> Optional[NoteItem]:
        nb = self.get_notebook_by_id(notebook_id)
        if not nb:
            return None

        if item_type not in ("todo", "note"):
            raise ValueError("item_type must be 'todo' or 'note'")

        if item_order is None:
            # 追加到末尾
            max_order = (
                NoteItem.select(fn.MAX(NoteItem.item_order))
                .where(NoteItem.notebook == nb)
                .scalar()
            )
            item_order = (max_order or 0) + 1

        ni = NoteItem.create(
            notebook=nb,
            item_type=item_type,
            title=title,             # <-- 已保存 title
            content=content,
            is_completed=is_completed,
            item_order=item_order
        )
        # 同步 notebook 的 updated_at
        nb.updated_at = datetime.now()
        nb.save()
        return ni

    def get_note_items_by_notebook(self, notebook_id: int) -> List[NoteItem]:
        return list(
            NoteItem.select()
            .where(NoteItem.notebook == notebook_id)
            .order_by(NoteItem.updated_at.desc()) 
        )

    def get_note_item_by_id(self, note_item_id: int) -> Optional[NoteItem]:
        return NoteItem.get_or_none(NoteItem.id == note_item_id)

    def update_note_item(
        self,
        note_item_id: int,
        **update_data: dict # <-- 已修改为接收字典，更灵活
    ) -> Optional[NoteItem]:
        ni = self.get_note_item_by_id(note_item_id)
        if not ni:
            return None

        changed = False
        # 动态更新传入的字段
        for key, value in update_data.items():
            if hasattr(ni, key):
                setattr(ni, key, value)
                changed = True
        
        if changed:
            ni.updated_at = datetime.now()
            ni.save()
            # 触发父 notebook 更新时间
            Notebook.update({Notebook.updated_at: datetime.now()}).where(
                Notebook.id == ni.notebook_id
            ).execute()
        return ni

    def delete_note_item(self, note_item_id: int) -> bool:
        ni = self.get_note_item_by_id(note_item_id)
        if not ni:
            return False
        nb_id = ni.notebook_id
        ni.delete_instance()
        # 删除条目也更新 notebook 时间
        Notebook.update({Notebook.updated_at: datetime.now()}).where(
            Notebook.id == nb_id
        ).execute()
        return True

    # ---------- 可选：批量重排 (保持不变) ----------
    def reorder_notes(self, notebook_id: int, orders: List[dict]) -> int:
        """
        批量更新 item_order
        orders: [{'id': 1, 'item_order': 1}, ...]
        return: 受影响行数
        """
        count = 0
        with self.db.atomic():
            for item in orders:
                _id = item.get("id")
                _order = item.get("item_order")
                if _id is None or _order is None:
                    continue
                updated = NoteItem.update({NoteItem.item_order: _order}).where(
                    (NoteItem.id == _id) & (NoteItem.notebook_id == notebook_id)
                ).execute()
                count += updated
            # 更新父 notebook 时间
            Notebook.update({Notebook.updated_at: datetime.now()}).where(
                Notebook.id == notebook_id
            ).execute()
        return count


# --- 单例实例化（供路由导入使用） ---
note_table = NoteTable(cabinet_db)