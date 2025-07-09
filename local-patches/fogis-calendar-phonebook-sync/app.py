import logging
import os
import subprocess

# Import dotenv for loading environment variables from .env file
from dotenv import load_dotenv
from flask import Flask, jsonify, request

# Import version information
from version import get_version

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Docker healthcheck."""
    try:
        # Check if we can access the data directory
        if not os.path.exists("data"):
            return jsonify({"status": "error", "message": "Data directory not accessible"}), 500

        # Check if token.json exists and is readable
        if not os.path.exists("/app/data/token.json"):
            return (
                jsonify(
                    {
                        "status": "warning",
                        "message": "token.json not found, may need authentication",
                    }
                ),
                200,
            )

        # Add any other critical checks here

        # Get version information
        version = get_version()

        return (
            jsonify(
                {
                    "status": "healthy",
                    "version": version,
                    "environment": os.environ.get("ENVIRONMENT", "development"),
                }
            ),
            200,
        )
    except Exception as e:
        logging.exception("Health check failed")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/sync", methods=["POST"])
def sync_fogis():
    """Endpoint to trigger FOGIS calendar and contacts sync."""
    try:
        # Get optional parameters from request
        data = request.get_json(silent=True) or {}
        delete_events = data.get("delete", False)

        # Build command
        cmd = ["python", "fogis_calendar_sync.py"]
        if delete_events:
            cmd.append("--delete")

        # Set environment variables for FOGIS credentials if provided
        env = os.environ.copy()
        if "username" in data and "password" in data:
            env["FOGIS_USERNAME"] = data["username"]
            env["FOGIS_PASSWORD"] = data["password"]

        # Run the sync script as a subprocess
        logging.info("Starting FOGIS sync process")
        process = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)

        # Check if the process was successful
        if process.returncode == 0:
            logging.info("FOGIS sync completed successfully")
            return jsonify(
                {
                    "status": "success",
                    "message": "FOGIS sync completed successfully",
                    "output": process.stdout,
                }
            )

        logging.error("FOGIS sync failed with error: %s", process.stderr)
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "FOGIS sync failed",
                    "error": process.stderr,
                    "output": process.stdout,
                }
            ),
            500,
        )

    except Exception as e:
        logging.exception("Error during FOGIS sync")
        return jsonify({"status": "error", "message": f"Error during FOGIS sync: {str(e)}"}), 500


@app.route("/create_events", methods=["POST"])
def create_calendar_events():
    """Endpoint to create calendar events for FOGIS matches."""
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400

        calendar_id = data.get('calendar_id')
        events = data.get('events', [])

        if not calendar_id or not events:
            return jsonify({"status": "error", "message": "calendar_id and events are required"}), 400

        logging.info(f"Creating {len(events)} calendar events for calendar: {calendar_id}")

        # Import Google Calendar API components
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        import json
        from datetime import datetime

        # Load credentials
        token_path = '/app/data/token.json'
        if not os.path.exists(token_path):
            return jsonify({"status": "error", "message": "Google credentials not found"}), 500

        try:
            with open(token_path, 'r') as f:
                token_data = json.load(f)

            creds = Credentials.from_authorized_user_info(token_data)

            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save refreshed token
                with open(token_path, 'w') as f:
                    f.write(creds.to_json())

            # Build Calendar service
            service = build('calendar', 'v3', credentials=creds)

            created_events = []

            for event_data in events:
                try:
                    # Convert event data to Google Calendar format
                    calendar_event = {
                        'summary': event_data.get('summary', 'FOGIS Match'),
                        'description': event_data.get('description', ''),
                        'location': event_data.get('location', ''),
                        'start': {
                            'dateTime': event_data.get('start_time'),  # UTC timezone (original format)
                            'timeZone': 'UTC',
                        },
                        'end': {
                            'dateTime': event_data.get('end_time'),  # UTC timezone (original format)
                            'timeZone': 'UTC',
                        },
                        'reminders': {
                            'useDefault': False,
                            'overrides': [
                                {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                                {'method': 'popup', 'minutes': 60},       # 1 hour before
                            ],
                        },
                    }

                    # Create the event
                    created_event = service.events().insert(
                        calendarId=calendar_id,
                        body=calendar_event
                    ).execute()

                    created_events.append({
                        'match_id': event_data.get('match_id'),
                        'event_id': created_event.get('id'),
                        'htmlLink': created_event.get('htmlLink'),
                        'summary': created_event.get('summary')
                    })

                    logging.info(f"Created calendar event: {created_event.get('summary')} - {created_event.get('htmlLink')}")

                except Exception as e:
                    logging.error(f"Error creating individual event: {e}")
                    continue

            logging.info(f"Successfully created {len(created_events)} calendar events")

            return jsonify({
                "status": "success",
                "message": f"Created {len(created_events)} calendar events",
                "events": created_events,
                "calendar_id": calendar_id
            })

        except Exception as e:
            logging.error(f"Error with Google Calendar API: {e}")
            return jsonify({"status": "error", "message": f"Calendar API error: {str(e)}"}), 500

    except Exception as e:
        logging.exception("Error creating calendar events")
        return jsonify({"status": "error", "message": f"Error creating calendar events: {str(e)}"}), 500


if __name__ == "__main__":
    # Use environment variables for host and port if available
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5003))
    app.run(host=host, port=port)
