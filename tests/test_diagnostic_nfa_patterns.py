#!/usr/bin/env python3
"""
DIAGNOSTIC: Vérifier patterns ajoutés au NFA temporaire
Analyser pourquoi .*Χ.* ne fonctionne pas vs .*Ω.*
"""

import unittest
from decimal import Decimal
import sys
import os

# Path setup pour import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_core.dag import DAG, Transaction, TransactionMeasure


class TestDiagnosticNFAPatterns(unittest.TestCase):
    """Diagnostic patterns NFA construction"""

    def test_nfa_patterns_construction(self):
        """Test patterns ajoutés au NFA temporaire"""
        print("\n=== DIAGNOSTIC NFA PATTERNS ===")

        # Setup simple
        dag = DAG()
        node_mappings = {
            "account_source_0_source": "Ω",
            "account_source_0_sink": "Ψ",
            "account_target_0_source": "Χ",
            "account_target_0_sink": "Φ"
        }
        dag.account_taxonomy.update_taxonomy(node_mappings, 0)

        # Transaction avec patterns source ET target
        transaction = Transaction(
            transaction_id="patterns_test",
            source_account_id="account_source_0",
            target_account_id="account_target_0",
            amount=Decimal('100'),
            source_measures=[
                TransactionMeasure(
                    measure_id="source_omega",
                    account_id="account_source_0",
                    primary_regex_pattern=".*Ω.*",
                    primary_regex_weight=Decimal('1.0'),
                    acceptable_value=Decimal('500')
                )
            ],
            target_measures=[
                TransactionMeasure(
                    measure_id="target_chi",
                    account_id="account_target_0",
                    primary_regex_pattern=".*Χ.*",
                    primary_regex_weight=Decimal('1.0'),
                    acceptable_value=Decimal('0'),
                    required_value=Decimal('50')
                )
            ]
        )

        print(f"Source measures: {[m.primary_regex_pattern for m in transaction.source_measures]}")
        print(f"Target measures: {[m.primary_regex_pattern for m in transaction.target_measures]}")

        # STEP 1: Créer NFA temporaire et analyser contenu
        print("\n--- CRÉATION NFA TEMPORAIRE ---")
        temp_nfa = dag._create_temporary_nfa_for_transaction(transaction)

        print(f"NFA créé: {len(temp_nfa.get_final_states())} états finaux")

        # Test systématique tous patterns attendus
        test_cases = [
            ("Ω", "source pattern .*Ω.*", True),
            ("Χ", "target pattern .*Χ.*", True),
            ("ΩΧ", "contains Ω (source)", True),
            ("ΧΩ", "contains Ω (source)", True),
            ("ΦΧ", "contains Χ (target)", True),
            ("ΧΦ", "contains Χ (target)", True),
            ("ΨΦ", "no Ω or Χ", False),
            ("ΑΒ", "unrelated chars", False)
        ]

        print("\n--- TEST PATTERNS SYSTÉMATIQUE ---")
        for word, description, expected_match in test_cases:
            try:
                result = temp_nfa.evaluate_to_final_state(word)
                match_found = result is not None
                status = "✅" if match_found == expected_match else "❌"
                print(f"{status} '{word}' → {result} ({description}) [expected: {'match' if expected_match else 'no match'}]")

                if match_found != expected_match:
                    print(f"   💡 MISMATCH DÉTECTÉ: '{word}' devrait {'matcher' if expected_match else 'ne pas matcher'}")

            except Exception as e:
                print(f"❌ '{word}' → ERROR: {e}")

        # STEP 2: Test patterns isolés (un par un)
        print("\n--- TEST PATTERNS ISOLÉS ---")

        # Test pattern source seul
        print("Test pattern source seul (.*Ω.*):")
        dag_source_only = DAG()
        dag_source_only.account_taxonomy.update_taxonomy(node_mappings, 0)

        transaction_source_only = Transaction(
            transaction_id="source_only",
            source_account_id="account_source_0",
            target_account_id="account_target_0",
            amount=Decimal('100'),
            source_measures=[transaction.source_measures[0]],
            target_measures=[]  # Pas de target
        )

        temp_nfa_source = dag_source_only._create_temporary_nfa_for_transaction(transaction_source_only)
        test_words = ["Ω", "Χ", "ΩΧ", "ΦΧ"]
        for word in test_words:
            result = temp_nfa_source.evaluate_to_final_state(word)
            print(f"  Source-only: '{word}' → {result}")

        # Test pattern target seul
        print("\nTest pattern target seul (.*Χ.*):")
        dag_target_only = DAG()
        dag_target_only.account_taxonomy.update_taxonomy(node_mappings, 0)

        transaction_target_only = Transaction(
            transaction_id="target_only",
            source_account_id="account_source_0",
            target_account_id="account_target_0",
            amount=Decimal('100'),
            source_measures=[],  # Pas de source
            target_measures=[transaction.target_measures[0]]
        )

        temp_nfa_target = dag_target_only._create_temporary_nfa_for_transaction(transaction_target_only)
        for word in test_words:
            result = temp_nfa_target.evaluate_to_final_state(word)
            print(f"  Target-only: '{word}' → {result}")

        print("\n--- DIAGNOSTIC FINAL ---")
        print("🎯 Vérifier si patterns target ajoutés correctement au NFA combiné")

        self.assertTrue(True, "Diagnostic patterns terminé")


if __name__ == '__main__':
    unittest.main(verbosity=2)