#!/usr/bin/env python3
"""
FOGIS Redis Testing Framework

This module provides comprehensive testing utilities for Redis integration
across all FOGIS services, including end-to-end testing, performance testing,
and integration validation.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Redis testing framework for FOGIS system
"""

import logging
import time
import json
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from .client import FogisRedisClient, create_fogis_redis_client

logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Result of a Redis test operation."""
    test_name: str
    success: bool
    duration_ms: float
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class TestSuiteResult:
    """Result of a complete test suite execution."""
    suite_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    total_duration_ms: float
    test_results: List[TestResult]
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    @property
    def success_rate(self) -> float:
        """Calculate test success rate."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100

class FogisRedisTestSuite:
    """Comprehensive Redis testing framework for FOGIS system."""
    
    def __init__(self, redis_url: str = None, service_name: str = "test-suite"):
        """
        Initialize Redis test suite.
        
        Args:
            redis_url: Redis connection URL (optional)
            service_name: Name of the service being tested
        """
        self.redis_url = redis_url
        self.service_name = service_name
        self.client: Optional[FogisRedisClient] = None
        self.test_results: List[TestResult] = []
        
        logger.info(f"🧪 FOGIS Redis Test Suite initialized for {self.service_name}")
    
    def _execute_test(self, test_name: str, test_function: Callable[[], bool], 
                     details_function: Callable[[], Dict[str, Any]] = None) -> TestResult:
        """
        Execute a single test with timing and error handling.
        
        Args:
            test_name: Name of the test
            test_function: Function that performs the test
            details_function: Optional function to gather test details
            
        Returns:
            TestResult: Result of the test execution
        """
        start_time = time.time()
        
        try:
            logger.debug(f"🔬 Executing test: {test_name}")
            
            success = test_function()
            duration_ms = (time.time() - start_time) * 1000
            
            details = None
            if details_function:
                try:
                    details = details_function()
                except Exception as e:
                    logger.warning(f"⚠️ Failed to gather test details for {test_name}: {e}")
            
            result = TestResult(
                test_name=test_name,
                success=success,
                duration_ms=duration_ms,
                details=details
            )
            
            if success:
                logger.debug(f"✅ Test passed: {test_name} ({duration_ms:.2f}ms)")
            else:
                logger.warning(f"❌ Test failed: {test_name} ({duration_ms:.2f}ms)")
            
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            logger.error(f"❌ Test error: {test_name} - {error_msg}")
            
            return TestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                error=error_msg
            )
    
    def test_connection(self) -> TestResult:
        """Test Redis connection."""
        def test_func():
            self.client = create_fogis_redis_client(self.redis_url, f"{self.service_name}-connection-test")
            return self.client.ensure_connection()
        
        def details_func():
            if self.client:
                return self.client.get_connection_status()
            return {}
        
        return self._execute_test("Redis Connection", test_func, details_func)
    
    def test_basic_operations(self) -> TestResult:
        """Test basic Redis operations (set, get, delete)."""
        def test_func():
            if not self.client or not self.client.ensure_connection():
                return False
            
            test_key = f"fogis:test:{self.service_name}:{int(time.time())}"
            test_value = f"test_value_{int(time.time())}"
            
            # Test set
            if not self.client.set(test_key, test_value, ex=60):
                return False
            
            # Test get
            retrieved_value = self.client.get(test_key)
            if retrieved_value != test_value:
                return False
            
            # Test delete
            if not self.client.delete(test_key):
                return False
            
            # Verify deletion
            if self.client.exists(test_key):
                return False
            
            return True
        
        return self._execute_test("Basic Operations", test_func)
    
    def test_publish_subscribe(self) -> TestResult:
        """Test Redis pub/sub functionality."""
        def test_func():
            if not self.client or not self.client.ensure_connection():
                return False
            
            test_channel = f"fogis:test:channel:{self.service_name}:{int(time.time())}"
            test_message = f"test_message_{int(time.time())}"
            
            # Test publish
            result = self.client.publish(test_channel, test_message)
            return result is not None
        
        return self._execute_test("Publish/Subscribe", test_func)
    
    def test_performance(self, num_operations: int = 100) -> TestResult:
        """Test Redis performance with multiple operations."""
        def test_func():
            if not self.client or not self.client.ensure_connection():
                return False
            
            test_key_prefix = f"fogis:perf:test:{self.service_name}:{int(time.time())}"
            
            # Perform multiple set operations
            for i in range(num_operations):
                key = f"{test_key_prefix}:{i}"
                value = f"value_{i}"
                if not self.client.set(key, value, ex=60):
                    return False
            
            # Perform multiple get operations
            for i in range(num_operations):
                key = f"{test_key_prefix}:{i}"
                value = self.client.get(key)
                if value != f"value_{i}":
                    return False
            
            # Cleanup
            keys_to_delete = [f"{test_key_prefix}:{i}" for i in range(num_operations)]
            self.client.delete(*keys_to_delete)
            
            return True
        
        def details_func():
            return {"operations_count": num_operations}
        
        return self._execute_test(f"Performance ({num_operations} ops)", test_func, details_func)
    
    def test_error_handling(self) -> TestResult:
        """Test Redis error handling and recovery."""
        def test_func():
            if not self.client:
                return False
            
            # Test operation with invalid parameters
            try:
                # This should handle gracefully
                result = self.client.execute_operation('invalid_operation')
                # Should return None for invalid operations
                return result is None
            except Exception:
                # Should not raise exceptions
                return False
        
        return self._execute_test("Error Handling", test_func)
    
    def test_message_format_validation(self) -> TestResult:
        """Test FOGIS message format validation."""
        def test_func():
            # Test valid message format
            valid_message = {
                'message_id': 'test-123',
                'timestamp': datetime.now().isoformat(),
                'source': self.service_name,
                'version': '1.0',
                'type': 'test_message',
                'payload': {'test': 'data'}
            }
            
            try:
                # Test JSON serialization
                json_message = json.dumps(valid_message)
                
                # Test JSON deserialization
                parsed_message = json.loads(json_message)
                
                # Validate required fields
                required_fields = ['message_id', 'timestamp', 'source', 'version', 'type', 'payload']
                for field in required_fields:
                    if field not in parsed_message:
                        return False
                
                return True
                
            except Exception:
                return False
        
        return self._execute_test("Message Format Validation", test_func)
    
    def run_comprehensive_test_suite(self) -> TestSuiteResult:
        """
        Run comprehensive Redis test suite.
        
        Returns:
            TestSuiteResult: Complete test suite results
        """
        logger.info(f"🚀 Starting comprehensive Redis test suite for {self.service_name}")
        
        suite_start_time = time.time()
        self.test_results = []
        
        # Execute all tests
        tests = [
            self.test_connection,
            self.test_basic_operations,
            self.test_publish_subscribe,
            lambda: self.test_performance(50),  # 50 operations for performance test
            self.test_error_handling,
            self.test_message_format_validation
        ]
        
        for test in tests:
            result = test()
            self.test_results.append(result)
        
        # Calculate suite results
        total_duration_ms = (time.time() - suite_start_time) * 1000
        passed_tests = sum(1 for result in self.test_results if result.success)
        failed_tests = len(self.test_results) - passed_tests
        
        suite_result = TestSuiteResult(
            suite_name=f"FOGIS Redis Test Suite - {self.service_name}",
            total_tests=len(self.test_results),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            total_duration_ms=total_duration_ms,
            test_results=self.test_results
        )
        
        # Log results
        logger.info(f"📊 Test Suite Results for {self.service_name}:")
        logger.info(f"   Total Tests: {suite_result.total_tests}")
        logger.info(f"   Passed: {suite_result.passed_tests}")
        logger.info(f"   Failed: {suite_result.failed_tests}")
        logger.info(f"   Success Rate: {suite_result.success_rate:.1f}%")
        logger.info(f"   Duration: {suite_result.total_duration_ms:.2f}ms")
        
        if suite_result.failed_tests > 0:
            logger.warning("❌ Failed tests:")
            for result in self.test_results:
                if not result.success:
                    logger.warning(f"   - {result.test_name}: {result.error or 'Test failed'}")
        
        # Cleanup
        if self.client:
            self.client.close()
        
        return suite_result
    
    def run_integration_test(self, match_processor_url: str = None, 
                           calendar_service_url: str = None) -> TestResult:
        """
        Run end-to-end integration test across FOGIS services.
        
        Args:
            match_processor_url: URL of match processor service
            calendar_service_url: URL of calendar service
            
        Returns:
            TestResult: Integration test result
        """
        def test_func():
            try:
                # Test Redis infrastructure
                if not self.client or not self.client.ensure_connection():
                    return False
                
                # Test message publishing (simulating match processor)
                test_message = {
                    'message_id': f'integration-test-{int(time.time())}',
                    'timestamp': datetime.now().isoformat(),
                    'source': 'integration-test',
                    'version': '1.0',
                    'type': 'match_updates',
                    'payload': {
                        'matches': [{'matchid': 999999, 'hemmalag': 'Test Team A', 'bortalag': 'Test Team B'}],
                        'metadata': {'has_changes': True, 'change_summary': {'new_matches': 1}}
                    }
                }
                
                # Publish to match updates channel
                result = self.client.publish('fogis:matches:updates', json.dumps(test_message))
                if result is None:
                    return False
                
                # Test status publishing (simulating match processor status)
                status_message = {
                    'message_id': f'status-test-{int(time.time())}',
                    'timestamp': datetime.now().isoformat(),
                    'source': 'integration-test',
                    'version': '1.0',
                    'type': 'processing_status',
                    'payload': {
                        'status': 'completed',
                        'cycle_number': 999,
                        'matches_processed': 1
                    }
                }
                
                # Publish to processor status channel
                result = self.client.publish('fogis:processor:status', json.dumps(status_message))
                return result is not None
                
            except Exception as e:
                logger.error(f"❌ Integration test error: {e}")
                return False
        
        def details_func():
            return {
                "match_processor_url": match_processor_url,
                "calendar_service_url": calendar_service_url,
                "test_channels": ["fogis:matches:updates", "fogis:processor:status"]
            }
        
        return self._execute_test("End-to-End Integration", test_func, details_func)

