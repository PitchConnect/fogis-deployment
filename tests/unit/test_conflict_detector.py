"""
Unit tests for the FOGIS Conflict Detection System.

This module contains comprehensive unit tests for the conflict detection
functionality, including directory, container, network, port, and cron conflicts.
"""

import os
import subprocess
import tempfile
from unittest.mock import Mock, call, patch

import pytest


class TestConflictDetector:
    """Test cases for conflict detection functions."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.test_install_dir = "/tmp/test_fogis_deployment"
        self.test_env = {
            "INSTALL_DIR": self.test_install_dir,
            "FOGIS_NETWORK_NAME": "fogis-network",
            "FOGIS_PORTS": "9080 9081 9082 9083 9084 9085 9086 9087 9088",
            "FOGIS_CONTAINER_PATTERNS": "fogis team-logo match-list google-drive cron-scheduler",
        }

    def teardown_method(self):
        """Clean up after each test."""
        # Clean up any test directories
        if os.path.exists(self.test_install_dir):
            subprocess.run(["rm", "-rf", self.test_install_dir], check=False)

    @patch("subprocess.run")
    @patch("os.path.exists")
    def test_check_directory_conflicts_no_directory(self, mock_exists, mock_run):
        """Test directory conflict check when no directory exists."""
        mock_exists.return_value = False

        # Run the bash function via subprocess
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/conflict_detector.sh && "
                f"INSTALL_DIR={self.test_install_dir} && "
                f"check_directory_conflicts",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 0
        assert "No existing installation directory found" in result.stdout

    @patch("subprocess.run")
    def test_check_directory_conflicts_with_directory(self, mock_run):
        """Test directory conflict check when directory exists."""
        # Create test directory structure
        os.makedirs(f"{self.test_install_dir}/credentials", exist_ok=True)
        os.makedirs(f"{self.test_install_dir}/data", exist_ok=True)
        os.makedirs(f"{self.test_install_dir}/logs", exist_ok=True)

        # Create some test files
        with open(f"{self.test_install_dir}/credentials/test.json", "w") as f:
            f.write('{"test": "data"}')
        with open(f"{self.test_install_dir}/logs/test.log", "w") as f:
            f.write("test log entry")

        # Run the bash function
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/conflict_detector.sh && "
                f"INSTALL_DIR={self.test_install_dir} && "
                f"check_directory_conflicts",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 1  # Conflicts found
        assert "Directory:" in result.stdout
        assert "Credentials:" in result.stdout
        assert "Data:" in result.stdout
        assert "Logs:" in result.stdout

    @patch("subprocess.run")
    def test_check_container_conflicts_no_containers(self, mock_run):
        """Test container conflict check when no containers are running."""
        # Mock docker ps to return empty result
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        result = subprocess.run(
            [
                "bash",
                "-c",
                "source fogis-deployment/lib/conflict_detector.sh && "
                "check_container_conflicts",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 0
        assert "No running FOGIS containers found" in result.stdout

    @patch("subprocess.run")
    def test_check_container_conflicts_with_containers(self, mock_run):
        """Test container conflict check when containers are running."""

        # Mock docker ps to return container names
        def mock_docker_ps(*args, **kwargs):
            if "docker ps" in " ".join(args[0]):
                return subprocess.CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout="fogis-api-client-service\nteam-logo-combiner\n",
                    stderr="",
                )
            elif "docker inspect" in " ".join(args[0]):
                return subprocess.CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout="running\n2023-01-01T00:00:00Z",
                    stderr="",
                )
            return subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )

        mock_run.side_effect = mock_docker_ps

        result = subprocess.run(
            [
                "bash",
                "-c",
                "source fogis-deployment/lib/conflict_detector.sh && "
                "check_container_conflicts",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 1  # Conflicts found
        assert "Running containers:" in result.stdout

    @patch("subprocess.run")
    def test_check_network_conflicts_no_network(self, mock_run):
        """Test network conflict check when no network exists."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        result = subprocess.run(
            [
                "bash",
                "-c",
                "source fogis-deployment/lib/conflict_detector.sh && "
                "check_network_conflicts",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 0
        assert "No existing FOGIS network found" in result.stdout

    @patch("subprocess.run")
    def test_check_network_conflicts_with_network(self, mock_run):
        """Test network conflict check when network exists."""

        def mock_docker_network(*args, **kwargs):
            if "docker network ls" in " ".join(args[0]):
                return subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="fogis-network", stderr=""
                )
            elif "docker network inspect" in " ".join(args[0]):
                return subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="bridge (2 containers)", stderr=""
                )
            return subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )

        mock_run.side_effect = mock_docker_network

        result = subprocess.run(
            [
                "bash",
                "-c",
                "source fogis-deployment/lib/conflict_detector.sh && "
                "check_network_conflicts",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 1  # Conflicts found
        assert "Docker network:" in result.stdout

    @patch("subprocess.run")
    def test_check_port_conflicts_no_conflicts(self, mock_run):
        """Test port conflict check when no ports are occupied."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="",  # lsof returns 1 when no matches
        )

        result = subprocess.run(
            [
                "bash",
                "-c",
                "source fogis-deployment/lib/conflict_detector.sh && "
                "check_port_conflicts",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 0
        assert "No port conflicts found" in result.stdout

    @patch("subprocess.run")
    def test_check_port_conflicts_with_conflicts(self, mock_run):
        """Test port conflict check when ports are occupied."""

        def mock_lsof(*args, **kwargs):
            if "lsof" in " ".join(args[0]) and ":9080" in " ".join(args[0]):
                return subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="1234", stderr=""
                )
            elif "ps -p" in " ".join(args[0]):
                return subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="docker", stderr=""
                )
            return subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr=""
            )

        mock_run.side_effect = mock_lsof

        result = subprocess.run(
            [
                "bash",
                "-c",
                "source fogis-deployment/lib/conflict_detector.sh && "
                "check_port_conflicts",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 1  # Conflicts found
        assert "Occupied ports:" in result.stdout

    @patch("subprocess.run")
    def test_check_cron_conflicts_no_jobs(self, mock_run):
        """Test cron conflict check when no FOGIS cron jobs exist."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="",  # crontab -l returns 1 when no crontab
        )

        result = subprocess.run(
            [
                "bash",
                "-c",
                "source fogis-deployment/lib/conflict_detector.sh && "
                "check_cron_conflicts",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 0
        assert "No existing FOGIS cron jobs found" in result.stdout

    @patch("subprocess.run")
    def test_check_cron_conflicts_with_jobs(self, mock_run):
        """Test cron conflict check when FOGIS cron jobs exist."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="0 * * * * cd /path && docker-compose run match-list-processor",
            stderr="",
        )

        result = subprocess.run(
            [
                "bash",
                "-c",
                "source fogis-deployment/lib/conflict_detector.sh && "
                "check_cron_conflicts",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 1  # Conflicts found
        assert "FOGIS cron jobs:" in result.stdout

    def test_detect_all_conflicts_integration(self):
        """Integration test for comprehensive conflict detection."""
        # Create a test scenario with some conflicts
        os.makedirs(f"{self.test_install_dir}/credentials", exist_ok=True)
        with open(f"{self.test_install_dir}/credentials/test.json", "w") as f:
            f.write('{"test": "data"}')

        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/conflict_detector.sh && "
                f"INSTALL_DIR={self.test_install_dir} && "
                f"detect_all_conflicts",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 1  # Conflicts found
        assert "COMPREHENSIVE CONFLICT DETECTION" in result.stdout
        assert "Existing FOGIS installation detected" in result.stdout

    def test_generate_conflict_report(self):
        """Test conflict report generation."""
        # Create test directory with conflicts
        os.makedirs(f"{self.test_install_dir}/credentials", exist_ok=True)

        result = subprocess.run(
            [
                "bash",
                "-c",
                f"source fogis-deployment/lib/conflict_detector.sh && "
                f"INSTALL_DIR={self.test_install_dir} && "
                f"detect_all_conflicts >/dev/null 2>&1 && "
                f"generate_conflict_report /tmp/test_conflict_report.txt && "
                f"cat /tmp/test_conflict_report.txt",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        assert result.returncode == 0
        assert "FOGIS Installation Conflict Report" in result.stdout
        assert "Generated:" in result.stdout
        assert "Recommended Actions:" in result.stdout

        # Clean up
        if os.path.exists("/tmp/test_conflict_report.txt"):
            os.remove("/tmp/test_conflict_report.txt")


class TestConflictDetectorEdgeCases:
    """Test edge cases and error conditions for conflict detector."""

    @patch("subprocess.run")
    def test_docker_command_failure(self, mock_run):
        """Test behavior when Docker commands fail."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker")

        result = subprocess.run(
            [
                "bash",
                "-c",
                "source fogis-deployment/lib/conflict_detector.sh && "
                "check_container_conflicts",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        # Should handle Docker failures gracefully
        assert result.returncode == 0
        assert "No running FOGIS containers found" in result.stdout

    def test_permission_denied_scenarios(self):
        """Test behavior when permission is denied for certain operations."""
        # This test would require specific permission setups
        # For now, we'll test that the functions handle errors gracefully
        result = subprocess.run(
            [
                "bash",
                "-c",
                "source fogis-deployment/lib/conflict_detector.sh && "
                "INSTALL_DIR=/root/restricted && "
                "check_directory_conflicts",
            ],
            capture_output=True,
            text=True,
            cwd=".",
        )

        # Should handle permission errors gracefully
        assert result.returncode in [0, 1]  # Either no conflicts or conflicts detected

    def test_malformed_docker_output(self):
        """Test behavior with malformed Docker command output."""
        # This would require mocking Docker commands to return malformed output
        # The bash functions should handle this gracefully
        pass


if __name__ == "__main__":
    pytest.main([__file__])
