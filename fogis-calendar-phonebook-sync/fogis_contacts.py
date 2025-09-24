"""FOGIS Contacts Management Module.

This module manages contacts from FOGIS (Swedish Football Association)
and synchronizes them with Google Contacts.
"""

import logging
import os
import re  # For phone number normalization
import time  # Import time for sleep

import google.auth

# Import dotenv for loading environment variables from .env file
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2 import credentials, service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import token manager for unified authentication
import token_manager

# Load environment variables from .env file
load_dotenv()


SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/contacts",
]

CREDENTIALS_FILE = "credentials.json"

MAX_RETRIES_GOOGLE_API = 5
BACKOFF_FACTOR_GOOGLE_API = 2
BASE_DELAY_GOOGLE_API = 60  # Increased base delay to 60 seconds for quota errors!
DELAY_BETWEEN_CONTACT_CALLS = 1  # Increased delay between calls to 1 second!


def normalize_email_address(email):
    """
    Normalize email address for better duplicate detection.

    Handles common email variations:
    - Converts to lowercase
    - Strips whitespace
    - Validates basic email format

    Args:
        email (str): Raw email address

    Returns:
        str: Normalized email address or empty string if invalid
    """
    if not email or not isinstance(email, str):
        return ""

    # Strip whitespace and convert to lowercase
    normalized = email.strip().lower()

    # Basic email validation (contains @ with content before and after, and at least one dot after @)
    if "@" in normalized:
        parts = normalized.split("@")
        if len(parts) == 2 and parts[0] and parts[1] and "." in parts[1]:
            return normalized

    # Return empty string for invalid emails
    logging.debug(f"Email address normalization failed for: {email}")
    return ""


def normalize_phone_number(phone):
    """
    Normalize phone number for better duplicate detection.

    Handles common Swedish phone number formats:
    - Removes spaces, dashes, parentheses
    - Converts Swedish national format (07X) to international (+467X)
    - Ensures consistent +46 country code format

    Args:
        phone (str): Raw phone number

    Returns:
        str: Normalized phone number or empty string if invalid
    """
    if not phone or not isinstance(phone, str):
        return ""

    # Remove all non-digit characters except +
    normalized = re.sub(r"[^\d+]", "", phone.strip())

    # Handle empty result
    if not normalized:
        return ""

    # Handle Swedish phone number formats
    if normalized.startswith("0"):
        # Convert Swedish national format (07X) to international (+467X)
        normalized = "+46" + normalized[1:]
    elif normalized.startswith("46") and not normalized.startswith("+46"):
        # Add + to country code if missing
        normalized = "+" + normalized
    elif not normalized.startswith("+") and len(normalized) >= 10:
        # Assume Swedish number if no country code and reasonable length
        normalized = "+46" + normalized

    # Validate final format (should be +46 followed by 8-9 digits)
    if re.match(r"^\+46\d{8,9}$", normalized) or re.match(r"^\+\d{10,15}$", normalized):
        return normalized
    else:
        # Return original if normalization failed
        logging.debug(f"Phone number normalization failed for: {phone} -> {normalized}")
        return phone


def authorize_google_people():
    """
    Authorizes access to the Google People API using unified token management.

    This function now uses the same token management system as the calendar sync
    to ensure consistent OAuth token handling and proper container path support.

    Returns:
        google.oauth2.credentials.Credentials: Valid credentials or None if authentication fails
    """
    try:
        # Use configurable token path (same as calendar sync)
        token_path = os.environ.get("TOKEN_PATH", "token.json")
        logging.info("🔐 Google People API authentication in progress...")
        logging.info(f"📁 Using token path: {token_path}")

        # Try to load existing credentials using the same approach as calendar sync
        creds = None
        if os.path.exists(token_path):
            try:
                logging.info(
                    "📁 Token file found, attempting to load OAuth credentials..."
                )
                creds = google.oauth2.credentials.Credentials.from_authorized_user_file(
                    token_path, SCOPES
                )
                logging.info(
                    "✅ Successfully loaded Google People credentials from %s",
                    token_path,
                )
            except Exception as e:
                logging.error(
                    "❌ Error loading OAuth credentials from %s: %s", token_path, e
                )
                logging.info("🔄 Will attempt to use token manager fallback")
                creds = None

        # If no credentials loaded from file, try token manager
        if not creds:
            logging.info("🔄 Attempting to load credentials via token manager...")
            try:
                creds = token_manager.load_token()
                if creds:
                    logging.info("✅ Successfully loaded credentials via token manager")
                else:
                    logging.warning("⚠️ Token manager returned no credentials")
            except Exception as e:
                logging.error("❌ Error loading credentials via token manager: %s", e)

        # Validate and refresh credentials if needed
        if creds:
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    try:
                        logging.info(
                            "🔄 Refreshing expired Google People API credentials..."
                        )
                        creds.refresh(google.auth.transport.requests.Request())

                        # Save refreshed credentials back to token file
                        try:
                            with open(token_path, "w", encoding="utf-8") as token_file:
                                token_file.write(creds.to_json())
                            logging.info(
                                "💾 Refreshed credentials saved to %s", token_path
                            )
                        except Exception as save_e:
                            logging.warning(
                                "⚠️ Failed to save refreshed credentials: %s", save_e
                            )

                        logging.info(
                            "✅ Google People API credentials successfully refreshed"
                        )
                    except Exception as refresh_e:
                        logging.error(
                            "❌ Failed to refresh Google People API credentials: %s",
                            refresh_e,
                        )
                        creds = None
                else:
                    logging.error(
                        "❌ Credentials are invalid and cannot be refreshed (no refresh token)"
                    )
                    creds = None

        if creds and creds.valid:
            logging.info("✅ Google People API authentication established")
            return creds
        else:
            logging.error("❌ Failed to obtain valid Google People API credentials")
            logging.error("💡 This may be due to:")
            logging.error("   - Missing or invalid token file at: %s", token_path)
            logging.error("   - Expired credentials without refresh token")
            logging.error("   - OAuth scope mismatch")
            logging.error("   - Container path configuration issues")
            return None

    except Exception as e:
        logging.exception(
            "❌ Unexpected error during Google People API authorization: %s", e
        )
        return None


