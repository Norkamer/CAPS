"""
LinearProgram - Module de Programmation Linéaire ICGS

Implémentation complète système LP pour validation transactions économiques
avec garanties mathématiques absolues et précision Decimal.

Composants principaux:
- FluxVariable: Variables de flux avec bounds et état Simplex
- LinearConstraint: Contraintes linéaires avec types LEQ/GEQ/EQ
- LinearProgram: Problème LP complet avec matrice et validation
- Constructeurs: build_source/target/secondary_constraint pour économie

Propriétés mathématiques:
- Précision Decimal pour éviter erreurs floating-point
- Validation stricte cohérence problèmes LP
- Support bounds inférieurs/supérieurs variables
- Extraction matrice standard form pour solveurs

Architecture:
- Conçu pour TripleValidationOrientedSimplex
- Interface clean pour DAG transaction validation
- Extensible vers EnhancedLinearProgram (objectives)
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import copy


class ConstraintType(Enum):
    """Types de contraintes linéaires pour formulation LP standard"""
    LEQ = "LEQ"  # ≤ (Less or Equal)
    GEQ = "GEQ"  # ≥ (Greater or Equal)  
    EQ = "EQ"    # = (Equality)


@dataclass
class FluxVariable:
    """
    Variable flux représentant capacité classe équivalence NFA
    
    Propriétés:
    - variable_id: Identifiant unique (correspond state_id NFA)
    - value: Valeur actuelle variable (nombre de chemins f_i)
    - lower_bound: Borne inférieure (f_i ≥ 0 généralement)
    - upper_bound: Borne supérieure (None = unbounded)
    - is_basic: État dans base Simplex (True si basic)
    - metadata: Données additionnelles pour debugging
    """
    variable_id: str
    value: Decimal = Decimal('0')
    lower_bound: Decimal = Decimal('0')  
    upper_bound: Optional[Decimal] = None
    is_basic: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
            
        # Validation bornes cohérentes
        if self.upper_bound is not None and self.lower_bound > self.upper_bound:
            raise ValueError(f"Invalid bounds for variable {self.variable_id}: "
                           f"lower_bound {self.lower_bound} > upper_bound {self.upper_bound}")
    
    def is_feasible(self, tolerance: Decimal = Decimal('1e-10')) -> bool:
        """Teste si valeur actuelle respecte les bounds avec tolérance"""
        if self.value < self.lower_bound - tolerance:
            return False
        if self.upper_bound is not None and self.value > self.upper_bound + tolerance:
            return False
        return True
    
    def get_bound_violation(self) -> Decimal:
        """Retourne magnitude violation bounds (> 0 si violation)"""
        violation = Decimal('0')
        
        if self.value < self.lower_bound:
            violation = max(violation, self.lower_bound - self.value)
            
        if self.upper_bound is not None and self.value > self.upper_bound:
            violation = max(violation, self.value - self.upper_bound)
            
        return violation
    
    def project_to_bounds(self) -> None:
        """Projette valeur sur intervalle [lower_bound, upper_bound]"""
        self.value = max(self.value, self.lower_bound)
        if self.upper_bound is not None:
            self.value = min(self.value, self.upper_bound)


@dataclass  
class LinearConstraint:
    """
    Contrainte linéaire: Σ(coeff_i × var_i) {≤,≥,=} bound
    
    Propriétés:
    - coefficients: Mapping variable_id → coefficient
    - bound: Valeur RHS (Right Hand Side)
    - constraint_type: LEQ, GEQ, ou EQ
    - name: Nom descriptif pour debugging
    - tolerance: Tolérance satisfaction numérique
    """
    coefficients: Dict[str, Decimal]
    bound: Decimal
    constraint_type: ConstraintType
    name: Optional[str] = None
    tolerance: Decimal = Decimal('1e-10')
    
    def __post_init__(self):
        if not self.coefficients:
            raise ValueError("Constraint must have at least one coefficient")
            
        if self.name is None:
            self.name = f"constraint_{id(self)}"
    
    def evaluate(self, variables: Dict[str, Decimal]) -> Decimal:
        """
        Évalue LHS contrainte avec valeurs variables données
        
        Returns:
            Valeur LHS = Σ(coeff_i × var_i)
        """
        lhs_value = Decimal('0')
        
        for var_id, coeff in self.coefficients.items():
            if var_id in variables:
                lhs_value += coeff * variables[var_id]
            # Si variable non définie, considérée comme 0
                
        return lhs_value
    
    def is_satisfied(self, variables: Dict[str, Decimal]) -> bool:
        """
        Teste satisfaction contrainte avec tolérance
        
        Returns:
            True si contrainte satisfaite, False sinon
        """
        lhs_value = self.evaluate(variables)
        
        if self.constraint_type == ConstraintType.LEQ:
            return lhs_value <= self.bound + self.tolerance
        elif self.constraint_type == ConstraintType.GEQ:
            return lhs_value >= self.bound - self.tolerance  
        else:  # EQ
            return abs(lhs_value - self.bound) <= self.tolerance
    
    def get_violation(self, variables: Dict[str, Decimal]) -> Decimal:
        """
        Retourne magnitude violation (> 0 = violée)
        
        Returns:
            Montant violation, 0 si satisfaite
        """
        lhs_value = self.evaluate(variables)
        
        if self.constraint_type == ConstraintType.LEQ:
            return max(Decimal('0'), lhs_value - self.bound)
        elif self.constraint_type == ConstraintType.GEQ:
            return max(Decimal('0'), self.bound - lhs_value)
        else:  # EQ
            return abs(lhs_value - self.bound)
    
    def get_slack(self, variables: Dict[str, Decimal]) -> Decimal:
        """
        Retourne slack/surplus de la contrainte
        
        Returns:
            Slack pour LEQ, Surplus pour GEQ, écart absolu pour EQ
        """
        lhs_value = self.evaluate(variables)
        
        if self.constraint_type == ConstraintType.LEQ:
            return self.bound - lhs_value  # slack ≥ 0 si faisable
        elif self.constraint_type == ConstraintType.GEQ:
            return lhs_value - self.bound  # surplus ≥ 0 si faisable
        else:  # EQ
            return abs(self.bound - lhs_value)  # écart absolu


class LinearProgram:
    """
    Problème LP complet avec variables, contraintes, et métadonnées
    
    Architecture:
    - variables: Dict variable_id → FluxVariable
    - constraints: Liste LinearConstraint ordonnée
    - problem_name: Nom descriptif pour debugging
    - metadata: Données additionnelles (source, target measures, etc.)
    
    Fonctionnalités:
    - Construction incrémentale variables/contraintes
    - Validation cohérence problème
    - Extraction matrice standard form
    - Interface pour solveurs Simplex
    """
    
    def __init__(self, problem_name: str = "ICGS_LP"):
        self.variables: Dict[str, FluxVariable] = {}
        self.constraints: List[LinearConstraint] = []
        self.problem_name = problem_name
        self.metadata: Dict[str, Any] = {}
        
        # Statistiques construction
        self.stats = {
            'variables_added': 0,
            'constraints_added': 0,
            'validations_performed': 0,
            'matrix_extractions': 0
        }
    
    def add_variable(self, var_id: str, lower_bound: Decimal = Decimal('0'), 
                    upper_bound: Optional[Decimal] = None, 
                    initial_value: Decimal = Decimal('0')) -> FluxVariable:
        """
        Ajoute variable flux au problème
        
        Args:
            var_id: Identifiant unique variable
            lower_bound: Borne inférieure (défaut 0)
            upper_bound: Borne supérieure (défaut None = unbounded)
            initial_value: Valeur initiale
            
        Returns:
            FluxVariable créée
            
        Raises:
            ValueError: Si var_id déjà existe
        """
        if var_id in self.variables:
            raise ValueError(f"Variable {var_id} already exists in problem {self.problem_name}")
        
        variable = FluxVariable(
            variable_id=var_id,
            value=initial_value,
            lower_bound=lower_bound,
            upper_bound=upper_bound
        )
        
        self.variables[var_id] = variable
        self.stats['variables_added'] += 1
        
        return variable
    
    def add_constraint(self, constraint: LinearConstraint) -> None:
        """
        Ajoute contrainte avec validation variables référencées existent
        
        Args:
            constraint: LinearConstraint à ajouter
            
        Raises:
            ValueError: Si variables référencées n'existent pas
        """
        # Validation toutes variables existent
        for var_id in constraint.coefficients.keys():
            if var_id not in self.variables:
                raise ValueError(f"Variable {var_id} referenced in constraint "
                               f"{constraint.name} not found in problem {self.problem_name}")
        
        self.constraints.append(constraint)
        self.stats['constraints_added'] += 1
    
    def get_constraint_matrix(self) -> Tuple[List[List[Decimal]], List[Decimal], List[str]]:
        """
        Extraction matrice standard form pour Simplex: Ax {≤,≥,=} b
        
        Returns:
            Tuple (A_matrix, b_vector, variable_order)
            - A_matrix: Matrice coefficients [m×n]
            - b_vector: Vecteur RHS [m]
            - variable_order: Ordre variables dans colonnes
        """
        self.stats['matrix_extractions'] += 1
        
        if not self.constraints:
            return [], [], []
            
        # Ordre variables fixe pour cohérence
        variable_order = sorted(self.variables.keys())
        n_vars = len(variable_order)
        m_constraints = len(self.constraints)
        
        # Construction matrice A et vecteur b
        A_matrix = []
        b_vector = []
        
        for constraint in self.constraints:
            row = [Decimal('0')] * n_vars
            
            # Remplissage coefficients
            for var_id, coeff in constraint.coefficients.items():
                var_index = variable_order.index(var_id)
                row[var_index] = coeff
                
            A_matrix.append(row)
            b_vector.append(constraint.bound)
            
        return A_matrix, b_vector, variable_order
    
    def get_variable_values(self) -> Dict[str, Decimal]:
        """Retourne valeurs actuelles toutes variables"""
        return {var_id: var.value for var_id, var in self.variables.items()}
    
    def set_variable_values(self, values: Dict[str, Decimal]) -> None:
        """Met à jour valeurs variables avec validation bounds"""
        for var_id, value in values.items():
            if var_id in self.variables:
                self.variables[var_id].value = value
                # Projection automatique sur bounds si nécessaire
                self.variables[var_id].project_to_bounds()
    
    def validate_problem(self) -> List[str]:
        """
        Validation cohérence: variables définies, contraintes valides
        
        Returns:
            Liste erreurs détectées (vide si problème valide)
        """
        self.stats['validations_performed'] += 1
        errors = []
        
        # Validation variables
        if not self.variables:
            errors.append("Problem has no variables defined")
            
        for var_id, var in self.variables.items():
            if not var.is_feasible():
                errors.append(f"Variable {var_id} violates bounds: "
                             f"value={var.value}, bounds=[{var.lower_bound}, {var.upper_bound}]")
        
        # Validation contraintes
        if not self.constraints:
            errors.append("Problem has no constraints defined")
            
        for i, constraint in enumerate(self.constraints):
            # Variables référencées existent
            for var_id in constraint.coefficients.keys():
                if var_id not in self.variables:
                    errors.append(f"Constraint {i} ({constraint.name}) references "
                                 f"undefined variable {var_id}")
            
            # Coefficients non-zéro
            if all(coeff == Decimal('0') for coeff in constraint.coefficients.values()):
                errors.append(f"Constraint {i} ({constraint.name}) has all zero coefficients")
        
        return errors
    
    def evaluate_objective(self, coefficients: Dict[str, Decimal]) -> Decimal:
        """
        Évalue fonction objectif avec coefficients donnés
        
        Args:
            coefficients: variable_id → coefficient objectif
            
        Returns:
            Valeur fonction objectif
        """
        objective_value = Decimal('0')
        current_values = self.get_variable_values()
        
        for var_id, coeff in coefficients.items():
            if var_id in current_values:
                objective_value += coeff * current_values[var_id]
                
        return objective_value
    
    def is_feasible(self, tolerance: Decimal = Decimal('1e-10')) -> bool:
        """
        Teste faisabilité solution courante
        
        Returns:
            True si toutes contraintes et bounds satisfaites
        """
        current_values = self.get_variable_values()
        
        # Test bounds variables
        for var in self.variables.values():
            if not var.is_feasible(tolerance):
                return False
                
        # Test contraintes
        for constraint in self.constraints:
            if not constraint.is_satisfied(current_values):
                return False
                
        return True
    
    def get_constraint_violations(self) -> Dict[str, Decimal]:
        """
        Retourne violations toutes contraintes
        
        Returns:
            Dict constraint_name → magnitude violation
        """
        current_values = self.get_variable_values()
        violations = {}
        
        for constraint in self.constraints:
            violation = constraint.get_violation(current_values)
            if violation > Decimal('0'):
                violations[constraint.name] = violation
                
        return violations
    
    def __repr__(self) -> str:
        """Représentation string pour debugging"""
        return (f"LinearProgram(name='{self.problem_name}', "
                f"variables={len(self.variables)}, "
                f"constraints={len(self.constraints)}, "
                f"feasible={self.is_feasible()})")


# Constructeurs de Contraintes Économiques


def build_source_constraint(nfa_state_weights: Dict[str, Decimal], 
                           primary_regex_weight: Decimal,
                           acceptable_value: Decimal,
                           constraint_name: str = "source_primary") -> LinearConstraint:
    """
    Contrainte source primaire: Σ(f_i × weight_i) ≤ V_source_acceptable
    
    Interprétation économique:
    Montant maximum que le compte source peut débiter selon patterns NFA.
    Coefficients basés sur poids regex états finaux.
    
    Args:
        nfa_state_weights: state_id → poids regex associé
        primary_regex_weight: Poids principal pattern source  
        acceptable_value: Montant maximum acceptable (V_source)
        constraint_name: Nom descriptif contrainte
        
    Returns:
        LinearConstraint de type LEQ
    """
    if not nfa_state_weights:
        raise ValueError("nfa_state_weights cannot be empty")
        
    if acceptable_value < Decimal('0'):
        raise ValueError("acceptable_value must be non-negative")
    
    # Construction coefficients: f_i × weight_i
    coefficients = {}
    for state_id, weight in nfa_state_weights.items():
        # Coefficient = poids regex de l'état
        coefficients[state_id] = weight
    
    constraint = LinearConstraint(
        coefficients=coefficients,
        bound=acceptable_value,
        constraint_type=ConstraintType.LEQ,
        name=constraint_name
    )
    
    return constraint


def build_target_constraint(nfa_state_weights: Dict[str, Decimal],
                           primary_regex_weight: Decimal, 
                           required_value: Decimal,
                           constraint_name: str = "target_primary") -> LinearConstraint:
    """
    Contrainte cible primaire: Σ(f_i × weight_i) ≥ V_target_required
    
    Interprétation économique:
    Montant minimum que le compte cible doit recevoir selon patterns NFA.
    Coefficients basés sur poids regex états finaux.
    
    Args:
        nfa_state_weights: state_id → poids regex associé
        primary_regex_weight: Poids principal pattern cible
        required_value: Montant minimum requis (V_target)
        constraint_name: Nom descriptif contrainte
        
    Returns:
        LinearConstraint de type GEQ
    """
    if not nfa_state_weights:
        raise ValueError("nfa_state_weights cannot be empty")
        
    if required_value < Decimal('0'):
        raise ValueError("required_value must be non-negative")
    
    # Construction coefficients: f_i × weight_i  
    coefficients = {}
    for state_id, weight in nfa_state_weights.items():
        coefficients[state_id] = weight
    
    constraint = LinearConstraint(
        coefficients=coefficients,
        bound=required_value,
        constraint_type=ConstraintType.GEQ,
        name=constraint_name
    )
    
    return constraint


def build_secondary_constraint(nfa_state_weights: Dict[str, Decimal],
                              secondary_regex_weight: Decimal,
                              constraint_name: str = "secondary") -> LinearConstraint:
    """
    Contrainte secondaire: Σ(f_i × weight_i) ≤ 0
    
    Interprétation économique:
    Patterns interdits ou bonus négatifs (ex: pénalités carbone).
    Généralement bound=0 pour interdire activation.
    
    Args:
        nfa_state_weights: state_id → poids regex associé
        secondary_regex_weight: Poids pattern secondaire (souvent négatif)
        constraint_name: Nom descriptif contrainte
        
    Returns:
        LinearConstraint de type LEQ avec bound=0
    """
    if not nfa_state_weights:
        raise ValueError("nfa_state_weights cannot be empty")
    
    # Construction coefficients: f_i × weight_i
    coefficients = {}
    for state_id, weight in nfa_state_weights.items():
        coefficients[state_id] = weight
    
    constraint = LinearConstraint(
        coefficients=coefficients,
        bound=Decimal('0'),  # Pattern secondaire ≤ 0
        constraint_type=ConstraintType.LEQ,
        name=constraint_name
    )
    
    return constraint


def build_equality_constraint(nfa_state_weights: Dict[str, Decimal],
                             exact_value: Decimal,
                             constraint_name: str = "equality") -> LinearConstraint:
    """
    Contrainte d'égalité: Σ(f_i × weight_i) = exact_value
    
    Interprétation économique:
    Montant exact requis, sans tolérance. Utilisé pour contraintes
    de conservation ou équilibres stricts.
    
    Args:
        nfa_state_weights: state_id → poids regex associé
        exact_value: Valeur exacte requise
        constraint_name: Nom descriptif contrainte
        
    Returns:
        LinearConstraint de type EQ
    """
    if not nfa_state_weights:
        raise ValueError("nfa_state_weights cannot be empty")
    
    coefficients = {}
    for state_id, weight in nfa_state_weights.items():
        coefficients[state_id] = weight
    
    constraint = LinearConstraint(
        coefficients=coefficients,
        bound=exact_value,
        constraint_type=ConstraintType.EQ,
        name=constraint_name
    )
    
    return constraint


# Fonctions utilitaires


def create_simple_lp_problem() -> LinearProgram:
    """
    Crée problème LP simple pour tests unitaires
    
    Structure:
    Variables: x1, x2 ≥ 0
    Contraintes: 
    - x1 + x2 ≤ 10 (capacity)
    - 2*x1 + x2 ≥ 5 (minimum)
    """
    lp = LinearProgram("simple_test_lp")
    
    # Variables
    lp.add_variable("x1", lower_bound=Decimal('0'))
    lp.add_variable("x2", lower_bound=Decimal('0'))
    
    # Contraintes
    capacity_constraint = LinearConstraint(
        coefficients={"x1": Decimal('1'), "x2": Decimal('1')},
        bound=Decimal('10'),
        constraint_type=ConstraintType.LEQ,
        name="capacity"
    )
    
    minimum_constraint = LinearConstraint(
        coefficients={"x1": Decimal('2'), "x2": Decimal('1')},
        bound=Decimal('5'),
        constraint_type=ConstraintType.GEQ,
        name="minimum"
    )
    
    lp.add_constraint(capacity_constraint)
    lp.add_constraint(minimum_constraint)
    
    return lp


def validate_economic_consistency(source_constraint: LinearConstraint,
                                target_constraint: LinearConstraint,
                                tolerance: Decimal = Decimal('1e-8')) -> bool:
    """
    Valide cohérence économique contraintes source/target
    
    Vérifie que les poids sont cohérents et que le problème
    n'est pas trivialement infaisable.
    
    Returns:
        True si contraintes économiquement cohérentes
    """
    # Variables communes
    common_vars = set(source_constraint.coefficients.keys()) & set(target_constraint.coefficients.keys())
    
    if not common_vars:
        return False  # Aucune variable commune
    
    # Test cohérence directionnelle simple
    for var_id in common_vars:
        source_coeff = source_constraint.coefficients[var_id]
        target_coeff = target_constraint.coefficients[var_id]
        
        # Si même variable avec poids positifs dans source (LEQ) et target (GEQ)
        if (source_coeff > 0 and target_coeff > 0 and
            source_constraint.constraint_type == ConstraintType.LEQ and
            target_constraint.constraint_type == ConstraintType.GEQ):
            
            # Vérification compatibilité bounds basique
            if source_constraint.bound < target_constraint.bound:
                # Potentiellement infaisable si coefficients similaires
                coeff_ratio = abs(source_coeff - target_coeff)
                if coeff_ratio < tolerance:
                    return False
    
    return True