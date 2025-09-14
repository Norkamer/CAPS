#!/usr/bin/env python3
"""
Performance Validation Suite Phase 0
Tests performance internes CAPS + validation non-régression
"""

import time
import sys
from decimal import Decimal, getcontext
from typing import Dict, List, Any
import tracemalloc

# Configuration précision
getcontext().prec = 50

try:
    from icgs_core import DAG, DAGConfiguration, Transaction, TransactionMeasure
    from icgs_core.regex_parser import RegexParser
    from icgs_core.thompson_nfa import ThompsonNFABuilder
    from icgs_diagnostics import run_quick_diagnostic
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


class PerformanceValidator:
    """Validation performance + non-régression Phase 0"""

    def __init__(self):
        self.baseline_metrics = {}
        self.current_metrics = {}
        self.validation_results = {}

    def establish_baseline(self) -> Dict[str, Any]:
        """Établit baseline performance avant optimizations"""
        print("📊 ESTABLISHING PERFORMANCE BASELINE")
        print("-" * 50)

        baseline = {}

        # Test 1: Regex parsing performance
        parser = RegexParser()
        test_patterns = ["[A-Z]", "[A-Za-z0-9]+", ".*N.*", "[^abc]+"]

        regex_times = {}
        for pattern in test_patterns:
            times = []
            for _ in range(100):
                start = time.perf_counter()
                try:
                    tokens = parser.parse(pattern)
                    times.append(time.perf_counter() - start)
                except Exception:
                    times.append(float('inf'))
                    break

            if times and times[0] != float('inf'):
                regex_times[pattern] = sum(times) / len(times)
                print(f"  Regex {pattern}: {regex_times[pattern]*1000:.3f}ms avg")

        baseline['regex_parsing'] = regex_times

        # Test 2: NFA construction performance
        builder = ThompsonNFABuilder()
        nfa_times = {}
        nfa_complexity = {}

        for pattern in test_patterns:
            times = []
            for _ in range(50):
                start = time.perf_counter()
                try:
                    fragment = builder.build_pattern_fragment(pattern)
                    times.append(time.perf_counter() - start)

                    # Measure complexity
                    nfa_complexity[pattern] = {
                        'states': len(fragment.all_state_ids),
                        'transitions': len(fragment.transitions)
                    }
                except Exception:
                    times.append(float('inf'))
                    break

            if times and times[0] != float('inf'):
                nfa_times[pattern] = sum(times) / len(times)
                complexity = nfa_complexity.get(pattern, {})
                print(f"  NFA {pattern}: {nfa_times[pattern]*1000:.3f}ms avg "
                      f"({complexity.get('states', 0)} states, {complexity.get('transitions', 0)} transitions)")

        baseline['nfa_construction'] = nfa_times
        baseline['nfa_complexity'] = nfa_complexity

        # Test 3: DAG basic operations
        dag_times = {}

        # DAG initialization
        times = []
        for _ in range(10):
            start = time.perf_counter()
            config = DAGConfiguration(max_path_enumeration=50, validation_mode="RELAXED")
            dag = DAG(config)
            times.append(time.perf_counter() - start)

        dag_times['initialization'] = sum(times) / len(times)
        print(f"  DAG init: {dag_times['initialization']*1000:.3f}ms avg")

        baseline['dag_operations'] = dag_times

        self.baseline_metrics = baseline
        return baseline

    def run_functional_tests(self) -> Dict[str, Any]:
        """Tests fonctionnels pour non-régression"""
        print("\n🧪 FUNCTIONAL TESTS (Non-Regression)")
        print("-" * 50)

        results = {}

        # Test 1: Regex parsing correctness
        parser = RegexParser()
        regex_tests = {
            "[A-Z]": {
                'expected_token_type': 'CHARACTER_CLASS',
                'expected_char_set_size': 26,
                'expected_negated': False
            },
            "[^abc]": {
                'expected_token_type': 'CHARACTER_CLASS',
                'expected_char_set_size': 3,
                'expected_negated': True
            },
            ".*N.*": {
                'expected_tokens': 3  # dot, literal N, dot
            }
        }

        regex_results = {}
        for pattern, expected in regex_tests.items():
            try:
                tokens = parser.parse(pattern)

                if pattern in ["[A-Z]", "[^abc]"]:
                    token = tokens[0]
                    checks = {
                        'correct_type': token.token_type.value == expected['expected_token_type'],
                        'correct_char_set_size': len(token.char_set or []) == expected['expected_char_set_size'],
                        'correct_negated': getattr(token, 'negated', False) == expected['expected_negated']
                    }
                elif pattern == ".*N.*":
                    checks = {
                        'correct_token_count': len(tokens) == expected['expected_tokens']
                    }

                regex_results[pattern] = {
                    'success': all(checks.values()),
                    'checks': checks
                }

                status = "✅" if regex_results[pattern]['success'] else "❌"
                print(f"  {status} Regex {pattern}: {checks}")

            except Exception as e:
                regex_results[pattern] = {'success': False, 'error': str(e)}
                print(f"  ❌ Regex {pattern}: ERROR - {e}")

        results['regex_parsing'] = regex_results

        # Test 2: NFA construction correctness
        builder = ThompsonNFABuilder()
        nfa_results = {}

        for pattern in ["[A-Z]", ".*N.*", "(abc)+"]:
            try:
                fragment = builder.build_pattern_fragment(pattern)

                checks = {
                    'has_states': len(fragment.all_state_ids) > 0,
                    'has_transitions': len(fragment.transitions) > 0,
                    'has_start_state': fragment.start_state_id is not None,
                    'has_final_states': len(fragment.final_state_ids) > 0
                }

                nfa_results[pattern] = {
                    'success': all(checks.values()),
                    'checks': checks,
                    'states_count': len(fragment.all_state_ids),
                    'transitions_count': len(fragment.transitions)
                }

                status = "✅" if nfa_results[pattern]['success'] else "❌"
                print(f"  {status} NFA {pattern}: {nfa_results[pattern]['states_count']} states, "
                      f"{nfa_results[pattern]['transitions_count']} transitions")

            except Exception as e:
                nfa_results[pattern] = {'success': False, 'error': str(e)}
                print(f"  ❌ NFA {pattern}: ERROR - {e}")

        results['nfa_construction'] = nfa_results

        # Test 3: DAG basic functionality
        try:
            config = DAGConfiguration(validation_mode="RELAXED")
            dag = DAG(config)

            dag_checks = {
                'initialization': dag is not None,
                'has_accounts': hasattr(dag, 'accounts'),
                'has_transaction_counter': hasattr(dag, 'transaction_counter'),
                'has_taxonomy': hasattr(dag, 'account_taxonomy')
            }

            # Test diagnostics integration
            diagnostic_result = run_quick_diagnostic(dag)
            dag_checks['diagnostics_working'] = 'health_check' in diagnostic_result

            results['dag_functionality'] = {
                'success': all(dag_checks.values()),
                'checks': dag_checks
            }

            status = "✅" if results['dag_functionality']['success'] else "❌"
            print(f"  {status} DAG functionality: {dag_checks}")

        except Exception as e:
            results['dag_functionality'] = {'success': False, 'error': str(e)}
            print(f"  ❌ DAG functionality: ERROR - {e}")

        return results

    def measure_memory_usage(self) -> Dict[str, Any]:
        """Mesure utilisation mémoire"""
        print("\n🧠 MEMORY USAGE ANALYSIS")
        print("-" * 50)

        memory_results = {}

        # Test 1: Regex parser memory
        parser = RegexParser()

        tracemalloc.start()
        for _ in range(100):
            for pattern in ["[A-Z]", "[A-Za-z0-9]+", ".*N.*"]:
                try:
                    tokens = parser.parse(pattern)
                except:
                    pass

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        memory_results['regex_parser'] = {
            'current_mb': current / 1024 / 1024,
            'peak_mb': peak / 1024 / 1024
        }

        print(f"  Regex Parser: {memory_results['regex_parser']['peak_mb']:.2f}MB peak")

        # Test 2: NFA construction memory
        builder = ThompsonNFABuilder()

        tracemalloc.start()
        for _ in range(50):
            for pattern in ["[A-Z]", "[A-Za-z0-9]+", ".*N.*"]:
                try:
                    fragment = builder.build_pattern_fragment(pattern)
                except:
                    pass

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        memory_results['nfa_construction'] = {
            'current_mb': current / 1024 / 1024,
            'peak_mb': peak / 1024 / 1024
        }

        print(f"  NFA Construction: {memory_results['nfa_construction']['peak_mb']:.2f}MB peak")

        return memory_results

    def generate_validation_report(self, baseline: Dict, functional: Dict, memory: Dict) -> str:
        """Génère rapport validation complet"""
        report = []
        report.append("="*70)
        report.append("PERFORMANCE VALIDATION REPORT - PHASE 0")
        report.append("="*70)

        # Performance Baseline
        report.append("\n📊 PERFORMANCE BASELINE")
        report.append("-" * 30)

        if 'regex_parsing' in baseline:
            for pattern, time_ms in baseline['regex_parsing'].items():
                report.append(f"Regex {pattern}: {time_ms*1000:.3f}ms")

        if 'nfa_construction' in baseline:
            for pattern, time_ms in baseline['nfa_construction'].items():
                complexity = baseline.get('nfa_complexity', {}).get(pattern, {})
                report.append(f"NFA {pattern}: {time_ms*1000:.3f}ms "
                           f"({complexity.get('states', 0)}s, {complexity.get('transitions', 0)}t)")

        # Functional Tests
        report.append("\n🧪 FUNCTIONAL VALIDATION")
        report.append("-" * 30)

        total_tests = 0
        passed_tests = 0

        for component, results in functional.items():
            if isinstance(results, dict):
                for test, result in results.items():
                    total_tests += 1
                    if isinstance(result, dict) and result.get('success'):
                        passed_tests += 1
                        report.append(f"✅ {component}.{test}")
                    else:
                        report.append(f"❌ {component}.{test}")

        report.append(f"\nTEST SUMMARY: {passed_tests}/{total_tests} passed "
                     f"({passed_tests/total_tests*100:.1f}%)")

        # Memory Usage
        report.append("\n🧠 MEMORY USAGE")
        report.append("-" * 30)

        for component, usage in memory.items():
            report.append(f"{component}: {usage['peak_mb']:.2f}MB peak")

        # Overall Status
        overall_success = passed_tests / total_tests >= 0.9 if total_tests > 0 else False
        status = "✅ VALIDATION PASSED" if overall_success else "❌ VALIDATION ISSUES"
        report.append(f"\n🎯 OVERALL STATUS: {status}")

        return "\n".join(report)


def run_performance_validation():
    """Execute validation suite complète"""
    print("🚀 PHASE 0 PERFORMANCE VALIDATION SUITE")
    print("="*70)

    validator = PerformanceValidator()

    # Run validation steps
    baseline = validator.establish_baseline()
    functional = validator.run_functional_tests()
    memory = validator.measure_memory_usage()

    # Generate report
    report = validator.generate_validation_report(baseline, functional, memory)
    print("\n" + report)

    # Save report
    with open("PERFORMANCE_VALIDATION_PHASE_0.txt", "w") as f:
        f.write(report)

    print(f"\n✅ VALIDATION COMPLETE - Report saved to PERFORMANCE_VALIDATION_PHASE_0.txt")

    return {
        'baseline': baseline,
        'functional': functional,
        'memory': memory
    }


if __name__ == "__main__":
    results = run_performance_validation()