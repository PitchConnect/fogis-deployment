"""
Unit tests for the secure storage module.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
import os
import json
import sys
import tempfile
import shutil

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from lib.secure_storage import SecureCredentialStore


class TestSecureCredentialStore:
    """Test cases for SecureCredentialStore class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Use a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.store = SecureCredentialStore(storage_dir=self.test_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_store_initialization(self):
        """Test secure store initialization."""
        assert self.store.storage_dir == self.test_dir
        assert os.path.exists(self.test_dir)
        assert oct(os.stat(self.test_dir).st_mode)[-3:] == '700'  # Check permissions

    def test_store_and_retrieve_credentials(self):
        """Test storing and retrieving credentials."""
        test_credentials = {
            'username': 'testuser',
            'password': 'testpass',
            'api_key': 'test_api_key'
        }
        
        # Store credentials
        result = self.store.store_credentials('test_service', test_credentials)
        assert result is True
        
        # Retrieve credentials
        retrieved = self.store.retrieve_credentials('test_service')
        assert retrieved == test_credentials

    def test_retrieve_nonexistent_credentials(self):
        """Test retrieving credentials that don't exist."""
        result = self.store.retrieve_credentials('nonexistent_service')
        assert result is None

    def test_delete_credentials(self):
        """Test deleting credentials."""
        test_credentials = {'test': 'data'}
        
        # Store and then delete
        self.store.store_credentials('test_service', test_credentials)
        result = self.store.delete_credentials('test_service')
        assert result is True
        
        # Verify deletion
        retrieved = self.store.retrieve_credentials('test_service')
        assert retrieved is None

    def test_delete_nonexistent_credentials(self):
        """Test deleting credentials that don't exist."""
        result = self.store.delete_credentials('nonexistent_service')
        assert result is True  # Should succeed even if file doesn't exist

    def test_list_stored_services(self):
        """Test listing stored services."""
        # Store multiple services
        self.store.store_credentials('service1', {'data': 'test1'})
        self.store.store_credentials('service2', {'data': 'test2'})
        self.store.store_credentials('service3', {'data': 'test3'})
        
        services = self.store.list_stored_services()
        assert len(services) == 3
        assert 'service1' in services
        assert 'service2' in services
        assert 'service3' in services

    def test_backup_and_restore_credentials(self):
        """Test backup and restore functionality."""
        # Store test data
        test_data1 = {'username': 'user1', 'password': 'pass1'}
        test_data2 = {'username': 'user2', 'password': 'pass2'}
        
        self.store.store_credentials('service1', test_data1)
        self.store.store_credentials('service2', test_data2)
        
        # Create backup
        backup_file = os.path.join(self.test_dir, 'backup.enc')
        result = self.store.backup_credentials(backup_file)
        assert result is True
        assert os.path.exists(backup_file)
        
        # Clear existing data
        self.store.delete_credentials('service1')
        self.store.delete_credentials('service2')
        
        # Restore from backup
        result = self.store.restore_credentials(backup_file)
        assert result is True
        
        # Verify restored data
        restored1 = self.store.retrieve_credentials('service1')
        restored2 = self.store.retrieve_credentials('service2')
        assert restored1 == test_data1
        assert restored2 == test_data2

    def test_restore_nonexistent_backup(self):
        """Test restoring from nonexistent backup file."""
        result = self.store.restore_credentials('nonexistent_backup.enc')
        assert result is False

    def test_get_storage_info(self):
        """Test getting storage information."""
        # Store some test data
        self.store.store_credentials('test_service', {'test': 'data'})
        
        info = self.store.get_storage_info()
        
        assert info['storage_dir'] == self.test_dir
        assert 'test_service' in info['stored_services']
        assert info['service_count'] == 1
        assert info['total_size_bytes'] > 0
        assert info['encryption_enabled'] is True

    @patch('os.makedirs')
    @patch('os.chmod')
    def test_create_secure_directory_new(self, mock_chmod, mock_makedirs):
        """Test creating new secure directory."""
        with patch('os.path.exists', return_value=False):
            store = SecureCredentialStore('new_test_dir')
            mock_makedirs.assert_called_once_with('new_test_dir', mode=0o700)

    @patch('os.chmod')
    def test_create_secure_directory_existing(self, mock_chmod):
        """Test securing existing directory."""
        with patch('os.path.exists', return_value=True):
            store = SecureCredentialStore('existing_dir')
            mock_chmod.assert_called_with('existing_dir', 0o700)

    def test_encryption_key_persistence(self):
        """Test that encryption key persists across instances."""
        # Store data with first instance
        test_data = {'test': 'encryption_persistence'}
        self.store.store_credentials('test_service', test_data)
        
        # Create new instance with same directory
        new_store = SecureCredentialStore(storage_dir=self.test_dir)
        
        # Should be able to retrieve data encrypted by first instance
        retrieved = new_store.retrieve_credentials('test_service')
        assert retrieved == test_data

    def test_audit_logging(self):
        """Test audit logging functionality."""
        # Perform some operations
        self.store.store_credentials('test_service', {'test': 'data'})
        self.store.retrieve_credentials('test_service')
        self.store.delete_credentials('test_service')
        
        # Check audit log exists
        audit_log_path = os.path.join(self.test_dir, 'access.log')
        assert os.path.exists(audit_log_path)
        
        # Check log content
        with open(audit_log_path, 'r') as f:
            log_content = f.read()
            assert 'STORE - test_service - SUCCESS' in log_content
            assert 'RETRIEVE - test_service - SUCCESS' in log_content
            assert 'DELETE - test_service - SUCCESS' in log_content

    @patch('cryptography.fernet.Fernet.encrypt')
    def test_store_credentials_encryption_failure(self, mock_encrypt):
        """Test handling of encryption failure during store."""
        mock_encrypt.side_effect = Exception("Encryption failed")
        
        result = self.store.store_credentials('test_service', {'test': 'data'})
        assert result is False

    @patch('cryptography.fernet.Fernet.decrypt')
    def test_retrieve_credentials_decryption_failure(self, mock_decrypt):
        """Test handling of decryption failure during retrieve."""
        # First store some data normally
        self.store.store_credentials('test_service', {'test': 'data'})
        
        # Then mock decryption failure
        mock_decrypt.side_effect = Exception("Decryption failed")
        
        result = self.store.retrieve_credentials('test_service')
        assert result is None

    def test_file_permissions(self):
        """Test that stored files have correct permissions."""
        self.store.store_credentials('test_service', {'test': 'data'})
        
        # Check credential file permissions
        credential_file = os.path.join(self.test_dir, 'test_service.enc')
        assert os.path.exists(credential_file)
        assert oct(os.stat(credential_file).st_mode)[-3:] == '600'  # Owner read/write only
        
        # Check key file permissions
        key_file = os.path.join(self.test_dir, '.encryption_key')
        assert os.path.exists(key_file)
        assert oct(os.stat(key_file).st_mode)[-3:] == '600'  # Owner read/write only

    def test_master_password_key_derivation(self):
        """Test key derivation from master password."""
        # Create store with master password
        master_password = "test_master_password"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            store_with_password = SecureCredentialStore(
                storage_dir=temp_dir, 
                master_password=master_password
            )
            
            # Store and retrieve data
            test_data = {'test': 'password_derived_key'}
            store_with_password.store_credentials('test_service', test_data)
            retrieved = store_with_password.retrieve_credentials('test_service')
            
            assert retrieved == test_data

    def test_concurrent_access_safety(self):
        """Test that concurrent access doesn't corrupt data."""
        import threading
        import time
        
        results = []
        
        def store_data(service_name, data):
            try:
                result = self.store.store_credentials(service_name, data)
                results.append(('store', service_name, result))
            except Exception as e:
                results.append(('store', service_name, False, str(e)))
        
        def retrieve_data(service_name):
            try:
                result = self.store.retrieve_credentials(service_name)
                results.append(('retrieve', service_name, result is not None))
            except Exception as e:
                results.append(('retrieve', service_name, False, str(e)))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            t1 = threading.Thread(target=store_data, args=(f'service_{i}', {'data': f'test_{i}'}))
            t2 = threading.Thread(target=retrieve_data, args=(f'service_{i}'))
            threads.extend([t1, t2])
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check that operations completed successfully
        store_results = [r for r in results if r[0] == 'store']
        assert len(store_results) == 5
        assert all(r[2] for r in store_results)  # All stores should succeed

    def test_large_data_handling(self):
        """Test handling of large credential data."""
        # Create large test data (1MB)
        large_data = {
            'large_field': 'x' * (1024 * 1024),
            'metadata': {'size': '1MB', 'type': 'test'}
        }
        
        # Store and retrieve large data
        result = self.store.store_credentials('large_service', large_data)
        assert result is True
        
        retrieved = self.store.retrieve_credentials('large_service')
        assert retrieved == large_data

    def test_special_characters_in_data(self):
        """Test handling of special characters in credential data."""
        special_data = {
            'unicode': 'Test with üñíçødé characters 🔐',
            'special_chars': '!@#$%^&*()_+-=[]{}|;:,.<>?',
            'newlines': 'Line 1\nLine 2\nLine 3',
            'quotes': 'Single \'quotes\' and "double quotes"'
        }
        
        # Store and retrieve data with special characters
        result = self.store.store_credentials('special_service', special_data)
        assert result is True
        
        retrieved = self.store.retrieve_credentials('special_service')
        assert retrieved == special_data
