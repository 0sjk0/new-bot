import os
import sqlite3
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from . import (
    db, User, Alliance, AllianceSettings, GiftCode, UserGiftCode,
    GiftCodeControl, GiftCodeChannel, FurnaceChange, NicknameChange,
    BotSettings, Admin
)

class DatabaseMigration:
    def __init__(self):
        self.old_db_connections: Dict[str, sqlite3.Connection] = {}
        
    def _get_connection(self, db_path: str) -> sqlite3.Connection:
        """Get or create a database connection."""
        if db_path not in self.old_db_connections:
            self.old_db_connections[db_path] = sqlite3.connect(db_path)
        return self.old_db_connections[db_path]
        
    def _close_connections(self):
        """Close all database connections."""
        for conn in self.old_db_connections.values():
            conn.close()
        self.old_db_connections.clear()

    async def migrate_v2(self, alliance_id: int, source_path: str = 'gift_db.sqlite') -> Tuple[bool, List[str]]:
        """Migrate data from V2 database format."""
        if not os.path.exists(source_path):
            return False, ["Source database not found"]
            
        messages = []
        try:
            with db.atomic():
                # Migrate users
                source_conn = self._get_connection(source_path)
                cursor = source_conn.cursor()
                
                cursor.execute("SELECT fid, nickname, furnace_lv FROM users")
                users = cursor.fetchall()
                for fid, nickname, furnace_lv in users:
                    User.create_or_update(
                        fid=fid,
                        nickname=nickname,
                        furnace_lv=furnace_lv,
                        alliance=str(alliance_id)
                    )
                messages.append(f"Migrated {len(users)} users")
                
                # Migrate other tables
                self._migrate_changes(source_conn, messages)
                self._migrate_giftcodes(source_conn, messages)
                
            return True, messages
            
        except Exception as e:
            return False, [f"Error during migration: {str(e)}"]
        finally:
            self._close_connections()

    async def migrate_v3(self, source_dir: str = 'old bot/db') -> Tuple[bool, List[str]]:
        """Migrate data from V3 database format."""
        if not os.path.exists(source_dir):
            return False, ["Source directory not found"]
            
        messages = []
        try:
            with db.atomic():
                # Migrate users
                users_conn = self._get_connection(os.path.join(source_dir, 'users.sqlite'))
                cursor = users_conn.cursor()
                cursor.execute("SELECT * FROM users")
                users = cursor.fetchall()
                for user in users:
                    User.create_or_update(
                        fid=user[0],
                        nickname=user[1],
                        furnace_lv=user[2],
                        kid=user[3],
                        stove_lv_content=user[4],
                        alliance=user[5]
                    )
                messages.append(f"Migrated {len(users)} users")
                
                # Migrate alliances
                alliance_conn = self._get_connection(os.path.join(source_dir, 'alliance.sqlite'))
                self._migrate_alliances(alliance_conn, messages)
                
                # Migrate gift codes
                giftcode_conn = self._get_connection(os.path.join(source_dir, 'giftcode.sqlite'))
                self._migrate_giftcodes(giftcode_conn, messages)
                
                # Migrate changes
                changes_conn = self._get_connection(os.path.join(source_dir, 'changes.sqlite'))
                self._migrate_changes(changes_conn, messages)
                
                # Migrate settings
                settings_conn = self._get_connection(os.path.join(source_dir, 'settings.sqlite'))
                self._migrate_settings(settings_conn, messages)
                
            return True, messages
            
        except Exception as e:
            return False, [f"Error during migration: {str(e)}"]
        finally:
            self._close_connections()

    def _migrate_alliances(self, conn: sqlite3.Connection, messages: List[str]):
        """Migrate alliance data."""
        cursor = conn.cursor()
        
        # Migrate alliance list
        cursor.execute("SELECT * FROM alliance_list")
        alliances = cursor.fetchall()
        for alliance in alliances:
            Alliance.create_or_update(
                alliance_id=alliance[0],
                name=alliance[1],
                discord_server_id=alliance[2] if len(alliance) > 2 else None
            )
        messages.append(f"Migrated {len(alliances)} alliances")
        
        # Migrate alliance settings
        cursor.execute("SELECT * FROM alliancesettings")
        settings = cursor.fetchall()
        for setting in settings:
            AllianceSettings.create_or_update(
                alliance_id=setting[0],
                channel_id=setting[1],
                interval=setting[2] if len(setting) > 2 else 0
            )
        messages.append(f"Migrated {len(settings)} alliance settings")

    def _migrate_giftcodes(self, conn: sqlite3.Connection, messages: List[str]):
        """Migrate gift code data."""
        cursor = conn.cursor()
        
        # Migrate gift codes
        cursor.execute("SELECT * FROM gift_codes")
        codes = cursor.fetchall()
        for code in codes:
            GiftCode.create_or_update(
                giftcode=code[0],
                date=code[1],
                validation_status=code[2] if len(code) > 2 else 'pending'
            )
        messages.append(f"Migrated {len(codes)} gift codes")
        
        # Migrate user gift codes
        cursor.execute("SELECT * FROM user_giftcodes")
        user_codes = cursor.fetchall()
        for user_code in user_codes:
            UserGiftCode.create_or_update(
                fid=user_code[0],
                giftcode=user_code[1],
                status=user_code[2]
            )
        messages.append(f"Migrated {len(user_codes)} user gift codes")

    def _migrate_changes(self, conn: sqlite3.Connection, messages: List[str]):
        """Migrate change history data."""
        cursor = conn.cursor()
        
        # Migrate furnace changes
        cursor.execute("SELECT * FROM furnace_changes")
        furnace_changes = cursor.fetchall()
        for change in furnace_changes:
            FurnaceChange.create_or_update(
                id=change[0],
                fid=change[1],
                old_furnace_lv=change[2],
                new_furnace_lv=change[3],
                change_date=change[4]
            )
        messages.append(f"Migrated {len(furnace_changes)} furnace changes")
        
        # Migrate nickname changes
        cursor.execute("SELECT * FROM nickname_changes")
        nickname_changes = cursor.fetchall()
        for change in nickname_changes:
            NicknameChange.create_or_update(
                id=change[0],
                fid=change[1],
                old_nickname=change[2],
                new_nickname=change[3],
                change_date=change[4]
            )
        messages.append(f"Migrated {len(nickname_changes)} nickname changes")

    def _migrate_settings(self, conn: sqlite3.Connection, messages: List[str]):
        """Migrate bot settings and admin data."""
        cursor = conn.cursor()
        
        # Migrate bot settings
        cursor.execute("SELECT * FROM botsettings")
        settings = cursor.fetchall()
        for setting in settings:
            BotSettings.create_or_update(
                id=setting[0],
                channelid=setting[1]
            )
        messages.append(f"Migrated {len(settings)} bot settings")
        
        # Migrate admin settings
        cursor.execute("SELECT * FROM admin")
        admins = cursor.fetchall()
        for admin in admins:
            Admin.create_or_update(
                id=admin[0],
                is_initial=admin[1]
            )
        messages.append(f"Migrated {len(admins)} admin settings")

    async def migrate_v4(self, source_path: str) -> Tuple[bool, List[str]]:
        """Migrate data from V4 database format."""
        if not os.path.exists(source_path):
            return False, ["Source database not found"]
            
        messages = []
        try:
            with db.atomic():
                source_conn = self._get_connection(source_path)
                cursor = source_conn.cursor()
                
                # Migrate users with expanded fields
                cursor.execute("SELECT * FROM users")
                users = cursor.fetchall()
                for user in users:
                    User.create_or_update(
                        fid=user[0],
                        nickname=user[1],
                        furnace_lv=user[2],
                        kid=user[3],
                        stove_lv_content=user[4],
                        alliance=user[5],
                        last_updated=user[6] if len(user) > 6 else None,
                        created_at=user[7] if len(user) > 7 else None
                    )
                messages.append(f"Migrated {len(users)} users")
                
                # Migrate alliances with expanded fields
                self._migrate_alliances(source_conn, messages)
                
                # Migrate gift codes with additional metadata
                cursor.execute("SELECT * FROM gift_codes")
                codes = cursor.fetchall()
                for code in codes:
                    GiftCode.create_or_update(
                        giftcode=code[0],
                        date=code[1],
                        validation_status=code[2],
                        expiry_date=code[3] if len(code) > 3 else None,
                        created_by=code[4] if len(code) > 4 else None
                    )
                messages.append(f"Migrated {len(codes)} gift codes")
                
                # Migrate other tables
                self._migrate_changes(source_conn, messages)
                self._migrate_settings(source_conn, messages)
                
                # Migrate any V4-specific tables
                self._migrate_v4_specific_tables(source_conn, messages)
                
            return True, messages
            
        except Exception as e:
            return False, [f"Error during migration: {str(e)}"]
        finally:
            self._close_connections()
            
    def _migrate_v4_specific_tables(self, conn: sqlite3.Connection, messages: List[str]):
        """Migrate V4-specific tables and fields."""
        cursor = conn.cursor()
        
        # Add any V4-specific table migrations here
        # For example:
        try:
            cursor.execute("SELECT * FROM gift_code_control")
            controls = cursor.fetchall()
            for control in controls:
                GiftCodeControl.create_or_update(
                    id=control[0],
                    alliance_id=control[1],
                    channel_id=control[2],
                    last_check=control[3],
                    is_active=control[4]
                )
            messages.append(f"Migrated {len(controls)} gift code controls")
        except sqlite3.OperationalError:
            # Table might not exist in some V4 versions
            pass
            
        try:
            cursor.execute("SELECT * FROM gift_code_channels")
            channels = cursor.fetchall()
            for channel in channels:
                GiftCodeChannel.create_or_update(
                    channel_id=channel[0],
                    alliance_id=channel[1],
                    last_message_id=channel[2] if len(channel) > 2 else None
                )
            messages.append(f"Migrated {len(channels)} gift code channels")
        except sqlite3.OperationalError:
            pass 