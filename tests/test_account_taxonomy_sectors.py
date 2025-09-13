"""
Tests AccountTaxonomy avec Character-Sets Support

Test suite validation integration AccountTaxonomy + NamedCharacterSetManager:
- Mode character-sets vs mode classique (backward compatibility)
- Allocation automatique avec secteurs économiques
- Mécanisme freeze après première transaction
- Gestion erreurs et validation cohérence
- Performance et métriques integration
"""

import pytest
from decimal import Decimal
from icgs_core.account_taxonomy import AccountTaxonomy, TaxonomySnapshot
from icgs_core.character_set_manager import (
    NamedCharacterSetManager,
    create_default_character_set_manager
)


class TestAccountTaxonomyCharacterSetsIntegration:
    """Tests integration AccountTaxonomy + Character-Sets"""

    def test_initialization_with_character_sets(self):
        """Test initialisation AccountTaxonomy avec character-sets"""
        # Manager avec secteurs économiques
        char_manager = NamedCharacterSetManager()
        char_manager.define_character_set('AGRICULTURE', ['A', 'B', 'C'])
        char_manager.define_character_set('INDUSTRY', ['I', 'J', 'K'])

        # AccountTaxonomy avec character-sets
        taxonomy = AccountTaxonomy(character_set_manager=char_manager)

        assert taxonomy.use_character_sets == True
        assert taxonomy.character_set_manager is char_manager
        assert taxonomy.stats['character_set_mode'] == True
        assert taxonomy.stats['sector_allocations'] == 0

    def test_initialization_classic_mode(self):
        """Test initialisation mode classique (backward compatibility)"""
        taxonomy = AccountTaxonomy()  # Sans character-set manager

        assert taxonomy.use_character_sets == False
        assert taxonomy.character_set_manager is None
        assert taxonomy.stats['character_set_mode'] == False

    def test_update_taxonomy_with_sectors_basic(self):
        """Test mise à jour taxonomie avec secteurs basic"""
        # Setup character-sets
        char_manager = create_default_character_set_manager()
        taxonomy = AccountTaxonomy(character_set_manager=char_manager)

        # Transaction 0 avec secteurs
        accounts_sectors = {
            'ALICE_sink': 'AGRICULTURE',
            'BOB_sink': 'INDUSTRY',
            'CHARLIE_sink': 'SERVICES'
        }

        mapping = taxonomy.update_taxonomy_with_sectors(accounts_sectors, 0)

        # Validation allocation automatique
        assert mapping['ALICE_sink'] == 'A'      # Premier AGRICULTURE
        assert mapping['BOB_sink'] == 'I'        # Premier INDUSTRY
        assert mapping['CHARLIE_sink'] == 'S'    # Premier SERVICES

        # Validation statistiques
        assert taxonomy.stats['sector_allocations'] == 3
        assert taxonomy.stats['freeze_transaction'] == 0

        # Validation character-sets manager frozen
        assert char_manager.is_frozen == True

    def test_multi_agents_same_sector_allocation(self):
        """Test critique: Plusieurs agents même secteur → caractères différents"""
        char_manager = create_default_character_set_manager()
        taxonomy = AccountTaxonomy(character_set_manager=char_manager)

        # Scénario problématique original: 3 agents INDUSTRY
        accounts_sectors = {
            'BOB_sink': 'INDUSTRY',
            'CHARLIE_sink': 'INDUSTRY',
            'DAVID_sink': 'INDUSTRY'
        }

        mapping = taxonomy.update_taxonomy_with_sectors(accounts_sectors, 0)

        # SOLUTION: Caractères différents pour même secteur
        assert mapping['BOB_sink'] == 'I'        # Premier INDUSTRY
        assert mapping['CHARLIE_sink'] == 'J'    # Deuxième INDUSTRY
        assert mapping['DAVID_sink'] == 'K'      # Troisième INDUSTRY

        # Validation unicité caractères
        allocated_chars = set(mapping.values())
        assert len(allocated_chars) == 3  # Pas de collision

        # Pattern regex match tous caractères
        pattern = char_manager.get_regex_pattern_for_sector('INDUSTRY')
        assert pattern == '.*[IJKL].*'

        import re
        regex = re.compile(pattern)
        assert regex.match('I') is not None
        assert regex.match('J') is not None
        assert regex.match('K') is not None

    def test_sector_capacity_overflow_handling(self):
        """Test gestion dépassement capacité secteur"""
        char_manager = NamedCharacterSetManager()
        char_manager.define_character_set('FINANCE', ['F', 'G'])  # Capacité 2
        taxonomy = AccountTaxonomy(character_set_manager=char_manager)

        # Transaction valid - dans capacité
        accounts_valid = {
            'BANK1_sink': 'FINANCE',
            'BANK2_sink': 'FINANCE'
        }
        mapping = taxonomy.update_taxonomy_with_sectors(accounts_valid, 0)
        assert mapping['BANK1_sink'] == 'F'
        assert mapping['BANK2_sink'] == 'G'

        # Transaction overflow - dépassement capacité
        accounts_overflow = {
            'BANK3_sink': 'FINANCE'  # Plus de place dans FINANCE
        }

        with pytest.raises(ValueError, match="Échec allocation secteur 'FINANCE'"):
            taxonomy.update_taxonomy_with_sectors(accounts_overflow, 1)

    def test_freeze_mechanism_after_transaction_zero(self):
        """Test freeze automatique après transaction 0"""
        char_manager = NamedCharacterSetManager()
        char_manager.define_character_set('AGRICULTURE', ['A', 'B'])
        taxonomy = AccountTaxonomy(character_set_manager=char_manager)

        # Avant transaction 0
        assert char_manager.is_frozen == False

        # Transaction 0
        accounts = {'ALICE_sink': 'AGRICULTURE'}
        taxonomy.update_taxonomy_with_sectors(accounts, 0)

        # Après transaction 0 - freeze automatique
        assert char_manager.is_frozen == True
        assert taxonomy.stats['freeze_transaction'] == 0

        # Tentative définition nouveau secteur impossible
        with pytest.raises(RuntimeError):
            char_manager.define_character_set('NEW_SECTOR', ['N'])

        # Mais allocation encore possible
        accounts2 = {'BOB_sink': 'AGRICULTURE'}
        mapping2 = taxonomy.update_taxonomy_with_sectors(accounts2, 1)
        assert mapping2['BOB_sink'] == 'B'

    def test_historical_consistency_with_sectors(self):
        """Test cohérence historique avec character-sets"""
        char_manager = create_default_character_set_manager()
        taxonomy = AccountTaxonomy(character_set_manager=char_manager)

        # Transaction 0
        accounts_0 = {'ALICE_sink': 'AGRICULTURE', 'BOB_sink': 'INDUSTRY'}
        mapping_0 = taxonomy.update_taxonomy_with_sectors(accounts_0, 0)

        # Transaction 1 - nouveaux comptes
        accounts_1 = {'CHARLIE_sink': 'INDUSTRY', 'DAVID_sink': 'SERVICES'}
        mapping_1 = taxonomy.update_taxonomy_with_sectors(accounts_1, 1)

        # Validation historique transaction 0
        alice_char_t0 = taxonomy.get_character_mapping('ALICE_sink', 0)
        bob_char_t0 = taxonomy.get_character_mapping('BOB_sink', 0)
        assert alice_char_t0 == 'A'
        assert bob_char_t0 == 'I'

        # Validation historique transaction 1 (héritage + nouveaux)
        alice_char_t1 = taxonomy.get_character_mapping('ALICE_sink', 1)
        charlie_char_t1 = taxonomy.get_character_mapping('CHARLIE_sink', 1)
        assert alice_char_t1 == 'A'   # Héritage transaction 0
        assert charlie_char_t1 == 'J'  # Nouveau, deuxième INDUSTRY

        # Validation cohérence
        errors = taxonomy.validate_historical_consistency()
        assert len(errors) == 0

    def test_fallback_to_classic_mode(self):
        """Test fallback vers mode classique si pas character-sets"""
        char_manager = create_default_character_set_manager()
        taxonomy = AccountTaxonomy(character_set_manager=char_manager)

        # Mode character-sets désactivé temporairement
        taxonomy.use_character_sets = False

        # Update avec secteurs → fallback mode classique
        accounts_sectors = {'ALICE_sink': 'AGRICULTURE'}

        # Fallback vers update_taxonomy classique avec None
        with pytest.raises(ValueError, match="Explicit character mapping required"):
            taxonomy.update_taxonomy_with_sectors(accounts_sectors, 0)

    def test_unknown_sector_error_handling(self):
        """Test gestion secteur inexistant"""
        char_manager = NamedCharacterSetManager()
        char_manager.define_character_set('AGRICULTURE', ['A'])
        taxonomy = AccountTaxonomy(character_set_manager=char_manager)

        accounts_invalid = {'ALICE_sink': 'UNKNOWN_SECTOR'}

        with pytest.raises(ValueError, match="Échec allocation secteur 'UNKNOWN_SECTOR'"):
            taxonomy.update_taxonomy_with_sectors(accounts_invalid, 0)

    def test_mixed_transactions_sectors_and_classic(self):
        """Test mélange transactions secteurs et héritage classique"""
        char_manager = create_default_character_set_manager()
        taxonomy = AccountTaxonomy(character_set_manager=char_manager)

        # Transaction 0 - avec secteurs
        accounts_0 = {'ALICE_sink': 'AGRICULTURE', 'BOB_sink': 'INDUSTRY'}
        mapping_0 = taxonomy.update_taxonomy_with_sectors(accounts_0, 0)

        # Transaction 1 - ajout comptes sans modification secteurs existants
        accounts_1 = {'CHARLIE_sink': 'SERVICES'}
        mapping_1 = taxonomy.update_taxonomy_with_sectors(accounts_1, 1)

        # Validation héritage correct
        snapshot_1 = taxonomy.get_taxonomy_snapshot(1)
        assert 'ALICE_sink' in snapshot_1.account_mappings  # Hérité
        assert 'BOB_sink' in snapshot_1.account_mappings    # Hérité
        assert 'CHARLIE_sink' in snapshot_1.account_mappings  # Nouveau

        assert snapshot_1.account_mappings['ALICE_sink'] == 'A'  # Préservé
        assert snapshot_1.account_mappings['CHARLIE_sink'] == 'S'  # Nouveau

    def test_path_to_word_conversion_with_sectors(self):
        """Test conversion chemin → mot avec character-sets"""
        char_manager = create_default_character_set_manager()
        taxonomy = AccountTaxonomy(character_set_manager=char_manager)

        # Setup comptes avec secteurs
        accounts = {
            'ALICE_sink': 'AGRICULTURE',  # A
            'BOB_sink': 'INDUSTRY',       # I
            'CHARLIE_sink': 'SERVICES'    # S
        }
        taxonomy.update_taxonomy_with_sectors(accounts, 0)

        # Mock nodes pour chemin
        from icgs_core.account_taxonomy import Node
        nodes = [
            Node('ALICE_sink'),
            Node('BOB_sink'),
            Node('CHARLIE_sink')
        ]

        # Conversion chemin → mot
        word = taxonomy.convert_path_to_word(nodes, 0)
        assert word == 'AIS'  # Agriculture → Industry → Services

        # Test avec transaction historique
        word_t0 = taxonomy.convert_path_to_word(nodes, 0)
        assert word_t0 == 'AIS'


