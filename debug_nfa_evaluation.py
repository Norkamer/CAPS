#!/usr/bin/env python3
"""
Debug spécifique évaluation NFA
"""

import re
from decimal import Decimal, getcontext
getcontext().prec = 50

from icgs_core import AnchoredWeightedNFA

def test_nfa_patterns():
    """Test patterns NFA directement"""
    print("=== DEBUG NFA PATTERNS ===")

    # Test pattern brut
    pattern = ".*N.*"
    word = "NB"

    print(f"Pattern: '{pattern}'")
    print(f"Word: '{word}'")
    print(f"Python re.match: {bool(re.match(pattern, word))}")
    print(f"Python re.search: {bool(re.search(pattern, word))}")

    # Test pattern ancré
    anchored_pattern = f".*{pattern}$"
    print(f"\nAnchored pattern: '{anchored_pattern}'")
    print(f"Python re.match: {bool(re.match(anchored_pattern, word))}")
    print(f"Python re.search: {bool(re.search(anchored_pattern, word))}")

    # Test NFA ICGS
    print("\n=== TEST NFA ICGS ===")
    nfa = AnchoredWeightedNFA("test_nfa")

    # Ajout patterns identiques au debug
    agriculture_state = nfa.add_weighted_regex(
        "agriculture_debit",
        ".*N.*",
        Decimal('1.2'),
        "source_agriculture_debit"
    )

    industry_state = nfa.add_weighted_regex(
        "industry_credit",
        ".*N.*",
        Decimal('0.9'),
        "target_industry_credit"
    )

    print(f"États finaux avant freeze: {len(nfa.get_final_states())}")
    for state in nfa.get_final_states():
        print(f"  État {state.state_id}: regex_weights={len(state.regex_weights)}")

    # Freeze et test
    nfa.freeze()

    print(f"\nÉtats finaux après freeze: {len(nfa.frozen_final_states)}")
    for state in nfa.frozen_final_states:
        print(f"  État frozen {state.state_id}: regex_weights={len(state.regex_weights)}")

    # Test évaluation
    test_words = ["NB", "BN", "N", "B", "AB", ""]
    for test_word in test_words:
        result = nfa.evaluate_to_final_state(test_word)
        print(f"NFA eval '{test_word}': {result}")

    # Test évaluation détaillée pour NB
    print(f"\n=== DEBUG DÉTAILLÉ POUR 'NB' ===")
    try:
        # Utilisation méthode interne pour debug
        final_states = nfa._evaluate_with_frozen_snapshot("NB")
        print(f"États finaux atteints: {final_states}")

        if not final_states:
            print("❌ Aucun état final atteint")

            # Test des transitions step by step
            print("\n--- Debug transitions étape par étape ---")
            current_states = nfa._epsilon_closure_frozen({nfa.initial_state_id}) if nfa.initial_state_id else set()
            print(f"États initiaux après epsilon-closure: {current_states}")

            for i, symbol in enumerate("NB"):
                print(f"\nSymbole '{symbol}' (étape {i+1}):")
                next_states = set()

                for state_id in current_states:
                    print(f"  Depuis état {state_id}:")

                    # Vérification transitions frozen
                    matching_transitions = [
                        t for t in nfa.frozen_transitions
                        if t.from_state == state_id
                    ]
                    print(f"    Transitions disponibles: {len(matching_transitions)}")

                    for transition in matching_transitions:
                        print(f"    Transition: {transition.from_state} --{getattr(transition, 'pattern', 'no_pattern')}--> {transition.to_state}")
                        if hasattr(transition, 'matches') and transition.matches(symbol):
                            print(f"      ✅ Match symbole '{symbol}'")
                            next_states.add(transition.to_state)
                        else:
                            print(f"      ❌ Pas de match pour symbole '{symbol}'")

                current_states = nfa._epsilon_closure_frozen(next_states)
                print(f"  États après '{symbol}': {current_states}")

                if not current_states:
                    print(f"  ❌ Plus d'états - échec à l'étape {i+1}")
                    break

    except Exception as e:
        print(f"ERREUR debug détaillé: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_nfa_patterns()