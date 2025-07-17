"""
Unit tests for the FOGIS Multi-Platform Installation System.

This module contains comprehensive unit tests for all components of the
platform manager, including platform detection, package managers, and
the main orchestration class.
"""

import subprocess
from unittest.mock import Mock, mock_open, patch

from platform_manager import (
    ApkPackageManager,
    AptPackageManager,
    BrewPackageManager,
    MultiPlatformManager,
    PacmanPackageManager,
    PlatformInfo,
    YumPackageManager,
    ZypperPackageManager,
)


class TestPlatformInfo:
    """Test cases for PlatformInfo dataclass."""

    def test_platform_info_creation(self):
        """Test creating a PlatformInfo object."""
        info = PlatformInfo(
            os_name="linux",
            distribution="Ubuntu",
            version="22.04",
            architecture="x86_64",
            package_manager="apt",
        )

        assert info.os_name == "linux"
        assert info.distribution == "Ubuntu"
        assert info.version == "22.04"
        assert info.architecture == "x86_64"
        assert info.package_manager == "apt"
        assert info.is_wsl2 is False
        assert info.kernel_version is None

    def test_platform_info_str_representation(self):
        """Test string representation of PlatformInfo."""
        info = PlatformInfo(
            os_name="linux",
            distribution="Ubuntu",
            version="22.04",
            architecture="x86_64",
            package_manager="apt",
        )

        expected = "Ubuntu 22.04 (x86_64)"
        assert str(info) == expected

    def test_platform_info_wsl2_indicator(self):
        """Test WSL2 indicator in string representation."""
        info = PlatformInfo(
            os_name="linux",
            distribution="Ubuntu",
            version="22.04",
            architecture="x86_64",
            package_manager="apt",
            is_wsl2=True,
        )

        expected = "Ubuntu 22.04 (x86_64) (WSL2)"
        assert str(info) == expected


class TestAptPackageManager:
    """Test cases for APT package manager."""

    def test_apt_manager_initialization(self):
        """Test APT package manager initialization."""
        manager = AptPackageManager()
        assert manager.name == "apt"

    @patch("subprocess.run")
    def test_apt_update_success(self, mock_run):
        """Test successful APT package list update."""
        mock_run.return_value = Mock(returncode=0)

        manager = AptPackageManager()
        result = manager.update_package_list()

        assert result is True
        mock_run.assert_called_once_with(
            ["sudo", "apt", "update"], capture_output=True, text=True, check=True
        )

    @patch("subprocess.run")
    def test_apt_update_failure(self, mock_run):
        """Test failed APT package list update."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "apt")

        manager = AptPackageManager()
        result = manager.update_package_list()

        assert result is False

    @patch("subprocess.run")
    def test_apt_install_success(self, mock_run):
        """Test successful APT package installation."""
        mock_run.return_value = Mock(returncode=0)

        manager = AptPackageManager()
        result = manager.install_package("git")

        assert result is True
        mock_run.assert_called_once_with(
            ["sudo", "apt", "install", "-y", "git"],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_apt_install_failure(self, mock_run):
        """Test failed APT package installation."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "apt")

        manager = AptPackageManager()
        result = manager.install_package("nonexistent-package")

        assert result is False

    @patch("subprocess.run")
    def test_apt_is_package_installed_true(self, mock_run):
        """Test APT package installation check - installed."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="ii  git  1:2.34.1-1ubuntu1.9  amd64  fast, scalable, distributed revision control system",
        )

        manager = AptPackageManager()
        result = manager.is_package_installed("git")

        assert result is True
        mock_run.assert_called_once_with(
            ["dpkg", "-l", "git"], capture_output=True, text=True, check=True
        )

    @patch("subprocess.run")
    def test_apt_is_package_installed_false(self, mock_run):
        """Test APT package installation check - not installed."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "dpkg")

        manager = AptPackageManager()
        result = manager.is_package_installed("nonexistent-package")

        assert result is False

    def test_apt_get_install_command(self):
        """Test APT install command generation."""
        manager = AptPackageManager()
        command = manager.get_install_command("git")

        expected = ["sudo", "apt", "install", "-y", "git"]
        assert command == expected


