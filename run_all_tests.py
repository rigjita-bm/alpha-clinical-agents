#!/usr/bin/env python3
"""
Alpha Clinical Agents - Master Test Runner
Executes all 1000+ test simulations and generates comprehensive report
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Import test modules
sys.path.insert(0, str(Path(__file__).parent))

from test_simulator_1000 import TestSimulator, TestSuiteReport
from test_scenarios import ScenarioSimulator, ScenarioResult
from test_load import LoadTester, LoadTestResult

class MasterTestRunner:
    """Orchestrates all test suites"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_dir = Path("test_reports")
        self.report_dir.mkdir(exist_ok=True)
        
    async def run_all_tests(self):
        """Execute complete test suite"""
        print("=" * 100)
        print("🧪 ALPHA CLINICAL AGENTS - MASTER TEST SUITE")
        print("   1000+ Comprehensive Test Simulations")
        print("=" * 100)
        print()
        
        overall_start = datetime.now()
        
        # Test Suite 1: 1000+ Unit & Integration Tests
        print("📦 TEST SUITE 1: Comprehensive Test Simulator (1000+ tests)")
        print("-" * 100)
        simulator = TestSimulator()
        suite1_report = await simulator.run_all_tests()
        suite1_details = simulator.generate_report(suite1_report)
        
        # Test Suite 2: Scenario-Based Tests
        print("\n📦 TEST SUITE 2: Scenario-Based Tests (24 scenarios)")
        print("-" * 100)
        scenario_sim = ScenarioSimulator()
        suite2_results = await scenario_sim.run_all_scenarios()
        
        # Test Suite 3: Load & Stress Tests
        print("\n📦 TEST SUITE 3: Load & Stress Tests (20 load profiles)")
        print("-" * 100)
        load_tester = LoadTester()
        suite3_results = await load_tester.run_all_load_tests()
        
        overall_duration = (datetime.now() - overall_start).total_seconds()
        
        # Generate master report
        master_report = self._generate_master_report(
            suite1_details,
            suite2_results,
            suite3_results,
            overall_duration
        )
        
        # Print summary
        self._print_master_summary(master_report)
        
        # Save reports
        self._save_reports(master_report, suite1_details, suite2_results, suite3_results)
        
        return master_report
    
    def _generate_master_report(self, suite1: dict, suite2: list, suite3: list, duration: float) -> dict:
        """Generate comprehensive master report"""
        
        # Suite 2 stats
        s2_passed = sum(1 for r in suite2 if r.success)
        s2_failed = len(suite2) - s2_passed
        
        # Suite 3 stats
        s3_total_req = sum(r.total_requests for r in suite3)
        s3_success = sum(r.successful for r in suite3)
        s3_failed = sum(r.failed for r in suite3)
        
        # Calculate overall health score
        s1_rate = suite1['summary']['success_rate']
        s2_rate = (s2_passed / len(suite2)) * 100 if suite2 else 0
        s3_rate = (s3_success / s3_total_req) * 100 if s3_total_req else 0
        
        # Weighted average (Unit tests 40%, Scenarios 30%, Load 30%)
        health_score = (s1_rate * 0.4) + (s2_rate * 0.3) + (s3_rate * 0.3)
        
        return {
            "meta": {
                "timestamp": datetime.now().isoformat(),
                "total_duration_sec": round(duration, 2),
                "test_framework_version": "2.0.0"
            },
            "summary": {
                "total_tests": suite1['summary']['total_tests'] + len(suite2) + len(suite3),
                "total_requests": s3_total_req,
                "suite_1_unit_tests": {
                    "total": suite1['summary']['total_tests'],
                    "passed": suite1['summary']['passed'],
                    "failed": suite1['summary']['failed'],
                    "success_rate": s1_rate
                },
                "suite_2_scenarios": {
                    "total": len(suite2),
                    "passed": s2_passed,
                    "failed": s2_failed,
                    "success_rate": round(s2_rate, 2)
                },
                "suite_3_load_tests": {
                    "total_load_tests": len(suite3),
                    "total_requests": s3_total_req,
                    "successful": s3_success,
                    "failed": s3_failed,
                    "success_rate": round(s3_rate, 2)
                },
                "overall_health_score": round(health_score, 2),
                "grade": self._calculate_grade(health_score)
            },
            "breakdown_by_category": suite1['category_breakdown'],
            "performance_metrics": {
                "avg_test_duration_ms": suite1['duration_statistics']['mean_ms'],
                "max_test_duration_ms": suite1['duration_statistics']['max_ms'],
                "load_test_throughput_rps": round(
                    sum(r.throughput_rps for r in suite3) / len(suite3), 2
                ) if suite3 else 0
            }
        }
    
    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score"""
        if score >= 95:
            return "A+ (Excellent)"
        elif score >= 90:
            return "A (Very Good)"
        elif score >= 85:
            return "B+ (Good)"
        elif score >= 80:
            return "B (Acceptable)"
        elif score >= 70:
            return "C (Needs Improvement)"
        else:
            return "D (Critical Issues)"
    
    def _print_master_summary(self, report: dict):
        """Print formatted master summary"""
        s = report['summary']
        
        print("\n" + "=" * 100)
        print("📊 MASTER TEST REPORT")
        print("=" * 100)
        
        print(f"\n🎯 OVERALL HEALTH SCORE: {s['overall_health_score']}%")
        print(f"   Grade: {s['grade']}")
        print(f"   Duration: {report['meta']['total_duration_sec']:.1f} seconds")
        
        print("\n" + "-" * 100)
        print("📦 TEST SUITE BREAKDOWN")
        print("-" * 100)
        
        # Suite 1
        s1 = s['suite_1_unit_tests']
        s1_status = "✅" if s1['success_rate'] >= 90 else "⚠️" if s1['success_rate'] >= 80 else "❌"
        print(f"\n{s1_status} Suite 1 - Unit & Integration Tests")
        print(f"   Tests:     {s1['total']}")
        print(f"   Passed:    {s1['passed']} ({s1['success_rate']:.1f}%)")
        print(f"   Failed:    {s1['failed']}")
        
        # Suite 2
        s2 = s['suite_2_scenarios']
        s2_status = "✅" if s2['success_rate'] >= 90 else "⚠️" if s2['success_rate'] >= 80 else "❌"
        print(f"\n{s2_status} Suite 2 - Scenario-Based Tests")
        print(f"   Scenarios: {s2['total']}")
        print(f"   Passed:    {s2['passed']} ({s2['success_rate']:.1f}%)")
        print(f"   Failed:    {s2['failed']}")
        
        # Suite 3
        s3 = s['suite_3_load_tests']
        s3_status = "✅" if s3['success_rate'] >= 90 else "⚠️" if s3['success_rate'] >= 80 else "❌"
        print(f"\n{s3_status} Suite 3 - Load & Stress Tests")
        print(f"   Profiles:  {s3['total_load_tests']}")
        print(f"   Requests:  {s3['total_requests']:,}")
        print(f"   Success:   {s3['successful']:,} ({s3['success_rate']:.1f}%)")
        print(f"   Failed:    {s3['failed']:,}")
        
        # Performance
        print("\n" + "-" * 100)
        print("⚡ PERFORMANCE METRICS")
        print("-" * 100)
        pm = report['performance_metrics']
        print(f"   Average Test Duration:    {pm['avg_test_duration_ms']:.1f} ms")
        print(f"   Slowest Test:             {pm['max_test_duration_ms']:.1f} ms")
        print(f"   Load Test Throughput:     {pm['load_test_throughput_rps']:.1f} req/s")
        
        # Category breakdown
        print("\n" + "-" * 100)
        print("📁 CATEGORY BREAKDOWN (Suite 1)")
        print("-" * 100)
        for cat, stats in report['breakdown_by_category'].items():
            rate = (stats['passed'] / stats['total']) * 100
            status = "✅" if rate >= 90 else "⚠️" if rate >= 80 else "❌"
            print(f"   {status} {cat:<20s}: {stats['passed']:3d}/{stats['total']:3d} ({rate:5.1f}%)")
        
        # Final verdict
        print("\n" + "=" * 100)
        if s['overall_health_score'] >= 90:
            print("✅ FINAL VERDICT: SYSTEM READY FOR PRODUCTION")
        elif s['overall_health_score'] >= 80:
            print("⚠️  FINAL VERDICT: SYSTEM ACCEPTABLE WITH MONITORING")
        else:
            print("❌ FINAL VERDICT: CRITICAL ISSUES MUST BE ADDRESSED")
        print("=" * 100)
    
    def _save_reports(self, master: dict, suite1: dict, suite2: list, suite3: list):
        """Save all reports to files"""
        timestamp = self.timestamp
        
        # Master report
        master_file = self.report_dir / f"master_report_{timestamp}.json"
        with open(master_file, 'w') as f:
            json.dump(master, f, indent=2)
        print(f"\n📄 Reports saved:")
        print(f"   • Master Report:     {master_file}")
        
        # Suite 1 detailed report
        suite1_file = self.report_dir / f"unit_tests_{timestamp}.json"
        with open(suite1_file, 'w') as f:
            json.dump(suite1, f, indent=2)
        print(f"   • Unit Tests:        {suite1_file}")
        
        # Suite 2 summary
        suite2_summary = [
            {"name": r.scenario_name, "success": r.success, "errors": r.errors}
            for r in suite2
        ]
        suite2_file = self.report_dir / f"scenarios_{timestamp}.json"
        with open(suite2_file, 'w') as f:
            json.dump(suite2_summary, f, indent=2)
        print(f"   • Scenarios:         {suite2_file}")
        
        # Suite 3 summary
        suite3_summary = [
            {
                "name": r.test_name,
                "concurrent": r.concurrent_ops,
                "success_rate": round(r.successful / r.total_requests * 100, 1),
                "avg_latency_ms": round(r.avg_latency_ms, 1),
                "throughput_rps": round(r.throughput_rps, 1)
            }
            for r in suite3
        ]
        suite3_file = self.report_dir / f"load_tests_{timestamp}.json"
        with open(suite3_file, 'w') as f:
            json.dump(suite3_summary, f, indent=2)
        print(f"   • Load Tests:        {suite3_file}")
        
        # HTML Report
        html_file = self._generate_html_report(master, suite1, suite2, suite3)
        print(f"   • HTML Report:       {html_file}")
    
    def _generate_html_report(self, master: dict, suite1: dict, suite2: list, suite3: list) -> Path:
        """Generate HTML report"""
        timestamp = self.timestamp
        html_file = self.report_dir / f"test_report_{timestamp}.html"
        
        s = master['summary']
        health_color = "#4CAF50" if s['overall_health_score'] >= 90 else "#FF9800" if s['overall_health_score'] >= 80 else "#F44336"
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Alpha Clinical Agents - Test Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .score-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .score-value {{
            font-size: 48px;
            font-weight: bold;
            color: {health_color};
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h3 {{
            margin-top: 0;
            color: #333;
        }}
        .metric {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }}
        .pass {{
            color: #4CAF50;
            font-weight: bold;
        }}
        .fail {{
            color: #F44336;
            font-weight: bold;
        }}
        .warning {{
            color: #FF9800;
            font-weight: bold;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            text-align: left;
            padding: 10px;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 Alpha Clinical Agents - Test Report</h1>
        <p>Comprehensive Test Suite - 1000+ Simulations</p>
        <p>Generated: {master['meta']['timestamp']}</p>
    </div>
    
    <div class="grid">
        <div class="score-card">
            <h2>Overall Health Score</h2>
            <div class="score-value">{s['overall_health_score']:.1f}%</div>
            <p>Grade: <strong>{s['grade']}</strong></p>
        </div>
        
        <div class="card">
            <h3>📦 Test Suite Summary</h3>
            <div class="metric">
                <span>Unit Tests</span>
                <span class="{'pass' if s['suite_1_unit_tests']['success_rate'] >= 90 else 'warning' if s['suite_1_unit_tests']['success_rate'] >= 80 else 'fail'}">
                    {s['suite_1_unit_tests']['passed']}/{s['suite_1_unit_tests']['total']} ({s['suite_1_unit_tests']['success_rate']:.1f}%)
                </span>
            </div>
            <div class="metric">
                <span>Scenarios</span>
                <span class="{'pass' if s['suite_2_scenarios']['success_rate'] >= 90 else 'warning' if s['suite_2_scenarios']['success_rate'] >= 80 else 'fail'}">
                    {s['suite_2_scenarios']['passed']}/{s['suite_2_scenarios']['total']} ({s['suite_2_scenarios']['success_rate']:.1f}%)
                </span>
            </div>
            <div class="metric">
                <span>Load Tests</span>
                <span class="{'pass' if s['suite_3_load_tests']['success_rate'] >= 90 else 'warning' if s['suite_3_load_tests']['success_rate'] >= 80 else 'fail'}">
                    {s['suite_3_load_tests']['successful']:,}/{s['suite_3_load_tests']['total_requests']:,} ({s['suite_3_load_tests']['success_rate']:.1f}%)
                </span>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h3>📁 Category Breakdown</h3>
        <table>
            <tr>
                <th>Category</th>
                <th>Passed</th>
                <th>Total</th>
                <th>Rate</th>
            </tr>
"""
        
        for cat, stats in master['breakdown_by_category'].items():
            rate = (stats['passed'] / stats['total']) * 100
            html += f"""
            <tr>
                <td>{cat}</td>
                <td>{stats['passed']}</td>
                <td>{stats['total']}</td>
                <td class="{'pass' if rate >= 90 else 'warning' if rate >= 80 else 'fail'}">{rate:.1f}%</td>
            </tr>
"""
        
        html += """
        </table>
    </div>
    
    <div class="card">
        <h3>⚡ Performance Metrics</h3>
"""
        pm = master['performance_metrics']
        html += f"""
        <div class="metric">
            <span>Average Test Duration</span>
            <span>{pm['avg_test_duration_ms']:.1f} ms</span>
        </div>
        <div class="metric">
            <span>Load Test Throughput</span>
            <span>{pm['load_test_throughput_rps']:.1f} req/s</span>
        </div>
    </div>
    
    <footer style="text-align: center; margin-top: 40px; color: #666;">
        <p>Alpha Clinical Agents v2.0 - Test Framework</p>
    </footer>
</body>
</html>
"""
        
        with open(html_file, 'w') as f:
            f.write(html)
        
        return html_file


async def main():
    runner = MasterTestRunner()
    report = await runner.run_all_tests()
    return report


if __name__ == "__main__":
    asyncio.run(main())
