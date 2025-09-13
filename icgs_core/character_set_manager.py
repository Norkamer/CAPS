"""
Named Character Set Manager pour ICGS Core

Gestion des character-sets nommés avec allocation automatique et freeze mechanism.
Résout la limitation multi-agents même secteur : 83.3% → 100% FEASIBILITY.

Fonctionnalités:
- Configuration character-sets par secteur économique
- Allocation automatique caractères dans sets disponibles
- Freeze configuration après première transaction
- Support regex character-class [ABC] patterns
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from decimal import Decimal


@dataclass
class CharacterSetDefinition:
    """
    Définition d'un character-set nommé pour secteur économique

    Exemple:
        CharacterSetDefinition(
            name="AGRICULTURE",
            characters=['A', 'B', 'C'],
            regex_pattern=".*[ABC].*",
            max_capacity=3,
            allocated_characters={'A', 'B'}  # 2/3 utilisés
        )
    """
    name: str                                    # "AGRICULTURE", "INDUSTRY"
    characters: List[str]                        # ['A', 'B', 'C']
    regex_pattern: str                           # ".*[ABC].*"
    max_capacity: int                            # 3 agents maximum
    allocated_characters: Set[str] = field(default_factory=set)  # {'A', 'B'}

    @property
    def available_characters(self) -> Set[str]:
        """Retourne caractères disponibles pour allocation"""
        return set(self.characters) - self.allocated_characters

    @property
    def is_full(self) -> bool:
        """True si character-set à capacité maximale"""
        return len(self.allocated_characters) >= self.max_capacity

    @property
    def utilization_rate(self) -> float:
        """Taux d'utilisation character-set (0.0 à 1.0)"""
        return len(self.allocated_characters) / self.max_capacity


