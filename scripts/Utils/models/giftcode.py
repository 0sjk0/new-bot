from typing import Optional, List
from datetime import datetime
from peewee import *  # type: ignore
from .base import BaseModel, MODELS
from .alliance import Alliance

class GiftCode(BaseModel):
    """Gift code model for managing game gift codes."""
    giftcode = TextField(primary_key=True)
    date = TextField()  # Keeping as TextField to maintain compatibility
    validation_status = TextField(default='pending')
    
    class Meta:
        table_name = 'gift_codes'
        
    @classmethod
    def get_active_codes(cls) -> List['GiftCode']:
        """Get all active (pending) gift codes."""
        return list(cls.select().where(cls.validation_status == 'pending'))
        
    @classmethod
    def validate_code(cls, code: str) -> bool:
        """Check if a gift code is valid."""
        try:
            giftcode = cls.get(cls.giftcode == code)
            return giftcode.validation_status == 'pending'
        except DoesNotExist:
            return False

class UserGiftCode(BaseModel):
    """Model for tracking user gift code usage."""
    fid = IntegerField()
    giftcode = ForeignKeyField(GiftCode, backref='users')
    status = TextField()
    
    class Meta:
        table_name = 'user_giftcodes'
        primary_key = CompositeKey('fid', 'giftcode')
        
    @classmethod
    def has_used_code(cls, fid: int, code: str) -> bool:
        """Check if a user has used a specific gift code."""
        return cls.select().where(
            (cls.fid == fid) & 
            (cls.giftcode == code)
        ).exists()

class GiftCodeControl(BaseModel):
    """Gift code control settings per alliance."""
    alliance_id = ForeignKeyField(Alliance, primary_key=True)
    status = IntegerField(default=0)
    
    class Meta:
        table_name = 'giftcodecontrol'
        
    @classmethod
    def get_alliance_status(cls, alliance_id: int) -> int:
        """Get the gift code status for an alliance."""
        try:
            control = cls.get(cls.alliance_id == alliance_id)
            return control.status
        except DoesNotExist:
            return 0

class GiftCodeChannel(BaseModel):
    """Gift code channel configuration."""
    alliance_id = ForeignKeyField(Alliance)
    channel_id = IntegerField()
    
    class Meta:
        table_name = 'giftcode_channel'
        
    @classmethod
    def get_channel(cls, alliance_id: int) -> Optional[int]:
        """Get the gift code channel for an alliance."""
        try:
            config = cls.get(cls.alliance_id == alliance_id)
            return config.channel_id
        except DoesNotExist:
            return None

# Register models for initialization
MODELS.extend([GiftCode, UserGiftCode, GiftCodeControl, GiftCodeChannel]) 