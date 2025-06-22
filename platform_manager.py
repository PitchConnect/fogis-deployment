#!/usr/bin/env python3
"""
FOGIS Multi-Platform Installation System

This module provides comprehensive platform detection and package management
capabilities for the FOGIS deployment system across multiple operating systems.

Features:
- Automatic platform detection (Linux, macOS, Windows/WSL2)
- Multi-package manager support (apt, yum/dnf, pacman, brew, apk, zypper)
- Cross-platform package name resolution
- Prerequisite verification and installation
- Comprehensive error handling and logging

Author: The Augster
License: MIT
"""

import logging
import platform
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PlatformInfo:
    """Container for platform information."""
    os_name: str
    distribution: str
    version: str
    architecture: str
    package_manager: str
    is_wsl2: bool = False
    kernel_version: Optional[str] = None

    def __str__(self) -> str:
        """String representation of platform info."""
        base = f"{self.distribution} {self.version} ({self.architecture})"
        if self.is_wsl2:
            base += " [WSL2]"
        return base


class PackageManager(ABC):
    """Abstract base class for package managers."""

    def __init__(self):
        self.name = self.__class__.__name__.replace('PackageManager', '').lower()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def update_package_list(self) -> bool:
        """Update package repository lists."""
        pass

    @abstractmethod
    def install_package(self, package: str) -> bool:
        """Install a single package."""
        pass

    @abstractmethod
    def is_package_installed(self, package: str) -> bool:
        """Check if a package is installed."""
        pass

    @abstractmethod
    def get_install_command(self, package: str) -> List[str]:
        """Get the command to install a package."""
        pass

    def verify_prerequisites(self, packages: List[str]) -> Dict[str, bool]:
        """Verify if multiple packages are installed."""
        return {pkg: self.is_package_installed(pkg) for pkg in packages}

    def _run_command(self, command: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a command and return the result."""
        try:
            self.logger.debug(f"Running command: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {' '.join(command)}")
            self.logger.error(f"Error: {e}")
            raise


class AptPackageManager(PackageManager):
    """Package manager for Ubuntu/Debian systems using APT."""

    def __init__(self):
        super().__init__()
        self.name = "apt"

    def update_package_list(self) -> bool:
        """Update APT package lists."""
        try:
            self._run_command(["sudo", "apt", "update"])
            return True
        except subprocess.CalledProcessError:
            return False

    def install_package(self, package: str) -> bool:
        """Install a package using APT."""
        try:
            self._run_command(["sudo", "apt", "install", "-y", package])
            return True
        except subprocess.CalledProcessError:
            return False

    def is_package_installed(self, package: str) -> bool:
        """Check if a package is installed using dpkg."""
        try:
            result = self._run_command(["dpkg", "-l", package], check=False)
            return result.returncode == 0
        except Exception:
            return False

    def get_install_command(self, package: str) -> List[str]:
        """Get APT install command."""
        return ["sudo", "apt", "install", "-y", package]


class YumPackageManager(PackageManager):
    """Package manager for CentOS/RHEL/Fedora systems using YUM/DNF."""

    def __init__(self):
        super().__init__()
        self.name = "yum/dnf"
        # Prefer DNF over YUM if available
        try:
            subprocess.run(["which", "dnf"], check=True, capture_output=True)
            self.cmd = "dnf"
        except subprocess.CalledProcessError:
            self.cmd = "yum"

    def update_package_list(self) -> bool:
        """Update YUM/DNF package lists."""
        try:
            self._run_command(["sudo", self.cmd, "check-update"])
            return True
        except subprocess.CalledProcessError:
            # check-update returns 100 if updates are available, which is normal
            return True

    def install_package(self, package: str) -> bool:
        """Install a package using YUM/DNF."""
        try:
            self._run_command(["sudo", self.cmd, "install", "-y", package])
            return True
        except subprocess.CalledProcessError:
            return False

    def is_package_installed(self, package: str) -> bool:
        """Check if a package is installed using rpm."""
        try:
            result = self._run_command(["rpm", "-q", package], check=False)
            return result.returncode == 0
        except Exception:
            return False

    def get_install_command(self, package: str) -> List[str]:
        """Get YUM/DNF install command."""
        return ["sudo", self.cmd, "install", "-y", package]


class PacmanPackageManager(PackageManager):
    """Package manager for Arch Linux systems using Pacman."""

    def __init__(self):
        super().__init__()
        self.name = "pacman"

    def update_package_list(self) -> bool:
        """Update Pacman package lists."""
        try:
            self._run_command(["sudo", "pacman", "-Sy"])
            return True
        except subprocess.CalledProcessError:
            return False

    def install_package(self, package: str) -> bool:
        """Install a package using Pacman."""
        try:
            self._run_command(["sudo", "pacman", "-S", "--noconfirm", package])
            return True
        except subprocess.CalledProcessError:
            return False

    def is_package_installed(self, package: str) -> bool:
        """Check if a package is installed using pacman."""
        try:
            result = self._run_command(["pacman", "-Q", package], check=False)
            return result.returncode == 0
        except Exception:
            return False

    def get_install_command(self, package: str) -> List[str]:
        """Get Pacman install command."""
        return ["sudo", "pacman", "-S", "--noconfirm", package]


class BrewPackageManager(PackageManager):
    """Package manager for macOS systems using Homebrew."""

    def __init__(self):
        super().__init__()
        self.name = "brew"

    def update_package_list(self) -> bool:
        """Update Homebrew package lists."""
        try:
            self._run_command(["brew", "update"])
            return True
        except subprocess.CalledProcessError:
            return False

    def install_package(self, package: str) -> bool:
        """Install a package using Homebrew."""
        try:
            self._run_command(["brew", "install", package])
            return True
        except subprocess.CalledProcessError:
            return False

    def is_package_installed(self, package: str) -> bool:
        """Check if a package is installed using brew."""
        try:
            result = self._run_command(["brew", "list", package], check=False)
            return result.returncode == 0
        except Exception:
            return False

    def get_install_command(self, package: str) -> List[str]:
        """Get Homebrew install command."""
        return ["brew", "install", package]


class ApkPackageManager(PackageManager):
    """Package manager for Alpine Linux systems using APK."""

    def __init__(self):
        super().__init__()
        self.name = "apk"

    def update_package_list(self) -> bool:
        """Update APK package lists."""
        try:
            self._run_command(["sudo", "apk", "update"])
            return True
        except subprocess.CalledProcessError:
            return False

    def install_package(self, package: str) -> bool:
        """Install a package using APK."""
        try:
            self._run_command(["sudo", "apk", "add", package])
            return True
        except subprocess.CalledProcessError:
            return False

    def is_package_installed(self, package: str) -> bool:
        """Check if a package is installed using apk."""
        try:
            result = self._run_command(["apk", "info", "-e", package], check=False)
            return result.returncode == 0
        except Exception:
            return False

    def get_install_command(self, package: str) -> List[str]:
        """Get APK install command."""
        return ["sudo", "apk", "add", package]


class ZypperPackageManager(PackageManager):
    """Package manager for openSUSE systems using Zypper."""

    def __init__(self):
        super().__init__()
        self.name = "zypper"

    def update_package_list(self) -> bool:
        """Update Zypper package lists."""
        try:
            self._run_command(["sudo", "zypper", "refresh"])
            return True
        except subprocess.CalledProcessError:
            return False

    def install_package(self, package: str) -> bool:
        """Install a package using Zypper."""
        try:
            self._run_command(["sudo", "zypper", "install", "-y", package])
            return True
        except subprocess.CalledProcessError:
            return False

    def is_package_installed(self, package: str) -> bool:
        """Check if a package is installed using zypper."""
        try:
            result = self._run_command(["zypper", "search", "-i", package], check=False)
            return result.returncode == 0 and package in result.stdout
        except Exception:
            return False

    def get_install_command(self, package: str) -> List[str]:
        """Get Zypper install command."""
        return ["sudo", "zypper", "install", "-y", package]


class MultiPlatformManager:
    """Main orchestration class for multi-platform installation management."""

    def __init__(self):
        self.platform_info: Optional[PlatformInfo] = None
        self.package_manager: Optional[PackageManager] = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Package name mappings for different package managers
        self.package_mappings = {
            'git': {
                'apt': 'git',
                'yum': 'git',
                'dnf': 'git',
                'pacman': 'git',
                'brew': 'git',
                'apk': 'git',
                'zypper': 'git'
            },
            'docker': {
                'apt': 'docker.io',
                'yum': 'docker',
                'dnf': 'docker',
                'pacman': 'docker',
                'brew': 'docker',
                'apk': 'docker',
                'zypper': 'docker'
            },
            'python3': {
                'apt': 'python3',
                'yum': 'python3',
                'dnf': 'python3',
                'pacman': 'python',
                'brew': 'python@3.11',
                'apk': 'python3',
                'zypper': 'python3'
            }
        }

    def detect_platform(self) -> PlatformInfo:
        """Detect the current platform and return platform information."""
        os_name = platform.system().lower()
        architecture = platform.machine()

        if os_name == "linux":
            return self._detect_linux_platform(architecture)
        elif os_name == "darwin":
            return self._detect_macos_platform(architecture)
        elif os_name == "windows":
            return self._detect_windows_platform(architecture)
        else:
            raise RuntimeError(f"Unsupported operating system: {os_name}")

    def _detect_linux_platform(self, architecture: str) -> PlatformInfo:
        """Detect Linux distribution and package manager."""
        distribution = "Unknown"
        version = "Unknown"
        package_manager = "unknown"
        kernel_version = platform.release()
        is_wsl2 = self._detect_wsl2()

        # Try to read /etc/os-release
        try:
            with open('/etc/os-release', 'r') as f:
                os_release = f.read()

            for line in os_release.split('\n'):
                if line.startswith('NAME='):
                    distribution = line.split('=')[1].strip('"')
                elif line.startswith('VERSION_ID='):
                    version = line.split('=')[1].strip('"')

        except FileNotFoundError:
            self.logger.warning("Could not read /etc/os-release")

        # Determine package manager based on distribution
        if 'ubuntu' in distribution.lower() or 'debian' in distribution.lower():
            package_manager = "apt"
        elif 'centos' in distribution.lower() or 'rhel' in distribution.lower() or 'red hat' in distribution.lower():
            package_manager = "yum"
        elif 'fedora' in distribution.lower():
            package_manager = "dnf"
        elif 'arch' in distribution.lower():
            package_manager = "pacman"
        elif 'alpine' in distribution.lower():
            package_manager = "apk"
        elif 'opensuse' in distribution.lower() or 'suse' in distribution.lower():
            package_manager = "zypper"
        else:
            # Try to detect package manager by checking for commands
            package_manager = self._detect_package_manager()

        self.platform_info = PlatformInfo(
            os_name="linux",
            distribution=distribution,
            version=version,
            architecture=architecture,
            package_manager=package_manager,
            is_wsl2=is_wsl2,
            kernel_version=kernel_version
        )

        return self.platform_info

    def _detect_macos_platform(self, architecture: str) -> PlatformInfo:
        """Detect macOS version and set up Homebrew."""
        version = platform.mac_ver()[0]
        kernel_version = platform.release()

        self.platform_info = PlatformInfo(
            os_name="darwin",
            distribution="macOS",
            version=version,
            architecture=architecture,
            package_manager="brew",
            kernel_version=kernel_version
        )

        return self.platform_info

    def _detect_windows_platform(self, architecture: str) -> PlatformInfo:
        """Detect Windows platform (likely WSL2)."""
        version = platform.version()

        self.platform_info = PlatformInfo(
            os_name="windows",
            distribution="Windows",
            version=version,
            architecture=architecture,
            package_manager="unknown",
            is_wsl2=True
        )

        return self.platform_info

    def _detect_wsl2(self) -> bool:
        """Detect if running in WSL2 environment."""
        try:
            proc_version_path = Path('/proc/version')
            if proc_version_path.exists():
                with open(proc_version_path, 'r') as f:
                    content = f.read().lower()
                    return 'microsoft' in content and 'wsl2' in content
        except Exception:
            pass
        return False

    def _detect_package_manager(self) -> str:
        """Detect package manager by checking for available commands."""
        managers = [
            ("apt", "apt"),
            ("dnf", "dnf"),
            ("yum", "yum"),
            ("pacman", "pacman"),
            ("brew", "brew"),
            ("apk", "apk"),
            ("zypper", "zypper")
        ]

        for name, command in managers:
            try:
                subprocess.run(["which", command], check=True, capture_output=True)
                return name
            except subprocess.CalledProcessError:
                continue

        return "unknown"

    def get_package_manager(self) -> PackageManager:
        """Get the appropriate package manager for the current platform."""
        if not self.platform_info:
            self.detect_platform()

        if self.package_manager:
            return self.package_manager

        pm_name = self.platform_info.package_manager

        if pm_name == "apt":
            self.package_manager = AptPackageManager()
        elif pm_name in ["yum", "dnf"]:
            self.package_manager = YumPackageManager()
        elif pm_name == "pacman":
            self.package_manager = PacmanPackageManager()
        elif pm_name == "brew":
            self.package_manager = BrewPackageManager()
        elif pm_name == "apk":
            self.package_manager = ApkPackageManager()
        elif pm_name == "zypper":
            self.package_manager = ZypperPackageManager()
        else:
            raise RuntimeError(f"Unsupported package manager: {pm_name}")

        return self.package_manager

    def resolve_package_name(self, package: str) -> str:
        """Resolve package name for the current platform."""
        if not self.platform_info:
            self.detect_platform()

        pm_name = self.platform_info.package_manager

        if package in self.package_mappings:
            mapping = self.package_mappings[package]
            if pm_name in mapping:
                return mapping[pm_name]

        # Return original package name if no mapping found
        return package

    def verify_prerequisites(self, packages: Optional[List[str]] = None) -> Dict[str, bool]:
        """Verify if prerequisites are installed."""
        if packages is None:
            packages = ['git', 'docker', 'python3']

        package_manager = self.get_package_manager()
        result = {}

        for package in packages:
            resolved_name = self.resolve_package_name(package)
            result[package] = package_manager.is_package_installed(resolved_name)

        return result

    def install_prerequisites(self, packages: Optional[List[str]] = None) -> bool:
        """Install missing prerequisites."""
        if packages is None:
            packages = ['git', 'docker', 'python3']

        package_manager = self.get_package_manager()

        # Update package lists first
        self.logger.info("Updating package lists...")
        if not package_manager.update_package_list():
            self.logger.warning("Failed to update package lists")

        # Install packages
        success = True
        for package in packages:
            resolved_name = self.resolve_package_name(package)

            if not package_manager.is_package_installed(resolved_name):
                self.logger.info(f"Installing {package} ({resolved_name})...")
                if not package_manager.install_package(resolved_name):
                    self.logger.error(f"Failed to install {package}")
                    success = False
                else:
                    self.logger.info(f"Successfully installed {package}")
            else:
                self.logger.info(f"{package} is already installed")

        return success


if __name__ == "__main__":
    # Basic functionality test when run directly
    print("=== FOGIS Multi-Platform Installation System ===")
    print()
    
    manager = MultiPlatformManager()
    platform_info = manager.detect_platform()
    
    print("Platform Information:")
    print(f"  OS: {platform_info.os_name.title()}")
    print(f"  Distribution: {platform_info.distribution}")
    print(f"  Version: {platform_info.version}")
    print(f"  Architecture: {platform_info.architecture}")
    print(f"  Package Manager: {platform_info.package_manager}")
    if platform_info.kernel_version:
        print(f"  Kernel: {platform_info.kernel_version}")
    print()
    
    print("Checking prerequisites...")
    prereqs = manager.verify_prerequisites()
    
    for package, installed in prereqs.items():
        status = "✓" if installed else "✗"
        print(f"  {status} {package}")