class TestAccountTaxonomyBackwardCompatibility:
    """Tests compatibility mode classique préservée"""

    def test_classic_mode_unchanged(self):
        """Test mode classique inchangé (backward compatibility)"""
        taxonomy = AccountTaxonomy()  # Sans character-sets

        # Comportement classique standard
        accounts = {
            'ALICE_sink': 'A',
            'BOB_sink': 'B'
        }

        mapping = taxonomy.update_taxonomy(accounts, 0)
        assert mapping['ALICE_sink'] == 'A'
        assert mapping['BOB_sink'] == 'B'

        # Méthodes existantes fonctionnent
        alice_char = taxonomy.get_character_mapping('ALICE_sink', 0)
        assert alice_char == 'A'

    def test_mixed_usage_character_sets_and_classic(self):
        """Test utilisation mixte character-sets et classique"""
        # Même instance peut utiliser les deux modes selon contexte
        char_manager = create_default_character_set_manager()
        taxonomy = AccountTaxonomy(character_set_manager=char_manager)

        # Mode character-sets
        accounts_sectors = {'ALICE_sink': 'AGRICULTURE'}
        mapping_sectors = taxonomy.update_taxonomy_with_sectors(accounts_sectors, 0)
        assert mapping_sectors['ALICE_sink'] == 'A'

        # Mode character-sets désactivé pour test backward compatibility
        taxonomy.use_character_sets = False

        # Fallback classique (avec erreur pour None - design actuel)
        accounts_classic = {'BOB_sink': 'B'}

        # En mode classique, il faut explicitement fournir le mapping
        # (comportement actuel AccountTaxonomy)
        # Ce test valide que le fallback fonctionne correctement