def find_or_create_referees_group(service):
    """Finds the 'Referees' group or creates it if it doesn't exist."""
    group_name = "Referees"

    for attempt in range(MAX_RETRIES_GOOGLE_API):  # Retry loop
        try:
            results = service.contactGroups().list(pageSize=10).execute()
            groups = results.get("contactGroups", [])
            logging.info("  - Contact groups fetched")

            for group in groups:
                if group["name"] == group_name:
                    logging.info(
                        f"  - Existing '{group_name}' group found with ID: {group['resourceName']}"
                    )
                    return group["resourceName"]

            logging.info("  - '%s' group not found, creating...", group_name)
            group_body = {"contactGroup": {"name": group_name}}
            create_result = service.contactGroups().create(body=group_body).execute()
            new_group_id = create_result["resourceName"]
            logging.info(
                "  - Created new '%s' group with ID: %s", group_name, new_group_id
            )
            return new_group_id

        except HttpError as error:
            if error.resp.status == 429:  # Quota exceeded
                if attempt < MAX_RETRIES_GOOGLE_API - 1:
                    delay = BASE_DELAY_GOOGLE_API * (BACKOFF_FACTOR_GOOGLE_API**attempt)
                    logging.warning(
                        f"Google People API Quota exceeded, retrying in {delay} seconds... "
                        f"(Attempt {attempt + 1}/{MAX_RETRIES_GOOGLE_API})"
                    )
                    time.sleep(delay)
                else:
                    logging.error(
                        f"Google People API Quota exceeded, max retries reached. Error: {error}"
                    )
                    print(f"Full error details: {error.content.decode()}")
                    return None  # Return None to indicate failure
            else:  # Other HTTP errors
                logging.error("An HTTP error occurred: %s", error)
                print(f"Full error details: {error.content.decode()}")
                return None
        except Exception as e:
            logging.exception(
                "An unexpected error occurred while finding or creating group: %s", e
            )
            return None
        time.sleep(DELAY_BETWEEN_CONTACT_CALLS)  # Rate limiting delay
    return None  # Return None if all retries fail


