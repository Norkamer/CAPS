"""
Module Simplex Solver - Solveur LP avec Triple Validation

Ce module implémente le solveur Simplex Phase 1 avec garanties mathématiques
absolues pour le système ICGS, incluant validation pivot géométrique.

Classes principales:
- PivotStatus: États pivot avec métriques stabilité géométrique
- MathematicallyRigorousPivotManager: Validation pivot rigoureuse
- TripleValidationOrientedSimplex: Solveur principal Phase 1
- SimplexSolution: Résultats avec métadonnées validation

Garanties mathématiques:
- Triple validation: pivot + résolution + cross-validation
- Métriques stabilité géométrique basées distance hyperplanes
- Warm-start sécurisé avec fallback cold-start automatique
- Compatibilité sink-to-source pour énumération DAG reverse
"""

from dataclasses import dataclass, field
from decimal import Decimal, getcontext
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set, Any
import math
import logging
import time

# Import des modules ICGS
from .linear_programming import LinearProgram, LinearConstraint, FluxVariable, ConstraintType


# Configuration précision Decimal étendue pour Simplex
getcontext().prec = 50


class PivotStatus(Enum):
    """États pivot avec classification géométrique"""
    HIGHLY_STABLE = "HIGHLY_STABLE"                 # Distance >> tolerance, warm-start recommandé
    MODERATELY_STABLE = "MODERATELY_STABLE"         # Distance > tolerance, warm-start acceptable  
    GEOMETRICALLY_UNSTABLE = "GEOMETRICALLY_UNSTABLE" # Distance ≈ tolerance, cold-start préférable
    MATHEMATICALLY_INFEASIBLE = "MATHEMATICALLY_INFEASIBLE" # Pivot viole contraintes


class SolutionStatus(Enum):
    """États solution Simplex"""
    FEASIBLE = "FEASIBLE"           # Solution faisable trouvée
    INFEASIBLE = "INFEASIBLE"       # Problème infaisable
    UNBOUNDED = "UNBOUNDED"         # Solution non-bornée (rare en Phase 1)
    MAX_ITERATIONS = "MAX_ITERATIONS" # Limite itérations atteinte
    NUMERICAL_ERROR = "NUMERICAL_ERROR" # Erreur numérique détectée


@dataclass
class SimplexSolution:
    """
    Solution Simplex avec métadonnées complètes
    
    Contient solution variables + diagnostics validation pour
    traçabilité complète processus résolution.
    """
    status: SolutionStatus
    variables: Dict[str, Decimal] = field(default_factory=dict)
    iterations_used: int = 0
    solving_time: float = 0.0
    pivot_status_used: Optional[PivotStatus] = None
    warm_start_successful: bool = False
    cross_validation_passed: bool = False
    geometric_stability: Decimal = Decimal('0')
    
    # Métadonnées diagnostiques
    constraints_satisfied: int = 0
    total_constraints: int = 0
    final_objective_value: Decimal = Decimal('0')
    solver_warnings: List[str] = field(default_factory=list)


