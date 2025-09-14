#!/usr/bin/env python3
"""
Debug Word-NFA Matching - Identification problème classification 0%

Script pour débugger le problème où Phase 3 classification retourne 0%
malgré patterns alignés. Test direct des composants:
1. Génération mots à partir paths avec taxonomy mappings
2. Construction NFA avec patterns alignés
3. Évaluation NFA des mots générés
4. Identification exact du problème
"""

import sys
from decimal import Decimal, getcontext
from typing import List

# Configuration précision étendue
getcontext().prec = 50

try:
    from icgs_core import (
        DAG, DAGConfiguration, Transaction, TransactionMeasure,
        AnchoredWeightedNFA, AccountTaxonomy
    )
    from icgs_core.dag_structures import Node
except ImportError as e:
    print(f"IMPORT ERROR: {e}")
    sys.exit(1)


class WordNFADebugger:
    """
    Debugger détaillé pour problème Word-NFA matching
    """

    def __init__(self):
        # Configuration DAG identique aux tests
        self.config = DAGConfiguration(
            max_path_enumeration=1000,
            simplex_max_iterations=500,
            simplex_tolerance=Decimal('1e-10'),
            nfa_explosion_threshold=100,
            enable_warm_start=True,
            enable_cross_validation=True,
            validation_mode="STRICT"
        )

        self.dag = DAG(self.config)

        # Configuration taxonomie FIXÉE (sans collisions)
        self.fixed_mappings = {
            "alice_farm_source": "A",
            "alice_farm_sink": "B",
            "bob_factory_source": "C",
            "bob_factory_sink": "D",
        }

        # Configuration pour transaction 0
        self.dag.account_taxonomy.update_taxonomy(self.fixed_mappings, 0)

        print("=== DEBUG WORD-NFA MATCHING ===")
        print(f"Taxonomy mappings configured:")
        for node_id, char in self.fixed_mappings.items():
            actual_char = self.dag.account_taxonomy.get_character_mapping(node_id, 0)
            print(f"  {node_id}: '{char}' (actual: '{actual_char}')")

    def test_1_word_generation_from_paths(self):
        """
        Test 1: Génération mots à partir paths réels
        """
        print(f"\n=== TEST 1: WORD GENERATION FROM PATHS ===")

        # Création nodes réels (comme dans DAG)
        alice_farm_source = Node("alice_farm_source", "source")
        alice_farm_sink = Node("alice_farm_sink", "sink")
        bob_factory_source = Node("bob_factory_source", "source")
        bob_factory_sink = Node("bob_factory_sink", "sink")

        # Paths réels (comme énumération retournerait)
        test_paths = [
            [bob_factory_sink],  # Path simple: target sink seulement
            [alice_farm_source, bob_factory_sink],  # Path: source → target sink
            [alice_farm_sink, bob_factory_source, bob_factory_sink],  # Path complexe
        ]

        transaction_num = 0

        print(f"Testing {len(test_paths)} paths:")

        for i, path in enumerate(test_paths):
            path_str = " → ".join(node.node_id for node in path)
            print(f"\nPath {i}: {path_str}")

            # Conversion via taxonomy
            try:
                word = self.dag.account_taxonomy.convert_path_to_word(path, transaction_num)
                print(f"  Word generated: '{word}'")

                # Analyse caractères word
                if word:
                    unique_chars = set(word)
                    print(f"  Characters: {unique_chars}")
                    print(f"  Length: {len(word)}")

                    # Vérification mapping expected
                    expected_chars = []
                    for node in path:
                        if node.node_id in self.fixed_mappings:
                            expected_chars.append(self.fixed_mappings[node.node_id])

                    print(f"  Expected chars: {expected_chars}")

                    # Vérification si word contient expected chars
                    for expected_char in expected_chars:
                        if expected_char in word:
                            print(f"  ✅ Contains '{expected_char}' as expected")
                        else:
                            print(f"  ❌ Missing '{expected_char}' - PROBLEM!")

                else:
                    print(f"  ❌ No word generated - PROBLEM!")

            except Exception as e:
                print(f"  ❌ Word generation error: {e}")

        return test_paths

    def test_2_nfa_construction_with_patterns(self):
        """
        Test 2: Construction NFA avec patterns alignés
        """
        print(f"\n=== TEST 2: NFA CONSTRUCTION WITH ALIGNED PATTERNS ===")

        # Patterns alignés sur nos mappings
        test_patterns = [
            (".*B", "alice_farm_sink = B"),  # Should match words containing B
            (".*D", "bob_factory_sink = D"),  # Should match words containing D
            ("B", "exact B"),                 # Exact match B
            ("D", "exact D"),                 # Exact match D
        ]

        for pattern, description in test_patterns:
            print(f"\nTesting pattern: '{pattern}' ({description})")

            try:
                # Construction NFA avec pattern
                nfa = AnchoredWeightedNFA("debug_nfa")

                # Ajout pattern avec poids
                nfa.add_weighted_regex(
                    measure_id="debug_measure",
                    regex_pattern=pattern,
                    weight=Decimal('1.0'),
                    regex_id="debug_pattern"
                )

                print(f"  ✅ NFA constructed successfully")

                # Test mots simples
                test_words = ["B", "D", "BD", "DB", "A", "C", "", "XDY", "XBY"]

                print(f"  Testing words:")
                for word in test_words:
                    try:
                        final_state_id = nfa.evaluate_to_final_state(word)
                        match_status = "✅ MATCH" if final_state_id else "❌ NO MATCH"
                        print(f"    '{word}' → {match_status} (state: {final_state_id})")
                    except Exception as e:
                        print(f"    '{word}' → ❌ ERROR: {e}")

            except Exception as e:
                print(f"  ❌ NFA construction error: {e}")

    def test_3_full_integration_debug(self):
        """
        Test 3: Intégration complète Path → Word → NFA
        """
        print(f"\n=== TEST 3: FULL INTEGRATION PATH → WORD → NFA ===")

        # Path réel
        bob_sink = Node("bob_factory_sink", "sink")
        test_path = [bob_sink]

        print(f"Test path: {bob_sink.node_id}")

        # Step 1: Path → Word
        try:
            word = self.dag.account_taxonomy.convert_path_to_word(test_path, 0)
            print(f"Step 1 - Generated word: '{word}'")

            if not word:
                print(f"❌ PROBLEM: No word generated")
                return

        except Exception as e:
            print(f"❌ PROBLEM: Word generation failed: {e}")
            return

        # Step 2: NFA construction avec pattern aligné
        pattern = ".*D"  # Aligné sur bob_factory_sink = D
        print(f"Step 2 - Pattern: '{pattern}' (should match word containing 'D')")

        try:
            nfa = AnchoredWeightedNFA("integration_test")
            nfa.add_weighted_regex(
                measure_id="bob_measure",
                regex_pattern=pattern,
                weight=Decimal('1.0'),
                regex_id="bob_pattern"
            )
            print(f"✅ NFA constructed")

        except Exception as e:
            print(f"❌ PROBLEM: NFA construction failed: {e}")
            return

        # Step 3: NFA evaluation
        try:
            final_state_id = nfa.evaluate_to_final_state(word)

            if final_state_id:
                print(f"✅ SUCCESS: Word '{word}' matches pattern '{pattern}' → state {final_state_id}")
                print(f"✅ INTEGRATION WORKING - Classification should succeed")
            else:
                print(f"❌ PROBLEM: Word '{word}' does NOT match pattern '{pattern}'")
                print(f"❌ ROOT CAUSE IDENTIFIED - This is why classification = 0%")

                # Diagnostic approfondi
                print(f"\nDIAGNOSTIC APPROFONDI:")
                print(f"  Word: '{word}'")
                print(f"  Pattern: '{pattern}'")
                print(f"  Expected mapping: bob_factory_sink → 'D'")

                if 'D' in word:
                    print(f"  ✅ Word contains 'D'")
                    print(f"  ❌ But pattern '.*D' doesn't match - NFA evaluation problem")
                else:
                    print(f"  ❌ Word doesn't contain 'D' - Taxonomy mapping problem")

        except Exception as e:
            print(f"❌ PROBLEM: NFA evaluation failed: {e}")

    def test_4_transaction_measures_patterns_debug(self):
        """
        Test 4: Debug patterns des TransactionMeasure vs mots réels
        """
        print(f"\n=== TEST 4: TRANSACTION MEASURES PATTERNS DEBUG ===")

        # Patterns des tests FIXED
        source_pattern = ".*B"  # alice_farm pattern pour sink B
        target_pattern = ".*D"  # bob_factory pattern pour sink D

        print(f"Source pattern: '{source_pattern}' (alice_farm_sink = B)")
        print(f"Target pattern: '{target_pattern}' (bob_factory_sink = D)")

        # Paths typiques énumération
        alice_sink = Node("alice_farm_sink", "sink")
        bob_sink = Node("bob_factory_sink", "sink")

        test_scenarios = [
            ([alice_sink], source_pattern, "Alice path vs source pattern"),
            ([bob_sink], target_pattern, "Bob path vs target pattern"),
            ([alice_sink, bob_sink], source_pattern, "Multi-path vs source pattern"),
            ([alice_sink, bob_sink], target_pattern, "Multi-path vs target pattern"),
        ]

        for path, pattern, description in test_scenarios:
            print(f"\n{description}:")
            path_str = " → ".join(node.node_id for node in path)
            print(f"  Path: {path_str}")

            # Génération word
            try:
                word = self.dag.account_taxonomy.convert_path_to_word(path, 0)
                print(f"  Word: '{word}'")

                # Test pattern matching avec NFA
                try:
                    nfa = AnchoredWeightedNFA("scenario_test")
                    nfa.add_weighted_regex("test_measure", pattern, Decimal('1.0'), "test_pattern")

                    final_state = nfa.evaluate_to_final_state(word)

                    if final_state:
                        print(f"  ✅ MATCH: Pattern '{pattern}' matches word '{word}'")
                    else:
                        print(f"  ❌ NO MATCH: Pattern '{pattern}' does NOT match word '{word}'")

                        # Analyse détaillée pourquoi pas de match
                        if word and pattern.startswith(".*"):
                            expected_char = pattern[2:]  # Enlève ".*"
                            if expected_char in word:
                                print(f"      Word contains '{expected_char}' but pattern doesn't match - NFA issue")
                            else:
                                print(f"      Word doesn't contain '{expected_char}' - Taxonomy issue")

                except Exception as e:
                    print(f"  ❌ NFA error: {e}")

            except Exception as e:
                print(f"  ❌ Word generation error: {e}")


def main():
    """Execute comprehensive debugging"""
    debugger = WordNFADebugger()

    # Test sequence
    test_paths = debugger.test_1_word_generation_from_paths()
    debugger.test_2_nfa_construction_with_patterns()
    debugger.test_3_full_integration_debug()
    debugger.test_4_transaction_measures_patterns_debug()

    print(f"\n=== DEBUGGING SUMMARY ===")
    print(f"Tests completed - Check output above for root cause identification")
    print(f"Focus on any ❌ PROBLEM messages for the exact issue")


if __name__ == "__main__":
    main()