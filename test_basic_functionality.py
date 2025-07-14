#!/usr/bin/env python3
"""Basic functionality test for FOGIS Multi-Platform Installation System."""

import sys

from platform_manager import MultiPlatformManager, PlatformInfo


def test_platform_info():
    """Test PlatformInfo dataclass."""
    print("Testing PlatformInfo...")

    info = PlatformInfo(
        os_name="linux",
        distribution="Ubuntu",
        version="22.04",
        architecture="x86_64",
        package_manager="apt",
    )

    assert info.os_name == "linux"
    assert str(info) == "Ubuntu 22.04 (x86_64)"
    print("✓ PlatformInfo tests passed!")


def test_multi_platform_manager():
    """Test MultiPlatformManager."""
    print("Testing MultiPlatformManager...")

    manager = MultiPlatformManager()
    assert "git" in manager.package_mappings

    # Test platform detection
    platform_info = manager.detect_platform()
    assert platform_info is not None
    print(f"✓ Detected platform: {platform_info}")


def main():
    """Run all tests."""
    print("=== FOGIS Multi-Platform Installation System - Basic Tests ===")
    print()

    try:
        test_platform_info()
        test_multi_platform_manager()

        print()
        print("🎉 All tests passed successfully!")
        return 0

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
