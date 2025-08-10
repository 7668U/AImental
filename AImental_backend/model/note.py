from peewee import Model, CharField, TextField, DateTimeField, BooleanField, ForeignKeyField, IntegerField, fn
from datetime import datetime
from db import cabinet_db # Import the new db instance

# Base Model for cabinet_db
class BaseModel(Model):
    class Meta:
        database = cabinet_db

# Notebook Model
class Notebook(BaseModel):
    user_id = CharField()
    name = CharField()
    cover_image = CharField(null=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'notebooks'

# NoteItem Model (for to-dos and general notes within a notebook)
class NoteItem(BaseModel):
    notebook = ForeignKeyField(Notebook, backref='notes', on_delete='CASCADE')
    item_type = CharField() # 'todo' or 'note'
    content = TextField()
    is_completed = BooleanField(default=False) # For todo items
    item_order = IntegerField(default=0) # To maintain order of items
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'notes'

# --- Database Operations ---

def create_tables():
    """Creates the notebook and note_item tables if they don't exist."""
    with cabinet_db:
        cabinet_db.create_tables([Notebook, NoteItem])

# Notebook CRUD operations
def create_notebook(user_id: str, name: str, cover_image: str = None):
    """Creates a new notebook."""
    return Notebook.create(user_id=user_id, name=name, cover_image=cover_image)

def get_notebooks_by_user(user_id: str):
    """Retrieves all notebooks for a given user, sorted by updated_at."""
    return list(Notebook.select().where(Notebook.user_id == user_id).order_by(Notebook.updated_at.desc()))

def get_notebook_by_id(notebook_id: int):
    """Retrieves a single notebook by its ID."""
    return Notebook.get_or_none(Notebook.id == notebook_id)

def update_notebook(notebook_id: int, name: str = None, cover_image: str = None):
    """Updates an existing notebook."""
    notebook = get_notebook_by_id(notebook_id)
    if notebook:
        if name is not None:
            notebook.name = name
        if cover_image is not None:
            notebook.cover_image = cover_image
        notebook.updated_at = datetime.now()
        notebook.save()
        return notebook
    return None

def delete_notebook(notebook_id: int):
    """Deletes a notebook by its ID."""
    notebook = get_notebook_by_id(notebook_id)
    if notebook:
        notebook.delete_instance(recursive=True) # recursive=True deletes associated notes
        return True
    return False

# NoteItem CRUD operations
def create_note_item(notebook_id: int, item_type: str, content: str, is_completed: bool = False, item_order: int = None):
    """Creates a new note item within a notebook."""
    notebook = get_notebook_by_id(notebook_id)
    if not notebook:
        return None
    if item_order is None:
        # Get the max order for the current notebook and add 1
        max_order = NoteItem.select(fn.MAX(NoteItem.item_order)).where(NoteItem.notebook == notebook).scalar()
        item_order = (max_order or 0) + 1
    return NoteItem.create(notebook=notebook, item_type=item_type, content=content, is_completed=is_completed, item_order=item_order)

def get_note_items_by_notebook(notebook_id: int):
    """Retrieves all note items for a given notebook, sorted by item_order."""
    return list(NoteItem.select().where(NoteItem.notebook == notebook_id).order_by(NoteItem.item_order))

def get_note_item_by_id(note_item_id: int):
    """Retrieves a single note item by its ID."""
    return NoteItem.get_or_none(NoteItem.id == note_item_id)

def update_note_item(note_item_id: int, content: str = None, is_completed: bool = None, item_order: int = None):
    """Updates an existing note item."""
    note_item = get_note_item_by_id(note_item_id)
    if note_item:
        if content is not None:
            note_item.content = content
        if is_completed is not None:
            note_item.is_completed = is_completed
        if item_order is not None:
            note_item.item_order = item_order
        note_item.updated_at = datetime.now()
        note_item.save()
        return note_item
    return None

def delete_note_item(note_item_id: int):
    """Deletes a note item by its ID."""
    note_item = get_note_item_by_id(note_item_id)
    if note_item:
        note_item.delete_instance()
        return True
    return False