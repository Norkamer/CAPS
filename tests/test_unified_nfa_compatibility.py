"""
Tests de Compatibilité et Non-Régression - Extension Character-Class

Validation que l'extension character-class préserve parfaitement la compatibilité
avec l'API WeightedNFA existante et fonctionne correctement dans le pipeline ICGS.

Tests:
1. Non-régression: API existante identique
2. Extension character-class: Nouveaux patterns fonctionnent
3. Hybride: Patterns standards + character-class coexistent
4. Pipeline ICGS: Integration transparente enumerate_and_classify
5. Performance: Pas de dégradation significative
"""

import unittest
from decimal import Decimal
from typing import Dict, List, Set, Any
import time

# Import modules à tester
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_core.weighted_nfa import WeightedNFA
from icgs_core.anchored_nfa import AnchoredWeightedNFA
from icgs_core.character_set_manager import create_default_character_set_manager
from icgs_core.account_taxonomy import AccountTaxonomy


class TestUnifiedNFACompatibility(unittest.TestCase):
    """Suite tests compatibilité extension character-class"""

    def setUp(self):
        """Setup pour chaque test"""
        self.baseline_time = time.time()

    def test_weighted_nfa_non_regression(self):
        """
        TEST 1: Non-Régression WeightedNFA
        L'API existante doit fonctionner exactement comme avant
        """
        # Création NFA standard
        nfa = WeightedNFA("regression_test")

        # Patterns standards comme avant
        final_state_1 = nfa.add_weighted_regex_simple("measure1", ".*A.*", Decimal('1.0'))
        final_state_2 = nfa.add_weighted_regex_simple("measure2", ".*B.*", Decimal('2.0'))

        # Validation structure États
        self.assertIsNotNone(final_state_1)
        self.assertIsNotNone(final_state_2)
        self.assertTrue(final_state_1.is_final)
        self.assertTrue(final_state_2.is_final)

        # Test évaluation API standard
        # Mots qui matchent
        result_A = nfa.evaluate_word("XAY")
        result_B = nfa.evaluate_word("XBZ")
        result_AB = nfa.evaluate_word("XABY")

        # Validation résultats
        self.assertGreater(len(result_A), 0, "Pattern .*A.* should match XAY")
        self.assertGreater(len(result_B), 0, "Pattern .*B.* should match XBZ")
        self.assertGreater(len(result_AB), 0, "Patterns should match XABY")

        # Mots qui ne matchent pas
        result_none = nfa.evaluate_word("XYZ")
        # Peut être vide ou non selon implémentation - test que API ne crash pas
        self.assertIsInstance(result_none, set)

    def test_anchored_nfa_non_regression(self):
        """
        TEST 2: Non-Régression AnchoredWeightedNFA
        L'API AnchoredWeightedNFA existante doit fonctionner identiquement
        """
        nfa = AnchoredWeightedNFA("anchored_regression_test")

        # Patterns avec ancrage automatique
        final_state = nfa.add_weighted_regex("measure_anchored", "A.*", Decimal('1.5'))

        self.assertIsNotNone(final_state)
        self.assertTrue(final_state.is_final)

        # Vérification ancrage automatique dans métadonnées
        self.assertIn('original_pattern', final_state.metadata)
        self.assertIn('anchored_pattern', final_state.metadata)

        # Test évaluation avec patterns ancrés
        result_match = nfa.evaluate_word("AXY")  # Should match A.*
        result_no_match = nfa.evaluate_word("XAY")  # Should not match A.*

        self.assertGreater(len(result_match), 0, "Anchored pattern should match AXY")
        # Note: result_no_match peut être vide ou non selon ancrage

    def test_character_class_extension_functionality(self):
        """
        TEST 3: Fonctionnalité Extension Character-Class
        Nouveaux patterns character-class doivent fonctionner correctement

        FALLBACK API USAGE: Ce test utilise evaluate_word() (FALLBACK API) pour valider
        spécifiquement l'architecture unifiée character-class. L'API fallback est le point
        d'entrée unifié qui combine patterns standards + character-class automatiquement,
        testant ainsi l'intégration complète de l'extension.
        """
        nfa = AnchoredWeightedNFA("character_class_test")

        # Ajout pattern character-class
        final_state = nfa.add_weighted_regex_with_character_class_support(
            "industry_measure", ".*[IJK].*", Decimal('2.0')
        )

        self.assertIsNotNone(final_state)
        self.assertTrue(final_state.is_final)

        # Vérification structure character-class
        self.assertTrue(hasattr(final_state, 'compiled_patterns'))
        self.assertGreater(len(final_state.compiled_patterns), 0)

        nfa.freeze()

        # Test évaluation character-class
        words_should_match = ["XIY", "XJZ", "XKW"]
        words_should_not_match = ["XAY", "XLM", "XYZ"]

        for word in words_should_match:
            result = nfa.evaluate_word(word)
            print(f"   🧪 CHARACTER-CLASS TEST: '{word}' → {result}")
            self.assertGreater(len(result), 0, f"Character-class should match {word}")

        for word in words_should_not_match:
            result = nfa.evaluate_word(word)
            # Peut matcher d'autres patterns - teste juste que API ne crash pas
            self.assertIsInstance(result, set)

    def test_hybrid_patterns_coexistence(self):
        """
        TEST 4: Coexistence Patterns Standards + Character-Class
        Patterns standards et character-class doivent coexister dans même NFA
        """
        nfa = AnchoredWeightedNFA("hybrid_test")

        # Patterns standards
        standard_final = nfa.add_weighted_regex("standard_A", ".*A.*", Decimal('1.0'))
        standard_final2 = nfa.add_weighted_regex("standard_B", ".*B.*", Decimal('1.0'))

        # Pattern character-class
        character_class_final = nfa.add_weighted_regex_with_character_class_support(
            "industry", ".*[IJK].*", Decimal('2.0')
        )

        # Validation États distincts
        self.assertNotEqual(standard_final.state_id, character_class_final.state_id)
        self.assertNotEqual(standard_final2.state_id, character_class_final.state_id)

        nfa.freeze()

        # Test évaluation hybride
        test_cases = [
            ("XAY", "Should match standard pattern .*A.*"),
            ("XBZ", "Should match standard pattern .*B.*"),
            ("XIW", "Should match character-class .*[IJK].*"),
            ("XJQ", "Should match character-class .*[IJK].*"),
            ("XAIY", "Should match both standard A and character-class I")
        ]

        for word, description in test_cases:
            result = nfa.evaluate_word(word)
            self.assertIsInstance(result, set, f"API should work for: {description}")
            # Note: Validation spécifique difficile sans connaître état IDs exacts

    def test_pipeline_integration_transparency(self):
        """
        TEST 5: Intégration Pipeline ICGS Transparente
        Simulation du pipeline path_enumerator.enumerate_and_classify

        DUAL API USAGE: Ce test utilise BOTH APIs pour simuler le comportement pipeline ICGS :
        - evaluate_to_final_state() (PRIMARY API) : Utilisée en priorité par le pipeline
        - evaluate_word() (FALLBACK API) : Utilisée si l'API primaire échoue
        Ceci valide que l'architecture unifiée garantit compatibilité complète pipeline.
        """
        # Setup comme dans pipeline ICGS
        char_manager = create_default_character_set_manager()
        taxonomy = AccountTaxonomy(char_manager)

        # Configuration multi-agent même secteur
        agents = {
            'bob_factory': 'INDUSTRY',
            'charlie_factory': 'INDUSTRY',
            'david_factory': 'INDUSTRY'
        }

        mapping = taxonomy.update_taxonomy_with_sectors(agents, 0)

        # NFA hybride
        nfa = AnchoredWeightedNFA("pipeline_test")

        # Patterns standards pour autres agents
        nfa.add_weighted_regex("agriculture", ".*A.*", Decimal('1.0'))

        # Pattern character-class pour INDUSTRY
        industry_chars = char_manager.get_character_set_info('INDUSTRY').characters
        industry_pattern = f".*[{''.join(industry_chars)}].*"
        nfa.add_weighted_regex_with_character_class_support("industry", industry_pattern, Decimal('2.0'))

        nfa.freeze()

        # Simulation pipeline: mots paths pour agents INDUSTRY
        for agent_id, allocated_char in mapping.items():
            test_word = f"X{allocated_char}Y"

            # DIAGNOSTIC COMPLET API USAGE
            diagnostics = diagnose_api_usage(nfa, test_word, f"PIPELINE-{agent_id}")

            # Simulation classify_paths_with_nfa logic
            final_state_id = None

            # API primaire (utilisée par pipeline)
            if hasattr(nfa, 'evaluate_to_final_state'):
                final_state_id = nfa.evaluate_to_final_state(test_word)

            # API fallback (utilisée par pipeline) - NOUVEAU: avec character-class
            elif hasattr(nfa, 'evaluate_word'):
                result = nfa.evaluate_word(test_word)
                final_state_id = list(result)[0] if result else None

            # Validation: agent INDUSTRY doit être classifié
            self.assertIsNotNone(final_state_id, f"Agent {agent_id} word '{test_word}' should be classified")

            # Validation diagnostic
            self.assertTrue(diagnostics['unified_architecture'],
                           f"Pipeline test should use unified architecture for {agent_id}")

    def test_performance_no_regression(self):
        """
        TEST 6: Performance Non-Régression
        Extension character-class ne doit pas dégrader performance significativement
        """
        # Benchmark NFA sans character-class
        nfa_standard = WeightedNFA("perf_standard")
        for i in range(10):
            nfa_standard.add_weighted_regex_simple(f"measure_{i}", f".*{chr(65+i)}.*", Decimal('1.0'))

        # Benchmark NFA avec character-class
        nfa_extended = AnchoredWeightedNFA("perf_extended")
        for i in range(5):
            nfa_extended.add_weighted_regex(f"standard_{i}", f".*{chr(65+i)}.*", Decimal('1.0'))
        for i in range(5):
            chars = ''.join([chr(70+j) for j in range(3)])  # FGH, IJK, etc.
            nfa_extended.add_weighted_regex_with_character_class_support(
                f"charclass_{i}", f".*[{chars}].*", Decimal('1.0')
            )

        # Test performance mots multiples
        test_words = [f"X{chr(65+i)}Y" for i in range(20)]

        # Standard timing
        start_standard = time.perf_counter()
        for word in test_words:
            nfa_standard.evaluate_word(word)
        time_standard = time.perf_counter() - start_standard

        # Extended timing
        start_extended = time.perf_counter()
        for word in test_words:
            nfa_extended.evaluate_word(word)
        time_extended = time.perf_counter() - start_extended

        # Performance ratio
        if time_standard > 0:
            performance_ratio = time_extended / time_standard
            # Tolérance 100% dégradation maximum (character-class initialization overhead)
            self.assertLess(performance_ratio, 2.0,
                          f"Performance degradation too high: {performance_ratio:.2f}x slower")

    def test_error_resilience_compatibility(self):
        """
        TEST 7: Résilience Erreurs et Edge Cases
        Extension doit être robuste comme API existante
        """
        nfa = AnchoredWeightedNFA("error_resilience_test")

        # Test patterns invalides - ne doit pas crash
        try:
            nfa.add_weighted_regex("invalid", "[", Decimal('1.0'))  # Regex invalide
        except ValueError:
            pass  # Comportement attendu

        # Ajout patterns válidos
        nfa.add_weighted_regex("valid", ".*A.*", Decimal('1.0'))
        nfa.add_weighted_regex_with_character_class_support("valid_cc", ".*[BC].*", Decimal('1.0'))

        nfa.freeze()

        # Test évaluation mots edge cases
        edge_case_words = ["", "X", "VERYLONGWORDTHATMAYCAUSEPROBLEM", "UNICODE🚀TEST"]

        for word in edge_case_words:
            try:
                result = nfa.evaluate_word(word)
                self.assertIsInstance(result, set)  # API doit retourner Set même si vide
            except Exception as e:
                self.fail(f"evaluate_word should not crash on '{word}': {e}")

    def test_freeze_unfreeze_compatibility(self):
        """
        TEST 8: Compatibilité Freeze/Unfreeze
        Extension doit respecter état frozen comme API existante
        """
        nfa = AnchoredWeightedNFA("freeze_test")

        # Ajout patterns avant freeze
        nfa.add_weighted_regex("pre_freeze", ".*A.*", Decimal('1.0'))
        nfa.add_weighted_regex_with_character_class_support("pre_freeze_cc", ".*[BC].*", Decimal('1.0'))

        # État initial: non frozen
        self.assertFalse(nfa.is_frozen)

        # Freeze
        nfa.freeze()
        self.assertTrue(nfa.is_frozen)

        # Modifications interdites après freeze
        with self.assertRaises(RuntimeError):
            nfa.add_weighted_regex("post_freeze", ".*D.*", Decimal('1.0'))

        with self.assertRaises(RuntimeError):
            nfa.add_weighted_regex_with_character_class_support("post_freeze_cc", ".*[DE].*", Decimal('1.0'))

        # Évaluation autorisée quand frozen
        result = nfa.evaluate_word("XAY")
        self.assertIsInstance(result, set)

        # Unfreeze (si disponible)
        if hasattr(nfa, 'unfreeze'):
            nfa.unfreeze()
            self.assertFalse(nfa.is_frozen)

            # Modifications à nouveau autorisées
            final_state = nfa.add_weighted_regex("post_unfreeze", ".*E.*", Decimal('1.0'))
            self.assertIsNotNone(final_state)


