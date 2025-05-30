import os
from datetime import datetime
from typing import List, Type
from peewee import *  # type: ignore

# Ensure database directory exists
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "database")
os.makedirs(DB_DIR, exist_ok=True)

# Database file path
DB_PATH = os.path.join(DB_DIR, "whiteout.db")

# Initialize database
db = SqliteDatabase(DB_PATH, pragmas={
    'journal_mode': 'wal',     # Write-Ahead Logging for better concurrency
    'cache_size': -1024 * 32,  # 32MB cache
    'foreign_keys': 1,         # Enable foreign key support
    'ignore_check_constraints': 0,
    'synchronous': 0           # Let OS handle fsync (faster)
})

class BaseModel(Model):
    """Base model class that should be inherited by all models."""
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)
    
    def save(self, *args, **kwargs):
        """Override save to update the updated_at timestamp."""
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)
    
    class Meta:
        database = db
        legacy_table_names = False

# Store all model classes that need to be initialized
MODELS: List[Type[BaseModel]] = []

def initialize_db():
    """Initialize the database and create all tables."""
    with db:
        db.create_tables(MODELS)

# Connect to the database when module is imported
db.connect(reuse_if_open=True)

# Register close on application exit
import atexit
atexit.register(db.close) 