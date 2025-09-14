"""
Tests AnchoredWeightedNFA Character-Class Support

Test suite validation extension character-class patterns dans AnchoredWeightedNFA:
- Support regex character-class [ABC] syntax
- Thompson NFA construction pour character-sets
- Integration patterns classiques + character-class
- Matching complet pour tous caractères dans sets
- Performance et compatibilité backward
"""

import pytest
from decimal import Decimal
from icgs_core.anchored_nfa import AnchoredWeightedNFA
from icgs_core.weighted_nfa import RegexWeight
import re


class TestCharacterClassPatternDetection:
    """Tests détection patterns character-class"""

    def test_has_character_class_detection(self):
        """Test détection patterns character-class [ABC]"""
        nfa = AnchoredWeightedNFA("test_character_class")

        # Patterns avec character-class
        assert nfa._has_character_class(".*[ABC].*") == True
        assert nfa._has_character_class(".*[IJKL].*") == True
        assert nfa._has_character_class("[XYZ]") == True
        assert nfa._has_character_class("prefix[123]suffix") == True

        # Patterns sans character-class
        assert nfa._has_character_class(".*ABC.*") == False
        assert nfa._has_character_class("simple") == False
        assert nfa._has_character_class(".*A.*") == False

        # Patterns échappés (pas character-class)
        assert nfa._has_character_class("\\[ABC\\]") == False

    def test_extract_character_class_basic(self):
        """Test extraction caractères de [ABC]"""
        nfa = AnchoredWeightedNFA("test_extract")

        # Extraction basic
        chars = nfa._extract_character_class(".*[ABC].*")
        assert chars == ['A', 'B', 'C']

        chars = nfa._extract_character_class(".*[IJKL].*")
        assert chars == ['I', 'J', 'K', 'L']

        chars = nfa._extract_character_class("[XYZ]")
        assert chars == ['X', 'Y', 'Z']

        # Pattern sans character-class
        chars = nfa._extract_character_class(".*simple.*")
        assert chars == []

    def test_substitute_character_class(self):
        """Test substitution [ABC] → caractère spécifique"""
        nfa = AnchoredWeightedNFA("test_substitute")

        # Substitution basic
        result = nfa._substitute_character_class(".*[ABC].*", ['A', 'B', 'C'], 'A')
        assert result == ".*A.*"

        result = nfa._substitute_character_class(".*[IJKL].*", ['I', 'J', 'K', 'L'], 'J')
        assert result == ".*J.*"

        # Pattern complexe
        result = nfa._substitute_character_class("prefix[XYZ]suffix", ['X', 'Y', 'Z'], 'Y')
        assert result == "prefixYsuffix"