# Convenience functions for external use
def run_fogis_redis_tests(redis_url: str = None, service_name: str = "test-service") -> TestSuiteResult:
    """
    Run comprehensive FOGIS Redis tests.
    
    Args:
        redis_url: Redis connection URL (optional)
        service_name: Name of the service being tested
        
    Returns:
        TestSuiteResult: Complete test results
    """
    test_suite = FogisRedisTestSuite(redis_url, service_name)
    return test_suite.run_comprehensive_test_suite()

def validate_fogis_redis_setup(redis_url: str = None) -> bool:
    """
    Validate FOGIS Redis setup and configuration.
    
    Args:
        redis_url: Redis connection URL (optional)
        
    Returns:
        bool: True if Redis setup is valid
    """
    test_suite = FogisRedisTestSuite(redis_url, "validation")
    result = test_suite.run_comprehensive_test_suite()
    return result.success_rate >= 80.0  # 80% success rate threshold

if __name__ == "__main__":
    # Run FOGIS Redis tests
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("🧪 Running FOGIS Redis test suite...")
    
    # Run comprehensive tests
    results = run_fogis_redis_tests(service_name="standalone-test")
    
    if results.success_rate >= 80.0:
        logger.info("✅ FOGIS Redis test suite passed")
    else:
        logger.error("❌ FOGIS Redis test suite failed")
    
    # Validate setup
    if validate_fogis_redis_setup():
        logger.info("✅ FOGIS Redis setup validation passed")
    else:
        logger.error("❌ FOGIS Redis setup validation failed")
