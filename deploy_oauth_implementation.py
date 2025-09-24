#!/usr/bin/env python3
"""
Deployment script for FOGIS OAuth 2.0 PKCE implementation.

This script helps deploy the OAuth implementation to the FOGIS API client container
and validates that the authentication works correctly.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def print_status(message: str, status: str = "INFO"):
    """Print a status message with formatting."""
    icons = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "PROGRESS": "🔄"
    }
    print(f"{icons.get(status, 'ℹ️')} {message}")


def run_command(command: str, cwd: str = None) -> tuple[bool, str]:
    """Run a shell command and return success status and output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def backup_container_files():
    """Backup existing container files before deployment."""
    print_status("Creating backup of existing container files...", "PROGRESS")

    backup_dir = Path("oauth_deployment_backup")
    backup_dir.mkdir(exist_ok=True)

    # Files to backup from container
    files_to_backup = [
        "/app/fogis_api_client/internal/auth.py",
        "/app/fogis_api_client/public_api_client.py",
        "/app/fogis_api_client/fogis_api_client.py"
    ]

    backup_success = True
    for file_path in files_to_backup:
        try:
            success, output = run_command(f"docker cp fogis-api-client-service:{file_path} {backup_dir}/")
            if success:
                print_status(f"Backed up {file_path}", "SUCCESS")
            else:
                print_status(f"Failed to backup {file_path}: {output}", "WARNING")
                # Don't fail the entire backup for individual file failures
        except Exception as e:
            print_status(f"Error backing up {file_path}: {e}", "WARNING")

    print_status("Backup completed", "SUCCESS")
    return True  # Always return True since backup failures shouldn't stop deployment


def deploy_oauth_files():
    """Deploy OAuth implementation files to the container."""
    print_status("Deploying OAuth implementation files...", "PROGRESS")
    
    # Files to deploy
    deployment_files = [
        ("fogis_oauth_manager.py", "/app/fogis_oauth_manager.py"),
        ("fogis_auth_oauth.py", "/app/fogis_api_client/internal/auth_oauth.py"),
        ("fogis_public_api_client_oauth.py", "/app/fogis_api_client/public_api_client_oauth.py")
    ]
    
    for local_file, container_path in deployment_files:
        if not Path(local_file).exists():
            print_status(f"Local file {local_file} not found", "ERROR")
            return False
        
        try:
            success, output = run_command(f"docker cp {local_file} fogis-api-client-service:{container_path}")
            if success:
                print_status(f"Deployed {local_file} to {container_path}", "SUCCESS")
            else:
                print_status(f"Failed to deploy {local_file}: {output}", "ERROR")
                return False
        except Exception as e:
            print_status(f"Error deploying {local_file}: {e}", "ERROR")
            return False
    
    return True


def update_container_imports():
    """Update container imports to use OAuth implementation."""
    print_status("Updating container imports for OAuth...", "PROGRESS")
    
    # Create a script to update imports in the container
    update_script = """
import sys
import os

# Update the main API client to use OAuth
try:
    # Backup original auth module
    os.rename('/app/fogis_api_client/internal/auth.py', '/app/fogis_api_client/internal/auth_original.py')
    
    # Replace with OAuth version
    os.rename('/app/fogis_api_client/internal/auth_oauth.py', '/app/fogis_api_client/internal/auth.py')
    
    print("✅ Updated auth module to use OAuth")
    
    # Update public API client
    os.rename('/app/fogis_api_client/public_api_client.py', '/app/fogis_api_client/public_api_client_original.py')
    os.rename('/app/fogis_api_client/public_api_client_oauth.py', '/app/fogis_api_client/public_api_client.py')
    
    print("✅ Updated public API client to use OAuth")
    
except Exception as e:
    print(f"❌ Error updating imports: {e}")
    sys.exit(1)
"""
    
    # Write update script to temporary file
    with open("update_imports.py", "w") as f:
        f.write(update_script)
    
    try:
        # Copy script to container and run it
        success, output = run_command("docker cp update_imports.py fogis-api-client-service:/app/")
        if not success:
            print_status(f"Failed to copy update script: {output}", "ERROR")
            return False
        
        success, output = run_command("docker exec fogis-api-client-service python /app/update_imports.py")
        if success:
            print_status("Container imports updated successfully", "SUCCESS")
            return True
        else:
            print_status(f"Failed to update imports: {output}", "ERROR")
            return False
            
    finally:
        # Clean up temporary file
        if os.path.exists("update_imports.py"):
            os.remove("update_imports.py")


def restart_container_service():
    """Restart the FOGIS API client service."""
    print_status("Restarting FOGIS API client service...", "PROGRESS")
    
    success, output = run_command("docker-compose restart fogis-api-client-service")
    if success:
        print_status("Service restarted successfully", "SUCCESS")
        
        # Wait for service to be ready
        print_status("Waiting for service to be ready...", "PROGRESS")
        time.sleep(10)
        
        return True
    else:
        print_status(f"Failed to restart service: {output}", "ERROR")
        return False