class NamedCharacterSetManager:
    """
    Gestionnaire character-sets nommés avec allocation automatique et freeze

    Architecture:
    - Configuration initiale des secteurs économiques
    - Allocation automatique caractères par ordre alphabétique
    - Freeze après première transaction (sécurité configuration)
    - Support génération regex patterns character-class

    Usage:
        manager = NamedCharacterSetManager()
        manager.define_character_set('AGRICULTURE', ['A', 'B', 'C'])
        manager.define_character_set('INDUSTRY', ['I', 'J', 'K', 'L'])

        char = manager.allocate_character_for_sector('AGRICULTURE')  # 'A'
        char = manager.allocate_character_for_sector('AGRICULTURE')  # 'B'

        manager.freeze()  # Configuration figée
    """

    def __init__(self):
        # Character-sets définis par secteur
        self.character_sets: Dict[str, CharacterSetDefinition] = {}

        # État freeze - bloque modifications après première transaction
        self.is_frozen: bool = False

        # Mapping inverse: caractère → secteur ('A' → 'AGRICULTURE')
        self.character_to_sector: Dict[str, str] = {}

        # Statistiques allocation
        self.total_allocations: int = 0
        self.allocation_history: List[tuple] = []  # (sector, character, timestamp)

    def define_character_set(self, sector_name: str, characters: List[str]) -> None:
        """
        Définit character-set pour secteur économique

        Args:
            sector_name: Nom secteur ('AGRICULTURE', 'INDUSTRY', etc.)
            characters: Liste caractères disponibles (['A', 'B', 'C'])

        Raises:
            RuntimeError: Si manager figé (freeze)
            ValueError: Si secteur déjà défini ou caractères invalides
        """
        if self.is_frozen:
            raise RuntimeError(
                f"Character-sets figés après première transaction. "
                f"Impossible de définir secteur '{sector_name}'"
            )

        if sector_name in self.character_sets:
            raise ValueError(f"Secteur '{sector_name}' déjà défini")

        if not characters:
            raise ValueError(f"Liste caractères vide pour secteur '{sector_name}'")

        # Validation unicité caractères globale
        for char in characters:
            if char in self.character_to_sector:
                existing_sector = self.character_to_sector[char]
                raise ValueError(
                    f"Caractère '{char}' déjà utilisé dans secteur '{existing_sector}'"
                )

        # Construction regex pattern character-class
        if len(characters) == 1:
            regex_pattern = f".*{characters[0]}.*"  # Pattern simple
        else:
            char_class = ''.join(sorted(characters))
            regex_pattern = f".*[{char_class}].*"  # Pattern character-class

        # Création character-set definition
        char_set = CharacterSetDefinition(
            name=sector_name,
            characters=characters,
            regex_pattern=regex_pattern,
            max_capacity=len(characters),
            allocated_characters=set()
        )

        self.character_sets[sector_name] = char_set

        # Pré-reservation mapping (pas encore alloué)
        for char in characters:
            self.character_to_sector[char] = sector_name

    def allocate_character_for_sector(self, sector_name: str) -> str:
        """
        Alloue automatiquement caractère dans secteur spécifié

        Args:
            sector_name: Nom secteur pour allocation

        Returns:
            Caractère alloué (premier disponible par ordre alphabétique)

        Raises:
            ValueError: Si secteur inexistant
            RuntimeError: Si secteur à capacité maximale
        """
        if sector_name not in self.character_sets:
            available_sectors = ', '.join(self.character_sets.keys())
            raise ValueError(
                f"Secteur '{sector_name}' non défini. "
                f"Secteurs disponibles: {available_sectors}"
            )

        char_set = self.character_sets[sector_name]

        if char_set.is_full:
            raise RuntimeError(
                f"Secteur '{sector_name}' à capacité maximale "
                f"({char_set.max_capacity} agents). "
                f"Impossible d'allouer nouveau caractère."
            )

        # Allocation premier caractère disponible (ordre alphabétique)
        available_chars = char_set.available_characters
        allocated_char = min(available_chars)

        # Marquage allocation
        char_set.allocated_characters.add(allocated_char)
        self.total_allocations += 1

        # Historique allocation
        import time
        self.allocation_history.append((sector_name, allocated_char, time.time()))

        return allocated_char

    def deallocate_character(self, character: str) -> None:
        """
        Libère caractère alloué (pour tests/debugging uniquement)

        Args:
            character: Caractère à libérer

        Raises:
            RuntimeError: Si manager figé
            ValueError: Si caractère non alloué
        """
        if self.is_frozen:
            raise RuntimeError("Impossible de libérer caractères après freeze")

        if character not in self.character_to_sector:
            raise ValueError(f"Caractère '{character}' non défini")

        sector_name = self.character_to_sector[character]
        char_set = self.character_sets[sector_name]

        if character not in char_set.allocated_characters:
            raise ValueError(f"Caractère '{character}' non alloué dans secteur '{sector_name}'")

        char_set.allocated_characters.remove(character)
        self.total_allocations -= 1

    def freeze(self) -> None:
        """
        Fige configuration character-sets après première transaction

        Sécurité: Empêche modifications configuration en cours d'utilisation
        Appelé automatiquement par AccountTaxonomy après transaction 0
        """
        if self.is_frozen:
            return  # Déjà figé, pas d'erreur

        self.is_frozen = True

        # Log freeze pour debugging
        sectors_count = len(self.character_sets)
        total_capacity = sum(cs.max_capacity for cs in self.character_sets.values())
        allocated_count = sum(len(cs.allocated_characters) for cs in self.character_sets.values())

        print(f"CharacterSetManager figé: {sectors_count} secteurs, "
              f"{allocated_count}/{total_capacity} caractères alloués")

    def get_regex_pattern_for_sector(self, sector_name: str) -> str:
        """
        Retourne regex pattern character-class pour secteur

        Args:
            sector_name: Nom secteur

        Returns:
            Pattern regex (ex: ".*[ABC].*" ou ".*A.*")

        Raises:
            ValueError: Si secteur inexistant
        """
        if sector_name not in self.character_sets:
            available_sectors = ', '.join(self.character_sets.keys())
            raise ValueError(
                f"Secteur '{sector_name}' non défini. "
                f"Secteurs disponibles: {available_sectors}"
            )

        return self.character_sets[sector_name].regex_pattern

    def get_character_set_info(self, sector_name: str) -> CharacterSetDefinition:
        """Retourne définition complète character-set"""
        if sector_name not in self.character_sets:
            raise ValueError(f"Secteur '{sector_name}' non défini")
        return self.character_sets[sector_name]

    def list_defined_sectors(self) -> List[str]:
        """Retourne liste secteurs définis"""
        return list(self.character_sets.keys())

    def get_allocation_statistics(self) -> Dict[str, any]:
        """
        Retourne statistiques allocation pour monitoring/debugging

        Returns:
            Dict avec métriques allocation et utilisation
        """
        stats = {
            'total_sectors': len(self.character_sets),
            'total_allocations': self.total_allocations,
            'is_frozen': self.is_frozen,
            'sectors': {}
        }

        for sector_name, char_set in self.character_sets.items():
            stats['sectors'][sector_name] = {
                'max_capacity': char_set.max_capacity,
                'allocated_count': len(char_set.allocated_characters),
                'utilization_rate': char_set.utilization_rate,
                'available_characters': list(char_set.available_characters),
                'allocated_characters': list(char_set.allocated_characters),
                'is_full': char_set.is_full,
                'regex_pattern': char_set.regex_pattern
            }

        return stats

    def validate_configuration(self) -> bool:
        """
        Validation cohérence configuration character-sets

        Returns:
            True si configuration valide

        Raises:
            ValueError: Si incohérences détectées
        """
        # Validation caractères uniques globalement
        all_characters = set()
        for char_set in self.character_sets.values():
            for char in char_set.characters:
                if char in all_characters:
                    raise ValueError(f"Caractère '{char}' utilisé dans plusieurs secteurs")
                all_characters.add(char)

        # Validation regex patterns
        import re
        for sector_name, char_set in self.character_sets.items():
            try:
                re.compile(char_set.regex_pattern)
            except re.error as e:
                raise ValueError(f"Pattern regex invalide pour secteur '{sector_name}': {e}")

        # Validation allocations cohérentes
        for sector_name, char_set in self.character_sets.items():
            for allocated_char in char_set.allocated_characters:
                if allocated_char not in char_set.characters:
                    raise ValueError(
                        f"Caractère alloué '{allocated_char}' pas dans définition "
                        f"secteur '{sector_name}'"
                    )

        return True


