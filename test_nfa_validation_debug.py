#!/usr/bin/env python3
"""
Test spécifique de validation NFA pour debug Test 16
"""

from decimal import Decimal, getcontext
getcontext().prec = 50

from icgs_core import AnchoredWeightedNFA, TransactionMeasure

def test_nfa_construction_and_validation():
    """Test construction et validation NFA Test 16"""
    print("=== TEST NFA CONSTRUCTION & VALIDATION ===")

    # Création NFA identique au Test 16
    nfa = AnchoredWeightedNFA("transaction_0")

    # Mesures identiques au test
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

    print("=== AJOUT MESURES ===")

    # Ajout source measure
    print(f"Ajout source measure: {source_measure.measure_id}")
    try:
        source_state = nfa.add_weighted_regex(
            source_measure.measure_id,
            source_measure.primary_regex_pattern,
            source_measure.primary_regex_weight,
            regex_id=f"source_{source_measure.measure_id}"
        )
        print(f"✅ Source state créé: {source_state.state_id}")
        print(f"  RegexWeights: {len(source_state.regex_weights)}")
        for rw in source_state.regex_weights:
            print(f"    {rw}")
    except Exception as e:
        print(f"❌ ERREUR source measure: {e}")
        return

    # Ajout target measure
    print(f"\nAjout target measure: {target_measure.measure_id}")
    try:
        target_state = nfa.add_weighted_regex(
            target_measure.measure_id,
            target_measure.primary_regex_pattern,
            target_measure.primary_regex_weight,
            regex_id=f"target_{target_measure.measure_id}"
        )
        print(f"✅ Target state créé: {target_state.state_id}")
        print(f"  RegexWeights: {len(target_state.regex_weights)}")
        for rw in target_state.regex_weights:
            print(f"    {rw}")
    except Exception as e:
        print(f"❌ ERREUR target measure: {e}")
        return

    print("=== VALIDATION STRUCTURE NFA ===")

    # Test validation structure
    validation_errors = nfa.validate_nfa_structure()
    if validation_errors:
        print(f"❌ Erreurs validation: {validation_errors}")
    else:
        print("✅ Structure NFA valide")

    # État avant freeze
    print(f"\n=== ÉTAT AVANT FREEZE ===")
    print(f"États: {len(nfa.states)}")
    print(f"Transitions: {len(nfa.transitions)}")
    print(f"États finaux: {len(nfa.get_final_states())}")
    print(f"État initial: {nfa.initial_state_id}")

    for state_id, state in nfa.states.items():
        print(f"  État {state_id}: final={state.is_final}, regex_weights={len(state.regex_weights)}")

    for transition in nfa.transitions:
        print(f"  Transition: {transition.from_state} → {transition.to_state} ({transition.transition_type.value})")

    # Freeze et état après
    print(f"\n=== FREEZE NFA ===")
    nfa.freeze()

    print(f"États finaux frozen: {len(nfa.frozen_final_states)}")
    for state in nfa.frozen_final_states:
        print(f"  État frozen {state.state_id}: regex_weights={len(state.regex_weights)}")

    print(f"Transitions frozen: {len(nfa.frozen_transitions)}")

    print("=== TEST ÉVALUATION ===")

    # Test avec mots différents
    test_words = ["N", "B", "NB", "BN", ""]

    for word in test_words:
        result = nfa.evaluate_to_final_state(word)
        print(f"'{word}' → {result}")

        # Vérification get_state_weights_for_measure
        if result:
            source_weights = nfa.get_state_weights_for_measure("agriculture_debit")
            target_weights = nfa.get_state_weights_for_measure("industry_credit")
            print(f"  Source weights: {source_weights}")
            print(f"  Target weights: {target_weights}")

    print("=== TEST get_state_weights_for_measure ===")

    # Test méthode cruciale pour LP construction
    source_weights = nfa.get_state_weights_for_measure("agriculture_debit")
    target_weights = nfa.get_state_weights_for_measure("industry_credit")

    print(f"Source weights pour agriculture_debit: {source_weights}")
    print(f"Target weights pour industry_credit: {target_weights}")

    if not source_weights and not target_weights:
        print("❌ PROBLÈME: Aucun weight trouvé pour les mesures")

        # Debug approfondi
        print("\n--- Debug get_state_weights_for_measure ---")
        print("États finaux frozen:")
        for state in nfa.frozen_final_states:
            print(f"  État {state.state_id}:")
            for i, rw in enumerate(state.regex_weights):
                print(f"    RegexWeight {i}: measure_id={rw.measure_id}, regex_id={rw.regex_id}, weight={rw.weight}")

        # Test fonction manuelle
        print("\nTest manuel get_state_weights_for_measure:")
        for measure_id in ["agriculture_debit", "industry_credit"]:
            manual_weights = {}
            for state in nfa.frozen_final_states:
                for rw in state.regex_weights:
                    if rw.measure_id == measure_id:
                        manual_weights[state.state_id] = rw.weight
                        print(f"  Trouvé: {state.state_id} → {rw.weight} pour {measure_id}")
            print(f"  Manual weights pour {measure_id}: {manual_weights}")

if __name__ == "__main__":
    test_nfa_construction_and_validation()