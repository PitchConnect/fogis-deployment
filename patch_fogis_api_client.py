#!/usr/bin/env python3
"""
Patch script to update fogis_api_client.py with OAuth authentication.
"""

import re
import sys

def patch_fogis_api_client():
    """Update the fogis_api_client.py file to use OAuth authentication."""
    
    file_path = '/app/fogis_api_client/fogis_api_client.py'
    
    try:
        # Read the original file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # 1. Add OAuth import after existing imports
        # Find the last import line
        import_lines = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if line.strip().startswith('from ') or line.strip().startswith('import '):
                import_lines.append(i)
        
        if import_lines:
            # Insert OAuth import after the last import
            last_import_line = max(import_lines)
            oauth_import = 'from fogis_api_client.internal.auth import authenticate, FogisAuthenticationError, FogisOAuthAuthenticationError'
            lines.insert(last_import_line + 1, oauth_import)
        
        # 2. Replace the login method
        content = '\n'.join(lines)
        
        # Find the login method
        login_start = content.find('    def login(self) -> CookieDict:')
        if login_start == -1:
            print("❌ Could not find login method")
            return False
        
        # Find the end of the login method (next method at same indentation level)
        lines_after_login = content[login_start:].split('\n')
        method_end_line = 1  # Start after the def line
        
        for i, line in enumerate(lines_after_login[1:], 1):
            # Look for next method or end of class
            if line.strip() and not line.startswith('        ') and not line.startswith('    def login'):
                if line.startswith('    def ') or line.startswith('class ') or line == '':
                    method_end_line = i
                    break
        
        # Calculate absolute positions
        login_end = login_start + len('\n'.join(lines_after_login[:method_end_line]))
        
        # New OAuth-enabled login method
        new_login_method = '''    def login(self) -> CookieDict:
        """
        Logs into the FOGIS API using OAuth 2.0 or ASP.NET authentication.

        Returns:
            CookieDict: The session cookies if login is successful

        Raises:
            FogisLoginError: If login fails
            FogisAPIRequestError: If there is an error during the login request
        """
        # If cookies are already set, return them without logging in again
        if self.cookies:
            self.logger.debug("Already authenticated, using existing cookies")
            return self.cookies

        # If no username/password provided, we can't log in
        if not (self.username and self.password):
            error_msg = "Login failed: No credentials provided and no cookies available"
            self.logger.error(error_msg)
            raise FogisLoginError(error_msg)

        try:
            # Use the OAuth-enabled authentication
            auth_result = authenticate(self.session, self.username, self.password, self.BASE_URL)
            
            # Handle different authentication methods
            if 'oauth_authenticated' in auth_result:
                if auth_result.get('authentication_method') == 'oauth_hybrid':
                    # OAuth hybrid: OAuth login + ASP.NET cookies
                    self.cookies = {k: v for k, v in auth_result.items() 
                                  if not k.startswith('oauth') and not k.startswith('authentication')}
                    self.logger.info("OAuth hybrid authentication successful")
                else:
                    # Pure OAuth (not expected for FOGIS but handle it)
                    self.cookies = {'oauth_access_token': auth_result.get('access_token', '')}
                    self.logger.info("OAuth authentication successful")
            elif 'aspnet_authenticated' in auth_result:
                # Traditional ASP.NET authentication
                self.cookies = {k: v for k, v in auth_result.items() if not k.startswith('aspnet')}
                self.logger.info("ASP.NET authentication successful")
            else:
                # Unknown result format
                self.logger.error("Unknown authentication result format")
                raise FogisLoginError("Authentication completed but result format is unknown")
            
            # Set cookies in session
            for key, value in self.cookies.items():
                self.session.cookies.set(key, value)
            
            self.logger.info(f"Login successful with {len(self.cookies)} cookies")
            return self.cookies
            
        except (FogisAuthenticationError, FogisOAuthAuthenticationError) as e:
            error_msg = f"Login failed: {e}"
            self.logger.error(error_msg)
            raise FogisLoginError(error_msg) from e
        except Exception as e:
            error_msg = f"Login request failed: {e}"
            self.logger.error(error_msg)
            raise FogisAPIRequestError(error_msg) from e

'''
        
        # Replace the old login method with the new one
        updated_content = content[:login_start] + new_login_method + content[login_end:]
        
        # Write the updated content back
        with open(file_path, 'w') as f:
            f.write(updated_content)
        
        print('✅ Successfully updated fogis_api_client.py with OAuth authentication')
        return True
        
    except Exception as e:
        print(f'❌ Error updating fogis_api_client.py: {e}')
        return False

if __name__ == '__main__':
    success = patch_fogis_api_client()
    sys.exit(0 if success else 1)
