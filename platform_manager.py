#!/usr/bin/env python3
"""
FOGIS Multi-Platform Installation System - Platform Manager

This module provides comprehensive platform detection and package management
abstraction for installing FOGIS across multiple operating systems and distributions.

Supported Platforms:
- Ubuntu/Debian (apt)
- CentOS/RHEL/Fedora (yum/dnf)
- Arch Linux (pacman)
- Alpine Linux (apk)
- openSUSE (zypper)
- macOS (homebrew)
- WSL2 (Windows Subsystem for Linux)

Author: The Augster
License: MIT
"""

import logging
import os
import platform
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PlatformInfo:
    """Structured platform information container."""
    
    os_name: str
    distribution: str
    version: str
    architecture: str
    package_manager: str
    is_wsl2: bool = False
    kernel_version: Optional[str] = None
    
    def __str__(self) -> str:
        """Human-readable platform description."""
        wsl_indicator = " (WSL2)" if self.is_wsl2 else ""
        return f"{self.distribution} {self.version} ({self.architecture}){wsl_indicator}"


class PackageManager(ABC):
    """Abstract base class for package manager implementations."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def update_package_list(self) -> bool:
        """Update the package manager's package list."""
        pass
    
    @abstractmethod
    def install_package(self, package_name: str) -> bool:
        """Install a single package."""
        pass
    
    @abstractmethod
    def is_package_installed(self, package_name: str) -> bool:
        """Check if a package is installed."""
        pass
    
    @abstractmethod
    def get_install_command(self, package_name: str) -> List[str]:
        """Get the command to install a package."""
        pass
    
    def install_packages(self, package_names: List[str]) -> bool:
        """Install multiple packages."""
        success = True
        for package in package_names:
            if not self.install_package(package):
                success = False
        return success
    
    def verify_prerequisites(self, packages: List[str]) -> Tuple[List[str], List[str]]:
        """Verify which packages are installed and which are missing."""
        installed = []
        missing = []
        
        for package in packages:
            if self.is_package_installed(package):
                installed.append(package)
            else:
                missing.append(package)
        
        return installed, missing


