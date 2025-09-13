"""
Domaines Économiques Pré-configurés

Définit les secteurs économiques standards avec leurs patterns NFA
et poids associés pour faciliter les simulations économiques.
"""

from decimal import Decimal
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class EconomicSector:
    """
    Secteur économique avec configuration NFA pré-définie

    Simplifie création d'agents économiques avec patterns
    et poids optimisés pour validation ICGS.
    """
    name: str
    pattern: str                    # Regex pattern pour NFA
    weight: Decimal                # Poids NFA principal
    description: str
    typical_balance_range: Tuple[Decimal, Decimal]  # (min, max)


# Secteurs économiques standards selon blueprint
SECTORS = {
    'AGRICULTURE': EconomicSector(
        name='AGRICULTURE',
        pattern='.*A.*',
        weight=Decimal('1.5'),
        description='Secteur agricole - production primaire',
        typical_balance_range=(Decimal('500'), Decimal('2000'))
    ),

    'INDUSTRY': EconomicSector(
        name='INDUSTRY',
        pattern='.*I.*',
        weight=Decimal('1.2'),
        description='Secteur industriel - transformation',
        typical_balance_range=(Decimal('300'), Decimal('1500'))
    ),

    'SERVICES': EconomicSector(
        name='SERVICES',
        pattern='.*S.*',
        weight=Decimal('1.0'),
        description='Secteur services - tertiaire',
        typical_balance_range=(Decimal('200'), Decimal('1200'))
    ),

    # Secteurs spécialisés pour simulations avancées
    'FINANCE': EconomicSector(
        name='FINANCE',
        pattern='.*F.*',
        weight=Decimal('0.8'),
        description='Secteur financier - intermédiation',
        typical_balance_range=(Decimal('1000'), Decimal('5000'))
    ),

    'ENERGY': EconomicSector(
        name='ENERGY',
        pattern='.*E.*',
        weight=Decimal('1.3'),
        description='Secteur énergétique - utilities',
        typical_balance_range=(Decimal('800'), Decimal('3000'))
    )
}


def get_sector_info(sector_name: str) -> EconomicSector:
    """Retourne informations secteur économique"""
    if sector_name.upper() not in SECTORS:
        available = ', '.join(SECTORS.keys())
        raise ValueError(f"Secteur '{sector_name}' non reconnu. Disponibles: {available}")

    return SECTORS[sector_name.upper()]


def list_available_sectors() -> List[str]:
    """Liste tous les secteurs économiques disponibles"""
    return list(SECTORS.keys())


def get_recommended_balance(sector_name: str) -> Decimal:
    """Retourne balance recommandée pour un secteur (milieu de range)"""
    sector = get_sector_info(sector_name)
    min_bal, max_bal = sector.typical_balance_range
    return (min_bal + max_bal) / 2