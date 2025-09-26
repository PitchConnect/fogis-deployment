# Enhanced Schema v2.0 Integration for match-list-processor
# File: src/app_integration_enhanced.py

"""
Integration module for Enhanced Schema v2.0 with existing match-list-processor workflow.

This module provides seamless integration of Enhanced Schema v2.0 publishing
with the existing match processing logic, ensuring backward compatibility
while enabling new features like Organization ID mapping and complete contact data.
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional

# Import Enhanced Schema v2.0 components
try:
    from redis_integration import (
        EnhancedSchemaV2Formatter,
        get_enhanced_redis_publisher,
    )

    ENHANCED_REDIS_AVAILABLE = True
except ImportError:
    ENHANCED_REDIS_AVAILABLE = False
    logging.warning("⚠️ Enhanced Redis integration not available - using fallback")

logger = logging.getLogger(__name__)


class EnhancedMatchProcessingIntegration:
    """
    Enhanced integration class for match processing with Schema v2.0 support.

    Features:
    - Seamless integration with existing match processing workflow
    - Multi-version publishing (v1.0 and v2.0)
    - Organization ID mapping for logo service integration
    - Complete contact data for calendar sync
    - Graceful fallback to existing HTTP notifications
    """

    def __init__(self):
        self.enhanced_redis_enabled = (
            ENHANCED_REDIS_AVAILABLE
            and os.getenv("REDIS_ENABLED", "false").lower() == "true"
            and os.getenv("REDIS_SCHEMA_VERSION", "2.0") == "2.0"
        )

        self.publisher = None
        if self.enhanced_redis_enabled:
            try:
                self.publisher = get_enhanced_redis_publisher()
                logger.info("✅ Enhanced Schema v2.0 integration initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Enhanced Redis publisher: {e}")
                self.enhanced_redis_enabled = False

    def process_matches_with_enhanced_publishing(
        self,
        matches_data: List[Dict],
        changes_summary: Any = None,
        existing_http_callback: Optional[Callable] = None,
    ) -> bool:
        """
        Process matches and publish with Enhanced Schema v2.0.

        Args:
            matches_data: List of processed match objects
            changes_summary: Change detection results
            existing_http_callback: Existing HTTP notification function for fallback

        Returns:
            bool: True if publishing succeeded (Redis or HTTP fallback)
        """
        try:
            # Prepare metadata for Enhanced Schema v2.0
            metadata = {
                "processor_version": "2.1.0",
                "schema_version": "2.0",
                "logo_service_compatible": True,
                "contact_data_included": True,
                "integration_method": "enhanced_app_integration",
            }

            # Log processing details
            self._log_processing_details(matches_data, changes_summary)

            # Try Enhanced Schema v2.0 publishing first
            if self.enhanced_redis_enabled and self.publisher:
                redis_success = self.publisher.handle_match_processing_complete(
                    matches=matches_data,
                    changes_summary=changes_summary,
                    metadata=metadata,
                )

                if redis_success:
                    logger.info("✅ Enhanced Schema v2.0 publishing successful")
                    return True
                else:
                    logger.warning(
                        "⚠️ Enhanced Schema v2.0 publishing failed - trying fallback"
                    )

            # Fallback to existing HTTP notification
            if existing_http_callback:
                try:
                    http_success = existing_http_callback(matches_data, changes_summary)
                    if http_success:
                        logger.info("✅ HTTP fallback notification successful")
                        return True
                    else:
                        logger.warning("⚠️ HTTP fallback notification failed")
                except Exception as e:
                    logger.error(f"❌ HTTP fallback failed: {e}")

            # If both Redis and HTTP failed
            logger.error("❌ All notification methods failed")
            return False

        except Exception as e:
            logger.error(f"❌ Enhanced match processing failed: {e}")
            return False

    def validate_organization_id_mapping(
        self, matches_data: List[Dict]
    ) -> Dict[str, Any]:
        """
        Validate Organization ID mapping for logo service integration.

        Args:
            matches_data: List of match objects

        Returns:
            dict: Validation results with statistics
        """
        validation_results = {
            "total_matches": len(matches_data),
            "matches_with_home_org_id": 0,
            "matches_with_away_org_id": 0,
            "matches_with_both_org_ids": 0,
            "logo_service_compatible": 0,
            "compatibility_rate": 0.0,
            "validation_passed": False,
        }

        try:
            for match in matches_data:
                home_org_id = match.get("lag1foreningid")
                away_org_id = match.get("lag2foreningid")

                if home_org_id:
                    validation_results["matches_with_home_org_id"] += 1
                if away_org_id:
                    validation_results["matches_with_away_org_id"] += 1
                if home_org_id and away_org_id:
                    validation_results["matches_with_both_org_ids"] += 1
                    validation_results["logo_service_compatible"] += 1

            # Consider validation passed if at least 80% of matches have Org IDs
            total_matches = validation_results["total_matches"]
            compatible_matches = validation_results["logo_service_compatible"]

            if total_matches > 0:
                compatibility_rate = float(compatible_matches) / total_matches
                validation_results["compatibility_rate"] = compatibility_rate
                validation_results["validation_passed"] = compatibility_rate >= 0.8

            logger.info(
                f"📊 Organization ID Validation: "
                f"{compatible_matches}/{total_matches} matches compatible"
            )

        except Exception as e:
            logger.error(f"❌ Organization ID validation failed: {e}")

        return validation_results

    def generate_enhanced_schema_sample(
        self, matches_data: List[Dict]
    ) -> Optional[str]:
        """
        Generate a sample Enhanced Schema v2.0 message for testing.

        Args:
            matches_data: List of match objects

        Returns:
            str: Sample Enhanced Schema v2.0 JSON message
        """
        try:
            if not matches_data:
                return None

            # Use first match as sample
            sample_matches = matches_data[:1]

            formatter = EnhancedSchemaV2Formatter()
            sample_message = formatter.format_match_updates_v2(
                matches=sample_matches,
                changes_summary=None,
                metadata={
                    "sample_generation": True,
                    "timestamp": "2025-09-26T10:30:00Z",
                },
            )

            logger.info("✅ Enhanced Schema v2.0 sample generated")
            return sample_message

        except Exception as e:
            logger.error(f"❌ Failed to generate Enhanced Schema sample: {e}")
            return None

    def _log_processing_details(self, matches_data: List[Dict], changes_summary: Any):
        """Log processing details for operational visibility."""
        try:
            total_matches = len(matches_data)
            has_changes = bool(changes_summary)

            # Validate Organization ID mapping
            validation_results = self.validate_organization_id_mapping(matches_data)

            logger.info("📊 Enhanced Processing Details:")
            logger.info(f"   Total matches: {total_matches}")
            compatible_count = validation_results["logo_service_compatible"]
            logger.info(f"   Logo service compatible: {compatible_count}")
            rate = validation_results.get("compatibility_rate", 0)
            logger.info(f"   Compatibility rate: {rate:.1%}")
            logger.info(f"   Has changes: {has_changes}")
            logger.info(f"   Enhanced Redis enabled: {self.enhanced_redis_enabled}")

        except Exception as e:
            logger.warning(f"⚠️ Failed to log processing details: {e}")


# Global instance for easy access
_enhanced_integration = None


def get_enhanced_integration() -> EnhancedMatchProcessingIntegration:
    """Get global Enhanced integration instance."""
    global _enhanced_integration
    if _enhanced_integration is None:
        _enhanced_integration = EnhancedMatchProcessingIntegration()
    return _enhanced_integration


def process_matches_with_enhanced_schema(
    matches_data: List[Dict],
    changes_summary: Any = None,
    existing_http_callback: Optional[Callable] = None,
) -> bool:
    """
    Helper function to process matches with Enhanced Schema v2.0.

    Args:
        matches_data: List of match objects
        changes_summary: Change detection results
        existing_http_callback: Existing HTTP notification function

    Returns:
        bool: True if processing and publishing succeeded
    """
    integration = get_enhanced_integration()
    return integration.process_matches_with_enhanced_publishing(
        matches_data, changes_summary, existing_http_callback
    )


def validate_enhanced_schema_compatibility(matches_data: List[Dict]) -> bool:
    """
    Validate if matches are compatible with Enhanced Schema v2.0.

    Args:
        matches_data: List of match objects

    Returns:
        bool: True if matches are compatible with Enhanced Schema v2.0
    """
    integration = get_enhanced_integration()
    validation_results = integration.validate_organization_id_mapping(matches_data)
    return validation_results.get("validation_passed", False)


# Example integration with existing match processing workflow
def enhanced_match_processing_example():
    """
    Example of how to integrate Enhanced Schema v2.0 with existing workflow.
    """
    # This would be called from the existing match processing logic

    # 1. Process matches (existing logic)
    matches_data = []  # This would come from existing processing
    changes_summary = None  # This would come from existing change detection

    # 2. Define existing HTTP callback (existing logic)
    def existing_http_notification(matches, changes):
        # Existing HTTP notification logic
        return True

    # 3. Process with Enhanced Schema v2.0
    success = process_matches_with_enhanced_schema(
        matches_data=matches_data,
        changes_summary=changes_summary,
        existing_http_callback=existing_http_notification,
    )

    if success:
        logger.info("✅ Enhanced match processing completed successfully")
    else:
        logger.error("❌ Enhanced match processing failed")

    return success
