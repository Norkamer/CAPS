#!/usr/bin/env python3
"""
Script de diagnostic pour debug path enumeration Test 16
"""

from decimal import Decimal, getcontext
getcontext().prec = 50

from icgs_core import (
    DAG, DAGConfiguration, Transaction, TransactionMeasure, Account,
    AnchoredWeightedNFA, AccountTaxonomy
)

def debug_path_enumeration():
    """Debug simple énumération chemins"""
    print("=== DEBUG PATH ENUMERATION ===")

    # Configuration DAG identique au test
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

    # Configuration taxonomie manuelle (identique au test)
    explicit_mappings = {
        "alice_farm_source": "A",
        "alice_farm_sink": "Z",
        "bob_factory_source": "B",
        "bob_factory_sink": "N",  # N pour pattern .*N.*
    }

    dag.account_taxonomy.update_taxonomy(explicit_mappings, 0)

    # Création transaction simple
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
        transaction_id="debug_tx",
        source_account_id="alice_farm",
        target_account_id="bob_factory",
        amount=Decimal('150'),
        source_measures=[source_measure],
        target_measures=[target_measure]
    )

    print(f"Transaction créée: {transaction.transaction_id}")

    # Étape 1: Création comptes manuellement
    print("\n=== ÉTAPE 1: Création comptes ===")
    try:
        new_accounts = dag._extract_accounts_from_transaction(transaction)
        print(f"Comptes créés: {list(dag.accounts.keys())}")
        print(f"Nodes créés: {list(dag.nodes.keys())}")
        print(f"Edges créés: {list(dag.edges.keys())}")

        # Vérification edges internes
        for account_id, account in dag.accounts.items():
            print(f"\nCompte {account_id}:")
            print(f"  - source_node: {account.source_node.node_id}")
            print(f"  - sink_node: {account.sink_node.node_id}")
            print(f"  - source outgoing edges: {len(account.source_node.outgoing_edges)}")
            print(f"  - sink incoming edges: {len(account.sink_node.incoming_edges)}")

    except Exception as e:
        print(f"ERREUR création comptes: {e}")
        return

    # Étape 2: Création NFA temporaire
    print("\n=== ÉTAPE 2: Création NFA temporaire ===")
    try:
        temp_nfa = dag._create_temporary_nfa_for_transaction(transaction)
        temp_nfa.freeze()
        print(f"NFA temporaire créé: {temp_nfa}")
        print(f"États finaux frozen: {len(temp_nfa.frozen_final_states)}")

        for state in temp_nfa.frozen_final_states:
            print(f"  État final {state.state_id}: {len(state.regex_weights)} regex_weights")

    except Exception as e:
        print(f"ERREUR création NFA: {e}")
        return

    # Étape 3: Création edge temporaire
    print("\n=== ÉTAPE 3: Création edge temporaire ===")
    try:
        temp_edge = dag._create_temporary_transaction_edge(transaction)
        print(f"Edge temporaire: {temp_edge.edge_id}")
        print(f"  Source: {temp_edge.source_node.node_id}")
        print(f"  Target: {temp_edge.target_node.node_id}")

    except Exception as e:
        print(f"ERREUR création edge: {e}")
        return

    # Étape 4: Énumération chemins
    print("\n=== ÉTAPE 4: Énumération chemins ===")
    try:
        path_classes = dag.path_enumerator.enumerate_and_classify(
            temp_edge, temp_nfa, dag.transaction_counter
        )
        print(f"Classes de chemins: {len(path_classes)}")

        for state_id, paths in path_classes.items():
            print(f"  État {state_id}: {len(paths)} chemins")

        if not path_classes:
            print("❌ AUCUN CHEMIN TROUVÉ - DIAGNOSTIC APPROFONDI")

            # Debug énumération manuelle
            print("\n--- Debug énumération manuelle ---")
            paths_found = []
            for path in dag.path_enumerator.enumerate_paths_from_transaction(temp_edge, dag.transaction_counter):
                paths_found.append(path)
                print(f"Chemin trouvé: {[node.node_id for node in path]}")
                if len(paths_found) >= 5:  # Limite pour debug
                    break

            print(f"Total chemins énumérés: {len(paths_found)}")

            if paths_found:
                print("\n--- Debug conversion mots ---")
                for i, path in enumerate(paths_found[:3]):
                    try:
                        word = dag.account_taxonomy.convert_path_to_word(path, dag.transaction_counter)
                        print(f"Chemin {i}: {[node.node_id for node in path]} → mot: '{word}'")

                        # Test évaluation NFA
                        final_state_id = temp_nfa.evaluate_to_final_state(word)
                        print(f"  NFA évaluation: {final_state_id}")

                    except Exception as e:
                        print(f"  ERREUR conversion/évaluation: {e}")

    except Exception as e:
        print(f"ERREUR énumération: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_path_enumeration()