"""Tests for the app module."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.app.config["TESTING"] = True
    with app.app.test_client() as test_client:
        yield test_client


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_health_endpoint(client):
    """Test the health endpoint."""
    # Mock os.path.exists to return True for the data directory check
    # Mock get_version to return a test version
    with patch("os.path.exists", return_value=True), patch(
        "app.get_version", return_value="test-version"
    ):
        response = client.get("/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert "version" in data
        assert data["version"] == "test-version"
        assert "environment" in data


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_sync_endpoint_success(client):
    """Test the sync endpoint with a successful sync."""
    # Mock the subprocess.run function
    with patch("subprocess.run") as mock_run:
        # Configure the mock for success
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Sync completed successfully"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        # Mock the environment variables
        with patch.dict("os.environ", {"PYTHONPATH": "/app"}):
            # Call the endpoint
            response = client.post("/sync")

            # Verify the response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "success"
            assert data["message"] == "FOGIS sync completed successfully"


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_sync_endpoint_failure(client):
    """Test the sync endpoint with a failed sync."""
    # Mock the subprocess.run function
    with patch("subprocess.run") as mock_run:
        # Configure the mock for failure
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = ""
        mock_process.stderr = "Error during sync"
        mock_run.return_value = mock_process

        # Mock the environment variables
        with patch.dict("os.environ", {"PYTHONPATH": "/app"}):
            # Call the endpoint
            response = client.post("/sync")

            # Verify the response
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data["status"] == "error"
            assert data["message"] == "FOGIS sync failed"
            assert data["error"] == "Error during sync"


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_health_endpoint_no_data_directory(client):
    """Test health check when data directory doesn't exist."""
    with patch("os.path.exists", return_value=False):
        response = client.get("/health")
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "Data directory not accessible" in data["message"]


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_health_endpoint_no_token_file(client):
    """Test health check when OAuth token doesn't exist in any location."""

    def mock_exists_side_effect(path):
        # Data directory exists
        if path == "data":
            return True
        # All token locations return False
        if "token.json" in path:
            return False
        # Enhanced logging may check log directories - allow them to exist
        return True

    with patch("os.path.exists", side_effect=mock_exists_side_effect):
        with patch("app.get_version", return_value="test-version"):
            response = client.get("/health")
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "initializing"
            assert data["auth_status"] == "initializing"
            assert "OAuth token not found" in data["message"]
            assert "checked_locations" in data
            assert "auth_url" in data
            assert data["auth_url"] == "http://localhost:9083/authorize"
            assert "note" in data


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_health_endpoint_token_in_environment_path(client):
    """Test health check when token exists in environment variable path (preferred location)."""

    def mock_exists_side_effect(path):
        # Data directory exists
        if path == "data":
            return True
        # Environment variable token path exists (actual default value)
        if path == "/app/credentials/tokens/calendar/token.json":
            return True
        # Enhanced logging may check log directories - allow them to exist
        return True

    with patch.dict(
        os.environ,
        {"GOOGLE_CALENDAR_TOKEN_FILE": "/app/credentials/tokens/calendar/token.json"},
    ):
        with patch("os.path.exists", side_effect=mock_exists_side_effect):
            with patch("app.get_version", return_value="test-version"):
                response = client.get("/health")
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["status"] == "healthy"
                assert data["auth_status"] == "authenticated"
                assert (
                    data["token_location"]
                    == "/app/credentials/tokens/calendar/token.json"
                )
            assert data["version"] == "test-version"
            assert "environment" in data


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_health_endpoint_token_in_legacy_path(client):
    """Test health check when token exists in legacy data directory."""

    def mock_exists_side_effect(path):
        # Data directory exists
        if path == "data":
            return True
        # Environment variable token path doesn't exist (actual default value)
        if path == "/app/credentials/tokens/calendar/token.json":
            return False
        # Legacy token path exists
        if path == "/app/data/token.json":
            return True
        # Enhanced logging may check log directories - allow them to exist
        return True

    with patch.dict(
        os.environ,
        {"GOOGLE_CALENDAR_TOKEN_FILE": "/app/credentials/tokens/calendar/token.json"},
    ):
        with patch("os.path.exists", side_effect=mock_exists_side_effect):
            with patch("app.get_version", return_value="test-version"):
                response = client.get("/health")
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["status"] == "healthy"
                assert data["auth_status"] == "authenticated"
                assert data["token_location"] == "/app/data/token.json"
            assert data["version"] == "test-version"


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_health_endpoint_token_in_working_directory(client):
    """Test health check when token exists in working directory (backward compatibility)."""

    def mock_exists_side_effect(path):
        # Data directory exists
        if path == "data":
            return True
        # Environment variable and legacy token paths don't exist
        if path in [
            "/app/credentials/tokens/calendar/token.json",
            "/app/data/token.json",
        ]:
            return False
        # Working directory token path exists
        if path == "/app/token.json":
            return True
        # Enhanced logging may check log directories - allow them to exist
        return True

    with patch.dict(
        os.environ,
        {"GOOGLE_CALENDAR_TOKEN_FILE": "/app/credentials/tokens/calendar/token.json"},
    ):
        with patch("os.path.exists", side_effect=mock_exists_side_effect):
            with patch("app.get_version", return_value="test-version"):
                response = client.get("/health")
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["status"] == "healthy"
                assert data["auth_status"] == "authenticated"
                assert data["token_location"] == "/app/token.json"
            assert data["version"] == "test-version"


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_health_endpoint_with_custom_environment_variable(client):
    """Test health check with custom GOOGLE_CALENDAR_TOKEN_FILE environment variable."""
    custom_token_path = "/custom/path/to/token.json"

    def mock_exists_side_effect(path):
        # Data directory exists
        if path == "data":
            return True
        # Custom environment variable token path exists
        if path == custom_token_path:
            return True
        # Enhanced logging may check log directories - allow them to exist
        return True

    with patch.dict("os.environ", {"GOOGLE_CALENDAR_TOKEN_FILE": custom_token_path}):
        with patch("os.path.exists", side_effect=mock_exists_side_effect):
            with patch("app.get_version", return_value="test-version"):
                response = client.get("/health")
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["status"] == "healthy"
                assert data["auth_status"] == "authenticated"
                assert data["token_location"] == custom_token_path
                assert data["version"] == "test-version"


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_health_endpoint_exception(client):
    """Test health check when an exception occurs."""
    with patch("os.path.exists", side_effect=Exception("Test exception")):
        response = client.get("/health")
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "Test exception" in data["message"]


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_sync_endpoint_with_credentials(client):
    """Test sync endpoint with FOGIS credentials."""
    with patch("subprocess.run") as mock_run:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Sync completed"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        response = client.post(
            "/sync",
            json={"username": "test_user", "password": "test_pass", "delete": False},
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"

        # Verify subprocess was called with correct environment
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "FOGIS_USERNAME" in call_args.kwargs["env"]
        assert "FOGIS_PASSWORD" in call_args.kwargs["env"]


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_sync_endpoint_with_delete_flag(client):
    """Test sync endpoint with delete flag."""
    with patch("subprocess.run") as mock_run:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Sync completed"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        response = client.post("/sync", json={"delete": True})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"

        # Verify subprocess was called with --delete flag
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "--delete" in call_args[0][0]


@pytest.mark.unit
# pylint: disable=redefined-outer-name
def test_sync_endpoint_exception(client):
    """Test sync endpoint when an exception occurs."""
    with patch("subprocess.run", side_effect=Exception("Subprocess error")):
        response = client.post("/sync")
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "Error during FOGIS sync" in data["message"]