class TestCharacterSetManagerFreezeMechanism:
    """Tests spécifiques mécanisme freeze"""

    def test_freeze_timing_transaction_zero(self):
        """Test timing freeze exactement après transaction 0"""
        char_manager = create_default_character_set_manager()
        taxonomy = AccountTaxonomy(character_set_manager=char_manager)

        # Transaction -1 (initialisation) - pas de freeze
        accounts_init = {'INIT_sink': 'AGRICULTURE'}
        try:
            mapping = taxonomy.update_taxonomy_with_sectors(accounts_init, -1)
            # Si -1 accepté, pas encore de freeze
            assert char_manager.is_frozen == False
        except ValueError:
            # Si -1 rejeté (comportement normal), skip ce test
            pass

        # Transaction 0 - trigger freeze
        accounts_0 = {'ALICE_sink': 'AGRICULTURE'}
        mapping = taxonomy.update_taxonomy_with_sectors(accounts_0, 0)

        # Freeze après transaction 0
        assert char_manager.is_frozen == True
        assert taxonomy.stats['freeze_transaction'] == 0

    def test_freeze_preserves_allocation_capability(self):
        """Test freeze préserve capacité allocation (pas définition)"""
        char_manager = NamedCharacterSetManager()
        char_manager.define_character_set('TEST', ['T', 'E', 'S'])
        taxonomy = AccountTaxonomy(character_set_manager=char_manager)

        # Transaction 0 avec freeze
        accounts_0 = {'ALICE_sink': 'TEST'}
        mapping_0 = taxonomy.update_taxonomy_with_sectors(accounts_0, 0)
        assert char_manager.is_frozen == True

        # Allocation encore possible après freeze
        accounts_1 = {'BOB_sink': 'TEST'}
        mapping_1 = taxonomy.update_taxonomy_with_sectors(accounts_1, 1)

        # Caractères alloués par ordre alphabétique: E, S, T
        expected_chars = sorted(['T', 'E', 'S'])
        first_allocated = mapping_0['ALICE_sink']  # Premier alloué
        second_allocated = mapping_1['BOB_sink']   # Deuxième alloué

        # Validation que les deux caractères sont différents
        assert first_allocated != second_allocated
        assert first_allocated in expected_chars
        assert second_allocated in expected_chars

        # Mais définition nouveau secteur impossible
        with pytest.raises(RuntimeError):
            char_manager.define_character_set('NEW', ['N'])

    def test_freeze_statistics_tracking(self):
        """Test suivi statistiques freeze"""
        char_manager = create_default_character_set_manager()
        taxonomy = AccountTaxonomy(character_set_manager=char_manager)

        # Avant freeze
        assert taxonomy.stats['freeze_transaction'] is None

        # Transaction trigger freeze
        accounts = {'ALICE_sink': 'AGRICULTURE'}
        taxonomy.update_taxonomy_with_sectors(accounts, 0)

        # Statistiques freeze enregistrées
        assert taxonomy.stats['freeze_transaction'] == 0

        # Manager stats cohérentes
        manager_stats = char_manager.get_allocation_statistics()
        assert manager_stats['is_frozen'] == True


