"""
Test Académique 2: Validation Construction NFA - Déterminisme et Propriétés

Ce test vérifie rigoureusement les propriétés mathématiques fondamentales
de la construction d'automates finis pondérés selon le blueprint ICGS.

Propriétés testées:
1. Déterminisme: Construction reproductible et cohérente
2. Structure NFA: États, transitions, et alphabet corrects
3. Évaluation correcte: Algorithme NFA standard conforme
4. Poids regex: Association et extraction correctes
5. Performance construction: Complexité O(R×S) respectée
6. Robustesse: Gestion erreurs et cas limites

Niveau académique: Validation formelle des algorithmes NFA/regex
"""

import pytest
import time
from decimal import Decimal
from typing import Dict, List, Set

# Import des modules à tester
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_core.weighted_nfa import (
    WeightedNFA, RegexWeight, NFAState, NFATransition, TransitionType, 
    create_simple_test_nfa
)
from icgs_core.anchored_nfa import AnchoredWeightedNFA, create_anchored_test_nfa


class TestAcademicNFADeterminism:
    """Suite de tests académiques pour validation construction NFA déterministe"""

    def setup_method(self):
        """Setup clean pour chaque test avec métriques baseline"""
        self.nfa_basic = WeightedNFA("test_nfa")
        self.nfa_anchored = AnchoredWeightedNFA("test_anchored_nfa")
        self.baseline_time = time.time()
        
    def test_deterministic_nfa_construction(self):
        """
        PROPRIÉTÉ 1: Déterminisme Construction
        ∀ inputs identiques : construction NFA → résultat identique
        """
        # Construction identique répétée
        construction_results = []
        
        for i in range(5):
            nfa = WeightedNFA(f"test_{i}")
            
            # Ajout états identiques
            nfa.add_state("q0")
            nfa.add_state("q1", is_final=True)
            nfa.set_initial_state("q0")
            
            # Transition identique
            transition = nfa.add_transition("q0", "q1", "test", TransitionType.CHARACTER)
            
            # Extraction signature pour comparaison
            signature = {
                'states_count': len(nfa.states),
                'transitions_count': len(nfa.transitions),
                'initial_state': nfa.initial_state_id,
                'final_states_count': len(nfa.get_final_states()),
                'transition_condition': transition.condition
            }
            
            construction_results.append(signature)
        
        # Vérification déterminisme: tous résultats identiques
        first_result = construction_results[0]
        for result in construction_results[1:]:
            assert result == first_result, f"Construction non-déterministe détectée: {result} != {first_result}"
    
    def test_nfa_structure_validation(self):
        """
        PROPRIÉTÉ 2: Structure NFA Correcte
        États, transitions, alphabet selon spécifications formelles
        """
        # Construction NFA de test structuré
        nfa = create_simple_test_nfa()
        
        # Validation structure de base
        assert len(nfa.states) == 3, f"Expected 3 states, got {len(nfa.states)}"
        assert nfa.initial_state_id == "q0", f"Initial state incorrect: {nfa.initial_state_id}"
        
        final_states = nfa.get_final_states()
        assert len(final_states) == 1, f"Expected 1 final state, got {len(final_states)}"
        assert final_states[0].state_id == "q2", f"Final state incorrect: {final_states[0].state_id}"
        
        # Validation transitions
        assert len(nfa.transitions) == 2, f"Expected 2 transitions, got {len(nfa.transitions)}"
        
        # Vérification alphabet automatiquement déduit
        expected_alphabet = {'a', 'b'}
        assert nfa.alphabet == expected_alphabet, f"Alphabet incorrect: {nfa.alphabet}"
        
        # Validation structure via méthode intégrée
        validation_errors = nfa.validate_nfa_structure()
        assert len(validation_errors) == 0, f"Structure validation failed: {validation_errors}"
    
    def test_nfa_evaluation_correctness(self):
        """
        PROPRIÉTÉ 3: Évaluation Correcte
        Algorithme NFA standard avec gestion non-déterminisme

        FALLBACK API USAGE: Ce test utilise evaluate_word() (FALLBACK API) pour valider
        le comportement fondamental de l'évaluation NFA. L'API fallback est appropriée ici
        car elle teste directement la logique interne de navigation états/transitions,
        indépendamment des optimisations pipeline de l'API primaire evaluate_to_final_state().
        """
        # NFA de test: q0 -'a'-> q1 -'b'-> q2(final)
        nfa = create_simple_test_nfa()
        
        # Tests évaluation mots acceptés
        accepted_words = ["ab"]
        for word in accepted_words:
            final_states = nfa.evaluate_word(word)
            print(f"   🔄 FALLBACK API: evaluate_word('{word}') → {len(final_states)} states")
            assert len(final_states) == 1, f"Word '{word}' should reach exactly 1 final state, got {len(final_states)}"
            assert "q2" in final_states, f"Word '{word}' should reach state q2, got {final_states}"
        
        # Tests évaluation mots rejetés
        rejected_words = ["", "a", "b", "ba", "abc", "abb", "aab"]
        for word in rejected_words:
            final_states = nfa.evaluate_word(word)
            print(f"   🔄 FALLBACK API: evaluate_word('{word}') → {len(final_states)} states (rejected)")
            assert len(final_states) == 0, f"Word '{word}' should be rejected, but reached {final_states}"
        
        # Vérification métriques évaluation
        initial_evaluations = nfa.stats['evaluations_performed']
        nfa.evaluate_word("test_word")
        assert nfa.stats['evaluations_performed'] == initial_evaluations + 1, "Evaluation metrics not updated"
    
    def test_regex_weights_association(self):
        """
        PROPRIÉTÉ 4: Association Poids Regex Correcte
        RegexWeight correctement associés aux états finaux
        """
        # Construction NFA avec poids regex
        nfa = WeightedNFA("weighted_test")
        
        # Ajout pattern avec poids
        test_weight = Decimal('2.5')
        final_state = nfa.add_weighted_regex_simple(
            measure_id="test_measure",
            regex_pattern="test.*",
            weight=test_weight,
            regex_id="test_regex"
        )
        
        # Validation RegexWeight associé
        assert len(final_state.regex_weights) == 1, f"Expected 1 regex weight, got {len(final_state.regex_weights)}"
        
        regex_weight = final_state.regex_weights[0]
        assert regex_weight.measure_id == "test_measure"
        assert regex_weight.regex_id == "test_regex"
        assert regex_weight.weight == test_weight
        
        # Validation extraction poids par état
        weights = nfa.get_regex_weights_for_state(final_state.state_id)
        assert len(weights) == 1
        assert weights[0] == regex_weight
        
        # Test état non-existant
        empty_weights = nfa.get_regex_weights_for_state("non_existent")
        assert len(empty_weights) == 0
    
    def test_construction_performance_complexity(self):
        """
        PROPRIÉTÉ 5: Performance Construction O(R×S)
        Complexité temporelle proportionnelle à regex×états
        """
        # Test scalabilité construction
        pattern_counts = [5, 10, 20]
        construction_times = []
        
        for pattern_count in pattern_counts:
            nfa = WeightedNFA(f"perf_test_{pattern_count}")
            
            start_time = time.perf_counter()
            
            # Construction patterns multiples
            for i in range(pattern_count):
                nfa.add_weighted_regex_simple(
                    measure_id=f"measure_{i}",
                    regex_pattern=f"pattern_{i}",
                    weight=Decimal('1.0'),
                    regex_id=f"regex_{i}"
                )
            
            end_time = time.perf_counter()
            construction_time = end_time - start_time
            construction_times.append(construction_time)
        
        # Vérification croissance sub-quadratique (approximation O(R×S))
        if len(construction_times) >= 2:
            # Ratio croissance ne doit pas être quadratique
            time_ratio = construction_times[-1] / construction_times[0]
            pattern_ratio = pattern_counts[-1] / pattern_counts[0]
            
            # Pour O(R×S), ratio temporel ≈ ratio patterns (linéaire pour S constant)
            assert time_ratio < pattern_ratio * 2, f"Construction time growth too high: {time_ratio} vs pattern ratio {pattern_ratio}"
    
    def test_error_handling_robustness(self):
        """
        PROPRIÉTÉ 6: Robustesse Gestion Erreurs
        Gestion correcte cas limites et erreurs
        """
        nfa = WeightedNFA("error_test")
        
        # Test état déjà existant
        nfa.add_state("duplicate_test")
        with pytest.raises(ValueError, match="already exists"):
            nfa.add_state("duplicate_test")
        
        # Test transition avec états non-existants
        with pytest.raises(ValueError, match="not found"):
            nfa.add_transition("non_existent", "q1", "a")
            
        with pytest.raises(ValueError, match="not found"):
            nfa.add_transition("q1", "non_existent", "a")
        
        # Test état initial non-existant
        with pytest.raises(ValueError, match="not found"):
            nfa.set_initial_state("non_existent")
        
        # Test regex invalide
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            nfa.add_weighted_regex_simple("test", "[", Decimal('1.0'))  # Regex invalide
        
        # Test RegexWeight paramètres invalides
        with pytest.raises(ValueError, match="cannot be empty"):
            RegexWeight("", "test", Decimal('1.0'))
        
        with pytest.raises(ValueError, match="cannot be empty"):
            RegexWeight("test", "", Decimal('1.0'))
        
        with pytest.raises(ValueError, match="cannot be None"):
            RegexWeight("test", "test", None)
    
    def test_anchored_nfa_automatic_anchoring(self):
        """
        PROPRIÉTÉ 7: Ancrage Automatique AnchoredWeightedNFA
        Transformation automatique patterns → ".*pattern$"
        """
        anchored_nfa = AnchoredWeightedNFA("anchoring_test")
        
        # Test ancrage automatique
        original_pattern = "test"
        final_state = anchored_nfa.add_weighted_regex(
            measure_id="test_measure",
            regex_pattern=original_pattern,
            weight=Decimal('1.0')
        )
        
        # Vérification transformation automatique
        assert 'original_pattern' in final_state.metadata
        assert 'anchored_pattern' in final_state.metadata
        assert 'was_anchored' in final_state.metadata
        
        assert final_state.metadata['original_pattern'] == original_pattern
        assert final_state.metadata['anchored_pattern'] == f".*{original_pattern}$"
        assert final_state.metadata['was_anchored'] is True
        
        # Test pattern déjà ancré (ne doit pas être modifié)
        already_anchored = "test$"
        final_state_2 = anchored_nfa.add_weighted_regex(
            measure_id="test_measure_2", 
            regex_pattern=already_anchored,
            weight=Decimal('2.0')
        )
        
        assert final_state_2.metadata['original_pattern'] == already_anchored
        assert final_state_2.metadata['anchored_pattern'] == already_anchored
        assert final_state_2.metadata['was_anchored'] is False
        
        # Vérification statistiques ancrage
        assert anchored_nfa.stats['patterns_anchored'] == 1
        assert anchored_nfa.stats['anchor_transformations'] == 1
    
    def test_frozen_state_mechanism(self):
        """
        PROPRIÉTÉ 8: Mécanisme Frozen State
        Cohérence temporelle avec freeze/unfreeze

        PRIMARY API USAGE: Ce test utilise evaluate_to_final_state() (PRIMARY API) car c'est
        l'API optimisée pour le pipeline ICGS qui gère nativement les frozen states.
        L'API primaire utilise les snapshots frozen pour cohérence temporelle, tandis que
        l'API fallback evaluate_word() ne garantit pas cette cohérence lors énumération.
        """
        anchored_nfa = AnchoredWeightedNFA("frozen_test")
        
        # Construction initiale
        anchored_nfa.add_weighted_regex("measure1", "pattern1", Decimal('1.0'))
        anchored_nfa.add_weighted_regex("measure2", "pattern2", Decimal('2.0'))
        
        # État avant freeze
        initial_final_count = len(anchored_nfa.get_final_states())
        initial_transitions_count = len(anchored_nfa.transitions)
        
        # Freeze NFA
        assert not anchored_nfa.is_frozen
        anchored_nfa.freeze()
        assert anchored_nfa.is_frozen
        
        # Vérification snapshot frozen
        frozen_info = anchored_nfa.get_frozen_state_info()
        assert frozen_info['is_frozen'] is True
        assert frozen_info['frozen_final_states_count'] == initial_final_count
        assert frozen_info['frozen_transitions_count'] == initial_transitions_count
        assert frozen_info['freeze_operations_total'] == 1
        
        # Test modification interdite pendant frozen
        with pytest.raises(RuntimeError, match="Cannot modify frozen"):
            anchored_nfa.add_weighted_regex("blocked", "blocked", Decimal('1.0'))
        
        # Test évaluation avec frozen state
        word_test = "somepattern1"
        result_frozen = anchored_nfa.evaluate_to_final_state(word_test)
        print(f"   🎯 PRIMARY API: evaluate_to_final_state('{word_test}') → {result_frozen}")
        
        # Unfreeze et vérification état restauré
        anchored_nfa.unfreeze()
        assert not anchored_nfa.is_frozen
        
        # Modification possible après unfreeze
        anchored_nfa.add_weighted_regex("measure3", "pattern3", Decimal('3.0'))
        assert len(anchored_nfa.get_final_states()) == initial_final_count + 1
    
    def test_nfa_comprehensive_integration(self):
        """
        META-PROPRIÉTÉ: Intégration Complète NFA
        Test end-to-end avec toutes fonctionnalités
        """
        # Construction NFA complexe multi-patterns
        nfa = AnchoredWeightedNFA("integration_test")
        
        patterns = [
            ("agriculture", "A.*", Decimal('1.2')),
            ("industry", "I.*", Decimal('0.9')), 
            ("services", "S.*", Decimal('1.1')),
            ("carbon_penalty", ".*carbon.*", Decimal('-0.5'))
        ]
        
        for measure_id, pattern, weight in patterns:
            nfa.add_weighted_regex(measure_id, pattern, weight)
        
        # Validation structure complète
        validation_errors = nfa.validate_anchored_nfa_properties()
        assert len(validation_errors) == 0, f"Integration validation failed: {validation_errors}"
        
        # Test évaluation mots multiples
        test_cases = [
            ("Agriculture_account", True),  # Match A.*
            ("Industry_factory", True),     # Match I.*
            ("Services_bank", True),        # Match S.*
            ("carbon_agriculture", True),   # Match .*carbon.* et A.*
            ("random_account", False),      # Aucun match
        ]
        
        for word, should_match in test_cases:
            result = nfa.evaluate_to_final_state(word)
            match_status = "MATCH" if result is not None else "NO_MATCH"
            print(f"   🎯 PRIMARY API: evaluate_to_final_state('{word}') → {match_status}")
            if should_match:
                assert result is not None, f"Word '{word}' should match but didn't"
            else:
                assert result is None, f"Word '{word}' shouldn't match but did: {result}"
        
        # Test extraction classifications pour LP
        classifications = nfa.get_final_state_classifications()
        assert len(classifications) > 0, "No classifications extracted"
        
        # Vérification poids par mesure
        agri_weights = nfa.get_state_weights_for_measure("agriculture")
        assert len(agri_weights) > 0, "Agriculture measure weights not found"


def run_academic_test_2():
    """
    Exécution test académique 2 avec rapport détaillé de validation
    
    Returns:
        bool: True si tous propriétés NFA validées, False sinon
    """
    pytest_result = pytest.main([
        __file__,
        "-v", 
        "--tb=short",
        "-x"  # Stop au premier échec pour diagnostic précis
    ])
    
    return pytest_result == 0


if __name__ == "__main__":
    success = run_academic_test_2()
    if success:
        print("✅ TEST ACADÉMIQUE 2 RÉUSSI - Construction NFA déterministe validée")
        print("📊 Propriétés mathématiques vérifiées:")
        print("   • Déterminisme construction reproductible")
        print("   • Structure NFA formellement correcte")
        print("   • Évaluation algorithme standard conforme")
        print("   • Association poids regex validée")
        print("   • Complexité O(R×S) respectée")
        print("   • Ancrage automatique fonctionnel")
        print("   • Mécanisme frozen state opérationnel")
        print("   • Intégration complète end-to-end")
    else:
        print("❌ TEST ACADÉMIQUE 2 ÉCHOUÉ - Violations propriétés NFA détectées")
        exit(1)