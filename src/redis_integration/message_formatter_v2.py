# Enhanced Schema v2.0 Implementation for match-list-processor
# File: src/redis_integration/message_formatter_v2.py

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class EnhancedSchemaV2Formatter:
    """
    Enhanced Schema v2.0 formatter with Organization ID mapping for logo service.

    Key Features:
    - Corrected Organization ID mapping for logo service (lag1foreningid/lag2foreningid)
    - Complete contact data structure for calendar sync
    - Detailed change information with categories and priorities
    - Backward compatibility with v1.0 schema
    """

    @staticmethod
    def format_match_updates_v2(
        matches: List[Dict], changes_summary=None, metadata: Optional[Dict] = None
    ) -> str:
        """
        Format match updates using Enhanced Schema v2.0 with Organization ID mapping.

        Args:
            matches: List of FOGIS match objects
            changes_summary: Change detection results with detailed_changes
            metadata: Optional metadata

        Returns:
            JSON string with Enhanced Schema v2.0 structure
        """

        # Process matches with corrected team ID mapping
        processed_matches = []
        for match in matches:
            processed_match = {
                "match_id": match.get("matchid"),
                "match_number": match.get("matchnr"),
                "date": match.get("speldatum"),
                "time": match.get("avsparkstid"),
                "formatted_datetime": match.get("tidsangivelse"),
                # ✅ CORRECTED: Teams with proper logo_id mapping
                "teams": {
                    "home": {
                        "name": match.get("lag1namn"),
                        "id": match.get("lag1lagid"),  # Database reference
                        "logo_id": match.get(
                            "lag1foreningid"
                        ),  # ✅ Organization ID for logo service
                        "organization_id": match.get(
                            "lag1foreningid"
                        ),  # Semantic clarity
                    },
                    "away": {
                        "name": match.get("lag2namn"),
                        "id": match.get("lag2lagid"),  # Database reference
                        "logo_id": match.get(
                            "lag2foreningid"
                        ),  # ✅ Organization ID for logo service
                        "organization_id": match.get(
                            "lag2foreningid"
                        ),  # Semantic clarity
                    },
                },
                # Venue with coordinates
                "venue": {
                    "name": match.get("anlaggningnamn"),
                    "id": match.get("anlaggningid"),
                    "coordinates": {
                        "latitude": match.get("anlaggningLatitud"),
                        "longitude": match.get("anlaggningLongitud"),
                    },
                },
                # Competition context
                "competition": {
                    "name": match.get("tavlingnamn"),
                    "number": match.get("tavlingnr"),
                    "category": match.get("tavlingskategorinamn"),
                    "id": match.get("tavlingid"),
                },
                # Match status
                "status": {
                    "cancelled": match.get("avbruten", False),
                    "postponed": match.get("uppskjuten", False),
                    "suspended": match.get("installd", False),
                    "final_result": match.get("arslutresultat", False),
                    "referee_approved": match.get("matchrapportgodkandavdomare", False),
                },
                # ✅ Referee contacts (Essential for calendar sync)
                "referees": [
                    {
                        "name": ref.get("namn"),
                        "role": ref.get("domarrollnamn"),
                        "role_short": ref.get("domarrollkortnamn"),
                        "id": ref.get("domareid"),
                        "contact": {
                            "mobile": ref.get("mobiltelefon"),
                            "phone": ref.get("telefon") if ref.get("telefon") else None,
                            "email": ref.get("epostadress"),
                            "address": {
                                "street": ref.get("adress"),
                                "postal_code": ref.get("postnr"),
                                "city": ref.get("postort"),
                            },
                        },
                    }
                    for ref in match.get("domaruppdraglista", [])
                ],
                # ✅ Team contacts (Essential for calendar sync)
                "team_contacts": [
                    {
                        "name": contact.get("personnamn"),
                        "team_name": contact.get("lagnamn"),
                        "team_id": contact.get("lagid"),
                        "organization_id": contact.get("foreningId"),
                        "is_reserve": contact.get("reserv", False),
                        "contact": {
                            "mobile": contact.get("mobiltelefon"),
                            "phone": contact.get("telefon")
                            if contact.get("telefon")
                            else None,
                            "work_phone": contact.get("telefonarbete")
                            if contact.get("telefonarbete")
                            else None,
                            "email": contact.get("epostadress"),
                            "address": {
                                "street": contact.get("adress"),
                                "postal_code": contact.get("postnr"),
                                "city": contact.get("postort"),
                            }
                            if contact.get("adress")
                            else None,
                        },
                    }
                    for contact in match.get("kontaktpersoner", [])
                ],
                # Match details URL
                "match_url": f"https://www.svenskfotboll.se/matchfakta/{match.get('matchid')}/",  # noqa: E501
            }
            processed_matches.append(processed_match)

        # Include detailed changes in payload
        detailed_changes = []
        if changes_summary and hasattr(changes_summary, "categorized_changes"):
            if changes_summary.categorized_changes:
                for change in changes_summary.categorized_changes.changes:
                    detailed_changes.append(
                        {
                            "field": change.field_name,
                            "from": change.previous_value,
                            "to": change.current_value,
                            "category": change.category.value,
                            "priority": change.priority.value,
                            "description": change.change_description,
                        }
                    )

        # Create Enhanced Schema v2.0 message
        message = {
            "schema_version": "2.0",
            "schema_type": "enhanced_with_contacts_and_logo_ids",
            "backward_compatible": True,
            "new_fields": [
                "teams.home.logo_id",
                "teams.away.logo_id",
                "team_contacts",
                "referees.contact",
            ],
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source": "match-list-processor",
            "version": "1.0",
            "type": "match_updates",
            "payload": {
                "matches": processed_matches,
                "detailed_changes": detailed_changes,
                "metadata": {
                    "total_matches": len(processed_matches),
                    "has_changes": bool(changes_summary),
                    "change_summary": changes_summary.get("summary", {})
                    if hasattr(changes_summary, "get")
                    else {},
                    "processing_timestamp": datetime.now(timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    **(metadata or {}),
                },
            },
        }

        return json.dumps(message, ensure_ascii=False)

    @staticmethod
    def format_match_updates_v1_legacy(
        matches: List[Dict], changes_summary=None, metadata: Optional[Dict] = None
    ) -> str:
        """
        Legacy v1.0 formatter for backward compatibility.
        Maintains simplified schema for existing subscribers.
        """
        simplified_matches = []
        for match in matches:
            simplified_match = {
                "match_id": match.get("matchid"),
                "teams": f"{match.get('lag1namn', 'N/A')} vs {match.get('lag2namn', 'N/A')}",  # noqa: E501
                "date": match.get("speldatum"),
                "time": match.get("avsparkstid"),
                "venue": match.get("anlaggningnamn"),
                "referees": [
                    ref.get("namn") for ref in match.get("domaruppdraglista", [])
                ],
            }
            simplified_matches.append(simplified_match)

        message = {
            "schema_version": "1.0",
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source": "match-list-processor",
            "type": "match_updates",
            "payload": {
                "matches": simplified_matches,
                "metadata": {
                    "total_matches": len(simplified_matches),
                    "has_changes": bool(changes_summary),
                    "change_summary": "Changes detected"
                    if changes_summary
                    else "No changes",
                    **(metadata or {}),
                },
            },
        }

        return json.dumps(message, ensure_ascii=False)


# Usage example for multi-version publishing
def publish_multi_version_messages(matches, changes, metadata=None):
    """
    Publish both v1.0 and v2.0 messages for backward compatibility.
    """
    formatter = EnhancedSchemaV2Formatter()

    # Publish v2.0 (Enhanced Schema with contacts and logo IDs)
    v2_message = formatter.format_match_updates_v2(matches, changes, metadata)
    publish_to_channel("match_updates_v2", v2_message)
    publish_to_channel("match_updates", v2_message)  # Default to latest

    # Publish v1.0 (Legacy simplified schema)
    v1_message = formatter.format_match_updates_v1_legacy(matches, changes, metadata)
    publish_to_channel("match_updates_v1", v1_message)

    logger.info(
        f"✅ Published multi-version messages: v2.0 and v1.0 for {len(matches)} matches"
    )


def publish_to_channel(channel: str, message: str):
    """
    Placeholder function for Redis publishing.
    This should be implemented by the Redis publisher service.
    """
    # This will be implemented by the actual Redis publisher
    pass
