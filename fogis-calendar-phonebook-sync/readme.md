# FOGIS Calendar & Contacts Sync

[![Tests](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/tests.yml/badge.svg)](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/tests.yml)
[![Code Quality](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/code-quality.yml/badge.svg)](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/code-quality.yml)
[![Docker Build](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/docker-build.yml/badge.svg)](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/docker-build.yml)
[![Deploy](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/deploy.yml/badge.svg)](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/deploy.yml)
[![Nightly CI/CD](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/nightly.yml/badge.svg)](https://github.com/PitchConnect/fogis-calendar-phonebook-sync/actions/workflows/nightly.yml)
[![codecov](https://codecov.io/gh/PitchConnect/fogis-calendar-phonebook-sync/branch/main/graph/badge.svg)](https://codecov.io/gh/PitchConnect/fogis-calendar-phonebook-sync)

[![Repository Link](https://img.shields.io/badge/GitHub-Repo-blue?logo=github)](https://github.com/PitchConnect/fogis-calendar-phonebook-sync)

This Python script synchronizes match data from the FOGIS API with your Google Calendar and manages referee contacts in Google Contacts. It helps you keep your calendar updated with your referee assignments and maintain an organized contact list of referees.

## Features

* Calendar Synchronization:
    * Automatically creates, updates, and deletes Google Calendar events based on your FOGIS match schedule.
    * Detects changes in match details (time, venue, referees, etc.) and updates existing calendar events accordingly.
    * Includes detailed event descriptions with match number, competition name, referee information, team contact details, and a link to the official match facts page.
    * Prevents duplicate events and efficiently updates only when necessary.
    * Supports deleting orphaned calendar events (events no longer in your FOGIS schedule).
    * Option to delete all existing calendar events before syncing for a clean refresh.

* Referee Contact Management:
    * Automatically adds referees from your FOGIS match assignments to your Google Contacts.
    * Organizes referees into a "Referees" contact group.
    * Creates new contacts for referees not already in your Google Contacts.
    * Updates existing referee contacts with the latest information from FOGIS (phone number, address, etc.).
    * Uses Fogis ID (DomarNr) and phone number to efficiently find and update existing contacts, minimizing duplicates.
    * Implements robust error handling and retry mechanisms for reliable contact management, even with Google API rate limits.

* Headless Authentication:
    * Run the application on servers without a browser or GUI.
    * Receive authentication links via email, Discord, or Slack.
    * Lightweight authentication server handles OAuth callbacks.
    * Proactive token refresh to minimize authentication requests.

* Logging: Comprehensive logging to track script execution, identify issues, and debug problems.

## Prerequisites

Before running this script, you need to have the following:

* Python 3.6 or higher: Make sure Python is installed on your system.
* Google Account: You need a Google account to access Google Calendar and Google Contacts.
* FOGIS Account: You need a FOGIS account with access to your match schedule.
* Google Cloud Project: You need to create a Google Cloud project and enable the following APIs:
    * Google Calendar API
    * Google People API
* Google API Credentials: You will need to download credentials for your Google Cloud project.
* FOGIS Credentials: You need your FOGIS username and password.


## Installation

1. Clone the repository (if applicable):

   ```bash
   git clone [repository URL] # If you are using Git
   cd [repository directory]
   ```

   If you downloaded the files directly, navigate to the directory where you saved them in your terminal.

2. Install Python dependencies:

   It's recommended to use a virtual environment. If you don't have `virtualenv` installed, install it:

   ```bash
   pip install virtualenv
   ```

   Create and activate a virtual environment:

   ```bash
   virtualenv venv
   source venv/bin/activate  # On Linux/macOS
   venv\Scripts\activate  # On Windows
   ```

   Install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure Google API Credentials:

    * Go to your Google Cloud Project's Credentials page: [https://console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials)
    * Create credentials: Click "Create Credentials" > "OAuth client ID".
    * Select "Application type" as "Desktop app".
    * Name your application (e.g., "FOGIS Sync").
    * Click "Create".
    * Download the credentials as a JSON file (click the download icon next to the newly created client ID).
    * **Rename the downloaded JSON file to `credentials.json` and place it in the same directory as the Python scripts.**

4. Configure `config.json`:

    * Create a file named `config.json` in the same directory as the Python scripts.
    * Copy and paste the following JSON structure into `config.json` and modify the values according to your setup:

    ```bash
    {
      "CREDENTIALS_FILE": "credentials.json",
      "TOKEN_FILE": "token.json",
      "SCOPES": [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/contacts"
      ],
      "CALENDAR_ID": "your_google_calendar_id@group.calendar.google.com",
      "SYNC_TAG": "FOGIS_SYNC",
      "MATCH_FILE": "matches_cache.json",
      "NOTIFICATION_METHOD": "email",
      "NOTIFICATION_EMAIL_SENDER": "your-email@gmail.com",
      "NOTIFICATION_EMAIL_RECEIVER": "your-email@gmail.com",
      "SMTP_SERVER": "smtp.gmail.com",
      "SMTP_PORT": 587,
      "SMTP_USERNAME": "your-email@gmail.com",
      "SMTP_PASSWORD": "your-app-password",
      "AUTH_SERVER_PORT": 8080,
      "AUTH_SERVER_HOST": "localhost",
      "DISCORD_WEBHOOK_URL": "",
      "SLACK_WEBHOOK_URL": "",
      "TOKEN_REFRESH_BUFFER_DAYS": 1
    }
    ```
    * `CREDENTIALS_FILE`:  Should be "credentials.json" if you followed step 3.
    * `TOKEN_FILE`:  Should be "token.json". This file will be automatically created to store your authorization tokens.
    * `SCOPES`:  Keep this as is, these are the necessary permissions for the script.
    * `CALENDAR_ID`: **Replace "your_google_calendar_id@group.calendar.google.com" with the actual ID of the Google Calendar you want to sync with.** You can find your calendar ID in your Google Calendar settings (Settings and sharing > Integrate calendar > Calendar ID).
    * `SYNC_TAG`:  Set a unique tag (e.g., "FOGIS_SYNC") to identify events created by this script in your calendar. This is used for deleting orphaned events.
    * `MATCH_FILE`:  Filename (e.g., "matches_cache.json") where the script will store hashes of processed matches to detect changes and avoid redundant updates.

5. Set FOGIS Credentials as Environment Variables:

    * **It is highly recommended to set your FOGIS username and password as environment variables for security.**
    * **On Linux/macOS:**

        ```bash
        export FOGIS_USERNAME="your_fogis_username"
        export FOGIS_PASSWORD="your_fogis_password"
        ```
    * **On Windows (Command Prompt):**

        ```bash
        set FOGIS_USERNAME=your_fogis_username
        set FOGIS_PASSWORD=your_fogis_password
        ```
    * **On Windows (PowerShell):**

        ```bash
        $env:FOGIS_USERNAME="your_fogis_username"
        $env:FOGIS_PASSWORD="your_fogis_password"
        ```
    * **Replace "your_fogis_username" and "your_fogis_password" with your actual FOGIS login credentials.**
    * Alternatively, you can provide username and password as command-line arguments (see Usage section), but environment variables are more secure.

## Usage - Basic Example

Open your terminal, navigate to the directory containing the scripts, and run `fogis_calendar_sync.py` with the desired options.

**Basic Sync (Calendar and Contacts):**

```bash
python fogis_calendar_sync.py
```

This will:
* Log in to FOGIS.
* Fetch your upcoming matches.
* Synchronize matches with your Google Calendar (create/update events).
* Manage referee contacts in Google Contacts (create/update contacts and groups).

**Command-line Arguments:**

* `--delete`: Delete existing calendar events created by this script (identified by `SYNC_TAG` in `config.json`) before syncing. This is useful for a clean resync.

   ```bash
   python fogis_calendar_sync.py --delete
   ```

* `--fresh-sync`: Force complete reprocessing of both calendar events and referee contacts, regardless of cached state. This bypasses all change detection and ensures every match is fully processed.

   ```bash
   python fogis_calendar_sync.py --fresh-sync
   ```

   **Use cases:**
   - When referee contacts are missing from Google Contacts
   - After authentication or configuration changes
   - To force reprocessing of all matches without deleting calendar events
   - Can be combined with `--delete` for complete refresh

   ```bash
   # Force complete reprocessing with calendar event deletion
   python fogis_calendar_sync.py --fresh-sync --delete
   ```
* `--force-calendar`: Force reprocessing of calendar events only, ignoring calendar cache but preserving contact processing cache.

   ```bash
   python fogis_calendar_sync.py --force-calendar
   ```

   **Use cases:**
   - When calendar events need updating but contacts are correct
   - After calendar configuration changes
   - To refresh calendar events without reprocessing contacts

* `--force-contacts`: Force reprocessing of referee contacts only, ignoring contact cache but preserving calendar processing cache.

   ```bash
   python fogis_calendar_sync.py --force-contacts
   ```

   **Use cases:**
   - When referee contacts are missing or outdated
   - After Google Contacts configuration changes
   - To refresh contacts without updating calendar events

* `--force-all`: Force reprocessing of both calendar events and contacts, ignoring all caches (equivalent to `--fresh-sync`).

   ```bash
   python fogis_calendar_sync.py --force-all
   ```

   **Use cases:**
   - Complete refresh of both calendar and contacts
   - Alternative to `--fresh-sync` with clearer intent

* `--download`:  *(Currently this option is not fully implemented and doesn't perform a separate download)*. In the current version, the script always downloads match data from FOGIS.

* `--username <fogis_username>`:  Provide your FOGIS username via command line.

   ```bash
   python fogis_calendar_sync.py --username your_fogis_username
   ```

* `--password <fogis_password>`: Provide your FOGIS password via command line.

   ```bash
   python fogis_calendar_sync.py --password your_fogis_password
   ```

   **Warning:** Providing passwords directly in the command line is less secure than using environment variables.

* `--headless`: Run in headless authentication mode for server environments.

   ```bash
   python fogis_calendar_sync.py --headless
   ```

   This mode starts a lightweight authentication server and sends a notification with an authentication link. Useful for running on servers without a browser.

**Example with delete option:**

```bash
python fogis_calendar_sync.py --delete
```

This will first delete all existing events in your calendar with the `SYNC_TAG` defined in `config.json`, and then sync your current FOGIS match schedule.


## Configuration (`config.json` details)

* `CREDENTIALS_FILE`:  Path to your Google API credentials JSON file (should be "credentials.json").
* `TOKEN_FILE`: Path to the token JSON file (should be "token.json"). This file is automatically managed by the script.
* `SCOPES`:  List of Google API scopes required by the script. **Do not modify unless you know what you are doing.**
* `CALENDAR_ID`:  The ID of your Google Calendar where events will be created.
* `SYNC_TAG`:  A unique tag to identify events created by this script in your calendar.
* `MATCH_FILE`:  Filename for caching match hashes to detect changes efficiently.

### Headless Authentication Configuration

* `NOTIFICATION_METHOD`: Method to send authentication notifications (`email`, `discord`, or `slack`).
* `NOTIFICATION_EMAIL_SENDER`: Email address to send notifications from (when using email).
* `NOTIFICATION_EMAIL_RECEIVER`: Email address to send notifications to (when using email).
* `SMTP_SERVER`: SMTP server for sending email notifications (e.g., `smtp.gmail.com`).
* `SMTP_PORT`: SMTP port (typically `587` for TLS).
* `SMTP_USERNAME`: Username for SMTP authentication.
* `SMTP_PASSWORD`: Password or app password for SMTP authentication.
* `AUTH_SERVER_PORT`: Port for the authentication server (default: `8080`).
* `AUTH_SERVER_HOST`: Host for the authentication server (default: `localhost`).
* `DISCORD_WEBHOOK_URL`: Discord webhook URL for sending notifications (when using Discord).
* `SLACK_WEBHOOK_URL`: Slack webhook URL for sending notifications (when using Slack).
* `TOKEN_REFRESH_BUFFER_DAYS`: Number of days before token expiration to trigger refresh (default: `1`).

## Logging

The script uses the `logging` module to provide detailed information about its execution. Logs are printed to the console and can be redirected to a file if needed by modifying the logging configuration in `fogis_calendar_sync.py`.

Log levels are set to `INFO` by default, providing informative messages about the script's progress.  You can change the logging level in `fogis_calendar_sync.py` to `DEBUG` for more verbose output, which is helpful for debugging.

Logs will show information about:
* Configuration loading.
* Google Calendar and People API authorization.
* FOGIS login and match fetching.
* Calendar event creation, updating, and deletion.
* Contact creation and updates.
* Error messages and warnings.

## Troubleshooting

* Google API Errors (Quota Exceeded, etc.):
    * The script implements retry mechanisms with exponential backoff to handle transient Google API errors.
    * If you encounter persistent quota errors (HTTP 429), you might need to wait and try again later.  The script logs detailed error messages, check the console output for more information.
    * Ensure you have enabled the Google Calendar API and Google People API for your Google Cloud project.
* Authorization Errors:
    * If you get authorization errors, delete the `token.json` file and run the script again. It will re-initiate the authorization flow.
    * Make sure `credentials.json` is correctly placed in the same directory as the scripts and is valid.
    * Verify that the `SCOPES` in `config.json` match the APIs you have enabled in your Google Cloud project.
* Headless Authentication Issues:
    * If using headless mode, ensure your notification settings in `config.json` are correct.
    * For email notifications, make sure your SMTP settings are valid and the email account allows sending emails from less secure apps or has an app password configured.
    * Check that the authentication server port (default: 8080) is not blocked by a firewall.
    * The authentication link is valid for 10 minutes. If it expires, run the script again to generate a new link.
* FOGIS Login Errors:
    * Double-check your FOGIS username and password environment variables or command-line arguments.
    * Ensure your FOGIS account is active and you have access to your match schedule.
* Calendar Events Not Syncing/Contacts Not Updating:
    * Check the logs for any error messages.
    * Verify that the `CALENDAR_ID` in `config.json` is correct.
    * If using the `--delete` option, ensure that the `SYNC_TAG` in `config.json` is correct so the script can identify and delete existing events.
    * If referee contacts are missing, try using `--fresh-sync` to force complete reprocessing.
* Referee Contacts Missing from Google Contacts:
    * Use the `--fresh-sync` flag to bypass change detection and force contact processing.
    * Check that Google People API is enabled in your Google Cloud project.
    * Verify that your OAuth token has the necessary scopes for Google Contacts.
    * Look for contact processing logs with emoji indicators (🏃‍♂️, 📋, ✅) to confirm processing.

If you encounter issues, please review the logs carefully.  Detailed error messages are logged to help you diagnose problems.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

### Development Setup

For development, you **must** install the development dependencies and pre-commit hooks:

```bash
# Install development dependencies
pip install -r dev-requirements.txt

# Install pre-commit hooks (REQUIRED)
pre-commit install

# Verify pre-commit setup
pre-commit run --all-files
```

**⚠️ Important**: Pre-commit hooks are required for all development work. They ensure code quality standards are met and prevent CI/CD pipeline failures.

The pre-commit hooks include:
- **Code formatting** (black, isort)
- **Linting** (flake8)
- **Security scanning** (bandit)
- **Test execution** (pytest)
- **File validation** (YAML, JSON)

For more information on our code quality standards, see the [Pre-commit Setup Guide](../PRE_COMMIT_SETUP_GUIDE.md).

### CI/CD Pipeline

This project uses a comprehensive CI/CD pipeline with automated testing, code quality checks, and deployment processes. For detailed information about the CI/CD pipeline, see [docs/ci_cd.md](docs/ci_cd.md).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE.txt) file for details.

## Contact

For questions, issues, or contributions, please feel free to reach out:

* Email: [bartek.svaberg@gmail.com](mailto:bartek.svaberg@gmail.com)
* [GitHub](https://github.com/timmybird)

## Thank you for using Fogis Calendar Sync!
