"""
Tests unitaires NamedCharacterSetManager

Test suite complète pour validation character-sets nommés avec:
- Définition character-sets et validation configuration
- Allocation automatique caractères par secteur
- Mécanisme freeze et protection configuration
- Gestion erreurs et cas limites
- Performance et métriques
"""

import pytest
from decimal import Decimal
from icgs_core.character_set_manager import (
    NamedCharacterSetManager,
    CharacterSetDefinition,
    create_default_character_set_manager,
    DEFAULT_ECONOMIC_SECTORS
)


class TestCharacterSetDefinition:
    """Tests unitaires CharacterSetDefinition dataclass"""

    def test_character_set_creation(self):
        """Test création basic CharacterSetDefinition"""
        char_set = CharacterSetDefinition(
            name='AGRICULTURE',
            characters=['A', 'B', 'C'],
            regex_pattern='.*[ABC].*',
            max_capacity=3
        )

        assert char_set.name == 'AGRICULTURE'
        assert char_set.characters == ['A', 'B', 'C']
        assert char_set.max_capacity == 3
        assert len(char_set.allocated_characters) == 0
        assert not char_set.is_full
        assert char_set.utilization_rate == 0.0

    def test_available_characters_property(self):
        """Test propriété available_characters"""
        char_set = CharacterSetDefinition(
            name='INDUSTRY',
            characters=['I', 'J', 'K', 'L'],
            regex_pattern='.*[IJKL].*',
            max_capacity=4
        )

        # Initial state
        assert char_set.available_characters == {'I', 'J', 'K', 'L'}

        # Après allocation partielle
        char_set.allocated_characters.add('I')
        char_set.allocated_characters.add('J')
        assert char_set.available_characters == {'K', 'L'}

        # Après allocation complète
        char_set.allocated_characters.add('K')
        char_set.allocated_characters.add('L')
        assert char_set.available_characters == set()
        assert char_set.is_full

    def test_utilization_rate_calculation(self):
        """Test calcul taux d'utilisation"""
        char_set = CharacterSetDefinition(
            name='SERVICES',
            characters=['S', 'T', 'U', 'V'],
            regex_pattern='.*[STUV].*',
            max_capacity=4
        )

        # 0% utilisé
        assert char_set.utilization_rate == 0.0

        # 50% utilisé
        char_set.allocated_characters.update(['S', 'T'])
        assert char_set.utilization_rate == 0.5

        # 100% utilisé
        char_set.allocated_characters.update(['U', 'V'])
        assert char_set.utilization_rate == 1.0


