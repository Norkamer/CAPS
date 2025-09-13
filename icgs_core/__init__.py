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

# Imports DAG structures
from .dag_structures import Account, Node, Edge, EdgeType, NodeType

# Imports Phase 2.6-2.8 + Price Discovery activés - Simplex et DAG Core implémentés
from .simplex_solver import (
    TripleValidationOrientedSimplex, MathematicallyRigorousPivotManager,
    SimplexSolution, SolutionStatus, PivotStatus, ValidationMode
)
from .dag import DAG, Transaction, TransactionMeasure, DAGConfiguration

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
    'Account',
    'Node', 
    'Edge',
    'EdgeType',
    'NodeType',
    'MathematicallyRigorousPivotManager',
    'TripleValidationOrientedSimplex',
    'SimplexSolution',
    'SolutionStatus',
    'PivotStatus',
    'ValidationMode',
    'DAG',
    'Transaction',
    'TransactionMeasure',
    'DAGConfiguration'
]