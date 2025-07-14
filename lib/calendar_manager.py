"""
Google Calendar Manager

Handles Google Calendar operations including calendar creation, listing,
validation, and management for the FOGIS system.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class CalendarManager:
    """
    Manages Google Calendar operations for FOGIS system.

    This class provides functionality for:
    - Listing available calendars
    - Creating dedicated FOGIS calendars
    - Validating calendar access
    - Managing calendar permissions
    """

    def __init__(self, credentials: Credentials):
        """
        Initialize the calendar manager.

        Args:
            credentials: Valid Google OAuth credentials
        """
        self.credentials = credentials
        self.service = build("calendar", "v3", credentials=credentials)
        self.logger = logging.getLogger(__name__)

    def list_calendars(self) -> List[Dict[str, Any]]:
        """
        List all accessible calendars for the authenticated user.

        Returns:
            List of calendar dictionaries with id, summary, and access info
        """
        try:
            calendars_result = self.service.calendarList().list().execute()
            calendars = calendars_result.get("items", [])

            calendar_list = []
            for calendar in calendars:
                calendar_info = {
                    "id": calendar["id"],
                    "summary": calendar["summary"],
                    "description": calendar.get("description", ""),
                    "access_role": calendar.get("accessRole", "unknown"),
                    "primary": calendar.get("primary", False),
                    "selected": calendar.get("selected", False),
                }
                calendar_list.append(calendar_info)

            self.logger.info(f"Found {len(calendar_list)} accessible calendars")
            return calendar_list

        except HttpError as e:
            self.logger.error(f"Error listing calendars: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error listing calendars: {e}")
            return []

    def create_fogis_calendar(
        self, name: str, description: str = None
    ) -> Optional[str]:
        """
        Create a new dedicated FOGIS calendar.

        Args:
            name: Name for the new calendar
            description: Optional description for the calendar

        Returns:
            Calendar ID if creation was successful, None otherwise
        """
        if description is None:
            description = f"Automated FOGIS match scheduling - Created {datetime.now().strftime('%Y-%m-%d')}"

        calendar_body = {
            "summary": name,
            "description": description,
            "timeZone": "Europe/Stockholm",
            "location": "Sweden",
        }

        try:
            created_calendar = (
                self.service.calendars().insert(body=calendar_body).execute()
            )
            calendar_id = created_calendar["id"]

            # Make the calendar visible in the calendar list
            calendar_list_entry = {
                "id": calendar_id,
                "selected": True,
                "colorId": "10",  # Green color for FOGIS calendars
            }

            self.service.calendarList().insert(body=calendar_list_entry).execute()

            self.logger.info(f"Created FOGIS calendar: {name} (ID: {calendar_id})")
            return calendar_id

        except HttpError as e:
            self.logger.error(f"Error creating calendar: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error creating calendar: {e}")
            return None

    def validate_calendar_access(self, calendar_id: str) -> Dict[str, Any]:
        """
        Validate access to a specific calendar and test permissions.

        Args:
            calendar_id: ID of the calendar to validate

        Returns:
            Dictionary with validation results and access information
        """
        result = {
            "valid": False,
            "exists": False,
            "readable": False,
            "writable": False,
            "calendar_info": {},
            "error": None,
        }

        try:
            # Try to get calendar metadata
            calendar = self.service.calendars().get(calendarId=calendar_id).execute()
            result["exists"] = True
            result["readable"] = True
            result["calendar_info"] = {
                "summary": calendar.get("summary", "Unknown"),
                "description": calendar.get("description", ""),
                "timeZone": calendar.get("timeZone", "Unknown"),
            }

            # Test write access by creating and deleting a test event
            test_event = {
                "summary": "FOGIS Access Test - Safe to Delete",
                "description": "This is a test event created by FOGIS setup wizard. It will be automatically deleted.",
                "start": {
                    "dateTime": (datetime.now() + timedelta(days=1)).isoformat(),
                    "timeZone": "Europe/Stockholm",
                },
                "end": {
                    "dateTime": (
                        datetime.now() + timedelta(days=1, hours=1)
                    ).isoformat(),
                    "timeZone": "Europe/Stockholm",
                },
            }

            # Create test event
            event = (
                self.service.events()
                .insert(calendarId=calendar_id, body=test_event)
                .execute()
            )

            # Delete test event immediately
            self.service.events().delete(
                calendarId=calendar_id, eventId=event["id"]
            ).execute()

            result["writable"] = True
            result["valid"] = True

            self.logger.info(f"Calendar validation successful for: {calendar_id}")

        except HttpError as e:
            error_msg = f"HTTP error validating calendar: {e}"
            self.logger.error(error_msg)
            result["error"] = error_msg

            # Check if it's a permission issue
            if e.resp.status == 403:
                result["error"] = "Insufficient permissions to access this calendar"
            elif e.resp.status == 404:
                result["error"] = "Calendar not found or not accessible"

        except Exception as e:
            error_msg = f"Unexpected error validating calendar: {e}"
            self.logger.error(error_msg)
            result["error"] = error_msg

        return result

    def share_calendar(
        self, calendar_id: str, email: str, role: str = "writer"
    ) -> bool:
        """
        Share a calendar with another user.

        Args:
            calendar_id: ID of the calendar to share
            email: Email address of the user to share with
            role: Access role ('reader', 'writer', 'owner')

        Returns:
            True if sharing was successful, False otherwise
        """
        acl_rule = {"scope": {"type": "user", "value": email}, "role": role}

        try:
            self.service.acl().insert(calendarId=calendar_id, body=acl_rule).execute()

            self.logger.info(f"Shared calendar {calendar_id} with {email} as {role}")
            return True

        except HttpError as e:
            self.logger.error(f"Error sharing calendar: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sharing calendar: {e}")
            return False

    def get_calendar_info(self, calendar_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific calendar.

        Args:
            calendar_id: ID of the calendar

        Returns:
            Dictionary with calendar information or None if not found
        """
        try:
            calendar = self.service.calendars().get(calendarId=calendar_id).execute()

            return {
                "id": calendar["id"],
                "summary": calendar.get("summary", "Unknown"),
                "description": calendar.get("description", ""),
                "timeZone": calendar.get("timeZone", "Unknown"),
                "location": calendar.get("location", ""),
                "etag": calendar.get("etag", ""),
            }

        except HttpError as e:
            self.logger.error(f"Error getting calendar info: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error getting calendar info: {e}")
            return None

    def delete_calendar(self, calendar_id: str) -> bool:
        """
        Delete a calendar (use with caution).

        Args:
            calendar_id: ID of the calendar to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            self.service.calendars().delete(calendarId=calendar_id).execute()
            self.logger.info(f"Deleted calendar: {calendar_id}")
            return True

        except HttpError as e:
            self.logger.error(f"Error deleting calendar: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error deleting calendar: {e}")
            return False

    def create_test_event(self, calendar_id: str) -> Optional[str]:
        """
        Create a test event to verify calendar functionality.

        Args:
            calendar_id: ID of the calendar

        Returns:
            Event ID if creation was successful, None otherwise
        """
        test_event = {
            "summary": "FOGIS Test Event",
            "description": "Test event created by FOGIS setup wizard to verify calendar functionality.",
            "start": {
                "dateTime": (datetime.now() + timedelta(hours=1)).isoformat(),
                "timeZone": "Europe/Stockholm",
            },
            "end": {
                "dateTime": (datetime.now() + timedelta(hours=2)).isoformat(),
                "timeZone": "Europe/Stockholm",
            },
        }

        try:
            event = (
                self.service.events()
                .insert(calendarId=calendar_id, body=test_event)
                .execute()
            )

            self.logger.info(f"Created test event in calendar {calendar_id}")
            return event["id"]

        except HttpError as e:
            self.logger.error(f"Error creating test event: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error creating test event: {e}")
            return None
