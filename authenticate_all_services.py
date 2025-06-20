#!/usr/bin/env python3
"""
Unified authentication script for all FOGIS services
Handles initial setup and token renewal
"""

import json
import os
import subprocess
import time

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    import requests
except ImportError as e:
    print("❌ Missing required Python packages!")
    print("📦 Please install required packages:")
    print("   pip3 install google-auth-oauthlib requests")
    print(f"   Missing: {e}")
    exit(1)

def check_credentials():
    """Check if Google credentials file exists"""
    if not os.path.exists('credentials.json'):
        print("❌ credentials.json not found!")
        print("📋 Please download Google OAuth credentials and save as 'credentials.json'")
        return False
    return True

def check_services_running():
    """Check if required services are running"""
    services = [
        'fogis-calendar-phonebook-sync',
        'google-drive-service'
    ]
    
    for service in services:
        try:
            result = subprocess.run(['docker', 'ps', '--filter', f'name={service}', '--format', '{{.Names}}'], 
                                  capture_output=True, text=True, check=True)
            if service not in result.stdout:
                print(f"❌ Service {service} is not running!")
                print("🚀 Please start services first: docker-compose -f docker-compose-master.yml up -d")
                return False
        except subprocess.CalledProcessError:
            print("❌ Docker is not available or services are not running")
            return False
    
    return True

def authenticate_services():
    """Perform unified authentication for all services"""
    print("🔐 FOGIS SERVICES AUTHENTICATION")
    print("=" * 40)
    
    # All scopes needed
    scopes = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/contacts',
        'https://www.googleapis.com/auth/drive'
    ]
    
    try:
        print("🔄 Starting authentication flow...")
        
        # Create flow
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scopes)
        flow.redirect_uri = 'http://localhost:8080/callback'
        
        # Generate auth URL
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        print("\n🔗 AUTHENTICATION URL:")
        print(auth_url)
        print("\n📋 INSTRUCTIONS:")
        print("1. Copy the URL above and open it in your browser")
        print("2. Sign in to Google and grant permissions for:")
        print("   - Google Calendar (for match scheduling)")
        print("   - Google Contacts (for referee phonebook)")
        print("   - Google Drive (for WhatsApp assets)")
        print("3. Copy the ENTIRE callback URL from your browser")
        print("4. Paste it below and press Enter")
        print()
        
        # Get callback URL from user
        callback_url = input("📥 Paste the callback URL here: ").strip()
        
        if not callback_url.startswith('http://localhost:8080/callback'):
            print("❌ Invalid callback URL. Please try again.")
            return False
        
        print("\n🔄 Exchanging authorization code for tokens...")
        
        # Complete the flow
        flow.fetch_token(authorization_response=callback_url)
        credentials = flow.credentials
        
        print("💾 Saving tokens to services...")
        
        # Save token data
        token_data = credentials.to_json()
        
        # Save local copy
        with open('token.json', 'w') as f:
            f.write(token_data)
        
        # Copy to calendar/contacts service
        print("📅 Updating calendar/contacts service...")
        subprocess.run(['docker', 'cp', 'token.json', 
                       'fogis-calendar-phonebook-sync:/app/token.json'], check=True)
        
        # Copy to Google Drive service (different path)
        print("☁️  Updating Google Drive service...")
        subprocess.run(['docker', 'cp', 'token.json', 
                       'google-drive-service:/app/data/google-drive-token.json'], check=True)
        
        print("🔄 Restarting services to pick up new tokens...")
        
        # Restart services to pick up new tokens
        subprocess.run(['docker', 'restart', 'fogis-calendar-phonebook-sync'], check=True)
        subprocess.run(['docker', 'restart', 'google-drive-service'], check=True)
        
        # Wait for services to restart
        print("⏳ Waiting for services to restart...")
        time.sleep(15)
        
        print("\n✅ AUTHENTICATION COMPLETE!")
        print("✅ Calendar/Contacts service authenticated")
        print("✅ Google Drive service authenticated")
        print("✅ Services restarted successfully")
        print(f"✅ Token expires: {credentials.expiry}")
        print(f"✅ Has refresh token: {bool(credentials.refresh_token)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False

def verify_authentication():
    """Verify that all services are properly authenticated"""
    print("\n🔍 Verifying service authentication...")
    
    services = [
        ('Calendar/Contacts', 'fogis-calendar-phonebook-sync', 9083),
        ('Google Drive', 'google-drive-service', 9085),
        ('Avatar Service', 'team-logo-combiner', 9088),
    ]
    
    all_healthy = True
    
    for service_name, container_name, port in services:
        print(f"🔍 Checking {service_name}...")
        
        try:
            response = requests.get(f'http://localhost:{port}/health', timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'auth_status' in data:
                    if data['auth_status'] == 'authenticated':
                        print(f"✅ {service_name}: Authenticated")
                    else:
                        print(f"❌ {service_name}: Not authenticated")
                        all_healthy = False
                else:
                    print(f"✅ {service_name}: Healthy")
            else:
                print(f"❌ {service_name}: Health check failed")
                all_healthy = False
        except Exception as e:
            print(f"❌ {service_name}: Connection failed - {e}")
            all_healthy = False
    
    return all_healthy

def main():
    """Main authentication flow"""
    print("🚀 FOGIS UNIFIED AUTHENTICATION")
    print("=" * 50)
    
    # Check prerequisites
    if not check_credentials():
        return 1
    
    if not check_services_running():
        return 1
    
    # Perform authentication
    if not authenticate_services():
        return 1
    
    # Verify authentication
    if verify_authentication():
        print("\n🎉 ALL SERVICES SUCCESSFULLY AUTHENTICATED!")
        print("\n📋 SYSTEM STATUS:")
        print("✅ Google Calendar sync ready")
        print("✅ Google Contacts sync ready") 
        print("✅ Google Drive uploads ready")
        print("✅ WhatsApp avatar creation ready")
        print("\n🔄 The system will now automatically:")
        print("- Check for new matches every hour")
        print("- Create WhatsApp group assets")
        print("- Sync matches to Google Calendar")
        print("- Upload assets to Google Drive")
        print("\n🎯 Your FOGIS system is fully operational!")
    else:
        print("\n⚠️  Some services may not be fully authenticated.")
        print("Please check the service logs for more details.")
        return 1
    
    return 0

if __name__ == "__main__":
    # Set environment variable for localhost OAuth
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    exit(main())
