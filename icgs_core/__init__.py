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

# Exports principaux selon blueprint - modules disponibles seulement
from .account_taxonomy import AccountTaxonomy

# TODO: Imports à activer au fur et à mesure de l'implémentation
# from .anchored_nfa import AnchoredWeightedNFA, WeightedNFA
# from .linear_programming import LinearProgram, FluxVariable, LinearConstraint
# from .simplex_solver import TripleValidationOrientedSimplex, MathematicallyRigorousPivotManager
# from .dag import DAG
# from .path_enumerator import DAGPathEnumerator

__all__ = [
    'AccountTaxonomy',
    # 'WeightedNFA',
    # 'AnchoredWeightedNFA', 
    # 'LinearProgram',
    # 'FluxVariable',
    # 'LinearConstraint',
    # 'MathematicallyRigorousPivotManager',
    # 'TripleValidationOrientedSimplex',
    # 'DAGPathEnumerator',
    # 'DAG'
]