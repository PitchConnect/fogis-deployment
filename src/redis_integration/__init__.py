# Redis Integration Module for Enhanced Schema v2.0
# File: src/redis_integration/__init__.py

"""
Enhanced Redis Integration for match-list-processor with Schema v2.0 support.

This module provides:
- Enhanced Schema v2.0 message formatting with Organization ID mapping
- Multi-version publishing (v1.0 and v2.0) for backward compatibility
- Complete contact data structure for calendar sync integration
- Logo service integration with corrected Organization IDs
- Graceful fallback and error handling

Key Features:
- Organization ID mapping: Uses lag1foreningid/lag2foreningid for logo service
- Contact data: Full referee and team contact information
- Change detection: Detailed field-level changes with categories and priorities
- Multi-channel publishing: Supports multiple Redis channels for schemas
"""

from .enhanced_publisher import (
    EnhancedRedisPublisher,
    get_enhanced_redis_publisher,
    publish_enhanced_match_updates,
)
from .message_formatter_v2 import (
    EnhancedSchemaV2Formatter,
    publish_multi_version_messages,
)

__version__ = "2.0.0"
__author__ = "FOGIS Development Team"

# Export main classes and functions
__all__ = [
    "EnhancedSchemaV2Formatter",
    "EnhancedRedisPublisher",
    "get_enhanced_redis_publisher",
    "publish_enhanced_match_updates",
    "publish_multi_version_messages",
]


def create_enhanced_redis_service(redis_client=None, enabled: bool = True):
    """
    Factory function to create Enhanced Redis service with Schema v2.0 support.

    Args:
        redis_client: Optional Redis client instance
        enabled: Whether Redis publishing is enabled

    Returns:
        EnhancedRedisPublisher: Configured publisher instance
    """
    return EnhancedRedisPublisher(redis_client=redis_client, enabled=enabled)


def format_enhanced_message(matches, changes_summary=None, metadata=None):
    """
    Helper function to format Enhanced Schema v2.0 message.

    Args:
        matches: List of match objects
        changes_summary: Change detection results
        metadata: Optional metadata

    Returns:
        str: JSON formatted Enhanced Schema v2.0 message
    """
    formatter = EnhancedSchemaV2Formatter()
    return formatter.format_match_updates_v2(matches, changes_summary, metadata)


def format_legacy_message(matches, changes_summary=None, metadata=None):
    """
    Helper function to format Legacy Schema v1.0 message.

    Args:
        matches: List of match objects
        changes_summary: Change detection results
        metadata: Optional metadata

    Returns:
        str: JSON formatted Legacy Schema v1.0 message
    """
    formatter = EnhancedSchemaV2Formatter()
    return formatter.format_match_updates_v1_legacy(matches, changes_summary, metadata)


# Integration example for existing match processing workflow
def integrate_with_match_processing(process_matches_function):
    """
    Decorator to integrate Enhanced Schema v2.0 with existing processing.

    Usage:
        @integrate_with_match_processing
        def process_matches():
            # Existing match processing logic
            return matches, changes_summary
    """

    def wrapper(*args, **kwargs):
        # Call original function
        result = process_matches_function(*args, **kwargs)

        # Extract matches and changes from result
        if isinstance(result, tuple) and len(result) >= 2:
            matches, changes_summary = result[0], result[1]

            # Publish Enhanced Schema v2.0
            success = publish_enhanced_match_updates(
                matches=matches,
                changes_summary=changes_summary,
                metadata={
                    "integration_method": "decorator",
                    "function_name": process_matches_function.__name__,
                },
            )

            if success:
                print("✅ Enhanced Schema v2.0 publishing completed")
            else:
                print("⚠️ Enhanced Schema v2.0 publishing failed - fallback")

        return result

    return wrapper
