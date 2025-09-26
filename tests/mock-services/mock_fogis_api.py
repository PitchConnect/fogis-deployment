#!/usr/bin/env python3
"""
Mock FOGIS API Server for Integration Testing

Provides a lightweight mock of the FOGIS API to replace the unavailable GHCR.
Supports match data endpoints with configurable scenarios for testing.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)


class MockFOGISAPI:
    """Mock FOGIS API with configurable test scenarios."""

    def __init__(self):
        self.scenarios = self._load_test_scenarios()
        self.current_scenario = "default"
        self.request_count = 0

    def _load_test_scenarios(self) -> Dict[str, Any]:
        """Load test scenarios for different testing needs."""
        base_date = datetime.now()

        return {
            "default": {
                "matches": [
                    {
                        "match_id": "MOCK001",
                        "home_team": "Mock Team A",
                        "away_team": "Mock Team B",
                        "date": (base_date + timedelta(days=7)).strftime("%Y-%m-%d"),
                        "time": "15:00",
                        "venue": "Mock Stadium A",
                        "referee": "Mock Referee 1",
                        "assistant_referees": ["Mock Assistant 1", "Mock Assistant 2"],
                        "competition": "Mock League",
                        "round": "Round 1",
                    },
                    {
                        "match_id": "MOCK002",
                        "home_team": "Mock Team C",
                        "away_team": "Mock Team D",
                        "date": (base_date + timedelta(days=14)).strftime("%Y-%m-%d"),
                        "time": "17:30",
                        "venue": "Mock Stadium B",
                        "referee": "Mock Referee 2",
                        "assistant_referees": ["Mock Assistant 3", "Mock Assistant 4"],
                        "competition": "Mock Cup",
                        "round": "Quarter Final",
                    },
                ],
                "metadata": {
                    "total_matches": 2,
                    "last_updated": base_date.isoformat(),
                    "source": "mock_api",
                },
            },
            "change_detection": {
                "matches": [
                    {
                        "match_id": "MOCK001",
                        "home_team": "Mock Team A",
                        "away_team": "Mock Team B",
                        "date": (base_date + timedelta(days=7)).strftime("%Y-%m-%d"),
                        "time": "16:00",  # Changed time
                        "venue": "Mock Stadium A - Updated",  # Changed venue
                        "referee": "Mock Referee 1",
                        "assistant_referees": ["Mock Assistant 1", "Mock Assistant 2"],
                        "competition": "Mock League",
                        "round": "Round 1",
                    },
                    {
                        "match_id": "MOCK003",  # New match
                        "home_team": "Mock Team E",
                        "away_team": "Mock Team F",
                        "date": (base_date + timedelta(days=21)).strftime("%Y-%m-%d"),
                        "time": "19:00",
                        "venue": "Mock Stadium C",
                        "referee": "Mock Referee 3",
                        "assistant_referees": ["Mock Assistant 5", "Mock Assistant 6"],
                        "competition": "Mock League",
                        "round": "Round 2",
                    },
                ],
                "metadata": {
                    "total_matches": 2,
                    "last_updated": (base_date + timedelta(hours=1)).isoformat(),
                    "source": "mock_api",
                },
            },
            "empty": {
                "matches": [],
                "metadata": {
                    "total_matches": 0,
                    "last_updated": base_date.isoformat(),
                    "source": "mock_api",
                },
            },
            "error": {
                "error": "Mock API Error",
                "status": "error",
                "message": "Simulated API error for testing error handling",
            },
        }

    def get_matches(self, scenario: Optional[str] = None) -> Dict[str, Any]:
        """Get matches for the specified scenario."""
        scenario_name = scenario or self.current_scenario
        self.request_count += 1

        logger.info(
            f"Serving matches for scenario: {scenario_name} "
            f"(request #{self.request_count})"
        )

        if scenario_name not in self.scenarios:
            return {
                "error": f"Unknown scenario: {scenario_name}",
                "available_scenarios": list(self.scenarios.keys()),
            }

        return self.scenarios[scenario_name]

    def set_scenario(self, scenario: str) -> bool:
        """Set the current scenario."""
        if scenario in self.scenarios:
            self.current_scenario = scenario
            logger.info(f"Switched to scenario: {scenario}")
            return True
        return False


# Global mock API instance
mock_api = MockFOGISAPI()


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify(
        {
            "status": "healthy",
            "service": "mock-fogis-api",
            "timestamp": datetime.now().isoformat(),
            "current_scenario": mock_api.current_scenario,
            "request_count": mock_api.request_count,
        }
    )


@app.route("/api/matches", methods=["GET"])
def get_matches():
    """Get matches endpoint - main FOGIS API simulation."""
    scenario = request.args.get("scenario", mock_api.current_scenario)

    # Simulate API delay
    import time

    time.sleep(0.1)

    data = mock_api.get_matches(scenario)

    # Handle error scenarios
    if "error" in data:
        return jsonify(data), 500

    return jsonify(data)


@app.route("/api/matches/<match_id>", methods=["GET"])
def get_match_details(match_id: str):
    """Get specific match details."""
    data = mock_api.get_matches()

    if "matches" in data:
        for match in data["matches"]:
            if match["match_id"] == match_id:
                return jsonify(match)

    return jsonify({"error": f"Match {match_id} not found"}), 404


@app.route("/api/scenarios", methods=["GET"])
def list_scenarios():
    """List available test scenarios."""
    return jsonify(
        {
            "current_scenario": mock_api.current_scenario,
            "available_scenarios": list(mock_api.scenarios.keys()),
            "request_count": mock_api.request_count,
        }
    )


@app.route("/api/scenarios/<scenario>", methods=["POST"])
def set_scenario(scenario: str):
    """Set the current test scenario."""
    if mock_api.set_scenario(scenario):
        return jsonify(
            {
                "status": "success",
                "current_scenario": mock_api.current_scenario,
                "message": f"Switched to scenario: {scenario}",
            }
        )
    else:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"Unknown scenario: {scenario}",
                    "available_scenarios": list(mock_api.scenarios.keys()),
                }
            ),
            400,
        )


@app.route("/api/reset", methods=["POST"])
def reset_api():
    """Reset the mock API state."""
    mock_api.current_scenario = "default"
    mock_api.request_count = 0

    return jsonify(
        {
            "status": "reset",
            "current_scenario": mock_api.current_scenario,
            "request_count": mock_api.request_count,
        }
    )


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get API usage statistics."""
    return jsonify(
        {
            "request_count": mock_api.request_count,
            "current_scenario": mock_api.current_scenario,
            "uptime": "mock_uptime",
            "scenarios": list(mock_api.scenarios.keys()),
        }
    )


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return (
        jsonify(
            {
                "error": "Endpoint not found",
                "available_endpoints": [
                    "/health",
                    "/api/matches",
                    "/api/matches/<match_id>",
                    "/api/scenarios",
                    "/api/scenarios/<scenario>",
                    "/api/reset",
                    "/api/stats",
                ],
            }
        ),
        404,
    )


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error", "message": str(error)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    debug = os.getenv("FLASK_ENV") == "testing"

    logger.info(f"Starting Mock FOGIS API on port {port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Available scenarios: {list(mock_api.scenarios.keys())}")

    app.run(host="0.0.0.0", port=port, debug=debug)
