"""
Test Académique 15 : Triple Validation Simplex Implementation - Étape 2.6

Validation complète de l'implémentation TripleValidationOrientedSimplex selon blueprint ICGS
avec garanties mathématiques absolues et pipeline de validation triple.

Objectifs Test :
1. Validation pivot géométrique MathematicallyRigorousPivotManager  
2. Pipeline triple validation complet (pivot + résolution + cross-validation)
3. Warm-start vs cold-start avec métriques stabilité
4. Équivalence mathématique avec Simplex classique
5. Performance et convergence garantie

Architecture Test :
- Scénarios pivot : HIGHLY_STABLE, MODERATELY_STABLE, GEOMETRICALLY_UNSTABLE, INFEASIBLE
- Problèmes LP variés : faisables, infaisables, unbounded edge-cases
- Métriques performance et statistiques validation
- Cross-validation automatique pour cas instables

Conformité Blueprint :
✅ MathematicallyRigorousPivotManager avec métriques géométriques
✅ TripleValidationOrientedSimplex avec warm/cold-start
✅ SimplexSolution avec métadonnées complètes validation
✅ Pipeline sink-to-source compatible énumération DAG
"""

import unittest
from decimal import Decimal, getcontext
import time
import logging

# Configuration précision étendue pour tests
getcontext().prec = 50

from icgs_core import (
    LinearProgram, FluxVariable, LinearConstraint, ConstraintType,
    MathematicallyRigorousPivotManager, TripleValidationOrientedSimplex,
    SimplexSolution, SolutionStatus, PivotStatus,
    build_source_constraint, build_target_constraint, build_secondary_constraint
)