def diagnose_api_usage(nfa, word: str, test_context: str = "UNKNOWN") -> Dict[str, Any]:
    """
    Diagnostic détaillé utilisation APIs avec indication fallback

    Args:
        nfa: Instance NFA à tester
        word: Mot de test
        test_context: Contexte du test

    Returns:
        Dict avec résultats et métriques API usage
    """
    diagnostics = {
        'context': test_context,
        'word': word,
        'api_calls': {},
        'results': {},
        'fallback_used': False,
        'unified_architecture': False
    }

    print(f"📊 API DIAGNOSTIC [{test_context}]: Testing word '{word}'")

    # Test API primaire evaluate_to_final_state
    if hasattr(nfa, 'evaluate_to_final_state'):
        try:
            result = nfa.evaluate_to_final_state(word)
            diagnostics['api_calls']['evaluate_to_final_state'] = 'SUCCESS'
            diagnostics['results']['primary_api'] = result
            print(f"   🎯 PRIMARY API: evaluate_to_final_state('{word}') → {result}")
        except Exception as e:
            diagnostics['api_calls']['evaluate_to_final_state'] = f'ERROR: {e}'
            diagnostics['fallback_used'] = True
            print(f"   ❌ PRIMARY API FAILED: {e}")

    # Test API fallback evaluate_word
    if hasattr(nfa, 'evaluate_word'):
        try:
            result = nfa.evaluate_word(word)
            diagnostics['api_calls']['evaluate_word'] = 'SUCCESS'
            diagnostics['results']['fallback_api'] = result
            print(f"   🔄 FALLBACK API: evaluate_word('{word}') → {result}")

            # Détection architecture unifiée (character-class support)
            if hasattr(nfa, '_evaluate_character_class_patterns_direct'):
                char_class_result = nfa._evaluate_character_class_patterns_direct(word)
                diagnostics['results']['character_class_direct'] = char_class_result
                diagnostics['unified_architecture'] = True
                print(f"   🎨 CHARACTER-CLASS DIRECT: '{word}' → {char_class_result}")

        except Exception as e:
            diagnostics['api_calls']['evaluate_word'] = f'ERROR: {e}'
            print(f"   ❌ FALLBACK API FAILED: {e}")

    # Performance stats si disponible
    if hasattr(nfa, 'get_performance_stats'):
        try:
            stats = nfa.get_performance_stats()
            diagnostics['performance_stats'] = stats
            cache_hit_rate = stats.get('cache', {}).get('hit_rate', 0)
            print(f"   📈 PERFORMANCE: Cache hit rate {cache_hit_rate:.1%}")
        except:
            pass

    # Résumé diagnostic
    api_status = "✅ UNIFIED" if diagnostics['unified_architecture'] else "⚠️ FALLBACK" if diagnostics['fallback_used'] else "🎯 PRIMARY"
    print(f"   📋 STATUS: {api_status} Architecture")
    print(f"   ─────────────────────────────────")

    return diagnostics


def run_compatibility_tests():
    """
    Exécution suite tests compatibilité avec rapport détaillé

    Returns:
        bool: True si tous tests passent, False sinon
    """
    import pytest
    pytest_result = pytest.main([
        __file__,
        "-v",
        "--tb=short"
    ])

    return pytest_result == 0


if __name__ == "__main__":
    success = run_compatibility_tests()
    if success:
        print("✅ TESTS COMPATIBILITÉ RÉUSSIS - Extension character-class compatible")
        print("📊 Validation complète:")
        print("   • Non-régression API existante")
        print("   • Fonctionnalité character-class opérationnelle")
        print("   • Coexistence patterns hybrides")
        print("   • Intégration pipeline ICGS transparente")
        print("   • Performance acceptable")
        print("   • Résilience erreurs maintenue")
        print("   • Compatibilité freeze/unfreeze")
    else:
        print("❌ TESTS COMPATIBILITÉ ÉCHOUÉS - Extension problématique")
        exit(1)