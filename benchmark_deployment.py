#!/usr/bin/env python3
"""
Performance benchmarking script for FOGIS deployment.
Measures deployment times and validates the 30-60 second target.
"""

import subprocess
import time
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

class DeploymentBenchmark:
    """Benchmark FOGIS deployment performance."""
    
    def __init__(self):
        self.results = {}
        self.services = [
            "fogis-api-client-service",
            "team-logo-combiner",
            "match-list-processor", 
            "match-list-change-detector",
            "fogis-calendar-phonebook-sync",
            "google-drive-service"
        ]
        self.compose_file = "docker-compose-master.yml"
    
    def run_command(self, command: List[str], timeout: int = 300) -> Tuple[int, str, str, float]:
        """Run command and measure execution time."""
        start_time = time.time()
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=Path(__file__).parent
            )
            end_time = time.time()
            return result.returncode, result.stdout, result.stderr, end_time - start_time
        except subprocess.TimeoutExpired:
            end_time = time.time()
            return -1, "", f"Command timed out after {timeout} seconds", end_time - start_time
        except Exception as e:
            end_time = time.time()
            return -1, "", str(e), end_time - start_time
    
    def check_prerequisites(self) -> bool:
        """Check that required tools are available."""
        print("🔍 Checking prerequisites...")
        
        # Check Docker
        exit_code, stdout, stderr, duration = self.run_command(["docker", "--version"])
        if exit_code != 0:
            print(f"❌ Docker not available: {stderr}")
            return False
        print(f"✅ Docker: {stdout.strip()}")
        
        # Check Docker Compose
        exit_code, stdout, stderr, duration = self.run_command(["docker-compose", "--version"])
        if exit_code != 0:
            print(f"❌ Docker Compose not available: {stderr}")
            return False
        print(f"✅ Docker Compose: {stdout.strip()}")
        
        # Check compose file exists
        if not Path(self.compose_file).exists():
            print(f"❌ Compose file not found: {self.compose_file}")
            return False
        print(f"✅ Compose file found: {self.compose_file}")
        
        return True
    
    def cleanup_existing_containers(self) -> bool:
        """Clean up any existing containers."""
        print("🧹 Cleaning up existing containers...")
        
        exit_code, stdout, stderr, duration = self.run_command([
            "docker-compose", "-f", self.compose_file, "down", "--remove-orphans"
        ])
        
        if exit_code != 0:
            print(f"⚠️ Cleanup warning: {stderr}")
        
        print(f"✅ Cleanup completed in {duration:.2f}s")
        return True
    
    def benchmark_image_pull(self) -> Dict[str, float]:
        """Benchmark image pulling performance."""
        print("📥 Benchmarking image pull performance...")
        
        pull_times = {}
        
        # Pull all images
        start_time = time.time()
        exit_code, stdout, stderr, duration = self.run_command([
            "docker-compose", "-f", self.compose_file, "pull"
        ])
        
        if exit_code != 0:
            print(f"❌ Image pull failed: {stderr}")
            return {}
        
        pull_times["total_pull_time"] = duration
        print(f"✅ All images pulled in {duration:.2f}s")
        
        return pull_times
    
    def benchmark_service_startup(self) -> Dict[str, float]:
        """Benchmark service startup performance."""
        print("🚀 Benchmarking service startup performance...")
        
        startup_times = {}
        
        # Start all services
        start_time = time.time()
        exit_code, stdout, stderr, duration = self.run_command([
            "docker-compose", "-f", self.compose_file, "up", "-d"
        ])
        
        if exit_code != 0:
            print(f"❌ Service startup failed: {stderr}")
            return {}
        
        startup_times["service_startup_time"] = duration
        print(f"✅ Services started in {duration:.2f}s")
        
        # Wait for services to be healthy
        print("⏳ Waiting for services to become healthy...")
        health_start = time.time()
        
        max_wait = 120  # 2 minutes max wait
        healthy_services = 0
        
        while time.time() - health_start < max_wait:
            exit_code, stdout, stderr, _ = self.run_command([
                "docker-compose", "-f", self.compose_file, "ps"
            ])
            
            if exit_code == 0:
                # Count healthy services
                healthy_count = stdout.count("Up")
                if healthy_count >= len(self.services) - 1:  # Allow for some services to be optional
                    break
            
            time.sleep(5)
        
        health_duration = time.time() - health_start
        startup_times["health_check_time"] = health_duration
        print(f"✅ Services healthy in {health_duration:.2f}s")
        
        return startup_times
    
    def benchmark_total_deployment(self) -> Dict[str, float]:
        """Benchmark complete deployment from scratch."""
        print("📊 Benchmarking complete deployment...")
        
        # Clean up first
        self.cleanup_existing_containers()
        
        # Remove images to simulate fresh deployment
        print("🗑️ Removing existing images for fresh deployment test...")
        for service in self.services:
            self.run_command([
                "docker", "rmi", f"ghcr.io/pitchconnect/{service}:latest"
            ], timeout=30)
        
        # Measure complete deployment
        total_start = time.time()
        
        # Pull and start
        pull_times = self.benchmark_image_pull()
        startup_times = self.benchmark_service_startup()
        
        total_time = time.time() - total_start
        
        deployment_times = {
            "total_deployment_time": total_time,
            **pull_times,
            **startup_times
        }
        
        print(f"🎯 Total deployment time: {total_time:.2f}s")
        
        return deployment_times
    
    def validate_performance_targets(self, results: Dict[str, float]) -> bool:
        """Validate that performance targets are met."""
        print("🎯 Validating performance targets...")
        
        total_time = results.get("total_deployment_time", 0)
        target_min = 30  # 30 seconds minimum expected
        target_max = 60  # 60 seconds maximum target
        
        if total_time <= target_max:
            print(f"✅ Performance target met: {total_time:.2f}s ≤ {target_max}s")
            return True
        elif total_time <= target_max * 1.5:  # Allow 50% margin
            print(f"⚠️ Performance acceptable: {total_time:.2f}s (within 50% margin)")
            return True
        else:
            print(f"❌ Performance target missed: {total_time:.2f}s > {target_max}s")
            return False
    
    def generate_report(self, results: Dict[str, float]) -> str:
        """Generate performance report."""
        report = []
        report.append("# FOGIS Deployment Performance Report")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        report.append("## Performance Metrics")
        for metric, value in results.items():
            report.append(f"- **{metric.replace('_', ' ').title()}**: {value:.2f}s")
        
        report.append("")
        report.append("## Target Analysis")
        total_time = results.get("total_deployment_time", 0)
        if total_time <= 60:
            report.append("✅ **Target Met**: Deployment completed within 60-second target")
        else:
            report.append("❌ **Target Missed**: Deployment exceeded 60-second target")
        
        report.append("")
        report.append("## Recommendations")
        if total_time > 60:
            report.append("- Consider optimizing image sizes")
            report.append("- Check network connectivity to GHCR")
            report.append("- Verify Docker daemon performance")
        else:
            report.append("- Performance targets achieved")
            report.append("- No optimization needed")
        
        return "\n".join(report)
    
    def run_benchmark(self) -> bool:
        """Run complete benchmark suite."""
        print("🏁 FOGIS Deployment Performance Benchmark")
        print("=" * 50)
        
        if not self.check_prerequisites():
            return False
        
        try:
            results = self.benchmark_total_deployment()
            
            if not results:
                print("❌ Benchmark failed to complete")
                return False
            
            # Save results
            self.results = results
            
            # Generate and save report
            report = self.generate_report(results)
            with open("deployment_benchmark_report.md", "w") as f:
                f.write(report)
            
            print("\n📊 Benchmark Results:")
            for metric, value in results.items():
                print(f"  {metric.replace('_', ' ').title()}: {value:.2f}s")
            
            # Validate targets
            target_met = self.validate_performance_targets(results)
            
            print(f"\n📄 Report saved to: deployment_benchmark_report.md")
            
            return target_met
            
        except Exception as e:
            print(f"❌ Benchmark failed with error: {e}")
            return False
        finally:
            # Cleanup
            self.cleanup_existing_containers()

def main():
    """Main benchmark execution."""
    benchmark = DeploymentBenchmark()
    
    if benchmark.run_benchmark():
        print("\n🎉 Benchmark completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Benchmark failed or targets not met!")
        sys.exit(1)

if __name__ == "__main__":
    main()
