"""
FOGIS Authentication Manager

Handles FOGIS login authentication, session management, and referee information
extraction for the FOGIS system.
"""

import logging
import requests
from typing import Dict, Optional, Any
import re
from urllib.parse import urljoin


class FogisAuthManager:
    """
    Manages FOGIS authentication and session handling.
    
    This class provides functionality for:
    - FOGIS login authentication
    - Session management
    - Referee information extraction
    - Authentication validation
    """

    def __init__(self):
        """Initialize the FOGIS authentication manager."""
        self.session = requests.Session()
        self.base_url = "https://fogis.se"
        self.login_url = urljoin(self.base_url, "/login")
        self.profile_url = urljoin(self.base_url, "/profile")
        self.logger = logging.getLogger(__name__)
        
        # Set up session headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'sv-SE,sv;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

    def test_connection(self) -> bool:
        """
        Test connection to FOGIS website.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            response = self.session.get(self.base_url, timeout=10)
            if response.status_code == 200:
                self.logger.info("Successfully connected to FOGIS")
                return True
            else:
                self.logger.error(f"FOGIS connection failed with status: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error connecting to FOGIS: {e}")
            return False

    def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate with FOGIS using username and password.
        
        Args:
            username: FOGIS username
            password: FOGIS password
            
        Returns:
            Dictionary with authentication result and information
        """
        result = {
            'success': False,
            'authenticated': False,
            'referee_info': {},
            'session_valid': False,
            'error': None
        }
        
        try:
            # First, get the login page to extract any CSRF tokens or form data
            login_page = self.session.get(self.login_url, timeout=10)
            
            if login_page.status_code != 200:
                result['error'] = f"Could not access login page (status: {login_page.status_code})"
                return result
            
            # Extract CSRF token or other required form fields
            csrf_token = self._extract_csrf_token(login_page.text)
            
            # Prepare login data
            login_data = {
                'username': username,
                'password': password
            }
            
            # Add CSRF token if found
            if csrf_token:
                login_data['_token'] = csrf_token
            
            # Perform login
            login_response = self.session.post(
                self.login_url,
                data=login_data,
                timeout=10,
                allow_redirects=True
            )
            
            # Check if login was successful
            if self._is_login_successful(login_response):
                result['success'] = True
                result['authenticated'] = True
                result['session_valid'] = True
                
                # Extract referee information
                referee_info = self._extract_referee_info(login_response.text)
                result['referee_info'] = referee_info
                
                self.logger.info(f"Successfully authenticated user: {username}")
                
            else:
                result['error'] = "Invalid username or password"
                self.logger.error(f"Authentication failed for user: {username}")
            
        except requests.exceptions.Timeout:
            result['error'] = "Connection timeout - FOGIS may be slow or unavailable"
            self.logger.error("FOGIS authentication timeout")
            
        except requests.exceptions.RequestException as e:
            result['error'] = f"Network error during authentication: {str(e)}"
            self.logger.error(f"Network error during FOGIS authentication: {e}")
            
        except Exception as e:
            result['error'] = f"Unexpected error during authentication: {str(e)}"
            self.logger.error(f"Unexpected error during FOGIS authentication: {e}")
        
        return result

    def _extract_csrf_token(self, html_content: str) -> Optional[str]:
        """
        Extract CSRF token from HTML content.
        
        Args:
            html_content: HTML content from login page
            
        Returns:
            CSRF token if found, None otherwise
        """
        # Look for common CSRF token patterns
        patterns = [
            r'<input[^>]*name=["\']_token["\'][^>]*value=["\']([^"\']+)["\']',
            r'<meta[^>]*name=["\']csrf-token["\'][^>]*content=["\']([^"\']+)["\']',
            r'window\.Laravel\.csrfToken\s*=\s*["\']([^"\']+)["\']'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                token = match.group(1)
                self.logger.debug(f"Found CSRF token: {token[:10]}...")
                return token
        
        self.logger.debug("No CSRF token found")
        return None

    def _is_login_successful(self, response: requests.Response) -> bool:
        """
        Check if login was successful based on response.
        
        Args:
            response: Response from login attempt
            
        Returns:
            True if login was successful, False otherwise
        """
        # Check for redirect to dashboard or profile
        if response.url and ('dashboard' in response.url.lower() or 'profile' in response.url.lower()):
            return True
        
        # Check for absence of login form in response
        if 'login' not in response.text.lower() and 'password' not in response.text.lower():
            return True
        
        # Check for success indicators in HTML
        success_indicators = [
            'välkommen',  # Swedish for "welcome"
            'dashboard',
            'logga ut',   # Swedish for "log out"
            'min profil'  # Swedish for "my profile"
        ]
        
        content_lower = response.text.lower()
        for indicator in success_indicators:
            if indicator in content_lower:
                return True
        
        return False

    def _extract_referee_info(self, html_content: str) -> Dict[str, Any]:
        """
        Extract referee information from authenticated page.
        
        Args:
            html_content: HTML content from authenticated page
            
        Returns:
            Dictionary with referee information
        """
        referee_info = {
            'referee_number': None,
            'name': None,
            'email': None,
            'club': None,
            'district': None
        }
        
        try:
            # Look for referee number patterns
            referee_patterns = [
                r'domare[^:]*:\s*(\d+)',  # Swedish for "referee"
                r'referee[^:]*:\s*(\d+)',
                r'nummer[^:]*:\s*(\d+)',  # Swedish for "number"
                r'id[^:]*:\s*(\d+)'
            ]
            
            for pattern in referee_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    referee_info['referee_number'] = match.group(1)
                    break
            
            # Look for name patterns
            name_patterns = [
                r'<h1[^>]*>([^<]+)</h1>',
                r'namn[^:]*:\s*([^<\n]+)',  # Swedish for "name"
                r'name[^:]*:\s*([^<\n]+)'
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    if len(name) > 2 and not name.isdigit():
                        referee_info['name'] = name
                        break
            
            # Look for email patterns
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', html_content)
            if email_match:
                referee_info['email'] = email_match.group(1)
            
            self.logger.info(f"Extracted referee info: {referee_info}")
            
        except Exception as e:
            self.logger.error(f"Error extracting referee info: {e}")
        
        return referee_info

    def validate_session(self) -> bool:
        """
        Validate that the current session is still active.
        
        Returns:
            True if session is valid, False otherwise
        """
        try:
            response = self.session.get(self.profile_url, timeout=10)
            
            # If we get redirected to login, session is invalid
            if 'login' in response.url.lower():
                self.logger.info("Session expired - redirected to login")
                return False
            
            # Check for authenticated content
            if self._is_login_successful(response):
                self.logger.info("Session is valid")
                return True
            else:
                self.logger.info("Session appears to be invalid")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error validating session: {e}")
            return False

    def logout(self) -> bool:
        """
        Logout from FOGIS and clear session.
        
        Returns:
            True if logout was successful, False otherwise
        """
        try:
            # Try to find and use logout URL
            logout_url = urljoin(self.base_url, "/logout")
            response = self.session.get(logout_url, timeout=10)
            
            # Clear session cookies
            self.session.cookies.clear()
            
            self.logger.info("Logged out from FOGIS")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error during logout: {e}")
            return False

    def get_session_info(self) -> Dict[str, Any]:
        """
        Get information about the current session.
        
        Returns:
            Dictionary with session information
        """
        return {
            'has_cookies': len(self.session.cookies) > 0,
            'session_valid': self.validate_session(),
            'base_url': self.base_url
        }