class TestNamedCharacterSetManager:
    """Tests unitaires NamedCharacterSetManager principal"""

    def test_manager_initialization(self):
        """Test initialisation manager vide"""
        manager = NamedCharacterSetManager()

        assert len(manager.character_sets) == 0
        assert not manager.is_frozen
        assert len(manager.character_to_sector) == 0
        assert manager.total_allocations == 0

    def test_define_character_set_basic(self):
        """Test définition character-set basic"""
        manager = NamedCharacterSetManager()

        # Définition AGRICULTURE
        manager.define_character_set('AGRICULTURE', ['A', 'B', 'C'])

        assert 'AGRICULTURE' in manager.character_sets
        char_set = manager.character_sets['AGRICULTURE']
        assert char_set.name == 'AGRICULTURE'
        assert char_set.characters == ['A', 'B', 'C']
        assert char_set.regex_pattern == '.*[ABC].*'
        assert char_set.max_capacity == 3

        # Validation mapping inverse
        assert manager.character_to_sector['A'] == 'AGRICULTURE'
        assert manager.character_to_sector['B'] == 'AGRICULTURE'
        assert manager.character_to_sector['C'] == 'AGRICULTURE'

    def test_define_character_set_single_character(self):
        """Test pattern regex pour character-set à caractère unique"""
        manager = NamedCharacterSetManager()

        manager.define_character_set('CARBON', ['Z'])

        char_set = manager.character_sets['CARBON']
        assert char_set.regex_pattern == '.*Z.*'  # Pattern simple, pas [Z]

    def test_define_character_set_validation_errors(self):
        """Test validation erreurs définition character-sets"""
        manager = NamedCharacterSetManager()

        # Secteur déjà défini
        manager.define_character_set('AGRICULTURE', ['A', 'B'])
        with pytest.raises(ValueError, match="Secteur 'AGRICULTURE' déjà défini"):
            manager.define_character_set('AGRICULTURE', ['C', 'D'])

        # Liste caractères vide
        with pytest.raises(ValueError, match="Liste caractères vide"):
            manager.define_character_set('EMPTY', [])

        # Collision caractères global
        with pytest.raises(ValueError, match="Caractère 'A' déjà utilisé"):
            manager.define_character_set('INDUSTRY', ['A', 'I'])

    def test_automatic_allocation_sequential(self):
        """Test allocation automatique séquentielle par ordre alphabétique"""
        manager = NamedCharacterSetManager()
        manager.define_character_set('INDUSTRY', ['I', 'J', 'K', 'L'])

        # Allocations séquentielles
        char1 = manager.allocate_character_for_sector('INDUSTRY')
        char2 = manager.allocate_character_for_sector('INDUSTRY')
        char3 = manager.allocate_character_for_sector('INDUSTRY')
        char4 = manager.allocate_character_for_sector('INDUSTRY')

        # Vérification ordre alphabétique
        assert [char1, char2, char3, char4] == ['I', 'J', 'K', 'L']

        # Validation état character-set
        char_set = manager.character_sets['INDUSTRY']
        assert char_set.is_full
        assert char_set.utilization_rate == 1.0
        assert char_set.allocated_characters == {'I', 'J', 'K', 'L'}

        # Validation métriques manager
        assert manager.total_allocations == 4

    def test_allocation_capacity_overflow(self):
        """Test dépassement capacité secteur"""
        manager = NamedCharacterSetManager()
        manager.define_character_set('FINANCE', ['F', 'G'])  # Capacité 2

        # Allocations valides
        char1 = manager.allocate_character_for_sector('FINANCE')
        char2 = manager.allocate_character_for_sector('FINANCE')
        assert [char1, char2] == ['F', 'G']

        # Dépassement capacité
        with pytest.raises(RuntimeError, match="Secteur 'FINANCE' à capacité maximale"):
            manager.allocate_character_for_sector('FINANCE')

    def test_allocation_unknown_sector(self):
        """Test allocation secteur inexistant"""
        manager = NamedCharacterSetManager()
        manager.define_character_set('AGRICULTURE', ['A', 'B'])

        with pytest.raises(ValueError, match="Secteur 'UNKNOWN' non défini"):
            manager.allocate_character_for_sector('UNKNOWN')

    def test_deallocate_character_functionality(self):
        """Test libération caractères (debugging/tests)"""
        manager = NamedCharacterSetManager()
        manager.define_character_set('SERVICES', ['S', 'T'])

        # Allocation puis libération
        char = manager.allocate_character_for_sector('SERVICES')
        assert char == 'S'
        assert manager.total_allocations == 1

        manager.deallocate_character('S')
        assert manager.total_allocations == 0

        char_set = manager.character_sets['SERVICES']
        assert 'S' not in char_set.allocated_characters
        assert char_set.available_characters == {'S', 'T'}

    def test_freeze_mechanism_basic(self):
        """Test mécanisme freeze basic"""
        manager = NamedCharacterSetManager()
        manager.define_character_set('AGRICULTURE', ['A', 'B'])
        manager.define_character_set('INDUSTRY', ['I', 'J'])

        # Allocation avant freeze
        char = manager.allocate_character_for_sector('AGRICULTURE')
        assert char == 'A'

        # Freeze
        manager.freeze()
        assert manager.is_frozen

        # Tentatives modifications après freeze
        with pytest.raises(RuntimeError, match="Character-sets figés"):
            manager.define_character_set('SERVICES', ['S', 'T'])

        with pytest.raises(RuntimeError, match="Impossible de libérer"):
            manager.deallocate_character('A')

        # Allocation encore possible après freeze
        char2 = manager.allocate_character_for_sector('INDUSTRY')
        assert char2 == 'I'

    def test_freeze_idempotent(self):
        """Test freeze idempotent (pas d'erreur si re-freeze)"""
        manager = NamedCharacterSetManager()
        manager.define_character_set('AGRICULTURE', ['A'])

        manager.freeze()
        assert manager.is_frozen

        # Re-freeze ne doit pas lever d'erreur
        manager.freeze()
        assert manager.is_frozen

    def test_regex_pattern_retrieval(self):
        """Test récupération patterns regex"""
        manager = NamedCharacterSetManager()
        manager.define_character_set('AGRICULTURE', ['A', 'B', 'C'])
        manager.define_character_set('INDUSTRY', ['I', 'J', 'K', 'L'])
        manager.define_character_set('CARBON', ['Z'])

        # Patterns character-class
        assert manager.get_regex_pattern_for_sector('AGRICULTURE') == '.*[ABC].*'
        assert manager.get_regex_pattern_for_sector('INDUSTRY') == '.*[IJKL].*'

        # Pattern simple
        assert manager.get_regex_pattern_for_sector('CARBON') == '.*Z.*'

        # Secteur inexistant
        with pytest.raises(ValueError, match="Secteur 'UNKNOWN' non défini"):
            manager.get_regex_pattern_for_sector('UNKNOWN')

    def test_character_set_info_retrieval(self):
        """Test récupération informations character-set"""
        manager = NamedCharacterSetManager()
        manager.define_character_set('SERVICES', ['S', 'T', 'U'])
        manager.allocate_character_for_sector('SERVICES')

        char_set_info = manager.get_character_set_info('SERVICES')
        assert isinstance(char_set_info, CharacterSetDefinition)
        assert char_set_info.name == 'SERVICES'
        assert 'S' in char_set_info.allocated_characters
        assert char_set_info.utilization_rate == 1/3

    def test_allocation_statistics_comprehensive(self):
        """Test statistiques allocation complètes"""
        manager = NamedCharacterSetManager()
        manager.define_character_set('AGRICULTURE', ['A', 'B'])
        manager.define_character_set('INDUSTRY', ['I', 'J', 'K'])

        # Allocations partielles
        manager.allocate_character_for_sector('AGRICULTURE')  # A
        manager.allocate_character_for_sector('INDUSTRY')     # I
        manager.allocate_character_for_sector('INDUSTRY')     # J

        stats = manager.get_allocation_statistics()

        # Métriques globales
        assert stats['total_sectors'] == 2
        assert stats['total_allocations'] == 3
        assert stats['is_frozen'] == False

        # Métriques par secteur
        agri_stats = stats['sectors']['AGRICULTURE']
        assert agri_stats['max_capacity'] == 2
        assert agri_stats['allocated_count'] == 1
        assert agri_stats['utilization_rate'] == 0.5
        assert agri_stats['available_characters'] == ['B']
        assert agri_stats['allocated_characters'] == ['A']
        assert agri_stats['is_full'] == False
        assert agri_stats['regex_pattern'] == '.*[AB].*'

        ind_stats = stats['sectors']['INDUSTRY']
        assert ind_stats['allocated_count'] == 2
        assert ind_stats['utilization_rate'] == 2/3

    def test_configuration_validation(self):
        """Test validation cohérence configuration"""
        manager = NamedCharacterSetManager()
        manager.define_character_set('AGRICULTURE', ['A', 'B'])
        manager.define_character_set('INDUSTRY', ['I', 'J'])

        # Configuration valide
        assert manager.validate_configuration() == True

        # Test avec allocations
        manager.allocate_character_for_sector('AGRICULTURE')
        assert manager.validate_configuration() == True

    def test_list_defined_sectors(self):
        """Test listage secteurs définis"""
        manager = NamedCharacterSetManager()

        # Manager vide
        assert manager.list_defined_sectors() == []

        # Après définitions
        manager.define_character_set('AGRICULTURE', ['A'])
        manager.define_character_set('INDUSTRY', ['I'])
        manager.define_character_set('SERVICES', ['S'])

        sectors = manager.list_defined_sectors()
        assert set(sectors) == {'AGRICULTURE', 'INDUSTRY', 'SERVICES'}


