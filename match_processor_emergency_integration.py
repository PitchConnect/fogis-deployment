"""
Emergency Integration: Direct Calendar Service Notification

This module adds direct HTTP communication to the calendar service emergency endpoint,
bypassing the failing FOGIS OAuth authentication in the calendar service.

Author: System Architecture Team
Date: 2025-09-19
Issue: #100 - OAuth authentication failures blocking calendar sync
"""

import json
import logging
import requests
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class EmergencyCalendarNotifier:
    """
    Handles direct communication with calendar service emergency endpoint.
    """
    
    def __init__(self, calendar_service_url: str, timeout: int = 30, max_retries: int = 3):
        """
        Initialize emergency calendar notifier.
        
        Args:
            calendar_service_url: Base URL of calendar service
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.calendar_service_url = calendar_service_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.emergency_endpoint = f"{self.calendar_service_url}/sync-with-data"
        self.status_endpoint = f"{self.calendar_service_url}/emergency-status"
        
    def check_emergency_endpoint_availability(self) -> bool:
        """
        Check if emergency endpoint is available.
        
        Returns:
            bool: True if endpoint is available, False otherwise
        """
        try:
            response = requests.get(
                self.status_endpoint,
                timeout=10,
                headers={'User-Agent': 'match-list-processor/emergency-client'}
            )
            
            if response.status_code == 200:
                status_data = response.json()
                available = status_data.get('status') == 'available'
                logger.info(f"Emergency endpoint status: {'available' if available else 'unavailable'}")
                return available
            else:
                logger.warning(f"Emergency endpoint status check failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to check emergency endpoint availability: {e}")
            return False
    
    def notify_calendar_service(self, matches: List[Dict], metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Send match data directly to calendar service emergency endpoint.
        
        Args:
            matches: List of match dictionaries
            metadata: Optional metadata about the notification
            
        Returns:
            Dict containing notification results
        """
        
        # Prepare payload
        payload = {
            'matches': matches,
            'timestamp': datetime.now().isoformat(),
            'source': 'match-list-processor',
            'metadata': metadata or {}
        }
        
        # Add request tracking
        request_id = f"emergency-{int(time.time())}"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'match-list-processor/emergency-client',
            'X-Request-ID': request_id
        }
        
        logger.info(f"Sending emergency notification: {len(matches)} matches (Request ID: {request_id})")
        
        # Attempt notification with retry logic
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Emergency notification attempt {attempt + 1}/{self.max_retries}")
                
                response = requests.post(
                    self.emergency_endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Emergency notification successful: {result.get('events_created', 0)} events created")
                    
                    # Log specific success for target match
                    target_match = next((m for m in matches if m.get('speldatum') == '2025-09-23'), None)
                    if target_match:
                        logger.info(f"✅ Target match notification sent: {target_match.get('lag1namn')} vs {target_match.get('lag2namn')} on 2025-09-23")
                    
                    return {
                        'status': 'success',
                        'attempt': attempt + 1,
                        'request_id': request_id,
                        'calendar_response': result
                    }
                    
                else:
                    error_msg = f"Calendar service returned {response.status_code}: {response.text}"
                    logger.warning(error_msg)
                    last_exception = Exception(error_msg)
                    
            except requests.exceptions.Timeout:
                error_msg = f"Request timeout after {self.timeout}s (attempt {attempt + 1})"
                logger.warning(error_msg)
                last_exception = Exception(error_msg)
                
            except requests.exceptions.ConnectionError as e:
                error_msg = f"Connection error to calendar service (attempt {attempt + 1}): {e}"
                logger.warning(error_msg)
                last_exception = e
                
            except Exception as e:
                error_msg = f"Unexpected error in emergency notification (attempt {attempt + 1}): {e}"
                logger.error(error_msg, exc_info=True)
                last_exception = e
            
            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
        
        # All attempts failed
        error_msg = f"Emergency notification failed after {self.max_retries} attempts"
        logger.error(error_msg)
        
        return {
            'status': 'failed',
            'attempts': self.max_retries,
            'request_id': request_id,
            'last_error': str(last_exception) if last_exception else 'Unknown error'
        }


class EnhancedMatchProcessor:
    """
    Enhanced match processor with emergency calendar notification.
    """
    
    def __init__(self, existing_processor, calendar_service_url: str):
        """
        Initialize enhanced processor.
        
        Args:
            existing_processor: Your existing match processor instance
            calendar_service_url: URL of calendar service
        """
        self.existing_processor = existing_processor
        self.emergency_notifier = EmergencyCalendarNotifier(calendar_service_url)
        self.emergency_enabled = True
        
    def process_matches_with_emergency_notification(self) -> Dict[str, Any]:
        """
        Process matches and send emergency notification to calendar service.
        
        Returns:
            Dict containing processing results
        """
        try:
            # Use existing match processing logic
            logger.info("Starting match processing with emergency calendar notification")
            
            # Get processed matches from existing logic
            matches = self.existing_processor.fetch_and_process_matches()
            
            results = {
                'matches_processed': len(matches),
                'timestamp': datetime.now().isoformat(),
                'emergency_notification': None,
                'legacy_notifications': None
            }
            
            # Emergency notification to calendar service
            if self.emergency_enabled:
                logger.info("Sending emergency notification to calendar service")
                
                # Check endpoint availability first
                if self.emergency_notifier.check_emergency_endpoint_availability():
                    notification_result = self.emergency_notifier.notify_calendar_service(matches)
                    results['emergency_notification'] = notification_result
                    
                    if notification_result['status'] == 'success':
                        logger.info("✅ Emergency calendar notification successful")
                    else:
                        logger.error("❌ Emergency calendar notification failed")
                else:
                    logger.warning("Emergency endpoint not available, skipping notification")
                    results['emergency_notification'] = {'status': 'endpoint_unavailable'}
            
            # Keep existing notifications for other services (WhatsApp, alerts, etc.)
            try:
                legacy_results = self.existing_processor.notify_other_services(matches)
                results['legacy_notifications'] = legacy_results
                logger.info("Legacy service notifications completed")
            except Exception as e:
                logger.error(f"Legacy notifications failed: {e}")
                results['legacy_notifications'] = {'status': 'failed', 'error': str(e)}
            
            return results
            
        except Exception as e:
            logger.error(f"Enhanced match processing failed: {e}", exc_info=True)
            raise


def integrate_emergency_notification(existing_processor, calendar_service_url: str = None):
    """
    Integrate emergency notification into existing match processor.
    
    Args:
        existing_processor: Your existing match processor
        calendar_service_url: URL of calendar service (default: from environment)
    """
    
    # Get calendar service URL from environment or default
    if not calendar_service_url:
        import os
        calendar_service_url = os.getenv(
            'CALENDAR_SERVICE_URL', 
            'http://fogis-calendar-phonebook-sync:9083'
        )
    
    # Create enhanced processor
    enhanced_processor = EnhancedMatchProcessor(existing_processor, calendar_service_url)
    
    # Replace main processing function
    def emergency_main_loop():
        """Main processing loop with emergency notification."""
        try:
            results = enhanced_processor.process_matches_with_emergency_notification()
            
            # Log summary
            logger.info("=== Processing Summary ===")
            logger.info(f"Matches processed: {results['matches_processed']}")
            
            emergency_status = results.get('emergency_notification', {}).get('status', 'not_attempted')
            logger.info(f"Emergency calendar notification: {emergency_status}")
            
            legacy_status = results.get('legacy_notifications', {}).get('status', 'not_attempted')
            logger.info(f"Legacy notifications: {legacy_status}")
            
            return results
            
        except Exception as e:
            logger.error(f"Emergency main loop failed: {e}", exc_info=True)
            raise
    
    return emergency_main_loop


# Example integration for existing match-list-processor
def example_integration():
    """
    Example of how to integrate emergency notification into existing processor.
    """
    
    # Your existing processor class/instance
    # existing_processor = YourExistingMatchProcessor()
    
    # Integrate emergency notification
    # emergency_main = integrate_emergency_notification(
    #     existing_processor,
    #     calendar_service_url='http://fogis-calendar-phonebook-sync:9083'
    # )
    
    # Replace your main processing call
    # if __name__ == "__main__":
    #     emergency_main()
    
    pass


if __name__ == "__main__":
    # This would be your main execution
    logger.info("Emergency integration module loaded")
    logger.info("Use integrate_emergency_notification() to add emergency calendar notification")