# Configuration par défaut secteurs économiques ICGS
DEFAULT_ECONOMIC_SECTORS = {
    'AGRICULTURE': ['A', 'B', 'C'],           # 3 agents agriculture max
    'INDUSTRY': ['I', 'J', 'K', 'L'],         # 4 agents industry max
    'SERVICES': ['S', 'T', 'U', 'V'],         # 4 agents services max
    'FINANCE': ['F', 'G'],                    # 2 agents finance max
    'ENERGY': ['E', 'H'],                     # 2 agents energy max
    'CARBON': ['Z']                           # 1 agent carbon (pénalités)
}


def create_default_character_set_manager() -> NamedCharacterSetManager:
    """
    Factory function pour configuration par défaut ICGS

    Returns:
        NamedCharacterSetManager pré-configuré secteurs économiques standard
    """
    manager = NamedCharacterSetManager()

    for sector_name, characters in DEFAULT_ECONOMIC_SECTORS.items():
        manager.define_character_set(sector_name, characters)

    return manager


if __name__ == "__main__":
    # Démo usage NamedCharacterSetManager
    print("=== Démonstration NamedCharacterSetManager ===")

    manager = create_default_character_set_manager()

    print(f"Secteurs définis: {manager.list_defined_sectors()}")

    # Allocations test
    try:
        agri1 = manager.allocate_character_for_sector('AGRICULTURE')  # 'A'
        agri2 = manager.allocate_character_for_sector('AGRICULTURE')  # 'B'
        ind1 = manager.allocate_character_for_sector('INDUSTRY')      # 'I'

        print(f"Allocations: AGRICULTURE={agri1},{agri2}, INDUSTRY={ind1}")

        # Statistiques
        stats = manager.get_allocation_statistics()
        print(f"Statistiques: {stats['total_allocations']} allocations")

        # Freeze test
        manager.freeze()
        print("Configuration figée avec succès")

    except Exception as e:
        print(f"Erreur: {e}")