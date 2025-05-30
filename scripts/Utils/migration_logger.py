import os
import logging
from datetime import datetime
from typing import Optional

class MigrationLogger:
    """Handles logging for database migrations."""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        self.log_file = os.path.join(
            log_dir, 
            f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        
        # Set up file logger
        self.logger = logging.getLogger('migration')
        self.logger.setLevel(logging.DEBUG)
        
        # File handler with detailed formatting
        fh = logging.FileHandler(self.log_file)
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        
        self.current_table: Optional[str] = None
        self.records_processed = 0
        self.start_time: Optional[datetime] = None
        
    def start_migration(self, version: str):
        """Log the start of a migration."""
        self.start_time = datetime.now()
        self.logger.info(f"Starting migration from version {version}")
        
    def end_migration(self):
        """Log the end of a migration."""
        if self.start_time:
            duration = datetime.now() - self.start_time
            self.logger.info(f"Migration completed in {duration}")
        
    def start_table(self, table_name: str):
        """Log the start of table migration."""
        self.current_table = table_name
        self.records_processed = 0
        self.logger.info(f"Starting migration of table: {table_name}")
        
    def end_table(self):
        """Log the end of table migration."""
        if self.current_table:
            self.logger.info(
                f"Completed migration of table {self.current_table}. "
                f"Processed {self.records_processed} records."
            )
        self.current_table = None
        
    def record_processed(self, record_id: str, success: bool = True):
        """Log a processed record."""
        self.records_processed += 1
        if success:
            self.logger.debug(f"Successfully processed record {record_id}")
        else:
            self.logger.warning(f"Failed to process record {record_id}")
            
    def error(self, message: str, exception: Optional[Exception] = None):
        """Log an error."""
        if exception:
            self.logger.error(f"{message}: {str(exception)}")
        else:
            self.logger.error(message)
            
    def warning(self, message: str):
        """Log a warning."""
        self.logger.warning(message)
        
    def info(self, message: str):
        """Log an info message."""
        self.logger.info(message)
        
    def get_log_file(self) -> str:
        """Get the path to the current log file."""
        return self.log_file 