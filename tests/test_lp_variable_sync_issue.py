#!/usr/bin/env python3
"""
DIAGNOSTIC CIBLÉ: Problème synchronisation variables LP - Test 16
Issue: "Variable q24 referenced in constraint target_primary_me"
"""

import unittest
from decimal import Decimal
import sys
import os

# Path setup pour import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_core.dag import DAG, Transaction, TransactionMeasure


class TestLPVariableSyncIssue(unittest.TestCase):
    """Diagnostic ciblé synchronisation variables LP"""

    def test_lp_sync_issue_reproduction(self):
        """Reproduction exacte problème LP sync Test 16"""
        print("\n=== REPRODUCTION PROBLÈME LP SYNC ===")

        # Setup DAG avec taxonomie correcte
        dag = DAG()

        # Taxonomie manuelle unique (transaction_num=0)
        node_mappings = {
            "alice_source": "A",
            "alice_sink": "X",
            "bob_source": "B",
            "bob_sink": "Y"
        }

        try:
            dag.account_taxonomy.update_taxonomy(node_mappings, 0)
            print("✅ Taxonomie configurée")

            # Transaction Test 16 exacte
            transaction = Transaction(
                transaction_id="lp_sync_test",
                source_account_id="alice",
                target_account_id="bob",
                amount=Decimal('100'),
                source_measures=[
                    TransactionMeasure(
                        measure_id="agriculture_debit",
                        account_id="alice",
                        primary_regex_pattern=".*A.*",
                        primary_regex_weight=Decimal('1.2'),
                        acceptable_value=Decimal('500')
                    )
                ],
                target_measures=[
                    TransactionMeasure(
                        measure_id="industry_credit",
                        account_id="bob",
                        primary_regex_pattern=".*B.*",
                        primary_regex_weight=Decimal('0.9'),
                        acceptable_value=Decimal('0'),
                        required_value=Decimal('100')
                    )
                ]
            )

            # Création comptes
            dag._ensure_accounts_exist_with_taxonomy(transaction)
            print(f"✅ Comptes: {list(dag.accounts.keys())}")

            # Test NFA validation (doit passer)
            print("Test NFA validation...")
            nfa_valid = dag._validate_transaction_nfa_explosion(transaction)
            print(f"NFA validation: {nfa_valid}")

            if nfa_valid:
                # Test Simplex (doit échouer avec erreur variable)
                print("Test Simplex validation...")
                try:
                    simplex_valid = dag._validate_transaction_simplex(transaction)
                    print(f"✅ UNEXPECTED: Simplex validation passed: {simplex_valid}")
                except Exception as e:
                    error_str = str(e)
                    print(f"❌ EXPECTED: Simplex validation failed: {error_str}")

                    # Analyse de l'erreur
                    if "Variable q" in error_str and "referenced in constraint" in error_str:
                        print("🔍 ERREUR VARIABLE LP CONFIRMÉE")

                        # Extraction variable problématique
                        import re
                        var_match = re.search(r'Variable (q\d+)', error_str)
                        constraint_match = re.search(r'constraint (\w+)', error_str)

                        if var_match and constraint_match:
                            problematic_var = var_match.group(1)
                            problematic_constraint = constraint_match.group(1)

                            print(f"   Variable manquante: {problematic_var}")
                            print(f"   Contrainte: {problematic_constraint}")

                            # Extraction ID numérique
                            numeric_match = re.search(r'(\d+)', problematic_var)
                            if numeric_match:
                                missing_state_id = int(numeric_match.group(1))
                                print(f"   État ID manquant: {missing_state_id}")

                                print("\n🎯 DIAGNOSTIC FINAL:")
                                print(f"   → État NFA ID {missing_state_id} utilisé dans contraintes")
                                print(f"   → Mais variable LP q{missing_state_id} n'existe pas")
                                print(f"   → Désynchronisation NFA états ↔ Variables LP")

                                self.assertTrue(True, f"LP sync issue confirmed: missing variable {problematic_var}")
                                return

                    print("❌ Erreur non reconnue comme problème LP sync")
                    self.fail(f"Unexpected error format: {error_str}")
            else:
                print("❌ NFA validation échoue - problème précédent")
                self.fail("NFA validation should pass with correct taxonomy")

        except Exception as e:
            print(f"❌ Erreur setup: {e}")
            import traceback
            traceback.print_exc()
            self.fail(f"Setup failed: {e}")


if __name__ == '__main__':
    unittest.main(verbosity=2)