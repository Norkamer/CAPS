"""
Test Académique 4: Validation Contraintes LP - Satisfaction Mathématique

Ce test valide rigoureusement les propriétés mathématiques des contraintes
de programmation linéaire selon le blueprint ICGS avec précision Decimal.

Propriétés testées:
1. Satisfaction Contraintes: Évaluation correcte LEQ/GEQ/EQ avec tolerances
2. Calcul Violations: Magnitude violations et slack/surplus précis
3. Validation Problème LP: Cohérence variables/contraintes/bounds
4. Faisabilité Solution: Tests avec tolerances numériques strictes
5. Extraction Matrice: Génération matrice standard form Ax≤b
6. Constructeurs Économiques: Contraintes source/target/secondary
7. Précision Decimal: Évitement erreurs floating-point 
8. Performance Construction: Complexité acceptable problèmes moyens
9. Intégration NFA-LP: Pipeline classifications → contraintes

Niveau académique: Validation formelle propriétés mathématiques LP
"""

import pytest
import time
from decimal import Decimal
from typing import Dict, List, Tuple

# Import des modules à tester
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_core.linear_programming import (
    LinearProgram, FluxVariable, LinearConstraint, ConstraintType,
    build_source_constraint, build_target_constraint, build_secondary_constraint,
    build_equality_constraint, create_simple_lp_problem, validate_economic_consistency
)


