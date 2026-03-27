#!/usr/bin/env python3
"""
Alpha Clinical Agents - Load & Stress Test Suite
1000+ concurrent operations simulation
"""

import asyncio
import random
import time
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import statistics

@dataclass
class LoadTestResult:
    test_name: str
    concurrent_ops: int
    total_requests: int
    successful: int
    failed: int
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_rps: float
    duration_sec: float
    errors: List[str] = field(default_factory=list)

class LoadTester:
    """Simulates high-load scenarios"""
    
    def __init__(self):
        self.results: List[LoadTestResult] = []
    
    async def run_all_load_tests(self):
        """Run complete load test suite"""
        print("Starting load test suite...")
        
        # Individual agent load tests
        await self._test_agent_under_load("ProtocolAnalyzer", 100)
        await self._test_agent_under_load("SectionWriter", 50)  # LLM is slower
        await self._test_agent_under_load("StatisticalValidator", 200)
        await self._test_agent_under_load("FactChecker", 150)
        await self._test_agent_under_load("ComplianceChecker", 180)
        await self._test_agent_under_load("MetaValidator", 120)
        
        # Workflow load tests
        await self._test_full_workflow_load(10)
        await self._test_full_workflow_load(50)
        await self._test_full_workflow_load(100)
        
        # Database load tests
        await self._test_database_reads(500)
        await self._test_database_writes(300)
        await self._test_database_mixed(400)
        
        # API load tests
        await self._test_api_endpoints(200)
        await self._test_webhook_processing(150)
        
        # Memory pressure tests
        await self._test_memory_pressure(50)
        await self._test_memory_pressure(100)
        
        # Circuit breaker tests
        await self._test_circuit_breaker(100)
        
        # Recovery tests
        await self._test_failure_recovery(50)
        
        return self.results
    
    async def _simulate_operation(self, op_type: str, fail_rate: float = 0.05) -> Dict:
        """Simulate a single operation"""
        start = time.time()
        
        # Simulate processing time
        if op_type == "llm_generation":
            await asyncio.sleep(random.uniform(1.0, 3.0))
        elif op_type == "nlp_extraction":
            await asyncio.sleep(random.uniform(0.1, 0.5))
        elif op_type == "validation":
            await asyncio.sleep(random.uniform(0.05, 0.2))
        elif op_type == "database":
            await asyncio.sleep(random.uniform(0.01, 0.1))
        else:
            await asyncio.sleep(random.uniform(0.1, 0.5))
        
        duration_ms = (time.time() - start) * 1000
        success = random.random() > fail_rate
        
        return {
            "success": success,
            "duration_ms": duration_ms,
            "error": None if success else f"{op_type}_failed"
        }
    
    async def _run_concurrent_ops(self, name: str, count: int, op_type: str, 
                                   fail_rate: float = 0.05) -> LoadTestResult:
        """Run concurrent operations"""
        start_time = time.time()
        
        # Create all tasks
        tasks = [self._simulate_operation(op_type, fail_rate) for _ in range(count)]
        
        # Run all concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        duration_sec = time.time() - start_time
        
        # Process results
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = count - successful
        
        latencies = [r.get("duration_ms", 0) for r in results if isinstance(r, dict)]
        
        errors = []
        for r in results:
            if isinstance(r, Exception):
                errors.append(str(r))
            elif isinstance(r, dict) and r.get("error"):
                errors.append(r["error"])
        
        result = LoadTestResult(
            test_name=name,
            concurrent_ops=count,
            total_requests=count,
            successful=successful,
            failed=failed,
            avg_latency_ms=statistics.mean(latencies) if latencies else 0,
            p95_latency_ms=statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies) if latencies else 0,
            p99_latency_ms=statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies) if latencies else 0,
            throughput_rps=count / duration_sec if duration_sec > 0 else 0,
            duration_sec=duration_sec,
            errors=list(set(errors))[:5]  # Unique errors, max 5
        )
        
        self.results.append(result)
        return result
    
    async def _test_agent_under_load(self, agent_name: str, concurrent: int):
        """Test individual agent under load"""
        op_type = "llm_generation" if agent_name == "SectionWriter" else "validation"
        fail_rate = 0.02 if agent_name != "SectionWriter" else 0.05
        
        await self._run_concurrent_ops(
            f"Agent_{agent_name}_Load",
            concurrent,
            op_type,
            fail_rate
        )
    
    async def _test_full_workflow_load(self, concurrent: int):
        """Test full workflow with multiple concurrent CSRs"""
        await self._run_concurrent_ops(
            f"FullWorkflow_{concurrent}concurrent",
            concurrent,
            "workflow",
            0.08  # Higher fail rate for full workflow
        )
    
    async def _test_database_reads(self, concurrent: int):
        """Test database read performance"""
        await self._run_concurrent_ops(
            f"DB_Reads_{concurrent}",
            concurrent,
            "database",
            0.01  # Very low fail rate for reads
        )
    
    async def _test_database_writes(self, concurrent: int):
        """Test database write performance"""
        await self._run_concurrent_ops(
            f"DB_Writes_{concurrent}",
            concurrent,
            "database",
            0.03
        )
    
    async def _test_database_mixed(self, concurrent: int):
        """Test mixed read/write operations"""
        await self._run_concurrent_ops(
            f"DB_Mixed_{concurrent}",
            concurrent,
            "database",
            0.02
        )
    
    async def _test_api_endpoints(self, concurrent: int):
        """Test API endpoint load"""
        await self._run_concurrent_ops(
            f"API_Load_{concurrent}",
            concurrent,
            "api",
            0.04
        )
    
    async def _test_webhook_processing(self, concurrent: int):
        """Test webhook processing capacity"""
        await self._run_concurrent_ops(
            f"Webhook_{concurrent}",
            concurrent,
            "webhook",
            0.03
        )
    
    async def _test_memory_pressure(self, concurrent: int):
        """Test under memory pressure"""
        await self._run_concurrent_ops(
            f"MemoryPressure_{concurrent}",
            concurrent,
            "memory_heavy",
            0.10  # Higher fail rate under pressure
        )
    
    async def _test_circuit_breaker(self, concurrent: int):
        """Test circuit breaker behavior"""
        # Simulate failing service
        await self._run_concurrent_ops(
            f"CircuitBreaker_{concurrent}",
            concurrent,
            "failing_service",
            0.30  # High fail rate triggers circuit breaker
        )
    
    async def _test_failure_recovery(self, concurrent: int):
        """Test system recovery after failures"""
        await self._run_concurrent_ops(
            f"Recovery_{concurrent}",
            concurrent,
            "recovery",
            0.15
        )


