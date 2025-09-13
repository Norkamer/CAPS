"""
ICGS Simulation Framework

Interface publique simplifiée pour simulations économiques avec ICGS.
Masque la complexité d'icgs_core et fournit une API intuitive pour:
- Création d'agents économiques
- Validation de transactions
- Découverte de prix optimaux (Price Discovery)

Architecture selon ICGS_MASTER_RECONSTRUCTION_BLUEPRINT.md Phase 5.
"""

from .api.icgs_bridge import EconomicSimulation
from .domains.base import EconomicSector, SECTORS

__version__ = "1.0.0"
__author__ = "ICGS Team"

# Interface publique simplifiée
__all__ = [
    'EconomicSimulation',
    'EconomicSector',
    'SECTORS'
]