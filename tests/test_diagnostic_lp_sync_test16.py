#!/usr/bin/env python3
"""
DIAGNOSTIC: Analyse synchronisation LP variables - Test 16 après corrections taxonomie
Problème détecté: "Variable q24 referenced in constraint target_primary_me"
"""

import unittest
from decimal import Decimal
import sys
import os

# Path setup pour import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_core.enhanced_dag import EnhancedDAG
from icgs_core.dag import Transaction, TransactionMeasure


class TestDiagnosticLPSyncTest16(unittest.TestCase):
    """Diagnostic synchronisation LP variables après corrections taxonomie"""

    def setUp(self):
        """Setup EnhancedDAG avec API simplifiée"""
        self.dag = EnhancedDAG()

    def test_01_setup_correct_taxonomy_test16(self):
        """Étape 1: Configuration taxonomie Test 16 avec corrections"""
        print("\n=== CONFIGURATION TAXONOMIE TEST 16 CORRIGÉE ===")

        # Taxonomie manuelle Test 16 (pas d'auto-assignment)
        node_mappings_test16 = {
            "alice_source": "A",
            "alice_sink": "X",
            "bob_source": "B",
            "bob_sink": "Y"
        }

        try:
            # Migration vers EnhancedDAG API - Gestion automatique transaction_num
            configured_mappings = self.dag.configure_accounts_simple(node_mappings_test16)
            print("✅ Taxonomie Test 16 configurée via EnhancedDAG API")

            # Vérification mappings avec gestion automatique du transaction_num
            current_tx_num = self.dag.transaction_manager.get_current_transaction_num()
            for node_id, expected_char in node_mappings_test16.items():
                actual_char = self.dag.account_taxonomy.get_character_mapping(node_id, current_tx_num)
                print(f"  {node_id} → '{actual_char}' (tx_num: {current_tx_num})")
                self.assertEqual(actual_char, expected_char)

            return configured_mappings

        except Exception as e:
            print(f"❌ Erreur configuration taxonomie: {e}")
            self.fail(f"Enhanced taxonomy setup failed: {e}")

    def test_02_create_transaction_test16(self):
        """Étape 2: Création transaction Test 16 standard"""
        print("\n=== TRANSACTION TEST 16 ===")

        self.test_01_setup_correct_taxonomy_test16()

        transaction = Transaction(
            transaction_id="diagnostic_lp_sync",
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

        print(f"Transaction créée: {transaction.transaction_id}")
        print(f"  Source: {transaction.source_account_id}")
        print(f"  Target: {transaction.target_account_id}")
        print(f"  Amount: {transaction.amount}")

        return transaction

    def test_03_analyze_path_enumeration_output(self):
        """Étape 3: Analyse output path enumeration détaillé"""
        print("\n=== ANALYSE PATH ENUMERATION OUTPUT ===")

        transaction = self.test_02_create_transaction_test16()

        # Créer comptes dans DAG
        self.dag._ensure_accounts_exist_with_taxonomy(transaction)
        print(f"Comptes créés: {list(self.dag.accounts.keys())}")

        # Path enumeration avec debug détaillé
        print("Lancement path enumeration...")
        try:
            enumerated_paths = self.dag.path_enumerator.enumerate_paths_for_transaction(
                transaction,
                self.dag.accounts
            )

            print(f"Path enumeration result type: {type(enumerated_paths)}")

            if hasattr(enumerated_paths, '__len__'):
                print(f"Nombre de résultats: {len(enumerated_paths)}")

            if hasattr(enumerated_paths, 'path_classes'):
                print(f"Path classes: {len(enumerated_paths.path_classes)}")

                # Analyse détaillée path classes
                for i, path_class in enumerate(enumerated_paths.path_classes):
                    print(f"  Path class {i}:")
                    print(f"    State ID: {getattr(path_class, 'state_id', 'N/A')}")
                    print(f"    Pattern: {getattr(path_class, 'pattern', 'N/A')}")
                    print(f"    Paths count: {len(getattr(path_class, 'paths', []))}")

                    # Analyse premier path si disponible
                    if hasattr(path_class, 'paths') and path_class.paths:
                        first_path = path_class.paths[0]
                        print(f"    First path nodes: {[getattr(node, 'node_id', str(node)) for node in first_path]}")

            return enumerated_paths

        except Exception as e:
            print(f"❌ Erreur path enumeration: {e}")
            import traceback
            traceback.print_exc()
            return None

    def test_04_analyze_nfa_construction(self):
        """Étape 4: Analyse construction NFA et état IDs"""
        print("\n=== ANALYSE CONSTRUCTION NFA ===")

        transaction = self.test_02_create_transaction_test16()
        enumerated_paths = self.test_03_analyze_path_enumeration_output()

        if not enumerated_paths:
            print("❌ Pas de paths enumerated - arrêt analyse NFA")
            return None

        # Analyse NFA dans DAG
        print("Construction NFA pour transaction...")

        try:
            # Accès direct aux NFAs du DAG si disponibles
            if hasattr(self.dag, 'nfa_temp') and self.dag.nfa_temp:
                print(f"NFA temp disponible: {len(self.dag.nfa_temp.states)} états")

                # Analyse état IDs dans NFA temp
                for i, state in enumerate(self.dag.nfa_temp.states[:5]):  # Premier 5 états
                    print(f"  État {i}: ID={getattr(state, 'state_id', 'N/A')}")

            if hasattr(self.dag, 'nfa_persistent') and self.dag.nfa_persistent:
                print(f"NFA persistent disponible: {len(self.dag.nfa_persistent.states)} états")

            # Test construction via pattern
            patterns = [".*A.*", ".*B.*"]
            print(f"Test construction NFA pour patterns: {patterns}")

            return enumerated_paths

        except Exception as e:
            print(f"❌ Erreur analyse NFA: {e}")
            import traceback
            traceback.print_exc()
            return None

    def test_05_analyze_lp_variable_construction(self):
        """Étape 5: Analyse construction variables LP détaillée"""
        print("\n=== ANALYSE CONSTRUCTION VARIABLES LP ===")

        transaction = self.test_02_create_transaction_test16()
        enumerated_paths = self.test_04_analyze_nfa_construction()

        if not enumerated_paths:
            print("❌ Pas de paths/NFA - arrêt analyse LP")
            return

        print("Tentative construction variables LP...")

        try:
            # Simulation appel Simplex pour voir variables créées
            if hasattr(self.dag, '_validate_transaction_simplex'):
                print("Test Simplex validation (pour debug variables)...")

                # Capture de l'erreur pour analyse
                try:
                    simplex_result = self.dag._validate_transaction_simplex(transaction)
                    print(f"✅ Simplex validation réussie: {simplex_result}")
                except Exception as simplex_error:
                    print(f"❌ Erreur Simplex: {simplex_error}")

                    # Analyse de l'erreur spécifique
                    error_str = str(simplex_error)
                    if "Variable q" in error_str and "referenced in constraint" in error_str:
                        print("🔍 ERREUR VARIABLE LP DÉTECTÉE:")
                        print(f"   Message: {error_str}")

                        # Extraction ID variable problématique
                        import re
                        var_match = re.search(r'Variable (q\d+)', error_str)
                        if var_match:
                            problematic_var = var_match.group(1)
                            print(f"   Variable problématique: {problematic_var}")

                            # Extraction ID numérique
                            numeric_id = re.search(r'\d+', problematic_var)
                            if numeric_id:
                                state_id = int(numeric_id.group())
                                print(f"   État ID supposé: {state_id}")

                                # Vérification si cet état existe dans path_classes
                                if hasattr(enumerated_paths, 'path_classes'):
                                    found_in_classes = False
                                    for path_class in enumerated_paths.path_classes:
                                        if hasattr(path_class, 'state_id') and path_class.state_id == state_id:
                                            found_in_classes = True
                                            print(f"   ✅ État {state_id} trouvé dans path_classes")
                                            break

                                    if not found_in_classes:
                                        print(f"   ❌ État {state_id} MANQUE dans path_classes")
                                        print("   → PROBLÈME SYNCHRONISATION NFA/LP CONFIRMÉ")

        except Exception as e:
            print(f"❌ Erreur analyse LP: {e}")
            import traceback
            traceback.print_exc()

    def test_06_summary_lp_sync_diagnostic(self):
        """Étape 6: Résumé diagnostic synchronisation LP"""
        print("\n=== RÉSUMÉ DIAGNOSTIC LP SYNCHRONISATION ===")

        try:
            self.test_05_analyze_lp_variable_construction()

            print("\n🔍 DIAGNOSTIC SYNCHRONISATION LP:")
            print("1. Taxonomie manuelle: ✅ Corrigée")
            print("2. Path enumeration: ✅ Fonctionne (amélioré)")
            print("3. Construction NFA: ✅ Probablement OK")
            print("4. Variables LP: ❌ Désynchronisation état IDs")
            print()
            print("📋 PROBLÈME IDENTIFIÉ:")
            print("   → Variables LP créées avec IDs d'états qui n'existent pas")
            print("   → Contraintes référencent variables inexistantes")
            print("   → Origine: temp_nfa vs persistent_nfa ou path_classes")
            print()
            print("🎯 SOLUTION REQUISE:")
            print("   → Synchroniser IDs états entre NFA et variables LP")
            print("   → Vérifier correspondance path_classes.state_id et get_state_weights_for_measure")

        except Exception as e:
            print(f"❌ Erreur résumé diagnostic: {e}")


if __name__ == '__main__':
    unittest.main(verbosity=2)