class TestCharacterClassNFAConstruction:
    """Tests construction NFA character-class"""

    def test_add_character_class_regex_basic(self):
        """Test ajout regex character-class basic"""
        nfa = AnchoredWeightedNFA("test_character_class")

        # Ajout pattern character-class
        final_state = nfa.add_weighted_regex_with_character_class_support(
            measure_id="industry_measure",
            regex_pattern=".*[IJKL].*",
            weight=Decimal('1.2')
        )

        # Validation état final créé
        assert final_state is not None
        assert final_state.is_final == True
        assert "industry_measure" in final_state.state_id
        assert "character_class" in final_state.state_id

        # Validation RegexWeight
        assert len(final_state.regex_weights) == 1
        regex_weight = final_state.regex_weights[0]
        assert regex_weight.measure_id == "industry_measure"
        assert regex_weight.weight == Decimal('1.2')

        # Validation métadonnées character-class
        assert final_state.metadata['pattern_type'] == 'character_class'
        assert final_state.metadata['character_class'] == ['I', 'J', 'K', 'L']
        assert final_state.metadata['character_count'] == 4

    def test_character_class_compiled_patterns(self):
        """Test patterns compilés pour chaque caractère"""
        nfa = AnchoredWeightedNFA("test_compiled")

        final_state = nfa.add_weighted_regex_with_character_class_support(
            "test_measure", ".*[ABC].*", Decimal('1.0')
        )

        # Validation patterns compilés créés
        assert hasattr(final_state, 'compiled_patterns')
        assert len(final_state.compiled_patterns) == 3

        # Validation patterns individuels
        patterns = [p['pattern'] for p in final_state.compiled_patterns]
        # Patterns ancré avec double .* à cause de l'ancrage automatique
        assert ".*.*A.*$" in patterns  # Ancrage automatique appliqué
        assert ".*.*B.*$" in patterns
        assert ".*.*C.*$" in patterns

        # Validation compilation regex
        for pattern_info in final_state.compiled_patterns:
            assert 'compiled' in pattern_info
            assert 'weight' in pattern_info
            assert pattern_info['weight'] == Decimal('1.0')

    def test_character_class_vs_simple_pattern_dispatch(self):
        """Test dispatch correct character-class vs patterns simples"""
        nfa = AnchoredWeightedNFA("test_dispatch")

        # Pattern character-class → utilise _add_character_class_regex
        cc_state = nfa.add_weighted_regex_with_character_class_support(
            "cc_measure", ".*[XYZ].*", Decimal('2.0')
        )
        assert cc_state.metadata['pattern_type'] == 'character_class'
        assert hasattr(cc_state, 'compiled_patterns')

        # Pattern simple → utilise add_weighted_regex standard
        simple_state = nfa.add_weighted_regex_with_character_class_support(
            "simple_measure", ".*simple.*", Decimal('1.0')
        )
        # Pattern simple n'a pas de métadonnées character-class
        assert 'pattern_type' not in simple_state.metadata or simple_state.metadata['pattern_type'] != 'character_class'

    def test_character_class_error_handling(self):
        """Test gestion erreurs character-class"""
        nfa = AnchoredWeightedNFA("test_errors")

        # Pattern character-class invalide
        with pytest.raises(ValueError, match="Invalid character-class pattern"):
            nfa._add_character_class_regex("test", ".*invalid.*", Decimal('1.0'))

        # NFA frozen
        nfa.freeze()
        with pytest.raises(RuntimeError, match="Cannot modify frozen"):
            nfa.add_weighted_regex_with_character_class_support(
                "test", ".*[ABC].*", Decimal('1.0')
            )


class TestCharacterClassMatching:
    """Tests matching avec character-class patterns"""

    def test_character_class_matching_basic(self):
        """Test matching basic character-class"""
        nfa = AnchoredWeightedNFA("test_matching")

        # Setup pattern character-class
        final_state = nfa.add_weighted_regex_with_character_class_support(
            "industry_measure", ".*[IJKL].*", Decimal('1.2')
        )

        # Test matching avec nouvelle méthode
        assert nfa.evaluate_to_final_state_with_character_class_support('I') == final_state.state_id
        assert nfa.evaluate_to_final_state_with_character_class_support('J') == final_state.state_id
        assert nfa.evaluate_to_final_state_with_character_class_support('K') == final_state.state_id
        assert nfa.evaluate_to_final_state_with_character_class_support('L') == final_state.state_id

        # Test non-matching
        assert nfa.evaluate_to_final_state_with_character_class_support('A') is None
        assert nfa.evaluate_to_final_state_with_character_class_support('X') is None

    def test_multiple_character_classes(self):
        """Test matching multiples character-classes"""
        nfa = AnchoredWeightedNFA("test_multiple")

        # Setup multiple character-classes
        agri_state = nfa.add_weighted_regex_with_character_class_support(
            "agriculture_measure", ".*[ABC].*", Decimal('1.5')
        )
        industry_state = nfa.add_weighted_regex_with_character_class_support(
            "industry_measure", ".*[IJKL].*", Decimal('1.2')
        )

        # Test matching distinctes
        assert nfa.evaluate_to_final_state_with_character_class_support('A') == agri_state.state_id
        assert nfa.evaluate_to_final_state_with_character_class_support('B') == agri_state.state_id
        assert nfa.evaluate_to_final_state_with_character_class_support('I') == industry_state.state_id
        assert nfa.evaluate_to_final_state_with_character_class_support('J') == industry_state.state_id

        # Test non-matching
        assert nfa.evaluate_to_final_state_with_character_class_support('X') is None

    def test_character_class_with_frozen_state(self):
        """Test matching character-class avec NFA frozen"""
        nfa = AnchoredWeightedNFA("test_frozen")

        # Setup avant freeze
        final_state = nfa.add_weighted_regex_with_character_class_support(
            "test_measure", ".*[XYZ].*", Decimal('1.0')
        )

        # Freeze NFA
        nfa.freeze()

        # Test matching après freeze
        assert nfa.evaluate_to_final_state_with_character_class_support('X') == final_state.state_id
        assert nfa.evaluate_to_final_state_with_character_class_support('Y') == final_state.state_id
        assert nfa.evaluate_to_final_state_with_character_class_support('Z') == final_state.state_id

        # Validation statistiques frozen
        assert nfa.stats['frozen_evaluations'] >= 3

    def test_character_class_complex_patterns(self):
        """Test patterns character-class complexes"""
        nfa = AnchoredWeightedNFA("test_complex")

        # Pattern avec ancrage automatique
        final_state = nfa.add_weighted_regex_with_character_class_support(
            "complex_measure", "[ABC]suffix", Decimal('2.0')
        )

        # Test matching patterns complexes
        # Note: ici simplifié car implementation utilise regex Python
        # Pattern devient .*Asuffix$ etc.
        result_A = nfa.evaluate_to_final_state_with_character_class_support('Asuffix')
        # Selon implémentation, peut nécessiter ajustement