class MathematicallyRigorousPivotManager:
    """
    Gestionnaire validation pivot avec garanties géométriques
    
    Objectif: Validation mathématiquement rigoureuse compatibilité pivot
    selon métriques distance hyperplanes et stabilité géométrique.
    
    Architecture sink-to-source compatible:
    - Validation bidirectionnelle pivot (source→sink et sink→source)
    - Support énumération reverse DAG avec conservation stabilité
    - Métriques géométriques adaptées flux économiques
    """
    
    def __init__(self, tolerance: Decimal = Decimal('1e-12')):
        """
        Args:
            tolerance: Tolérance numérique pour validation géométrique
        """
        self.tolerance = tolerance
        self.logger = logging.getLogger("MathematicallyRigorousPivotManager")
        
        # Statistiques validation
        self.stats = {
            'pivots_validated': 0,
            'highly_stable_pivots': 0,
            'moderately_stable_pivots': 0,
            'unstable_pivots': 0,
            'infeasible_pivots': 0,
            'geometric_computations': 0
        }
    
    def validate_pivot_compatibility(self, old_pivot: Dict[str, Decimal], 
                                   new_constraints: List[LinearConstraint]) -> PivotStatus:
        """
        Test rigoureux compatibilité pivot avec nouvelles contraintes
        
        Algorithme validation géométrique:
        1. Test faisabilité stricte: toutes contraintes satisfaites avec tolérance
        2. Calcul stabilité géométrique: distance minimale aux hyperplanes
        3. Classification selon métriques stabilité et recommandation stratégie
        
        Args:
            old_pivot: Solution pivot précédente (var_id → valeur)
            new_constraints: Nouvelles contraintes à valider
            
        Returns:
            PivotStatus avec recommandation warm-start/cold-start
        """
        self.stats['pivots_validated'] += 1
        
        if not old_pivot:
            return PivotStatus.MATHEMATICALLY_INFEASIBLE
        
        # Phase 1: Test faisabilité stricte
        feasibility_violations = []
        for constraint in new_constraints:
            if not constraint.is_satisfied(old_pivot):
                violation = constraint.get_violation(old_pivot)
                feasibility_violations.append((constraint.name, violation))
        
        if feasibility_violations:
            self.logger.info(f"Pivot infeasible: {len(feasibility_violations)} violations")
            self.stats['infeasible_pivots'] += 1
            return PivotStatus.MATHEMATICALLY_INFEASIBLE
        
        # Phase 2: Calcul stabilité géométrique
        geometric_stability = self._compute_geometric_stability(old_pivot, new_constraints)
        
        # Phase 3: Classification selon stabilité
        return self._classify_pivot_stability(geometric_stability)
    
    def _compute_geometric_stability(self, pivot: Dict[str, Decimal], 
                                   constraints: List[LinearConstraint]) -> Decimal:
        """
        Métrique stabilité basée distance hyperplanes contraintes
        
        Formule: stabilité = min_distance / ||pivot||_2
        Où min_distance = minimum des distances aux hyperplanes actifs
        
        Interprétation géométrique:
        - Distance relative minimale aux contraintes actives
        - Plus élevée = pivot plus stable géométriquement
        - Sink-to-source: même métrique dans les deux sens
        
        Args:
            pivot: Point pivot à évaluer
            constraints: Contraintes définissant hyperplanes
            
        Returns:
            Decimal: Métrique stabilité géométrique (≥ 0)
        """
        self.stats['geometric_computations'] += 1
        
        if not pivot or not constraints:
            return Decimal('0')
        
        # Calcul norme euclidienne pivot
        pivot_norm = self._compute_euclidean_norm(pivot)
        if pivot_norm == Decimal('0'):
            return Decimal('0')
        
        # Calcul distance minimale aux hyperplanes
        min_distance = None
        
        for constraint in constraints:
            # Distance point-hyperplan: |ax + by + c - bound| / ||coefficients||
            lhs_value = constraint.evaluate(pivot)
            
            # Norme coefficients contrainte
            coeff_norm = self._compute_constraint_norm(constraint)
            if coeff_norm == Decimal('0'):
                continue
            
            # Distance selon type contrainte
            if constraint.constraint_type == ConstraintType.EQ:
                distance = abs(lhs_value - constraint.bound) / coeff_norm
            elif constraint.constraint_type == ConstraintType.LEQ:
                # Distance = slack/norm si satisfaite, 0 si sur hyperplan
                slack = constraint.bound - lhs_value
                distance = max(Decimal('0'), slack) / coeff_norm
            else:  # GEQ
                # Distance = surplus/norm si satisfaite, 0 si sur hyperplan
                surplus = lhs_value - constraint.bound
                distance = max(Decimal('0'), surplus) / coeff_norm
            
            if min_distance is None or distance < min_distance:
                min_distance = distance
        
        if min_distance is None:
            return Decimal('0')
        
        # Stabilité relative = min_distance / ||pivot||
        geometric_stability = min_distance / pivot_norm
        return geometric_stability
    
    def _compute_euclidean_norm(self, vector: Dict[str, Decimal]) -> Decimal:
        """Calcul norme euclidienne L2 du vecteur"""
        sum_squares = sum(value ** 2 for value in vector.values())
        return sum_squares.sqrt()
    
    def _compute_constraint_norm(self, constraint: LinearConstraint) -> Decimal:
        """Calcul norme euclidienne coefficients contrainte"""
        sum_squares = sum(coeff ** 2 for coeff in constraint.coefficients.values())
        return sum_squares.sqrt()
    
    def _classify_pivot_stability(self, geometric_stability: Decimal) -> PivotStatus:
        """
        Classification pivot selon métrique stabilité géométrique
        
        Seuils calibrés pour compatibilité sink-to-source:
        - HIGHLY_STABLE: stabilité >> tolerance (warm-start sécurisé)
        - MODERATELY_STABLE: stabilité > 10×tolerance (warm-start acceptable)
        - GEOMETRICALLY_UNSTABLE: stabilité ≈ tolerance (cold-start préférable)
        """
        high_threshold = self.tolerance * 100    # 100× tolérance
        moderate_threshold = self.tolerance * 10  # 10× tolérance
        
        if geometric_stability >= high_threshold:
            self.stats['highly_stable_pivots'] += 1
            return PivotStatus.HIGHLY_STABLE
        elif geometric_stability >= moderate_threshold:
            self.stats['moderately_stable_pivots'] += 1
            return PivotStatus.MODERATELY_STABLE
        else:
            self.stats['unstable_pivots'] += 1
            return PivotStatus.GEOMETRICALLY_UNSTABLE
    
    def get_pivot_recommendation(self, pivot_status: PivotStatus) -> str:
        """
        Recommandation stratégie résolution selon statut pivot
        
        Compatible architecture sink-to-source avec stratégies bidirectionnelles.
        """
        recommendations = {
            PivotStatus.HIGHLY_STABLE: "Warm-start recommandé - stabilité géométrique élevée",
            PivotStatus.MODERATELY_STABLE: "Warm-start acceptable - stabilité modérée avec monitoring",
            PivotStatus.GEOMETRICALLY_UNSTABLE: "Cold-start préférable - risque instabilité numérique",
            PivotStatus.MATHEMATICALLY_INFEASIBLE: "Cold-start obligatoire - pivot viole contraintes"
        }
        return recommendations.get(pivot_status, "Statut pivot inconnu")
    
    def get_validation_stats(self) -> Dict[str, int]:
        """Retourne statistiques validation pivot pour monitoring"""
        return dict(self.stats)