class TestAcademicLPConstraints:
    """Suite de tests académiques pour validation contraintes LP"""

    def setup_method(self):
        """Setup clean pour chaque test avec problème LP baseline"""
        self.lp = LinearProgram("academic_test_lp")
        self.tolerance = Decimal('1e-12')
        self.baseline_time = time.time()

    def test_constraint_satisfaction_correctness(self):
        """
        PROPRIÉTÉ 1: Satisfaction Contraintes Correcte
        Évaluation mathématiquement rigoureuse LEQ/GEQ/EQ
        """
        # Variables de test
        variables = {
            "x1": Decimal('3.5'),
            "x2": Decimal('2.0'),
            "x3": Decimal('1.5')
        }
        
        # Test contrainte LEQ : 2*x1 + x2 ≤ 9 
        constraint_leq = LinearConstraint(
            coefficients={"x1": Decimal('2'), "x2": Decimal('1')},
            bound=Decimal('9'),
            constraint_type=ConstraintType.LEQ,
            name="test_leq"
        )
        
        # LHS = 2*3.5 + 1*2.0 = 7.0 + 2.0 = 9.0
        lhs_value = constraint_leq.evaluate(variables)
        assert lhs_value == Decimal('9.0'), f"LHS evaluation incorrect: {lhs_value}"
        
        # 9.0 ≤ 9.0 → True (avec tolérance)
        assert constraint_leq.is_satisfied(variables), "LEQ constraint should be satisfied"
        assert constraint_leq.get_violation(variables) == Decimal('0'), "No violation expected"
        
        # Test contrainte GEQ : x1 + 2*x2 ≥ 7
        constraint_geq = LinearConstraint(
            coefficients={"x1": Decimal('1'), "x2": Decimal('2')},
            bound=Decimal('7'),
            constraint_type=ConstraintType.GEQ,
            name="test_geq"
        )
        
        # LHS = 3.5 + 2*2.0 = 7.5
        lhs_geq = constraint_geq.evaluate(variables)
        assert lhs_geq == Decimal('7.5'), f"GEQ LHS incorrect: {lhs_geq}"
        
        # 7.5 ≥ 7.0 → True
        assert constraint_geq.is_satisfied(variables), "GEQ constraint should be satisfied"
        assert constraint_geq.get_violation(variables) == Decimal('0'), "No violation expected"
        
        # Test contrainte EQ : x1 + x3 = 5.0
        constraint_eq = LinearConstraint(
            coefficients={"x1": Decimal('1'), "x3": Decimal('1')},
            bound=Decimal('5.0'),
            constraint_type=ConstraintType.EQ,
            name="test_eq"
        )
        
        # LHS = 3.5 + 1.5 = 5.0
        lhs_eq = constraint_eq.evaluate(variables)
        assert lhs_eq == Decimal('5.0'), f"EQ LHS incorrect: {lhs_eq}"
        
        # 5.0 = 5.0 → True
        assert constraint_eq.is_satisfied(variables), "EQ constraint should be satisfied"
        assert constraint_eq.get_violation(variables) == Decimal('0'), "No violation expected"

    def test_violation_calculation_precision(self):
        """
        PROPRIÉTÉ 2: Calcul Violations Précis
        Magnitude violations et slack/surplus avec Decimal
        """
        variables = {"x1": Decimal('5'), "x2": Decimal('3')}
        
        # Test violation LEQ : 2*x1 + x2 ≤ 10
        # LHS = 2*5 + 3 = 13, bound = 10 → violation = 3
        violated_leq = LinearConstraint(
            coefficients={"x1": Decimal('2'), "x2": Decimal('1')},
            bound=Decimal('10'),
            constraint_type=ConstraintType.LEQ,
            name="violated_leq"
        )
        
        assert not violated_leq.is_satisfied(variables), "LEQ should be violated"
        violation_leq = violated_leq.get_violation(variables)
        assert violation_leq == Decimal('3'), f"LEQ violation should be 3, got {violation_leq}"
        
        # Slack LEQ (négatif car violé)
        slack_leq = violated_leq.get_slack(variables)
        assert slack_leq == Decimal('-3'), f"LEQ slack should be -3, got {slack_leq}"
        
        # Test violation GEQ : x1 + x2 ≥ 10
        # LHS = 5 + 3 = 8, bound = 10 → violation = 2
        violated_geq = LinearConstraint(
            coefficients={"x1": Decimal('1'), "x2": Decimal('1')},
            bound=Decimal('10'),
            constraint_type=ConstraintType.GEQ,
            name="violated_geq"
        )
        
        assert not violated_geq.is_satisfied(variables), "GEQ should be violated"
        violation_geq = violated_geq.get_violation(variables)
        assert violation_geq == Decimal('2'), f"GEQ violation should be 2, got {violation_geq}"
        
        # Surplus GEQ (négatif car violé)
        surplus_geq = violated_geq.get_slack(variables)
        assert surplus_geq == Decimal('-2'), f"GEQ surplus should be -2, got {surplus_geq}"
        
        # Test violation EQ : x1 = 7
        # LHS = 5, bound = 7 → violation = |5-7| = 2
        violated_eq = LinearConstraint(
            coefficients={"x1": Decimal('1')},
            bound=Decimal('7'),
            constraint_type=ConstraintType.EQ,
            name="violated_eq"
        )
        
        assert not violated_eq.is_satisfied(variables), "EQ should be violated"
        violation_eq = violated_eq.get_violation(variables)
        assert violation_eq == Decimal('2'), f"EQ violation should be 2, got {violation_eq}"

    def test_lp_problem_validation_comprehensive(self):
        """
        PROPRIÉTÉ 3: Validation Problème LP Complète
        Cohérence variables, contraintes, bounds avec détection erreurs
        """
        # Problème valide
        valid_lp = LinearProgram("valid_test")
        
        # Variables avec bounds
        x1 = valid_lp.add_variable("x1", lower_bound=Decimal('0'), upper_bound=Decimal('10'))
        x2 = valid_lp.add_variable("x2", lower_bound=Decimal('-1'))
        
        # Contrainte valide
        constraint = LinearConstraint(
            coefficients={"x1": Decimal('2'), "x2": Decimal('1')},
            bound=Decimal('5'),
            constraint_type=ConstraintType.LEQ,
            name="valid_constraint"
        )
        valid_lp.add_constraint(constraint)
        
        # Validation doit passer
        errors = valid_lp.validate_problem()
        assert len(errors) == 0, f"Valid problem should have no errors: {errors}"
        
        # Test problème invalide : variable manquante
        invalid_lp = LinearProgram("invalid_test")
        invalid_lp.add_variable("x1")
        
        # Contrainte référence variable inexistante
        invalid_constraint = LinearConstraint(
            coefficients={"x1": Decimal('1'), "x_missing": Decimal('1')},
            bound=Decimal('10'),
            constraint_type=ConstraintType.LEQ,
            name="invalid_constraint"
        )
        
        # add_constraint doit lever exception
        with pytest.raises(ValueError, match="not found"):
            invalid_lp.add_constraint(invalid_constraint)
        
        # Test problème sans variables
        empty_lp = LinearProgram("empty_test")
        empty_errors = empty_lp.validate_problem()
        assert any("no variables" in error.lower() for error in empty_errors), "Empty problem should be detected"
        
        # Test bounds violations
        bound_violating_lp = LinearProgram("bound_test")
        var = bound_violating_lp.add_variable("x", lower_bound=Decimal('5'), upper_bound=Decimal('10'))
        var.value = Decimal('15')  # Violation upper bound
        
        bound_errors = bound_violating_lp.validate_problem()
        assert any("violates bounds" in error for error in bound_errors), "Bound violation should be detected"

    def test_feasibility_testing_rigorous(self):
        """
        PROPRIÉTÉ 4: Test Faisabilité Rigoureux
        Validation faisabilité avec tolerances numériques
        """
        # Construction problème faisable
        feasible_lp = LinearProgram("feasible_test")
        feasible_lp.add_variable("x1", lower_bound=Decimal('0'))
        feasible_lp.add_variable("x2", lower_bound=Decimal('0'))
        
        # Contraintes faisables
        constraint1 = LinearConstraint(
            coefficients={"x1": Decimal('1'), "x2": Decimal('1')},
            bound=Decimal('10'),
            constraint_type=ConstraintType.LEQ
        )
        constraint2 = LinearConstraint(
            coefficients={"x1": Decimal('2'), "x2": Decimal('1')},
            bound=Decimal('8'),
            constraint_type=ConstraintType.GEQ
        )
        
        feasible_lp.add_constraint(constraint1)
        feasible_lp.add_constraint(constraint2)
        
        # Solution faisable : x1=4, x2=2
        # Vérification: 4+2=6≤10 ✓, 2*4+2=10≥8 ✓
        feasible_solution = {"x1": Decimal('4'), "x2": Decimal('2')}
        feasible_lp.set_variable_values(feasible_solution)
        
        assert feasible_lp.is_feasible(), "Problem should be feasible"
        
        violations = feasible_lp.get_constraint_violations()
        assert len(violations) == 0, f"Feasible solution should have no violations: {violations}"
        
        # Test solution infaisable
        infeasible_solution = {"x1": Decimal('1'), "x2": Decimal('1')}
        feasible_lp.set_variable_values(infeasible_solution)
        
        # Vérification: 1+1=2≤10 ✓, 2*1+1=3≥8 ✗ (violé)
        assert not feasible_lp.is_feasible(), "Solution should be infeasible"
        
        violations_infeasible = feasible_lp.get_constraint_violations()
        assert len(violations_infeasible) > 0, "Infeasible solution should have violations"
        
        # Test tolérance numérique
        tolerance_lp = LinearProgram("tolerance_test")
        tolerance_lp.add_variable("x")
        
        # x ≤ 5.0000000001 avec x = 5.000000001
        tight_constraint = LinearConstraint(
            coefficients={"x": Decimal('1')},
            bound=Decimal('5.0000000001'),
            constraint_type=ConstraintType.LEQ,
            tolerance=Decimal('1e-8')  # Tolérance large
        )
        tolerance_lp.add_constraint(tight_constraint)
        tolerance_lp.set_variable_values({"x": Decimal('5.000000001')})
        
        # Devrait être faisable avec tolérance
        assert tolerance_lp.is_feasible(tolerance=Decimal('1e-8')), "Should be feasible with tolerance"

    def test_constraint_matrix_extraction(self):
        """
        PROPRIÉTÉ 5: Extraction Matrice Standard Form
        Génération matrice A×b pour solveurs Simplex
        """
        matrix_lp = LinearProgram("matrix_test")
        
        # Variables : x1, x2, x3
        matrix_lp.add_variable("x1")
        matrix_lp.add_variable("x2") 
        matrix_lp.add_variable("x3")
        
        # Contraintes :
        # 2*x1 + x2 + 0*x3 ≤ 10
        # x1 + 0*x2 + x3 ≥ 5
        # 0*x1 + x2 + x3 = 3
        
        constraint1 = LinearConstraint(
            coefficients={"x1": Decimal('2'), "x2": Decimal('1')},
            bound=Decimal('10'),
            constraint_type=ConstraintType.LEQ,
            name="c1"
        )
        
        constraint2 = LinearConstraint(
            coefficients={"x1": Decimal('1'), "x3": Decimal('1')},
            bound=Decimal('5'),
            constraint_type=ConstraintType.GEQ,
            name="c2"
        )
        
        constraint3 = LinearConstraint(
            coefficients={"x2": Decimal('1'), "x3": Decimal('1')},
            bound=Decimal('3'),
            constraint_type=ConstraintType.EQ,
            name="c3"
        )
        
        matrix_lp.add_constraint(constraint1)
        matrix_lp.add_constraint(constraint2)
        matrix_lp.add_constraint(constraint3)
        
        # Extraction matrice
        A_matrix, b_vector, variable_order = matrix_lp.get_constraint_matrix()
        
        # Vérification dimensions
        assert len(A_matrix) == 3, f"Matrix should have 3 rows, got {len(A_matrix)}"
        assert len(b_vector) == 3, f"Vector should have 3 elements, got {len(b_vector)}"
        assert len(variable_order) == 3, f"Variable order should have 3 elements, got {len(variable_order)}"
        
        # Variables triées alphabétiquement
        assert variable_order == ["x1", "x2", "x3"], f"Variable order incorrect: {variable_order}"
        
        # Vérification matrice A (ordre: x1, x2, x3)
        expected_A = [
            [Decimal('2'), Decimal('1'), Decimal('0')],  # constraint1
            [Decimal('1'), Decimal('0'), Decimal('1')],  # constraint2  
            [Decimal('0'), Decimal('1'), Decimal('1')]   # constraint3
        ]
        
        for i, row in enumerate(A_matrix):
            for j, coeff in enumerate(row):
                assert coeff == expected_A[i][j], f"A[{i}][{j}] should be {expected_A[i][j]}, got {coeff}"
        
        # Vérification vecteur b
        expected_b = [Decimal('10'), Decimal('5'), Decimal('3')]
        assert b_vector == expected_b, f"b vector should be {expected_b}, got {b_vector}"
        
        # Statistiques
        assert matrix_lp.stats['matrix_extractions'] == 1, "Matrix extraction count should be updated"

    def test_economic_constraint_builders(self):
        """
        PROPRIÉTÉ 6: Constructeurs Contraintes Économiques
        Validation build_source/target/secondary_constraint
        """
        # Simulation poids NFA états finaux
        nfa_weights = {
            "agriculture_state": Decimal('1.2'),
            "industry_state": Decimal('0.9'),
            "services_state": Decimal('1.1')
        }
        
        # Test contrainte source : Σ(f_i × w_i) ≤ V_acceptable
        acceptable_amount = Decimal('100')
        source_constraint = build_source_constraint(
            nfa_state_weights=nfa_weights,
            primary_regex_weight=Decimal('1.0'),  # Pas utilisé dans implémentation actuelle
            acceptable_value=acceptable_amount,
            constraint_name="source_economic"
        )
        
        assert source_constraint.constraint_type == ConstraintType.LEQ
        assert source_constraint.bound == acceptable_amount
        assert source_constraint.name == "source_economic"
        
        # Vérification coefficients
        expected_coeffs = nfa_weights
        assert source_constraint.coefficients == expected_coeffs
        
        # Test contrainte target : Σ(f_i × w_i) ≥ V_required
        required_amount = Decimal('50')
        target_constraint = build_target_constraint(
            nfa_state_weights=nfa_weights,
            primary_regex_weight=Decimal('1.0'),
            required_value=required_amount,
            constraint_name="target_economic"
        )
        
        assert target_constraint.constraint_type == ConstraintType.GEQ
        assert target_constraint.bound == required_amount
        assert target_constraint.name == "target_economic"
        assert target_constraint.coefficients == nfa_weights
        
        # Test contrainte secondaire : Σ(f_i × w_i) ≤ 0 (patterns interdits)
        carbon_weights = {
            "carbon_penalty_state": Decimal('-0.5')  # Pénalité négative
        }
        secondary_constraint = build_secondary_constraint(
            nfa_state_weights=carbon_weights,
            secondary_regex_weight=Decimal('-0.5'),
            constraint_name="carbon_penalty"
        )
        
        assert secondary_constraint.constraint_type == ConstraintType.LEQ
        assert secondary_constraint.bound == Decimal('0')
        assert secondary_constraint.name == "carbon_penalty"
        assert secondary_constraint.coefficients == carbon_weights
        
        # Test contrainte égalité
        equality_constraint = build_equality_constraint(
            nfa_state_weights={"balance_state": Decimal('1.0')},
            exact_value=Decimal('25'),
            constraint_name="exact_balance"
        )
        
        assert equality_constraint.constraint_type == ConstraintType.EQ
        assert equality_constraint.bound == Decimal('25')
        
        # Test validation cohérence économique
        coherence_valid = validate_economic_consistency(source_constraint, target_constraint)
        # Devrait être cohérent : même coefficients positifs, source LEQ, target GEQ
        # avec source.bound (100) > target.bound (50)
        assert coherence_valid, "Economic constraints should be coherent"

    def test_decimal_precision_guarantees(self):
        """
        PROPRIÉTÉ 7: Précision Decimal Garantie
        Évitement erreurs floating-point avec calculs exacts
        """
        precision_lp = LinearProgram("precision_test")
        
        # Variables avec valeurs précises Decimal
        precision_lp.add_variable("x1")
        precision_lp.add_variable("x2")
        
        # Contrainte avec coefficients précis
        precise_constraint = LinearConstraint(
            coefficients={
                "x1": Decimal('0.1'),  # 1/10 exact
                "x2": Decimal('0.2')   # 2/10 exact  
            },
            bound=Decimal('0.3'),  # 3/10 exact
            constraint_type=ConstraintType.EQ,
            tolerance=Decimal('0')  # Tolérance nulle pour test précision
        )
        precision_lp.add_constraint(precise_constraint)
        
        # Solution exacte : x1=1, x2=1 → 0.1*1 + 0.2*1 = 0.3 exactement
        exact_solution = {"x1": Decimal('1'), "x2": Decimal('1')}
        
        # Évaluation doit être exactement 0.3
        lhs_exact = precise_constraint.evaluate(exact_solution)
        assert lhs_exact == Decimal('0.3'), f"Exact evaluation should be 0.3, got {lhs_exact}"
        
        # Satisfaction avec tolérance 0
        assert precise_constraint.is_satisfied(exact_solution), "Exact solution should satisfy with 0 tolerance"
        
        # Test calculs répétés (accumulation erreurs impossible avec Decimal)
        accumulated = Decimal('0')
        for _ in range(10):
            accumulated += Decimal('0.1')
        
        assert accumulated == Decimal('1.0'), f"Accumulated 10*0.1 should be exactly 1.0, got {accumulated}"
        
        # Comparaison avec float (démonstration problème)
        float_accumulated = 0.0
        for _ in range(10):
            float_accumulated += 0.1
        
        # float_accumulated ≈ 0.9999999999999999 (erreur floating-point)
        assert float_accumulated != 1.0, "Float accumulation should have rounding errors"
        
        # Decimal n'a pas ce problème
        decimal_accumulated = Decimal('0')
        for _ in range(100):
            decimal_accumulated += Decimal('0.01')
        assert decimal_accumulated == Decimal('1.00'), "Decimal precision maintained over many operations"

    def test_performance_construction_scalability(self):
        """
        PROPRIÉTÉ 8: Performance Construction Scalable
        Complexité acceptable pour problèmes LP moyens
        """
        variable_counts = [50, 100, 200]
        construction_times = []
        
        for n_vars in variable_counts:
            start_time = time.perf_counter()
            
            # Construction problème avec n variables
            perf_lp = LinearProgram(f"performance_test_{n_vars}")
            
            # Ajout variables
            for i in range(n_vars):
                perf_lp.add_variable(f"x{i}", lower_bound=Decimal('0'))
            
            # Ajout contraintes (n/2 contraintes)
            for i in range(n_vars // 2):
                coeffs = {
                    f"x{i}": Decimal('1'),
                    f"x{(i + 1) % n_vars}": Decimal('1')
                }
                constraint = LinearConstraint(
                    coefficients=coeffs,
                    bound=Decimal('10'),
                    constraint_type=ConstraintType.LEQ,
                    name=f"perf_constraint_{i}"
                )
                perf_lp.add_constraint(constraint)
            
            # Validation et extraction matrice
            errors = perf_lp.validate_problem()
            assert len(errors) == 0, f"Performance test problem should be valid: {errors}"
            
            A_matrix, b_vector, var_order = perf_lp.get_constraint_matrix()
            assert len(A_matrix) == n_vars // 2
            assert len(var_order) == n_vars
            
            end_time = time.perf_counter()
            construction_time = end_time - start_time
            construction_times.append(construction_time)
        
        # Vérification croissance sous-quadratique
        if len(construction_times) >= 2:
            time_ratio = construction_times[-1] / construction_times[0] 
            var_ratio = variable_counts[-1] / variable_counts[0]
            
            # Construction devrait être approximativement linéaire
            assert time_ratio < var_ratio * 2, f"Construction time growth too high: {time_ratio} vs variable ratio {var_ratio}"

    def test_comprehensive_lp_integration(self):
        """
        META-PROPRIÉTÉ: Intégration Complète LP
        Test end-to-end avec scénario économique réaliste
        """
        # Scénario : Transaction Alice (Agriculture) → Bob (Industry) 
        # avec contraintes carbone et équilibres
        integration_lp = LinearProgram("economic_integration")
        
        # Variables : flux par classification NFA
        integration_lp.add_variable("agri_flux", lower_bound=Decimal('0'))
        integration_lp.add_variable("indus_flux", lower_bound=Decimal('0'))
        integration_lp.add_variable("carbon_flux", lower_bound=Decimal('0'))
        
        # Simulation poids NFA depuis classifications
        agri_weights = {"agri_flux": Decimal('1.2')}  # Agriculture: coefficient 1.2
        indus_weights = {"indus_flux": Decimal('0.9')}  # Industry: coefficient 0.9
        carbon_weights = {"carbon_flux": Decimal('-0.3')}  # Carbon penalty: -0.3
        
        # Construction contraintes économiques
        source_constraint = build_source_constraint(
            nfa_state_weights=agri_weights,
            primary_regex_weight=Decimal('1.2'),
            acceptable_value=Decimal('1000'),  # Alice peut débiter max 1000
            constraint_name="alice_source"
        )
        
        target_constraint = build_target_constraint(
            nfa_state_weights=indus_weights,
            primary_regex_weight=Decimal('0.9'),
            required_value=Decimal('800'),  # Bob doit recevoir min 800
            constraint_name="bob_target"
        )
        
        carbon_constraint = build_secondary_constraint(
            nfa_state_weights=carbon_weights,
            secondary_regex_weight=Decimal('-0.3'),
            constraint_name="carbon_penalty"
        )
        
        # Ajout au problème
        integration_lp.add_constraint(source_constraint)
        integration_lp.add_constraint(target_constraint)
        integration_lp.add_constraint(carbon_constraint)
        
        # Validation structure problème
        validation_errors = integration_lp.validate_problem()
        assert len(validation_errors) == 0, f"Integration problem should be valid: {validation_errors}"
        
        # Test solution faisable
        # agri_flux = 800, indus_flux = 900, carbon_flux = 0
        # Source: 1.2 * 800 = 960 ≤ 1000 ✓
        # Target: 0.9 * 900 = 810 ≥ 800 ✓  
        # Carbon: -0.3 * 0 = 0 ≤ 0 ✓
        
        feasible_solution = {
            "agri_flux": Decimal('800'),
            "indus_flux": Decimal('900'),
            "carbon_flux": Decimal('0')
        }
        
        integration_lp.set_variable_values(feasible_solution)
        
        assert integration_lp.is_feasible(), "Integration solution should be feasible"
        
        # Vérification contraintes individuellement
        current_values = integration_lp.get_variable_values()
        
        assert source_constraint.is_satisfied(current_values), "Source constraint should be satisfied"
        assert target_constraint.is_satisfied(current_values), "Target constraint should be satisfied"  
        assert carbon_constraint.is_satisfied(current_values), "Carbon constraint should be satisfied"
        
        # Extraction pour solveur Simplex
        A_matrix, b_vector, variable_order = integration_lp.get_constraint_matrix()
        
        assert len(A_matrix) == 3, "Should have 3 constraints"
        assert len(variable_order) == 3, "Should have 3 variables"
        assert variable_order == ["agri_flux", "carbon_flux", "indus_flux"], "Variables should be sorted"
        
        # Test fonction objectif (si besoin)
        objective_coeffs = {"agri_flux": Decimal('1'), "indus_flux": Decimal('1')}
        objective_value = integration_lp.evaluate_objective(objective_coeffs)
        expected_objective = Decimal('800') + Decimal('900')
        assert objective_value == expected_objective, f"Objective should be {expected_objective}, got {objective_value}"


def run_academic_test_4():
    """
    Exécution test académique 4 avec rapport détaillé
    
    Returns:
        bool: True si toutes propriétés LP validées
    """
    pytest_result = pytest.main([
        __file__,
        "-v", 
        "--tb=short",
        "-x"  # Stop au premier échec
    ])
    
    return pytest_result == 0


if __name__ == "__main__":
    success = run_academic_test_4()
    if success:
        print("✅ TEST ACADÉMIQUE 4 RÉUSSI - Contraintes LP validées")
        print("📊 Propriétés mathématiques vérifiées:")
        print("   • Satisfaction contraintes LEQ/GEQ/EQ rigoureuse")
        print("   • Calcul violations et slack/surplus précis")
        print("   • Validation problème LP avec détection erreurs")
        print("   • Faisabilité solution avec tolerances numériques")
        print("   • Extraction matrice standard form A×b correcte")
        print("   • Constructeurs contraintes économiques fonctionnels")
        print("   • Précision Decimal garantie sans erreurs floating-point")
        print("   • Performance construction scalable (complexité sous-quadratique)")
        print("   • Intégration complète NFA-LP avec scénario économique")
    else:
        print("❌ TEST ACADÉMIQUE 4 ÉCHOUÉ - Violations propriétés LP détectées")
        exit(1)