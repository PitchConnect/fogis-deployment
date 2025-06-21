#!/usr/bin/env python3
"""
FOGIS System Configuration Wizard
Interactive setup for all required configuration parameters
"""

import os
import json
import getpass
import subprocess
from pathlib import Path

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_step(step_num, title):
    """Print a formatted step"""
    print(f"\n🔧 Step {step_num}: {title}")
    print("-" * 40)

def check_prerequisites():
    """Check if required tools are installed"""
    print_header("CHECKING PREREQUISITES")
    
    required_tools = ['docker', 'docker-compose']
    missing_tools = []
    
    for tool in required_tools:
        try:
            subprocess.run([tool, '--version'], capture_output=True, check=True)
            print(f"✅ {tool} is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"❌ {tool} is not installed")
            missing_tools.append(tool)
    
    if missing_tools:
        print(f"\n❌ Missing required tools: {', '.join(missing_tools)}")
        print("Please install them and run this script again.")
        return False
    
    return True

def collect_fogis_credentials():
    """Collect FOGIS login credentials"""
    print_step(1, "FOGIS Credentials")
    print("Enter your FOGIS login credentials:")
    
    username = input("FOGIS Username: ").strip()
    password = getpass.getpass("FOGIS Password: ")
    referee_number = input("Referee Number (from FOGIS profile): ").strip()
    
    return {
        'FOGIS_USERNAME': username,
        'FOGIS_PASSWORD': password,
        'USER_REFEREE_NUMBER': referee_number
    }

def setup_google_credentials():
    """Guide user through Google credentials setup"""
    print_step(2, "Google API Credentials")
    print("You need to set up Google API credentials for:")
    print("  • Google Calendar (match scheduling)")
    print("  • Google Contacts (referee phonebook)")
    print("  • Google Drive (WhatsApp assets)")
    print()
    print("📋 Instructions:")
    print("1. Go to: https://console.cloud.google.com/")
    print("2. Create a new project or select existing one")
    print("3. Enable these APIs:")
    print("   - Google Calendar API")
    print("   - Google People API (Contacts)")
    print("   - Google Drive API")
    print("4. Go to 'Credentials' → 'Create Credentials' → 'OAuth client ID'")
    print("5. Choose 'Desktop application'")
    print("6. Download the JSON file")
    print()
    
    while True:
        creds_path = input("Path to your Google credentials JSON file: ").strip()
        if os.path.exists(creds_path):
            # Copy to credentials directory
            os.makedirs('credentials', exist_ok=True)
            import shutil
            shutil.copy(creds_path, 'credentials/google-credentials.json')
            print("✅ Google credentials copied successfully")
            break
        else:
            print("❌ File not found. Please check the path and try again.")

def collect_service_configuration():
    """Collect service-specific configuration"""
    print_step(3, "Service Configuration")
    
    log_level = input("Log level (DEBUG/INFO/WARNING/ERROR) [INFO]: ").strip() or "INFO"
    
    print("\nAdvanced options (press Enter for defaults):")
    debug_mode = input("Enable debug mode? (y/N): ").strip().lower() == 'y'
    verbose_logging = input("Enable verbose logging? (y/N): ").strip().lower() == 'y'
    
    return {
        'LOG_LEVEL': log_level,
        'DEBUG_MODE': '1' if debug_mode else '0',
        'VERBOSE_LOGGING': '1' if verbose_logging else '0'
    }

def generate_env_file(config):
    """Generate .env file from configuration"""
    print_step(4, "Generating Configuration")
    
    # Default values
    defaults = {
        'GOOGLE_CREDENTIALS_PATH': '/app/credentials/google-credentials.json',
        'GOOGLE_SCOPES': 'https://www.googleapis.com/auth/calendar,https://www.googleapis.com/auth/contacts,https://www.googleapis.com/auth/drive',
        'MATCH_DETECTOR_PORT': '9080',
        'MATCH_PROCESSOR_PORT': '9082',
        'CALENDAR_SYNC_PORT': '9083',
        'LOGO_COMBINER_PORT': '9088',
        'DRIVE_SERVICE_PORT': '9085',
        'API_CLIENT_PORT': '9086',
        'MATCH_CHECK_SCHEDULE': '0 * * * *',
        'WEBHOOK_URL': 'http://match-list-processor:5000/process',
        'CALENDAR_SYNC_URL': 'http://fogis-calendar-phonebook-sync:5003/sync',
        'LOGO_COMBINER_URL': 'http://team-logo-combiner:5000/combine',
        'RESTART_POLICY': 'unless-stopped',
        'SKIP_SSL_VERIFICATION': '0',
        'FLASK_ENV': 'production',
        'GOOGLE_TOKEN_PATH': '/app/data/google-drive-token.json',
        'HEALTH_SERVER_PORT': '8080',
        'HEALTH_SERVER_HOST': '0.0.0.0',
        'PROMETHEUS_PORT': '8081'
    }
    
    # Merge configuration
    final_config = {**defaults, **config}
    
    # Write .env file
    with open('.env', 'w') as f:
        f.write("# FOGIS Deployment Configuration\n")
        f.write("# Generated by configure_system.py\n\n")
        
        for key, value in final_config.items():
            f.write(f"{key}={value}\n")
    
    print("✅ Configuration saved to .env")

def verify_configuration():
    """Verify the configuration is valid"""
    print_step(5, "Verifying Configuration")
    
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        return False
    
    if not os.path.exists('credentials/google-credentials.json'):
        print("❌ Google credentials not found")
        return False
    
    print("✅ Configuration files verified")
    return True

def main():
    """Main configuration wizard"""
    print_header("FOGIS SYSTEM CONFIGURATION WIZARD")
    print("This wizard will help you configure your FOGIS deployment.")
    print("You'll need:")
    print("  • FOGIS login credentials")
    print("  • Google Cloud project with APIs enabled")
    print("  • Google OAuth credentials JSON file")
    
    if not check_prerequisites():
        return 1
    
    try:
        # Collect all configuration
        fogis_config = collect_fogis_credentials()
        setup_google_credentials()
        service_config = collect_service_configuration()
        
        # Generate configuration files
        all_config = {**fogis_config, **service_config}
        generate_env_file(all_config)
        
        # Verify configuration
        if verify_configuration():
            print_header("CONFIGURATION COMPLETE")
            print("✅ Your FOGIS system is now configured!")
            print("\n📋 Next steps:")
            print("1. Start the system: ./manage_fogis_system.sh start")
            print("2. Authenticate services: python authenticate_all_services.py")
            print("3. Check system status: ./show_system_status.sh")
            print("\n🎯 Your FOGIS system will be ready to use!")
            return 0
        else:
            print("❌ Configuration verification failed")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n❌ Configuration cancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Configuration failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
