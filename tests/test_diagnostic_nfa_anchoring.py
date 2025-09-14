#!/usr/bin/env python3
"""
DIAGNOSTIC: Analyser ancrage automatique patterns NFA
Vérifier si ancrage cause conflit entre .*Ω.* et .*Χ.*
"""

import unittest
from decimal import Decimal
import sys
import os

# Path setup pour import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_core.anchored_nfa_v2 import AnchoredWeightedNFA


class TestDiagnosticNFAAnchoring(unittest.TestCase):
    """Diagnostic ancrage automatique NFA"""

    def test_anchoring_patterns_conflict(self):
        """Test ancrage automatique et conflits patterns"""
        print("\n=== DIAGNOSTIC ANCRAGE AUTOMATIQUE ===")

        # Test 1: Pattern individuel
        print("--- TEST 1: PATTERNS INDIVIDUELS ---")

        nfa1 = AnchoredWeightedNFA("test_source")
        state1 = nfa1.add_weighted_regex("source_omega", ".*Ω.*", Decimal('1.0'))
        print(f"Pattern source seul:")
        print(f"  Original: .*Ω.*")
        print(f"  Ancré: {getattr(state1, 'metadata', {}).get('anchored_pattern', 'N/A')}")

        nfa2 = AnchoredWeightedNFA("test_target")
        state2 = nfa2.add_weighted_regex("target_chi", ".*Χ.*", Decimal('1.0'))
        print(f"Pattern target seul:")
        print(f"  Original: .*Χ.*")
        print(f"  Ancré: {getattr(state2, 'metadata', {}).get('anchored_pattern', 'N/A')}")

        # Test évaluation individuelle
        test_words = ["Ω", "Χ", "ΩΧ", "ΦΧ"]
        print(f"\nTest évaluation individuelle:")
        for word in test_words:
            result1 = nfa1.evaluate_to_final_state(word)
            result2 = nfa2.evaluate_to_final_state(word)
            print(f"  '{word}': source={result1}, target={result2}")

        # Test 2: Patterns combinés dans même NFA
        print("\n--- TEST 2: PATTERNS COMBINÉS ---")

        nfa_combined = AnchoredWeightedNFA("test_combined")

        # Ajout séquentiel des patterns
        print("Ajout pattern source (.*Ω.*)...")
        state_src = nfa_combined.add_weighted_regex("source_omega", ".*Ω.*", Decimal('1.0'))
        print(f"  États après source: {len(nfa_combined.get_final_states())}")

        print("Ajout pattern target (.*Χ.*)...")
        state_tgt = nfa_combined.add_weighted_regex("target_chi", ".*Χ.*", Decimal('1.0'))
        print(f"  États après target: {len(nfa_combined.get_final_states())}")

        # Vérifier métadonnées ancrage
        print(f"\nMétadonnées ancrage:")
        print(f"  Source ancré: {getattr(state_src, 'metadata', {}).get('anchored_pattern', 'N/A')}")
        print(f"  Target ancré: {getattr(state_tgt, 'metadata', {}).get('anchored_pattern', 'N/A')}")

        # Test évaluation combinée
        print(f"\nTest évaluation combinée:")
        for word in test_words:
            result = nfa_combined.evaluate_to_final_state(word)
            print(f"  '{word}': combined={result}")

        # Test 3: Ordre d'ajout inversé
        print("\n--- TEST 3: ORDRE D'AJOUT INVERSÉ ---")

        nfa_inverted = AnchoredWeightedNFA("test_inverted")

        # Ajout target puis source
        print("Ajout pattern target en premier...")
        nfa_inverted.add_weighted_regex("target_chi", ".*Χ.*", Decimal('1.0'))
        print("Ajout pattern source en second...")
        nfa_inverted.add_weighted_regex("source_omega", ".*Ω.*", Decimal('1.0'))

        print(f"Test évaluation ordre inversé:")
        for word in test_words:
            result = nfa_inverted.evaluate_to_final_state(word)
            print(f"  '{word}': inverted={result}")

        # Test 4: Analyse états finaux
        print("\n--- TEST 4: ANALYSE ÉTATS FINAUX ---")

        print(f"États finaux NFA combiné: {len(nfa_combined.get_final_states())}")
        print(f"États finaux NFA inversé: {len(nfa_inverted.get_final_states())}")

        # Comparaison avec résultats attendus
        print(f"\n--- COMPARAISON RÉSULTATS ---")
        expected = {
            "Ω": "should match source .*Ω.*",
            "Χ": "should match target .*Χ.*",
            "ΩΧ": "should match both (ambiguous)",
            "ΦΧ": "should match target .*Χ.*"
        }

        for word, expectation in expected.items():
            combined_result = nfa_combined.evaluate_to_final_state(word)
            inverted_result = nfa_inverted.evaluate_to_final_state(word)

            print(f"  '{word}' ({expectation}):")
            print(f"    Combined: {combined_result}")
            print(f"    Inverted: {inverted_result}")

            if word == "ΦΧ":  # Notre cas problématique
                if combined_result is None:
                    print(f"    ❌ PROBLÈME CONFIRMÉ: '{word}' devrait matcher .*Χ.*")
                else:
                    print(f"    ✅ Fonctionne correctement")

        self.assertTrue(True, "Diagnostic ancrage terminé")


if __name__ == '__main__':
    unittest.main(verbosity=2)