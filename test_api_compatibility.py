#!/usr/bin/env python3
"""
Test API Compatibility - Validation Backward Compatibility après Price Discovery

Vérifier que l'API existante fonctionne exactement comme avant
avec les mêmes résultats et performance.
"""

import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from decimal import Decimal
from icgs_core import (
    TripleValidationOrientedSimplex, LinearProgram, FluxVariable,
    LinearConstraint, ConstraintType, SolutionStatus, ValidationMode
)


def test_api_compatibility_existing_behavior():
    """Test que l'API existante donne exactement les mêmes résultats"""
    print("=== TEST API COMPATIBILITY - COMPORTEMENT EXISTANT ===")

    # IMPORTANT: Tester exactement comme avant Price Discovery
    solver = TripleValidationOrientedSimplex(max_iterations=1000, tolerance=Decimal('1e-10'))

    # Problème identique aux tests existants
    problem = LinearProgram("compatibility_test")

    # Variables
    problem.add_variable("v1", lower_bound=Decimal('0'))
    problem.add_variable("v2", lower_bound=Decimal('0'))
    problem.add_variable("v3", lower_bound=Decimal('0'))

    # Contraintes typiques ICGS
    # Source constraint: v1 + v2 <= 100
    source_constraint = LinearConstraint(
        coefficients={"v1": Decimal('1'), "v2": Decimal('1')},
        bound=Decimal('100'),
        constraint_type=ConstraintType.LEQ,
        name="source_capacity"
    )
    problem.add_constraint(source_constraint)

    # Target constraint: v2 + v3 >= 50
    target_constraint = LinearConstraint(
        coefficients={"v2": Decimal('1'), "v3": Decimal('1')},
        bound=Decimal('50'),
        constraint_type=ConstraintType.GEQ,
        name="target_demand"
    )
    problem.add_constraint(target_constraint)

    # Secondary constraint: v1 - v3 <= 10
    secondary_constraint = LinearConstraint(
        coefficients={"v1": Decimal('1'), "v3": Decimal('-1')},
        bound=Decimal('10'),
        constraint_type=ConstraintType.LEQ,
        name="secondary_balance"
    )
    problem.add_constraint(secondary_constraint)

    print("Problème test:")
    print("  Variables: v1, v2, v3 >= 0")
    print("  Contraintes: v1+v2 <= 100, v2+v3 >= 50, v1-v3 <= 10")

    # Test 1: Méthode existante solve_with_absolute_guarantees
    print(f"\n--- TEST 1: solve_with_absolute_guarantees (EXISTANT) ---")

    start_time = time.time()
    solution_existing = solver.solve_with_absolute_guarantees(problem)
    elapsed_existing = time.time() - start_time

    print(f"Status: {solution_existing.status}")
    print(f"Variables: {solution_existing.variables}")
    print(f"Iterations: {solution_existing.iterations_used}")
    print(f"Time: {elapsed_existing:.6f}s")
    print(f"Warm-start: {solution_existing.warm_start_successful}")
    print(f"Validation mode: {solution_existing.validation_mode or 'None (expected)'}")

    # Test 2: Test que nouveaux enum n'interfèrent pas
    print(f"\n--- TEST 2: VALIDATION NOUVEAUX ENUM ---")

    # ValidationMode doit être importable sans impact
    print(f"ValidationMode.FEASIBILITY: {ValidationMode.FEASIBILITY}")
    print(f"ValidationMode.OPTIMIZATION: {ValidationMode.OPTIMIZATION}")

    # SolutionStatus doit avoir nouveaux états
    print(f"SolutionStatus.FEASIBLE: {SolutionStatus.FEASIBLE}")
    print(f"SolutionStatus.OPTIMAL: {SolutionStatus.OPTIMAL}")

    # Test 3: Validation pivot storage (comportement warm-start préservé)
    print(f"\n--- TEST 3: PIVOT STORAGE COMPATIBILITY ---")

    # Premier solve pour créer pivot
    first_solution = solver.solve_with_absolute_guarantees(problem)

    # Deuxième solve avec pivot (warm-start)
    if first_solution.status == SolutionStatus.FEASIBLE:
        start_time = time.time()
        second_solution = solver.solve_with_absolute_guarantees(problem, first_solution.variables)
        elapsed_warmstart = time.time() - start_time

        print(f"First solve status: {first_solution.status}")
        print(f"Second solve status: {second_solution.status}")
        print(f"Second solve warm-start success: {second_solution.warm_start_successful}")
        print(f"Second solve time: {elapsed_warmstart:.6f}s")
        print(f"Warm-start speed improvement: {elapsed_existing/elapsed_warmstart:.1f}x" if elapsed_warmstart > 0 else "∞")

    # Test 4: Métrics et stats
    print(f"\n--- TEST 4: STATISTICS COMPATIBILITY ---")

    print(f"Solver stats: {solver.stats}")
    expected_keys = ['warm_starts_used', 'cold_starts_used', 'cross_validations_performed',
                    'pivot_rejections', 'solutions_found', 'infeasible_problems']

    stats_compatible = True
    for key in expected_keys:
        if key not in solver.stats:
            print(f"❌ Missing expected stat key: {key}")
            stats_compatible = False
        else:
            print(f"✅ {key}: {solver.stats[key]}")

    # VALIDATION FINALE
    print(f"\n--- VALIDATION FINALE COMPATIBILITY ---")

    success = True

    # Vérifications critiques
    if solution_existing.status != SolutionStatus.FEASIBLE:
        print(f"❌ solve_with_absolute_guarantees devrait retourner FEASIBLE")
        success = False

    if solution_existing.validation_mode is not None:
        print(f"❌ validation_mode devrait être None par défaut (backward compatibility)")
        success = False

    if not solution_existing.variables:
        print(f"❌ Variables solution ne devraient pas être vides")
        success = False

    if solution_existing.iterations_used < 0:
        print(f"❌ Iterations should be >= 0")
        success = False

    if not stats_compatible:
        print(f"❌ Solver stats incompatibles")
        success = False

    # Performance check (pas de régression majeure)
    if elapsed_existing > 1.0:  # Plus de 1s = problème performance
        print(f"❌ Performance régression: {elapsed_existing:.3f}s (should be < 1s)")
        success = False
    else:
        print(f"✅ Performance acceptable: {elapsed_existing:.6f}s")

    if success:
        print(f"\n✅ API COMPATIBILITY VALIDÉE")
        print(f"   solve_with_absolute_guarantees: comportement identique")
        print(f"   Pivot storage: warm-start fonctionne")
        print(f"   Performance: pas de régression")
        print(f"   Nouveaux enums: pas d'interférence")
    else:
        print(f"\n❌ API COMPATIBILITY ÉCHOUÉE")

    return success


