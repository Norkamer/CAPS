"""
Scénarios Économiques CAPS - Module Principal

Scénarios économiques avancés pour validation production-ready:
- "Économie Stable" : Simulation équilibrée 7 jours
- "Choc Pétrolier" : ENERGY -40%, propagation inter-sectorielle
- "Innovation Tech" : INDUSTRY +50%, réallocation automatique

Usage:
    from icgs_simulation.scenarios import StableEconomyScenario
    scenario = StableEconomyScenario(simulation)
    results = scenario.run_7_day_simulation()
"""

from .stable_economy import StableEconomyScenario
from .oil_shock import OilShockScenario
from .tech_innovation import TechInnovationScenario

__all__ = [
    'StableEconomyScenario',
    'OilShockScenario',
    'TechInnovationScenario'
]