class TestDefaultCharacterSetManager:
    """Tests factory function et configuration par défaut"""

    def test_create_default_manager(self):
        """Test création manager avec configuration économique par défaut"""
        manager = create_default_character_set_manager()

        # Validation secteurs par défaut
        expected_sectors = set(DEFAULT_ECONOMIC_SECTORS.keys())
        actual_sectors = set(manager.list_defined_sectors())
        assert actual_sectors == expected_sectors

        # Validation capacités
        assert manager.get_character_set_info('AGRICULTURE').max_capacity == 3
        assert manager.get_character_set_info('INDUSTRY').max_capacity == 4
        assert manager.get_character_set_info('SERVICES').max_capacity == 4
        assert manager.get_character_set_info('FINANCE').max_capacity == 2
        assert manager.get_character_set_info('ENERGY').max_capacity == 2
        assert manager.get_character_set_info('CARBON').max_capacity == 1

        # Validation patterns
        assert manager.get_regex_pattern_for_sector('AGRICULTURE') == '.*[ABC].*'
        assert manager.get_regex_pattern_for_sector('INDUSTRY') == '.*[IJKL].*'
        assert manager.get_regex_pattern_for_sector('CARBON') == '.*Z.*'

    def test_default_manager_allocation_flow(self):
        """Test flux allocation complet avec manager par défaut"""
        manager = create_default_character_set_manager()

        # Simulation allocation multi-agents INDUSTRY (problème original)
        bob_char = manager.allocate_character_for_sector('INDUSTRY')      # I
        charlie_char = manager.allocate_character_for_sector('INDUSTRY')  # J
        david_char = manager.allocate_character_for_sector('INDUSTRY')    # K

        assert [bob_char, charlie_char, david_char] == ['I', 'J', 'K']

        # Validation pattern regex multi-caractères
        pattern = manager.get_regex_pattern_for_sector('INDUSTRY')
        assert pattern == '.*[IJKL].*'

        # Test matching (sera validé dans test NFA)
        import re
        regex = re.compile(pattern)
        assert regex.match('I') is not None
        assert regex.match('J') is not None
        assert regex.match('K') is not None
        assert regex.match('A') is None