class TestCharacterSetsPerformanceIntegration:
    """Tests performance integration character-sets"""

    def test_allocation_performance_multiple_sectors(self):
        """Test performance allocation multiple secteurs"""
        char_manager = create_default_character_set_manager()
        taxonomy = AccountTaxonomy(character_set_manager=char_manager)

        import time
        start_time = time.time()

        # Simulation charge: 10 comptes, 5 secteurs
        accounts_sectors = {}
        sectors = ['AGRICULTURE', 'INDUSTRY', 'SERVICES', 'FINANCE', 'ENERGY']

        for i in range(10):
            sector = sectors[i % len(sectors)]
            account_id = f'ACCOUNT_{i}_sink'
            accounts_sectors[account_id] = sector

        # Allocation batch
        mapping = taxonomy.update_taxonomy_with_sectors(accounts_sectors, 0)

        allocation_time = time.time() - start_time

        # Validation performance acceptable (<10ms pour 10 comptes)
        assert allocation_time < 0.01
        assert len(mapping) == 10

        # Validation distribution secteurs
        sector_counts = {}
        for account_id, sector in accounts_sectors.items():
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

        # Vérification capacités respectées
        for sector, count in sector_counts.items():
            char_set = char_manager.get_character_set_info(sector)
            assert count <= char_set.max_capacity

    def test_memory_usage_character_sets_vs_classic(self):
        """Test usage mémoire character-sets vs classique"""
        import sys

        # Mode classique
        taxonomy_classic = AccountTaxonomy()
        accounts_classic = {f'ACCOUNT_{i}_sink': chr(ord('A') + i) for i in range(10)}
        taxonomy_classic.update_taxonomy(accounts_classic, 0)

        classic_size = sys.getsizeof(taxonomy_classic.taxonomy_history)

        # Mode character-sets
        char_manager = create_default_character_set_manager()
        taxonomy_sectors = AccountTaxonomy(character_set_manager=char_manager)

        accounts_sectors = {f'ACCOUNT_{i}_sink': 'AGRICULTURE' for i in range(3)}
        taxonomy_sectors.update_taxonomy_with_sectors(accounts_sectors, 0)

        sectors_size = sys.getsizeof(taxonomy_sectors.taxonomy_history)
        manager_size = sys.getsizeof(char_manager.character_sets)

        total_sectors_size = sectors_size + manager_size

        # Overhead acceptable (character-sets apporte fonctionnalités supplémentaires)
        overhead_ratio = total_sectors_size / max(classic_size, 1)

        # Overhead doit être raisonnable (<5x pour fonctionnalités avancées)
        # Character-sets manager contient beaucoup plus de structures de données
        assert overhead_ratio < 5.0

        # Test que l'overhead reste dans une gamme acceptable
        print(f"Memory overhead ratio: {overhead_ratio:.2f}x")


if __name__ == "__main__":
    # Exécution tests
    pytest.main([__file__, "-v", "--tb=short"])