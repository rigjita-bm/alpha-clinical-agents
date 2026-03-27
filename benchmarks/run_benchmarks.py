"""
Benchmark suite for Alpha Clinical Agents
Performance testing and comparison metrics
"""

import sys
from pathlib import Path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

import time
import json
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import statistics

# Import sample protocols directly
import importlib.util
spec = importlib.util.spec_from_file_location(
    "sample_protocols", 
    f"{project_root}/data/sample_protocols/__init__.py"
)
sample_protocols = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sample_protocols)

ONCOLOGY_PHASE3_PROTOCOL = sample_protocols.ONCOLOGY_PHASE3_PROTOCOL
CARDIOLOGY_PHASE2_PROTOCOL = sample_protocols.CARDIOLOGY_PHASE2_PROTOCOL
RARE_DISEASE_PHASE2_PROTOCOL = sample_protocols.RARE_DISEASE_PHASE2_PROTOCOL

from agents import (
    ProtocolAnalyzer, SectionWriter, StatisticalValidator,
    ComplianceChecker, CrossReferenceValidator, HallucinationDetector
)


@dataclass
class BenchmarkResult:
    """Result of a benchmark run"""
    test_name: str
    duration_seconds: float
    success: bool
    metrics: Dict[str, Any]
    timestamp: datetime


