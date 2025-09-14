#!/usr/bin/env python3
"""
DIAGNOSTIC: Test tx_sequential_1 qui échoue
Vérifier pourquoi 2ème transaction séquentielle échoue vs 1ère
"""

import unittest
from decimal import Decimal
import sys
import os

# Path setup pour import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_core.dag import DAG, Transaction, TransactionMeasure


class TestDiagnosticSequentialTx(unittest.TestCase):
    """Diagnostic transaction séquentielle échouante"""

    def test_sequential_transactions_step_by_step(self):
        """Test tx_sequential_0 (succès) vs tx_sequential_1 (échec)"""
        print("\n=== DIAGNOSTIC TRANSACTIONS SÉQUENTIELLES ===")

        dag = DAG()

        # Taxonomie étendue identique au Test 16
        explicit_mappings = {
            # Test 16.2 patterns
            "account_source_0_source": "Ω",  # Pour pattern .*Ω.*
            "account_source_0_sink": "Ψ",
            "account_target_0_source": "Χ",  # Pour pattern .*Χ.*
            "account_target_0_sink": "Φ",

            # Test 16.3 patterns séquentiels
            "account_source_1_source": "Υ",  # Pour pattern .*Υ.*
            "account_source_1_sink": "Τ",
            "account_target_1_source": "Σ",  # Pour pattern .*Σ.*
            "account_target_1_sink": "Ρ",

            "account_source_2_source": "Π",  # Pour pattern .*Π.*
            "account_source_2_sink": "Ο",
            "account_target_2_source": "Ν",  # Pour pattern .*Ν.*
            "account_target_2_sink": "Μ",
        }

        # Configure taxonomy for multiple transaction numbers (0, 1, 2)
        for tx_num in range(3):
            dag.account_taxonomy.update_taxonomy(explicit_mappings, tx_num)
        print(f"✅ Taxonomie configurée avec {len(explicit_mappings)} mappings pour transactions 0-2")

        # Créer 3 transactions séquentielles identiques au Test 16.3
        transactions = []
        patterns = [
            (".*Ω.*", ".*Χ.*"),  # tx_sequential_0 (succès attendu)
            (".*Υ.*", ".*Σ.*"),  # tx_sequential_1 (échec)
            (".*Π.*", ".*Ν.*"),  # tx_sequential_2
        ]

        for i, (source_pattern, target_pattern) in enumerate(patterns):
            source_measure = TransactionMeasure(
                measure_id=f"measure_source_{i}",
                account_id=f"account_source_{i}",
                primary_regex_pattern=source_pattern,
                primary_regex_weight=Decimal('1.0'),
                acceptable_value=Decimal('500'),
                secondary_patterns=[]
            )

            target_measure = TransactionMeasure(
                measure_id=f"measure_target_{i}",
                account_id=f"account_target_{i}",
                primary_regex_pattern=target_pattern,
                primary_regex_weight=Decimal('1.0'),
                acceptable_value=Decimal('0'),
                required_value=Decimal('50'),
                secondary_patterns=[]
            )

            transaction = Transaction(
                transaction_id=f"tx_sequential_{i}",
                source_account_id=f"account_source_{i}",
                target_account_id=f"account_target_{i}",
                amount=Decimal(str(100 + i * 10)),
                source_measures=[source_measure],
                target_measures=[target_measure]
            )
            transactions.append(transaction)

        # Test chaque transaction individuellement
        for i, transaction in enumerate(transactions):
            print(f"\n--- TRANSACTION {i}: {transaction.transaction_id} ---")
            print(f"Source pattern: {transaction.source_measures[0].primary_regex_pattern}")
            print(f"Target pattern: {transaction.target_measures[0].primary_regex_pattern}")
            print(f"DAG counter avant: {dag.transaction_counter}")

            try:
                result = dag.add_transaction(transaction)
                print(f"✅ Résultat: {result}")
                print(f"DAG counter après: {dag.transaction_counter}")

                if not result:
                    print(f"❌ Transaction {i} échouée - diagnostic détaillé:")

                    # Test NFA individuel
                    temp_nfa = dag._create_temporary_nfa_for_transaction(transaction)
                    temp_nfa.freeze()
                    print(f"  Main NFA: {len(temp_nfa.get_final_states())} états")

                    if hasattr(temp_nfa, 'metadata') and isinstance(temp_nfa.metadata, dict):
                        target_nfa = temp_nfa.metadata.get('target_nfa')
                        if target_nfa:
                            target_nfa.freeze()
                            print(f"  Target NFA: {len(target_nfa.get_final_states())} états")
                        else:
                            print(f"  ❌ Target NFA manquant!")

                    # Test taxonomie pour cette transaction
                    current_tx = dag.transaction_counter
                    for account_id in [transaction.source_account_id, transaction.target_account_id]:
                        source_char = dag.account_taxonomy.get_character_mapping(f"{account_id}_source", current_tx)
                        sink_char = dag.account_taxonomy.get_character_mapping(f"{account_id}_sink", current_tx)
                        print(f"  {account_id}: source='{source_char}', sink='{sink_char}'")

            except Exception as e:
                print(f"❌ Erreur exception: {e}")

        print(f"\n--- RÉCAPITULATIF ---")
        print(f"DAG final counter: {dag.transaction_counter}")

        self.assertTrue(True, "Diagnostic séquentiel terminé")


if __name__ == '__main__':
    unittest.main(verbosity=2)