#!/usr/bin/env python3
"""
Performance Profiling Suite Phase 0
Identification goulots d'étranglement critiques pour optimisations
"""

import time
import sys
import tracemalloc
from decimal import Decimal, getcontext
from typing import Dict, List, Tuple, Any
import cProfile
import pstats
import io

# Configuration précision étendue
getcontext().prec = 50

try:
    from icgs_core import (
        DAG, DAGConfiguration, Transaction, TransactionMeasure
    )
    from icgs_core.regex_parser import RegexParser
    from icgs_core.thompson_nfa import ThompsonNFABuilder
    from icgs_diagnostics import run_quick_diagnostic
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


class PerformanceProfiler:
    """Profiler performance pour identification bottlenecks Phase 0"""

    def __init__(self):
        self.results = {}
        self.baseline_metrics = {}

    def profile_regex_parser(self, iterations: int = 1000) -> Dict[str, Any]:
        """Profile regex parser avec patterns complexes"""
        print(f"\n🔍 PROFILING REGEX PARSER ({iterations} iterations)")

        parser = RegexParser()
        test_patterns = [
            "[A-Z]",           # Simple character class
            "[A-Za-z0-9]+",    # Complex character class
            ".*N.*",           # Dot + literal + dot
            "[^abc]+",         # Negated character class
            "(abc|def)",       # Groups
            "[A-Z][a-z]*",     # Multiple classes
        ]

        results = {}

        for pattern in test_patterns:
            print(f"  Testing pattern: {pattern}")

            # Profiling avec cProfile
            pr = cProfile.Profile()

            start_time = time.perf_counter()
            tracemalloc.start()

            pr.enable()
            for _ in range(iterations):
                try:
                    tokens = parser.parse(pattern)
                    # Force evaluation
                    _ = [str(t) for t in tokens]
                except Exception as e:
                    print(f"    ⚠️ Error with {pattern}: {e}")
                    continue
            pr.disable()

            end_time = time.perf_counter()
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Analyse résultats
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s)
            ps.sort_stats('tottime').print_stats(10)

            results[pattern] = {
                'total_time': end_time - start_time,
                'avg_time_per_parse': (end_time - start_time) / iterations,
                'memory_current': current / 1024 / 1024,  # MB
                'memory_peak': peak / 1024 / 1024,        # MB
                'profile_stats': s.getvalue()
            }

            print(f"    Time: {results[pattern]['avg_time_per_parse']:.6f}s per parse")
            print(f"    Memory: {results[pattern]['memory_peak']:.2f}MB peak")

        self.results['regex_parser'] = results
        return results

    def profile_nfa_construction(self, iterations: int = 500) -> Dict[str, Any]:
        """Profile Thompson NFA construction"""
        print(f"\n🔍 PROFILING NFA CONSTRUCTION ({iterations} iterations)")

        builder = ThompsonNFABuilder()
        test_patterns = [
            "[A-Z]",           # Simple class → simple NFA
            "[A-Za-z0-9]+",    # Complex class + quantifier
            ".*N.*",           # Multiple fragments
            "(abc)+",          # Group + quantifier
            "[A-Z][a-z]*[0-9]?",  # Complex sequence
        ]

        results = {}

        for pattern in test_patterns:
            print(f"  Testing pattern: {pattern}")

            pr = cProfile.Profile()

            start_time = time.perf_counter()
            tracemalloc.start()

            pr.enable()
            for _ in range(iterations):
                try:
                    fragment = builder.build_pattern_fragment(pattern)
                    # Force evaluation
                    _ = len(fragment.all_state_ids)
                    _ = len(fragment.transitions)
                except Exception as e:
                    print(f"    ⚠️ Error with {pattern}: {e}")
                    continue
            pr.disable()

            end_time = time.perf_counter()
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Test final construction
            try:
                final_fragment = builder.build_pattern_fragment(pattern)
                complexity_metrics = {
                    'states_count': len(final_fragment.all_state_ids),
                    'transitions_count': len(final_fragment.transitions),
                    'pattern_length': len(pattern)
                }
            except Exception:
                complexity_metrics = {'states_count': 0, 'transitions_count': 0}

            results[pattern] = {
                'total_time': end_time - start_time,
                'avg_time_per_build': (end_time - start_time) / iterations,
                'memory_current': current / 1024 / 1024,
                'memory_peak': peak / 1024 / 1024,
                'complexity': complexity_metrics
            }

            print(f"    Time: {results[pattern]['avg_time_per_build']:.6f}s per build")
            print(f"    Memory: {results[pattern]['memory_peak']:.2f}MB peak")
            print(f"    NFA: {complexity_metrics['states_count']} states, {complexity_metrics['transitions_count']} transitions")

        self.results['nfa_construction'] = results
        return results

    def profile_dag_operations(self, iterations: int = 100) -> Dict[str, Any]:
        """Profile DAG operations critiques"""
        print(f"\n🔍 PROFILING DAG OPERATIONS ({iterations} iterations)")

        config = DAGConfiguration(
            max_path_enumeration=100,
            simplex_max_iterations=100,
            validation_mode="STRICT"
        )

        results = {}

        # Test 1: DAG initialization
        print("  Testing DAG initialization")
        start_time = time.perf_counter()
        tracemalloc.start()

        for _ in range(iterations):
            dag = DAG(config)
            # Force some operations
            _ = len(dag.accounts)
            _ = dag.transaction_counter

        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results['dag_initialization'] = {
            'total_time': end_time - start_time,
            'avg_time': (end_time - start_time) / iterations,
            'memory_peak': peak / 1024 / 1024
        }

        print(f"    Time: {results['dag_initialization']['avg_time']:.6f}s per init")
        print(f"    Memory: {results['dag_initialization']['memory_peak']:.2f}MB peak")

        # Test 2: Simple transaction creation (sans execution)
        print("  Testing transaction creation")
        dag = DAG(config)

        start_time = time.perf_counter()

        for i in range(iterations):
            transaction = Transaction(
                transaction_id=f"perf_test_{i}",
                source_account_id="source_account",
                target_account_id="target_account",
                amount=Decimal('100'),
                source_measures=[
                    TransactionMeasure(
                        measure_id="test_measure",
                        account_id="source_account",
                        primary_regex_pattern=".*",
                        primary_regex_weight=Decimal('1.0'),
                        acceptable_value=Decimal('100')
                    )
                ],
                target_measures=[]
            )
            # Force evaluation
            _ = transaction.transaction_id
            _ = len(transaction.source_measures)

        end_time = time.perf_counter()

        results['transaction_creation'] = {
            'total_time': end_time - start_time,
            'avg_time': (end_time - start_time) / iterations
        }

        print(f"    Time: {results['transaction_creation']['avg_time']:.6f}s per transaction")

        self.results['dag_operations'] = results
        return results

    def analyze_bottlenecks(self) -> Dict[str, Any]:
        """Analyse bottlenecks identifiés"""
        print(f"\n📊 ANALYSE BOTTLENECKS")

        bottlenecks = []
        recommendations = []

        # Analyse regex parser
        if 'regex_parser' in self.results:
            regex_results = self.results['regex_parser']
            slowest_pattern = max(regex_results.keys(),
                                key=lambda p: regex_results[p]['avg_time_per_parse'])

            bottlenecks.append({
                'component': 'regex_parser',
                'slowest_operation': f"Pattern: {slowest_pattern}",
                'time': regex_results[slowest_pattern]['avg_time_per_parse'],
                'memory': regex_results[slowest_pattern]['memory_peak']
            })

            recommendations.append(
                f"REGEX PARSER: Optimize {slowest_pattern} parsing "
                f"({regex_results[slowest_pattern]['avg_time_per_parse']:.6f}s)"
            )

        # Analyse NFA construction
        if 'nfa_construction' in self.results:
            nfa_results = self.results['nfa_construction']
            slowest_nfa = max(nfa_results.keys(),
                             key=lambda p: nfa_results[p]['avg_time_per_build'])

            bottlenecks.append({
                'component': 'nfa_construction',
                'slowest_operation': f"Pattern: {slowest_nfa}",
                'time': nfa_results[slowest_nfa]['avg_time_per_build'],
                'memory': nfa_results[slowest_nfa]['memory_peak'],
                'complexity': nfa_results[slowest_nfa]['complexity']
            })

            recommendations.append(
                f"NFA CONSTRUCTION: Optimize {slowest_nfa} building "
                f"({nfa_results[slowest_nfa]['avg_time_per_build']:.6f}s)"
            )

        analysis = {
            'bottlenecks': bottlenecks,
            'recommendations': recommendations,
            'optimization_targets': []
        }

        # Priorités optimisation
        for bottleneck in bottlenecks:
            if bottleneck['time'] > 0.001:  # > 1ms
                analysis['optimization_targets'].append({
                    'priority': 'HIGH',
                    'component': bottleneck['component'],
                    'target_improvement': '10x faster',
                    'current_time': bottleneck['time']
                })
            elif bottleneck['time'] > 0.0001:  # > 0.1ms
                analysis['optimization_targets'].append({
                    'priority': 'MEDIUM',
                    'component': bottleneck['component'],
                    'target_improvement': '5x faster',
                    'current_time': bottleneck['time']
                })

        print("\n🎯 OPTIMIZATION TARGETS:")
        for target in analysis['optimization_targets']:
            print(f"  {target['priority']}: {target['component']} "
                  f"({target['current_time']:.6f}s → {target['target_improvement']})")

        self.results['analysis'] = analysis
        return analysis

    def generate_baseline_report(self) -> str:
        """Génère rapport baseline performance"""
        report = []
        report.append("="*60)
        report.append("PERFORMANCE BASELINE REPORT - PHASE 0")
        report.append("="*60)

        for component, results in self.results.items():
            if component == 'analysis':
                continue

            report.append(f"\n🔍 {component.upper()}")
            report.append("-" * 40)

            if isinstance(results, dict) and 'avg_time_per_parse' in list(results.values())[0]:
                # Regex parser results
                for pattern, metrics in results.items():
                    report.append(f"Pattern: {pattern}")
                    report.append(f"  Time: {metrics['avg_time_per_parse']:.6f}s")
                    report.append(f"  Memory: {metrics['memory_peak']:.2f}MB")

            elif isinstance(results, dict) and 'avg_time_per_build' in list(results.values())[0]:
                # NFA construction results
                for pattern, metrics in results.items():
                    report.append(f"Pattern: {pattern}")
                    report.append(f"  Time: {metrics['avg_time_per_build']:.6f}s")
                    report.append(f"  Memory: {metrics['memory_peak']:.2f}MB")
                    if 'complexity' in metrics:
                        c = metrics['complexity']
                        report.append(f"  NFA: {c['states_count']} states, {c['transitions_count']} transitions")

        if 'analysis' in self.results:
            report.append(f"\n🎯 OPTIMIZATION RECOMMENDATIONS")
            report.append("-" * 40)
            for rec in self.results['analysis']['recommendations']:
                report.append(f"• {rec}")

        return "\n".join(report)


def run_performance_profiling():
    """Execute profiling complet Phase 0"""
    print("🚄 PHASE 0 PERFORMANCE PROFILING - START")
    print("="*60)

    profiler = PerformanceProfiler()

    # Profiling séquentiel
    profiler.profile_regex_parser(iterations=1000)
    profiler.profile_nfa_construction(iterations=500)
    profiler.profile_dag_operations(iterations=100)

    # Analyse
    analysis = profiler.analyze_bottlenecks()

    # Rapport
    report = profiler.generate_baseline_report()
    print("\n" + report)

    # Save baseline
    with open("PERFORMANCE_BASELINE_PHASE_0.txt", "w") as f:
        f.write(report)

    print(f"\n✅ PROFILING COMPLETE - Baseline saved to PERFORMANCE_BASELINE_PHASE_0.txt")
    return profiler.results


if __name__ == "__main__":
    results = run_performance_profiling()