class AlphaClinicalBenchmarks:
    """
    Benchmark suite for measuring system performance
    and hallucination detection effectiveness
    """
    
    def __init__(self):
        self.results: List[BenchmarkResult] = []
        
    def run_all_benchmarks(self) -> Dict[str, Any]:
        """Run complete benchmark suite"""
        print("=" * 70)
        print("ALPHA CLINICAL AGENTS - BENCHMARK SUITE")
        print("=" * 70)
        
        benchmarks = [
            ("protocol_analysis_speed", self.benchmark_protocol_analysis),
            ("statistical_validation_accuracy", self.benchmark_statistical_validation),
            ("compliance_check_speed", self.benchmark_compliance_check),
            ("hallucination_detection_rate", self.benchmark_hallucination_detection),
            ("end_to_end_workflow", self.benchmark_end_to_end),
        ]
        
        for name, benchmark_func in benchmarks:
            print(f"\n[Running] {name}...")
            try:
                result = benchmark_func()
                self.results.append(result)
                status = "✅ PASS" if result.success else "❌ FAIL"
                print(f"  {status}: {result.duration_seconds:.2f}s")
            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                self.results.append(BenchmarkResult(
                    test_name=name,
                    duration_seconds=0,
                    success=False,
                    metrics={"error": str(e)},
                    timestamp=datetime.now()
                ))
        
        return self.generate_report()
    
    def benchmark_protocol_analysis(self) -> BenchmarkResult:
        """Benchmark protocol analysis speed and accuracy"""
        start_time = time.time()
        
        analyzer = ProtocolAnalyzer()
        
        protocols = [
            ("oncology_phase3", ONCOLOGY_PHASE3_PROTOCOL),
            ("cardiology_phase2", CARDIOLOGY_PHASE2_PROTOCOL),
            ("rare_disease", RARE_DISEASE_PHASE2_PROTOCOL),
        ]
        
        results = []
        for name, protocol in protocols:
            result = analyzer.execute({"protocol_text": protocol})
            results.append({
                "protocol": name,
                "phase": result.get("phase"),
                "enrollment": result.get("planned_enrollment"),
                "confidence": result.get("extraction_confidence"),
                "complexity": result.get("complexity_score")
            })
        
        duration = time.time() - start_time
        
        # Check accuracy
        all_confident = all(r["confidence"] > 0.8 for r in results)
        
        return BenchmarkResult(
            test_name="protocol_analysis_speed",
            duration_seconds=duration,
            success=all_confident,
            metrics={
                "protocols_analyzed": len(protocols),
                "avg_confidence": statistics.mean(r["confidence"] for r in results),
                "results": results
            },
            timestamp=datetime.now()
        )
    
    def benchmark_statistical_validation(self) -> BenchmarkResult:
        """Benchmark statistical validation accuracy"""
        start_time = time.time()
        
        validator = StatisticalValidator()
        
        # Test cases with known correct/incorrect statistics
        test_cases = [
            # Valid statistics
            {
                "name": "valid_p_value",
                "section": {"statistics": {"p_value": 0.03}},
                "expected_valid": True
            },
            {
                "name": "invalid_p_value",
                "section": {"statistics": {"p_value": 1.5}},  # Invalid
                "expected_valid": False
            },
            {
                "name": "valid_hr",
                "section": {"statistics": {"hazard_ratio": 0.72, "ci_lower": 0.58, "ci_upper": 0.89}},
                "expected_valid": True
            },
            {
                "name": "invalid_percentage",
                "section": {"text": "Response rate was 145%"},  # Impossible
                "expected_valid": False
            },
            {
                "name": "inconsistent_ci",
                "section": {"statistics": {"hazard_ratio": 0.5, "ci_lower": 0.6, "ci_upper": 0.9}},  # HR outside CI
                "expected_valid": False
            },
        ]
        
        correct_detections = 0
        for test in test_cases:
            result = validator.execute({"sections": {"test": test["section"]}})
            
            # Determine if validation correctly identified the issue
            has_errors = any(
                finding.get("severity") in ["critical", "major"]
                for finding in result.get("findings", [])
            )
            
            if has_errors == (not test["expected_valid"]):
                correct_detections += 1
        
        duration = time.time() - start_time
        accuracy = correct_detections / len(test_cases)
        
        return BenchmarkResult(
            test_name="statistical_validation_accuracy",
            duration_seconds=duration,
            success=accuracy >= 0.8,
            metrics={
                "test_cases": len(test_cases),
                "correct_detections": correct_detections,
                "accuracy": accuracy
            },
            timestamp=datetime.now()
        )
    
    def benchmark_compliance_check(self) -> BenchmarkResult:
        """Benchmark compliance checking speed"""
        start_time = time.time()
        
        checker = ComplianceChecker()
        
        # Non-compliant document
        non_compliant = {
            "drafts": {
                "TitlePage": {"signed_by": None},  # Missing signature
                "Results": {"text": "The drug proves efficacy"}  # Prohibited term
            }
        }
        
        # Compliant document
        compliant = {
            "drafts": {
                "TitlePage": {
                    "signed_by": "Dr. Smith",
                    "signature_date": "2026-03-27",
                    "signature_hash": "abc123"
                },
                "Results": {"text": "The drug showed efficacy"}
            }
        }
        
        result_non_compliant = checker.execute(non_compliant)
        result_compliant = checker.execute(compliant)
        
        duration = time.time() - start_time
        
        # Verify correct detection
        non_compliant_detected = result_non_compliant["compliance_score"] < 50
        compliant_detected = result_compliant["compliance_score"] > 80
        
        return BenchmarkResult(
            test_name="compliance_check_speed",
            duration_seconds=duration,
            success=non_compliant_detected and compliant_detected,
            metrics={
                "non_compliant_score": result_non_compliant["compliance_score"],
                "compliant_score": result_compliant["compliance_score"],
                "critical_issues_detected": len(result_non_compliant.get("critical_issues", []))
            },
            timestamp=datetime.now()
        )
    
    def benchmark_hallucination_detection(self) -> BenchmarkResult:
        """Benchmark hallucination detection effectiveness"""
        start_time = time.time()
        
        detector = HallucinationDetector()
        
        # Test cases with fabricated information
        test_cases = [
            {
                "name": "fabricated_number",
                "text": "The study enrolled 850 patients",  # Protocol says 600
                "protocol": ONCOLOGY_PHASE3_PROTOCOL,
                "expected_hallucination": True
            },
            {
                "name": "fabricated_endpoint",
                "text": "The primary endpoint was disease-free survival",  # Protocol says OS
                "protocol": ONCOLOGY_PHASE3_PROTOCOL,
                "expected_hallucination": True
            },
            {
                "name": "correct_statement",
                "text": "The planned enrollment was 600 patients",  # Matches protocol
                "protocol": ONCOLOGY_PHASE3_PROTOCOL,
                "expected_hallucination": False
            },
        ]
        
        correct_detections = 0
        for test in test_cases:
            result = detector.execute({
                "text": test["text"],
                "protocol": test["protocol"]
            })
            
            has_hallucination = len(result.get("findings", [])) > 0
            
            if has_hallucination == test["expected_hallucination"]:
                correct_detections += 1
        
        duration = time.time() - start_time
        accuracy = correct_detections / len(test_cases)
        
        return BenchmarkResult(
            test_name="hallucination_detection_rate",
            duration_seconds=duration,
            success=accuracy >= 0.8,
            metrics={
                "test_cases": len(test_cases),
                "correct_detections": correct_detections,
                "accuracy": accuracy,
                "target_accuracy": 0.95
            },
            timestamp=datetime.now()
        )
    
    def benchmark_end_to_end(self) -> BenchmarkResult:
        """Benchmark complete workflow"""
        start_time = time.time()
        
        # Simple 3-agent workflow
        from core.orchestrator import ClinicalOrchestrator
        
        orchestrator = ClinicalOrchestrator()
        orchestrator.register_agent(ProtocolAnalyzer())
        orchestrator.register_agent(SectionWriter())
        orchestrator.register_agent(StatisticalValidator())
        
        result = orchestrator.execute_workflow({
            "protocol_text": ONCOLOGY_PHASE3_PROTOCOL[:1000]  # Truncated for speed
        })
        
        duration = time.time() - start_time
        
        return BenchmarkResult(
            test_name="end_to_end_workflow",
            duration_seconds=duration,
            success=result.get("status") == "completed",
            metrics={
                "stages_completed": len(result.get("state", {}).get("stage_history", [])),
                "final_status": result.get("status")
            },
            timestamp=datetime.now()
        )
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive benchmark report"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        total_duration = sum(r.duration_seconds for r in self.results)
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": total_tests - passed_tests,
                "pass_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "total_duration_seconds": round(total_duration, 2),
                "timestamp": datetime.now().isoformat()
            },
            "detailed_results": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "duration_seconds": round(r.duration_seconds, 3),
                    "metrics": r.metrics
                }
                for r in self.results
            ],
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        # Check for slow tests
        slow_tests = [r for r in self.results if r.duration_seconds > 5]
        if slow_tests:
            recommendations.append(
                f"Consider optimizing: {', '.join(t.test_name for t in slow_tests)} "
                "took >5 seconds"
            )
        
        # Check failed tests
        failed_tests = [r for r in self.results if not r.success]
        if failed_tests:
            recommendations.append(
                f"Fix failing tests: {', '.join(t.test_name for t in failed_tests)}"
            )
        
        if not recommendations:
            recommendations.append("All benchmarks passed! System is performing well.")
        
        return recommendations
    
    def save_report(self, filepath: str = "benchmark_report.json"):
        """Save benchmark report to file"""
        report = self.generate_report()
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n📊 Report saved to {filepath}")


def main():
    """Run benchmarks from command line"""
    benchmarks = AlphaClinicalBenchmarks()
    report = benchmarks.run_all_benchmarks()
    
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"Passed: {report['summary']['passed']} ✅")
    print(f"Failed: {report['summary']['failed']} ❌")
    print(f"Pass Rate: {report['summary']['pass_rate']*100:.1f}%")
    print(f"Total Duration: {report['summary']['total_duration_seconds']:.2f}s")
    print("\nRecommendations:")
    for rec in report['recommendations']:
        print(f"  • {rec}")
    
    benchmarks.save_report()


if __name__ == "__main__":
    main()
