#!/usr/bin/env python3
"""
Monitoring Setup for FOGIS Deployment
Enhanced monitoring and health check capabilities

This module provides comprehensive monitoring functionality for:
- Service health checks and status monitoring
- Performance metrics collection and reporting
- System resource monitoring (CPU, memory, disk)
- Log analysis and error detection
- Automated alerting and notifications
"""

import json
import logging
import os
import psutil
import requests
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MonitoringError(Exception):
    """Exception raised for monitoring errors"""


class MonitoringSetup:
    """
    Comprehensive monitoring and health check system for FOGIS deployment
    
    Provides monitoring capabilities for:
    - Service health and availability
    - Performance metrics and resource usage
    - Log analysis and error detection
    - System health and status reporting
    """
    
    def __init__(self, config_file: str = "fogis-config.yaml"):
        """
        Initialize monitoring setup
        
        Args:
            config_file: Path to FOGIS configuration file
        """
        self.config_file = config_file
        self.config = self._load_config()
        self.monitoring_dir = Path("monitoring")
        self.monitoring_dir.mkdir(exist_ok=True)
        
        # Service endpoints for health checks
        self.service_endpoints = self._get_service_endpoints()
        
        # Monitoring thresholds
        self.thresholds = {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "disk_usage": 90.0,
            "response_time": 5.0,  # seconds
            "error_rate": 5.0      # percentage
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """Load FOGIS configuration"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return yaml.safe_load(f)
            else:
                logger.warning(f"Config file not found: {self.config_file}")
                return {}
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    def _get_service_endpoints(self) -> Dict[str, str]:
        """Get service endpoints for health checks"""
        services = self.config.get("services", {})
        ports = services.get("ports", {})
        
        endpoints = {
            "calendar_sync": f"http://localhost:{ports.get('calendar_sync', 8080)}/health",
            "google_drive": f"http://localhost:{ports.get('google_drive', 8081)}/health",
            "match_list_processor": f"http://localhost:{ports.get('match_list_processor', 8082)}/health",
            "team_logo_combiner": f"http://localhost:{ports.get('team_logo_combiner', 8083)}/health",
            "whatsapp_avatar_automation": f"http://localhost:{ports.get('whatsapp_avatar_automation', 8084)}/health",
            "match_list_change_detector": f"http://localhost:{ports.get('match_list_change_detector', 8085)}/health"
        }
        
        return endpoints
    
    def run_health_check(self) -> Dict[str, Any]:
        """
        Run comprehensive health check
        
        Returns:
            Health check results dictionary
        """
        logger.info("Running comprehensive health check...")
        
        health_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "services": {},
            "system": {},
            "docker": {},
            "issues": []
        }
        
        try:
            # Check service health
            service_results = self._check_service_health()
            health_report["services"] = service_results
            
            # Check system resources
            system_results = self._check_system_health()
            health_report["system"] = system_results
            
            # Check Docker status
            docker_results = self._check_docker_health()
            health_report["docker"] = docker_results
            
            # Determine overall status
            health_report["overall_status"] = self._determine_overall_status(health_report)
            
            # Save health report
            self._save_health_report(health_report)
            
            logger.info(f"Health check completed. Status: {health_report['overall_status']}")
            return health_report
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_report["overall_status"] = "error"
            health_report["issues"].append(f"Health check error: {e}")
            return health_report
    
    def _check_service_health(self) -> Dict[str, Any]:
        """Check health of all FOGIS services"""
        logger.info("Checking service health...")
        
        service_results = {}
        
        for service_name, endpoint in self.service_endpoints.items():
            try:
                start_time = time.time()
                response = requests.get(endpoint, timeout=10)
                response_time = time.time() - start_time
                
                service_results[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "status_code": response.status_code,
                    "response_time": round(response_time, 3),
                    "endpoint": endpoint,
                    "last_check": datetime.now().isoformat()
                }
                
                if response.status_code == 200:
                    try:
                        health_data = response.json()
                        service_results[service_name]["details"] = health_data
                    except:
                        pass
                
            except requests.exceptions.ConnectionError:
                service_results[service_name] = {
                    "status": "down",
                    "error": "Connection refused",
                    "endpoint": endpoint,
                    "last_check": datetime.now().isoformat()
                }
            except requests.exceptions.Timeout:
                service_results[service_name] = {
                    "status": "timeout",
                    "error": "Request timeout",
                    "endpoint": endpoint,
                    "last_check": datetime.now().isoformat()
                }
            except Exception as e:
                service_results[service_name] = {
                    "status": "error",
                    "error": str(e),
                    "endpoint": endpoint,
                    "last_check": datetime.now().isoformat()
                }
        
        return service_results
    
    def _check_system_health(self) -> Dict[str, Any]:
        """Check system resource health"""
        logger.info("Checking system health...")
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Load average (Unix-like systems only)
            load_avg = None
            try:
                load_avg = os.getloadavg()
            except (OSError, AttributeError):
                pass
            
            # Network statistics
            network = psutil.net_io_counters()
            
            system_health = {
                "cpu": {
                    "usage_percent": round(cpu_percent, 2),
                    "status": "healthy" if cpu_percent < self.thresholds["cpu_usage"] else "warning",
                    "cores": psutil.cpu_count()
                },
                "memory": {
                    "usage_percent": round(memory_percent, 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "status": "healthy" if memory_percent < self.thresholds["memory_usage"] else "warning"
                },
                "disk": {
                    "usage_percent": round(disk_percent, 2),
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "status": "healthy" if disk_percent < self.thresholds["disk_usage"] else "warning"
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            }
            
            if load_avg:
                system_health["load_average"] = {
                    "1min": round(load_avg[0], 2),
                    "5min": round(load_avg[1], 2),
                    "15min": round(load_avg[2], 2)
                }
            
            return system_health
            
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return {"error": str(e)}
    
    def _check_docker_health(self) -> Dict[str, Any]:
        """Check Docker and container health"""
        logger.info("Checking Docker health...")
        
        try:
            # Check Docker daemon
            docker_info = subprocess.run(
                ["docker", "info", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if docker_info.returncode != 0:
                return {
                    "status": "error",
                    "error": "Docker daemon not accessible"
                }
            
            # Get container status
            containers_result = subprocess.run(
                ["docker", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            containers = []
            if containers_result.returncode == 0:
                for line in containers_result.stdout.strip().split('\n'):
                    if line:
                        try:
                            container = json.loads(line)
                            containers.append({
                                "name": container.get("Names", ""),
                                "image": container.get("Image", ""),
                                "status": container.get("Status", ""),
                                "ports": container.get("Ports", "")
                            })
                        except json.JSONDecodeError:
                            pass
            
            # Get Docker Compose status
            compose_status = self._check_docker_compose_status()
            
            return {
                "status": "healthy",
                "daemon_running": True,
                "containers": containers,
                "compose": compose_status
            }
            
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "error": "Docker command timeout"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _check_docker_compose_status(self) -> Dict[str, Any]:
        """Check Docker Compose service status"""
        try:
            compose_result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if compose_result.returncode != 0:
                return {"status": "error", "error": "Docker Compose not available"}
            
            services = []
            for line in compose_result.stdout.strip().split('\n'):
                if line:
                    try:
                        service = json.loads(line)
                        services.append({
                            "name": service.get("Name", ""),
                            "service": service.get("Service", ""),
                            "state": service.get("State", ""),
                            "health": service.get("Health", "")
                        })
                    except json.JSONDecodeError:
                        pass
            
            return {
                "status": "healthy",
                "services": services
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def _determine_overall_status(self, health_report: Dict[str, Any]) -> str:
        """Determine overall system status from health report"""
        # Check for critical issues
        if health_report.get("docker", {}).get("status") == "error":
            return "critical"

        # Check service health
        services = health_report.get("services", {})
        down_services = [name for name, info in services.items()
                        if info.get("status") in ["down", "error"]]

        if len(down_services) > len(services) / 2:  # More than half down
            return "critical"
        elif down_services:
            return "degraded"

        # Check system resources
        system = health_report.get("system", {})
        warnings = []

        if system.get("cpu", {}).get("status") == "warning":
            warnings.append("cpu")
        if system.get("memory", {}).get("status") == "warning":
            warnings.append("memory")
        if system.get("disk", {}).get("status") == "warning":
            warnings.append("disk")

        if len(warnings) >= 2:
            return "degraded"
        elif warnings:
            return "warning"

        return "healthy"

    def _save_health_report(self, health_report: Dict[str, Any]) -> None:
        """Save health report to file"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        report_file = self.monitoring_dir / f"health-report-{timestamp}.json"

        with open(report_file, 'w') as f:
            json.dump(health_report, f, indent=2)

        # Also save as latest
        latest_file = self.monitoring_dir / "health-report-latest.json"
        with open(latest_file, 'w') as f:
            json.dump(health_report, f, indent=2)

        logger.debug(f"Health report saved: {report_file}")

    def generate_performance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance report

        Returns:
            Performance report dictionary
        """
        logger.info("Generating performance report...")

        report = {
            "timestamp": datetime.now().isoformat(),
            "period": "last_24_hours",
            "metrics": {},
            "trends": {},
            "recommendations": []
        }

        try:
            # Collect current metrics
            current_metrics = self._collect_performance_metrics()
            report["metrics"]["current"] = current_metrics

            # Analyze historical data
            historical_data = self._load_historical_metrics()
            if historical_data:
                report["metrics"]["historical"] = historical_data
                report["trends"] = self._analyze_performance_trends(historical_data)

            # Generate recommendations
            report["recommendations"] = self._generate_performance_recommendations(
                current_metrics, report["trends"]
            )

            # Save performance report
            self._save_performance_report(report)

            logger.info("Performance report generated successfully")
            return report

        except Exception as e:
            logger.error(f"Performance report generation failed: {e}")
            report["error"] = str(e)
            return report

    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect current performance metrics"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "system": {},
            "services": {},
            "docker": {}
        }

        # System metrics
        metrics["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100,
            "network_io": psutil.net_io_counters()._asdict(),
            "disk_io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {}
        }

        # Service response times
        for service_name, endpoint in self.service_endpoints.items():
            try:
                start_time = time.time()
                response = requests.get(endpoint, timeout=5)
                response_time = time.time() - start_time

                metrics["services"][service_name] = {
                    "response_time": round(response_time, 3),
                    "status_code": response.status_code,
                    "available": response.status_code == 200
                }
            except:
                metrics["services"][service_name] = {
                    "response_time": None,
                    "status_code": None,
                    "available": False
                }

        return metrics

    def _load_historical_metrics(self) -> List[Dict[str, Any]]:
        """Load historical performance metrics"""
        historical_data = []

        # Look for performance reports from the last 24 hours
        cutoff_time = datetime.now() - timedelta(hours=24)

        for report_file in self.monitoring_dir.glob("performance-report-*.json"):
            try:
                # Extract timestamp from filename
                timestamp_str = report_file.stem.replace("performance-report-", "")
                file_time = datetime.strptime(timestamp_str, "%Y%m%d-%H%M%S")

                if file_time >= cutoff_time:
                    with open(report_file, 'r') as f:
                        data = json.load(f)
                        if "metrics" in data and "current" in data["metrics"]:
                            historical_data.append(data["metrics"]["current"])
            except:
                continue

        return sorted(historical_data, key=lambda x: x.get("timestamp", ""))

    def _analyze_performance_trends(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance trends from historical data"""
        if len(historical_data) < 2:
            return {"error": "Insufficient data for trend analysis"}

        trends = {
            "cpu_trend": self._calculate_trend([d["system"]["cpu_percent"] for d in historical_data]),
            "memory_trend": self._calculate_trend([d["system"]["memory_percent"] for d in historical_data]),
            "disk_trend": self._calculate_trend([d["system"]["disk_percent"] for d in historical_data]),
            "service_availability": {}
        }

        # Service availability trends
        for service_name in self.service_endpoints.keys():
            availability_data = [
                d["services"].get(service_name, {}).get("available", False)
                for d in historical_data
            ]
            availability_rate = sum(availability_data) / len(availability_data) * 100
            trends["service_availability"][service_name] = round(availability_rate, 2)

        return trends

    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend direction and rate for a series of values"""
        if len(values) < 2:
            return {"direction": "unknown", "rate": 0}

        # Simple linear trend calculation
        n = len(values)
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * values[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))

        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)

        return {
            "direction": "increasing" if slope > 0.1 else "decreasing" if slope < -0.1 else "stable",
            "rate": round(slope, 4),
            "current": round(values[-1], 2),
            "average": round(sum(values) / len(values), 2)
        }

    def _generate_performance_recommendations(self, current_metrics: Dict[str, Any],
                                           trends: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations based on metrics and trends"""
        recommendations = []

        # CPU recommendations
        cpu_percent = current_metrics["system"]["cpu_percent"]
        cpu_trend = trends.get("cpu_trend", {})

        if cpu_percent > 80:
            recommendations.append("High CPU usage detected. Consider scaling up or optimizing services.")
        elif cpu_trend.get("direction") == "increasing":
            recommendations.append("CPU usage is trending upward. Monitor for potential scaling needs.")

        # Memory recommendations
        memory_percent = current_metrics["system"]["memory_percent"]
        memory_trend = trends.get("memory_trend", {})

        if memory_percent > 85:
            recommendations.append("High memory usage detected. Consider increasing memory or optimizing services.")
        elif memory_trend.get("direction") == "increasing":
            recommendations.append("Memory usage is trending upward. Monitor for potential memory leaks.")

        # Disk recommendations
        disk_percent = current_metrics["system"]["disk_percent"]
        if disk_percent > 90:
            recommendations.append("Critical disk usage. Clean up logs and temporary files immediately.")
        elif disk_percent > 80:
            recommendations.append("High disk usage. Consider log rotation and cleanup procedures.")

        # Service availability recommendations
        service_availability = trends.get("service_availability", {})
        for service, availability in service_availability.items():
            if availability < 95:
                recommendations.append(f"Service {service} has low availability ({availability}%). Investigate issues.")

        return recommendations

    def _save_performance_report(self, report: Dict[str, Any]) -> None:
        """Save performance report to file"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        report_file = self.monitoring_dir / f"performance-report-{timestamp}.json"

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        # Also save as latest
        latest_file = self.monitoring_dir / "performance-report-latest.json"
        with open(latest_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.debug(f"Performance report saved: {report_file}")


def main():
    """
    Main function for monitoring setup CLI
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python monitoring_setup.py <command> [args]")
        print("Commands: health-check, performance-report, setup")
        sys.exit(1)

    command = sys.argv[1]
    config_file = sys.argv[2] if len(sys.argv) > 2 else "fogis-config.yaml"

    try:
        monitoring = MonitoringSetup(config_file)

        if command == "health-check":
            report = monitoring.run_health_check()
            print(f"Overall Status: {report['overall_status']}")
            print(f"Services: {len([s for s in report['services'].values() if s.get('status') == 'healthy'])} healthy")
            if report['issues']:
                print("Issues:")
                for issue in report['issues']:
                    print(f"  - {issue}")

        elif command == "performance-report":
            report = monitoring.generate_performance_report()
            print("Performance Report Generated")
            if report.get('recommendations'):
                print("Recommendations:")
                for rec in report['recommendations']:
                    print(f"  - {rec}")

        elif command == "setup":
            print("Setting up monitoring...")
            # Create monitoring directory and initial configuration
            monitoring.monitoring_dir.mkdir(exist_ok=True)
            print(f"Monitoring directory created: {monitoring.monitoring_dir}")

            # Run initial health check
            monitoring.run_health_check()
            print("Initial health check completed")

            # Generate initial performance report
            monitoring.generate_performance_report()
            print("Initial performance report generated")

            print("Monitoring setup completed successfully")

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
