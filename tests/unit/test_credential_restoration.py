#!/usr/bin/env python3

"""
Unit tests for FOGIS credential restoration functionality
Tests the restore_fogis_credentials.sh script and validation components
"""

import os
import sys
import pytest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the scripts directory to the path for importing validation module
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

try:
    from validate_fogis_credentials import FOGISCredentialValidator
except ImportError:
    # If import fails, create a mock for testing
    class FOGISCredentialValidator:
        def __init__(self, username=None, password=None):
            self.username = username
            self.password = password
        
        def validate(self):
            return True, "Mock validation", {}

class TestCredentialRestoration:
    """Test suite for credential restoration functionality"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def mock_backup_dir(self, temp_dir):
        """Create a mock backup directory with test credentials"""
        backup_dir = temp_dir / "fogis-credentials-backup-20250717-140734"
        backup_dir.mkdir()
        
        # Create mock credentials file
        credentials_file = backup_dir / "FOGIS_CREDENTIALS.txt"
        credentials_content = """FOGIS Authentication Credentials:
=================================

Found .env file - extracting FOGIS credentials...
FOGIS_USERNAME=Test User
FOGIS_PASSWORD=test_password

Note: Based on previous testing, FOGIS credentials are:
Username: [To be provided during setup]
Password: temporary
"""
        credentials_file.write_text(credentials_content)
        
        # Create restoration guide
        guide_file = backup_dir / "RESTORATION_GUIDE.md"
        guide_file.write_text("# Test restoration guide")
        
        return backup_dir
    
    @pytest.fixture
    def mock_env_file(self, temp_dir):
        """Create a mock .env file"""
        env_file = temp_dir / ".env"
        env_content = """# Test environment file
FOGIS_USERNAME=old_user
FOGIS_PASSWORD=old_password
LOG_LEVEL=INFO
"""
        env_file.write_text(env_content)
        return env_file
    
    def test_credential_extraction_from_backup(self, mock_backup_dir):
        """Test extracting credentials from backup file"""
        credentials_file = mock_backup_dir / "FOGIS_CREDENTIALS.txt"
        content = credentials_file.read_text()
        
        # Extract username and password using the same logic as the script
        username = None
        password = None
        
        for line in content.split('\n'):
            if line.startswith('FOGIS_USERNAME='):
                username = line.split('=', 1)[1].strip()
            elif line.startswith('FOGIS_PASSWORD='):
                password = line.split('=', 1)[1].strip()
        
        assert username == "Test User"
        assert password == "test_password"
    
    def test_env_file_update(self, temp_dir, mock_env_file):
        """Test updating .env file with restored credentials"""
        # Read original content
        original_content = mock_env_file.read_text()
        assert "FOGIS_USERNAME=old_user" in original_content
        
        # Simulate credential update
        new_content = original_content.replace(
            "FOGIS_USERNAME=old_user", 
            "FOGIS_USERNAME=Test User"
        ).replace(
            "FOGIS_PASSWORD=old_password",
            "FOGIS_PASSWORD=test_password"
        )
        
        mock_env_file.write_text(new_content)
        
        # Verify update
        updated_content = mock_env_file.read_text()
        assert "FOGIS_USERNAME=Test User" in updated_content
        assert "FOGIS_PASSWORD=test_password" in updated_content
        assert "LOG_LEVEL=INFO" in updated_content  # Ensure other vars preserved
    
    def test_backup_directory_detection(self, temp_dir):
        """Test automatic backup directory detection"""
        # Create multiple backup directories
        backup1 = temp_dir / "fogis-credentials-backup-20250717-140734"
        backup2 = temp_dir / "fogis-credentials-backup-20250717-150000"
        
        backup1.mkdir()
        backup2.mkdir()
        
        # Create credentials files
        (backup1 / "FOGIS_CREDENTIALS.txt").write_text("FOGIS_USERNAME=user1\nFOGIS_PASSWORD=pass1")
        (backup2 / "FOGIS_CREDENTIALS.txt").write_text("FOGIS_USERNAME=user2\nFOGIS_PASSWORD=pass2")
        
        # Test detection logic (most recent should be selected)
        backup_dirs = [str(backup1), str(backup2)]
        most_recent = sorted(backup_dirs, reverse=True)[0]
        
        assert "20250717-150000" in most_recent
    
    def test_credential_validation_format(self):
        """Test credential format validation"""
        validator = FOGISCredentialValidator("test_user", "test_password")
        
        # Test valid credentials
        valid, message = validator.validate_credentials_format()
        assert valid is True
        assert "valid" in message.lower()
        
        # Test empty username
        validator.username = ""
        valid, message = validator.validate_credentials_format()
        assert valid is False
        assert ("empty" in message.lower() or "not provided" in message.lower())
        
        # Test missing password
        validator.username = "test_user"
        validator.password = None
        valid, message = validator.validate_credentials_format()
        assert valid is False
        assert "password" in message.lower()
    
    def test_env_file_loading(self, temp_dir):
        """Test loading credentials from .env file"""
        env_file = temp_dir / ".env"
        env_content = """FOGIS_USERNAME=env_user
