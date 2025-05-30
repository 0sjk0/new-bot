from datetime import datetime
from peewee import *  # type: ignore
from .base import BaseModel, MODELS

class BearNotification(BaseModel):
    """Track bear notification timings."""
    id = AutoField()
    notification_id = IntegerField(null=False)
    notification_time = IntegerField(null=False)
    sent_at = DateTimeField(default=datetime.now)
    
    class Meta:
        table_name = 'bear_notifications'
        
    @classmethod
    def create_or_update(cls, **kwargs):
        """Create or update a bear notification."""
        notification = cls.get_or_none(notification_id=kwargs['notification_id'])
        if notification:
            for key, value in kwargs.items():
                setattr(notification, key, value)
            notification.save()
            return notification
        return cls.create(**kwargs)

class BearNotificationEmbed(BaseModel):
    """Track bear notification embed details."""
    id = AutoField()
    notification = ForeignKeyField(BearNotification, backref='embeds', field='notification_id')
    title = TextField(null=True)
    created_at = DateTimeField(default=datetime.now)
    
    class Meta:
        table_name = 'bear_notification_embeds'
        
    @classmethod
    def create_or_update(cls, **kwargs):
        """Create or update a bear notification embed."""
        embed = cls.get_or_none(
            notification=kwargs['notification'],
            title=kwargs.get('title')
        )
        if embed:
            for key, value in kwargs.items():
                setattr(embed, key, value)
            embed.save()
            return embed
        return cls.create(**kwargs)

# Register models for initialization
MODELS.extend([BearNotification, BearNotificationEmbed]) 