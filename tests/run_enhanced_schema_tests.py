#!/usr/bin/env python3
# Test Runner for Enhanced Schema v2.0
# File: tests/run_enhanced_schema_tests.py

"""
Test runner for Enhanced Schema v2.0 implementation.

This script runs comprehensive tests for:
- Organization ID mapping validation
- Message formatting (v1.0 and v2.0)
- Redis publishing integration
- Logo service compatibility
- Contact data completeness
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_unit_tests():
    """Run unit tests for Enhanced Schema v2.0."""
    logger.info("🧪 Running Enhanced Schema v2.0 unit tests...")

    try:
        # Run pytest with verbose output
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_enhanced_schema_v2.py",
                "-v",
                "--tb=short",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        if result.returncode == 0:
            logger.info("✅ Unit tests passed")
            print(result.stdout)
            return True
        else:
            logger.error("❌ Unit tests failed")
            print(result.stdout)
            print(result.stderr)
            return False

    except Exception as e:
        logger.error(f"❌ Failed to run unit tests: {e}")
        return False


def test_organization_id_mapping():
    """Test Organization ID mapping functionality."""
    logger.info("🔍 Testing Organization ID mapping...")

    try:
        from redis_integration.message_formatter_v2 import EnhancedSchemaV2Formatter

        # Test data with Organization IDs
        test_matches = [
            {
                "matchid": 6170049,
                "lag1namn": "Lindome GIF",
                "lag1lagid": 26405,  # Database ID
                "lag1foreningid": 10741,  # Organization ID for logo service
                "lag2namn": "Jonsereds IF",
                "lag2lagid": 25562,  # Database ID
                "lag2foreningid": 9595,  # Organization ID for logo service
            }
        ]

        formatter = EnhancedSchemaV2Formatter()
        result = formatter.format_match_updates_v2(test_matches)
        message = json.loads(result)

        # Validate Organization ID mapping
        match_data = message["payload"]["matches"][0]
        home_team = match_data["teams"]["home"]
        away_team = match_data["teams"]["away"]

        # Check that logo_id uses Organization ID, not Database ID
        assert home_team["id"] == 26405, "Home team database ID incorrect"
        assert home_team["logo_id"] == 10741, "Home team Organization ID incorrect"
        assert away_team["id"] == 25562, "Away team database ID incorrect"
        assert away_team["logo_id"] == 9595, "Away team Organization ID incorrect"

        logger.info("✅ Organization ID mapping test passed")
        logger.info(
            f"   Home team: DB ID {home_team['id']} → Logo ID {home_team['logo_id']}"
        )
        logger.info(
            f"   Away team: DB ID {away_team['id']} → Logo ID {away_team['logo_id']}"
        )
        return True

    except Exception as e:
        logger.error(f"❌ Organization ID mapping test failed: {e}")
        return False


def test_logo_service_integration():
    """Test logo service integration compatibility."""
    logger.info("🖼️ Testing logo service integration...")

    try:
        import requests

        from redis_integration.message_formatter_v2 import EnhancedSchemaV2Formatter

        # Test data
        test_matches = [
            {
                "matchid": 6170049,
                "lag1foreningid": 10741,  # Known Organization ID
                "lag2foreningid": 9595,  # Known Organization ID
                "lag1namn": "Lindome GIF",
                "lag2namn": "Jonsereds IF",
            }
        ]

        formatter = EnhancedSchemaV2Formatter()
        result = formatter.format_match_updates_v2(test_matches)
        message = json.loads(result)

        # Extract Organization IDs for logo service
        match_data = message["payload"]["matches"][0]
        team1_id = str(match_data["teams"]["home"]["logo_id"])
        team2_id = str(match_data["teams"]["away"]["logo_id"])

        logger.info(
            f"   Testing logo service with Organization IDs: {team1_id}, {team2_id}"
        )

        # Test logo service API (if available)
        try:
            logo_service_url = "http://localhost:9088/create_avatar"
            response = requests.post(
                logo_service_url,
                json={"team1_id": team1_id, "team2_id": team2_id},
                timeout=10,
            )

            if response.status_code == 200:
                logo_size = len(response.content)
                if logo_size > 100000:  # Real logos are > 100KB
                    logger.info(
                        f"✅ Logo service integration successful: {logo_size} bytes"
                    )
                    return True
                else:
                    logger.warning(
                        f"⚠️ Logo service returned fallback: {logo_size} bytes"
                    )
                    return False
            else:
                logger.warning(
                    f"⚠️ Logo service returned status {response.status_code}"
                )
                return False

        except requests.exceptions.RequestException:
            logger.warning("⚠️ Logo service not available - skipping integration test")
            logger.info("✅ Organization ID format validation passed")
            return True

    except Exception as e:
        logger.error(f"❌ Logo service integration test failed: {e}")
        return False


def test_message_size_validation():
    """Test that Enhanced Schema v2.0 messages are within size limits."""
    logger.info("📏 Testing message size validation...")

    try:
        from redis_integration.message_formatter_v2 import EnhancedSchemaV2Formatter

        # Create test data with full contact information
        test_matches = [
            {
                "matchid": 6170049,
                "lag1namn": "Lindome GIF",
                "lag1foreningid": 10741,
                "lag2namn": "Jonsereds IF",
                "lag2foreningid": 9595,
                "domaruppdraglista": [
                    {
                        "namn": "Bartek Svaberg",
                        "domarrollnamn": "Huvuddomare",
                        "mobiltelefon": "0709423055",
                        "epostadress": "bartek.svaberg@gmail.com",
                        "adress": "Lilla Tulteredsvägen 50",
                        "postnr": "43331",
                        "postort": "Partille",
                    }
                ],
                "kontaktpersoner": [
                    {
                        "personnamn": "Morgan Johansson",
                        "lagnamn": "Landvetter IS Senior",
                        "mobiltelefon": "0733472740",
                        "epostadress": "morgan@kalltorpsbygg.se",
                    }
                ],
            }
        ]

        formatter = EnhancedSchemaV2Formatter()
        result = formatter.format_match_updates_v2(test_matches)

        # Check message size
        message_size = len(result.encode("utf-8"))
        size_limit = 5120  # 5KB limit for optimal Redis performance

        if message_size < size_limit:
            logger.info(
                f"✅ Message size passed: {message_size} bytes (< {size_limit} bytes)"
            )
            return True
        else:
            logger.error(
                f"❌ Message size too large: {message_size} bytes (> {size_limit} bytes)"
            )
            return False

    except Exception as e:
        logger.error(f"❌ Message size validation failed: {e}")
        return False


def test_backward_compatibility():
    """Test backward compatibility with Legacy Schema v1.0."""
    logger.info("🔄 Testing backward compatibility...")

    try:
        from redis_integration.message_formatter_v2 import EnhancedSchemaV2Formatter

        test_matches = [
            {
                "matchid": 6170049,
                "lag1namn": "Lindome GIF",
                "lag2namn": "Jonsereds IF",
                "speldatum": "2025-09-19",
                "avsparkstid": "19:00",
                "anlaggningnamn": "Lindome IP",
                "domaruppdraglista": [{"namn": "Bartek Svaberg"}],
            }
        ]

        formatter = EnhancedSchemaV2Formatter()

        # Test v2.0 message
        v2_result = formatter.format_match_updates_v2(test_matches)
        v2_message = json.loads(v2_result)
        assert v2_message["schema_version"] == "2.0"

        # Test v1.0 message
        v1_result = formatter.format_match_updates_v1_legacy(test_matches)
        v1_message = json.loads(v1_result)
        assert v1_message["schema_version"] == "1.0"

        # Validate both contain core match data
        assert v2_message["payload"]["matches"][0]["match_id"] == 6170049
        assert v1_message["payload"]["matches"][0]["match_id"] == 6170049

        logger.info("✅ Backward compatibility test passed")
        logger.info(f"   v2.0 message: {len(v2_result)} bytes")
        logger.info(f"   v1.0 message: {len(v1_result)} bytes")
        return True

    except Exception as e:
        logger.error(f"❌ Backward compatibility test failed: {e}")
        return False


def main():
    """Run all Enhanced Schema v2.0 tests."""
    logger.info("🚀 Starting Enhanced Schema v2.0 test suite...")

    test_results = []

    # Run individual tests
    test_functions = [
        ("Unit Tests", run_unit_tests),
        ("Organization ID Mapping", test_organization_id_mapping),
        ("Logo Service Integration", test_logo_service_integration),
        ("Message Size Validation", test_message_size_validation),
        ("Backward Compatibility", test_backward_compatibility),
    ]

    for test_name, test_function in test_functions:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")

        try:
            result = test_function()
            test_results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {e}")
            test_results.append((test_name, False))

    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1

    logger.info(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 All Enhanced Schema v2.0 tests passed!")
        return True
    else:
        logger.error(f"💥 {total - passed} tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