def process_referees(match):
    """
    Manages referees contacts with unified authentication and enhanced error logging.

    This function now uses the same authentication system as calendar sync
    to ensure consistent OAuth token handling.

    Args:
        match (dict): Match data containing referee information in 'domaruppdraglista'

    Returns:
        bool: True if processing completed successfully, False if authentication failed
    """
    logging.info("🏃‍♂️ Starting referee contact processing...")

    # Check if match has referee data
    referees = match.get("domaruppdraglista", [])
    if not referees:
        logging.info("ℹ️ No referees found in match data, skipping contact processing")
        return True

    logging.info(f"📋 Found {len(referees)} referees to process")

    # Authenticate with Google People API using unified system
    creds = authorize_google_people()
    if not creds:
        logging.error(
            "❌ Failed to obtain Google People API credentials for referee processing"
        )
        logging.error(
            "💡 Contact processing cannot continue without valid authentication"
        )
        return False

    logging.info("✅ Google People API authentication successful")

    # Get the user's referee number from environment variable
    user_referee_number = os.environ.get("USER_REFEREE_NUMBER")
    if user_referee_number:
        logging.info(
            f"👤 User referee number set to {user_referee_number}, will skip updating this contact"
        )

    try:
        service = build("people", "v1", credentials=creds)
        logging.info("🔧 Google People API service built successfully")

        processed_count = 0
        skipped_count = 0
        error_count = 0

        for referee in match["domaruppdraglista"]:
            name = referee.get("personnamn", "Unknown")
            phone = referee.get("mobiltelefon", "")
            referee_number = referee.get("domarnr", "")

            logging.info(f"👤 Processing referee: {name} (#{referee_number})")

            # Skip updating the current user's contact
            if user_referee_number and referee_number == user_referee_number:
                logging.info(
                    f"⏭️ Skipping contact update for current user: {name} (Referee #{referee_number})"
                )
                skipped_count += 1
                continue

            try:
                existing_contact = find_contact_by_name_and_phone(
                    service, name, phone, referee
                )

                if existing_contact:
                    update_google_contact(
                        service, existing_contact["resourceName"], referee
                    )
                    logging.info("✅ Updated contact for referee: %s", name)
                    processed_count += 1
                else:
                    group_id = find_or_create_referees_group(service)
                    if group_id:
                        create_google_contact(service, referee, group_id)
                        logging.info("✅ Created contact for referee: %s", name)
                        processed_count += 1
                    else:
                        logging.error(
                            "❌ Could not find or create Referees group, skipping contact creation for %s",
                            name,
                        )
                        error_count += 1

            except Exception as e:
                logging.exception(
                    "❌ Error managing contact for referee %s: %s", name, e
                )
                error_count += 1

        # Summary logging
        total_referees = len(referees)
        logging.info("📊 Contact processing summary:")
        logging.info(f"   Total referees: {total_referees}")
        logging.info(f"   Processed: {processed_count}")
        logging.info(f"   Skipped: {skipped_count}")
        logging.info(f"   Errors: {error_count}")

        if error_count > 0:
            logging.warning(f"⚠️ Contact processing completed with {error_count} errors")
        else:
            logging.info("✅ Contact processing completed successfully")

        return True

    except Exception as e:
        logging.exception(
            "❌ Unexpected error occurred building Google People service: %s", e
        )
        logging.error("💡 This may be due to:")
        logging.error("   - Invalid or expired OAuth credentials")
        logging.error("   - Google People API service unavailable")
        logging.error("   - Network connectivity issues")
        return False