class TestYumPackageManager:
    """Test cases for YUM/DNF package manager."""

    @patch("subprocess.run")
    def test_yum_manager_initialization_with_dnf(self, mock_run):
        """Test YUM manager initialization when DNF is available."""
        mock_run.return_value = Mock(returncode=0)

        manager = YumPackageManager()
        assert manager.name == "yum/dnf"
        assert manager.cmd == "dnf"

    @patch("subprocess.run")
    def test_yum_manager_initialization_without_dnf(self, mock_run):
        """Test YUM manager initialization when DNF is not available."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "which")

        manager = YumPackageManager()
        assert manager.name == "yum/dnf"
        assert manager.cmd == "yum"

    @patch("subprocess.run")
    def test_yum_update_success(self, mock_run):
        """Test successful YUM package list update."""
        # First call for DNF detection
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "which"),  # DNF not available
            Mock(returncode=0),  # yum check-update
        ]

        manager = YumPackageManager()
        result = manager.update_package_list()

        assert result is True

    @patch("subprocess.run")
    def test_yum_install_success(self, mock_run):
        """Test successful YUM package installation."""
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "which"),  # DNF not available
            Mock(returncode=0),  # yum install
        ]

        manager = YumPackageManager()
        result = manager.install_package("git")

        assert result is True

    @patch("subprocess.run")
    def test_yum_is_package_installed_true(self, mock_run):
        """Test YUM package installation check - installed."""
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "which"),  # DNF not available
            Mock(returncode=0, stdout="git-2.39.3-1.el9_2.x86_64"),  # rpm query
        ]

        manager = YumPackageManager()
        result = manager.is_package_installed("git")

        assert result is True

    @patch("subprocess.run")
    def test_yum_is_package_installed_false(self, mock_run):
        """Test YUM package installation check - not installed."""
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "which"),  # DNF not available
            subprocess.CalledProcessError(1, "rpm"),  # package not found
        ]

        manager = YumPackageManager()
        result = manager.is_package_installed("nonexistent-package")

        assert result is False


class TestPacmanPackageManager:
    """Test cases for Pacman package manager."""

    def test_pacman_manager_initialization(self):
        """Test Pacman package manager initialization."""
        manager = PacmanPackageManager()
        assert manager.name == "pacman"

    @patch("subprocess.run")
    def test_pacman_update_success(self, mock_run):
        """Test successful Pacman package list update."""
        mock_run.return_value = Mock(returncode=0)

        manager = PacmanPackageManager()
        result = manager.update_package_list()

        assert result is True
        mock_run.assert_called_once_with(
            ["sudo", "pacman", "-Sy"], capture_output=True, text=True, check=True
        )

    @patch("subprocess.run")
    def test_pacman_install_success(self, mock_run):
        """Test successful Pacman package installation."""
        mock_run.return_value = Mock(returncode=0)

        manager = PacmanPackageManager()
        result = manager.install_package("git")

        assert result is True
        mock_run.assert_called_once_with(
            ["sudo", "pacman", "-S", "--noconfirm", "git"],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_pacman_is_package_installed_true(self, mock_run):
        """Test Pacman package installation check - installed."""
        mock_run.return_value = Mock(returncode=0, stdout="git 2.42.0-1")

        manager = PacmanPackageManager()
        result = manager.is_package_installed("git")

        assert result is True
        mock_run.assert_called_once_with(
            ["pacman", "-Q", "git"], capture_output=True, text=True, check=True
        )

    @patch("subprocess.run")
    def test_pacman_is_package_installed_false(self, mock_run):
        """Test Pacman package installation check - not installed."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "pacman")

        manager = PacmanPackageManager()
        result = manager.is_package_installed("nonexistent-package")

        assert result is False