class TestCharacterSetManagerErrorHandling:
    """Tests gestion erreurs et cas limites"""

    def test_character_validation_utf32(self):
        """Test validation caractères UTF-32"""
        manager = NamedCharacterSetManager()

        # Caractères valides
        manager.define_character_set('VALID', ['A', 'Z', 'α', '€'])

        # Validation réussie
        assert manager.validate_configuration() == True

    def test_allocation_history_tracking(self):
        """Test suivi historique allocations"""
        manager = NamedCharacterSetManager()
        manager.define_character_set('TEST', ['T', 'E', 'S'])

        # Allocations avec timestamps
        import time
        start_time = time.time()

        char1 = manager.allocate_character_for_sector('TEST')  # Premier: E (alphabétique)
        char2 = manager.allocate_character_for_sector('TEST')  # Deuxième: S

        # Validation historique (allocation par ordre alphabétique)
        assert len(manager.allocation_history) == 2
        assert manager.allocation_history[0][0] == 'TEST'  # sector
        assert manager.allocation_history[0][1] == char1    # premier caractère alloué
        assert manager.allocation_history[0][2] >= start_time  # timestamp

    def test_concurrent_allocation_safety(self):
        """Test sécurité allocation concurrent (simulation)"""
        manager = NamedCharacterSetManager()
        manager.define_character_set('CONCURRENT', ['C', 'O'])

        # Simulation allocation simultanée (même résultat déterministe)
        chars = []
        for _ in range(2):
            char = manager.allocate_character_for_sector('CONCURRENT')
            chars.append(char)

        # Allocation déterministe par ordre alphabétique
        assert chars == ['C', 'O']

        # Capacité atteinte
        with pytest.raises(RuntimeError):
            manager.allocate_character_for_sector('CONCURRENT')


if __name__ == "__main__":
    # Exécution tests avec pytest
    pytest.main([__file__, "-v", "--tb=short"])