def find_contact_by_name_and_phone(service, name, phone, referee):
    """Finds a contact in Google Contacts by domarNr, or fallback to phone number."""
    domar_nr = referee.get("domarnr")

    # --- Lookup by externalId (FogisId=DomarNr) with Pagination and Retry ---
    if domar_nr:
        fogis_external_id_value = f"FogisId=DomarNr={domar_nr}"

        for attempt in range(MAX_RETRIES_GOOGLE_API):
            try:
                all_connections = []
                request = (
                    service.people()
                    .connections()
                    .list(
                        resourceName="people/me",
                        personFields="names,phoneNumbers,externalIds",
                        pageSize=1000,
                    )
                )
                while request:
                    results = request.execute()
                    connections = results.get("connections", [])
                    all_connections.extend(connections)
                    request = service.people().connections().list_next(request, results)

                if all_connections:
                    for person in all_connections:
                        if "externalIds" in person:
                            for external_id in person["externalIds"]:
                                if (
                                    external_id.get("type") == "account"
                                    and external_id.get("value")
                                    == fogis_external_id_value
                                ):
                                    logging.info(
                                        f"  - Contact found by FogisId=DomarNr: {domar_nr}"
                                    )
                                    return person
                break  # Break retry loop if successful (or not found)

            except HttpError as error:
                if error.resp.status == 429:  # Quota exceeded - MORE AGGRESSIVE BACKOFF
                    if attempt < MAX_RETRIES_GOOGLE_API - 1:
                        delay = BASE_DELAY_GOOGLE_API * (
                            BACKOFF_FACTOR_GOOGLE_API**attempt
                        )  # Using increased BASE_DELAY
                        logging.warning(
                            f"Google People API Quota exceeded (FogisId lookup), retrying in {delay} seconds... "
                            f"(Attempt {attempt + 1}/{MAX_RETRIES_GOOGLE_API})"
                        )
                        time.sleep(delay)
                    else:
                        logging.error(
                            f"Google People API Quota exceeded (FogisId lookup), max retries reached. Error: {error}"
                        )
                        print(
                            f"   Full error details (FogisId paginated lookup): {error.content.decode()}"
                        )
                        break
                else:  # Other HTTP errors - LESS AGGRESSIVE (or no) BACKOFF if needed
                    logging.error(
                        "An HTTP error occurred during FogisId lookup: %s", error
                    )
                    print(
                        f"   Full error details (FogisId paginated lookup): {error.content.decode()}"
                    )
                    break
            except Exception as e:
                logging.exception(
                    f"An unexpected error occurred during FogisId lookup (paginated): {e}"
                )
                return None
            time.sleep(DELAY_BETWEEN_CONTACT_CALLS)  # Rate limiting delay

    # --- Fallback Lookup by Phone Number with Pagination and Retry ---
    for attempt in range(MAX_RETRIES_GOOGLE_API):
        try:
            all_connections = []
            request = (
                service.people()
                .connections()
                .list(
                    resourceName="people/me",
                    personFields="names,phoneNumbers,emailAddresses",  # Added emailAddresses for enhanced matching
                    pageSize=1000,
                )
            )
            while request:
                results = request.execute()
                connections = results.get("connections", [])
                all_connections.extend(connections)
                request = service.people().connections().list_next(request, results)

            if all_connections:
                # Normalize the search phone number for comparison
                normalized_search_phone = normalize_phone_number(phone)

                for person in all_connections:
                    if "phoneNumbers" in person:
                        for phone_number in person["phoneNumbers"]:
                            # Try exact match first
                            if phone_number["value"] == phone:
                                logging.info(
                                    f"  - Contact found by exact phone number match: {phone}"
                                )
                                return person

                            # Try normalized match for better duplicate detection
                            normalized_contact_phone = normalize_phone_number(
                                phone_number["value"]
                            )
                            if (
                                normalized_contact_phone
                                and normalized_contact_phone == normalized_search_phone
                            ):
                                logging.info(
                                    f"  - Contact found by normalized phone number match: {phone} -> {normalized_search_phone}"
                                )
                                return person

                # --- Tertiary: Email Address Matching ---
                referee_email = referee.get("epostadress", "")
                if referee_email:
                    normalized_search_email = normalize_email_address(referee_email)
                    if normalized_search_email:
                        for person in all_connections:
                            if "emailAddresses" in person:
                                for email_data in person["emailAddresses"]:
                                    contact_email = email_data.get("value", "")
                                    normalized_contact_email = normalize_email_address(
                                        contact_email
                                    )
                                    if (
                                        normalized_contact_email
                                        and normalized_contact_email
                                        == normalized_search_email
                                    ):
                                        logging.info(
                                            f"  - Contact found by email address match: {referee_email} -> {normalized_search_email}"
                                        )
                                        return person

                logging.info(
                    f"  - Contact not found for name '{name}', phone '{phone}', and email '{referee_email}' (comprehensive search)"
                )
                return None  # Not found by either method
            break  # Break retry loop if successful (or not found)

        except HttpError as error:
            if error.resp.status == 429:  # Quota exceeded - MORE AGGRESSIVE BACKOFF
                if attempt < MAX_RETRIES_GOOGLE_API - 1:
                    delay = BASE_DELAY_GOOGLE_API * (
                        BACKOFF_FACTOR_GOOGLE_API**attempt
                    )  # Using increased BASE_DELAY
                    logging.warning(
                        f"Google People API Quota exceeded (phone lookup), retrying in {delay} seconds... "
                        f"(Attempt {attempt + 1}/{MAX_RETRIES_GOOGLE_API})"
                    )
                    time.sleep(delay)
                else:
                    logging.error(
                        f"Google People API Quota exceeded (phone lookup), max retries reached. Error: {error}"
                    )
                    print(
                        f"   Full error details (phone paginated lookup): {error.content.decode()}"
                    )
                    return None
            else:  # Other HTTP errors - LESS AGGRESSIVE (or no) BACKOFF if needed
                logging.error(
                    f"An HTTP error occurred during phone number lookup (paginated): {error}"
                )
                print(
                    f"   Full error details (phone paginated lookup): {error.content.decode()}"
                )
                return None
        except Exception as e:
            logging.exception(
                f"An unexpected error occurred during phone number lookup (paginated): {e}"
            )
            return None
        time.sleep(DELAY_BETWEEN_CONTACT_CALLS)  # Rate limiting delay
    return None