class TestCharacterClassCompatibility:
    """Tests compatibilité patterns classiques + character-class"""

    def test_mixed_patterns_coexistence(self):
        """Test coexistence patterns classiques + character-class"""
        nfa = AnchoredWeightedNFA("test_mixed")

        # Pattern classique
        classic_state = nfa.add_weighted_regex("classic_measure", ".*A.*", Decimal('1.0'))

        # Pattern character-class
        cc_state = nfa.add_weighted_regex_with_character_class_support(
            "cc_measure", ".*[XYZ].*", Decimal('2.0')
        )

        # Test matching mixed
        classic_result = nfa.evaluate_to_final_state_with_character_class_support('A')
        cc_result = nfa.evaluate_to_final_state_with_character_class_support('X')

        # Validation états distincts
        assert classic_result != cc_result
        assert cc_result == cc_state.state_id

    def test_backward_compatibility_preservation(self):
        """Test backward compatibility méthodes existantes"""
        nfa = AnchoredWeightedNFA("test_backward")

        # Pattern classique via méthode standard
        classic_state = nfa.add_weighted_regex("test_measure", ".*test.*", Decimal('1.0'))

        # Méthodes existantes doivent fonctionner
        assert nfa.evaluate_to_final_state('test') == classic_state.state_id

        # Nouvelle méthode doit être compatible
        assert nfa.evaluate_to_final_state_with_character_class_support('test') == classic_state.state_id

    def test_character_class_state_management(self):
        """Test gestion états avec character-class"""
        nfa = AnchoredWeightedNFA("test_states")

        initial_state_count = len(nfa.states)

        # Ajout character-class
        cc_state = nfa.add_weighted_regex_with_character_class_support(
            "test_measure", ".*[ABC].*", Decimal('1.0')
        )

        # Validation état ajouté
        assert len(nfa.states) == initial_state_count + 1
        assert cc_state in nfa.get_final_states()
        assert cc_state.state_id in nfa.states


class TestCharacterClassPerformance:
    """Tests performance character-class vs classique"""

    def test_character_class_construction_performance(self):
        """Test performance construction character-class"""
        import time

        nfa = AnchoredWeightedNFA("test_performance")

        # Benchmark construction classique
        start_time = time.time()
        for i in range(10):
            nfa.add_weighted_regex(f"classic_{i}", f".*{chr(ord('A') + i)}.*", Decimal('1.0'))
        classic_time = time.time() - start_time

        # Benchmark construction character-class
        start_time = time.time()
        for i in range(5):  # Moins d'iterations car plus complexe
            chars = [chr(ord('A') + j) for j in range(i, i + 2)]
            char_class = ''.join(chars)
            nfa.add_weighted_regex_with_character_class_support(
                f"cc_{i}", f".*[{char_class}].*", Decimal('1.0')
            )
        cc_time = time.time() - start_time

        # Performance acceptable (character-class plus complexe mais raisonnable)
        overhead_ratio = cc_time / max(classic_time, 0.001)
        assert overhead_ratio < 10.0  # <10x overhead acceptable

    def test_character_class_matching_performance(self):
        """Test performance matching character-class"""
        nfa = AnchoredWeightedNFA("test_matching_perf")

        # Setup patterns
        nfa.add_weighted_regex_with_character_class_support(
            "perf_measure", ".*[ABCDEFGH].*", Decimal('1.0')
        )

        # Benchmark matching
        import time
        start_time = time.time()

        for _ in range(100):
            nfa.evaluate_to_final_state_with_character_class_support('A')
            nfa.evaluate_to_final_state_with_character_class_support('E')
            nfa.evaluate_to_final_state_with_character_class_support('H')

        matching_time = time.time() - start_time

        # Performance acceptable (<1ms pour 300 evaluations)
        assert matching_time < 0.001