class TestBrewPackageManager:
    """Test cases for Homebrew package manager."""

    def test_brew_manager_initialization(self):
        """Test Homebrew package manager initialization."""
        manager = BrewPackageManager()
        assert manager.name == "brew"

    @patch("subprocess.run")
    def test_brew_update_success(self, mock_run):
        """Test successful Homebrew package list update."""
        mock_run.return_value = Mock(returncode=0)

        manager = BrewPackageManager()
        result = manager.update_package_list()

        assert result is True
        mock_run.assert_called_once_with(
            ["brew", "update"], capture_output=True, text=True, check=True
        )

    @patch("subprocess.run")
    def test_brew_install_success(self, mock_run):
        """Test successful Homebrew package installation."""
        mock_run.return_value = Mock(returncode=0)

        manager = BrewPackageManager()
        result = manager.install_package("git")

        assert result is True
        mock_run.assert_called_once_with(
            ["brew", "install", "git"], capture_output=True, text=True, check=True
        )

    @patch("subprocess.run")
    def test_brew_is_package_installed_true(self, mock_run):
        """Test Homebrew package installation check - installed."""
        mock_run.return_value = Mock(returncode=0, stdout="git")

        manager = BrewPackageManager()
        result = manager.is_package_installed("git")

        assert result is True
        mock_run.assert_called_once_with(
            ["brew", "list", "git"], capture_output=True, text=True, check=True
        )

    @patch("subprocess.run")
    def test_brew_is_package_installed_false(self, mock_run):
        """Test Homebrew package installation check - not installed."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "brew")

        manager = BrewPackageManager()
        result = manager.is_package_installed("nonexistent-package")

        assert result is False


class TestApkPackageManager:
    """Test cases for APK package manager."""

    def test_apk_manager_initialization(self):
        """Test APK package manager initialization."""
        manager = ApkPackageManager()
        assert manager.name == "apk"

    @patch("subprocess.run")
    def test_apk_update_success(self, mock_run):
        """Test successful APK package list update."""
        mock_run.return_value = Mock(returncode=0)

        manager = ApkPackageManager()
        result = manager.update_package_list()

        assert result is True
        mock_run.assert_called_once_with(
            ["sudo", "apk", "update"], capture_output=True, text=True, check=True
        )

    @patch("subprocess.run")
    def test_apk_install_success(self, mock_run):
        """Test successful APK package installation."""
        mock_run.return_value = Mock(returncode=0)

        manager = ApkPackageManager()
        result = manager.install_package("git")

        assert result is True
        mock_run.assert_called_once_with(
            ["sudo", "apk", "add", "git"], capture_output=True, text=True, check=True
        )

    @patch("subprocess.run")
    def test_apk_is_package_installed_true(self, mock_run):
        """Test APK package installation check - installed."""
        mock_run.return_value = Mock(returncode=0, stdout="git-2.40.1-r0")

        manager = ApkPackageManager()
        result = manager.is_package_installed("git")

        assert result is True
        mock_run.assert_called_once_with(
            ["apk", "info", "-e", "git"], capture_output=True, text=True, check=True
        )

    @patch("subprocess.run")
    def test_apk_is_package_installed_false(self, mock_run):
        """Test APK package installation check - not installed."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "apk")

        manager = ApkPackageManager()
        result = manager.is_package_installed("nonexistent-package")

        assert result is False