def update_google_contact(service, contact_id, referee):
    """Updates a contact in Google Contacts."""
    for attempt in range(MAX_RETRIES_GOOGLE_API):
        try:
            # Retrieve the existing contact information
            existing_contact = (
                service.people()
                .get(
                    resourceName=contact_id,
                    personFields="names,phoneNumbers,emailAddresses,organizations,addresses",
                )
                .execute()
            )

            existing_etag = existing_contact["etag"]

            updated_names = existing_contact.get("names", [])
            updated_phone_numbers = existing_contact.get("phoneNumbers", [])
            updated_email_addresses = existing_contact.get("emailAddresses", [])
            updated_organizations = existing_contact.get("organizations", [])
            updated_addresses = existing_contact.get("addresses", [])

            if referee["mobiltelefon"]:
                new_phone_number = {"value": referee["mobiltelefon"], "type": "mobile"}
                if (
                    not updated_phone_numbers
                    or updated_phone_numbers[0].get("value") != referee["mobiltelefon"]
                ):
                    updated_phone_numbers = [new_phone_number]

            updated_contact_data = {
                "etag": existing_etag,
                "names": updated_names,
                "phoneNumbers": updated_phone_numbers,
                "emailAddresses": updated_email_addresses,
                "organizations": updated_organizations,
                "addresses": updated_addresses,
            }

            service.people().updateContact(
                resourceName=contact_id,
                body=updated_contact_data,
                updatePersonFields="names,phoneNumbers,emailAddresses,organizations,addresses",
            ).execute()

            logging.info(
                f"  - Updated contact for referee: {referee['personnamn']} with ID: {contact_id}"
            )
            return contact_id  # Return contact id on success

        except HttpError as error:
            if error.resp.status == 429:  # Quota exceeded - MORE AGGRESSIVE BACKOFF
                if attempt < MAX_RETRIES_GOOGLE_API - 1:
                    delay = BASE_DELAY_GOOGLE_API * (
                        BACKOFF_FACTOR_GOOGLE_API**attempt
                    )  # Using increased BASE_DELAY
                    logging.warning(
                        f"Google People API Quota exceeded (contact update), retrying in {delay} seconds... "
                        f"(Attempt {attempt + 1}/{MAX_RETRIES_GOOGLE_API})"
                    )
                    time.sleep(delay)
                else:
                    logging.error(
                        f"Google People API Quota exceeded (contact update), max retries reached. Error: {error}"
                    )
                    print(
                        f"   Full error details (contact update): {error.content.decode()}"
                    )
                    return None  # Return None on max retries
            elif (
                error.resp.status == 400
                and 'Invalid personFields mask path: "notes"' in error.content.decode()
            ):
                logging.warning(
                    f"Ignoring error 400 - Invalid personFields path 'notes'. "
                    f"Proceeding without updating notes. Full error: {error}"
                )
                return contact_id  # Return contact id and proceed without notes - specific error handling
            else:  # Other HTTP errors - LESS AGGRESSIVE (or no) BACKOFF if needed
                logging.error(
                    "An HTTP error occurred updating contact %s: %s", contact_id, error
                )
                print(
                    f"   Full error details (contact update): {error.content.decode()}"
                )
                return None  # Return None for other errors
        except Exception as e:
            logging.exception(
                "An unexpected error occurred while updating contact: %s", e
            )
            return None
        time.sleep(DELAY_BETWEEN_CONTACT_CALLS)  # Rate limiting delay
    return None  # Return None if all retries fail


def create_contact_data(referee, match_date_str=None):
    """Creates a Google Contact data structure from referee information."""
    contact_data = {
        "names": [
            {
                "displayName": referee["personnamn"],
                "givenName": (
                    referee["personnamn"].split()[0] if referee["personnamn"] else ""
                ),
                "familyName": (
                    referee["personnamn"].split()[-1] if referee["personnamn"] else ""
                ),
            }
        ],
        "phoneNumbers": [{"value": referee["mobiltelefon"], "type": "mobile"}],
        "emailAddresses": [{"value": referee["epostadress"], "type": "work"}],
        "addresses": [
            {
                "formattedValue": f"{referee['adress']}, {referee['postnr']} {referee['postort']}, {referee['land']}",
                "streetAddress": referee["adress"],
                "postalCode": referee["postnr"],
                "city": referee["postort"],
                "country": referee["land"],
                "type": "home",
            }
        ],
        "externalIds": [
            {"value": f"FogisId=DomarNr={referee['domarnr']}", "type": "account"}
        ],
    }

    if match_date_str:
        contact_data["importantDates"] = [
            {
                "label": "Refereed Until",
                "dateTime": {
                    "year": int(match_date_str.split("-")[0]),
                    "month": int(match_date_str.split("-")[1]),
                    "day": int(match_date_str.split("-")[2]),
                },
                "type": "other",
            }
        ]

    contact_data["phoneNumbers"] = [
        number for number in contact_data.get("phoneNumbers", []) if number.get("value")
    ]
    contact_data["emailAddresses"] = [
        email for email in contact_data.get("emailAddresses", []) if email.get("value")
    ]
    contact_data["organizations"] = [
        org for org in contact_data.get("organizations", []) if org.get("title")
    ]
    contact_data["addresses"] = [
        addr for addr in contact_data.get("addresses", []) if addr.get("formattedValue")
    ]
    contact_data["externalIds"] = [
        ext_id for ext_id in contact_data.get("externalIds", []) if ext_id.get("value")
    ]

    return contact_data