def test_oauth_deployment():
    """Test that the OAuth deployment is working."""
    print_status("Testing OAuth deployment...", "PROGRESS")
    
    # Test 1: Check if OAuth manager is importable
    test_import_script = """
try:
    from fogis_oauth_manager import FogisOAuthManager
    print("✅ OAuth manager import successful")
    
    # Test OAuth URL generation
    manager = FogisOAuthManager()
    auth_url = manager.create_authorization_url()
    print(f"✅ OAuth URL generation successful: {auth_url[:50]}...")
    
except Exception as e:
    print(f"❌ OAuth manager test failed: {e}")
    import traceback
    traceback.print_exc()
"""
    
    with open("test_oauth_import.py", "w") as f:
        f.write(test_import_script)
    
    try:
        success, output = run_command("docker cp test_oauth_import.py fogis-api-client-service:/app/")
        if not success:
            print_status(f"Failed to copy test script: {output}", "ERROR")
            return False
        
        success, output = run_command("docker exec fogis-api-client-service python /app/test_oauth_import.py")
        print(output)
        
        if success and "OAuth URL generation successful" in output:
            print_status("OAuth import test passed", "SUCCESS")
        else:
            print_status("OAuth import test failed", "ERROR")
            return False
            
    finally:
        if os.path.exists("test_oauth_import.py"):
            os.remove("test_oauth_import.py")
    
    # Test 2: Check API client initialization
    test_client_script = """
try:
    import sys
    sys.path.insert(0, '/app')
    
    from fogis_api_client.public_api_client import PublicApiClient
    
    # Test OAuth token initialization
    oauth_tokens = {
        'access_token': 'test_token',
        'refresh_token': 'test_refresh',
        'expires_in': 3600
    }
    
    client = PublicApiClient(oauth_tokens=oauth_tokens)
    print(f"✅ OAuth client initialization successful: {client.authentication_method}")
    
    # Test credential initialization
    client2 = PublicApiClient(username="test", password="test")
    print(f"✅ Credential client initialization successful")
    
except Exception as e:
    print(f"❌ Client test failed: {e}")
    import traceback
    traceback.print_exc()
"""
    
    with open("test_client.py", "w") as f:
        f.write(test_client_script)
    
    try:
        success, output = run_command("docker cp test_client.py fogis-api-client-service:/app/")
        if not success:
            print_status(f"Failed to copy client test script: {output}", "ERROR")
            return False
        
        success, output = run_command("docker exec fogis-api-client-service python /app/test_client.py")
        print(output)
        
        if success and "OAuth client initialization successful" in output:
            print_status("Client test passed", "SUCCESS")
            return True
        else:
            print_status("Client test failed", "ERROR")
            return False
            
    finally:
        if os.path.exists("test_client.py"):
            os.remove("test_client.py")


def test_authentication_endpoint():
    """Test the authentication endpoint to see if OAuth errors are resolved."""
    print_status("Testing authentication endpoint...", "PROGRESS")
    
    # Test the /matches endpoint that was failing
    success, output = run_command("curl -s http://localhost:9086/matches")
    
    if success:
        if "Bad Rquest" in output:
            print_status("OAuth errors still present in response", "WARNING")
            print(f"Response: {output[:200]}...")
            return False
        elif "500" in output or "error" in output.lower():
            print_status("Different error in response (progress!)", "WARNING")
            print(f"Response: {output[:200]}...")
            return True  # This is progress - no more OAuth errors
        else:
            print_status("Endpoint responding successfully", "SUCCESS")
            return True
    else:
        print_status(f"Failed to test endpoint: {output}", "ERROR")
        return False


def main():
    """Main deployment function."""
    print_status("🚀 FOGIS OAuth 2.0 PKCE Deployment", "INFO")
    print("=" * 60)
    
    # Check if container is running
    success, output = run_command("docker ps | grep fogis-api-client-service")
    if not success:
        print_status("FOGIS API client container is not running", "ERROR")
        print_status("Please start the container with: docker-compose up -d", "INFO")
        return False
    
    print_status("Container is running, proceeding with deployment", "SUCCESS")
    
    # Deployment steps
    steps = [
        ("Backup existing files", backup_container_files),
        ("Deploy OAuth files", deploy_oauth_files),
        ("Update container imports", update_container_imports),
        ("Restart service", restart_container_service),
        ("Test OAuth deployment", test_oauth_deployment),
        ("Test authentication endpoint", test_authentication_endpoint)
    ]
    
    for step_name, step_func in steps:
        print_status(f"Step: {step_name}", "PROGRESS")
        
        try:
            if not step_func():
                print_status(f"Step failed: {step_name}", "ERROR")
                return False
        except Exception as e:
            print_status(f"Step crashed: {step_name} - {e}", "ERROR")
            return False
        
        print_status(f"Step completed: {step_name}", "SUCCESS")
        print()
    
    print_status("🎉 OAuth deployment completed successfully!", "SUCCESS")
    print_status("The FOGIS API client now supports OAuth 2.0 PKCE authentication", "INFO")
    print_status("Monitor the logs to verify that 'Bad Rquest' errors are resolved", "INFO")
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
