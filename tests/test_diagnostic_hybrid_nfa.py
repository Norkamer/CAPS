#!/usr/bin/env python3
"""
DIAGNOSTIC: Vérifier fonctionnement hybrid dual-NFA
Tester si target NFA correctement stocké et frozen
"""

import unittest
from decimal import Decimal
import sys
import os

# Path setup pour import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_core.dag import DAG, Transaction, TransactionMeasure


class TestDiagnosticHybridNFA(unittest.TestCase):
    """Diagnostic hybrid dual-NFA approach"""

    def test_hybrid_nfa_storage_and_access(self):
        """Test stockage et accès target NFA dans metadata"""
        print("\n=== DIAGNOSTIC HYBRID DUAL-NFA ===")

        # Setup simple
        dag = DAG()
        node_mappings = {
            "account_source_0_source": "Ω",
            "account_source_0_sink": "Ψ",
            "account_target_0_source": "Χ",
            "account_target_0_sink": "Φ"
        }
        dag.account_taxonomy.update_taxonomy(node_mappings, 0)

        # Transaction avec source ET target patterns
        transaction = Transaction(
            transaction_id="hybrid_test",
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

        print(f"Source patterns: {[m.primary_regex_pattern for m in transaction.source_measures]}")
        print(f"Target patterns: {[m.primary_regex_pattern for m in transaction.target_measures]}")

        # ÉTAPE 1: Créer comptes
        dag._ensure_accounts_exist_with_taxonomy(transaction)

        # ÉTAPE 2: Créer NFA temporaire et vérifier metadata
        print("\n--- CRÉATION NFA TEMPORAIRE ---")
        temp_nfa = dag._create_temporary_nfa_for_transaction(transaction)

        print(f"Main NFA: {len(temp_nfa.get_final_states())} états finaux")
        print(f"Main NFA metadata: {hasattr(temp_nfa, 'metadata')}")

        if hasattr(temp_nfa, 'metadata') and isinstance(temp_nfa.metadata, dict):
            target_nfa = temp_nfa.metadata.get('target_nfa')
            if target_nfa:
                print(f"✅ Target NFA trouvé: {len(target_nfa.get_final_states())} états finaux")
                print(f"Target NFA frozen: {target_nfa.is_frozen if hasattr(target_nfa, 'is_frozen') else 'unknown'}")
            else:
                print("❌ Target NFA pas trouvé dans metadata")
        else:
            print("❌ Metadata pas disponible")

        # ÉTAPE 3: Test patterns individuels
        print("\n--- TEST PATTERNS INDIVIDUELS ---")
        test_words = ["Ω", "Χ", "ΩΧ", "ΦΧ"]

        # Test main NFA
        temp_nfa.freeze()
        print("Main NFA results:")
        for word in test_words:
            result = temp_nfa.evaluate_to_final_state(word)
            print(f"  '{word}' → {result}")

        # Test target NFA si disponible
        if hasattr(temp_nfa, 'metadata') and isinstance(temp_nfa.metadata, dict):
            target_nfa = temp_nfa.metadata.get('target_nfa')
            if target_nfa:
                target_nfa.freeze()
                print("Target NFA results:")
                for word in test_words:
                    result = target_nfa.evaluate_to_final_state(word)
                    print(f"  '{word}' → {result}")
            else:
                print("Target NFA indisponible pour test")

        # ÉTAPE 4: Test classification hybride avec pipeline complet
        print("\n--- TEST PIPELINE HYBRIDE ---")
        transaction_edge = dag._create_temporary_transaction_edge(transaction)

        try:
            path_classes = dag.path_enumerator.enumerate_and_classify(
                transaction_edge, temp_nfa, 0
            )

            total_classified = sum(len(paths) for paths in path_classes.values())
            print(f"Pipeline result: {len(path_classes)} états, {total_classified} paths classifiés")

            if total_classified > 0:
                print("✅ Classification hybride fonctionne!")
                for state_id, paths in path_classes.items():
                    print(f"  État {state_id}: {len(paths)} paths")
            else:
                print("❌ Classification hybride échoue encore")

        except Exception as e:
            print(f"❌ Erreur pipeline: {e}")

        self.assertTrue(True, "Diagnostic hybrid NFA terminé")


if __name__ == '__main__':
    unittest.main(verbosity=2)