def find_contact_by_phone(service, phone):
    """Finds a contact in Google Contacts by phone number."""
    for attempt in range(MAX_RETRIES_GOOGLE_API):
        try:
            results = (
                service.people()
                .connections()
                .list(
                    resourceName="people/me",
                    personFields="names,phoneNumbers,emailAddresses",  # Added emailAddresses for consistency
                    pageSize=100,
                )
                .execute()
            )
            connections = results.get("connections", [])

            if connections:
                # Normalize the search phone number for comparison
                normalized_search_phone = normalize_phone_number(phone)

                for person in connections:
                    if "phoneNumbers" in person:
                        for phone_number in person["phoneNumbers"]:
                            # Try exact match first
                            if phone_number["value"] == phone:
                                logging.info(
                                    f"  - Existing contact found for exact phone number: {phone}"
                                )
                                return person

                            # Try normalized match for better duplicate detection
                            normalized_contact_phone = normalize_phone_number(
                                phone_number["value"]
                            )
                            if (
                                normalized_contact_phone
                                and normalized_contact_phone == normalized_search_phone
                            ):
                                logging.info(
                                    f"  - Existing contact found for normalized phone number: {phone} -> {normalized_search_phone}"
                                )
                                return person
            return None  # Return None if not found in this attempt, will retry or finally return None

        except HttpError as error:
            if error.resp.status == 429:  # Quota exceeded - MORE AGGRESSIVE BACKOFF
                if attempt < MAX_RETRIES_GOOGLE_API - 1:
                    delay = BASE_DELAY_GOOGLE_API * (BACKOFF_FACTOR_GOOGLE_API**attempt)
                    logging.warning(
                        f"Google People API Quota exceeded (find_contact_by_phone), retrying in {delay} seconds... "
                        f"(Attempt {attempt + 1}/{MAX_RETRIES_GOOGLE_API})"
                    )
                    time.sleep(delay)
                else:
                    logging.error(
                        f"Google People API Quota exceeded (find_contact_by_phone), max retries reached. Error: {error}"
                    )
                    print(
                        f"   Full error details (find_contact_by_phone): {error.content.decode()}"
                    )
                    return None  # Return None if max retries reached
            else:  # Other HTTP errors - LESS AGGRESSIVE (or no) BACKOFF if needed
                logging.error(
                    "An HTTP error occurred in find_contact_by_phone(): %s", error
                )
                print(
                    f"   Full error details (find_contact_by_phone): {error.content.decode()}"
                )
                return None  # Return None for other errors
        except Exception as e:
            logging.exception(
                "An unexpected error occurred in find_contact_by_phone(): %s", e
            )
            return None
        time.sleep(DELAY_BETWEEN_CONTACT_CALLS)  # Rate limiting delay
    return None  # Return None if all retries fail


