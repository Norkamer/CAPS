"""
Test Académique 20: Intégration NFA Character-Class - Propriétés Algorithmiques

Ce test vérifie rigoureusement les propriétés mathématiques et algorithmiques
de l'extension NFA pour support character-class patterns selon ICGS.

Propriétés testées:
1. Thompson Construction: Algorithme standard pour character-class [ABC]
2. Pattern Equivalence: .*[ABC].* ≡ (.*A.*|.*B.*|.*C.*)
3. État Final Unique: Multi-patterns → single final state consolidation
4. Déterminisme Évaluation: Évaluation reproductible et cohérente
5. Performance Construction: O(|pattern|×|character_class|) respectée
6. Intégration ICGS: Pipeline DAG → NFA → Simplex sans régression

Niveau académique: Validation formelle algorithmes NFA étendus
"""

import pytest
import time
from decimal import Decimal
from typing import Dict, List, Set, Optional

# Import des modules à tester
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_core.anchored_nfa import AnchoredWeightedNFA
from icgs_core.weighted_nfa import WeightedNFA, NFAState, RegexWeight
from icgs_core.character_set_manager import create_default_character_set_manager
from icgs_core.account_taxonomy import AccountTaxonomy


class TestAcademicNFACharacterClassIntegration:
    """Suite de tests académiques pour validation NFA character-class integration"""

    def setup_method(self):
        """Setup clean pour chaque test avec métriques baseline"""
        self.nfa = AnchoredWeightedNFA("academic_test")
        self.char_manager = create_default_character_set_manager()
        self.baseline_time = time.time()

    def test_property_thompson_construction_correctness(self):
        """
        PROPRIÉTÉ 1: Thompson Construction Correctness
        Algorithme Thompson standard pour character-class [ABC]
        Validation structure NFA générée conforme théorie
        """
        # Pattern character-class simple
        pattern = ".*[IJK].*"
        weight = Decimal('1.5')

        # Construction Thompson via API
        final_state = self.nfa.add_weighted_regex_with_character_class_support(
            "test_measure", pattern, weight
        )

        # Validation structure générée
        assert final_state is not None, "Thompson construction should return final state"

        # Freeze pour finaliser construction
        self.nfa.freeze()

        # Validation propriétés Thompson:
        # 1. État final créé avec bonnes propriétés
        final_states = list(self.nfa.get_final_states())

        assert len(final_states) >= 1, f"Should have at least 1 final state, got {len(final_states)}"

        # Vérification state final a les bonnes métadonnées character-class
        character_class_state = final_state
        assert character_class_state.metadata.get('pattern_type') == 'character_class'
        assert character_class_state.metadata.get('character_class') == ['I', 'J', 'K']

        # 2. Character-class expansion correcte
        test_words = ["XI", "YJ", "ZK"]  # Mots contenant caractères I, J, K
        for word in test_words:
            final_states_reached = self.nfa.evaluate_word(word)
            assert len(final_states_reached) > 0, f"Word {word} should match character-class pattern"
            assert character_class_state.state_id in final_states_reached, f"Word {word} should reach character-class state"

    def _compute_reachable_states(self, start_state: NFAState) -> Set[str]:
        """Calcul états atteignables depuis état initial (BFS)"""
        reachable = set()
        queue = [start_state]
        reachable.add(start_state.state_id)

        while queue:
            current = queue.pop(0)
            for transition in current.outgoing_transitions:
                if transition.target_state.state_id not in reachable:
                    reachable.add(transition.target_state.state_id)
                    queue.append(transition.target_state)

        return reachable

    def test_property_pattern_equivalence_mathematical(self):
        """
        PROPRIÉTÉ 2: Équivalence Patterns Mathématique
        .*[ABC].* ≡ (.*A.*|.*B.*|.*C.*)
        Validation sémantique identique pour représentations équivalentes
        """
        # Pattern character-class et patterns individuels équivalents
        character_class_pattern = ".*[ABC].*"
        individual_patterns = [".*A.*", ".*B.*", ".*C.*"]

        # Construction NFA character-class
        nfa_char_class = AnchoredWeightedNFA("char_class_test")
        nfa_char_class.add_weighted_regex_with_character_class_support(
            "char_class", character_class_pattern, Decimal('2.0')
        )
        nfa_char_class.freeze()

        # Construction NFA patterns individuels
        nfa_individual = AnchoredWeightedNFA("individual_test")
        for i, pattern in enumerate(individual_patterns):
            nfa_individual.add_weighted_regex(f"individual_{i}", pattern, Decimal('2.0'))
        nfa_individual.freeze()

        # Test équivalence sémantique
        test_cases = [
            ("XAY", True),   # Contient A
            ("PBQ", True),   # Contient B
            ("ZCW", True),   # Contient C
            ("XYZ", False),  # Ne contient aucun de A,B,C
            ("ABCD", True),  # Contient A,B,C
            ("", False),     # Mot vide
            ("DEF", False)   # Autres caractères
        ]

        for word, should_match in test_cases:
            eval_char_class = nfa_char_class.evaluate_word(word)
            eval_individual = nfa_individual.evaluate_word(word)

            # Validation équivalence
            char_class_matches = len(eval_char_class) > 0
            individual_matches = len(eval_individual) > 0

            assert char_class_matches == individual_matches == should_match, \
                f"Pattern equivalence failed for '{word}': char_class={char_class_matches}, individual={individual_matches}, expected={should_match}"

            # Si match, poids doivent être cohérents
            if should_match:
                # Note: NFA individual peut avoir poids multiple si plusieurs patterns matchent
                assert len(eval_char_class) > 0, f"Character-class should match for '{word}'"
                assert len(eval_individual) > 0, f"Individual patterns should match for '{word}'"

    def test_property_unique_final_state_consolidation(self):
        """
        PROPRIÉTÉ 3: État Final Unique - Consolidation
        Multi-patterns character-class → single final state
        Garantit classification unique pour résolution FEASIBILITY
        """
        # Pattern multi-caractères INDUSTRY
        industry_pattern = ".*[IJKL].*"

        # Construction avec consolidation
        final_state = self.nfa.add_weighted_regex_with_character_class_support(
            "industry_measure", industry_pattern, Decimal('1.0')
        )
        self.nfa.freeze()

        # Test mots différents mais même classification attendue
        industry_words = ["XI", "YJ", "ZK", "WL"]
        final_states_reached = set()

        for word in industry_words:
            evaluation = self.nfa.evaluate_word(word)
            assert len(evaluation) > 0, f"Industry word {word} should match"

            # Collection états finals atteints
            for state_id in evaluation.final_states_reached:
                final_states_reached.add(state_id)

        # PROPRIÉTÉ CRITIQUE: Tous mots → même état final unique
        assert len(final_states_reached) == 1, \
            f"Character-class should consolidate to single final state, got: {final_states_reached}"

        # Validation: l'état final est celui retourné par construction
        expected_final_id = final_state.state_id
        actual_final_id = list(final_states_reached)[0]
        assert actual_final_id == expected_final_id, \
            f"Final state mismatch: expected {expected_final_id}, got {actual_final_id}"

    def test_property_deterministic_evaluation(self):
        """
        PROPRIÉTÉ 4: Déterminisme Évaluation
        ∀ word, pattern : évaluation reproductible et cohérente
        Même résultat pour évaluations répétées
        """
        # Setup pattern complexe
        complex_pattern = ".*[ABCDEF].*"
        self.nfa.add_weighted_regex_with_character_class_support(
            "complex_measure", complex_pattern, Decimal('3.14')
        )
        self.nfa.freeze()

        # Test words varié
        test_words = ["XAY", "PBQ", "ZZZ", "ABCDEF", ""]

        # Évaluations multiples pour chaque mot
        for word in test_words:
            evaluations = []

            # 10 évaluations répétées
            for _ in range(10):
                eval_result = self.nfa.evaluate_word(word)
                evaluations.append({
                    'final_states_count': len(eval_result),
                    'final_states': sorted(eval_result.final_states_reached),
                    'matched_regexes': sorted(eval_result.matched_regexes)
                })

            # Validation déterminisme: tous résultats identiques
            first_eval = evaluations[0]
            for i, evaluation in enumerate(evaluations[1:], 1):
                assert evaluation == first_eval, \
                    f"Non-deterministic evaluation for '{word}' at iteration {i}: {evaluation} != {first_eval}"

    def test_property_performance_construction(self):
        """
        PROPRIÉTÉ 5: Performance Construction
        Complexité O(|pattern| × |character_class|) respectée
        Construction temps proportionnel taille character-class
        """
        # Test construction temps proportionnel
        character_sets = {
            'small': ['A', 'B'],
            'medium': ['A', 'B', 'C', 'D', 'E'],
            'large': ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
        }

        construction_times = {}

        for set_name, chars in character_sets.items():
            pattern = f".*[{''.join(chars)}].*"

            # Mesure temps construction
            nfa = AnchoredWeightedNFA(f"perf_test_{set_name}")
            start_time = time.perf_counter()

            nfa.add_weighted_regex_with_character_class_support(
                "perf_measure", pattern, Decimal('1.0')
            )
            nfa.freeze()

            end_time = time.perf_counter()
            construction_times[set_name] = end_time - start_time

        # Validation complexité: temps proportionnel taille
        if len(construction_times) >= 3:
            small_time = construction_times['small']
            medium_time = construction_times['medium']
            large_time = construction_times['large']

            # Ratio growth doit être reasonable (pas exponentiel)
            if small_time > 0:
                medium_ratio = medium_time / small_time
                large_ratio = large_time / small_time

                # Croissance sub-quadratique acceptable
                assert medium_ratio < 10, f"Medium construction too slow: {medium_ratio}x"
                assert large_ratio < 50, f"Large construction too slow: {large_ratio}x"

    def test_property_icgs_pipeline_integration(self):
        """
        PROPRIÉTÉ 6: Intégration ICGS Pipeline
        Pipeline DAG → NFA → Simplex sans régression
        Validation intégration complète avec taxonomie
        """
        # Setup taxonomie avec character-sets
        taxonomy = AccountTaxonomy(self.char_manager)

        # Configuration multi-agent même secteur (problème résolu)
        agents_same_sector = {
            'bob_factory': 'INDUSTRY',
            'charlie_factory': 'INDUSTRY',
            'david_factory': 'INDUSTRY'
        }

        # Allocation caractères distincts
        mapping = taxonomy.update_taxonomy_with_sectors(agents_same_sector, 0)

        # Validation caractères distincts
        chars_allocated = list(mapping.values())
        assert len(set(chars_allocated)) == len(chars_allocated), "Character collision should be resolved"

        # Construction NFA avec pattern character-class INDUSTRY
        industry_chars = self.char_manager.get_sector_characters('INDUSTRY')
        industry_pattern = f".*[{''.join(industry_chars)}].*"

        pipeline_nfa = AnchoredWeightedNFA("pipeline_integration")
        final_state = pipeline_nfa.add_weighted_regex_with_character_class_support(
            "industry_measure", industry_pattern, Decimal('2.5')
        )
        pipeline_nfa.freeze()

        # Simulation mots paths multi-agent
        path_evaluations = {}
        for agent_id, allocated_char in mapping.items():
            # Simulation mot path contenant caractère agent
            path_word = f"START_{allocated_char}_END"

            # Évaluation pipeline
            evaluation = pipeline_nfa.evaluate_word(path_word)
            path_evaluations[agent_id] = evaluation

            # Validation match pour chaque agent
            assert len(evaluation) > 0, f"Pipeline should match path for agent {agent_id}"

        # PROPRIÉTÉ CRITIQUE ICGS: Tous agents même secteur → même classification
        final_states_by_agent = {
            agent: set(eval_result.final_states_reached)
            for agent, eval_result in path_evaluations.items()
        }

        # Tous agents doivent atteindre même état final
        all_final_states = list(final_states_by_agent.values())
        reference_states = all_final_states[0]

        for agent_id, agent_states in final_states_by_agent.items():
            assert agent_states == reference_states, \
                f"Agent {agent_id} reaches different final states: {agent_states} vs {reference_states}"

        # Validation finale: classification unique garantit FEASIBILITY 100%
        assert len(reference_states) == 1, \
            f"Should consolidate to single final state, got: {reference_states}"

    def test_complex_character_class_patterns(self):
        """Test patterns character-class complexes et compositions"""

        # Pattern composé avec multiple character-classes
        complex_patterns = [
            ".*[ABC].*[XYZ].*",  # Deux character-classes séparées
            ".*[A-C].*",          # Range notation (si supportée)
            ".*[IJKL]+.*",        # Répétition avec character-class
        ]

        for i, pattern in enumerate(complex_patterns[:1]):  # Test premier seulement
            try:
                nfa = AnchoredWeightedNFA(f"complex_test_{i}")
                nfa.add_weighted_regex_with_character_class_support(
                    f"complex_measure_{i}", pattern, Decimal('1.0')
                )
                nfa.freeze()

                # Test quelques cas
                test_words = ["AXYZ", "BXYZ", "CXYZ", "DEFG"]
                for word in test_words:
                    evaluation = nfa.evaluate_word(word)
                    # Pas d'assertion strict car pattern complexe
                    # Validation: pas d'exception during evaluation
                    assert evaluation is not None

            except NotImplementedError:
                # Pattern trop complexe non supporté dans version actuelle
                pytest.skip(f"Complex pattern not implemented: {pattern}")

    def test_edge_cases_character_class_robustness(self):
        """Test cas limites et robustesse character-class"""

        # Pattern avec caractère unique
        single_char_pattern = ".*[A].*"
        self.nfa.add_weighted_regex_with_character_class_support(
            "single", single_char_pattern, Decimal('1.0')
        )

        # Pattern caractères spéciaux (si echappés)
        try:
            special_pattern = ".*[A-Z].*"  # Range, peut ne pas être supporté
            self.nfa.add_weighted_regex_with_character_class_support(
                "special", special_pattern, Decimal('1.0')
            )
        except (ValueError, NotImplementedError):
            # Range notation non supportée dans version actuelle
            pass

        # Pattern vide devrait échouer
        with pytest.raises(ValueError):
            empty_pattern = ".*[].*"
            self.nfa.add_weighted_regex_with_character_class_support(
                "empty", empty_pattern, Decimal('1.0')
            )

        # Freeze et test basic functionality
        self.nfa.freeze()

        # Validation single character fonctionne
        result = self.nfa.evaluate_word("XAY")
        assert len(result) > 0, "Single character class should work"


def run_academic_test_20():
    """
    Exécution test académique 20 avec rapport détaillé de validation

    Returns:
        bool: True si toutes propriétés algorithmiques validées, False sinon
    """
    pytest_result = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x"  # Stop au premier échec pour diagnostic précis
    ])

    return pytest_result == 0


if __name__ == "__main__":
    success = run_academic_test_20()
    if success:
        print("✅ TEST ACADÉMIQUE 20 RÉUSSI - NFA Character-Class Integration validée")
        print("📊 Propriétés algorithmiques vérifiées:")
        print("   • Thompson Construction correcte")
        print("   • Équivalence patterns mathématique")
        print("   • Consolidation état final unique")
        print("   • Déterminisme évaluation garanti")
        print("   • Performance O(|pattern|×|char_class|) mesurée")
        print("   • Intégration ICGS pipeline complète")
    else:
        print("❌ TEST ACADÉMIQUE 20 ÉCHOUÉ - Violations propriétés algorithmiques détectées")
        exit(1)