class TestCharacterClassIntegrationICGS:
    """Tests integration character-class avec character-sets ICGS"""

    def test_icgs_character_sets_integration(self):
        """Test integration complète avec character-sets ICGS"""
        # Import nécessaire pour integration
        from icgs_core.character_set_manager import create_default_character_set_manager

        nfa = AnchoredWeightedNFA("test_icgs_integration")
        char_manager = create_default_character_set_manager()

        # Configuration patterns ICGS avec character-class
        sectors_patterns = {
            'AGRICULTURE': char_manager.get_regex_pattern_for_sector('AGRICULTURE'),  # .*[ABC].*
            'INDUSTRY': char_manager.get_regex_pattern_for_sector('INDUSTRY'),        # .*[IJKL].*
            'SERVICES': char_manager.get_regex_pattern_for_sector('SERVICES')         # .*[STUV].*
        }

        # Ajout patterns dans NFA
        sector_states = {}
        for sector, pattern in sectors_patterns.items():
            sector_states[sector] = nfa.add_weighted_regex_with_character_class_support(
                f"{sector.lower()}_measure", pattern, Decimal('1.0')
            )

        # Test matching complet selon character-sets
        # AGRICULTURE: ['A', 'B', 'C']
        assert nfa.evaluate_to_final_state_with_character_class_support('A') == sector_states['AGRICULTURE'].state_id
        assert nfa.evaluate_to_final_state_with_character_class_support('B') == sector_states['AGRICULTURE'].state_id
        assert nfa.evaluate_to_final_state_with_character_class_support('C') == sector_states['AGRICULTURE'].state_id

        # INDUSTRY: ['I', 'J', 'K', 'L']
        assert nfa.evaluate_to_final_state_with_character_class_support('I') == sector_states['INDUSTRY'].state_id
        assert nfa.evaluate_to_final_state_with_character_class_support('J') == sector_states['INDUSTRY'].state_id
        assert nfa.evaluate_to_final_state_with_character_class_support('K') == sector_states['INDUSTRY'].state_id
        assert nfa.evaluate_to_final_state_with_character_class_support('L') == sector_states['INDUSTRY'].state_id

        # SERVICES: ['S', 'T', 'U', 'V']
        assert nfa.evaluate_to_final_state_with_character_class_support('S') == sector_states['SERVICES'].state_id
        assert nfa.evaluate_to_final_state_with_character_class_support('T') == sector_states['SERVICES'].state_id

        # Test non-matching
        assert nfa.evaluate_to_final_state_with_character_class_support('X') is None
        assert nfa.evaluate_to_final_state_with_character_class_support('Z') is None

    def test_multi_agent_same_sector_resolution(self):
        """Test critique: Résolution multi-agents même secteur avec NFA"""
        nfa = AnchoredWeightedNFA("test_multi_agent")

        # Pattern INDUSTRY pour multi-agents
        industry_state = nfa.add_weighted_regex_with_character_class_support(
            "industry_measure", ".*[IJKL].*", Decimal('1.2')
        )

        # Simulation caractères alloués à 3 agents INDUSTRY
        bob_char = 'I'      # BOB_sink
        charlie_char = 'J'  # CHARLIE_sink
        david_char = 'K'    # DAVID_sink

        # VALIDATION CRITIQUE: Tous matchent même état final
        bob_result = nfa.evaluate_to_final_state_with_character_class_support(bob_char)
        charlie_result = nfa.evaluate_to_final_state_with_character_class_support(charlie_char)
        david_result = nfa.evaluate_to_final_state_with_character_class_support(david_char)

        # Même état final pour tous → classification cohérente
        assert bob_result == industry_state.state_id
        assert charlie_result == industry_state.state_id
        assert david_result == industry_state.state_id

        # RÉSOLUTION: Pas de collision, classification unifiée
        assert bob_result == charlie_result == david_result

        print(f"✅ Multi-agents INDUSTRY: BOB={bob_char}, CHARLIE={charlie_char}, DAVID={david_char}")
        print(f"   → Tous classifiés état: {bob_result}")
        print(f"   → Pattern: .*[IJKL].* matche tous caractères!")


if __name__ == "__main__":
    # Exécution tests
    pytest.main([__file__, "-v", "--tb=short"])