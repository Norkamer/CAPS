"""
ICGS-Core - Intelligent Computation Graph System

Composants principaux du système ICGS avec garanties mathématiques absolues:
- AccountTaxonomy : Fonction taxonomique historisée UTF-32
- AnchoredWeightedNFA : Automate fini pondéré avec ancrage automatique
- LinearProgram : Modélisation problèmes de programmation linéaire
- TripleValidationOrientedSimplex : Solveur Simplex avec triple validation
- DAG : Extension avec pipeline de validation économique Simplex
"""

__version__ = "1.0.0"
__author__ = "Norkamer"

# Exports principaux selon blueprint - modules disponibles
from .account_taxonomy import AccountTaxonomy
from .weighted_nfa import WeightedNFA, RegexWeight, NFAState, NFATransition, TransitionType
from .anchored_nfa import AnchoredWeightedNFA

# Imports programmation linéaire
from .linear_programming import (
    LinearProgram, FluxVariable, LinearConstraint, ConstraintType,
    build_source_constraint, build_target_constraint, build_secondary_constraint,
    build_equality_constraint, create_simple_lp_problem, validate_economic_consistency
)

# Imports path enumeration
from .path_enumerator import DAGPathEnumerator, EnumerationStatistics

# TODO: Imports à activer au fur et à mesure de l'implémentation
# from .simplex_solver import TripleValidationOrientedSimplex, MathematicallyRigorousPivotManager
# from .dag import DAG

__all__ = [
    'AccountTaxonomy',
    'WeightedNFA',
    'AnchoredWeightedNFA',
    'RegexWeight',
    'NFAState',
    'NFATransition',
    'TransitionType',
    'LinearProgram',
    'FluxVariable',
    'LinearConstraint',
    'ConstraintType',
    'build_source_constraint',
    'build_target_constraint',
    'build_secondary_constraint',
    'build_equality_constraint',
    'create_simple_lp_problem',
    'validate_economic_consistency',
    'DAGPathEnumerator',
    'EnumerationStatistics',
    # 'MathematicallyRigorousPivotManager',
    # 'TripleValidationOrientedSimplex',
    # 'DAG'
]