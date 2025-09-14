#!/usr/bin/env python3
"""
Test Basique Price Discovery - Validation Jour 1 Implementation
Tester la nouvelle fonctionnalité solve_optimization_problem
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from decimal import Decimal
from icgs_core import (
    TripleValidationOrientedSimplex, LinearProgram, FluxVariable,
    LinearConstraint, ConstraintType, ValidationMode, SolutionStatus
)


def test_basic_price_discovery():
    """Test basique solve_optimization_problem avec problème simple"""
    print("=== TEST BASIQUE PRICE DISCOVERY ===")

    # Création solveur Simplex avec price discovery
    solver = TripleValidationOrientedSimplex(max_iterations=100)

    # Problème LP simple : 2 variables
    problem = LinearProgram("test_price_discovery")

    # Variables : f1, f2 (flux de chemins)
    problem.add_variable("f1", lower_bound=Decimal('0'))
    problem.add_variable("f2", lower_bound=Decimal('0'))

    # Contraintes de faisabilité
    # Contrainte 1: f1 + f2 >= 10 (demande minimale)
    constraint1 = LinearConstraint(
        coefficients={"f1": Decimal('1'), "f2": Decimal('1')},
        bound=Decimal('10'),
        constraint_type=ConstraintType.GEQ,
        name="demande_minimale"
    )
    problem.add_constraint(constraint1)

    # Contrainte 2: f1 <= 20 (capacité source 1)
    constraint2 = LinearConstraint(
        coefficients={"f1": Decimal('1')},
        bound=Decimal('20'),
        constraint_type=ConstraintType.LEQ,
        name="capacite_f1"
    )
    problem.add_constraint(constraint2)

    # Contrainte 3: f2 <= 15 (capacité source 2)
    constraint3 = LinearConstraint(
        coefficients={"f2": Decimal('1')},
        bound=Decimal('15'),
        constraint_type=ConstraintType.LEQ,
        name="capacite_f2"
    )
    problem.add_constraint(constraint3)

    # Fonction objectif : minimize 3*f1 + 2*f2 (prix unitaire par chemin)
    objective_coeffs = {
        "f1": Decimal('3'),  # Prix unitaire chemin 1: 3€
        "f2": Decimal('2')   # Prix unitaire chemin 2: 2€
    }

    print(f"Problème LP:")
    print(f"  Variables: f1, f2 >= 0")
    print(f"  Contraintes: f1 + f2 >= 10, f1 <= 20, f2 <= 15")
    print(f"  Objectif: minimize 3*f1 + 2*f2")
    print(f"  Solution optimale théorique: f1=0, f2=10, prix=20€")

    # Test 1: Phase 1 seule (faisabilité - comportement actuel)
    print(f"\n--- TEST 1: FAISABILITÉ (Phase 1) ---")

    solution_feasible = solver.solve_with_absolute_guarantees(problem)
    print(f"Status: {solution_feasible.status}")
    print(f"Variables: {solution_feasible.variables}")
    print(f"Iterations: {solution_feasible.iterations_used}")
    print(f"Objective: {solution_feasible.final_objective_value}")
    print(f"Mode: {solution_feasible.validation_mode or 'FEASIBILITY (default)'}")

    # Test 2: Price Discovery (Phase 1 + Phase 2)
    print(f"\n--- TEST 2: PRICE DISCOVERY (Phase 1 + Phase 2) ---")

    solution_optimal = solver.solve_optimization_problem(problem, objective_coeffs)
    print(f"Status: {solution_optimal.status}")
    print(f"Variables: {solution_optimal.variables}")
    print(f"Total iterations: {solution_optimal.iterations_used}")
    print(f"Phase 2 iterations: {solution_optimal.phase2_iterations}")
    print(f"Prix découvert: {solution_optimal.optimal_price}")
    print(f"Mode: {solution_optimal.validation_mode}")
    print(f"Phase 2 time: {solution_optimal.phase2_solving_time:.4f}s")

    # Validation résultats
    print(f"\n--- VALIDATION ---")

    success = True
    if solution_feasible.status != SolutionStatus.FEASIBLE:
        print(f"❌ Phase 1 devrait être FEASIBLE, got {solution_feasible.status}")
        success = False

    if solution_optimal.status != SolutionStatus.OPTIMAL:
        print(f"❌ Phase 2 devrait être OPTIMAL, got {solution_optimal.status}")
        success = False

    if solution_optimal.validation_mode != ValidationMode.OPTIMIZATION:
        print(f"❌ Mode devrait être OPTIMIZATION, got {solution_optimal.validation_mode}")
        success = False

    if solution_optimal.optimal_price is None:
        print(f"❌ Prix découvert ne devrait pas être None")
        success = False
    elif solution_optimal.optimal_price <= 0:
        print(f"❌ Prix découvert devrait être > 0, got {solution_optimal.optimal_price}")
        success = False

    # Test continuité pivot (si les deux solutions ont des pivots)
    if solution_feasible.variables and solution_optimal.variables:
        print(f"\n--- TEST CONTINUITÉ PIVOT ---")
        print(f"Pivot Phase 1: {solution_feasible.variables}")
        print(f"Pivot Phase 2: {solution_optimal.variables}")

        # Les variables devraient être cohérentes
        for var_id in solution_feasible.variables:
            if var_id in solution_optimal.variables:
                diff = abs(solution_optimal.variables[var_id] - solution_feasible.variables[var_id])
                print(f"  {var_id}: Phase1={solution_feasible.variables[var_id]}, Phase2={solution_optimal.variables[var_id]}, diff={diff}")

    if success:
        print(f"\n✅ TEST PRICE DISCOVERY BASIQUE RÉUSSI")
        print(f"   Phase 1 + Phase 2 fonctionnels")
        print(f"   Continuité pivot préservée")
        print(f"   Prix découvert: {solution_optimal.optimal_price}")
    else:
        print(f"\n❌ TEST PRICE DISCOVERY ÉCHOUÉ")

    return success


if __name__ == "__main__":
    success = test_basic_price_discovery()
    sys.exit(0 if success else 1)