class AptPackageManager(PackageManager):
    """Package manager for Ubuntu/Debian systems using apt."""
    
    def __init__(self):
        super().__init__("apt")
    
    def update_package_list(self) -> bool:
        """Update apt package list."""
        try:
            result = subprocess.run(
                ["sudo", "apt", "update"],
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info("Package list updated successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to update package list: {e}")
            return False
    
    def install_package(self, package_name: str) -> bool:
        """Install package using apt."""
        try:
            result = subprocess.run(
                ["sudo", "apt", "install", "-y", package_name],
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info(f"Successfully installed {package_name}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install {package_name}: {e}")
            return False
    
    def is_package_installed(self, package_name: str) -> bool:
        """Check if package is installed using dpkg."""
        try:
            result = subprocess.run(
                ["dpkg", "-l", package_name],
                capture_output=True,
                text=True,
                check=True
            )
            return "ii" in result.stdout
        except subprocess.CalledProcessError:
            return False
    
    def get_install_command(self, package_name: str) -> List[str]:
        """Get apt install command."""
        return ["sudo", "apt", "install", "-y", package_name]


class YumPackageManager(PackageManager):
    """Package manager for CentOS/RHEL/Fedora systems using yum/dnf."""
    
    def __init__(self):
        super().__init__("yum/dnf")
        # Auto-detect yum vs dnf
        self.cmd = "dnf" if self._has_dnf() else "yum"
    
    def _has_dnf(self) -> bool:
        """Check if dnf is available."""
        try:
            subprocess.run(["which", "dnf"], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def update_package_list(self) -> bool:
        """Update package list."""
        try:
            subprocess.run(
                ["sudo", self.cmd, "check-update"],
                capture_output=True,
                text=True
            )
            self.logger.info("Package list updated successfully")
            return True
        except subprocess.CalledProcessError:
            # check-update returns non-zero when updates are available
            return True
    
    def install_package(self, package_name: str) -> bool:
        """Install package using yum/dnf."""
        try:
            result = subprocess.run(
                ["sudo", self.cmd, "install", "-y", package_name],
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info(f"Successfully installed {package_name}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install {package_name}: {e}")
            return False
    
    def is_package_installed(self, package_name: str) -> bool:
        """Check if package is installed using rpm."""
        try:
            result = subprocess.run(
                ["rpm", "-q", package_name],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def get_install_command(self, package_name: str) -> List[str]:
        """Get yum/dnf install command."""
        return ["sudo", self.cmd, "install", "-y", package_name]


class PacmanPackageManager(PackageManager):
    """Package manager for Arch Linux systems using pacman."""
    
    def __init__(self):
        super().__init__("pacman")
    
    def update_package_list(self) -> bool:
        """Update pacman package list."""
        try:
            result = subprocess.run(
                ["sudo", "pacman", "-Sy"],
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info("Package list updated successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to update package list: {e}")
            return False
    
    def install_package(self, package_name: str) -> bool:
        """Install package using pacman."""
        try:
            result = subprocess.run(
                ["sudo", "pacman", "-S", "--noconfirm", package_name],
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info(f"Successfully installed {package_name}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install {package_name}: {e}")
            return False
    
    def is_package_installed(self, package_name: str) -> bool:
        """Check if package is installed using pacman."""
        try:
            result = subprocess.run(
                ["pacman", "-Q", package_name],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def get_install_command(self, package_name: str) -> List[str]:
        """Get pacman install command."""
        return ["sudo", "pacman", "-S", "--noconfirm", package_name]


class BrewPackageManager(PackageManager):
    """Package manager for macOS systems using Homebrew."""
    
    def __init__(self):
        super().__init__("brew")
    
    def update_package_list(self) -> bool:
        """Update Homebrew package list."""
        try:
            result = subprocess.run(
                ["brew", "update"],
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info("Package list updated successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to update package list: {e}")
            return False
    
    def install_package(self, package_name: str) -> bool:
        """Install package using brew."""
        try:
            result = subprocess.run(
                ["brew", "install", package_name],
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info(f"Successfully installed {package_name}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install {package_name}: {e}")
            return False
    
    def is_package_installed(self, package_name: str) -> bool:
        """Check if package is installed using brew."""
        try:
            result = subprocess.run(
                ["brew", "list", package_name],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def get_install_command(self, package_name: str) -> List[str]:
        """Get brew install command."""
        return ["brew", "install", package_name]


class ApkPackageManager(PackageManager):
    """Package manager for Alpine Linux systems using apk."""

    def __init__(self):
        super().__init__("apk")

    def update_package_list(self) -> bool:
        """Update apk package list."""
        try:
            result = subprocess.run(
                ["sudo", "apk", "update"],
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info("Package list updated successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to update package list: {e}")
            return False

    def install_package(self, package_name: str) -> bool:
        """Install package using apk."""
        try:
            result = subprocess.run(
                ["sudo", "apk", "add", package_name],
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info(f"Successfully installed {package_name}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install {package_name}: {e}")
            return False

    def is_package_installed(self, package_name: str) -> bool:
        """Check if package is installed using apk."""
        try:
            result = subprocess.run(
                ["apk", "info", "-e", package_name],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def get_install_command(self, package_name: str) -> List[str]:
        """Get apk install command."""
        return ["sudo", "apk", "add", package_name]


class ZypperPackageManager(PackageManager):
    """Package manager for openSUSE systems using zypper."""

    def __init__(self):
        super().__init__("zypper")

    def update_package_list(self) -> bool:
        """Update zypper package list."""
        try:
            result = subprocess.run(
                ["sudo", "zypper", "refresh"],
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info("Package list updated successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to update package list: {e}")
            return False

    def install_package(self, package_name: str) -> bool:
        """Install package using zypper."""
        try:
            result = subprocess.run(
                ["sudo", "zypper", "install", "-y", package_name],
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info(f"Successfully installed {package_name}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install {package_name}: {e}")
            return False

    def is_package_installed(self, package_name: str) -> bool:
        """Check if package is installed using zypper."""
        try:
            result = subprocess.run(
                ["zypper", "search", "-i", package_name],
                capture_output=True,
                text=True,
                check=True
            )
            return package_name in result.stdout
        except subprocess.CalledProcessError:
            return False

    def get_install_command(self, package_name: str) -> List[str]:
        """Get zypper install command."""
        return ["sudo", "zypper", "install", "-y", package_name]


class MultiPlatformManager:
    """Main orchestration class for multi-platform installation management."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.platform_info: Optional[PlatformInfo] = None
        self.package_manager: Optional[PackageManager] = None

        # Cross-platform package mappings
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
        """Detect the current platform and return structured information."""
        if self.platform_info is not None:
            return self.platform_info

        os_name = platform.system().lower()
        architecture = platform.machine()
        kernel_version = platform.release()

        # Detect WSL2
        is_wsl2 = self._detect_wsl2()

        if os_name == "linux":
            distribution, version = self._detect_linux_distribution()
            package_manager = self._detect_package_manager()
        elif os_name == "darwin":
            distribution = "macOS"
            version = platform.mac_ver()[0]
            package_manager = "brew"
        else:
            distribution = "Unknown"
            version = "Unknown"
            package_manager = "unknown"

        self.platform_info = PlatformInfo(
            os_name=os_name,
            distribution=distribution,
            version=version,
            architecture=architecture,
            package_manager=package_manager,
            is_wsl2=is_wsl2,
            kernel_version=kernel_version
        )

        return self.platform_info

    def _detect_wsl2(self) -> bool:
        """Detect if running under WSL2."""
        try:
            with open('/proc/version', 'r') as f:
                version_info = f.read().lower()
                return 'microsoft' in version_info and 'wsl2' in version_info
        except (FileNotFoundError, PermissionError):
            return False

    def _detect_linux_distribution(self) -> Tuple[str, str]:
        """Detect Linux distribution and version."""
        # Try /etc/os-release first (most modern distributions)
        if Path('/etc/os-release').exists():
            return self._parse_os_release()

        # Fallback methods for older systems
        if Path('/etc/arch-release').exists():
            return "Arch Linux", "rolling"
        elif Path('/etc/alpine-release').exists():
            with open('/etc/alpine-release', 'r') as f:
                version = f.read().strip()
            return "Alpine Linux", version

        # Final fallback
        return "Unknown Linux", "Unknown"

    def _parse_os_release(self) -> Tuple[str, str]:
        """Parse /etc/os-release file."""
        distribution = "Unknown"
        version = "Unknown"

        try:
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    if line.startswith('NAME='):
                        distribution = line.split('=')[1].strip().strip('"')
                    elif line.startswith('VERSION_ID='):
                        version = line.split('=')[1].strip().strip('"')
        except (FileNotFoundError, PermissionError):
            pass

        return distribution, version

    def _detect_package_manager(self) -> str:
        """Detect the available package manager."""
        # Check for package managers in order of preference
        managers = [
            ("apt", ["apt", "--version"]),
            ("dnf", ["dnf", "--version"]),
            ("yum", ["yum", "--version"]),
            ("pacman", ["pacman", "--version"]),
            ("apk", ["apk", "--version"]),
            ("zypper", ["zypper", "--version"]),
            ("brew", ["brew", "--version"])
        ]

        for manager_name, check_cmd in managers:
            try:
                subprocess.run(check_cmd, capture_output=True, check=True)
                return manager_name
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        return "unknown"

    def get_package_manager(self) -> PackageManager:
        """Get the appropriate package manager instance."""
        if self.package_manager is not None:
            return self.package_manager

        platform_info = self.detect_platform()

        manager_map = {
            'apt': AptPackageManager,
            'yum': YumPackageManager,
            'dnf': YumPackageManager,
            'pacman': PacmanPackageManager,
            'brew': BrewPackageManager,
            'apk': ApkPackageManager,
            'zypper': ZypperPackageManager
        }

        manager_class = manager_map.get(platform_info.package_manager)
        if manager_class is None:
            raise RuntimeError(f"Unsupported package manager: {platform_info.package_manager}")

        self.package_manager = manager_class()
        return self.package_manager

    def resolve_package_name(self, generic_name: str) -> str:
        """Resolve a generic package name to platform-specific name."""
        platform_info = self.detect_platform()

        if generic_name not in self.package_mappings:
            return generic_name

        mapping = self.package_mappings[generic_name]
        return mapping.get(platform_info.package_manager, generic_name)

    def verify_prerequisites(self, packages: List[str] = None) -> Dict[str, bool]:
        """Verify that required packages are installed."""
        if packages is None:
            packages = ['git', 'docker', 'python3']

        package_manager = self.get_package_manager()
        results = {}

        for package in packages:
            platform_package = self.resolve_package_name(package)
            results[package] = package_manager.is_package_installed(platform_package)

        return results

    def install_prerequisites(self, packages: List[str] = None) -> bool:
        """Install required packages."""
        if packages is None:
            packages = ['git', 'docker', 'python3']

        package_manager = self.get_package_manager()

        # Update package list first
        if not package_manager.update_package_list():
            self.logger.warning("Failed to update package list, continuing anyway")

        success = True
        for package in packages:
            platform_package = self.resolve_package_name(package)
            if not package_manager.is_package_installed(platform_package):
                self.logger.info(f"Installing {package} ({platform_package})...")
                if not package_manager.install_package(platform_package):
                    success = False
            else:
                self.logger.info(f"{package} is already installed")

        return success

    def get_platform_summary(self) -> str:
        """Get a human-readable platform summary."""
        platform_info = self.detect_platform()

        summary = f"""Platform Information:
  OS: {platform_info.os_name.title()}
  Distribution: {platform_info.distribution}
  Version: {platform_info.version}
  Architecture: {platform_info.architecture}
  Package Manager: {platform_info.package_manager}
  Kernel: {platform_info.kernel_version}"""

        if platform_info.is_wsl2:
            summary += "\n  Environment: WSL2"

        return summary


if __name__ == "__main__":
    # Example usage
    manager = MultiPlatformManager()

    print("=== FOGIS Multi-Platform Installation System ===")
    print()
    print(manager.get_platform_summary())
    print()

    print("Checking prerequisites...")
    prereqs = manager.verify_prerequisites()
    for package, installed in prereqs.items():
        status = "✓" if installed else "✗"
        print(f"  {status} {package}")

    missing = [pkg for pkg, installed in prereqs.items() if not installed]
    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Run with --install to install missing packages")
    else:
        print("\n✓ All prerequisites are satisfied!")