def find_duplicate_contacts(service, dry_run=True):
    """
    Identify potential duplicate contacts in Google Contacts.

    This function scans all contacts and identifies potential duplicates based on:
    1. Normalized phone numbers
    2. Similar names with same phone numbers
    3. FogisId external IDs

    Args:
        service: Google People API service instance
        dry_run (bool): If True, only report duplicates without making changes

    Returns:
        dict: Dictionary containing duplicate groups and statistics
    """
    logging.info("🔍 Scanning for duplicate contacts...")

    try:
        # Fetch all contacts with relevant fields
        all_connections = []
        request = (
            service.people()
            .connections()
            .list(
                resourceName="people/me",
                personFields="names,phoneNumbers,emailAddresses,externalIds,resourceName",  # Added emailAddresses
                pageSize=1000,
            )
        )

        while request:
            results = request.execute()
            connections = results.get("connections", [])
            all_connections.extend(connections)
            request = service.people().connections().list_next(request, results)

        logging.info(f"📊 Analyzing {len(all_connections)} contacts for duplicates...")

        # Group contacts by normalized phone numbers and email addresses
        phone_groups = {}
        email_groups = {}
        fogis_groups = {}

        for contact in all_connections:
            contact_id = contact.get("resourceName", "")
            contact_name = ""

            # Extract contact name
            if "names" in contact and contact["names"]:
                contact_name = contact["names"][0].get("displayName", "")

            # Group by normalized phone numbers
            if "phoneNumbers" in contact:
                for phone_data in contact["phoneNumbers"]:
                    phone = phone_data.get("value", "")
                    if phone:
                        normalized_phone = normalize_phone_number(phone)
                        if normalized_phone:
                            if normalized_phone not in phone_groups:
                                phone_groups[normalized_phone] = []
                            phone_groups[normalized_phone].append(
                                {
                                    "id": contact_id,
                                    "name": contact_name,
                                    "phone": phone,
                                    "normalized_phone": normalized_phone,
                                }
                            )

            # Group by normalized email addresses
            if "emailAddresses" in contact:
                for email_data in contact["emailAddresses"]:
                    email = email_data.get("value", "")
                    if email:
                        normalized_email = normalize_email_address(email)
                        if normalized_email:
                            if normalized_email not in email_groups:
                                email_groups[normalized_email] = []
                            email_groups[normalized_email].append(
                                {
                                    "id": contact_id,
                                    "name": contact_name,
                                    "email": email,
                                    "normalized_email": normalized_email,
                                }
                            )

            # Group by FogisId external IDs
            if "externalIds" in contact:
                for external_id in contact["externalIds"]:
                    if external_id.get("type") == "account" and external_id.get(
                        "value", ""
                    ).startswith("FogisId="):
                        fogis_id = external_id.get("value")
                        if fogis_id not in fogis_groups:
                            fogis_groups[fogis_id] = []
                        fogis_groups[fogis_id].append(
                            {
                                "id": contact_id,
                                "name": contact_name,
                                "fogis_id": fogis_id,
                            }
                        )

        # Identify duplicate groups
        phone_duplicates = {
            phone: contacts
            for phone, contacts in phone_groups.items()
            if len(contacts) > 1
        }
        email_duplicates = {
            email: contacts
            for email, contacts in email_groups.items()
            if len(contacts) > 1
        }
        fogis_duplicates = {
            fogis_id: contacts
            for fogis_id, contacts in fogis_groups.items()
            if len(contacts) > 1
        }

        # Generate report
        duplicate_report = {
            "phone_duplicates": phone_duplicates,
            "email_duplicates": email_duplicates,
            "fogis_duplicates": fogis_duplicates,
            "total_contacts": len(all_connections),
            "phone_duplicate_groups": len(phone_duplicates),
            "email_duplicate_groups": len(email_duplicates),
            "fogis_duplicate_groups": len(fogis_duplicates),
            "total_duplicate_contacts": (
                sum(len(contacts) for contacts in phone_duplicates.values())
                + sum(len(contacts) for contacts in email_duplicates.values())
                + sum(len(contacts) for contacts in fogis_duplicates.values())
            ),
        }

        # Log summary
        logging.info("📋 Duplicate Analysis Results:")
        logging.info(
            f"   - Total contacts analyzed: {duplicate_report['total_contacts']}"
        )
        logging.info(
            f"   - Phone number duplicate groups: {duplicate_report['phone_duplicate_groups']}"
        )
        logging.info(
            f"   - Email address duplicate groups: {duplicate_report['email_duplicate_groups']}"
        )
        logging.info(
            f"   - FogisId duplicate groups: {duplicate_report['fogis_duplicate_groups']}"
        )
        logging.info(
            f"   - Total contacts involved in duplicates: {duplicate_report['total_duplicate_contacts']}"
        )

        # Log detailed duplicates
        if phone_duplicates:
            logging.info("📞 Phone Number Duplicates:")
            for phone, contacts in phone_duplicates.items():
                logging.info(f"   Phone {phone}:")
                for contact in contacts:
                    logging.info(
                        f"     - {contact['name']} (ID: {contact['id']}) - Original: {contact['phone']}"
                    )

        if email_duplicates:
            logging.info("📧 Email Address Duplicates:")
            for email, contacts in email_duplicates.items():
                logging.info(f"   Email {email}:")
                for contact in contacts:
                    logging.info(
                        f"     - {contact['name']} (ID: {contact['id']}) - Original: {contact['email']}"
                    )

        if fogis_duplicates:
            logging.info("🆔 FogisId Duplicates:")
            for fogis_id, contacts in fogis_duplicates.items():
                logging.info(f"   {fogis_id}:")
                for contact in contacts:
                    logging.info(f"     - {contact['name']} (ID: {contact['id']})")

        return duplicate_report

    except Exception as e:
        logging.exception(f"❌ Error scanning for duplicates: {e}")
        return {"error": str(e)}


