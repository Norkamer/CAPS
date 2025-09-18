#!/usr/bin/env python3
"""
Benchmark TransactionManager - Mesure de Performance et Overhead

Ce script mesure rigoureusement les performances du TransactionManager
vs le système AccountTaxonomy original pour valider que l'overhead
est inférieur à 5% comme spécifié dans les critères d'acceptation.

Métriques mesurées:
1. Temps d'initialisation
2. Temps d'ajout comptes (opération principale)
3. Temps de récupération mappings
4. Temps de conversion paths
5. Mémoire utilisée
"""

import time
import sys
import os
import gc
import statistics
from typing import List, Dict, Tuple

# Import des modules à benchmarker
sys.path.insert(0, os.path.dirname(__file__))

from icgs_core.transaction_manager import TransactionManager
from icgs_core.account_taxonomy import AccountTaxonomy
from icgs_core.dag_structures import Node


class PerformanceBenchmark:
    """Classe pour mesurer performances de manière rigoureuse"""

    def __init__(self, iterations: int = 100):
        self.iterations = iterations
        self.results = {}

    def measure_time(self, name: str, func, *args, **kwargs) -> float:
        """Mesure le temps d'exécution avec multiple itérations"""
        times = []

        # Warm-up
        for _ in range(5):
            func(*args, **kwargs)

        # Mesures réelles
        for _ in range(self.iterations):
            gc.collect()  # Force garbage collection
            start_time = time.perf_counter()
            func(*args, **kwargs)
            end_time = time.perf_counter()
            times.append(end_time - start_time)

        avg_time = statistics.mean(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0

        self.results[name] = {
            'avg_time': avg_time,
            'std_dev': std_dev,
            'min_time': min(times),
            'max_time': max(times),
            'measurements': len(times)
        }

        return avg_time

    def print_results(self):
        """Affiche les résultats de benchmark"""
        print("\n" + "="*80)
        print("BENCHMARK RESULTS - TransactionManager Performance Analysis")
        print("="*80)

        for name, metrics in self.results.items():
            print(f"\n{name}:")
            print(f"  Average: {metrics['avg_time']:.6f}s")
            print(f"  Std Dev: {metrics['std_dev']:.6f}s")
            print(f"  Min:     {metrics['min_time']:.6f}s")
            print(f"  Max:     {metrics['max_time']:.6f}s")
            print(f"  Samples: {metrics['measurements']}")

    def calculate_overhead(self, original_key: str, tm_key: str) -> float:
        """Calcule l'overhead en pourcentage"""
        original_time = self.results[original_key]['avg_time']
        tm_time = self.results[tm_key]['avg_time']

        if original_time == 0:
            return 0.0

        overhead = ((tm_time - original_time) / original_time) * 100
        return overhead


def benchmark_initialization():
    """Benchmark initialisation des systèmes"""
    print("🔄 Benchmarking initialization...")

    benchmark = PerformanceBenchmark(iterations=1000)

    # Benchmark AccountTaxonomy seul
    def create_original():
        return AccountTaxonomy()

    # Benchmark TransactionManager + AccountTaxonomy
    def create_with_tm():
        taxonomy = AccountTaxonomy()
        return TransactionManager(taxonomy)

    benchmark.measure_time("Original_Initialization", create_original)
    benchmark.measure_time("TM_Initialization", create_with_tm)

    overhead = benchmark.calculate_overhead("Original_Initialization", "TM_Initialization")

    print(f"✅ Initialization overhead: {overhead:.2f}%")

    return benchmark, overhead


def benchmark_account_addition():
    """Benchmark ajout de comptes - opération principale"""
    print("🔄 Benchmarking account addition...")

    benchmark = PerformanceBenchmark(iterations=100)

    # Setup systèmes
    original_taxonomy = AccountTaxonomy()
    tm_taxonomy = AccountTaxonomy()
    tm = TransactionManager(tm_taxonomy)

    # Test avec lots de 5 comptes
    test_accounts = {f"account_{i}": chr(65 + i) for i in range(5)}

    # Benchmark méthode originale
    def original_add_accounts():
        nonlocal original_taxonomy
        original_taxonomy = AccountTaxonomy()  # Reset pour chaque mesure
        tx_num = 0
        original_taxonomy.update_taxonomy(test_accounts, tx_num)

    # Benchmark TransactionManager
    def tm_add_accounts():
        nonlocal tm_taxonomy, tm
        tm_taxonomy = AccountTaxonomy()
        tm = TransactionManager(tm_taxonomy)
        tm.add_accounts_auto(test_accounts)

    benchmark.measure_time("Original_Add_Accounts", original_add_accounts)
    benchmark.measure_time("TM_Add_Accounts", tm_add_accounts)

    overhead = benchmark.calculate_overhead("Original_Add_Accounts", "TM_Add_Accounts")

    print(f"✅ Account addition overhead: {overhead:.2f}%")

    return benchmark, overhead


def benchmark_mapping_retrieval():
    """Benchmark récupération mappings"""
    print("🔄 Benchmarking mapping retrieval...")

    benchmark = PerformanceBenchmark(iterations=500)

    # Setup systèmes avec données
    original_taxonomy = AccountTaxonomy()
    test_accounts = {f"account_{i}": chr(65 + i) for i in range(10)}
    original_taxonomy.update_taxonomy(test_accounts, 0)

    tm_taxonomy = AccountTaxonomy()
    tm = TransactionManager(tm_taxonomy)
    tm.add_accounts_auto(test_accounts)

    test_account = "account_5"

    # Benchmark méthode originale
    def original_get_mapping():
        return original_taxonomy.get_character_mapping(test_account, 0)

    # Benchmark TransactionManager API simplifiée
    def tm_get_mapping():
        return tm.get_current_mapping(test_account)

    # Benchmark TransactionManager API avancée
    def tm_get_mapping_advanced():
        return tm.get_character_mapping_at(test_account, 0)

    benchmark.measure_time("Original_Get_Mapping", original_get_mapping)
    benchmark.measure_time("TM_Get_Mapping_Simple", tm_get_mapping)
    benchmark.measure_time("TM_Get_Mapping_Advanced", tm_get_mapping_advanced)

    overhead_simple = benchmark.calculate_overhead("Original_Get_Mapping", "TM_Get_Mapping_Simple")
    overhead_advanced = benchmark.calculate_overhead("Original_Get_Mapping", "TM_Get_Mapping_Advanced")

    print(f"✅ Mapping retrieval overhead (simple): {overhead_simple:.2f}%")
    print(f"✅ Mapping retrieval overhead (advanced): {overhead_advanced:.2f}%")

    return benchmark, max(overhead_simple, overhead_advanced)


def benchmark_path_conversion():
    """Benchmark conversion de paths"""
    print("🔄 Benchmarking path conversion...")

    benchmark = PerformanceBenchmark(iterations=200)

    # Setup systèmes avec données
    original_taxonomy = AccountTaxonomy()
    test_accounts = {"node1": "A", "node2": "B", "node3": "C"}
    original_taxonomy.update_taxonomy(test_accounts, 0)

    tm_taxonomy = AccountTaxonomy()
    tm = TransactionManager(tm_taxonomy)
    tm.add_accounts_auto(test_accounts)

    test_path = [Node("node1"), Node("node2"), Node("node3")]

    # Benchmark méthode originale
    def original_convert_path():
        return original_taxonomy.convert_path_to_word(test_path, 0)

    # Benchmark TransactionManager API simplifiée
    def tm_convert_path():
        return tm.convert_path_current(test_path)

    # Benchmark TransactionManager API avancée
    def tm_convert_path_advanced():
        return tm.convert_path_at(test_path, 0)

    benchmark.measure_time("Original_Convert_Path", original_convert_path)
    benchmark.measure_time("TM_Convert_Path_Simple", tm_convert_path)
    benchmark.measure_time("TM_Convert_Path_Advanced", tm_convert_path_advanced)

    overhead_simple = benchmark.calculate_overhead("Original_Convert_Path", "TM_Convert_Path_Simple")
    overhead_advanced = benchmark.calculate_overhead("Original_Convert_Path", "TM_Convert_Path_Advanced")

    print(f"✅ Path conversion overhead (simple): {overhead_simple:.2f}%")
    print(f"✅ Path conversion overhead (advanced): {overhead_advanced:.2f}%")

    return benchmark, max(overhead_simple, overhead_advanced)


def benchmark_memory_usage():
    """Benchmark utilisation mémoire"""
    print("🔄 Benchmarking memory usage...")

    import tracemalloc

    # Mesure AccountTaxonomy seul
    tracemalloc.start()
    taxonomies = []
    for i in range(100):
        taxonomy = AccountTaxonomy()
        accounts = {f"acc_{j}": chr(65 + j) for j in range(5)}
        taxonomy.update_taxonomy(accounts, i)
        taxonomies.append(taxonomy)

    current, peak_original = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Mesure avec TransactionManager
    tracemalloc.start()
    tms = []
    for i in range(100):
        taxonomy = AccountTaxonomy()
        tm = TransactionManager(taxonomy)
        accounts = {f"acc_{j}": chr(65 + j) for j in range(5)}
        tm.add_accounts_auto(accounts)
        tms.append(tm)

    current_tm, peak_tm = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    memory_overhead = ((peak_tm - peak_original) / peak_original) * 100

    print(f"✅ Memory usage:")
    print(f"  - Original peak: {peak_original / 1024 / 1024:.2f} MB")
    print(f"  - TM peak: {peak_tm / 1024 / 1024:.2f} MB")
    print(f"  - Memory overhead: {memory_overhead:.2f}%")

    return memory_overhead


def main():
    """Exécution complète des benchmarks"""
    print("\n🚀 TRANSACTION MANAGER PERFORMANCE BENCHMARK")
    print("=" * 60)

    # Collecte tous les overheads
    overheads = {}

    # Benchmarks individuels
    init_benchmark, init_overhead = benchmark_initialization()
    overheads['initialization'] = init_overhead

    add_benchmark, add_overhead = benchmark_account_addition()
    overheads['account_addition'] = add_overhead

    get_benchmark, get_overhead = benchmark_mapping_retrieval()
    overheads['mapping_retrieval'] = get_overhead

    path_benchmark, path_overhead = benchmark_path_conversion()
    overheads['path_conversion'] = path_overhead

    memory_overhead = benchmark_memory_usage()
    overheads['memory'] = memory_overhead

    # Résultats finaux
    print("\n" + "="*80)
    print("📊 FINAL PERFORMANCE ANALYSIS")
    print("="*80)

    print(f"\nOverhead Summary:")
    for operation, overhead in overheads.items():
        status = "✅ PASS" if overhead <= 5.0 else "❌ FAIL"
        print(f"  {operation:.<25} {overhead:>6.2f}% {status}")

    max_overhead = max(overheads.values())
    overall_status = "✅ PASS" if max_overhead <= 5.0 else "❌ FAIL"

    print(f"\nOverall Performance:")
    print(f"  Maximum overhead: {max_overhead:.2f}%")
    print(f"  Target threshold: ≤ 5.00%")
    print(f"  Status: {overall_status}")

    if max_overhead <= 5.0:
        print(f"\n🎉 SUCCESS: TransactionManager meets performance requirements!")
        print(f"   All operations show overhead ≤ 5%, maintaining excellent performance.")
    else:
        print(f"\n⚠️  WARNING: TransactionManager exceeds performance threshold!")
        print(f"   Maximum overhead of {max_overhead:.2f}% > 5% threshold.")

    return max_overhead <= 5.0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)