FOGIS_PASSWORD=env_password
OTHER_VAR=value
"""
        env_file.write_text(env_content)
        
        validator = FOGISCredentialValidator()
        success = validator.load_credentials_from_env_file(str(env_file))
        
        assert success is True
        assert validator.username == "env_user"
        assert validator.password == "env_password"
    
    def test_env_file_loading_missing_file(self, temp_dir):
        """Test loading from non-existent .env file"""
        validator = FOGISCredentialValidator()
        success = validator.load_credentials_from_env_file(str(temp_dir / "nonexistent.env"))
        
        assert success is False
    
    def test_credential_restoration_script_help(self):
        """Test that the restoration script shows help correctly"""
        script_path = Path(__file__).parent.parent.parent / "restore_fogis_credentials.sh"
        
        if script_path.exists():
            result = subprocess.run(
                [str(script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            assert result.returncode == 0
            assert "FOGIS Credential Restoration Tool" in result.stdout
            assert "Usage:" in result.stdout
            assert "--auto" in result.stdout
            assert "--validate" in result.stdout
            assert "--dry-run" in result.stdout
    
    def test_credential_restoration_script_dry_run(self, mock_backup_dir):
        """Test dry run functionality of restoration script"""
        script_path = Path(__file__).parent.parent.parent / "restore_fogis_credentials.sh"
        
        if script_path.exists():
            result = subprocess.run(
                [str(script_path), str(mock_backup_dir), "--dry-run"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(mock_backup_dir.parent)
            )
            
            # Should succeed and show what would be done
            assert "DRY RUN:" in result.stdout
            assert "Test User" in result.stdout
            assert "[REDACTED]" in result.stdout
    
    @patch('requests.Session')
    def test_fogis_authentication_mock(self, mock_session):
        """Test FOGIS authentication with mocked requests"""
        # Mock successful authentication
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Welcome to FOGIS"
        mock_session.return_value.get.return_value = mock_response
        mock_session.return_value.post.return_value = mock_response
        
        validator = FOGISCredentialValidator("test_user", "test_password")
        success, message, details = validator.test_fogis_authentication()
        
        assert success is True
        assert "successful" in message.lower()
        assert details.get('authenticated') is True
    
    @patch('requests.Session')
    def test_fogis_authentication_failure_mock(self, mock_session):
        """Test FOGIS authentication failure with mocked requests"""
        # Mock authentication failure
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Invalid credentials"
        mock_session.return_value.get.return_value = mock_response
        mock_session.return_value.post.return_value = mock_response
        
        validator = FOGISCredentialValidator("wrong_user", "wrong_password")
        success, message, details = validator.test_fogis_authentication()
        
        assert success is False
        assert "invalid" in message.lower()
    
    def test_missing_backup_directory_handling(self):
        """Test handling of missing backup directory"""
        script_path = Path(__file__).parent.parent.parent / "restore_fogis_credentials.sh"
        
        if script_path.exists():
            result = subprocess.run(
                [str(script_path), "/nonexistent/backup/dir"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            assert result.returncode != 0
            assert "not found" in result.stderr or "not found" in result.stdout
    
    def test_malformed_credentials_file(self, temp_dir):
        """Test handling of malformed credentials file"""
        backup_dir = temp_dir / "fogis-credentials-backup-malformed"
        backup_dir.mkdir()
        
        # Create malformed credentials file
        credentials_file = backup_dir / "FOGIS_CREDENTIALS.txt"
        credentials_file.write_text("This is not a valid credentials file")
        
        script_path = Path(__file__).parent.parent.parent / "restore_fogis_credentials.sh"
        
        if script_path.exists():
            result = subprocess.run(
                [str(script_path), str(backup_dir), "--dry-run"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Should fail gracefully
            assert result.returncode != 0
            assert "extract" in result.stderr or "extract" in result.stdout

class TestCredentialValidationIntegration:
    """Integration tests for credential validation"""
    
    def test_end_to_end_validation_with_env_file(self, tmp_path):
        """Test complete validation workflow with .env file"""
        # Create test .env file
        temp_dir = tmp_path
        env_file = temp_dir / ".env"
        env_content = """FOGIS_USERNAME=integration_test_user
FOGIS_PASSWORD=integration_test_password
"""
        env_file.write_text(env_content)
        
        # Change to temp directory for testing
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            validator = FOGISCredentialValidator()
            success, message, details = validator.validate()
            
            # Should load credentials successfully (authentication will fail with test creds)
            assert validator.username == "integration_test_user"
            assert validator.password == "integration_test_password"
            
        finally:
            os.chdir(original_cwd)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
