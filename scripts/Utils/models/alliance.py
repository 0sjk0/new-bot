from typing import Optional
from peewee import *  # type: ignore
from .base import BaseModel, MODELS

class Alliance(BaseModel):
    """Alliance model for managing game alliances."""
    alliance_id = AutoField()
    name = TextField()
    discord_server_id = IntegerField(null=True)
    
    class Meta:
        table_name = 'alliance_list'
        
    @classmethod
    def get_by_name(cls, name: str) -> Optional['Alliance']:
        """Get an alliance by its name."""
        try:
            return cls.get(cls.name == name)
        except DoesNotExist:
            return None
            
    @classmethod
    def get_by_server_id(cls, server_id: int) -> Optional['Alliance']:
        """Get an alliance by Discord server ID."""
        try:
            return cls.get(cls.discord_server_id == server_id)
        except DoesNotExist:
            return None

class AllianceSettings(BaseModel):
    """Settings for alliances."""
    alliance_id = ForeignKeyField(Alliance, backref='settings')
    channel_id = IntegerField()
    interval = IntegerField()
    
    class Meta:
        table_name = 'alliancesettings'
        
    @classmethod
    def get_by_alliance(cls, alliance_id: int) -> Optional['AllianceSettings']:
        """Get settings for a specific alliance."""
        try:
            return cls.get(cls.alliance_id == alliance_id)
        except DoesNotExist:
            return None

# Register models for initialization
MODELS.extend([Alliance, AllianceSettings]) 