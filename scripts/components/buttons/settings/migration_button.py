import os
import sqlite3
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime
import interactions # type: ignore
from ....Utils.models import (
    db, User, Alliance, AllianceSettings, GiftCode, 
    UserGiftCode, GiftCodeControl, GiftCodeChannel,
    FurnaceChange, NicknameChange, BotSettings, Admin,
    BearNotification, BearNotificationEmbed, BackupPassword
)
from ....Utils.migration_logger import MigrationLogger

class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass

class ValidationError(Exception):
    """Custom exception for data validation errors."""
    pass

class MigrationButton(interactions.Button):
    def __init__(self):
        super().__init__(
            style=interactions.ButtonStyle.PRIMARY,
            label="Migrate Database",
            custom_id="migrate_database"
        )
        self.db_connections: Dict[str, sqlite3.Connection] = {}
        self.logger = MigrationLogger()
        self.rollback_data: Dict[str, List[Dict[str, Any]]] = {}

    def _get_connection(self, db_path: str) -> sqlite3.Connection:
        """Get or create a database connection."""
        if not os.path.exists(db_path):
            self.logger.error(f"Database file not found: {db_path}")
            raise DatabaseError(f"Database file not found: {db_path}")
            
        if db_path not in self.db_connections:
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("PRAGMA foreign_keys = ON")
                self.db_connections[db_path] = conn
                self.logger.info(f"Connected to database: {db_path}")
            except sqlite3.Error as e:
                self.logger.error(f"Failed to connect to database {db_path}", e)
                raise DatabaseError(f"Failed to connect to database {db_path}: {str(e)}")
        return self.db_connections[db_path]

    def _close_connections(self):
        """Close all database connections."""
        for conn in self.db_connections.values():
            try:
                conn.close()
            except sqlite3.Error:
                pass  # Ignore errors during cleanup
        self.db_connections.clear()

    def detect_database_version(self) -> Tuple[str, str]:
        """
        Detect the database version from files in old_data folder.
        Returns: Tuple of (version, base_path)
        """
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), "old_data")
        
        if not os.path.exists(base_path):
            return "none", base_path
            
        # Check for V4 format (extended set of files)
        v4_files = [
            "users.sqlite", "alliance.sqlite", "giftcode.sqlite", 
            "changes.sqlite", "settings.sqlite", "id_channel.sqlite",
            "beartime.sqlite", "backup.sqlite"
        ]
        if all(os.path.exists(os.path.join(base_path, f)) for f in v4_files):
            return "v4", base_path
            
        # Check for V3 format (basic set of files)
        v3_files = ["users.sqlite", "alliance.sqlite", "giftcode.sqlite", "changes.sqlite", "settings.sqlite"]
        if all(os.path.exists(os.path.join(base_path, f)) for f in v3_files):
            return "v3", base_path
            
        # Check for V2 format
        if os.path.exists(os.path.join(base_path, "gift_db.sqlite")):
            return "v2", os.path.join(base_path, "gift_db.sqlite")
            
        return "unknown", base_path

    async def migrate_v2(self, alliance_id: int, source_path: str) -> Tuple[bool, List[str]]:
        """Migrate data from V2 database format."""
        if not os.path.exists(source_path):
            return False, ["Source database not found"]
            
        messages = []
        try:
            with db.atomic():
                source_conn = self._get_connection(source_path)
                cursor = source_conn.cursor()
                
                # Migrate users
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
                
                # Migrate gift codes
                cursor.execute("SELECT * FROM gift_codes")
                codes = cursor.fetchall()
                for code in codes:
                    GiftCode.create_or_update(
                        giftcode=code[0],
                        date=code[1],
                        validation_status='pending'
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
                
            return True, messages
            
        except Exception as e:
            return False, [f"Error during migration: {str(e)}"]
        finally:
            self._close_connections()

    async def migrate_v3(self, source_dir: str) -> Tuple[bool, List[str]]:
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
                await self._migrate_alliances(alliance_conn, messages)
                
                # Migrate gift codes
                giftcode_conn = self._get_connection(os.path.join(source_dir, 'giftcode.sqlite'))
                await self._migrate_giftcodes(giftcode_conn, messages)
                
                # Migrate changes
                changes_conn = self._get_connection(os.path.join(source_dir, 'changes.sqlite'))
                await self._migrate_changes(changes_conn, messages)
                
                # Migrate settings
                settings_conn = self._get_connection(os.path.join(source_dir, 'settings.sqlite'))
                await self._migrate_settings(settings_conn, messages)
                
            return True, messages
            
        except Exception as e:
            return False, [f"Error during migration: {str(e)}"]
        finally:
            self._close_connections()

    async def migrate_v4(self, source_dir: str) -> Tuple[bool, List[str]]:
        """Migrate data from V4 database format with validation and rollback."""
        if not os.path.exists(source_dir):
            return False, ["Source directory not found"]
            
        messages = []
        self.logger.start_migration("V4")
        
        try:
            # Backup existing data
            await self._backup_table(User, 'users')
            await self._backup_table(BearNotification, 'bear_notifications')
            await self._backup_table(BackupPassword, 'backup_passwords')
            
            with db.atomic():
                # Migrate users with validation
                users_conn = self._get_connection(os.path.join(source_dir, 'users.sqlite'))
                cursor = users_conn.cursor()
                self.logger.start_table('users')
                
                cursor.execute("SELECT * FROM users")
                users = cursor.fetchall()
                for user in users:
                    user_data = {
                        'fid': user[0],
                        'nickname': user[1],
                        'furnace_lv': user[2],
                        'kid': user[3],
                        'stove_lv_content': user[4],
                        'alliance': user[5],
                        'last_updated': user[6] if len(user) > 6 else None,
                        'created_at': user[7] if len(user) > 7 else None
                    }
                    
                    if self._validate_data('users', user_data):
                        User.create_or_update(**user_data)
                        self.logger.record_processed(str(user_data['fid']))
                    else:
                        self.logger.record_processed(str(user_data['fid']), False)
                        
                self.logger.end_table()
                messages.append(f"✓ Migrated {len(users)} users")
                
                # Migrate alliances and settings
                alliance_conn = self._get_connection(os.path.join(source_dir, 'alliance.sqlite'))
                await self._migrate_alliances(alliance_conn, messages)
                
                # Migrate gift codes
                giftcode_conn = self._get_connection(os.path.join(source_dir, 'giftcode.sqlite'))
                await self._migrate_giftcodes(giftcode_conn, messages)
                
                # Migrate changes
                changes_conn = self._get_connection(os.path.join(source_dir, 'changes.sqlite'))
                await self._migrate_changes(changes_conn, messages)
                
                # Migrate settings
                settings_conn = self._get_connection(os.path.join(source_dir, 'settings.sqlite'))
                await self._migrate_settings(settings_conn, messages)
                
                # Migrate V4-specific data
                await self._migrate_v4_specific_data(source_dir, messages)
                
            self.logger.end_migration()
            return True, messages
            
        except Exception as e:
            self.logger.error("Migration failed", e)
            if await self._rollback():
                messages.append("✗ Migration failed - Successfully rolled back changes")
            else:
                messages.append("✗ Migration failed - Rollback also failed")
            return False, messages
        finally:
            self._close_connections()

    async def _migrate_alliances(self, conn: sqlite3.Connection, messages: List[str]):
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

    async def _migrate_giftcodes(self, conn: sqlite3.Connection, messages: List[str]):
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

    async def _migrate_changes(self, conn: sqlite3.Connection, messages: List[str]):
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

    async def _migrate_settings(self, conn: sqlite3.Connection, messages: List[str]):
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

    async def _migrate_v4_specific_data(self, source_dir: str, messages: List[str]):
        """Migrate V4-specific data from additional files."""
        # Migrate ID Channel mappings
        try:
            id_channel_conn = self._get_connection(os.path.join(source_dir, 'id_channel.sqlite'))
            cursor = id_channel_conn.cursor()
            
            # Verify table structure
            cursor.execute("SELECT * FROM id_channel LIMIT 1")
            columns = [description[0] for description in cursor.description]
            expected_columns = ['channel_id', 'alliance_id', 'last_message_id']
            if not all(col in columns for col in expected_columns):
                raise DatabaseError("ID channel table missing required columns")
            
            cursor.execute("SELECT * FROM id_channel")
            channels = cursor.fetchall()
            for channel in channels:
                GiftCodeChannel.create_or_update(
                    channel_id=channel[0],
                    alliance_id=channel[1],
                    last_message_id=channel[2] if len(channel) > 2 else None
                )
            messages.append(f"✓ Migrated {len(channels)} ID channel mappings")
        except DatabaseError as e:
            messages.append(f"⚠ ID channel migration error: {str(e)}")
        except Exception as e:
            messages.append(f"✗ ID channel migration failed: {str(e)}")

        # Migrate Bear Time settings
        try:
            beartime_conn = self._get_connection(os.path.join(source_dir, 'beartime.sqlite'))
            cursor = beartime_conn.cursor()
            
            # Migrate notifications
            cursor.execute("SELECT * FROM bear_notifications")
            notifications = cursor.fetchall()
            migrated_notifications = []
            for notif in notifications:
                notification = BearNotification.create_or_update(
                    notification_id=notif[1],
                    notification_time=notif[2],
                    sent_at=datetime.strptime(notif[3], '%Y-%m-%d %H:%M:%S')
                    if len(notif) > 3 and notif[3] else datetime.now()
                )
                migrated_notifications.append(notification)
            messages.append(f"✓ Migrated {len(notifications)} bear notifications")
            
            # Migrate notification embeds
            cursor.execute("SELECT * FROM bear_notification_embeds")
            embeds = cursor.fetchall()
            for embed in embeds:
                BearNotificationEmbed.create_or_update(
                    notification=next(n for n in migrated_notifications if n.notification_id == embed[1]),
                    title=embed[2],
                    created_at=datetime.strptime(embed[3], '%Y-%m-%d %H:%M:%S')
                    if len(embed) > 3 and embed[3] else datetime.now()
                )
            messages.append(f"✓ Migrated {len(embeds)} bear notification embeds")
        except DatabaseError as e:
            messages.append(f"⚠ Bear time migration error: {str(e)}")
        except Exception as e:
            messages.append(f"✗ Bear time migration failed: {str(e)}")

        # Migrate backup data
        try:
            backup_conn = self._get_connection(os.path.join(source_dir, 'backup.sqlite'))
            cursor = backup_conn.cursor()
            
            # Verify table structure
            cursor.execute("SELECT * FROM backup_passwords LIMIT 1")
            columns = [description[0] for description in cursor.description]
            expected_columns = ['discord_id', 'backup_password', 'created_at']
            if not all(col in columns for col in expected_columns):
                raise DatabaseError("Backup passwords table missing required columns")
            
            cursor.execute("SELECT * FROM backup_passwords")
            backups = cursor.fetchall()
            for backup in backups:
                BackupPassword.create_or_update(
                    discord_id=backup[0],
                    backup_password=backup[1],
                    created_at=datetime.strptime(backup[2], '%Y-%m-%d %H:%M:%S')
                    if len(backup) > 2 and backup[2] else datetime.now()
                )
            messages.append(f"✓ Migrated {len(backups)} backup passwords")
        except DatabaseError as e:
            messages.append(f"⚠ Backup data migration error: {str(e)}")
        except Exception as e:
            messages.append(f"✗ Backup data migration failed: {str(e)}")

    async def _validate_data(self, table_name: str, data: Dict[str, Any]) -> bool:
        """Validate data before migration."""
        try:
            if table_name == 'users':
                if not isinstance(data.get('fid'), int):
                    raise ValidationError("Invalid FID")
                if not isinstance(data.get('nickname'), str):
                    raise ValidationError("Invalid nickname")
                if not isinstance(data.get('furnace_lv'), int):
                    raise ValidationError("Invalid furnace level")
                    
            elif table_name == 'bear_notifications':
                if not isinstance(data.get('notification_id'), int):
                    raise ValidationError("Invalid notification ID")
                if not isinstance(data.get('notification_time'), int):
                    raise ValidationError("Invalid notification time")
                    
            elif table_name == 'backup_passwords':
                if not isinstance(data.get('discord_id'), str):
                    raise ValidationError("Invalid discord ID")
                if not isinstance(data.get('backup_password'), str):
                    raise ValidationError("Invalid backup password")
                    
            return True
            
        except ValidationError as e:
            self.logger.warning(f"Validation failed for {table_name}: {str(e)}")
            return False

    async def _backup_table(self, model_class, table_name: str):
        """Backup existing data before migration."""
        self.logger.info(f"Backing up table: {table_name}")
        backup = []
        for record in model_class.select():
            backup.append(record.__data__)
        self.rollback_data[table_name] = backup
        self.logger.info(f"Backed up {len(backup)} records from {table_name}")

    async def _rollback(self):
        """Rollback changes in case of migration failure."""
        self.logger.info("Starting rollback process")
        try:
            with db.atomic():
                for table_name, records in self.rollback_data.items():
                    self.logger.info(f"Rolling back table: {table_name}")
                    model_class = next(m for m in [User, Alliance, BearNotification, BackupPassword]
                                    if m._meta.table_name == table_name)
                    
                    # Clear current data
                    model_class.delete().execute()
                    
                    # Restore backup
                    for record in records:
                        model_class.create(**record)
                        
                self.logger.info("Rollback completed successfully")
                return True
        except Exception as e:
            self.logger.error("Rollback failed", e)
            return False

    async def callback(self, ctx: interactions.ComponentContext):
        """Handle button click."""
        await ctx.defer(ephemeral=True)
        
        embed = interactions.Embed(
            title="Database Migration",
            color=interactions.Color.YELLOW
        )
        
        # Detect database version
        version, path = self.detect_database_version()
        
        if version == "none":
            embed.description = f"No database files found in the old_data folder.\nPlease place your old database files in: {path}"
            embed.color = interactions.Color.RED
            await ctx.send(embeds=[embed], ephemeral=True)
            return
            
        if version == "unknown":
            embed.description = f"Could not detect database version in: {path}\nPlease ensure you have placed the correct database files."
            embed.color = interactions.Color.RED
            await ctx.send(embeds=[embed], ephemeral=True)
            return
            
        # For V2, we need to select an alliance first
        if version == "v2":
            alliances = await self._get_alliances()
            if not alliances:
                embed.description = "Please create an alliance before migrating V2 data!"
                embed.color = interactions.Color.RED
                await ctx.send(embeds=[embed], ephemeral=True)
                return
                
            # Create alliance selection menu
            options = [
                interactions.StringSelectOption(
                    label=name,
                    value=str(alliance_id),
                    description=f"Alliance ID: {alliance_id}"
                )
                for alliance_id, name in alliances
            ]
            
            select_menu = interactions.StringSelectMenu(
                *options,
                placeholder="Select Alliance",
                custom_id="alliance_select"
            )
            
            embed.description = "Please select the alliance to migrate users to:"
            await ctx.send(embeds=[embed], components=select_menu, ephemeral=True)
            
            try:
                choice = await ctx.client.wait_for_component(
                    components=select_menu,
                    timeout=60.0
                )
                
                alliance_id = int(choice.values[0])
                success, messages = await self.migrate_v2(alliance_id, source_path=path)
                
            except TimeoutError:
                embed.description = "Selection timed out. Please try again."
                embed.color = interactions.Color.RED
                await ctx.edit(embeds=[embed], components=[])
                return
                
        elif version == "v3":
            success, messages = await self.migrate_v3(source_dir=path)
        else:  # V4
            success, messages = await self.migrate_v4(source_dir=path)
        
        # Update embed with results
        if success:
            embed.color = interactions.Color.GREEN
            embed.description = "Migration completed successfully!"
            for msg in messages:
                embed.add_field(name="✓", value=msg, inline=False)
        else:
            embed.color = interactions.Color.RED
            embed.description = "Migration failed!"
            for error in messages:
                embed.add_field(name="✗", value=error, inline=False)
        
        await ctx.edit(embeds=[embed], components=[])

    async def _get_alliances(self) -> List[tuple]:
        """Get list of alliances as (id, name) tuples."""
        alliances = []
        for alliance in Alliance.select():
            alliances.append((alliance.alliance_id, alliance.name))
        return alliances
