#!/usr/bin/env python3
"""
WeightedNFA v2 - Refactored avec SharedNFA core
API compatible avec version précédente mais architecture Thompson's rigoureuse
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from decimal import Decimal
from dataclasses import dataclass
import time

try:
    from .shared_nfa import SharedNFA, create_shared_nfa
except ImportError:
    from shared_nfa import SharedNFA, create_shared_nfa


@dataclass
class RegexWeight:
    """Structure poids regex pour compatibility API"""
    measure_id: str
    regex_id: str
    weight: Decimal

    def __str__(self) -> str:
        return f"RegexWeight(measure={self.measure_id}, regex={self.regex_id}, weight={self.weight})"


class WeightedNFA:
    """
    WeightedNFA v2 avec SharedNFA Thompson's core

    Préserve API existante mais utilise architecture SharedNFA interne
    pour respect rigoureux règle d'or: 1 caractère = 1 transition
    """

    def __init__(self, name: str = "weighted_nfa"):
        self.name = name
        self.shared_nfa = create_shared_nfa(f"core_{name}")

        # Compatibility layers
        self.regex_weights_registry: Dict[str, RegexWeight] = {}
        self._measure_counter = 0

        # Stats pour compatibility
        self.stats = {
            'regex_patterns_added': 0,
            'words_evaluated': 0,
            'states_created': 0,
            'validation_errors': 0
        }

    def add_weighted_regex_simple(self, measure_id: str, regex_pattern: str,
                                 weight: Decimal, regex_id: Optional[str] = None) -> 'NFAStateProxy':
        """
        Interface compatibility avec API précédente

        Args:
            measure_id: Identifiant mesure économique
            regex_pattern: Pattern regex
            weight: Poids associé
            regex_id: Identifiant regex (généré si None)

        Returns:
            Proxy NFAState pour compatibility
        """
        if regex_id is None:
            self._measure_counter += 1
            regex_id = f"regex_{self._measure_counter}"

        # Enregistrement RegexWeight pour compatibility
        regex_weight = RegexWeight(measure_id, regex_id, weight)
        self.regex_weights_registry[measure_id] = regex_weight

        # Ajout mesure dans SharedNFA
        success = self.shared_nfa.add_measure(measure_id, regex_pattern, weight)

        if success:
            self.stats['regex_patterns_added'] += 1
            self.stats['states_created'] += 1  # Approximation

            # Création proxy état final pour compatibility
            return NFAStateProxy(measure_id, regex_id, [regex_weight])

        raise RuntimeError(f"Failed to add weighted regex for measure {measure_id}")

    def evaluate_word(self, word: str) -> Tuple[Optional[str], bool]:
        """
        Évaluation mot avec API compatibility

        Returns:
            Tuple (final_state_id, acceptance) pour compatibility ancienne API
        """
        self.stats['words_evaluated'] += 1

        if not self.shared_nfa.is_frozen:
            self.shared_nfa.freeze()

        try:
            final_state_id = self.shared_nfa.evaluate_word_to_final(word)
            acceptance = final_state_id is not None

            return (final_state_id, acceptance)

        except Exception as e:
            self.stats['validation_errors'] += 1
            return (None, False)

    def get_final_states(self) -> List['NFAStateProxy']:
        """
        Récupération états finaux avec proxy compatibility

        Returns:
            Liste proxy states pour compatibility API
        """
        final_states = []

        for measure_id, entry_point in self.shared_nfa.entry_points.items():
            if measure_id in self.regex_weights_registry:
                regex_weight = self.regex_weights_registry[measure_id]

                proxy = NFAStateProxy(
                    measure_id,
                    regex_weight.regex_id,
                    [regex_weight]
                )
                final_states.append(proxy)

        return final_states

    def freeze_for_enumeration(self) -> None:
        """Freeze SharedNFA pour énumération"""
        self.shared_nfa.freeze()

    def unfreeze(self) -> None:
        """Unfreeze SharedNFA"""
        self.shared_nfa.unfreeze()

    def get_regex_weights_for_state(self, state_id: str) -> List[RegexWeight]:
        """
        Compatibility method pour récupération poids

        Args:
            state_id: Peut être measure_id ou state_id interne

        Returns:
            Liste RegexWeights associés
        """
        # Tentative match direct measure_id
        if state_id in self.regex_weights_registry:
            return [self.regex_weights_registry[state_id]]

        # Recherche dans classifications SharedNFA
        classifications = self.shared_nfa.get_final_state_classifications()

        for final_state_id, measures in classifications.items():
            if final_state_id == state_id:
                weights = []
                for measure_id, weight in measures:
                    if measure_id in self.regex_weights_registry:
                        weights.append(self.regex_weights_registry[measure_id])
                return weights

        return []

    def validate_nfa_structure(self) -> List[str]:
        """
        Validation structure NFA - délégué au SharedNFA

        Returns:
            Liste erreurs (vide si valide)
        """
        errors = []

        if not self.shared_nfa.states:
            errors.append("No states defined in SharedNFA")

        if not self.shared_nfa.transitions:
            errors.append("No transitions defined in SharedNFA")

        if not self.shared_nfa.initial_state_id:
            errors.append("No initial state defined in SharedNFA")

        if not self.shared_nfa.final_state_ids:
            errors.append("No final states defined in SharedNFA")

        return errors

    def get_shared_nfa_stats(self) -> Dict[str, Any]:
        """Accès stats SharedNFA pour debugging"""
        return self.shared_nfa.get_stats()

    def __str__(self) -> str:
        return (f"WeightedNFA_v2(name='{self.name}', "
                f"measures={len(self.regex_weights_registry)}, "
                f"shared_states={len(self.shared_nfa.states)})")


class NFAStateProxy:
    """
    Proxy NFAState pour compatibility API existante

    Émule comportement anciens NFAState sans duplication états Thompson's
    """

    def __init__(self, measure_id: str, state_id: str, regex_weights: List[RegexWeight]):
        self.state_id = f"{measure_id}_{state_id}_final"  # Format compatibility
        self.measure_id = measure_id
        self.is_final = True  # Toujours final pour compatibility
        self.regex_weights = regex_weights
        self.metadata = {
            'measure_id': measure_id,
            'is_proxy': True,
            'original_state_id': state_id
        }

    def __str__(self) -> str:
        return f"NFAStateProxy[{self.state_id}]({len(self.regex_weights)} weights)"


def create_weighted_nfa(name: str = "weighted_nfa") -> WeightedNFA:
    """Factory WeightedNFA v2"""
    return WeightedNFA(name)


if __name__ == "__main__":
    # Tests compatibility WeightedNFA v2
    print("=== WeightedNFA v2 Tests ===")

    nfa = create_weighted_nfa("test_v2")

    print("\n1. Ajout patterns...")

    # Test patterns identiques Test 16
    state1 = nfa.add_weighted_regex_simple(
        "agriculture_debit", ".*N.*", Decimal('1.2'), "source_agriculture"
    )
    print(f"State 1: {state1}")

    state2 = nfa.add_weighted_regex_simple(
        "industry_credit", ".*N.*", Decimal('0.9'), "target_industry"
    )
    print(f"State 2: {state2}")

    print(f"NFA: {nfa}")

    print("\n2. Validation structure...")
    errors = nfa.validate_nfa_structure()
    print(f"Validation errors: {errors}")

    print("\n3. Évaluation mots...")
    test_words = ["N", "NB", "BN", "A"]

    for word in test_words:
        result = nfa.evaluate_word(word)
        print(f"'{word}' → {result}")

    print("\n4. États finaux...")
    final_states = nfa.get_final_states()
    for state in final_states:
        print(f"Final state: {state}")

    print("\n5. SharedNFA stats...")
    shared_stats = nfa.get_shared_nfa_stats()
    print(f"SharedNFA: {shared_stats}")