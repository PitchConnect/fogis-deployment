#!/usr/bin/env python3
"""
Match-List-Processor Event Integration

This module integrates event publishing into the match-list-processor,
enabling event-driven communication with downstream services.

Author: System Architecture Team
Date: 2025-09-21
Issue: Event-driven architecture for match processing
"""

import json
import logging
import os
import requests
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import our event system
from fogis_event_system import setup_event_system, FOGISEventPublisher

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedMatchProcessor:
    """Enhanced match processor with event-driven architecture."""
    
    def __init__(self, enable_events: bool = True, enable_emergency_fallback: bool = True):
        """Initialize enhanced match processor."""
        self.enable_events = enable_events and os.getenv('EVENT_PUBLISHING_ENABLED', 'false').lower() == 'true'
        self.enable_emergency_fallback = enable_emergency_fallback
        
        # Initialize event system if enabled
        if self.enable_events:
            try:
                redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
                self.publisher, _, self.connection_manager = setup_event_system('match-list-processor', redis_url)
                logger.info("✅ Event publishing system initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize event system: {e}")
                self.enable_events = False
                self.publisher = None
        else:
            self.publisher = None
            logger.info("Event publishing disabled")
        
        # Emergency fallback configuration
        self.calendar_service_url = os.getenv('CALENDAR_SERVICE_URL', 'http://fogis-calendar-phonebook-sync:5003')
        
    def fetch_matches_from_fogis(self) -> List[Dict]:
        """Fetch matches from centralized FOGIS API."""
        try:
            logger.info("📊 Fetching matches from centralized FOGIS API...")
            
            # Use centralized FOGIS API client
            response = requests.get("http://fogis-api-client-service:8080/matches", timeout=30)
            
            if response.status_code == 200:
                matches = response.json()
                logger.info(f"✅ Retrieved {len(matches)} matches from FOGIS API")
                
                # Log target match if present
                target_match = next((m for m in matches if m.get('speldatum') == '2025-09-23'), None)
                if target_match:
                    logger.info(f"🎯 Target match found: {target_match.get('lag1namn')} vs {target_match.get('lag2namn')}")
                
                return matches
            else:
                logger.error(f"❌ Failed to fetch matches: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error fetching matches: {e}")
            return []
    
    def publish_match_events(self, matches: List[Dict]) -> bool:
        """Publish match events to Redis."""
        if not self.enable_events or not self.publisher:
            logger.debug("Event publishing disabled or not available")
            return False
        
        try:
            logger.info("📡 Publishing match events...")
            
            # Prepare metadata
            metadata = {
                'source_service': 'match-list-processor',
                'processing_timestamp': datetime.now().isoformat(),
                'total_matches': len(matches),
                'fogis_api_version': 'centralized-v1'
            }
            
            # Publish match events with change detection
            success = self.publisher.publish_match_events(matches, metadata)
            
            if success:
                logger.info("✅ Match events published successfully")
                return True
            else:
                logger.error("❌ Failed to publish match events")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error publishing match events: {e}")
            return False
    
    def emergency_calendar_notification(self, matches: List[Dict]) -> bool:
        """Send emergency notification to calendar service as fallback."""
        if not self.enable_emergency_fallback:
            logger.debug("Emergency fallback disabled")
            return False
        
        try:
            logger.info("🚨 Sending emergency calendar notification (fallback)...")
            
            # Prepare payload
            payload = {
                'matches': matches,
                'timestamp': datetime.now().isoformat(),
                'source': 'match-list-processor-fallback',
                'metadata': {
                    'fallback_reason': 'event_system_unavailable',
                    'total_matches': len(matches)
                }
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'match-list-processor/event-fallback',
                'X-Fallback-Mode': 'true'
            }
            
            # Send to emergency endpoint
            response = requests.post(
                f"{self.calendar_service_url}/sync-with-data",
                json=payload,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Emergency notification successful: {result.get('events_created', 0)} events created")
                return True
            else:
                logger.error(f"❌ Emergency notification failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Emergency notification error: {e}")
            return False
    
    def process_and_notify(self) -> Dict[str, Any]:
        """Main processing function with event-driven architecture."""
        try:
            logger.info("🔄 Starting enhanced match processing...")
            
            # Fetch matches
            matches = self.fetch_matches_from_fogis()
            
            if not matches:
                logger.warning("⚠️ No matches retrieved from FOGIS API")
                return {
                    'status': 'warning',
                    'matches_processed': 0,
                    'events_published': False,
                    'emergency_sent': False,
                    'message': 'No matches available'
                }
            
            results = {
                'status': 'success',
                'matches_processed': len(matches),
                'events_published': False,
                'emergency_sent': False,
                'timestamp': datetime.now().isoformat()
            }
            
            # Primary: Publish events
            if self.enable_events:
                logger.info("📡 Using event-driven architecture...")
                events_success = self.publish_match_events(matches)
                results['events_published'] = events_success
                
                if events_success:
                    logger.info("✅ Event-driven notification completed")
                else:
                    logger.warning("⚠️ Event publishing failed, trying emergency fallback...")
                    # Fall back to emergency notification
                    emergency_success = self.emergency_calendar_notification(matches)
                    results['emergency_sent'] = emergency_success
            else:
                # Fallback: Emergency notification
                logger.info("🚨 Using emergency fallback (events disabled)...")
                emergency_success = self.emergency_calendar_notification(matches)
                results['emergency_sent'] = emergency_success
            
            # Log summary
            logger.info("=== Processing Summary ===")
            logger.info(f"Matches processed: {results['matches_processed']}")
            logger.info(f"Events published: {results['events_published']}")
            logger.info(f"Emergency sent: {results['emergency_sent']}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Enhanced match processing failed: {e}", exc_info=True)
            return {
                'status': 'error',
                'matches_processed': 0,
                'events_published': False,
                'emergency_sent': False,
                'error': str(e)
            }

def test_event_integration():
    """Test the event integration functionality."""
    try:
        logger.info("🧪 Testing match processor event integration...")
        
        # Initialize processor
        processor = EnhancedMatchProcessor(enable_events=True, enable_emergency_fallback=True)
        
        # Test processing
        results = processor.process_and_notify()
        
        if results['status'] == 'success':
            logger.info("✅ Event integration test successful!")
            return True
        else:
            logger.error(f"❌ Event integration test failed: {results}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Event integration test error: {e}")
        return False

def integrate_with_existing_processor():
    """Integration function for existing match processor."""
    logger.info("🔗 Integrating event system with existing match processor...")
    
    # Create enhanced processor
    processor = EnhancedMatchProcessor()
    
    # Return the main processing function
    return processor.process_and_notify

def main():
    """Main function for standalone execution."""
    logger.info("🚀 Starting Enhanced Match Processor with Event-Driven Architecture")
    
    # Initialize processor
    processor = EnhancedMatchProcessor()
    
    # Run processing
    results = processor.process_and_notify()
    
    if results['status'] == 'success':
        logger.info("🎉 Enhanced match processing completed successfully!")
        
        if results['events_published']:
            logger.info("📡 Match events published to event system")
        elif results['emergency_sent']:
            logger.info("🚨 Emergency notification sent as fallback")
        
        return True
    else:
        logger.error("❌ Enhanced match processing failed")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
