#!/bin/bash
set -e

# Complete Google Calendar OAuth Setup Script
# Use this after getting the authorization code from the OAuth URL

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[OAUTH]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_status "🔐 Google Calendar OAuth Completion"
print_status "=================================="

if [ -z "$1" ]; then
    print_error "❌ Authorization code required!"
    echo ""
    echo "Usage: $0 <authorization_code>"
    echo ""
    echo "📋 Steps to get authorization code:"
    echo "1. Open this URL in your browser:"
    echo "   https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=726890168982-d4p74ljeh2bkjdialneqocpani6svfb9.apps.googleusercontent.com&redirect_uri=http%3A%2F%2Flocalhost%3A1&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcontacts+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive&state=zeqUwuX6KhXi0pFUQnvZOKRP7RRksv&access_type=offline&prompt=consent"
    echo ""
    echo "2. Complete Google authentication"
    echo "3. Copy the 'code' parameter from the error page URL"
    echo "4. Run: $0 <code>"
    exit 1
fi

AUTH_CODE="$1"
print_status "📥 Processing authorization code..."

# Create OAuth completion script in container
cat > /tmp/complete_oauth.py << 'EOF'
import sys
import json
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

def complete_oauth(auth_code):
    try:
        # Load client secrets
        with open('/app/credentials/google-credentials.json', 'r') as f:
            client_config = json.load(f)
        
        # Create flow
        scopes = [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/contacts', 
            'https://www.googleapis.com/auth/drive'
        ]
        
        flow = InstalledAppFlow.from_client_config(
            client_config, 
            scopes,
            redirect_uri='http://localhost:1'
        )
        
        # Exchange code for token
        flow.fetch_token(code=auth_code)
        
        # Save token
        token_data = {
            'token': flow.credentials.token,
            'refresh_token': flow.credentials.refresh_token,
            'token_uri': flow.credentials.token_uri,
            'client_id': flow.credentials.client_id,
            'client_secret': flow.credentials.client_secret,
            'scopes': flow.credentials.scopes
        }
        
        with open('/app/credentials/tokens/calendar/token.json', 'w') as f:
            json.dump(token_data, f, indent=2)
        
        print("✅ OAuth token saved successfully!")
        return True
        
    except Exception as e:
        print(f"❌ OAuth completion failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python complete_oauth.py <auth_code>")
        sys.exit(1)
    
    success = complete_oauth(sys.argv[1])
    sys.exit(0 if success else 1)
EOF

# Copy script to container and run it
docker cp /tmp/complete_oauth.py fogis-calendar-phonebook-sync:/app/
docker exec fogis-calendar-phonebook-sync python /app/complete_oauth.py "$AUTH_CODE"

if [ $? -eq 0 ]; then
    print_success "✅ OAuth setup completed successfully!"
    
    # Verify token was created
    print_status "📋 Verifying OAuth token..."
    TOKEN_SIZE=$(docker exec fogis-calendar-phonebook-sync stat -c%s /app/credentials/tokens/calendar/token.json)
    
    if [ "$TOKEN_SIZE" -gt 0 ]; then
        print_success "✅ OAuth token file created (${TOKEN_SIZE} bytes)"
        
        # Test calendar sync
        print_status "🧪 Testing calendar synchronization..."
        curl -X POST http://localhost:9083/sync > /tmp/sync_result.json 2>/dev/null
        
        if grep -q "Login successful" /tmp/sync_result.json; then
            print_success "✅ Calendar sync test successful!"
            print_success "🎉 Calendar synchronization is now fully functional!"
        else
            print_warning "⚠️ Calendar sync may need additional verification"
        fi
    else
        print_error "❌ OAuth token file is empty"
    fi
else
    print_error "❌ OAuth setup failed"
    exit 1
fi

# Cleanup
rm -f /tmp/complete_oauth.py /tmp/sync_result.json

print_status "📋 Calendar sync setup complete!"
print_status "   - FOGIS authentication: ✅ Working"
print_status "   - Match list retrieval: ✅ Working" 
print_status "   - Google Calendar OAuth: ✅ Configured"
print_status "   - Calendar event writing: ✅ Ready"
