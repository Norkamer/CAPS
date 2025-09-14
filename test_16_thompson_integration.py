#!/usr/bin/env python3
"""
Test 16 avec nouvelle architecture Thompson's NFA
Validation règle d'or intégrée dans pipeline DAG complet
"""

from decimal import Decimal, getcontext
import sys
import os

getcontext().prec = 50

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'icgs_core'))

# Imports directs pour éviter problèmes modules
from dag import DAG, DAGConfiguration
from dag_structures import Transaction, TransactionMeasure


def test_16_thompson_integration():
    """Test intégration Thompson's avec pipeline DAG Test 16"""
    print("=== TEST 16 THOMPSON'S INTEGRATION ===")

    # Configuration DAG identique
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

    # Configuration taxonomie manuelle
    explicit_mappings = {
        "alice_farm_source": "A",
        "alice_farm_sink": "Z",
        "bob_factory_source": "B",
        "bob_factory_sink": "N",  # N pour pattern .*N.*
    }

    dag.account_taxonomy.update_taxonomy(explicit_mappings, 0)

    print("✅ DAG initialisé avec taxonomie")

    # Transaction Test 16 identique
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
        transaction_id="tx_thompson_test",
        source_account_id="alice_farm",
        target_account_id="bob_factory",
        amount=Decimal('150'),
        source_measures=[source_measure],
        target_measures=[target_measure]
    )

    print("✅ Transaction Test 16 créée")

    # Test pipeline complet
    print("\n=== PIPELINE DAG.add_transaction() ===")

    try:
        success = dag.add_transaction(transaction)
        print(f"Pipeline result: {success}")

        # Statistiques DAG
        print(f"\nDAG stats: {dag.stats}")

        # Validation NFA Thompson's
        if hasattr(dag, 'anchored_nfa') and dag.anchored_nfa:
            nfa = dag.anchored_nfa
            print(f"\nNFA type: {type(nfa).__name__}")

            if hasattr(nfa, 'shared_nfa'):
                shared_stats = nfa.shared_nfa.get_stats()
                print(f"SharedNFA stats: {shared_stats}")

                # Test évaluation directe
                print(f"\n=== ÉVALUATION NFA DIRECTE ===")
                test_words = ["N", "NB", "BN", "A"]

                nfa.freeze()
                for word in test_words:
                    result = nfa.evaluate_to_final_state(word)
                    print(f"'{word}' → {result}")

                # Test get_state_weights_for_measure
                print(f"\n=== POIDS NFA ===")
                agri_weights = nfa.get_state_weights_for_measure("agriculture_debit")
                indu_weights = nfa.get_state_weights_for_measure("industry_credit")

                print(f"Agriculture: {agri_weights}")
                print(f"Industry: {indu_weights}")

        return success

    except Exception as e:
        print(f"❌ ERREUR pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = test_16_thompson_integration()

    if result:
        print("\n🎉 SUCCESS: Test 16 avec Thompson's architecture!")
    else:
        print("\n❌ FAILED: Problème intégration Thompson's")