# Implement OAuth 2.0 PKCE authentication to replace ASP.NET form login

## 🚨 Critical Issue: FOGIS Authentication Method Changed

### **Problem Description**

The FOGIS API client is experiencing authentication failures with "Bad Rquest" errors because FOGIS has changed their authentication system from ASP.NET form-based login to OAuth 2.0 PKCE flow. The current implementation expects traditional ASP.NET forms with `__VIEWSTATE` tokens, but FOGIS now redirects to OAuth endpoints.

### **Error Evidence**

```
ERROR: Login request failed: 400 Client Error: Bad Rquest for url: https://auth.fogis.se/connect/authorize?client_id=fogis.mobildomarklient&redirect_uri=https%3A%2F%2Ffogis.svenskfotboll.se%2Fmdk%2Fsignin-oidc&response_type=code&scope=openid%20fogis%20profile%20anvandare%20personid%20offline_access&code_challenge=...&code_challenge_method=S256&state=...&nonce=...&x-client-SKU=ID_NET472&x-client-ver=8.13.0.0
```

### **Root Cause Analysis**

**Authentication Flow Investigation:**
1. Client requests: `https://fogis.svenskfotboll.se/mdk/Login.aspx?ReturnUrl=%2fmdk%2f`
2. **Server redirects** (302) to: `https://auth.fogis.se/connect/authorize` (OAuth endpoint)
3. OAuth flow initiated with PKCE parameters
4. OAuth completion returns page without expected `__VIEWSTATE` token
5. ASP.NET form parser fails: `Failed to extract __VIEWSTATE token from login page`

**Technical Details:**
- **Current**: ASP.NET form authentication expecting `__VIEWSTATE` tokens
- **Required**: OAuth 2.0 Authorization Code flow with PKCE
- **OAuth Endpoint**: `https://auth.fogis.se/connect/authorize`
- **Client ID**: `fogis.mobildomarklient`
- **Redirect URI**: `https://fogis.svenskfotboll.se/mdk/signin-oidc`
- **Scopes**: `openid fogis profile anvandare personid offline_access`

## 🎯 Implementation Requirements

### **1. OAuth 2.0 PKCE Flow Implementation**

**Core Components:**
- [ ] OAuth 2.0 Authorization Code flow with PKCE
- [ ] Code challenge generation (`code_challenge`, `code_challenge_method=S256`)
- [ ] State parameter management for CSRF protection
- [ ] Nonce handling for OpenID Connect
- [ ] Token exchange and management
- [ ] Refresh token handling

**Authentication Flow:**
```python
# Replace current ASP.NET flow:
login_url = f"{BASE_URL}/Login.aspx?ReturnUrl=%2fmdk%2f"
# With OAuth 2.0 PKCE flow:
oauth_url = "https://auth.fogis.se/connect/authorize"
```

### **2. Server-Side Redirect Handling**

**Current Issue:**
```python
# Current code expects direct form access
response = session.get(login_url)
soup = BeautifulSoup(response.text, "html.parser")
# Fails because server redirects to OAuth
```

**Required Solution:**
```python
# Handle OAuth redirects properly
response = session.get(login_url, allow_redirects=True)
if "auth.fogis.se" in response.url:
    # Handle OAuth flow
    return handle_oauth_authentication()
```

### **3. Token Management**

**Replace ASP.NET Cookies:**
```python
# Current: ASP.NET session cookies
cookies = {
    "FogisMobilDomarKlient.ASPXAUTH": session.cookies.get("..."),
    "ASP.NET_SessionId": session.cookies.get("...")
}

# Required: OAuth tokens
tokens = {
    "access_token": oauth_response["access_token"],
    "refresh_token": oauth_response["refresh_token"],
    "expires_in": oauth_response["expires_in"],
    "token_type": "Bearer"
}
```

### **4. Backward Compatibility**

- [ ] Maintain existing `CookieDict` interface
- [ ] Support existing session management API
- [ ] Graceful fallback to ASP.NET if OAuth fails
- [ ] Preserve existing error handling patterns

## 🧪 Testing Requirements

### **Unit Tests**
- [ ] OAuth flow initialization
- [ ] PKCE code challenge generation
- [ ] Token exchange handling
- [ ] Error response processing
- [ ] State/nonce validation

### **Integration Tests**
- [ ] Full OAuth flow with FOGIS endpoints
- [ ] Token refresh functionality
- [ ] Session persistence
- [ ] API calls with OAuth tokens

### **Regression Tests**
- [ ] Existing API compatibility
- [ ] Error handling preservation
- [ ] Session management consistency

## 🔧 Technical Implementation Plan

### **Phase 1: OAuth Core Implementation**
1. Create `FogisOAuthManager` class
2. Implement PKCE code challenge generation
3. Handle OAuth authorization URL creation
4. Implement token exchange

### **Phase 2: Integration with Existing Code**
1. Modify `authenticate()` function in `/app/fogis_api_client/internal/auth.py`
2. Update session management in main client
3. Preserve existing API interfaces

### **Phase 3: Testing and Validation**
1. Create comprehensive test suite
2. Test with actual FOGIS OAuth endpoints
3. Validate token refresh functionality

## 📋 Acceptance Criteria

- [ ] ✅ "Bad Rquest" errors resolved
- [ ] ✅ `/matches` endpoint returns data successfully
- [ ] ✅ OAuth 2.0 PKCE flow implemented correctly
- [ ] ✅ Token refresh works automatically
- [ ] ✅ Backward compatibility maintained
- [ ] ✅ All existing tests pass
- [ ] ✅ New OAuth tests pass
- [ ] ✅ Container builds successfully
- [ ] ✅ GHCR deployment works

## 🔗 Related Issues

- FOGIS network functionality not working (deployment repository)
- Authentication failures affecting all FOGIS API operations
- Container image needs OAuth 2.0 support

## 📚 References

- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [PKCE RFC 7636](https://tools.ietf.org/html/rfc7636)
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)

---

**Priority**: 🔥 **CRITICAL** - Blocking all FOGIS functionality
**Estimated Effort**: 2-3 days
**Impact**: Resolves authentication for entire FOGIS ecosystem
