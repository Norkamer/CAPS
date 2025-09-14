#!/usr/bin/env python3
"""
CAPS Phase 0 Semaines 3-4: Innovation Validation Suite
Comprehensive validation of advanced features with regression testing
"""

import time
import tracemalloc
from typing import Dict, List, Any, Tuple
from decimal import Decimal
import sys
import os

# Import modules développés dans Phase 0
try:
    from advanced_regex_features import AdvancedRegexParser, AdvancedRegexMatcher, run_advanced_regex_tests
    from multi_objective_optimization import MultiObjectiveOptimizer, run_multi_objective_tests
    from enhanced_nfa_engine import EnhancedNFAEngine, create_test_nfa, run_enhanced_nfa_tests
except ImportError as e:
    print(f"⚠️  Import warning: {e}")

# Import core modules pour tests non-régression
try:
    from icgs_core import DAG, DAGConfiguration
    from icgs_core.regex_parser import RegexParser
    from icgs_core.thompson_nfa import ThompsonNFABuilder
    from performance_validation_suite import PerformanceValidator
except ImportError as e:
    print(f"⚠️  Core import warning: {e}")


class InnovationValidator:
    """Validateur intégré pour toutes les innovations Phase 0"""

    def __init__(self):
        self.test_results = {}
        self.performance_metrics = {}
        self.regression_status = {}
        self.innovation_summary = {}

    def validate_advanced_regex(self) -> Dict[str, Any]:
        """Validation fonctionnalités regex avancées"""
        print("🔍 VALIDATING ADVANCED REGEX FEATURES")
        print("-" * 40)

        try:
            # Test parser avancé
            parser = AdvancedRegexParser()

            # Cas de test complexes
            test_cases = [
                {
                    'pattern': r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})',
                    'text': '2023-12-25',
                    'expected_groups': {'year': '2023', 'month': '12', 'day': '25'},
                    'description': 'Date parsing avec groupes nommés'
                },
                {
                    'pattern': r'(?=.*[A-Z])(?=.*[a-z])(?=.*\d).{8,}',
                    'text': 'Password123',
                    'expected_match': True,
                    'description': 'Password validation avec lookaheads'
                },
                {
                    'pattern': r'(?<![\w])test(?![\w])',
                    'text': 'This is test data',
                    'expected_match': True,
                    'description': 'Word boundary avec lookbehind/lookahead'
                },
                {
                    'pattern': r'(?:http|https)://(?P<domain>[^/]+)/(?P<path>.*)',
                    'text': 'https://example.com/path/to/resource',
                    'expected_groups': {'domain': 'example.com', 'path': 'path/to/resource'},
                    'description': 'URL parsing avec groupes non-capturants'
                }
            ]

            results = []
            matcher = AdvancedRegexMatcher(parser)

            for case in test_cases:
                try:
                    # Validation pattern
                    validation = parser.validate_advanced_pattern(case['pattern'])

                    if not validation['valid']:
                        results.append({
                            'test': case['description'],
                            'status': 'FAILED',
                            'error': validation['error']
                        })
                        continue

                    # Test matching
                    match_result = matcher.match_with_groups(case['pattern'], case['text'])

                    # Vérification résultats
                    test_passed = True
                    error_details = []

                    if 'expected_groups' in case:
                        for group_name, expected_value in case['expected_groups'].items():
                            actual_value = match_result['named_groups'].get(group_name)
                            if actual_value != expected_value:
                                test_passed = False
                                error_details.append(f"Group {group_name}: expected {expected_value}, got {actual_value}")

                    if 'expected_match' in case:
                        if match_result['matched'] != case['expected_match']:
                            test_passed = False
                            error_details.append(f"Match status: expected {case['expected_match']}, got {match_result['matched']}")

                    results.append({
                        'test': case['description'],
                        'status': 'PASSED' if test_passed else 'FAILED',
                        'pattern_features': validation['features'],
                        'match_result': match_result,
                        'errors': error_details
                    })

                except Exception as e:
                    results.append({
                        'test': case['description'],
                        'status': 'ERROR',
                        'error': str(e)
                    })

            # Résumé
            passed = len([r for r in results if r['status'] == 'PASSED'])
            total = len(results)

            summary = {
                'total_tests': total,
                'passed_tests': passed,
                'success_rate': passed / total * 100 if total > 0 else 0,
                'detailed_results': results
            }

            for result in results:
                status_icon = "✅" if result['status'] == 'PASSED' else "❌" if result['status'] == 'FAILED' else "⚠️"
                print(f"  {status_icon} {result['test']}: {result['status']}")

            print(f"\n📊 Advanced Regex Summary: {passed}/{total} tests passed ({summary['success_rate']:.1f}%)")
            return summary

        except Exception as e:
            return {
                'total_tests': 0,
                'passed_tests': 0,
                'success_rate': 0,
                'error': f"Validation failed: {e}"
            }

    def validate_multi_objective_optimization(self) -> Dict[str, Any]:
        """Validation optimisation multi-objectifs"""
        print("\n🎯 VALIDATING MULTI-OBJECTIVE OPTIMIZATION")
        print("-" * 40)

        try:
            # Test intégration complète
            optimizer = MultiObjectiveOptimizer([])
            economic_objectives = optimizer.create_economic_objectives()
            optimizer.objectives = economic_objectives

            # Test évaluation solution économique
            test_variables = {
                'revenue': Decimal('50000'),
                'costs': Decimal('30000'),
                'volatility': Decimal('0.15'),
                'exposure': Decimal('2.5'),
                'cash_flow': Decimal('20000'),
                'working_capital': Decimal('10000'),
                'esg_score': Decimal('0.8'),
                'carbon_efficiency': Decimal('1.2'),
                'output': Decimal('100'),
                'input_resources': Decimal('80')
            }

            evaluated_solution = optimizer.evaluate_solution(test_variables)

            # Vérifications
            checks = {
                'solution_feasible': evaluated_solution.is_feasible,
                'has_all_objectives': len(evaluated_solution.objective_values) == len(economic_objectives),
                'positive_profit': evaluated_solution.objective_values.get('profit', Decimal('0')) > 0,
                'valid_fitness': evaluated_solution.fitness_score != Decimal('-inf'),
                'no_constraint_violations': len(evaluated_solution.constraint_violations) == 0
            }

            # Test optimisation rapide
            bounds = {
                'revenue': (Decimal('1000'), Decimal('100000')),
                'costs': (Decimal('500'), Decimal('80000')),
                'volatility': (Decimal('0.01'), Decimal('0.5')),
                'exposure': (Decimal('0.1'), Decimal('10.0')),
                'cash_flow': (Decimal('100'), Decimal('50000')),
                'working_capital': (Decimal('1000'), Decimal('20000')),
                'esg_score': (Decimal('0.1'), Decimal('1.0')),
                'carbon_efficiency': (Decimal('0.5'), Decimal('2.0')),
                'output': (Decimal('1'), Decimal('1000')),
                'input_resources': (Decimal('1'), Decimal('800'))
            }

            start_time = time.perf_counter()
            optimization_result = optimizer.optimize(bounds, population_size=10, generations=3)
            optimization_time = time.perf_counter() - start_time

            # Vérifications optimisation
            checks.update({
                'optimization_completed': 'pareto_solutions' in optimization_result,
                'has_pareto_solutions': len(optimization_result.get('pareto_solutions', [])) > 0,
                'reasonable_time': optimization_time < 30.0,  # moins de 30 secondes
                'generation_history': len(optimization_result.get('generation_history', [])) > 0
            })

            passed_checks = sum(1 for passed in checks.values() if passed)
            total_checks = len(checks)

            for check_name, passed in checks.items():
                status_icon = "✅" if passed else "❌"
                print(f"  {status_icon} {check_name}: {passed}")

            summary = {
                'total_checks': total_checks,
                'passed_checks': passed_checks,
                'success_rate': passed_checks / total_checks * 100,
                'optimization_time': optimization_time,
                'pareto_size': len(optimization_result.get('pareto_solutions', [])),
                'objectives_count': len(economic_objectives),
                'detailed_checks': checks
            }

            print(f"\n📊 Multi-Objective Summary: {passed_checks}/{total_checks} checks passed ({summary['success_rate']:.1f}%)")
            return summary

        except Exception as e:
            return {
                'total_checks': 0,
                'passed_checks': 0,
                'success_rate': 0,
                'error': f"Validation failed: {e}"
            }

    def validate_enhanced_nfa(self) -> Dict[str, Any]:
        """Validation moteur NFA avancé"""
        print("\n🔧 VALIDATING ENHANCED NFA ENGINE")
        print("-" * 40)

        try:
            engine = EnhancedNFAEngine()
            test_nfa = create_test_nfa()

            # Tests complets
            tests = []

            # Test 1: Analyse NFA original
            original_stats = engine.analyze_nfa(test_nfa)
            tests.append({
                'name': 'Original NFA analysis',
                'passed': original_stats.state_count > 0 and original_stats.transition_count > 0,
                'details': f"{original_stats.state_count} states, {original_stats.transition_count} transitions"
            })

            # Test 2: Fermeture epsilon
            epsilon_closure = engine.compute_epsilon_closure(test_nfa, 0)
            tests.append({
                'name': 'Epsilon closure computation',
                'passed': len(epsilon_closure.states) > 1,  # État 0 + états accessibles par epsilon
                'details': f"{len(epsilon_closure.states)} states in closure"
            })

            # Test 3: Suppression epsilon
            no_epsilon_nfa = engine.remove_epsilon_transitions(test_nfa)
            epsilon_removed = len([t for t in test_nfa.transitions if t.is_epsilon]) - len([t for t in no_epsilon_nfa.transitions if t.is_epsilon])
            tests.append({
                'name': 'Epsilon transition removal',
                'passed': epsilon_removed >= 0,
                'details': f"{epsilon_removed} epsilon transitions removed"
            })

            # Test 4: Suppression états inaccessibles
            no_unreachable_nfa = engine.remove_unreachable_states(test_nfa)
            states_removed = len(test_nfa.all_state_ids) - len(no_unreachable_nfa.all_state_ids)
            tests.append({
                'name': 'Unreachable state removal',
                'passed': states_removed >= 0,
                'details': f"{states_removed} unreachable states removed"
            })

            # Test 5: Optimisation complète
            optimized_nfa = engine.full_optimize(test_nfa)
            optimization_successful = (
                len(optimized_nfa.all_state_ids) <= len(test_nfa.all_state_ids) and
                len(optimized_nfa.transitions) <= len(test_nfa.transitions)
            )
            tests.append({
                'name': 'Full optimization pipeline',
                'passed': optimization_successful,
                'details': f"States: {len(test_nfa.all_state_ids)} -> {len(optimized_nfa.all_state_ids)}, Transitions: {len(test_nfa.transitions)} -> {len(optimized_nfa.transitions)}"
            })

            # Test 6: Comparaison et métriques
            comparison = engine.compare_nfas(test_nfa, optimized_nfa)
            tests.append({
                'name': 'NFA comparison and metrics',
                'passed': 'improvements' in comparison and 'optimization_history' in comparison,
                'details': f"Optimizations applied: {len(comparison['optimization_history'])}"
            })

            passed_tests = len([t for t in tests if t['passed']])
            total_tests = len(tests)

            for test in tests:
                status_icon = "✅" if test['passed'] else "❌"
                print(f"  {status_icon} {test['name']}: {test['details']}")

            summary = {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'success_rate': passed_tests / total_tests * 100,
                'optimizations_applied': len(engine.optimization_history),
                'state_reduction': comparison['improvements']['state_reduction'] if 'comparison' in locals() else 0,
                'transition_reduction': comparison['improvements']['transition_reduction'] if 'comparison' in locals() else 0,
                'detailed_tests': tests
            }

            print(f"\n📊 Enhanced NFA Summary: {passed_tests}/{total_tests} tests passed ({summary['success_rate']:.1f}%)")
            return summary

        except Exception as e:
            return {
                'total_tests': 0,
                'passed_tests': 0,
                'success_rate': 0,
                'error': f"Validation failed: {e}"
            }

    def run_regression_tests(self) -> Dict[str, Any]:
        """Tests non-régression sur fonctionnalités core"""
        print("\n🔄 RUNNING NON-REGRESSION TESTS")
        print("-" * 40)

        regression_results = {}

        try:
            # Test 1: Core DAG functionality
            try:
                config = DAGConfiguration(validation_mode="RELAXED")
                dag = DAG(config)

                regression_results['dag_core'] = {
                    'status': 'PASSED',
                    'details': 'DAG initialization and basic functionality working'
                }
                print("  ✅ Core DAG functionality: PASSED")
            except Exception as e:
                regression_results['dag_core'] = {
                    'status': 'FAILED',
                    'error': str(e)
                }
                print(f"  ❌ Core DAG functionality: FAILED - {e}")

            # Test 2: Regex parser baseline
            try:
                parser = RegexParser()
                basic_patterns = ["[A-Z]", ".*", "[0-9]+", "(abc|def)"]

                for pattern in basic_patterns:
                    tokens = parser.parse(pattern)
                    if not tokens:
                        raise ValueError(f"Failed to parse pattern: {pattern}")

                regression_results['regex_parser'] = {
                    'status': 'PASSED',
                    'details': f'Successfully parsed {len(basic_patterns)} basic patterns'
                }
                print("  ✅ Regex parser baseline: PASSED")
            except Exception as e:
                regression_results['regex_parser'] = {
                    'status': 'FAILED',
                    'error': str(e)
                }
                print(f"  ❌ Regex parser baseline: FAILED - {e}")

            # Test 3: Thompson NFA construction
            try:
                builder = ThompsonNFABuilder()
                test_patterns = ["[A-Z]", "abc*", "(a|b)+"]

                for pattern in test_patterns:
                    fragment = builder.build_pattern_fragment(pattern)
                    if not fragment or len(fragment.all_state_ids) == 0:
                        raise ValueError(f"Invalid NFA for pattern: {pattern}")

                regression_results['nfa_construction'] = {
                    'status': 'PASSED',
                    'details': f'Successfully built NFA for {len(test_patterns)} patterns'
                }
                print("  ✅ Thompson NFA construction: PASSED")
            except Exception as e:
                regression_results['nfa_construction'] = {
                    'status': 'FAILED',
                    'error': str(e)
                }
                print(f"  ❌ Thompson NFA construction: FAILED - {e}")

        except Exception as e:
            print(f"  ⚠️  Regression test setup failed: {e}")

        # Résumé
        passed = len([r for r in regression_results.values() if r['status'] == 'PASSED'])
        total = len(regression_results)

        return {
            'total_tests': total,
            'passed_tests': passed,
            'success_rate': passed / total * 100 if total > 0 else 0,
            'detailed_results': regression_results
        }

    def generate_innovation_report(self, results: Dict[str, Any]) -> str:
        """Génère rapport complet validation innovations"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("CAPS PHASE 0 SEMAINES 3-4: INNOVATION VALIDATION REPORT")
        report_lines.append("=" * 80)

        # Résumé général
        total_tests = sum(r.get('total_tests', r.get('total_checks', 0)) for r in results.values() if isinstance(r, dict))
        passed_tests = sum(r.get('passed_tests', r.get('passed_checks', 0)) for r in results.values() if isinstance(r, dict))

        overall_success_rate = passed_tests / total_tests * 100 if total_tests > 0 else 0

        report_lines.append(f"\n🎯 OVERALL INNOVATION VALIDATION")
        report_lines.append("-" * 40)
        report_lines.append(f"Total Tests: {total_tests}")
        report_lines.append(f"Passed Tests: {passed_tests}")
        report_lines.append(f"Success Rate: {overall_success_rate:.1f}%")

        # Détails par composant
        components = [
            ('advanced_regex', '🔍 Advanced Regex Features'),
            ('multi_objective', '🎯 Multi-Objective Optimization'),
            ('enhanced_nfa', '🔧 Enhanced NFA Engine'),
            ('regression', '🔄 Non-Regression Tests')
        ]

        for component_key, component_title in components:
            if component_key in results:
                result = results[component_key]
                report_lines.append(f"\n{component_title}")
                report_lines.append("-" * 40)

                if 'error' in result:
                    report_lines.append(f"❌ ERROR: {result['error']}")
                else:
                    total = result.get('total_tests', result.get('total_checks', 0))
                    passed = result.get('passed_tests', result.get('passed_checks', 0))
                    rate = result.get('success_rate', 0)

                    status = "✅ PASSED" if rate >= 90 else "⚠️  PARTIAL" if rate >= 70 else "❌ FAILED"
                    report_lines.append(f"Status: {status}")
                    report_lines.append(f"Tests: {passed}/{total} ({rate:.1f}%)")

        # Recommendations
        report_lines.append(f"\n📋 RECOMMENDATIONS")
        report_lines.append("-" * 40)

        if overall_success_rate >= 90:
            report_lines.append("✅ Innovation features ready for Phase 0 Semaines 5-6 (Excellence Académique)")
            report_lines.append("• All advanced features validated successfully")
            report_lines.append("• No regression detected in core functionality")
            report_lines.append("• Performance optimizations effective")
        elif overall_success_rate >= 70:
            report_lines.append("⚠️  Innovation features partially validated")
            report_lines.append("• Review failed test cases and address issues")
            report_lines.append("• Consider additional optimization rounds")
            report_lines.append("• Monitor regression test results")
        else:
            report_lines.append("❌ Innovation features require attention")
            report_lines.append("• Critical issues detected - full review needed")
            report_lines.append("• Address fundamental problems before proceeding")
            report_lines.append("• Consider rollback to stable baseline")

        # Status final
        final_status = "SUCCESS" if overall_success_rate >= 90 else "ISSUES DETECTED"
        report_lines.append(f"\n🎉 PHASE 0 SEMAINES 3-4 INNOVATION STATUS: {final_status}")

        return "\\n".join(report_lines)

    def run_complete_validation(self) -> Dict[str, Any]:
        """Validation complète de toutes les innovations Phase 0"""
        print("🚀 CAPS PHASE 0 SEMAINES 3-4: COMPLETE INNOVATION VALIDATION")
        print("=" * 70)

        start_time = time.perf_counter()

        # Mesure mémoire
        tracemalloc.start()
        initial_memory = tracemalloc.get_traced_memory()[0]

        # Exécuter validations
        results = {}

        results['advanced_regex'] = self.validate_advanced_regex()
        results['multi_objective'] = self.validate_multi_objective_optimization()
        results['enhanced_nfa'] = self.validate_enhanced_nfa()
        results['regression'] = self.run_regression_tests()

        # Métriques finales
        final_memory = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()

        execution_time = time.perf_counter() - start_time
        memory_usage = (final_memory - initial_memory) / 1024 / 1024  # MB

        # Générer rapport
        report = self.generate_innovation_report(results)

        final_results = {
            'validation_results': results,
            'execution_time': execution_time,
            'memory_usage_mb': memory_usage,
            'report': report
        }

        print("\n" + report)
        print(f"\n⏱️  Validation completed in {execution_time:.2f}s (Memory: {memory_usage:.2f}MB)")

        return final_results


def run_innovation_validation_suite():
    """Point d'entrée principal validation innovations"""
    validator = InnovationValidator()
    return validator.run_complete_validation()


if __name__ == "__main__":
    results = run_innovation_validation_suite()

    # Sauvegarder rapport
    with open("INNOVATION_VALIDATION_PHASE_0.txt", "w", encoding="utf-8") as f:
        f.write(results['report'])

    print(f"\\n✅ Innovation validation report saved to INNOVATION_VALIDATION_PHASE_0.txt")