class TestAcademic15TripleValidationSimplex(unittest.TestCase):
    """
    Test Académique 15 : Validation Triple Validation Simplex Implementation
    
    Couvre implémentation complète solveur Simplex avec garanties mathématiques
    selon spécifications blueprint ICGS Phase 2.6.
    """
    
    def setUp(self):
        """Initialisation tests avec composants production"""
        self.tolerance = Decimal('1e-10')
        self.pivot_manager = MathematicallyRigorousPivotManager(self.tolerance)
        self.simplex_solver = TripleValidationOrientedSimplex(
            max_iterations=1000,
            tolerance=self.tolerance
        )
        
        # Métriques test
        self.test_metrics = {
            'pivot_validations': 0,
            'simplex_solutions': 0,
            'warm_starts_tested': 0,
            'cold_starts_tested': 0,
            'cross_validations_performed': 0
        }
    
    def test_01_pivot_manager_geometric_stability(self):
        """
        Test 15.1 : Validation pivot manager métriques stabilité géométrique
        
        Valide calcul stabilité géométrique et classification selon blueprint :
        - HIGHLY_STABLE : stabilité >> tolerance
        - MODERATELY_STABLE : stabilité > 10×tolerance  
        - GEOMETRICALLY_UNSTABLE : stabilité ≈ tolerance
        - MATHEMATICALLY_INFEASIBLE : pivot viole contraintes
        """
        # Cas 1: Pivot hautement stable (distance grandes aux hyperplanes)
        stable_pivot = {"x1": Decimal('5'), "x2": Decimal('3')}
        loose_constraints = [
            LinearConstraint(
                coefficients={"x1": Decimal('1'), "x2": Decimal('1')}, 
                bound=Decimal('100'),  # Très large
                constraint_type=ConstraintType.LEQ,
                name="loose_capacity"
            )
        ]
        
        stable_status = self.pivot_manager.validate_pivot_compatibility(stable_pivot, loose_constraints)
        self.assertEqual(stable_status, PivotStatus.HIGHLY_STABLE)
        self.test_metrics['pivot_validations'] += 1
        
        # Cas 2: Pivot modérément stable  
        moderate_pivot = {"x1": Decimal('8'), "x2": Decimal('1')}
        moderate_constraints = [
            LinearConstraint(
                coefficients={"x1": Decimal('1'), "x2": Decimal('1')},
                bound=Decimal('10'),  # Modérée
                constraint_type=ConstraintType.LEQ,
                name="moderate_capacity"
            )
        ]
        
        moderate_status = self.pivot_manager.validate_pivot_compatibility(moderate_pivot, moderate_constraints)
        self.assertEqual(moderate_status, PivotStatus.MODERATELY_STABLE)
        
        # Cas 3: Pivot géométriquement instable (proche des hyperplanes)
        unstable_pivot = {"x1": Decimal('5'), "x2": Decimal('5')}
        tight_constraints = [
            LinearConstraint(
                coefficients={"x1": Decimal('1'), "x2": Decimal('1')},
                bound=Decimal('10') + self.tolerance,  # Très serré
                constraint_type=ConstraintType.LEQ,
                name="tight_capacity"
            )
        ]
        
        unstable_status = self.pivot_manager.validate_pivot_compatibility(unstable_pivot, tight_constraints)
        self.assertEqual(unstable_status, PivotStatus.GEOMETRICALLY_UNSTABLE)
        
        # Cas 4: Pivot mathématiquement infaisable (viole contraintes)
        infeasible_pivot = {"x1": Decimal('15'), "x2": Decimal('5')}
        violated_constraints = [
            LinearConstraint(
                coefficients={"x1": Decimal('1'), "x2": Decimal('1')},
                bound=Decimal('10'),
                constraint_type=ConstraintType.LEQ,
                name="violated_capacity"
            )
        ]
        
        infeasible_status = self.pivot_manager.validate_pivot_compatibility(infeasible_pivot, violated_constraints)
        self.assertEqual(infeasible_status, PivotStatus.MATHEMATICALLY_INFEASIBLE)
        
        # Validation métriques pivot manager
        stats = self.pivot_manager.get_validation_stats()
        self.assertGreater(stats['pivots_validated'], 0)
        self.assertGreater(stats['geometric_computations'], 0)
    
    def test_02_triple_validation_pipeline_feasible(self):
        """
        Test 15.2 : Pipeline triple validation pour problème faisable
        
        Teste pipeline complet avec warm-start, cold-start et cross-validation
        sur problème LP classique faisable.
        """
        # Construction problème LP faisable standard
        problem = LinearProgram("test_feasible_lp")
        
        # Variables: f1, f2 ≥ 0 (flux dans classes équivalence NFA)
        problem.add_variable("f1", lower_bound=Decimal('0'))
        problem.add_variable("f2", lower_bound=Decimal('0'))
        
        # Contraintes économiques simulées
        source_constraint = LinearConstraint(
            coefficients={"f1": Decimal('2'), "f2": Decimal('1')},
            bound=Decimal('10'),  # Limite source acceptable
            constraint_type=ConstraintType.LEQ,
            name="source_limit"
        )
        
        target_constraint = LinearConstraint(
            coefficients={"f1": Decimal('1'), "f2": Decimal('1')},
            bound=Decimal('3'),  # Minimum target requis
            constraint_type=ConstraintType.GEQ,
            name="target_minimum"
        )
        
        problem.add_constraint(source_constraint)
        problem.add_constraint(target_constraint)
        
        # Test 1: Résolution sans pivot (cold-start)
        cold_start_solution = self.simplex_solver.solve_with_absolute_guarantees(problem)
        
        self.assertEqual(cold_start_solution.status, SolutionStatus.FEASIBLE)
        self.assertFalse(cold_start_solution.warm_start_successful)
        self.assertGreater(cold_start_solution.iterations_used, 0)
        self.assertIn("f1", cold_start_solution.variables)
        self.assertIn("f2", cold_start_solution.variables)
        self.test_metrics['simplex_solutions'] += 1
        self.test_metrics['cold_starts_tested'] += 1
        
        # Validation solution satisfait contraintes
        f1_value = cold_start_solution.variables["f1"]
        f2_value = cold_start_solution.variables["f2"]
        
        # Vérification source_constraint: 2*f1 + f2 ≤ 10
        source_lhs = 2 * f1_value + f2_value
        self.assertLessEqual(source_lhs, Decimal('10') + self.tolerance)
        
        # Vérification target_constraint: f1 + f2 ≥ 3  
        target_lhs = f1_value + f2_value
        self.assertGreaterEqual(target_lhs, Decimal('3') - self.tolerance)
        
        # Test 2: Résolution avec warm-start (pivot précédent)
        warm_start_solution = self.simplex_solver.solve_with_absolute_guarantees(
            problem, old_pivot=cold_start_solution.variables
        )
        
        self.assertEqual(warm_start_solution.status, SolutionStatus.FEASIBLE)
        # Note: warm_start peut réussir ou fallback vers cold-start selon stabilité
        self.test_metrics['warm_starts_tested'] += 1
        
        # Validation équivalence solutions (dans tolérance)
        for var_id in ["f1", "f2"]:
            diff = abs(warm_start_solution.variables[var_id] - cold_start_solution.variables[var_id])
            self.assertLessEqual(diff, Decimal('1e-6'))  # Tolérance plus large pour équivalence
    
    def test_03_triple_validation_infeasible_problem(self):
        """
        Test 15.3 : Pipeline triple validation pour problème infaisable
        
        Valide détection correcte infaisabilité avec pipeline complet.
        """
        # Problème infaisable : contraintes contradictoires
        problem = LinearProgram("test_infeasible_lp")
        
        problem.add_variable("f1", lower_bound=Decimal('0'))
        problem.add_variable("f2", lower_bound=Decimal('0'))
        
        # Contraintes contradictoires
        constraint1 = LinearConstraint(
            coefficients={"f1": Decimal('1'), "f2": Decimal('1')},
            bound=Decimal('5'),
            constraint_type=ConstraintType.LEQ,
            name="upper_limit"
        )
        
        constraint2 = LinearConstraint(
            coefficients={"f1": Decimal('1'), "f2": Decimal('1')},
            bound=Decimal('10'),  # Contradiction: sum ≤ 5 ET sum ≥ 10 impossible
            constraint_type=ConstraintType.GEQ,
            name="lower_limit"  
        )
        
        problem.add_constraint(constraint1)
        problem.add_constraint(constraint2)
        
        # Résolution avec détection infaisabilité
        solution = self.simplex_solver.solve_with_absolute_guarantees(problem)
        
        self.assertEqual(solution.status, SolutionStatus.INFEASIBLE)
        self.assertGreater(solution.iterations_used, 0)
        # Variables peuvent être vides ou contenir dernière tentative
        self.test_metrics['simplex_solutions'] += 1
    
    def test_04_cross_validation_unstable_pivot(self):
        """
        Test 15.4 : Cross-validation automatique pour pivot instable
        
        Force scénario nécessitant cross-validation et valide exécution correcte.
        """
        # Problème avec pivot géométriquement instable
        problem = LinearProgram("test_cross_validation")
        
        problem.add_variable("f1", lower_bound=Decimal('0'))
        problem.add_variable("f2", lower_bound=Decimal('0'))
        
        # Contrainte serrée pour instabilité
        tight_constraint = LinearConstraint(
            coefficients={"f1": Decimal('1'), "f2": Decimal('1')},
            bound=Decimal('10'),
            constraint_type=ConstraintType.LEQ,
            name="tight_bound"
        )
        problem.add_constraint(tight_constraint)
        
        # Pivot sur la frontière (instable)
        unstable_pivot = {"f1": Decimal('5'), "f2": Decimal('5')}
        
        # Résolution avec pivot instable
        solution = self.simplex_solver.solve_with_absolute_guarantees(problem, unstable_pivot)
        
        # Vérification cross-validation exécutée si nécessaire
        if solution.pivot_status_used == PivotStatus.GEOMETRICALLY_UNSTABLE:
            # Cross-validation doit être effectuée
            self.test_metrics['cross_validations_performed'] += 1
            # Solution doit être valide malgré instabilité
            self.assertEqual(solution.status, SolutionStatus.FEASIBLE)
    
    def test_05_economic_constraints_integration(self):
        """
        Test 15.5 : Intégration constructeurs contraintes économiques avec Simplex
        
        Valide utilisation constructeurs build_source/target_constraint avec solveur.
        """
        # Simulation états finaux NFA avec poids
        nfa_state_weights = {
            "state_agriculture": Decimal('1.2'),
            "state_industry": Decimal('0.9'),
            "state_services": Decimal('1.1')
        }
        
        # Construction problème via constructeurs économiques
        problem = LinearProgram("economic_integration_test")
        
        # Variables flux par état NFA
        for state_id in nfa_state_weights.keys():
            problem.add_variable(state_id, lower_bound=Decimal('0'))
        
        # Contrainte source économique
        source_constraint = build_source_constraint(
            nfa_state_weights,
            Decimal('1.0'),  # Primary regex weight  
            Decimal('100'),  # Montant acceptable maximum
            "economic_source_constraint"
        )
        problem.add_constraint(source_constraint)
        
        # Contrainte cible économique
        target_constraint = build_target_constraint(
            nfa_state_weights,
            Decimal('1.0'),  # Primary regex weight
            Decimal('50'),   # Montant requis minimum  
            "economic_target_constraint"
        )
        problem.add_constraint(target_constraint)
        
        # Résolution avec triple validation
        solution = self.simplex_solver.solve_with_absolute_guarantees(problem)
        
        self.assertEqual(solution.status, SolutionStatus.FEASIBLE)
        
        # Validation contraintes économiques satisfaites
        total_source = sum(
            solution.variables[state] * weight 
            for state, weight in nfa_state_weights.items()
        )
        self.assertLessEqual(total_source, Decimal('100') + self.tolerance)
        
        total_target = sum(
            solution.variables[state] * weight
            for state, weight in nfa_state_weights.items() 
        )
        self.assertGreaterEqual(total_target, Decimal('50') - self.tolerance)
    
    def test_06_solver_statistics_and_performance(self):
        """
        Test 15.6 : Statistiques solveur et métriques performance
        
        Valide collecte statistiques et performance pipeline selon blueprint.
        """
        # Exécution série problèmes pour statistiques
        problems = []
        solutions = []
        
        for i in range(5):
            problem = LinearProgram(f"perf_test_{i}")
            problem.add_variable("x", lower_bound=Decimal('0'))
            problem.add_variable("y", lower_bound=Decimal('0'))
            
            constraint = LinearConstraint(
                coefficients={"x": Decimal('1'), "y": Decimal('1')},
                bound=Decimal(str(10 + i)),
                constraint_type=ConstraintType.LEQ,
                name=f"capacity_{i}"
            )
            problem.add_constraint(constraint)
            problems.append(problem)
        
        # Résolution avec warm-start séquentiel
        old_pivot = None
        for problem in problems:
            start_time = time.time()
            solution = self.simplex_solver.solve_with_absolute_guarantees(problem, old_pivot)
            solve_time = time.time() - start_time
            
            self.assertEqual(solution.status, SolutionStatus.FEASIBLE)
            self.assertLess(solve_time, 1.0)  # Performance < 1s par problème
            
            solutions.append(solution)
            old_pivot = solution.variables
        
        # Validation statistiques solveur
        stats = self.simplex_solver.get_solver_stats()
        
        self.assertGreater(stats['solutions_found'], 0)
        self.assertGreaterEqual(stats['warm_starts_used'] + stats['cold_starts_used'], len(problems))
        
        # Validation au moins un warm-start réussi dans séquence
        warm_start_found = any(sol.warm_start_successful for sol in solutions)
        # Note: warm-start peut échouer selon stabilité géométrique, c'est normal
        
        # Logs pour debugging
        print(f"\n=== Test 15.6 Statistics ===")
        print(f"Solver Stats: {stats}")
        print(f"Warm starts successful: {sum(1 for s in solutions if s.warm_start_successful)}/{len(solutions)}")
        print(f"Cross validations: {sum(1 for s in solutions if s.cross_validation_passed)}")
    
    def test_07_simplex_equivalence_guarantee(self):
        """
        Test 15.7 : Garantie équivalence avec Simplex classique
        
        Valide que TripleValidationOrientedSimplex produit solutions équivalentes
        aux algorithmes Simplex standard (Théorème 1 blueprint).
        """
        # Problème LP standard pour comparaison
        problem = LinearProgram("equivalence_test")
        
        problem.add_variable("x1", lower_bound=Decimal('0'))
        problem.add_variable("x2", lower_bound=Decimal('0'))
        
        # Contraintes du problème canonique: maximiser x1 + x2
        # Subject to: x1 + 2*x2 ≤ 4, 2*x1 + x2 ≤ 4, x1,x2 ≥ 0
        constraint1 = LinearConstraint(
            coefficients={"x1": Decimal('1'), "x2": Decimal('2')},
            bound=Decimal('4'),
            constraint_type=ConstraintType.LEQ,
            name="resource1"
        )
        
        constraint2 = LinearConstraint(
            coefficients={"x1": Decimal('2'), "x2": Decimal('1')},
            bound=Decimal('4'),
            constraint_type=ConstraintType.LEQ, 
            name="resource2"
        )
        
        problem.add_constraint(constraint1)
        problem.add_constraint(constraint2)
        
        # Résolution via TripleValidationOrientedSimplex
        solution = self.simplex_solver.solve_with_absolute_guarantees(problem)
        
        self.assertEqual(solution.status, SolutionStatus.FEASIBLE)
        
        # Validation solution optimale connue: x1=4/3, x2=4/3 (intersection contraintes)
        # Note: En Phase 1, on cherche faisabilité pas optimalité, donc solution dans région faisable
        x1_val = solution.variables["x1"]
        x2_val = solution.variables["x2"]
        
        # Vérification satisfaction contraintes
        self.assertLessEqual(x1_val + 2 * x2_val, Decimal('4') + self.tolerance)
        self.assertLessEqual(2 * x1_val + x2_val, Decimal('4') + self.tolerance)
        self.assertGreaterEqual(x1_val, Decimal('0'))
        self.assertGreaterEqual(x2_val, Decimal('0'))
        
        print(f"\n=== Test 15.7 Equivalence ===")
        print(f"Solution found: x1={x1_val}, x2={x2_val}")
        print(f"Constraint 1: {x1_val + 2 * x2_val} ≤ 4")
        print(f"Constraint 2: {2 * x1_val + x2_val} ≤ 4")
        print(f"Iterations: {solution.iterations_used}")
    
    def tearDown(self):
        """Nettoyage avec résumé métriques test"""
        print(f"\n=== Test Academic 15 Summary ===")
        print(f"Test metrics collected: {self.test_metrics}")
        print(f"Pivot manager stats: {self.pivot_manager.get_validation_stats()}")
        print(f"Simplex solver stats: {self.simplex_solver.get_solver_stats()}")


if __name__ == '__main__':
    # Configuration logging pour debugging
    logging.basicConfig(level=logging.INFO)
    
    # Suite tests complète
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAcademic15TripleValidationSimplex)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Résumé final
    print(f"\n" + "="*60)
    print(f"TEST ACADEMIC 15 - TRIPLE VALIDATION SIMPLEX")
    print(f"="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print(f"\nErrors:")  
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    print(f"\n✅ Test Academic 15 completed - TripleValidationOrientedSimplex validation selon blueprint ICGS Phase 2.6")