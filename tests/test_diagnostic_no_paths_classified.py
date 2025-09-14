#!/usr/bin/env python3
"""
DIAGNOSTIC MODE THINK: Analyser "no paths were classified"
Pipeline path enumeration → classification cassé
"""

import unittest
from decimal import Decimal
import sys
import os

# Path setup pour import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_core.dag import DAG, Transaction, TransactionMeasure


class TestDiagnosticNoPathsClassified(unittest.TestCase):
    """Diagnostic complet pipeline classification"""

    def test_diagnostic_pipeline_step_by_step(self):
        """Diagnostic étape par étape du pipeline"""
        print("\n=== DIAGNOSTIC PIPELINE CLASSIFICATION ===")

        # Setup DAG avec taxonomie Test 16 problématique
        dag = DAG()

        # Taxonomie UTF-32 grecque identique à Test 16
        node_mappings = {
            "account_source_0_source": "Ω",  # Pour pattern .*Ω.*
            "account_source_0_sink": "Ψ",
            "account_target_0_source": "Χ",  # Pour pattern .*Χ.*
            "account_target_0_sink": "Φ"
        }

        dag.account_taxonomy.update_taxonomy(node_mappings, 0)
        print(f"✅ Taxonomie configurée avec {len(node_mappings)} mappings")

        # Transaction problématique identique Test 16
        transaction = Transaction(
            transaction_id="diagnostic_tx",
            source_account_id="account_source_0",
            target_account_id="account_target_0",
            amount=Decimal('100'),
            source_measures=[
                TransactionMeasure(
                    measure_id="measure_source_0",
                    account_id="account_source_0",
                    primary_regex_pattern=".*Ω.*",  # Pattern pour Ω
                    primary_regex_weight=Decimal('1.0'),
                    acceptable_value=Decimal('500')
                )
            ],
            target_measures=[
                TransactionMeasure(
                    measure_id="measure_target_0",
                    account_id="account_target_0",
                    primary_regex_pattern=".*Χ.*",  # Pattern pour Χ
                    primary_regex_weight=Decimal('1.0'),
                    acceptable_value=Decimal('0'),
                    required_value=Decimal('50')
                )
            ]
        )

        print(f"Transaction: {transaction.transaction_id}")
        print(f"  Source patterns: {[m.primary_regex_pattern for m in transaction.source_measures]}")
        print(f"  Target patterns: {[m.primary_regex_pattern for m in transaction.target_measures]}")

        # ÉTAPE 1: Création comptes
        print("\n--- ÉTAPE 1: CRÉATION COMPTES ---")
        try:
            dag._ensure_accounts_exist_with_taxonomy(transaction)
            print(f"✅ Comptes créés: {list(dag.accounts.keys())}")

            # Vérifier mappings taxonomie
            for account_id in transaction.source_account_id, transaction.target_account_id:
                account = dag.accounts[account_id]
                source_char = dag.account_taxonomy.get_character_mapping(account.source_node.node_id, 0)
                sink_char = dag.account_taxonomy.get_character_mapping(account.sink_node.node_id, 0)
                print(f"  {account_id}: source='{source_char}', sink='{sink_char}'")

        except Exception as e:
            print(f"❌ Erreur création comptes: {e}")
            return

        # ÉTAPE 2: Création NFA temporaire
        print("\n--- ÉTAPE 2: CRÉATION NFA ---")
        try:
            temp_nfa = dag._create_temporary_nfa_for_transaction(transaction)
            print(f"✅ NFA créé: {len(temp_nfa.get_final_states())} états finaux")

            # Test patterns dans NFA avec API correcte
            test_words = ["Ω", "Χ", "ΩΧ", "ΧΩ", "ΨΦ"]
            print("Test patterns NFA:")
            for test_word in test_words:
                try:
                    if hasattr(temp_nfa, 'evaluate_to_final_state'):
                        result = temp_nfa.evaluate_to_final_state(test_word)
                        print(f"  '{test_word}' → {result} (evaluate_to_final_state)")
                    elif hasattr(temp_nfa, 'evaluate_word'):
                        result = temp_nfa.evaluate_word(test_word)
                        print(f"  '{test_word}' → {result} (evaluate_word)")
                    else:
                        print(f"  '{test_word}' → No evaluation method found")
                except Exception as e:
                    print(f"  '{test_word}' → ERROR: {e}")

        except Exception as e:
            print(f"❌ Erreur création NFA: {e}")
            return

        # ÉTAPE 3: Création transaction edge
        print("\n--- ÉTAPE 3: TRANSACTION EDGE ---")
        try:
            temp_edge = dag._create_temporary_transaction_edge(transaction)
            print(f"✅ Edge créé: {temp_edge.source_node.node_id} → {temp_edge.target_node.node_id}")

        except Exception as e:
            print(f"❌ Erreur transaction edge: {e}")
            return

        # ÉTAPE 4: Path enumeration
        print("\n--- ÉTAPE 4: PATH ENUMERATION ---")
        try:
            # Accès direct au path enumerator
            paths = list(dag.path_enumerator.enumerate_paths_from_transaction(temp_edge, 0))
            print(f"✅ Paths énumérés: {len(paths)}")

            if paths:
                for i, path in enumerate(paths[:3]):  # Premier 3 paths
                    path_nodes = [node.node_id for node in path]
                    print(f"  Path {i}: {path_nodes}")
            else:
                print("❌ PROBLÈME: Aucun path énuméré!")
                return

        except Exception as e:
            print(f"❌ Erreur path enumeration: {e}")
            return

        # ÉTAPE 5: Path → Word conversion
        print("\n--- ÉTAPE 5: PATH → WORD CONVERSION ---")
        try:
            words = dag.path_enumerator.convert_paths_to_words(paths, 0)
            print(f"✅ Words générés: {len(words)}")

            for i, (path, word) in enumerate(zip(paths[:3], words[:3])):
                path_nodes = [node.node_id for node in path]
                print(f"  Path {i}: {path_nodes} → '{word}'")

        except Exception as e:
            print(f"❌ Erreur path→word: {e}")
            return

        # ÉTAPE 6: NFA classification
        print("\n--- ÉTAPE 6: NFA CLASSIFICATION ---")
        try:
            classifications = {}
            classified_count = 0

            for i, (path, word) in enumerate(zip(paths, words)):
                if word:
                    try:
                        # Utiliser même API que path_enumerator
                        final_state_id = None
                        if hasattr(temp_nfa, 'evaluate_to_final_state'):
                            final_state_id = temp_nfa.evaluate_to_final_state(word)
                        elif hasattr(temp_nfa, 'evaluate_word'):
                            result = temp_nfa.evaluate_word(word)
                            final_state_id = result[0] if isinstance(result, tuple) else result

                        if final_state_id:
                            if final_state_id not in classifications:
                                classifications[final_state_id] = []
                            classifications[final_state_id].append(path)
                            classified_count += 1
                            if i < 3:  # Log premier 3
                                print(f"  Word '{word}' → state '{final_state_id}' ✅")
                        else:
                            if i < 3:
                                print(f"  Word '{word}' → NO MATCH ❌")
                    except Exception as e:
                        if i < 3:
                            print(f"  Word '{word}' → ERROR: {e}")

            print(f"\n📊 RÉSULTAT CLASSIFICATION:")
            print(f"  Total paths: {len(paths)}")
            print(f"  Paths classifiés: {classified_count}")
            print(f"  Taux classification: {(classified_count/len(paths)*100) if paths else 0:.1f}%")
            print(f"  États trouvés: {len(classifications)}")

            if classified_count == 0:
                print(f"\n❌ PROBLÈME IDENTIFIÉ: AUCUNE CLASSIFICATION")
                print(f"   → Patterns NFA ne matchent pas mots générés")
                print(f"   → Vérifier alignment patterns ↔ caractères taxonomie")
            else:
                print(f"\n✅ Classification réussie partiellement")

        except Exception as e:
            print(f"❌ Erreur classification NFA: {e}")

        # ÉTAPE 7: Diagnostic complet pipeline
        print("\n--- DIAGNOSTIC FINAL ---")
        try:
            result = dag.path_enumerator.enumerate_and_classify(temp_edge, temp_nfa, 0)
            print(f"Pipeline complet result: {type(result)}")

            if isinstance(result, dict):
                total_classified = sum(len(paths) for paths in result.values())
                print(f"  Classifications: {len(result)} états")
                print(f"  Paths classifiés: {total_classified}")

                if total_classified == 0:
                    print(f"  ❌ CONFIRMÉ: Pipeline retourne classifications vides")
                else:
                    print(f"  ✅ Pipeline fonctionne partiellement")

        except Exception as e:
            print(f"❌ Erreur pipeline complet: {e}")

        self.assertTrue(True, "Diagnostic terminé")


if __name__ == '__main__':
    unittest.main(verbosity=2)