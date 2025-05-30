from typing import Optional
from peewee import *  # type: ignore
from .base import BaseModel, MODELS

class User(BaseModel):
    """User model for game-related data."""
    fid = AutoField()  # Primary key from old database
    nickname = TextField(null=True)
    furnace_lv = IntegerField(default=0)
    kid = IntegerField(null=True)
    stove_lv_content = TextField(null=True)
    alliance = TextField(null=True)
    
    class Meta:
        table_name = 'users'
        
    @classmethod
    def get_by_fid(cls, fid: int) -> Optional['User']:
        """Get a user by their FID."""
        try:
            return cls.get(cls.fid == fid)
        except DoesNotExist:
            return None
            
    @classmethod
    def create_or_update(cls, fid: int, **kwargs) -> 'User':
        """Create a new user or update existing one."""
        user, created = cls.get_or_create(
            fid=fid,
            defaults=kwargs
        )
        
        if not created and kwargs:
            # Update only provided fields
            for key, value in kwargs.items():
                setattr(user, key, value)
            user.save()
            
        return user

# Register model for initialization
MODELS.append(User) 