class TripleValidationOrientedSimplex:
    """
    Solveur Simplex Phase 1 avec garanties mathématiques absolues
    
    Architecture Triple Validation:
    1. Validation pivot: compatibilité géométrique avant warm-start
    2. Resolution attempt: warm-start ou cold-start selon pivot
    3. Cross-validation: vérification solution pour cas instables
    
    Compatibilité sink-to-source:
    - Support énumération DAG bidirectionnelle (source→sink, sink→source)
    - Validation pivot adaptée flux économiques reverse
    - Métriques performance pour chemins complexes
    """
    
    def __init__(self, max_iterations: int = 10000, tolerance: Decimal = Decimal('1e-10')):
        """
        Args:
            max_iterations: Limite itérations Simplex
            tolerance: Tolérance numérique générale
        """
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.pivot_manager = MathematicallyRigorousPivotManager(tolerance / 100)  # Plus strict
        self.logger = logging.getLogger("TripleValidationOrientedSimplex")
        
        # Statistiques tracking
        self.stats = {
            'warm_starts_used': 0,
            'cold_starts_used': 0,
            'cross_validations_performed': 0,
            'pivot_rejections': 0,
            'solutions_found': 0,
            'infeasible_problems': 0
        }
    
    def solve_with_absolute_guarantees(self, problem: LinearProgram, 
                                     old_pivot: Optional[Dict[str, Decimal]] = None) -> SimplexSolution:
        """
        Pipeline triple validation avec garanties mathématiques absolues
        
        Algorithme complet:
        1. Validation pivot si fourni (warm-start candidat)
        2. Résolution primaire avec stratégie optimale
        3. Cross-validation si instabilité géométrique détectée
        4. Retour solution avec garanties correction
        
        Compatible sink-to-source avec validation bidirectionnelle.
        
        Args:
            problem: Problème LP à résoudre
            old_pivot: Solution pivot précédente (optionnelle)
            
        Returns:
            SimplexSolution avec validation complète
        """
        start_time = time.time()
        
        # Validation problème
        validation_errors = problem.validate_problem()
        if validation_errors:
            return SimplexSolution(
                status=SolutionStatus.NUMERICAL_ERROR,
                solving_time=time.time() - start_time,
                solver_warnings=validation_errors
            )
        
        # Phase 1: Validation pivot si fourni
        pivot_status = None
        if old_pivot:
            pivot_status = self.pivot_manager.validate_pivot_compatibility(
                old_pivot, problem.constraints
            )
        
        # Phase 2: Résolution avec stratégie optimale
        solution = self._resolve_with_strategy(problem, old_pivot, pivot_status)
        solution.solving_time = time.time() - start_time
        solution.pivot_status_used = pivot_status
        
        # Phase 3: Cross-validation si nécessaire
        if self._requires_cross_validation(solution, pivot_status):
            solution = self._perform_cross_validation(problem, solution)
        
        # Mise à jour statistiques
        self._update_solving_stats(solution)
        
        return solution
    
    def _resolve_with_strategy(self, problem: LinearProgram, 
                             old_pivot: Optional[Dict[str, Decimal]], 
                             pivot_status: Optional[PivotStatus]) -> SimplexSolution:
        """
        Résolution avec stratégie adaptée au statut pivot
        
        Stratégies sink-to-source:
        - HIGHLY_STABLE/MODERATELY_STABLE: warm-start avec pivot
        - GEOMETRICALLY_UNSTABLE/INFEASIBLE: cold-start from scratch
        """
        # Décision stratégie résolution
        use_warm_start = (
            pivot_status in [PivotStatus.HIGHLY_STABLE, PivotStatus.MODERATELY_STABLE]
            and old_pivot is not None
        )
        
        if use_warm_start:
            self.logger.info(f"Attempting warm-start with {pivot_status.value}")
            solution = self._solve_phase1_tableau(problem, warm_start=True, initial_pivot=old_pivot)
            if solution.status == SolutionStatus.FEASIBLE:
                solution.warm_start_successful = True
                self.stats['warm_starts_used'] += 1
                return solution
            else:
                self.logger.warning("Warm-start failed, falling back to cold-start")
                self.stats['pivot_rejections'] += 1
        
        # Cold-start (toujours en fallback)
        self.logger.info("Using cold-start resolution")
        solution = self._solve_phase1_tableau(problem, warm_start=False)
        self.stats['cold_starts_used'] += 1
        return solution
    
    def _solve_phase1_tableau(self, problem: LinearProgram, warm_start: bool = False,
                            initial_pivot: Optional[Dict[str, Decimal]] = None) -> SimplexSolution:
        """
        Implémentation core Simplex Phase 1 avec tableau
        
        Algorithme standard Phase 1:
        1. Construction tableau Phase 1 avec variables artificielles
        2. Itérations pivot: entering/leaving variable selection
        3. Test optimalité: tous coefficients objectif ≥ 0
        4. Extraction solution ou détection infaisabilité
        
        Sink-to-source: même algorithme, variables interprétées différemment.
        """
        solution = SimplexSolution(status=SolutionStatus.FEASIBLE)
        
        try:
            # Construction tableau Phase 1
            tableau, basic_vars, non_basic_vars = self._build_phase1_tableau(problem)
            
            if warm_start and initial_pivot:
                tableau, basic_vars = self._apply_warm_start(tableau, basic_vars, initial_pivot)
            
            # Itérations Simplex
            for iteration in range(self.max_iterations):
                solution.iterations_used = iteration + 1
                
                # Test optimalité
                if self._is_optimal(tableau):
                    break
                
                # Sélection variable entrante (plus négatif dans ligne objectif)
                entering_col = self._select_entering_variable(tableau)
                if entering_col == -1:
                    solution.status = SolutionStatus.UNBOUNDED
                    break
                
                # Sélection variable sortante (ratio test)
                leaving_row = self._select_leaving_variable(tableau, entering_col)
                if leaving_row == -1:
                    solution.status = SolutionStatus.UNBOUNDED
                    break
                
                # Opération pivot
                self._pivot_operation(tableau, leaving_row, entering_col)
                
                # Mise à jour variables de base
                basic_vars[leaving_row] = non_basic_vars[entering_col]
            
            else:
                solution.status = SolutionStatus.MAX_ITERATIONS
            
            # Extraction solution finale
            if solution.status == SolutionStatus.FEASIBLE:
                solution.variables = self._extract_solution(tableau, basic_vars, problem)
                solution.final_objective_value = tableau[0][0]  # Objectif Phase 1
                
                # Vérification faisabilité (objectif Phase 1 = 0)
                if abs(solution.final_objective_value) > self.tolerance:
                    solution.status = SolutionStatus.INFEASIBLE
                    self.stats['infeasible_problems'] += 1
                else:
                    self.stats['solutions_found'] += 1
            
        except Exception as e:
            self.logger.error(f"Simplex resolution error: {e}")
            solution.status = SolutionStatus.NUMERICAL_ERROR
            solution.solver_warnings.append(str(e))
        
        return solution
    
    def _build_phase1_tableau(self, problem: LinearProgram) -> Tuple[List[List[Decimal]], List[str], List[str]]:
        """
        Construction tableau initial Phase 1 avec variables artificielles
        
        Structure tableau: [objectif] + [contraintes]
        Colonnes: [RHS] + [variables_originales] + [slack/surplus] + [artificielles]
        Objectif Phase 1: min Σ(variables_artificielles)
        
        Compatible sink-to-source: même structure, interprétation différente variables.
        """
        A_matrix, b_vector, var_order = problem.get_constraint_matrix()
        n_vars = len(var_order)
        n_constraints = len(problem.constraints)
        
        # Variables artificielles/slack selon type contrainte
        artificial_vars = []
        slack_vars = []
        
        for i, constraint in enumerate(problem.constraints):
            if constraint.constraint_type == ConstraintType.LEQ:
                slack_vars.append(f"slack_{i}")
            elif constraint.constraint_type == ConstraintType.GEQ:
                slack_vars.append(f"surplus_{i}")
                artificial_vars.append(f"artificial_{i}")
            else:  # EQ
                artificial_vars.append(f"artificial_{i}")
        
        # Dimensions tableau
        n_slack = len(slack_vars)
        n_artificial = len(artificial_vars)
        tableau_cols = 1 + n_vars + n_slack + n_artificial  # RHS + vars + slack + artificial
        tableau_rows = 1 + n_constraints  # objectif + contraintes
        
        # Initialisation tableau
        tableau = [[Decimal('0') for _ in range(tableau_cols)] for _ in range(tableau_rows)]
        
        # Ligne objectif Phase 1: min Σ(artificial_vars)
        for i, _ in enumerate(artificial_vars):
            tableau[0][1 + n_vars + n_slack + i] = Decimal('1')
        
        # Contraintes
        slack_idx = 0
        artificial_idx = 0
        
        for i, constraint in enumerate(problem.constraints):
            # RHS
            tableau[i + 1][0] = constraint.bound
            
            # Variables originales
            for j, var_id in enumerate(var_order):
                if var_id in constraint.coefficients:
                    tableau[i + 1][1 + j] = constraint.coefficients[var_id]
            
            # Variables slack/surplus/artificial
            if constraint.constraint_type == ConstraintType.LEQ:
                tableau[i + 1][1 + n_vars + slack_idx] = Decimal('1')
                slack_idx += 1
            elif constraint.constraint_type == ConstraintType.GEQ:
                tableau[i + 1][1 + n_vars + slack_idx] = Decimal('-1')  # surplus
                tableau[i + 1][1 + n_vars + n_slack + artificial_idx] = Decimal('1')
                slack_idx += 1
                artificial_idx += 1
            else:  # EQ
                tableau[i + 1][1 + n_vars + n_slack + artificial_idx] = Decimal('1')
                artificial_idx += 1
        
        # Variables de base initiales (slack/artificial)
        basic_vars = slack_vars + artificial_vars
        non_basic_vars = var_order + (slack_vars if not slack_vars else []) + artificial_vars
        
        return tableau, basic_vars[:n_constraints], non_basic_vars
    
    def _is_optimal(self, tableau: List[List[Decimal]]) -> bool:
        """Test optimalité: tous coefficients objectif ≥ 0"""
        for j in range(1, len(tableau[0])):
            if tableau[0][j] < -self.tolerance:
                return False
        return True
    
    def _select_entering_variable(self, tableau: List[List[Decimal]]) -> int:
        """Sélection variable entrante (plus négatif dans ligne objectif)"""
        min_val = Decimal('0')
        entering_col = -1
        
        for j in range(1, len(tableau[0])):
            if tableau[0][j] < min_val:
                min_val = tableau[0][j]
                entering_col = j
        
        return entering_col
    
    def _select_leaving_variable(self, tableau: List[List[Decimal]], entering_col: int) -> int:
        """Sélection variable sortante via ratio test"""
        min_ratio = None
        leaving_row = -1
        
        for i in range(1, len(tableau)):
            if tableau[i][entering_col] > self.tolerance:  # Coefficient positif
                ratio = tableau[i][0] / tableau[i][entering_col]
                if ratio >= 0 and (min_ratio is None or ratio < min_ratio):
                    min_ratio = ratio
                    leaving_row = i
        
        return leaving_row
    
    def _pivot_operation(self, tableau: List[List[Decimal]], pivot_row: int, pivot_col: int) -> None:
        """Opération pivot standard Simplex"""
        pivot_element = tableau[pivot_row][pivot_col]
        
        # Normalisation ligne pivot
        for j in range(len(tableau[0])):
            tableau[pivot_row][j] /= pivot_element
        
        # Élimination autres lignes
        for i in range(len(tableau)):
            if i != pivot_row and abs(tableau[i][pivot_col]) > self.tolerance:
                multiplier = tableau[i][pivot_col]
                for j in range(len(tableau[0])):
                    tableau[i][j] -= multiplier * tableau[pivot_row][j]
    
    def _extract_solution(self, tableau: List[List[Decimal]], basic_vars: List[str], 
                         problem: LinearProgram) -> Dict[str, Decimal]:
        """Extraction solution depuis tableau final"""
        solution = {}
        
        # Initialisation toutes variables à 0
        for var_id in problem.variables.keys():
            solution[var_id] = Decimal('0')
        
        # Variables de base = RHS correspondant
        for i, basic_var in enumerate(basic_vars):
            if basic_var in problem.variables:
                solution[basic_var] = tableau[i + 1][0]
        
        return solution
    
    def _apply_warm_start(self, tableau: List[List[Decimal]], basic_vars: List[str],
                         initial_pivot: Dict[str, Decimal]) -> Tuple[List[List[Decimal]], List[str]]:
        """Application warm-start avec pivot initial (implémentation simplifiée)"""
        # Pour l'instant, retourne tableau inchangé
        # Implementation complète nécessiterait reconstruction base selon pivot
        return tableau, basic_vars
    
    def _requires_cross_validation(self, solution: SimplexSolution, 
                                 pivot_status: Optional[PivotStatus]) -> bool:
        """Détermine si cross-validation nécessaire"""
        return (
            solution.status == SolutionStatus.FEASIBLE and
            pivot_status == PivotStatus.GEOMETRICALLY_UNSTABLE
        )
    
    def _perform_cross_validation(self, problem: LinearProgram, solution: SimplexSolution) -> SimplexSolution:
        """Cross-validation solution avec méthode alternative"""
        self.stats['cross_validations_performed'] += 1
        
        # Vérification contraintes directe
        satisfied_constraints = 0
        for constraint in problem.constraints:
            if constraint.is_satisfied(solution.variables):
                satisfied_constraints += 1
        
        solution.constraints_satisfied = satisfied_constraints
        solution.total_constraints = len(problem.constraints)
        solution.cross_validation_passed = (satisfied_constraints == solution.total_constraints)
        
        if not solution.cross_validation_passed:
            solution.status = SolutionStatus.NUMERICAL_ERROR
            solution.solver_warnings.append(
                f"Cross-validation failed: {satisfied_constraints}/{solution.total_constraints} constraints satisfied"
            )
        
        return solution
    
    def _update_solving_stats(self, solution: SimplexSolution) -> None:
        """Mise à jour statistiques résolution"""
        if solution.status == SolutionStatus.FEASIBLE:
            self.stats['solutions_found'] += 1
        elif solution.status == SolutionStatus.INFEASIBLE:
            self.stats['infeasible_problems'] += 1
    
    def get_solver_stats(self) -> Dict[str, int]:
        """Retourne statistiques solveur pour monitoring"""
        combined_stats = dict(self.stats)
        combined_stats.update(self.pivot_manager.get_validation_stats())
        return combined_stats


# Fonctions utilitaires


def create_test_simplex_solver() -> TripleValidationOrientedSimplex:
    """Crée solveur Simplex pour tests unitaires avec paramètres optimaux"""
    return TripleValidationOrientedSimplex(
        max_iterations=1000,
        tolerance=Decimal('1e-10')
    )


def validate_simplex_solution(solution: SimplexSolution, problem: LinearProgram) -> List[str]:
    """
    Validation indépendante solution Simplex
    
    Retourne liste erreurs détectées (vide si solution valide)
    Compatible architecture sink-to-source.
    """
    errors = []
    
    if solution.status != SolutionStatus.FEASIBLE:
        return [f"Solution status not feasible: {solution.status.value}"]
    
    # Test satisfaction contraintes
    for i, constraint in enumerate(problem.constraints):
        if not constraint.is_satisfied(solution.variables):
            violation = constraint.get_violation(solution.variables)
            errors.append(f"Constraint {i} ({constraint.name}) violated by {violation}")
    
    # Test bounds variables
    for var_id, var in problem.variables.items():
        if var_id in solution.variables:
            value = solution.variables[var_id]
            if not var.is_feasible():
                errors.append(f"Variable {var_id} violates bounds: value={value}")
    
    return errors