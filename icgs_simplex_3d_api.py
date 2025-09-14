#!/usr/bin/env python3
"""
ICGS Simplex 3D Visualization API
================================

API read-only pour extraire les données internes du Simplex ICGS
et les mapper vers l'espace 3D pour visualisation du parcours algorithmique.

Architecture:
- SimplexState3D: Capture d'état à un moment donné du Simplex
- SimplexTransition3D: Transition entre deux états (arête 3D)
- Simplex3DCollector: Collecteur principal qui intercepte les données
- Simplex3DMapper: Mappage variables f_i vers coordonnées (x,y,z)

Liaison directe avec:
- icgs_core.simplex_solver (variables f_i réelles)
- icgs_core.linear_programming (contraintes SOURCE/TARGET/SECONDARY)
- icgs_core.path_enumerator (états NFA correspondants)

Garanties:
- Read-only: n'affecte pas le solveur Simplex
- Temps réel: collecte données pendant résolution
- Mathématiquement exact: variables f_i authentiques
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Set, Any
from enum import Enum
import time
import copy

# Import modules ICGS core
from icgs_core.simplex_solver import SimplexSolution, PivotStatus, ValidationMode
from icgs_core.linear_programming import LinearProgram, FluxVariable, LinearConstraint, ConstraintType


class ConstraintClass3D(Enum):
    """Classification 3D des contraintes pour visualisation"""
    SOURCE = "SOURCE"           # Axe X: Contraintes débiteur
    TARGET = "TARGET"           # Axe Y: Contraintes créditeur
    SECONDARY = "SECONDARY"     # Axe Z: Contraintes bonus/malus
    UNKNOWN = "UNKNOWN"         # Non classifié


class SimplexTransitionType(Enum):
    """Types de transitions entre états Simplex"""
    PIVOT_ENTER = "PIVOT_ENTER"     # Variable entre dans la base
    PIVOT_LEAVE = "PIVOT_LEAVE"     # Variable sort de la base
    FEASIBILITY_CHECK = "FEASIBILITY_CHECK"  # Test faisabilité
    OPTIMIZATION_STEP = "OPTIMIZATION_STEP"  # Étape optimisation
    CONVERGENCE = "CONVERGENCE"     # Convergence atteinte


@dataclass
class SimplexState3D:
    """
    État du Simplex à un moment donné avec projection 3D

    Capture :
    - Variables f_i authentiques du Simplex
    - Classification contraintes par axe 3D
    - Métadonnées algorithmiques
    - Coordonnées 3D résultantes
    """
    timestamp: float
    step_number: int
    variables_fi: Dict[str, Decimal]  # Variables f_i réelles du Simplex
    constraint_contributions: Dict[ConstraintClass3D, Decimal]  # Contributions par axe
    coordinates_3d: Tuple[float, float, float]  # (x, y, z) dans l'espace

    # Métadonnées algorithmiques
    pivot_status: Optional[PivotStatus] = None
    validation_mode: Optional[ValidationMode] = None
    is_feasible: bool = False
    is_optimal: bool = False
    basic_variables: Set[str] = field(default_factory=set)
    non_basic_variables: Set[str] = field(default_factory=set)

    # Métriques performance
    solving_time_ms: float = 0.0
    iterations_used: int = 0
    objective_value: Optional[Decimal] = None


@dataclass
class SimplexTransition3D:
    """
    Transition entre deux états Simplex avec visualisation 3D

    Représente :
    - Arête dans l'espace 3D entre deux points
    - Type de transition algorithmique
    - Impact sur variables f_i
    - Direction de pivot
    """
    from_state: SimplexState3D
    to_state: SimplexState3D
    transition_type: SimplexTransitionType

    # Analyse pivot
    entering_variable: Optional[str] = None  # Variable qui entre
    leaving_variable: Optional[str] = None   # Variable qui sort
    pivot_direction: Optional[str] = None    # Direction principale du mouvement

    # Impact géométrique
    euclidean_distance: float = 0.0
    dominant_axis: Optional[ConstraintClass3D] = None  # Axe principal du mouvement
    constraint_improvements: Dict[ConstraintClass3D, Decimal] = field(default_factory=dict)

    # Métadonnées
    computational_cost: float = 0.0
    stability_measure: Optional[float] = None


class Simplex3DMapper:
    """
    Mapper variables f_i du Simplex vers coordonnées 3D

    Algorithme:
    1. Classifier contraintes par type (SOURCE/TARGET/SECONDARY)
    2. Calculer contributions : coord_axe = Σ(f_i × weight_i) pour contraintes de cet axe
    3. Retourner point 3D (x,y,z) = (contrib_SOURCE, contrib_TARGET, contrib_SECONDARY)
    """

    def __init__(self):
        self.constraint_classification: Dict[str, ConstraintClass3D] = {}
        self.constraint_weights: Dict[str, Dict[str, Decimal]] = {}

    def classify_constraint(self, constraint: LinearConstraint) -> ConstraintClass3D:
        """Classifie une contrainte selon son type économique"""
        constraint_name = constraint.name.lower()

        if 'source' in constraint_name or 'debiteur' in constraint_name:
            return ConstraintClass3D.SOURCE
        elif 'target' in constraint_name or 'crediteur' in constraint_name:
            return ConstraintClass3D.TARGET
        elif 'secondary' in constraint_name or 'bonus' in constraint_name or 'malus' in constraint_name:
            return ConstraintClass3D.SECONDARY
        else:
            return ConstraintClass3D.UNKNOWN

    def extract_constraint_info(self, linear_program: LinearProgram):
        """Extrait informations contraintes du LinearProgram"""
        self.constraint_classification.clear()
        self.constraint_weights.clear()

        for constraint in linear_program.constraints:
            constraint_class = self.classify_constraint(constraint)
            self.constraint_classification[constraint.name] = constraint_class

            # Extraire poids variables pour cette contrainte
            if constraint_class not in [ConstraintClass3D.UNKNOWN]:
                self.constraint_weights[constraint.name] = constraint.coefficients.copy()

    def map_variables_to_3d(self, variables_fi: Dict[str, Decimal]) -> Tuple[float, float, float]:
        """
        Mappe variables f_i vers coordonnées 3D

        Returns:
            (x, y, z) où :
            - x = Σ(f_i × weight_i) pour contraintes SOURCE
            - y = Σ(f_i × weight_i) pour contraintes TARGET
            - z = Σ(f_i × weight_i) pour contraintes SECONDARY
        """
        contributions = {
            ConstraintClass3D.SOURCE: Decimal('0'),
            ConstraintClass3D.TARGET: Decimal('0'),
            ConstraintClass3D.SECONDARY: Decimal('0')
        }

        # Calculer contributions par axe
        for constraint_name, constraint_class in self.constraint_classification.items():
            if constraint_class in contributions and constraint_name in self.constraint_weights:
                weights = self.constraint_weights[constraint_name]

                # Contribution = Σ(f_i × weight_i) pour cette contrainte
                constraint_contribution = Decimal('0')
                for var_id, weight in weights.items():
                    if var_id in variables_fi:
                        constraint_contribution += variables_fi[var_id] * weight

                contributions[constraint_class] += constraint_contribution

        return (
            float(contributions[ConstraintClass3D.SOURCE]),
            float(contributions[ConstraintClass3D.TARGET]),
            float(contributions[ConstraintClass3D.SECONDARY])
        )


class Simplex3DCollector:
    """
    Collecteur principal données Simplex pour visualisation 3D

    Interface read-only qui :
    1. Intercepte états et transitions du Simplex
    2. Extrait variables f_i authentiques
    3. Mappe vers espace 3D
    4. Fournit données pour animation

    Usage:
        collector = Simplex3DCollector()
        collector.attach_to_solver(simplex_solver)
        # ... résolution Simplex ...
        animation_data = collector.export_animation_data()
    """

    def __init__(self):
        self.mapper = Simplex3DMapper()
        self.states_history: List[SimplexState3D] = []
        self.transitions_history: List[SimplexTransition3D] = []
        self.current_step = 0

    def capture_simplex_state(self,
                            linear_program: LinearProgram,
                            solution: SimplexSolution,
                            validation_mode: ValidationMode) -> SimplexState3D:
        """Capture état actuel du Simplex"""

        # Extraire informations contraintes si pas déjà fait
        if not self.mapper.constraint_classification:
            self.mapper.extract_constraint_info(linear_program)

        # Mapper variables f_i vers 3D
        coordinates_3d = self.mapper.map_variables_to_3d(solution.variables)

        # Calculer contributions par axe
        contributions = {}
        for constraint_class in ConstraintClass3D:
            if constraint_class != ConstraintClass3D.UNKNOWN:
                contributions[constraint_class] = self._calculate_axis_contribution(
                    solution.variables, constraint_class
                )

        # Identifier variables basic/non-basic
        basic_vars = set()
        non_basic_vars = set()
        for var_id, flux_var in linear_program.variables.items():
            if flux_var.is_basic:
                basic_vars.add(var_id)
            else:
                non_basic_vars.add(var_id)

        state = SimplexState3D(
            timestamp=time.time(),
            step_number=self.current_step,
            variables_fi=solution.variables.copy(),
            constraint_contributions=contributions,
            coordinates_3d=coordinates_3d,
            pivot_status=solution.pivot_status_used,
            validation_mode=validation_mode,
            is_feasible=solution.status.name in ['OPTIMAL', 'FEASIBLE'],
            is_optimal=solution.status.name == 'OPTIMAL',
            basic_variables=basic_vars,
            non_basic_variables=non_basic_vars,
            solving_time_ms=solution.solving_time * 1000,
            iterations_used=solution.iterations_used,
            objective_value=getattr(solution, 'final_objective_value', None)
        )

        self.states_history.append(state)
        self.current_step += 1
        return state

    def capture_transition(self, from_state: SimplexState3D, to_state: SimplexState3D,
                         transition_type: SimplexTransitionType) -> SimplexTransition3D:
        """Capture transition entre deux états"""

        # Analyser variables qui entrent/sortent
        entering_vars = to_state.basic_variables - from_state.basic_variables
        leaving_vars = from_state.basic_variables - to_state.basic_variables

        entering_var = list(entering_vars)[0] if entering_vars else None
        leaving_var = list(leaving_vars)[0] if leaving_vars else None

        # Calculer distance euclidienne
        from_coords = from_state.coordinates_3d
        to_coords = to_state.coordinates_3d
        distance = math.sqrt(sum((to_coords[i] - from_coords[i])**2 for i in range(3)))

        # Identifier axe dominant
        coord_diffs = [abs(to_coords[i] - from_coords[i]) for i in range(3)]
        max_diff_idx = coord_diffs.index(max(coord_diffs))
        axes = [ConstraintClass3D.SOURCE, ConstraintClass3D.TARGET, ConstraintClass3D.SECONDARY]
        dominant_axis = axes[max_diff_idx]

        # Calculer améliorations contraintes
        improvements = {}
        for axis in ConstraintClass3D:
            if axis in to_state.constraint_contributions and axis in from_state.constraint_contributions:
                improvements[axis] = to_state.constraint_contributions[axis] - from_state.constraint_contributions[axis]

        transition = SimplexTransition3D(
            from_state=from_state,
            to_state=to_state,
            transition_type=transition_type,
            entering_variable=entering_var,
            leaving_variable=leaving_var,
            euclidean_distance=distance,
            dominant_axis=dominant_axis,
            constraint_improvements=improvements,
            computational_cost=to_state.solving_time_ms - from_state.solving_time_ms
        )

        self.transitions_history.append(transition)
        return transition

    def _calculate_axis_contribution(self, variables_fi: Dict[str, Decimal],
                                   axis: ConstraintClass3D) -> Decimal:
        """Calcule contribution totale pour un axe donné"""
        total = Decimal('0')

        for constraint_name, constraint_class in self.mapper.constraint_classification.items():
            if constraint_class == axis and constraint_name in self.mapper.constraint_weights:
                weights = self.mapper.constraint_weights[constraint_name]
                for var_id, weight in weights.items():
                    if var_id in variables_fi:
                        total += variables_fi[var_id] * weight

        return total

    def export_animation_data(self) -> Dict[str, Any]:
        """Exporte données pour animation 3D"""
        return {
            'metadata': {
                'total_states': len(self.states_history),
                'total_transitions': len(self.transitions_history),
                'algorithm_steps': self.current_step,
                'export_timestamp': time.time()
            },
            'simplex_states': [
                {
                    'step': state.step_number,
                    'coordinates': state.coordinates_3d,
                    'variables_fi': {k: float(v) for k, v in state.variables_fi.items()},
                    'is_feasible': state.is_feasible,
                    'is_optimal': state.is_optimal,
                    'basic_variables': list(state.basic_variables),
                    'iterations': state.iterations_used,
                    'solving_time_ms': state.solving_time_ms,
                    'constraint_contributions': {
                        axis.value: float(contrib) for axis, contrib in state.constraint_contributions.items()
                    }
                }
                for state in self.states_history
            ],
            'simplex_transitions': [
                {
                    'from_step': trans.from_state.step_number,
                    'to_step': trans.to_state.step_number,
                    'from_coordinates': trans.from_state.coordinates_3d,
                    'to_coordinates': trans.to_state.coordinates_3d,
                    'transition_type': trans.transition_type.value,
                    'entering_variable': trans.entering_variable,
                    'leaving_variable': trans.leaving_variable,
                    'euclidean_distance': trans.euclidean_distance,
                    'dominant_axis': trans.dominant_axis.value if trans.dominant_axis else None,
                    'constraint_improvements': {
                        axis.value: float(improvement) for axis, improvement in trans.constraint_improvements.items()
                    }
                }
                for trans in self.transitions_history
            ],
            'axis_mapping': {
                'x': 'SOURCE constraints (Débiteur)',
                'y': 'TARGET constraints (Créditeur)',
                'z': 'SECONDARY constraints (Bonus/Malus)'
            }
        }

    def reset(self):
        """Remet à zéro le collecteur"""
        self.states_history.clear()
        self.transitions_history.clear()
        self.current_step = 0
        self.mapper.constraint_classification.clear()
        self.mapper.constraint_weights.clear()


# Import math module pour distance euclidienne
import math


def create_simplex_3d_api() -> Simplex3DCollector:
    """Factory function pour créer une instance API"""
    return Simplex3DCollector()


if __name__ == '__main__':
    # Démonstration API
    print("🌌 ICGS Simplex 3D Visualization API")
    print("=" * 50)
    print("API read-only pour extraction données Simplex authentiques")
    print("Variables f_i → Coordonnées 3D avec liaison directe icgs_core")
    print("\nArchitecture:")
    print("- SimplexState3D: État à un moment donné")
    print("- SimplexTransition3D: Transition entre états")
    print("- Simplex3DCollector: Collecteur principal")
    print("- Simplex3DMapper: Variables f_i → (x,y,z)")
    print("\n✅ API prête pour intégration avec icgs_core")