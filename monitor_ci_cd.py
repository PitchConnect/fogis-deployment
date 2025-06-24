#!/usr/bin/env python3
"""
CI/CD Performance Monitoring Script for FOGIS.
Tracks build times, success rates, and performance metrics.
"""

import requests
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

class CICDMonitor:
    """Monitor CI/CD pipeline performance and health."""
    
    def __init__(self, repo: str = "PitchConnect/fogis-deployment"):
        self.repo = repo
        self.api_base = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "FOGIS-CI-Monitor"
        }
        
        # Add GitHub token if available
        github_token = self.get_github_token()
        if github_token:
            self.headers["Authorization"] = f"token {github_token}"
    
    def get_github_token(self) -> Optional[str]:
        """Get GitHub token from environment or file."""
        import os
        
        # Try environment variable first
        token = os.getenv("GITHUB_TOKEN")
        if token:
            return token
        
        # Try token file
        token_file = Path.home() / ".github_token"
        if token_file.exists():
            return token_file.read_text().strip()
        
        return None
    
    def get_workflow_runs(self, days: int = 7) -> List[Dict]:
        """Get workflow runs from the last N days."""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        url = f"{self.api_base}/repos/{self.repo}/actions/runs"
        params = {
            "created": f">={since}",
            "per_page": 100
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get("workflow_runs", [])
        except requests.RequestException as e:
            print(f"❌ Failed to fetch workflow runs: {e}")
            return []
    
    def get_workflow_details(self, run_id: int) -> Optional[Dict]:
        """Get detailed information about a specific workflow run."""
        url = f"{self.api_base}/repos/{self.repo}/actions/runs/{run_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ Failed to fetch workflow details for {run_id}: {e}")
            return None
    
    def analyze_build_performance(self, runs: List[Dict]) -> Dict:
        """Analyze build performance metrics."""
        if not runs:
            return {}
        
        # Filter for completed runs
        completed_runs = [r for r in runs if r["status"] == "completed"]
        
        if not completed_runs:
            return {"error": "No completed runs found"}
        
        # Calculate metrics
        total_runs = len(completed_runs)
        successful_runs = len([r for r in completed_runs if r["conclusion"] == "success"])
        failed_runs = len([r for r in completed_runs if r["conclusion"] == "failure"])
        
        success_rate = (successful_runs / total_runs) * 100 if total_runs > 0 else 0
        
        # Calculate average duration for successful runs
        successful_durations = []
        for run in completed_runs:
            if run["conclusion"] == "success":
                created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
                updated = datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00"))
                duration = (updated - created).total_seconds()
                successful_durations.append(duration)
        
        avg_duration = sum(successful_durations) / len(successful_durations) if successful_durations else 0
        
        # Group by workflow
        workflow_stats = {}
        for run in completed_runs:
            workflow_name = run["name"]
            if workflow_name not in workflow_stats:
                workflow_stats[workflow_name] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "durations": []
                }
            
            workflow_stats[workflow_name]["total"] += 1
            if run["conclusion"] == "success":
                workflow_stats[workflow_name]["successful"] += 1
                created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
                updated = datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00"))
                duration = (updated - created).total_seconds()
                workflow_stats[workflow_name]["durations"].append(duration)
            elif run["conclusion"] == "failure":
                workflow_stats[workflow_name]["failed"] += 1
        
        return {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "success_rate": success_rate,
            "average_duration_seconds": avg_duration,
            "average_duration_minutes": avg_duration / 60,
            "workflow_stats": workflow_stats
        }
    
    def check_recent_failures(self, runs: List[Dict]) -> List[Dict]:
        """Check for recent workflow failures."""
        recent_failures = []
        
        for run in runs:
            if run["conclusion"] == "failure":
                recent_failures.append({
                    "id": run["id"],
                    "name": run["name"],
                    "created_at": run["created_at"],
                    "html_url": run["html_url"],
                    "head_branch": run["head_branch"],
                    "event": run["event"]
                })
        
        return recent_failures
    
    def generate_health_report(self, metrics: Dict, failures: List[Dict]) -> str:
        """Generate a health report."""
        report = []
        report.append("# FOGIS CI/CD Health Report")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        if "error" in metrics:
            report.append(f"❌ **Error**: {metrics['error']}")
            return "\n".join(report)
        
        # Overall health
        success_rate = metrics.get("success_rate", 0)
        if success_rate >= 90:
            health_status = "🟢 Excellent"
        elif success_rate >= 75:
            health_status = "🟡 Good"
        elif success_rate >= 50:
            health_status = "🟠 Fair"
        else:
            health_status = "🔴 Poor"
        
        report.append(f"## Overall Health: {health_status}")
        report.append("")
        
        # Key metrics
        report.append("## Key Metrics")
        report.append(f"- **Success Rate**: {success_rate:.1f}%")
        report.append(f"- **Total Runs**: {metrics.get('total_runs', 0)}")
        report.append(f"- **Successful**: {metrics.get('successful_runs', 0)}")
        report.append(f"- **Failed**: {metrics.get('failed_runs', 0)}")
        report.append(f"- **Average Duration**: {metrics.get('average_duration_minutes', 0):.1f} minutes")
        report.append("")
        
        # Workflow breakdown
        workflow_stats = metrics.get("workflow_stats", {})
        if workflow_stats:
            report.append("## Workflow Performance")
            for workflow, stats in workflow_stats.items():
                total = stats["total"]
                successful = stats["successful"]
                rate = (successful / total * 100) if total > 0 else 0
                avg_duration = sum(stats["durations"]) / len(stats["durations"]) if stats["durations"] else 0
                
                report.append(f"### {workflow}")
                report.append(f"- Success Rate: {rate:.1f}%")
                report.append(f"- Runs: {successful}/{total}")
                report.append(f"- Avg Duration: {avg_duration/60:.1f} minutes")
                report.append("")
        
        # Recent failures
        if failures:
            report.append("## Recent Failures")
            for failure in failures[:5]:  # Show last 5 failures
                report.append(f"- **{failure['name']}** ({failure['created_at']})")
                report.append(f"  - Branch: {failure['head_branch']}")
                report.append(f"  - Event: {failure['event']}")
                report.append(f"  - [View Details]({failure['html_url']})")
                report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        if success_rate < 90:
            report.append("- 🔍 Investigate recent failures")
            report.append("- 🔧 Review workflow configurations")
        
        avg_duration = metrics.get("average_duration_minutes", 0)
        if avg_duration > 10:
            report.append("- ⚡ Consider optimizing build times")
            report.append("- 💾 Review caching strategies")
        
        if not failures:
            report.append("- ✅ CI/CD pipeline is healthy")
            report.append("- 📈 Continue monitoring performance")
        
        return "\n".join(report)
    
    def run_monitoring(self, days: int = 7) -> bool:
        """Run complete monitoring analysis."""
        print("📊 FOGIS CI/CD Performance Monitor")
        print("=" * 40)
        
        print(f"📅 Analyzing last {days} days...")
        
        # Get workflow runs
        runs = self.get_workflow_runs(days)
        if not runs:
            print("❌ No workflow runs found")
            return False
        
        print(f"📋 Found {len(runs)} workflow runs")
        
        # Analyze performance
        metrics = self.analyze_build_performance(runs)
        failures = self.check_recent_failures(runs)
        
        # Generate report
        report = self.generate_health_report(metrics, failures)
        
        # Save report
        report_file = f"ci_cd_health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, "w") as f:
            f.write(report)
        
        print(f"📄 Report saved to: {report_file}")
        
        # Print summary
        if "error" not in metrics:
            success_rate = metrics.get("success_rate", 0)
            print(f"\n📊 Summary:")
            print(f"  Success Rate: {success_rate:.1f}%")
            print(f"  Total Runs: {metrics.get('total_runs', 0)}")
            print(f"  Average Duration: {metrics.get('average_duration_minutes', 0):.1f} minutes")
            
            if failures:
                print(f"  Recent Failures: {len(failures)}")
            
            return success_rate >= 75  # Consider 75%+ as healthy
        else:
            print(f"❌ Analysis failed: {metrics['error']}")
            return False

def main():
    """Main monitoring execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor FOGIS CI/CD performance")
    parser.add_argument("--days", type=int, default=7, help="Days to analyze (default: 7)")
    parser.add_argument("--repo", default="PitchConnect/fogis-deployment", help="Repository to monitor")
    
    args = parser.parse_args()
    
    monitor = CICDMonitor(args.repo)
    
    if monitor.run_monitoring(args.days):
        print("\n✅ CI/CD pipeline is healthy!")
        sys.exit(0)
    else:
        print("\n⚠️ CI/CD pipeline needs attention!")
        sys.exit(1)

if __name__ == "__main__":
    main()
