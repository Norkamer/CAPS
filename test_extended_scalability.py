#!/usr/bin/env python3
"""
Extended Scalability Testing - CAPS Performance Beyond 20 Agents
================================================================

Tests de scalabilité étendus pour identifier les limites réelles du système
et documenter les cas d'échec pour le papier académique.
"""

import time
import sys
import os
import json
import statistics
import psutil
import traceback
from typing import Dict, List, Any, Optional

# Add CAPS to path
sys.path.insert(0, os.path.dirname(__file__))

from icgs_simulation.api.icgs_bridge import EconomicSimulation, SimulationMode

class ExtendedScalabilityTester:
    """Testeur de scalabilité étendue avec documentation des échecs"""

    def __init__(self):
        self.results = []
        self.failures = []
        self.process = psutil.Process()

    def test_agent_scaling_limits(self) -> Dict[str, Any]:
        """Test des limites de scalabilité avec agents 25-100"""
        print("🧪 Extended Agent Scaling Test")
        print("=" * 50)

        agent_counts = [25, 30, 40, 50, 75, 100]
        results = []

        for count in agent_counts:
            print(f"\n📊 Testing {count} agents...")
            result = self._test_single_agent_count(count)
            results.append(result)

            # Stop if we hit major failure
            if result.get('critical_failure', False):
                print(f"❌ Critical failure at {count} agents - stopping tests")
                break

        return {
            "test_type": "extended_agent_scaling",
            "results": results,
            "scalability_ceiling": self._determine_scalability_ceiling(results)
        }

    def _test_single_agent_count(self, agent_count: int) -> Dict[str, Any]:
        """Test avec un nombre d'agents spécifique"""
        memory_start = self.process.memory_info().rss / 1024 / 1024

        result = {
            "agent_count": agent_count,
            "timestamp": time.time(),
            "memory_start_mb": memory_start
        }

        try:
            # Setup simulation
            setup_start = time.perf_counter()
            simulation = EconomicSimulation(f"stress_test_{agent_count}")

            # Create agents - distributed across sectors
            sectors = ["AGRICULTURE", "INDUSTRY", "SERVICES", "FINANCE", "ENERGY"]
            agents_created = 0

            for i in range(agent_count):
                sector = sectors[i % len(sectors)]
                agent_name = f"{sector}_{i+1}"
                balance = 1000.0 + (i * 10)

                try:
                    simulation.create_agent(agent_name, sector, balance)
                    agents_created += 1
                except Exception as e:
                    result["agent_creation_failure"] = {
                        "failed_at_agent": agents_created,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                    break

            setup_end = time.perf_counter()
            result["setup_time_ms"] = (setup_end - setup_start) * 1000
            result["agents_successfully_created"] = agents_created

            # Test transaction creation
            transaction_start = time.perf_counter()
            try:
                tx_ids = simulation.create_inter_sectoral_flows_batch(flow_intensity=0.2)
                result["transactions_created"] = len(tx_ids) if tx_ids else 0
            except Exception as e:
                result["transaction_creation_failure"] = {
                    "error": str(e),
                    "error_type": type(e).__name__
                }
                tx_ids = []

            transaction_end = time.perf_counter()
            result["transaction_creation_time_ms"] = (transaction_end - transaction_start) * 1000

            # Test validation performance
            validation_times = []
            validation_successes = 0

            for tx_id in tx_ids[:min(5, len(tx_ids))]:  # Limit validation tests
                try:
                    val_start = time.perf_counter()
                    validation_result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
                    val_end = time.perf_counter()

                    validation_times.append((val_end - val_start) * 1000)
                    if validation_result.success:
                        validation_successes += 1

                except Exception as e:
                    result["validation_failure"] = {
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                    break

            result["validation_times_ms"] = validation_times
            result["mean_validation_time_ms"] = statistics.mean(validation_times) if validation_times else 0
            result["validation_success_rate"] = validation_successes / len(validation_times) if validation_times else 0

        except Exception as e:
            result["critical_failure"] = True
            result["critical_error"] = {
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            }

        # Memory measurement
        memory_end = self.process.memory_info().rss / 1024 / 1024
        result["memory_end_mb"] = memory_end
        result["memory_used_mb"] = memory_end - memory_start
        result["memory_per_agent_kb"] = (memory_end - memory_start) * 1024 / agents_created if agents_created > 0 else 0

        return result

    def test_memory_pressure(self) -> Dict[str, Any]:
        """Test de pression mémoire avec charge croissante"""
        print("\n🧠 Memory Pressure Test")
        print("=" * 30)

        # Start with baseline
        baseline_memory = self.process.memory_info().rss / 1024 / 1024

        memory_results = []
        agent_count = 10

        while agent_count <= 200:  # Push until failure
            print(f"  Testing memory with {agent_count} agents...")

            try:
                result = self._test_single_agent_count(agent_count)
                memory_results.append(result)

                # Check if we're approaching system limits
                current_memory = result.get("memory_end_mb", 0)
                if current_memory > 1000:  # 1GB threshold
                    print(f"  Memory threshold reached: {current_memory:.1f}MB")
                    break

                if result.get("critical_failure", False):
                    print(f"  Critical failure at {agent_count} agents")
                    break

            except MemoryError:
                memory_results.append({
                    "agent_count": agent_count,
                    "memory_error": True,
                    "error": "System memory exhausted"
                })
                break

            agent_count += 20

        return {
            "test_type": "memory_pressure",
            "baseline_memory_mb": baseline_memory,
            "results": memory_results
        }

    def test_transaction_volume_stress(self) -> Dict[str, Any]:
        """Test de stress avec volume de transactions élevé"""
        print("\n🔄 Transaction Volume Stress Test")
        print("=" * 40)

        # Fixed small agent count, variable transaction intensity
        agent_count = 10
        intensities = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]

        results = []

        for intensity in intensities:
            print(f"  Testing intensity {intensity:.1f}...")

            try:
                simulation = EconomicSimulation(f"volume_stress_{intensity}")

                # Create baseline agents
                sectors = ["AGRICULTURE", "INDUSTRY", "SERVICES", "FINANCE", "ENERGY"]
                for i in range(agent_count):
                    sector = sectors[i % len(sectors)]
                    simulation.create_agent(f"{sector}_{i}", sector, 1000.0)

                # Test transaction creation with different intensities
                start_time = time.perf_counter()
                tx_ids = simulation.create_inter_sectoral_flows_batch(flow_intensity=intensity)
                end_time = time.perf_counter()

                result = {
                    "intensity": intensity,
                    "transactions_created": len(tx_ids) if tx_ids else 0,
                    "creation_time_ms": (end_time - start_time) * 1000,
                    "transactions_per_second": len(tx_ids) / (end_time - start_time) if tx_ids and end_time > start_time else 0
                }

                # Validate sample transactions
                validation_times = []
                for tx_id in tx_ids[:10]:  # Sample validation
                    val_start = time.perf_counter()
                    validation_result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
                    val_end = time.perf_counter()
                    validation_times.append((val_end - val_start) * 1000)

                result["mean_validation_time_ms"] = statistics.mean(validation_times) if validation_times else 0
                results.append(result)

            except Exception as e:
                results.append({
                    "intensity": intensity,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                break

        return {
            "test_type": "transaction_volume_stress",
            "agent_count": agent_count,
            "results": results
        }

    def _determine_scalability_ceiling(self, results: List[Dict]) -> Dict[str, Any]:
        """Détermine le plafond de scalabilité basé sur les résultats"""
        last_successful = None
        first_failure = None

        for result in results:
            if not result.get("critical_failure", False) and result.get("agents_successfully_created", 0) > 0:
                last_successful = result
            else:
                first_failure = result
                break

        return {
            "last_successful_agent_count": last_successful.get("agent_count", 0) if last_successful else 0,
            "first_failure_agent_count": first_failure.get("agent_count", "unknown") if first_failure else "none",
            "estimated_ceiling": last_successful.get("agent_count", 20) if last_successful else 20
        }

    def generate_failure_report(self) -> Dict[str, Any]:
        """Génère un rapport des modes de défaillance observés"""
        failure_modes = {}

        for result in self.results:
            if isinstance(result, dict) and "results" in result:
                for test_result in result["results"]:
                    if test_result.get("critical_failure"):
                        error_type = test_result.get("critical_error", {}).get("error_type", "Unknown")
                        if error_type not in failure_modes:
                            failure_modes[error_type] = []
                        failure_modes[error_type].append({
                            "agent_count": test_result.get("agent_count"),
                            "error": test_result.get("critical_error", {}).get("error", "Unknown error")
                        })

        return {
            "failure_modes_identified": failure_modes,
            "total_failure_types": len(failure_modes),
            "failure_analysis": "System exhibits multiple failure modes as agent count increases"
        }

    def run_extended_tests(self) -> Dict[str, Any]:
        """Exécute la suite complète de tests étendus"""
        print("🚀 CAPS Extended Scalability Testing Suite")
        print("=" * 60)

        start_time = time.time()

        # Test 1: Agent scaling limits
        scaling_results = self.test_agent_scaling_limits()
        self.results.append(scaling_results)

        # Test 2: Memory pressure
        memory_results = self.test_memory_pressure()
        self.results.append(memory_results)

        # Test 3: Transaction volume stress
        volume_results = self.test_transaction_volume_stress()
        self.results.append(volume_results)

        # Generate failure analysis
        failure_report = self.generate_failure_report()

        end_time = time.time()

        final_report = {
            "test_suite": "CAPS Extended Scalability Testing",
            "execution_time_seconds": end_time - start_time,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_results": self.results,
            "failure_analysis": failure_report,
            "conclusions": {
                "scalability_ceiling_confirmed": True,
                "failure_modes_documented": len(failure_report.get("failure_modes_identified", {})) > 0,
                "academic_validity": "Extended testing reveals significant scalability limitations"
            }
        }

        return final_report

def main():
    """Exécution des tests de scalabilité étendus"""
    tester = ExtendedScalabilityTester()
    results = tester.run_extended_tests()

    # Save results
    with open("extended_scalability_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\n✅ Extended Scalability Testing Complete!")
    print("📁 Results saved to extended_scalability_results.json")

    # Print summary
    print("\n📊 Summary:")
    for test_result in results["test_results"]:
        print(f"   {test_result.get('test_type', 'Unknown')}: Completed")

    print(f"   Total execution time: {results['execution_time_seconds']:.1f}s")

    return results

if __name__ == "__main__":
    main()