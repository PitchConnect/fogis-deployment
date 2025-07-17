#!/usr/bin/env python3
"""
Backup Manager for FOGIS Deployment
Complete system backup and restore capabilities

This module provides comprehensive backup and restore functionality for:
- Configuration files (fogis-config.yaml, .env, config.json)
- OAuth credentials and tokens
- Processing state and data
- System logs and metadata
"""

import glob
import json
import logging
import os
import shutil
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BackupError(Exception):
    """Exception raised for backup/restore errors"""


class BackupManager:
    """
    Comprehensive backup and restore manager for FOGIS deployment
    
    Supports different backup types:
    - complete: Full system backup including all files and state
    - config: Configuration files only
    - credentials: OAuth credentials and tokens only
    """
    
    def __init__(self, backup_dir: str = "backups"):
        """
        Initialize backup manager

        Args:
            backup_dir: Directory to store backups
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.base_path = Path.cwd()  # Current working directory for subprocess calls
        
        # Define backup components
        self.config_files = [
            "fogis-config.yaml",
            ".env",
            "fogis-calendar-phonebook-sync/config.json"
        ]
        
        self.credential_files = [
            "credentials.json",
            "credentials/google-credentials.json"
        ]
        
        self.token_files = [
            "data/google-drive-service/google-drive-token.json",
            "data/calendar-sync/calendar-token.json", 
            "fogis-calendar-phonebook-sync/token.json"
        ]
        
        self.data_directories = [
            "data/",
            "logs/",
            "credentials/"
        ]
    
    def create_backup(self, backup_type: str = "complete") -> str:
        """
        Create a system backup
        
        Args:
            backup_type: Type of backup ('complete', 'config', 'credentials')
            
        Returns:
            Path to created backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_name = f"fogis-backup-{backup_type}-{timestamp}"
        
        logger.info(f"Creating {backup_type} backup: {backup_name}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_staging = Path(temp_dir) / backup_name
            backup_staging.mkdir()
            
            try:
                # Create backup based on type
                if backup_type == "complete":
                    self._backup_complete_system(backup_staging)
                elif backup_type == "config":
                    self._backup_configuration(backup_staging)
                elif backup_type == "credentials":
                    self._backup_credentials(backup_staging)
                else:
                    raise BackupError(f"Unknown backup type: {backup_type}")
                
                # Create backup manifest
                manifest = self._create_backup_manifest(backup_staging, backup_type)
                self._save_manifest(backup_staging, manifest)
                
                # Create compressed archive
                archive_path = self._create_compressed_archive(backup_staging, backup_name)
                
                # Validate backup
                if self.validate_backup(archive_path):
                    logger.info(f"Backup created successfully: {archive_path}")
                    return str(archive_path)
                else:
                    raise BackupError("Backup validation failed")
                    
            except Exception as e:
                logger.error(f"Backup creation failed: {e}")
                raise BackupError(f"Failed to create backup: {e}")
    
    def _backup_complete_system(self, backup_dir: Path) -> None:
        """Backup complete system including all components"""
        logger.info("Backing up complete system...")
        
        # Backup configuration
        self._backup_configuration(backup_dir)
        
        # Backup credentials and tokens
        self._backup_credentials(backup_dir)
        
        # Backup data directories
        for data_dir in self.data_directories:
            if os.path.exists(data_dir):
                dest_dir = backup_dir / data_dir
                dest_dir.parent.mkdir(parents=True, exist_ok=True)
                if os.path.isdir(data_dir):
                    shutil.copytree(data_dir, dest_dir, dirs_exist_ok=True)
                else:
                    shutil.copy2(data_dir, dest_dir)
                logger.debug(f"Backed up data directory: {data_dir}")
        
        # Backup docker-compose files
        compose_files = ["docker-compose.yml", "docker-compose.override.yml"]
        for compose_file in compose_files:
            if os.path.exists(compose_file):
                shutil.copy2(compose_file, backup_dir / compose_file)
                logger.debug(f"Backed up compose file: {compose_file}")
    
    def _backup_configuration(self, backup_dir: Path) -> None:
        """Backup configuration files only"""
        logger.info("Backing up configuration files...")
        
        config_backup_dir = backup_dir / "config"
        config_backup_dir.mkdir(exist_ok=True)
        
        for config_file in self.config_files:
            if os.path.exists(config_file):
                dest_path = config_backup_dir / Path(config_file).name
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(config_file, dest_path)
                logger.debug(f"Backed up config file: {config_file}")
    
    def _backup_credentials(self, backup_dir: Path) -> None:
        """Backup credentials and tokens"""
        logger.info("Backing up credentials and tokens...")
        
        creds_backup_dir = backup_dir / "credentials"
        creds_backup_dir.mkdir(exist_ok=True)
        
        # Backup credential files
        for cred_file in self.credential_files:
            if os.path.exists(cred_file):
                dest_path = creds_backup_dir / Path(cred_file).name
                shutil.copy2(cred_file, dest_path)
                # Set secure permissions
                os.chmod(dest_path, 0o600)
                logger.debug(f"Backed up credential file: {cred_file}")
        
        # Backup token files
        tokens_backup_dir = creds_backup_dir / "tokens"
        tokens_backup_dir.mkdir(exist_ok=True)
        
        for token_file in self.token_files:
            if os.path.exists(token_file):
                dest_path = tokens_backup_dir / Path(token_file).name
                shutil.copy2(token_file, dest_path)
                os.chmod(dest_path, 0o600)
                logger.debug(f"Backed up token file: {token_file}")
    
    def _create_backup_manifest(self, backup_dir: Path, backup_type: str) -> Dict[str, Any]:
        """Create backup manifest with metadata"""
        manifest = {
            "backup_info": {
                "type": backup_type,
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "system": dict(zip(['sysname', 'nodename', 'release', 'version', 'machine'],
                                   os.uname())) if hasattr(os, 'uname') else {}
            },
            "files": [],
            "directories": []
        }
        
        # Catalog all files in backup
        for root, dirs, files in os.walk(backup_dir):
            rel_root = Path(root).relative_to(backup_dir)
            
            for directory in dirs:
                manifest["directories"].append(str(rel_root / directory))
            
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(backup_dir)
                
                manifest["files"].append({
                    "path": str(rel_path),
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })
        
        return manifest
    
    def _save_manifest(self, backup_dir: Path, manifest: Dict[str, Any]) -> None:
        """Save backup manifest to file"""
        manifest_path = backup_dir / "backup_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        logger.debug("Backup manifest created")
    
    def _create_compressed_archive(self, backup_dir: Path, backup_name: str) -> Path:
        """Create compressed tar archive of backup"""
        archive_path = self.backup_dir / f"{backup_name}.tar.gz"
        
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(backup_dir, arcname=backup_name)
        
        logger.debug(f"Created compressed archive: {archive_path}")
        return archive_path

    def restore_backup(self, backup_file: str) -> bool:
        """
        Restore system from backup

        Args:
            backup_file: Path to backup archive

        Returns:
            True if restore successful
        """
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise BackupError(f"Backup file not found: {backup_file}")

        logger.info(f"Restoring from backup: {backup_file}")

        # Validate backup before restore
        if not self.validate_backup(backup_file):
            raise BackupError("Backup validation failed")

        # Create pre-restore backup
        pre_restore_backup = self.create_backup("complete")
        logger.info(f"Created pre-restore backup: {pre_restore_backup}")

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract backup
                extract_dir = Path(temp_dir) / "restore"
                self._extract_backup(backup_file, extract_dir)

                # Load manifest
                manifest = self._load_manifest(extract_dir)
                backup_type = manifest["backup_info"]["type"]

                # Restore based on backup type
                if backup_type == "complete":
                    self._restore_complete_system(extract_dir)
                elif backup_type == "config":
                    self._restore_configuration(extract_dir)
                elif backup_type == "credentials":
                    self._restore_credentials(extract_dir)

                # Post-restore automation
                self._post_restore_automation(backup_type)

                logger.info("Backup restored successfully")
                return True

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            logger.info(f"Pre-restore backup available: {pre_restore_backup}")
            raise BackupError(f"Failed to restore backup: {e}")

    def _extract_backup(self, backup_file: str, extract_dir: Path) -> None:
        """Extract backup archive"""
        extract_dir.mkdir(parents=True, exist_ok=True)

        with tarfile.open(backup_file, "r:gz") as tar:
            # Security check: ensure no path traversal
            for member in tar.getmembers():
                if member.name.startswith('/') or '..' in member.name:
                    raise BackupError(f"Unsafe path in backup: {member.name}")

            tar.extractall(extract_dir)  # nosec B202 - validated above

        logger.debug(f"Extracted backup to: {extract_dir}")

    def _load_manifest(self, extract_dir: Path) -> Dict[str, Any]:
        """Load backup manifest"""
        # Find the actual backup directory (first subdirectory)
        backup_dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
        if not backup_dirs:
            raise BackupError("No backup directory found in archive")

        backup_dir = backup_dirs[0]
        manifest_path = backup_dir / "backup_manifest.json"

        if not manifest_path.exists():
            raise BackupError("Backup manifest not found")

        with open(manifest_path, 'r') as f:
            return json.load(f)

    def _restore_complete_system(self, extract_dir: Path) -> None:
        """Restore complete system"""
        logger.info("Restoring complete system...")

        backup_dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
        backup_dir = backup_dirs[0]

        # Restore configuration
        self._restore_configuration(extract_dir)

        # Restore credentials
        self._restore_credentials(extract_dir)

        # Restore data directories
        for data_dir in self.data_directories:
            source_path = backup_dir / data_dir
            if source_path.exists():
                if os.path.exists(data_dir):
                    shutil.rmtree(data_dir)

                if source_path.is_dir():
                    shutil.copytree(source_path, data_dir)
                else:
                    Path(data_dir).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, data_dir)

                logger.debug(f"Restored data directory: {data_dir}")

        # Restore docker-compose files
        compose_files = ["docker-compose.yml", "docker-compose.override.yml"]
        for compose_file in compose_files:
            source_path = backup_dir / compose_file
            if source_path.exists():
                shutil.copy2(source_path, compose_file)
                logger.debug(f"Restored compose file: {compose_file}")

        # Set secure permissions on restored files
        self._set_secure_permissions()

    def _restore_configuration(self, extract_dir: Path) -> None:
        """Restore configuration files"""
        logger.info("Restoring configuration files...")

        backup_dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
        backup_dir = backup_dirs[0]
        config_dir = backup_dir / "config"

        if not config_dir.exists():
            logger.warning("No configuration files found in backup")
            return

        for config_file in config_dir.iterdir():
            if config_file.is_file():
                # Map back to original location
                dest_path = self._map_config_file_destination(config_file.name)
                if dest_path:
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(config_file, dest_path)
                    logger.debug(f"Restored config file: {dest_path}")

    def _restore_credentials(self, extract_dir: Path) -> None:
        """Restore credentials and tokens"""
        logger.info("Restoring credentials and tokens...")

        backup_dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
        backup_dir = backup_dirs[0]
        creds_dir = backup_dir / "credentials"

        if not creds_dir.exists():
            logger.warning("No credentials found in backup")
            return

        # Restore credential files
        for cred_file in creds_dir.iterdir():
            if cred_file.is_file() and cred_file.name != "tokens":
                dest_path = Path(cred_file.name)
                if cred_file.name == "google-credentials.json":
                    dest_path = Path("credentials") / cred_file.name
                    dest_path.parent.mkdir(exist_ok=True)

                shutil.copy2(cred_file, dest_path)
                os.chmod(dest_path, 0o600)
                logger.debug(f"Restored credential file: {dest_path}")

        # Restore token files
        tokens_dir = creds_dir / "tokens"
        if tokens_dir.exists():
            for token_file in tokens_dir.iterdir():
                if token_file.is_file():
                    dest_path = self._map_token_file_destination(token_file.name)
                    if dest_path:
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(token_file, dest_path)
                        os.chmod(dest_path, 0o600)
                        logger.debug(f"Restored token file: {dest_path}")

    def _map_config_file_destination(self, filename: str) -> Optional[Path]:
        """Map config filename to destination path"""
        mapping = {
            "fogis-config.yaml": Path("fogis-config.yaml"),
            ".env": Path(".env"),
            "config.json": Path("fogis-calendar-phonebook-sync/config.json")
        }
        return mapping.get(filename)

    def _map_token_file_destination(self, filename: str) -> Optional[Path]:
        """Map token filename to destination path"""
        mapping = {
            "google-drive-token.json": Path("data/google-drive-service/google-drive-token.json"),
            "calendar-token.json": Path("data/calendar-sync/calendar-token.json"),
            "token.json": Path("fogis-calendar-phonebook-sync/token.json")
        }
        return mapping.get(filename)

    def validate_backup(self, backup_file: str) -> bool:
        """
        Validate backup file integrity

        Args:
            backup_file: Path to backup archive

        Returns:
            True if backup is valid
        """
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_file}")
                return False

            # Check if file is a valid tar.gz archive
            with tarfile.open(backup_file, "r:gz") as tar:
                # Verify archive can be read
                members = tar.getmembers()
                if not members:
                    logger.error("Backup archive is empty")
                    return False

                # Check for manifest
                manifest_found = any(
                    member.name.endswith("backup_manifest.json")
                    for member in members
                )

                if not manifest_found:
                    logger.error("Backup manifest not found")
                    return False

                logger.debug(f"Backup validation successful: {len(members)} files")
                return True

        except Exception as e:
            logger.error(f"Backup validation failed: {e}")
            return False

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups

        Returns:
            List of backup information dictionaries
        """
        backups = []

        for backup_file in self.backup_dir.glob("*.tar.gz"):
            try:
                backup_info = self.get_backup_info(str(backup_file))
                if backup_info:
                    backups.append(backup_info)
            except Exception as e:
                logger.warning(f"Could not read backup info for {backup_file}: {e}")

        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return backups

    def get_backup_info(self, backup_file: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific backup

        Args:
            backup_file: Path to backup archive

        Returns:
            Backup information dictionary or None if invalid
        """
        try:
            backup_path = Path(backup_file)

            with tempfile.TemporaryDirectory() as temp_dir:
                extract_dir = Path(temp_dir)

                # Extract just the manifest
                with tarfile.open(backup_file, "r:gz") as tar:
                    manifest_member = None
                    for member in tar.getmembers():
                        if member.name.endswith("backup_manifest.json"):
                            manifest_member = member
                            break

                    if not manifest_member:
                        return None

                    tar.extract(manifest_member, extract_dir)
                    manifest_path = extract_dir / manifest_member.name

                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)

                    # Add file information
                    file_info = backup_path.stat()
                    manifest["backup_info"]["file_path"] = str(backup_path)
                    manifest["backup_info"]["file_size"] = file_info.st_size
                    manifest["backup_info"]["file_modified"] = datetime.fromtimestamp(
                        file_info.st_mtime
                    ).isoformat()

                    return manifest["backup_info"]

        except Exception as e:
            logger.error(f"Failed to get backup info for {backup_file}: {e}")
            return None

    def delete_backup(self, backup_file: str) -> bool:
        """
        Delete a backup file

        Args:
            backup_file: Path to backup archive

        Returns:
            True if deletion successful
        """
        try:
            backup_path = Path(backup_file)
            if backup_path.exists():
                backup_path.unlink()
                logger.info(f"Deleted backup: {backup_file}")
                return True
            else:
                logger.warning(f"Backup file not found: {backup_file}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete backup {backup_file}: {e}")
            return False

    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        Clean up old backups, keeping only the most recent ones

        Args:
            keep_count: Number of backups to keep

        Returns:
            Number of backups deleted
        """
        backups = self.list_backups()

        if len(backups) <= keep_count:
            logger.info(f"No cleanup needed. {len(backups)} backups found, keeping {keep_count}")
            return 0

        backups_to_delete = backups[keep_count:]
        deleted_count = 0

        for backup in backups_to_delete:
            if self.delete_backup(backup["file_path"]):
                deleted_count += 1

        logger.info(f"Cleaned up {deleted_count} old backups")
        return deleted_count

    def _set_secure_permissions(self) -> None:
        """Set secure permissions on credential files"""
        try:
            # Set secure permissions on credential files
            credential_patterns = [
                "credentials.json",
                "credentials/*.json",
                "data/*/token.json",
                "data/*/*.json",
                ".env"
            ]

            for pattern in credential_patterns:
                for file_path in glob.glob(pattern):
                    if os.path.exists(file_path):
                        os.chmod(file_path, 0o600)
                        logger.debug(f"Set secure permissions on {file_path}")

        except Exception as e:
            logger.warning(f"Failed to set secure permissions: {e}")

    def _post_restore_automation(self, backup_type: str) -> None:
        """Perform post-restore automation tasks"""
        try:
            print("🔄 Running post-restore automation...")

            # Check OAuth status and offer setup if needed
            if backup_type in ["complete", "credentials"]:
                self._check_oauth_status()

            # Offer to start services if they're not running
            self._check_service_status()

            # Validate configuration after restore
            self._validate_post_restore_config()

            print("✅ Post-restore automation completed")

        except Exception as e:
            logger.warning(f"Post-restore automation failed: {e}")
            print(f"⚠️  Post-restore automation failed: {e}")

    def _check_oauth_status(self) -> None:
        """Check OAuth status and offer setup guidance"""
        try:
            import subprocess
            result = subprocess.run(
                ["./manage_fogis_system.sh", "oauth-status"],
                capture_output=True,
                text=True,
                cwd=self.base_path
            )

            if "Setup complete: ❌" in result.stdout:
                print("🔐 OAuth setup appears incomplete after restore.")
                print("💡 Consider running: ./manage_fogis_system.sh setup-oauth")

        except Exception as e:
            logger.debug(f"OAuth status check failed: {e}")

    def _check_service_status(self) -> None:
        """Check service status and offer to start if needed"""
        try:
            import subprocess
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                cwd=self.base_path
            )

            if result.returncode == 0:
                import json
                services = json.loads(result.stdout) if result.stdout.strip() else []
                running_services = [s for s in services if s.get("State") == "running"]

                if len(running_services) < 6:  # Expected number of services
                    print("🚀 Some services may not be running after restore.")
                    print("💡 Consider running: ./manage_fogis_system.sh start")

        except Exception as e:
            logger.debug(f"Service status check failed: {e}")

    def _validate_post_restore_config(self) -> None:
        """Validate configuration after restore"""
        try:
            import subprocess
            result = subprocess.run(
                ["./manage_fogis_system.sh", "config-validate"],
                capture_output=True,
                text=True,
                cwd=self.base_path
            )

            if result.returncode != 0:
                print("⚠️  Configuration validation found issues after restore.")
                print("💡 Consider running: ./manage_fogis_system.sh config-validate")

        except Exception as e:
            logger.debug(f"Config validation failed: {e}")


def main():
    """
    Main function for backup manager CLI
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python backup_manager.py <command> [args]")
        print("Commands: create, restore, list, validate, delete, cleanup")
        sys.exit(1)

    command = sys.argv[1]
    backup_manager = BackupManager()

    try:
        if command == "create":
            backup_type = sys.argv[2] if len(sys.argv) > 2 else "complete"
            backup_file = backup_manager.create_backup(backup_type)
            print(f"Backup created: {backup_file}")

        elif command == "restore":
            if len(sys.argv) < 3:
                print("Usage: python backup_manager.py restore <backup_file>")
                sys.exit(1)
            backup_file = sys.argv[2]
            backup_manager.restore_backup(backup_file)
            print("Backup restored successfully")

        elif command == "list":
            backups = backup_manager.list_backups()
            if backups:
                print(f"Found {len(backups)} backups:")
                for backup in backups:
                    print(f"  {backup['file_path']} ({backup['type']}) - {backup['created_at']}")
            else:
                print("No backups found")

        elif command == "validate":
            if len(sys.argv) < 3:
                print("Usage: python backup_manager.py validate <backup_file>")
                sys.exit(1)
            backup_file = sys.argv[2]
            if backup_manager.validate_backup(backup_file):
                print("Backup is valid")
            else:
                print("Backup is invalid")
                sys.exit(1)

        elif command == "delete":
            if len(sys.argv) < 3:
                print("Usage: python backup_manager.py delete <backup_file>")
                sys.exit(1)
            backup_file = sys.argv[2]
            if backup_manager.delete_backup(backup_file):
                print("Backup deleted successfully")
            else:
                print("Failed to delete backup")
                sys.exit(1)

        elif command == "cleanup":
            keep_count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            deleted = backup_manager.cleanup_old_backups(keep_count)
            print(f"Cleaned up {deleted} old backups")

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