class TestZypperPackageManager:
    """Test cases for Zypper package manager."""

    def test_zypper_manager_initialization(self):
        """Test Zypper package manager initialization."""
        manager = ZypperPackageManager()
        assert manager.name == "zypper"

    @patch("subprocess.run")
    def test_zypper_update_success(self, mock_run):
        """Test successful Zypper package list update."""
        mock_run.return_value = Mock(returncode=0)

        manager = ZypperPackageManager()
        result = manager.update_package_list()

        assert result is True
        mock_run.assert_called_once_with(
            ["sudo", "zypper", "refresh"], capture_output=True, text=True, check=True
        )

    @patch("subprocess.run")
    def test_zypper_install_success(self, mock_run):
        """Test successful Zypper package installation."""
        mock_run.return_value = Mock(returncode=0)

        manager = ZypperPackageManager()
        result = manager.install_package("git")

        assert result is True
        mock_run.assert_called_once_with(
            ["sudo", "zypper", "install", "-y", "git"],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_zypper_is_package_installed_true(self, mock_run):
        """Test Zypper package installation check - installed."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="i | git | package | 2.40.1 | x86_64 | openSUSE-Tumbleweed-Oss",
        )

        manager = ZypperPackageManager()
        result = manager.is_package_installed("git")

        assert result is True
        mock_run.assert_called_once_with(
            ["zypper", "search", "-i", "git"],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_zypper_is_package_installed_false(self, mock_run):
        """Test Zypper package installation check - not installed."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "zypper")

        manager = ZypperPackageManager()
        result = manager.is_package_installed("nonexistent-package")

        assert result is False


class TestMultiPlatformManager:
    """Test cases for MultiPlatformManager."""

    def test_multi_platform_manager_initialization(self):
        """Test MultiPlatformManager initialization."""
        manager = MultiPlatformManager()
        assert manager.platform_info is None
        assert manager.package_manager is None
        assert "git" in manager.package_mappings
        assert "docker" in manager.package_mappings
        assert "python3" in manager.package_mappings

    @patch("platform.system")
    @patch("platform.machine")
    @patch("platform.release")
    @patch("pathlib.Path.exists")
    def test_detect_platform_linux_ubuntu(
        self, mock_exists, mock_release, mock_machine, mock_system
    ):
        """Test platform detection for Ubuntu Linux."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "x86_64"
        mock_release.return_value = "5.15.0-91-generic"
        mock_exists.return_value = True

        with patch(
            "builtins.open", mock_open(read_data='NAME="Ubuntu"\nVERSION_ID="22.04"')
        ):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)

                manager = MultiPlatformManager()
                platform_info = manager.detect_platform()

                assert platform_info.os_name == "linux"
                assert platform_info.distribution == "Ubuntu"
                assert platform_info.version == "22.04"
                assert platform_info.architecture == "x86_64"
                assert platform_info.package_manager == "apt"
                assert platform_info.is_wsl2 is False

    @patch("platform.system")
    @patch("platform.mac_ver")
    def test_detect_platform_macos(self, mock_mac_ver, mock_system):
        """Test platform detection for macOS."""
        mock_system.return_value = "Darwin"
        mock_mac_ver.return_value = ("13.0", "", "")

        manager = MultiPlatformManager()
        platform_info = manager.detect_platform()

        assert platform_info.os_name == "darwin"
        assert platform_info.distribution == "macOS"
        assert platform_info.version == "13.0"
        assert platform_info.package_manager == "brew"

    @patch(
        "builtins.open",
        mock_open(read_data="Linux version 5.15.90.1-microsoft-standard-WSL2"),
    )
    @patch("pathlib.Path.exists")
    def test_detect_wsl2_true(self, mock_exists):
        """Test WSL2 detection - positive case."""
        mock_exists.return_value = True

        manager = MultiPlatformManager()
        result = manager._detect_wsl2()

        assert result is True

    @patch("builtins.open", mock_open(read_data="Linux version 5.15.0-91-generic"))
    @patch("pathlib.Path.exists")
    def test_detect_wsl2_false(self, mock_exists):
        """Test WSL2 detection - negative case."""
        mock_exists.return_value = True

        manager = MultiPlatformManager()
        result = manager._detect_wsl2()

        assert result is False

    @patch("pathlib.Path.exists")
    def test_detect_wsl2_file_not_found(self, mock_exists):
        """Test WSL2 detection when /proc/version doesn't exist."""
        mock_exists.return_value = False

        manager = MultiPlatformManager()
        result = manager._detect_wsl2()

        assert result is False

    def test_resolve_package_name_git(self):
        """Test package name resolution for git."""
        manager = MultiPlatformManager()
        manager.platform_info = PlatformInfo(
            os_name="linux",
            distribution="Ubuntu",
            version="22.04",
            architecture="x86_64",
            package_manager="apt",
        )

        result = manager.resolve_package_name("git")
        assert result == "git"

    def test_resolve_package_name_docker_apt(self):
        """Test package name resolution for docker on apt systems."""
        manager = MultiPlatformManager()
        manager.platform_info = PlatformInfo(
            os_name="linux",
            distribution="Ubuntu",
            version="22.04",
            architecture="x86_64",
            package_manager="apt",
        )

        result = manager.resolve_package_name("docker")
        assert result == "docker.io"

    def test_resolve_package_name_python3_brew(self):
        """Test package name resolution for python3 on brew systems."""
        manager = MultiPlatformManager()
        manager.platform_info = PlatformInfo(
            os_name="darwin",
            distribution="macOS",
            version="13.0",
            architecture="arm64",
            package_manager="brew",
        )

        result = manager.resolve_package_name("python3")
        assert result == "python@3.11"

    def test_resolve_package_name_unknown_package(self):
        """Test package name resolution for unknown package."""
        manager = MultiPlatformManager()
        manager.platform_info = PlatformInfo(
            os_name="linux",
            distribution="Ubuntu",
            version="22.04",
            architecture="x86_64",
            package_manager="apt",
        )

        result = manager.resolve_package_name("unknown-package")
        assert result == "unknown-package"

    @patch("platform_manager.MultiPlatformManager.get_package_manager")
    def test_verify_prerequisites_all_installed(self, mock_get_pm):
        """Test prerequisite verification when all packages are installed."""
        mock_pm = Mock()
        mock_pm.is_package_installed.return_value = True
        mock_get_pm.return_value = mock_pm

        manager = MultiPlatformManager()
        manager.platform_info = PlatformInfo(
            os_name="linux",
            distribution="Ubuntu",
            version="22.04",
            architecture="x86_64",
            package_manager="apt",
        )

        result = manager.verify_prerequisites(["git", "docker", "python3"])

        assert result == {"git": True, "docker": True, "python3": True}

    @patch("platform_manager.MultiPlatformManager.get_package_manager")
    def test_verify_prerequisites_some_missing(self, mock_get_pm):
        """Test prerequisite verification when some packages are missing."""
        mock_pm = Mock()

        def side_effect(*args, **kwargs):  # noqa: F841
            package = args[0]
            return package in ["git"]  # Only git is installed

        mock_pm.is_package_installed.side_effect = side_effect
        mock_get_pm.return_value = mock_pm

        manager = MultiPlatformManager()
        manager.platform_info = PlatformInfo(
            os_name="linux",
            distribution="Ubuntu",
            version="22.04",
            architecture="x86_64",
            package_manager="apt",
        )

        result = manager.verify_prerequisites(["git", "docker", "python3"])

        assert result == {"git": True, "docker": False, "python3": False}