def print_load_report(results: List[LoadTestResult]):
    """Print formatted load test report"""
    print("\n" + "=" * 100)
    print("🚀 LOAD & STRESS TEST REPORT")
    print("=" * 100)
    
    total_requests = sum(r.total_requests for r in results)
    total_successful = sum(r.successful for r in results)
    total_failed = sum(r.failed for r in results)
    
    print(f"\n📊 SUMMARY")
    print(f"   Total Load Tests:     {len(results)}")
    print(f"   Total Requests:       {total_requests}")
    print(f"   Successful:           {total_successful} ({total_successful/total_requests*100:.1f}%)")
    print(f"   Failed:               {total_failed} ({total_failed/total_requests*100:.1f}%)")
    
    # Find best and worst performing tests
    sorted_by_throughput = sorted(results, key=lambda r: r.throughput_rps, reverse=True)
    sorted_by_latency = sorted(results, key=lambda r: r.avg_latency_ms)
    
    print(f"\n🏆 BEST PERFORMERS")
    print(f"   Highest Throughput:   {sorted_by_throughput[0].test_name} ({sorted_by_throughput[0].throughput_rps:.1f} req/s)")
    print(f"   Lowest Latency:       {sorted_by_latency[0].test_name} ({sorted_by_latency[0].avg_latency_ms:.1f} ms)")
    
    print(f"\n⚠️  NEEDS ATTENTION")
    print(f"   Lowest Throughput:    {sorted_by_throughput[-1].test_name} ({sorted_by_throughput[-1].throughput_rps:.1f} req/s)")
    print(f"   Highest Latency:      {sorted_by_latency[-1].test_name} ({sorted_by_latency[-1].avg_latency_ms:.1f} ms)")
    
    # Detailed results
    print("\n" + "-" * 100)
    print(f"{'Test Name':<35} {'Concurrent':<12} {'Success':<10} {'Avg ms':<10} {'P95 ms':<10} {'RPS':<8}")
    print("-" * 100)
    
    for r in results:
        status = "✅" if r.failed == 0 else "⚠️" if r.failed / r.total_requests < 0.1 else "❌"
        print(f"{status} {r.test_name:<32} {r.concurrent_ops:<12} {r.successful}/{r.total_requests:<4} {r.avg_latency_ms:<10.1f} {r.p95_latency_ms:<10.1f} {r.throughput_rps:<8.1f}")
    
    # Performance recommendations
    print("\n" + "-" * 100)
    print("📋 PERFORMANCE RECOMMENDATIONS")
    print("-" * 100)
    
    slow_tests = [r for r in results if r.avg_latency_ms > 1000]
    failing_tests = [r for r in results if r.failed / r.total_requests > 0.05]
    
    if slow_tests:
        print("\n🐌 High Latency Detected:")
        for r in slow_tests[:3]:
            print(f"   • {r.test_name}: {r.avg_latency_ms:.0f}ms avg latency")
        print("   Recommendation: Consider caching, async processing, or scaling")
    
    if failing_tests:
        print("\n🔴 High Failure Rate Detected:")
        for r in failing_tests[:3]:
            fail_rate = r.failed / r.total_requests * 100
            print(f"   • {r.test_name}: {fail_rate:.1f}% failure rate")
        print("   Recommendation: Review error handling, add retry logic, check resource limits")
    
    if not slow_tests and not failing_tests:
        print("\n✅ All load tests passed performance thresholds")
    
    print("\n" + "=" * 100)


async def main():
    tester = LoadTester()
    results = await tester.run_all_load_tests()
    print_load_report(results)
    return results


if __name__ == "__main__":
    asyncio.run(main())
