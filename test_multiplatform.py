#!/usr/bin/env python3
"""
Multi-platform compatibility testing for FOGIS deployment.
Tests AMD64 and ARM64 image availability and functionality.
"""

import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class MultiPlatformTester:
    """Test multi-platform Docker image compatibility."""

    def __init__(self):
        self.services = [
            "fogis-api-client-service",
            "team-logo-combiner",
            "match-list-processor",
            "match-list-change-detector",
            "fogis-calendar-phonebook-sync",
            "google-drive-service",
        ]
        self.registry = "ghcr.io/pitchconnect"
        self.platforms = ["linux/amd64", "linux/arm64"]
        self.results = {}

    def run_command(
        self, command: List[str], timeout: int = 60
    ) -> Tuple[int, str, str]:
        """Run a shell command and return exit code, stdout, stderr."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=Path(__file__).parent,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return -1, "", str(e)

    def detect_current_platform(self) -> str:
        """Detect the current platform architecture."""
        machine = platform.machine().lower()
        system = platform.system().lower()

        if system == "darwin":  # macOS
            if machine in ["arm64", "aarch64"]:
                return "darwin/arm64"
            else:
                return "darwin/amd64"
        elif system == "linux":
            if machine in ["arm64", "aarch64"]:
                return "linux/arm64"
            else:
                return "linux/amd64"
        else:
            return f"{system}/{machine}"

    def check_docker_buildx(self) -> bool:
        """Check if Docker Buildx is available for multi-platform support."""
        print("🔍 Checking Docker Buildx availability...")

        exit_code, stdout, stderr = self.run_command(["docker", "buildx", "version"])

        if exit_code != 0:
            print(f"❌ Docker Buildx not available: {stderr}")
            return False

        print(f"✅ Docker Buildx available: {stdout.strip()}")
        return True

    def check_image_manifest(self, image: str) -> Dict[str, bool]:
        """Check if image has multi-platform manifests."""
        print(f"🔍 Checking manifest for {image}...")

        platform_support = {}

        # Try to inspect the manifest
        exit_code, stdout, stderr = self.run_command(
            ["docker", "manifest", "inspect", f"{self.registry}/{image}:latest"]
        )

        if exit_code != 0:
            print(f"⚠️ Could not inspect manifest for {image}: {stderr}")
            # Try alternative method - pull and inspect
            return self.check_image_platforms_alternative(image)

        try:
            manifest = json.loads(stdout)

            # Check if it's a manifest list (multi-platform)
            if (
                manifest.get("mediaType")
                == "application/vnd.docker.distribution.manifest.list.v2+json"
            ):
                manifests = manifest.get("manifests", [])

                for platform in self.platforms:
                    platform_parts = platform.split("/")
                    os_name = platform_parts[0]
                    arch = platform_parts[1]

                    platform_found = any(
                        m.get("platform", {}).get("os") == os_name
                        and m.get("platform", {}).get("architecture") == arch
                        for m in manifests
                    )

                    platform_support[platform] = platform_found

                    if platform_found:
                        print(f"✅ {image} supports {platform}")
                    else:
                        print(f"❌ {image} missing {platform}")
            else:
                # Single platform image
                print(f"⚠️ {image} appears to be single-platform")
                platform_support = {p: False for p in self.platforms}

        except json.JSONDecodeError:
            print(f"❌ Could not parse manifest for {image}")
            platform_support = {p: False for p in self.platforms}

        return platform_support

    def check_image_platforms_alternative(self, image: str) -> Dict[str, bool]:
        """Alternative method to check platform support by attempting pulls."""
        print(f"🔄 Using alternative platform check for {image}...")

        platform_support = {}

        for platform in self.platforms:
            print(f"  Testing {platform}...")

            # Try to pull the specific platform
            exit_code, stdout, stderr = self.run_command(
                [
                    "docker",
                    "pull",
                    "--platform",
                    platform,
                    f"{self.registry}/{image}:latest",
                ],
                timeout=120,
            )

            if exit_code == 0:
                platform_support[platform] = True
                print(f"  ✅ {platform} supported")
            else:
                platform_support[platform] = False
                print(f"  ❌ {platform} not available")

        return platform_support

    def test_current_platform_functionality(self, image: str) -> bool:
        """Test that the image works on the current platform."""
        print(f"🧪 Testing {image} functionality on current platform...")

        # Pull the image for current platform
        exit_code, stdout, stderr = self.run_command(
            ["docker", "pull", f"{self.registry}/{image}:latest"]
        )

        if exit_code != 0:
            print(f"❌ Failed to pull {image}: {stderr}")
            return False

        # Try to run a simple command to verify the image works
        exit_code, stdout, stderr = self.run_command(
            [
                "docker",
                "run",
                "--rm",
                "--entrypoint",
                "echo",
                f"{self.registry}/{image}:latest",
                "test",
            ],
            timeout=30,
        )

        if exit_code == 0 and "test" in stdout:
            print(f"✅ {image} runs successfully on current platform")
            return True
        else:
            print(f"❌ {image} failed to run: {stderr}")
            return False

    def generate_platform_report(self) -> str:
        """Generate multi-platform compatibility report."""
        report = []
        report.append("# Multi-Platform Compatibility Report")
        report.append("")

        current_platform = self.detect_current_platform()
        report.append(f"**Current Platform**: {current_platform}")
        report.append("")

        report.append("## Platform Support Matrix")
        report.append("")
        report.append("| Service | linux/amd64 | linux/arm64 | Functional Test |")
        report.append("|---------|-------------|-------------|-----------------|")

        for service in self.services:
            service_results = self.results.get(service, {})
            amd64_support = "✅" if service_results.get("linux/amd64", False) else "❌"
            arm64_support = "✅" if service_results.get("linux/arm64", False) else "❌"
            functional = "✅" if service_results.get("functional", False) else "❌"

            report.append(
                f"| {service} | {amd64_support} | {arm64_support} | {functional} |"
            )

        report.append("")

        # Summary
        total_services = len(self.services)
        amd64_count = sum(
            1
            for s in self.services
            if self.results.get(s, {}).get("linux/amd64", False)
        )
        arm64_count = sum(
            1
            for s in self.services
            if self.results.get(s, {}).get("linux/arm64", False)
        )
        functional_count = sum(
            1 for s in self.services if self.results.get(s, {}).get("functional", False)
        )

        report.append("## Summary")
        report.append(f"- **AMD64 Support**: {amd64_count}/{total_services} services")
        report.append(f"- **ARM64 Support**: {arm64_count}/{total_services} services")
        report.append(
            f"- **Functional Tests**: {functional_count}/{total_services} services"
        )

        if amd64_count == total_services and arm64_count == total_services:
            report.append("- **Status**: ✅ Full multi-platform support achieved")
        else:
            report.append("- **Status**: ❌ Multi-platform support incomplete")

        return "\n".join(report)

    def run_all_tests(self) -> bool:
        """Run all multi-platform tests."""
        print("🌐 FOGIS Multi-Platform Compatibility Test")
        print("=" * 50)

        current_platform = self.detect_current_platform()
        print(f"Current platform: {current_platform}")

        if not self.check_docker_buildx():
            print("⚠️ Docker Buildx not available - limited testing possible")

        all_passed = True

        for service in self.services:
            print(f"\n📦 Testing {service}...")

            # Check platform manifests
            platform_support = self.check_image_manifest(service)

            # Test functionality on current platform
            functional = self.test_current_platform_functionality(service)

            # Store results
            self.results[service] = {**platform_support, "functional": functional}

            # Check if this service passed all tests
            service_passed = (
                platform_support.get("linux/amd64", False)
                and platform_support.get("linux/arm64", False)
                and functional
            )

            if not service_passed:
                all_passed = False

        # Generate report
        report = self.generate_platform_report()
        with open("multiplatform_test_report.md", "w") as f:
            f.write(report)

        print(f"\n📄 Report saved to: multiplatform_test_report.md")

        # Print summary
        print("\n📊 Test Summary:")
        for service in self.services:
            service_results = self.results[service]
            amd64 = "✅" if service_results.get("linux/amd64", False) else "❌"
            arm64 = "✅" if service_results.get("linux/arm64", False) else "❌"
            func = "✅" if service_results.get("functional", False) else "❌"
            print(f"  {service}: AMD64={amd64} ARM64={arm64} Functional={func}")

        return all_passed


def main():
    """Main test execution."""
    tester = MultiPlatformTester()

    if tester.run_all_tests():
        print("\n🎉 All multi-platform tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some multi-platform tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
