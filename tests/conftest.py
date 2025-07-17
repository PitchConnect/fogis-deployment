"""
Shared test fixtures and configuration for FOGIS Multi-Platform Installation System tests.

This module provides common test fixtures, mock objects, and utilities
used across unit, integration, and end-to-end tests.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import modules under test
from platform_manager import PlatformInfo  # noqa: E402


@pytest.fixture
def mock_platform_info():
    """Create a mock PlatformInfo object for testing."""
    return PlatformInfo(
        os_name="linux",
        distribution="Ubuntu",
        version="22.04",
        architecture="x86_64",
        package_manager="apt",
        is_wsl2=False,
        kernel_version="5.15.0",
    )


@pytest.fixture
def mock_wsl2_platform_info():
    """Create a mock WSL2 PlatformInfo object for testing."""
    return PlatformInfo(
        os_name="linux",
        distribution="Ubuntu",
        version="22.04",
        architecture="x86_64",
        package_manager="apt",
        is_wsl2=True,
        kernel_version="5.15.0-microsoft-standard",
    )


@pytest.fixture
def mock_macos_platform_info():
    """Create a mock macOS PlatformInfo object for testing."""
    return PlatformInfo(
        os_name="darwin",
        distribution="macOS",
        version="13.0",
        architecture="arm64",
        package_manager="brew",
        is_wsl2=False,
        kernel_version="22.1.0",
    )


@pytest.fixture
def mock_arch_platform_info():
    """Create a mock Arch Linux PlatformInfo object for testing."""
    return PlatformInfo(
        os_name="linux",
        distribution="Arch Linux",
        version="rolling",
        architecture="x86_64",
        package_manager="pacman",
        is_wsl2=False,
        kernel_version="6.1.0",
    )


@pytest.fixture
def mock_alpine_platform_info():
    """Create a mock Alpine Linux PlatformInfo object for testing."""
    return PlatformInfo(
        os_name="linux",
        distribution="Alpine Linux",
        version="3.18",
        architecture="x86_64",
        package_manager="apk",
        is_wsl2=False,
        kernel_version="5.15.0",
    )


@pytest.fixture
def mock_centos_platform_info():
    """Create a mock CentOS PlatformInfo object for testing."""
    return PlatformInfo(
        os_name="linux",
        distribution="CentOS Linux",
        version="8",
        architecture="x86_64",
        package_manager="dnf",
        is_wsl2=False,
        kernel_version="4.18.0",
    )


@pytest.fixture
def mock_opensuse_platform_info():
    """Create a mock openSUSE PlatformInfo object for testing."""
    return PlatformInfo(
        os_name="linux",
        distribution="openSUSE Tumbleweed",
        version="20231201",
        architecture="x86_64",
        package_manager="zypper",
        is_wsl2=False,
        kernel_version="6.6.0",
    )


@pytest.fixture
def mock_subprocess_success():
    """Mock subprocess.run to always succeed."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="success", stderr="")
        yield mock_run


@pytest.fixture
def mock_subprocess_failure():
    """Mock subprocess.run to always fail."""
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")
        yield mock_run


@pytest.fixture
def mock_file_system():
    """Mock file system operations for testing."""
    with patch("pathlib.Path.exists") as mock_exists, patch(
        "builtins.open", create=True
    ) as mock_open:
        # Default behavior: files don't exist
        mock_exists.return_value = False

        yield {"exists": mock_exists, "open": mock_open}


class MockPackageManager:
    """Mock package manager for testing."""

    def __init__(self, should_succeed: bool = True):
        self.should_succeed = should_succeed
        self.installed_packages: set = set()
        self.update_called = False
        self.install_called = False

    def update_package_list(self) -> bool:
        self.update_called = True
        return self.should_succeed

    def install_package(self, package_name: str) -> bool:
        self.install_called = True
        if self.should_succeed:
            self.installed_packages.add(package_name)
        return self.should_succeed

    def is_package_installed(self, package_name: str) -> bool:
        return package_name in self.installed_packages

    def get_install_command(self, package_name: str) -> list:
        return ["mock", "install", package_name]

    def install_packages(self, package_names: list) -> bool:
        success = True
        for package in package_names:
            if not self.install_package(package):
                success = False
        return success

    def verify_prerequisites(self, packages: list) -> tuple:
        installed = [pkg for pkg in packages if self.is_package_installed(pkg)]
        missing = [pkg for pkg in packages if not self.is_package_installed(pkg)]
        return installed, missing


@pytest.fixture
def mock_package_manager_success():
    """Create a mock package manager that succeeds."""
    return MockPackageManager(should_succeed=True)


@pytest.fixture
def mock_package_manager_failure():
    """Create a mock package manager that fails."""
    return MockPackageManager(should_succeed=False)


@pytest.fixture
def sample_os_release_ubuntu():
    """Sample /etc/os-release content for Ubuntu."""
    return """NAME="Ubuntu"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 22.04.3 LTS"
VERSION_ID="22.04"
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
VERSION_CODENAME=jammy
UBUNTU_CODENAME=jammy"""


@pytest.fixture
def sample_os_release_centos():
    """Sample /etc/os-release content for CentOS."""
    return '''NAME="CentOS Linux"
VERSION="8"
ID="centos"
ID_LIKE="rhel fedora"
VERSION_ID="8"
PLATFORM_ID="platform:el8"
PRETTY_NAME="CentOS Linux 8"
ANSI_COLOR="0;31"
CPE_NAME="cpe:/o:centos:centos:8"
HOME_URL="https://www.centos.org/"
BUG_REPORT_URL="https://bugs.centos.org/"
CENTOS_MANTISBT_PROJECT="CentOS-8"
CENTOS_MANTISBT_PROJECT_VERSION="8"'''


@pytest.fixture
def sample_proc_version_wsl2():
    """Sample /proc/version content for WSL2."""
    return "Linux version 5.15.90.1-microsoft-standard-WSL2 (oe-user@oe-host) (x86_64-msft-linux-gcc (GCC) 9.3.0, GNU ld (GNU Binutils) 2.34.0.20200220) #1 SMP Fri Jan 27 02:56:13 UTC 2023"


@pytest.fixture
def sample_proc_version_native():
    """Sample /proc/version content for native Linux."""
    return "Linux version 5.15.0-91-generic (buildd@lcy02-amd64-044) (gcc (Ubuntu 9.4.0-1ubuntu1~20.04.2) 9.4.0, GNU ld (GNU Binutils for Ubuntu) 2.34) #101-Ubuntu SMP Tue Nov 14 13:30:08 UTC 2023"


# Test markers for categorizing tests
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line(
        "markers", "requires_network: mark test as requiring network access"
    )
    config.addinivalue_line("markers", "requires_docker: mark test as requiring Docker")
    config.addinivalue_line(
        "markers", "platform_specific: mark test as platform-specific"
    )
