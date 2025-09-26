# Enhanced Redis Publisher for Schema v2.0
# File: src/redis_integration/enhanced_publisher.py

import logging
import os
from typing import Dict, List, Optional

import redis  # type: ignore

from .message_formatter_v2 import EnhancedSchemaV2Formatter

logger = logging.getLogger(__name__)


class EnhancedRedisPublisher:
    """
    Enhanced Redis publisher with Schema v2.0 support and multi-version publishing.

    Features:
    - Multi-version publishing (v1.0 and v2.0)
    - Organization ID mapping for logo service integration
    - Complete contact data for calendar sync
    - Graceful fallback and error handling
    """

    def __init__(self, redis_client=None, enabled: bool = True):
        self.enabled = enabled and os.getenv("REDIS_ENABLED", "false").lower() == "true"
        self.redis_client = redis_client
        self.formatter = EnhancedSchemaV2Formatter()

        # Schema version configuration
        self.schema_version = os.getenv("REDIS_SCHEMA_VERSION", "2.0")
        self.publish_legacy = (
            os.getenv("REDIS_PUBLISH_LEGACY", "true").lower() == "true"
        )
        self.publish_v1 = os.getenv("REDIS_PUBLISH_V1", "true").lower() == "true"
        self.publish_v2 = os.getenv("REDIS_PUBLISH_V2", "true").lower() == "true"

        if not self.redis_client and self.enabled:
            self._initialize_redis_client()

    def _initialize_redis_client(self):
        """Initialize Redis client with configuration from environment."""
        try:
            redis_host = os.getenv("REDIS_HOST", "redis")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            redis_db = int(os.getenv("REDIS_DB", "0"))

            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )

            # Test connection
            self.redis_client.ping()
            logger.info(f"✅ Redis client initialized: {redis_host}:{redis_port}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis client: {e}")
            self.enabled = False
            self.redis_client = None

    def handle_match_processing_complete(
        self, matches: List[Dict], changes_summary=None, metadata: Optional[Dict] = None
    ) -> bool:
        """
        Handle match processing completion with Enhanced Schema v2.0 publishing.

        Args:
            matches: List of processed match objects
            changes_summary: Change detection results
            metadata: Optional metadata to include in messages

        Returns:
            bool: True if publishing succeeded, False otherwise
        """
        if not self.enabled or not self.redis_client:
            logger.warning("⚠️ Redis publishing disabled or client unavailable")
            return False

        try:
            # Prepare metadata with Enhanced Schema v2.0 information
            enhanced_metadata = {
                "processor_version": "2.1.0",
                "schema_version": self.schema_version,
                "logo_service_compatible": True,
                "contact_data_included": True,
                **(metadata or {}),
            }

            # Log Enhanced Schema v2.0 message details
            self._log_enhanced_message_details(matches, changes_summary)

            success_count = 0

            # Publish Enhanced Schema v2.0 (primary)
            if self.publish_v2:
                v2_success = self._publish_enhanced_schema_v2(
                    matches, changes_summary, enhanced_metadata
                )
                if v2_success:
                    success_count += 1

            # Publish Legacy Schema v1.0 (backward compatibility)
            if self.publish_legacy or self.publish_v1:
                v1_success = self._publish_legacy_schema_v1(
                    matches, changes_summary, enhanced_metadata
                )
                if v1_success:
                    success_count += 1

            # Consider successful if at least one version was published
            overall_success = success_count > 0

            if overall_success:
                logger.info(
                    f"✅ Enhanced Schema v2.0 completed: {success_count} versions"
                )
            else:
                logger.error("❌ All Enhanced Schema publishing attempts failed")

            return overall_success

        except Exception as e:
            logger.error(f"❌ Enhanced Schema v2.0 publishing failed: {e}")
            return False

    def _publish_enhanced_schema_v2(
        self, matches: List[Dict], changes_summary, metadata: Dict
    ) -> bool:
        """Publish Enhanced Schema v2.0 with Organization ID mapping."""
        try:
            v2_message = self.formatter.format_match_updates_v2(
                matches, changes_summary, metadata
            )

            # Publish to multiple channels for Enhanced Schema v2.0
            channels_published = 0

            # Primary Enhanced Schema v2.0 channel
            if self._publish_to_channel("match_updates_v2", v2_message):
                channels_published += 1
                logger.info("📡 Published to match_updates_v2 (Enhanced Schema v2.0)")

            # Default channel (latest schema)
            if self._publish_to_channel("match_updates", v2_message):
                channels_published += 1
                logger.info(
                    "📡 Published to match_updates (Default - Enhanced Schema v2.0)"
                )

            return channels_published > 0

        except Exception as e:
            logger.error(f"❌ Enhanced Schema v2.0 publishing failed: {e}")
            return False

    def _publish_legacy_schema_v1(
        self, matches: List[Dict], changes_summary, metadata: Dict
    ) -> bool:
        """Publish Legacy Schema v1.0 for backward compatibility."""
        try:
            v1_message = self.formatter.format_match_updates_v1_legacy(
                matches, changes_summary, metadata
            )

            # Publish to legacy channel
            if self._publish_to_channel("match_updates_v1", v1_message):
                logger.info("📡 Published to match_updates_v1 (Legacy Schema v1.0)")
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Legacy Schema v1.0 publishing failed: {e}")
            return False

    def _publish_to_channel(self, channel: str, message: str) -> bool:
        """Publish message to specific Redis channel."""
        try:
            if not self.redis_client:
                return False

            subscribers = self.redis_client.publish(channel, message)
            msg_size = len(message)
            logger.debug(
                f"📡 Published to {channel}: {msg_size} bytes, {subscribers} subs"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Failed to publish to {channel}: {e}")
            return False

    def _log_enhanced_message_details(self, matches: List[Dict], changes_summary):
        """Log Enhanced Schema v2.0 message details for operational visibility."""
        try:
            total_matches = len(matches)
            has_changes = bool(changes_summary)

            # Count matches with Organization IDs for logo service
            matches_with_logo_ids = sum(
                1
                for match in matches
                if match.get("lag1foreningid") and match.get("lag2foreningid")
            )

            # Count matches with contact data
            matches_with_contacts = sum(
                1
                for match in matches
                if match.get("domaruppdraglista") or match.get("kontaktpersoner")
            )

            logger.info("📊 Enhanced Schema v2.0 Message Details:")
            logger.info(f"   Total matches: {total_matches}")
            logger.info(f"   Matches with logo IDs: {matches_with_logo_ids}")
            logger.info(f"   Matches with contacts: {matches_with_contacts}")
            logger.info(f"   Has changes: {has_changes}")
            logger.info(f"   Schema version: {self.schema_version}")

        except Exception as e:
            logger.warning(f"⚠️ Failed to log message details: {e}")


# Global instance for easy access
_enhanced_publisher = None


def get_enhanced_redis_publisher() -> EnhancedRedisPublisher:
    """Get global Enhanced Redis publisher instance."""
    global _enhanced_publisher
    if _enhanced_publisher is None:
        _enhanced_publisher = EnhancedRedisPublisher()
    return _enhanced_publisher


def publish_enhanced_match_updates(
    matches: List[Dict], changes_summary=None, metadata: Optional[Dict] = None
) -> bool:
    """
    Helper function to publish Enhanced Schema v2.0 match updates.

    Args:
        matches: List of match objects
        changes_summary: Change detection results
        metadata: Optional metadata

    Returns:
        bool: True if publishing succeeded
    """
    publisher = get_enhanced_redis_publisher()
    return publisher.handle_match_processing_complete(
        matches, changes_summary, metadata
    )
