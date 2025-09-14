#!/usr/bin/env python3
"""
Debug final Test 16 avec architecture Thompson's
Trace complète pipeline DAG.add_transaction()
"""

import sys
import os
import time
from decimal import Decimal, getcontext

getcontext().prec = 50

# Path setup
sys.path.insert(0, os.path.dirname(__file__))

from icgs_core import DAG, DAGConfiguration, Transaction, TransactionMeasure


def debug_test16_detailed():
    """Debug détaillé Test 16 avec architecture Thompson's"""
    print("=== DEBUG TEST 16 FINAL - THOMPSON'S ARCHITECTURE ===")

    # Configuration DAG identique Test 16
    config = DAGConfiguration(
        max_path_enumeration=1000,
        simplex_max_iterations=500,
        simplex_tolerance=Decimal('1e-10'),
        nfa_explosion_threshold=100,
        enable_warm_start=True,
        enable_cross_validation=True,
        validation_mode="STRICT"
    )

    dag = DAG(config)
    print("✅ DAG initialisé")

    # Configuration taxonomie manuelle (identique Test 16)
    explicit_mappings = {
        "alice_farm_source": "A",
        "alice_farm_sink": "Z",
        "bob_factory_source": "B",
        "bob_factory_sink": "N",  # CRITIQUE: N pour pattern .*N.*
    }

    dag.account_taxonomy.update_taxonomy(explicit_mappings, 0)
    print("✅ Taxonomie configurée")

    # Transaction Test 16 exacte
    source_measure = TransactionMeasure(
        measure_id="agriculture_debit",
        account_id="alice_farm",
        primary_regex_pattern=".*N.*",
        primary_regex_weight=Decimal('1.2'),
        acceptable_value=Decimal('1000'),
        secondary_patterns=[]
    )

    target_measure = TransactionMeasure(
        measure_id="industry_credit",
        account_id="bob_factory",
        primary_regex_pattern=".*N.*",
        primary_regex_weight=Decimal('0.9'),
        acceptable_value=Decimal('0'),
        required_value=Decimal('100'),
        secondary_patterns=[]
    )

    transaction = Transaction(
        transaction_id="debug_final_tx",
        source_account_id="alice_farm",
        target_account_id="bob_factory",
        amount=Decimal('150'),
        source_measures=[source_measure],
        target_measures=[target_measure]
    )

    print("✅ Transaction créée")

    # ÉTAPE 1: Validation NFA explosion
    print("\n=== ÉTAPE 1: Validation NFA Explosion ===")
    try:
        nfa_explosion_ok = dag._validate_transaction_nfa_explosion(transaction)
        print(f"NFA explosion validation: {nfa_explosion_ok}")
    except Exception as e:
        print(f"❌ Erreur NFA explosion: {e}")
        return False

    # ÉTAPE 2: Création comptes (si nécessaire)
    print("\n=== ÉTAPE 2: Création Comptes ===")
    try:
        dag._extract_accounts_from_transaction(transaction)
        print(f"Comptes créés: {list(dag.accounts.keys())}")
        print(f"Nodes créés: {list(dag.nodes.keys())}")
        print(f"Edges créés: {list(dag.edges.keys())}")

        # Vérification structure comptes
        for account_id, account in dag.accounts.items():
            source_edges = len(account.source_node.outgoing_edges)
            sink_edges = len(account.sink_node.incoming_edges)
            print(f"  {account_id}: source_edges={source_edges}, sink_edges={sink_edges}")

    except Exception as e:
        print(f"❌ Erreur création comptes: {e}")
        return False

    # ÉTAPE 3: Validation Simplex
    print("\n=== ÉTAPE 3: Validation Simplex ===")
    try:
        simplex_result = dag._validate_transaction_simplex(transaction)
        print(f"Simplex validation: {simplex_result}")

        if not simplex_result:
            print("❌ Simplex infeasible - Diagnostic approfondi...")

            # Debug NFA temporaire
            print("\n--- Debug NFA Temporaire ---")
            temp_nfa = dag._create_temporary_nfa_for_transaction(transaction)
            print(f"NFA temporaire type: {type(temp_nfa)}")

            if hasattr(temp_nfa, 'shared_nfa'):
                shared_stats = temp_nfa.shared_nfa.get_stats()
                print(f"SharedNFA stats: {shared_stats}")

            temp_nfa.freeze()

            # Test évaluation directe
            print("\n--- Test Évaluation NFA Directe ---")
            test_words = ["N", "NB", "BN", "ZN", "NZ"]
            for word in test_words:
                result = temp_nfa.evaluate_to_final_state(word)
                print(f"  '{word}' → {result}")

            # Test get_state_weights_for_measure
            print("\n--- Test State Weights ---")
            agri_weights = temp_nfa.get_state_weights_for_measure("agriculture_debit")
            indu_weights = temp_nfa.get_state_weights_for_measure("industry_credit")
            print(f"  Agriculture weights: {agri_weights}")
            print(f"  Industry weights: {indu_weights}")

            # Debug path enumeration
            print("\n--- Debug Path Enumeration ---")
            temp_edge = dag._create_temporary_transaction_edge(transaction)
            print(f"Temp edge: {temp_edge.edge_id}")
            print(f"  Source: {temp_edge.source_node.node_id}")
            print(f"  Target: {temp_edge.target_node.node_id}")

            # Énumération manuelle
            paths_found = []
            try:
                for path in dag.path_enumerator.enumerate_paths_from_transaction(
                    temp_edge, dag.transaction_counter
                ):
                    paths_found.append(path)
                    path_str = " → ".join(node.node_id for node in path)
                    print(f"  Chemin: {path_str}")

                    if len(paths_found) >= 5:  # Limite debug
                        break

                print(f"Total chemins trouvés: {len(paths_found)}")

                if paths_found:
                    print("\n--- Debug Conversion Mots ---")
                    for i, path in enumerate(paths_found[:3]):
                        try:
                            word = dag.account_taxonomy.convert_path_to_word(path, dag.transaction_counter)
                            print(f"  Chemin {i}: {word}")

                            # Test classification NFA
                            final_state = temp_nfa.evaluate_to_final_state(word)
                            print(f"    NFA classification: {final_state}")

                        except Exception as e:
                            print(f"    ❌ Erreur conversion: {e}")

                else:
                    print("❌ AUCUN CHEMIN TROUVÉ")

            except Exception as e:
                print(f"❌ Erreur path enumeration: {e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"❌ Erreur validation Simplex: {e}")
        import traceback
        traceback.print_exc()
        return False

    return simplex_result


def debug_dag_state(dag):
    """Debug état interne DAG"""
    print(f"\n=== ÉTAT DAG ===")
    print(f"Accounts: {len(dag.accounts)}")
    print(f"Nodes: {len(dag.nodes)}")
    print(f"Edges: {len(dag.edges)}")
    print(f"Transaction counter: {dag.transaction_counter}")

    if dag.anchored_nfa:
        print(f"NFA permanent: {type(dag.anchored_nfa)}")
        if hasattr(dag.anchored_nfa, 'shared_nfa'):
            stats = dag.anchored_nfa.shared_nfa.get_stats()
            print(f"  SharedNFA stats: {stats}")


if __name__ == "__main__":
    success = debug_test16_detailed()

    if success:
        print("\n🎉 SUCCESS: Test 16 pipeline réussi!")
    else:
        print("\n❌ FAILED: Problèmes pipeline identifiés")