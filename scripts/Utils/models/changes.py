from typing import Optional, List
from datetime import datetime
from peewee import *  # type: ignore
from .base import BaseModel, MODELS
from .user import User

class FurnaceChange(BaseModel):
    """Track furnace level changes."""
    id = AutoField()
    fid = ForeignKeyField(User, field='fid', backref='furnace_changes')
    old_furnace_lv = IntegerField()
    new_furnace_lv = IntegerField()
    change_date = TextField()  # Keeping as TextField for compatibility
    
    class Meta:
        table_name = 'furnace_changes'
        
    @classmethod
    def get_user_changes(cls, fid: int) -> List['FurnaceChange']:
        """Get all furnace changes for a user."""
        return list(cls.select().where(cls.fid == fid).order_by(cls.change_date.desc()))

class NicknameChange(BaseModel):
    """Track nickname changes."""
    id = AutoField()
    fid = ForeignKeyField(User, field='fid', backref='nickname_changes')
    old_nickname = TextField()
    new_nickname = TextField()
    change_date = TextField()  # Keeping as TextField for compatibility
    
    class Meta:
        table_name = 'nickname_changes'
        
    @classmethod
    def get_user_changes(cls, fid: int) -> List['NicknameChange']:
        """Get all nickname changes for a user."""
        return list(cls.select().where(cls.fid == fid).order_by(cls.change_date.desc()))

# Register models for initialization
MODELS.extend([FurnaceChange, NicknameChange]) 