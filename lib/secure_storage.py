"""
Secure Credential Storage

Handles secure storage and encryption of credentials for the FOGIS system.
Provides encrypted storage with proper file permissions and access control.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import stat


class SecureCredentialStore:
    """
    Manages secure storage of credentials with encryption and access control.
    
    This class provides functionality for:
    - Encrypted credential storage
    - Secure file permissions
    - Credential backup and restore
    - Access logging and audit trails
    """

    def __init__(self, storage_dir: str = "credentials", master_password: Optional[str] = None):
        """
        Initialize the secure credential store.
        
        Args:
            storage_dir: Directory to store encrypted credentials
            master_password: Master password for encryption (auto-generated if None)
        """
        self.storage_dir = storage_dir
        self.logger = logging.getLogger(__name__)
        
        # Create storage directory with secure permissions
        self._create_secure_directory()
        
        # Initialize encryption
        self.key_file = os.path.join(self.storage_dir, '.encryption_key')
        self.fernet = self._initialize_encryption(master_password)
        
        # Audit log file
        self.audit_log = os.path.join(self.storage_dir, 'access.log')

    def _create_secure_directory(self) -> None:
        """Create storage directory with secure permissions."""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir, mode=0o700)  # Owner read/write/execute only
            self.logger.info(f"Created secure storage directory: {self.storage_dir}")
        else:
            # Ensure existing directory has secure permissions
            os.chmod(self.storage_dir, 0o700)

    def _initialize_encryption(self, master_password: Optional[str] = None) -> Fernet:
        """
        Initialize encryption key and Fernet cipher.
        
        Args:
            master_password: Master password for key derivation
            
        Returns:
            Fernet cipher instance
        """
        if os.path.exists(self.key_file):
            # Load existing key
            with open(self.key_file, 'rb') as f:
                key = f.read()
        else:
            # Generate new key
            if master_password is None:
                # Auto-generate a secure key
                key = Fernet.generate_key()
            else:
                # Derive key from master password
                password_bytes = master_password.encode()
                salt = os.urandom(16)
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
                
                # Store salt with key for future derivation
                key_data = {
                    'key': key.decode(),
                    'salt': base64.b64encode(salt).decode(),
                    'iterations': 100000
                }
                key = json.dumps(key_data).encode()
            
            # Save key with secure permissions
            with open(self.key_file, 'wb') as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)  # Owner read/write only
            
            self.logger.info("Generated new encryption key")
        
        # Handle both simple key and key with metadata
        try:
            if key.startswith(b'{'):
                # Key with metadata (from master password)
                key_data = json.loads(key.decode())
                actual_key = key_data['key'].encode()
            else:
                # Simple key
                actual_key = key
            
            return Fernet(actual_key)
        except Exception as e:
            self.logger.error(f"Error initializing encryption: {e}")
            raise

    def _log_access(self, action: str, service: str, success: bool) -> None:
        """
        Log access attempts for audit purposes.
        
        Args:
            action: Action performed (store, retrieve, delete)
            service: Service name
            success: Whether the action was successful
        """
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp} - {action.upper()} - {service} - {'SUCCESS' if success else 'FAILED'}\n"
        
        try:
            with open(self.audit_log, 'a') as f:
                f.write(log_entry)
            os.chmod(self.audit_log, 0o600)
        except Exception as e:
            self.logger.error(f"Error writing audit log: {e}")

    def store_credentials(self, service: str, credentials: Dict[str, Any]) -> bool:
        """
        Store credentials securely for a service.
        
        Args:
            service: Service name (e.g., 'google_oauth', 'fogis_auth')
            credentials: Dictionary containing credentials
            
        Returns:
            True if storage was successful, False otherwise
        """
        try:
            # Add metadata
            credential_data = {
                'service': service,
                'credentials': credentials,
                'stored_at': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            # Encrypt credentials
            json_data = json.dumps(credential_data).encode()
            encrypted_data = self.fernet.encrypt(json_data)
            
            # Store to file
            credential_file = os.path.join(self.storage_dir, f"{service}.enc")
            with open(credential_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Set secure permissions
            os.chmod(credential_file, 0o600)
            
            self._log_access('store', service, True)
            self.logger.info(f"Stored credentials for service: {service}")
            return True
            
        except Exception as e:
            self._log_access('store', service, False)
            self.logger.error(f"Error storing credentials for {service}: {e}")
            return False

    def retrieve_credentials(self, service: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve credentials for a service.
        
        Args:
            service: Service name
            
        Returns:
            Dictionary containing credentials or None if not found
        """
        try:
            credential_file = os.path.join(self.storage_dir, f"{service}.enc")
            
            if not os.path.exists(credential_file):
                self.logger.info(f"No credentials found for service: {service}")
                return None
            
            # Read encrypted data
            with open(credential_file, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt credentials
            decrypted_data = self.fernet.decrypt(encrypted_data)
            credential_data = json.loads(decrypted_data.decode())
            
            self._log_access('retrieve', service, True)
            self.logger.info(f"Retrieved credentials for service: {service}")
            
            return credential_data.get('credentials', {})
            
        except Exception as e:
            self._log_access('retrieve', service, False)
            self.logger.error(f"Error retrieving credentials for {service}: {e}")
            return None

    def delete_credentials(self, service: str) -> bool:
        """
        Delete credentials for a service.
        
        Args:
            service: Service name
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            credential_file = os.path.join(self.storage_dir, f"{service}.enc")
            
            if os.path.exists(credential_file):
                os.remove(credential_file)
                self._log_access('delete', service, True)
                self.logger.info(f"Deleted credentials for service: {service}")
                return True
            else:
                self.logger.info(f"No credentials to delete for service: {service}")
                return True
                
        except Exception as e:
            self._log_access('delete', service, False)
            self.logger.error(f"Error deleting credentials for {service}: {e}")
            return False

    def list_stored_services(self) -> list:
        """
        List all services with stored credentials.
        
        Returns:
            List of service names
        """
        try:
            services = []
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.enc'):
                    service_name = filename[:-4]  # Remove .enc extension
                    services.append(service_name)
            
            return services
            
        except Exception as e:
            self.logger.error(f"Error listing stored services: {e}")
            return []

    def backup_credentials(self, backup_file: str) -> bool:
        """
        Create a backup of all stored credentials.
        
        Args:
            backup_file: Path to backup file
            
        Returns:
            True if backup was successful, False otherwise
        """
        try:
            backup_data = {
                'created_at': datetime.now().isoformat(),
                'services': {}
            }
            
            # Collect all credentials
            for service in self.list_stored_services():
                credentials = self.retrieve_credentials(service)
                if credentials:
                    backup_data['services'][service] = credentials
            
            # Encrypt backup
            json_data = json.dumps(backup_data).encode()
            encrypted_backup = self.fernet.encrypt(json_data)
            
            # Save backup
            with open(backup_file, 'wb') as f:
                f.write(encrypted_backup)
            
            os.chmod(backup_file, 0o600)
            
            self.logger.info(f"Created credential backup: {backup_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            return False

    def restore_credentials(self, backup_file: str) -> bool:
        """
        Restore credentials from a backup file.
        
        Args:
            backup_file: Path to backup file
            
        Returns:
            True if restore was successful, False otherwise
        """
        try:
            if not os.path.exists(backup_file):
                self.logger.error(f"Backup file not found: {backup_file}")
                return False
            
            # Read and decrypt backup
            with open(backup_file, 'rb') as f:
                encrypted_backup = f.read()
            
            decrypted_data = self.fernet.decrypt(encrypted_backup)
            backup_data = json.loads(decrypted_data.decode())
            
            # Restore each service
            restored_count = 0
            for service, credentials in backup_data.get('services', {}).items():
                if self.store_credentials(service, credentials):
                    restored_count += 1
            
            self.logger.info(f"Restored {restored_count} services from backup")
            return restored_count > 0
            
        except Exception as e:
            self.logger.error(f"Error restoring from backup: {e}")
            return False

    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about the credential storage.
        
        Returns:
            Dictionary with storage information
        """
        try:
            services = self.list_stored_services()
            
            # Get storage directory size
            total_size = 0
            for filename in os.listdir(self.storage_dir):
                filepath = os.path.join(self.storage_dir, filename)
                if os.path.isfile(filepath):
                    total_size += os.path.getsize(filepath)
            
            return {
                'storage_dir': self.storage_dir,
                'stored_services': services,
                'service_count': len(services),
                'total_size_bytes': total_size,
                'encryption_enabled': True,
                'audit_log_exists': os.path.exists(self.audit_log)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting storage info: {e}")
            return {}
