"""
Credential Validator

Validates and tests all types of credentials used in the FOGIS system.
Provides comprehensive validation for Google OAuth, FOGIS authentication,
and calendar configurations.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from lib.google_oauth_manager import GoogleOAuthManager
from lib.calendar_manager import CalendarManager
from lib.fogis_auth_manager import FogisAuthManager


class CredentialValidator:
    """
    Validates and tests credentials for all FOGIS services.
    
    This class provides functionality for:
    - Google OAuth credential validation
    - FOGIS authentication testing
    - Calendar access verification
    - Integration testing
    - Health checks
    """

    def __init__(self):
        """Initialize the credential validator."""
        self.logger = logging.getLogger(__name__)
        self.validation_results = {}

    def validate_google_credentials(self, credentials_file: str = 'credentials.json') -> Dict[str, Any]:
        """
        Validate Google OAuth credentials file and test authentication.
        
        Args:
            credentials_file: Path to Google credentials JSON file
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'valid': False,
            'file_exists': False,
            'format_valid': False,
            'oauth_successful': False,
            'api_access': {},
            'token_info': {},
            'error': None
        }
        
        try:
            # Initialize OAuth manager
            oauth_manager = GoogleOAuthManager(credentials_file)
            
            # Validate credentials file
            result['file_exists'] = True
            if not oauth_manager.validate_credentials_file():
                result['error'] = "Invalid credentials file format"
                return result
            
            result['format_valid'] = True
            
            # Test OAuth flow (try existing token first)
            credentials = oauth_manager.get_credentials()
            if credentials:
                result['oauth_successful'] = True
                result['token_info'] = oauth_manager.get_token_info()
                
                # Test API access
                api_results = oauth_manager.test_credentials()
                result['api_access'] = api_results
                
                # Check if all required APIs are accessible
                required_apis = ['calendar', 'drive', 'contacts']
                all_apis_working = all(api_results.get(api, False) for api in required_apis)
                
                if all_apis_working:
                    result['valid'] = True
                    self.logger.info("Google credentials validation successful")
                else:
                    failed_apis = [api for api in required_apis if not api_results.get(api, False)]
                    result['error'] = f"API access failed for: {', '.join(failed_apis)}"
            else:
                result['error'] = "OAuth authentication failed"
            
        except Exception as e:
            result['error'] = f"Validation error: {str(e)}"
            self.logger.error(f"Google credentials validation failed: {e}")
        
        self.validation_results['google_oauth'] = result
        return result

    def validate_fogis_credentials(self, username: str, password: str) -> Dict[str, Any]:
        """
        Validate FOGIS authentication credentials.
        
        Args:
            username: FOGIS username
            password: FOGIS password
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'valid': False,
            'connection_successful': False,
            'authentication_successful': False,
            'referee_info': {},
            'session_valid': False,
            'error': None
        }
        
        try:
            # Initialize FOGIS auth manager
            fogis_manager = FogisAuthManager()
            
            # Test connection
            if not fogis_manager.test_connection():
                result['error'] = "Cannot connect to FOGIS website"
                return result
            
            result['connection_successful'] = True
            
            # Test authentication
            auth_result = fogis_manager.authenticate(username, password)
            
            if auth_result['success']:
                result['authentication_successful'] = True
                result['referee_info'] = auth_result['referee_info']
                result['session_valid'] = auth_result['session_valid']
                result['valid'] = True
                
                self.logger.info(f"FOGIS credentials validation successful for user: {username}")
            else:
                result['error'] = auth_result.get('error', 'Authentication failed')
                self.logger.error(f"FOGIS authentication failed for user: {username}")
            
        except Exception as e:
            result['error'] = f"Validation error: {str(e)}"
            self.logger.error(f"FOGIS credentials validation failed: {e}")
        
        self.validation_results['fogis_auth'] = result
        return result

    def validate_calendar_setup(self, calendar_id: str, credentials_file: str = 'credentials.json') -> Dict[str, Any]:
        """
        Validate calendar setup and access permissions.
        
        Args:
            calendar_id: Google Calendar ID to validate
            credentials_file: Path to Google credentials file
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'valid': False,
            'calendar_exists': False,
            'calendar_accessible': False,
            'read_permission': False,
            'write_permission': False,
            'calendar_info': {},
            'test_event_created': False,
            'error': None
        }
        
        try:
            # Get OAuth credentials
            oauth_manager = GoogleOAuthManager(credentials_file)
            credentials = oauth_manager.get_credentials()
            
            if not credentials:
                result['error'] = "No valid Google credentials available"
                return result
            
            # Initialize calendar manager
            calendar_manager = CalendarManager(credentials)
            
            # Validate calendar access
            validation_result = calendar_manager.validate_calendar_access(calendar_id)
            
            result['calendar_exists'] = validation_result['exists']
            result['calendar_accessible'] = validation_result['readable']
            result['read_permission'] = validation_result['readable']
            result['write_permission'] = validation_result['writable']
            result['calendar_info'] = validation_result['calendar_info']
            
            if validation_result['valid']:
                result['valid'] = True
                
                # Try to create a test event
                test_event_id = calendar_manager.create_test_event(calendar_id)
                if test_event_id:
                    result['test_event_created'] = True
                    self.logger.info(f"Calendar validation successful for: {calendar_id}")
                else:
                    result['error'] = "Could not create test event"
            else:
                result['error'] = validation_result.get('error', 'Calendar validation failed')
            
        except Exception as e:
            result['error'] = f"Validation error: {str(e)}"
            self.logger.error(f"Calendar validation failed: {e}")
        
        self.validation_results['calendar_setup'] = result
        return result

    def validate_integration_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive integration health check.
        
        Returns:
            Dictionary with overall health status
        """
        result = {
            'healthy': False,
            'components': {},
            'overall_score': 0,
            'issues': [],
            'recommendations': []
        }
        
        try:
            # Check each component
            components = ['google_oauth', 'fogis_auth', 'calendar_setup']
            healthy_components = 0
            
            for component in components:
                if component in self.validation_results:
                    component_result = self.validation_results[component]
                    result['components'][component] = {
                        'status': 'healthy' if component_result.get('valid', False) else 'unhealthy',
                        'last_checked': datetime.now().isoformat(),
                        'error': component_result.get('error')
                    }
                    
                    if component_result.get('valid', False):
                        healthy_components += 1
                    else:
                        result['issues'].append(f"{component}: {component_result.get('error', 'Unknown error')}")
                else:
                    result['components'][component] = {
                        'status': 'not_tested',
                        'last_checked': None,
                        'error': 'Component not tested'
                    }
                    result['issues'].append(f"{component}: Not tested")
            
            # Calculate overall score
            result['overall_score'] = (healthy_components / len(components)) * 100
            
            # Determine overall health
            result['healthy'] = result['overall_score'] >= 100  # All components must be healthy
            
            # Generate recommendations
            if result['overall_score'] < 100:
                result['recommendations'].append("Run credential setup wizard to fix issues")
                
                if 'google_oauth' in result['issues']:
                    result['recommendations'].append("Check Google Cloud Console configuration")
                
                if 'fogis_auth' in result['issues']:
                    result['recommendations'].append("Verify FOGIS username and password")
                
                if 'calendar_setup' in result['issues']:
                    result['recommendations'].append("Check calendar permissions and access")
            
            self.logger.info(f"Integration health check completed - Score: {result['overall_score']}%")
            
        except Exception as e:
            result['error'] = f"Health check error: {str(e)}"
            self.logger.error(f"Integration health check failed: {e}")
        
        return result

    def run_comprehensive_validation(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run comprehensive validation of all credentials and configurations.
        
        Args:
            config: Configuration dictionary with all credential information
            
        Returns:
            Dictionary with comprehensive validation results
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'overall_valid': False,
            'validations': {},
            'summary': {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0
            }
        }
        
        try:
            # Validate Google OAuth
            if 'google_credentials' in config:
                google_result = self.validate_google_credentials(config['google_credentials'])
                results['validations']['google_oauth'] = google_result
                results['summary']['total_tests'] += 1
                if google_result['valid']:
                    results['summary']['passed_tests'] += 1
                else:
                    results['summary']['failed_tests'] += 1
            
            # Validate FOGIS authentication
            if 'fogis_username' in config and 'fogis_password' in config:
                fogis_result = self.validate_fogis_credentials(
                    config['fogis_username'], 
                    config['fogis_password']
                )
                results['validations']['fogis_auth'] = fogis_result
                results['summary']['total_tests'] += 1
                if fogis_result['valid']:
                    results['summary']['passed_tests'] += 1
                else:
                    results['summary']['failed_tests'] += 1
            
            # Validate calendar setup
            if 'calendar_id' in config:
                calendar_result = self.validate_calendar_setup(
                    config['calendar_id'],
                    config.get('google_credentials', 'credentials.json')
                )
                results['validations']['calendar_setup'] = calendar_result
                results['summary']['total_tests'] += 1
                if calendar_result['valid']:
                    results['summary']['passed_tests'] += 1
                else:
                    results['summary']['failed_tests'] += 1
            
            # Run integration health check
            health_result = self.validate_integration_health()
            results['validations']['integration_health'] = health_result
            
            # Determine overall validity
            results['overall_valid'] = results['summary']['failed_tests'] == 0
            
            self.logger.info(f"Comprehensive validation completed - {results['summary']['passed_tests']}/{results['summary']['total_tests']} tests passed")
            
        except Exception as e:
            results['error'] = f"Comprehensive validation error: {str(e)}"
            self.logger.error(f"Comprehensive validation failed: {e}")
        
        return results

    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all validation results.
        
        Returns:
            Dictionary with validation summary
        """
        return {
            'last_updated': datetime.now().isoformat(),
            'results': self.validation_results,
            'component_count': len(self.validation_results),
            'healthy_components': sum(1 for r in self.validation_results.values() if r.get('valid', False))
        }
