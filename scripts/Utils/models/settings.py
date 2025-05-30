from typing import Optional
from peewee import *  # type: ignore
from .base import BaseModel, MODELS

class BotSettings(BaseModel):
    """Bot configuration settings."""
    id = AutoField()
    channelid = IntegerField(null=True)
    
    class Meta:
        table_name = 'botsettings'
        
    @classmethod
    def get_channel_id(cls) -> Optional[int]:
        """Get the configured channel ID."""
        try:
            settings = cls.get_by_id(1)
            return settings.channelid
        except DoesNotExist:
            return None

class Admin(BaseModel):
    """Admin configuration."""
    id = AutoField()
    is_initial = BooleanField(default=False)
    
    class Meta:
        table_name = 'admin'
        
    @classmethod
    def is_admin(cls, user_id: int) -> bool:
        """Check if a user is an admin."""
        try:
            return cls.get_by_id(user_id).is_initial
        except DoesNotExist:
            return False

# Register models for initialization
MODELS.extend([BotSettings, Admin]) 