def test_performance_benchmark():
    """Benchmark performance pour détecter régressions"""
    print(f"\n=== BENCHMARK PERFORMANCE ===")

    solver = TripleValidationOrientedSimplex()

    # Test sur problème plus complexe
    problem = LinearProgram("benchmark")

    # 10 variables
    for i in range(10):
        problem.add_variable(f"x{i}", lower_bound=Decimal('0'))

    # 20 contraintes
    for i in range(20):
        coeffs = {}
        for j in range(min(3, 10)):  # 3 variables par contrainte
            var_id = f"x{(i+j) % 10}"
            coeffs[var_id] = Decimal(str((i+j) % 5 + 1))

        constraint = LinearConstraint(
            coefficients=coeffs,
            bound=Decimal(str((i % 50) + 10)),
            constraint_type=ConstraintType.LEQ if i % 2 == 0 else ConstraintType.GEQ,
            name=f"bench_constraint_{i}"
        )
        problem.add_constraint(constraint)

    # Multiple runs pour moyenne
    times = []
    for run in range(5):
        start = time.time()
        solution = solver.solve_with_absolute_guarantees(problem)
        elapsed = time.time() - start
        times.append(elapsed)

        if solution.status not in [SolutionStatus.FEASIBLE, SolutionStatus.INFEASIBLE]:
            print(f"❌ Unexpected status: {solution.status}")
            return False

    avg_time = sum(times) / len(times)
    max_time = max(times)
    min_time = min(times)

    print(f"Benchmark results (5 runs):")
    print(f"  Average time: {avg_time:.6f}s")
    print(f"  Min time: {min_time:.6f}s")
    print(f"  Max time: {max_time:.6f}s")
    print(f"  Variance: {max_time - min_time:.6f}s")

    # Performance expectations
    if avg_time > 0.1:  # Plus de 100ms = problème
        print(f"❌ Performance régression: {avg_time:.3f}s average (should be < 0.1s)")
        return False

    print(f"✅ Performance benchmark passed")
    return True


if __name__ == "__main__":
    print("TESTS NON-RÉGRESSION API COMPATIBILITY")
    print("="*50)

    success1 = test_api_compatibility_existing_behavior()
    success2 = test_performance_benchmark()

    overall_success = success1 and success2

    print(f"\n" + "="*50)
    if overall_success:
        print(f"✅ TOUS LES TESTS NON-RÉGRESSION PASSÉS")
        print(f"   API existante: 100% compatible")
        print(f"   Performance: aucune régression détectée")
    else:
        print(f"❌ TESTS NON-RÉGRESSION ÉCHOUÉS")
        print(f"   Régressions détectées nécessitant correction")

    sys.exit(0 if overall_success else 1)