def create_google_contact(service, referee, group_id):
    """Creates a new contact in Google Contacts and adds it to the specified group."""
    contact_data = create_contact_data(referee)

    for attempt in range(MAX_RETRIES_GOOGLE_API):
        try:
            person = service.people().createContact(body=contact_data).execute()
            contact_id = person["resourceName"]
            logging.info(
                f"  - Created contact for referee: {referee['personnamn']} with ID: {contact_id}"
            )

            if group_id:
                try:
                    service.contactGroups().members().modify(
                        resourceName=group_id, body={"resourceNamesToAdd": [contact_id]}
                    ).execute()
                    logging.info(
                        f"  - Added contact '{referee['personnamn']}' to 'Referees' group."
                    )
                except HttpError as e:
                    if e.resp.status == 400:
                        logging.warning(
                            f"  - Contact '{referee['personnamn']}' already in group or invalid group ID."
                        )
                    else:
                        raise
                except Exception as e:
                    logging.error("  - Error adding contact to 'Referees' group: %s", e)
            return contact_id  # Return contact id on success

        except HttpError as error:
            if error.resp.status == 429:  # Quota exceeded - MORE AGGRESSIVE BACKOFF
                if attempt < MAX_RETRIES_GOOGLE_API - 1:
                    delay = BASE_DELAY_GOOGLE_API * (
                        BACKOFF_FACTOR_GOOGLE_API**attempt
                    )  # Using increased BASE_DELAY
                    logging.warning(
                        f"Google People API Quota exceeded (contact creation), retrying in {delay} seconds... "
                        f"(Attempt {attempt + 1}/{MAX_RETRIES_GOOGLE_API})"
                    )
                    time.sleep(delay)
                elif error.resp.status == 409:  # Conflict - contact already exists
                    logging.warning(
                        f"  - Contact for referee '{referee['personnamn']}' already exists (Conflict Error 409). "
                        f"Skipping creation, finding existing by phone for group add."
                    )
                    existing_contact = find_contact_by_phone(
                        service, referee["mobiltelefon"]
                    )
                    if existing_contact:
                        return existing_contact[
                            "resourceName"
                        ]  # Return existing contact id on conflict

                    return None  # Failed to create or find existing in conflict case

                else:  # Quota exceeded, but max retries reached
                    logging.error(
                        f"Google People API Quota exceeded (contact creation), max retries reached. Error: {error}"
                    )
                    print(
                        f"   Full error details (contact creation): {error.content.decode()}"
                    )
                    return None  # Return None on max retries
            elif (
                error.resp.status == 409
            ):  # 409 is conflict, contact already exists - handle gracefully
                logging.warning(
                    f"  - Contact for referee '{referee['personnamn']}' already exists (Conflict Error 409). "
                    f"Skipping creation, finding existing by phone."
                )
                existing_contact = find_contact_by_phone(
                    service, referee["mobiltelefon"]
                )
                if existing_contact:
                    return existing_contact[
                        "resourceName"
                    ]  # Return existing contact id on conflict

                return None  # Failed to create or find existing in conflict case
            else:  # Other HTTP errors
                logging.error(
                    "An HTTP error occurred during contact creation: %s", error
                )
                print(
                    f"   Full error details (contact creation): {error.content.decode()}"
                )
                return None  # Return None for other errors
        except Exception as e:
            logging.exception(
                "An unexpected error occurred while creating contact: %s", e
            )
            return None
        time.sleep(DELAY_BETWEEN_CONTACT_CALLS)  # Rate limiting delay
    return None  # Return None if all retries fail


def test_google_contacts_connection(service):
    """Test the connection to Google People API."""
    for attempt in range(MAX_RETRIES_GOOGLE_API):
        try:
            results = (
                service.people()
                .connections()
                .list(
                    resourceName="people/me",
                    personFields="names,phoneNumbers",
                    pageSize=10,
                )
                .execute()
            )

            connections = results.get("connections", [])
            if connections:
                logging.info(
                    "Connection established: Google People API is working and can access personal contacts!"
                )
                return True

            logging.warning(
                "Successfully connected to Google People API, but no contacts found in your list."
            )
            return True  # Still successful connection

        except HttpError as error:
            if error.resp.status == 429:  # Quota exceeded - MORE AGGRESSIVE BACKOFF
                if attempt < MAX_RETRIES_GOOGLE_API - 1:
                    delay = BASE_DELAY_GOOGLE_API * (BACKOFF_FACTOR_GOOGLE_API**attempt)
                    logging.warning(
                        f"Google People API Quota exceeded (connection test), retrying in {delay} seconds... "
                        f"(Attempt {attempt + 1}/{MAX_RETRIES_GOOGLE_API})"
                    )
                    time.sleep(delay)
                else:
                    logging.error(
                        f"Google People API Quota exceeded (connection test), max retries reached. Error: {error}"
                    )
                    print(
                        f"   Full error details (connection test): {error.content.decode()}"
                    )
                    return False  # Return False if max retries reached
            else:  # Other HTTP errors - LESS AGGRESSIVE (or no) BACKOFF if needed
                logging.error("HTTPError during People API test: %s", error)
                print(f"Full error details: {error.content.decode()}")
                return False  # Return False for other errors
        except Exception as e:
            logging.exception(
                f"An unexpected error occurred during People API connection test: {e}"
            )
            return False
        time.sleep(DELAY_BETWEEN_CONTACT_CALLS)  # Rate limiting delay
    return False  # Return False if all retries fail
