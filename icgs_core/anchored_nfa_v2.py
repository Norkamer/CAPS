#!/usr/bin/env python3
"""
AnchoredWeightedNFA v2 - Version Thompson's avec anchoring automatique
API compatible mais architecture SharedNFA rigoureuse
"""

import re
import copy
import time
from typing import Dict, List, Optional, Set, Any
from decimal import Decimal

try:
    from .weighted_nfa_v2 import WeightedNFA, RegexWeight, create_weighted_nfa
except ImportError:
    from weighted_nfa_v2 import WeightedNFA, RegexWeight, create_weighted_nfa


class AnchoredWeightedNFA(WeightedNFA):
    """
    AnchoredWeightedNFA v2 avec Thompson's core

    Fonctionnalités:
    - Ancrage automatique patterns (.*pattern$ si nécessaire)
    - États frozen pour énumération cohérente
    - API compatible avec version précédente
    - SharedNFA Thompson's interne
    """

    def __init__(self, name: str = "anchored_nfa"):
        super().__init__(name)

        # Anchoring features
        self.anchoring_enabled = True
        self.frozen_final_states: List[Any] = []  # Compatibility

        # HYBRID DUAL-NFA: Metadata support for external NFAs
        self.metadata = {}

        # Stats anchoring
        self.stats.update({
            'patterns_anchored': 0,
            'freeze_operations': 0,
            'frozen_evaluations': 0,
            'anchor_transformations': 0
        })

    def add_weighted_regex(self, measure_id: str, regex_pattern: str,
                          weight: Decimal, regex_id: Optional[str] = None) -> 'NFAStateProxy':
        """
        Ajoute regex avec ancrage automatique

        Args:
            measure_id: Identifiant mesure économique
            regex_pattern: Pattern regex (sera ancré automatiquement)
            weight: Poids associé
            regex_id: Identifiant regex

        Returns:
            Proxy état final pour compatibility
        """
        if self.shared_nfa.is_frozen:
            self.shared_nfa.unfreeze()

        # ANCRAGE AUTOMATIQUE selon blueprint
        anchored_pattern = self._apply_automatic_anchoring(regex_pattern)

        if anchored_pattern != regex_pattern:
            self.stats['anchor_transformations'] += 1
            self.stats['patterns_anchored'] += 1

        # Délégation au WeightedNFA parent avec pattern ancré
        final_state = super().add_weighted_regex_simple(
            measure_id, anchored_pattern, weight, regex_id
        )

        # Métadonnées anchoring pour debugging
        final_state.metadata.update({
            'original_pattern': regex_pattern,
            'anchored_pattern': anchored_pattern,
            'was_anchored': anchored_pattern != regex_pattern
        })

        return final_state

    def _apply_automatic_anchoring(self, regex_pattern: str) -> str:
        """
        Applique ancrage automatique selon Blueprint ICGS

        Transformation: "N" → ".*N.*$" pour match complet
        Préserve ancres existantes (^ et $)
        """
        if not self.anchoring_enabled:
            return regex_pattern

        # Validation pattern basique
        try:
            re.compile(regex_pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{regex_pattern}': {e}")

        # Ancrage automatique si pas déjà ancré
        if not regex_pattern.endswith('$'):
            if regex_pattern.startswith('^'):
                # "^A.*" → "^A.*$" (préserve ancre début)
                anchored_pattern = f"{regex_pattern}$"
            elif regex_pattern.startswith('.*'):
                # ".*N.*" → ".*N.*$"
                anchored_pattern = f"{regex_pattern}$"
            else:
                # "N" → ".*N.*$"
                anchored_pattern = f".*{regex_pattern}.*$"
        else:
            anchored_pattern = regex_pattern

        # Validation pattern ancré
        try:
            re.compile(anchored_pattern)
        except re.error as e:
            raise ValueError(f"Invalid anchored pattern '{anchored_pattern}': {e}")

        return anchored_pattern

    def freeze(self) -> None:
        """
        Fige NFA pour énumération cohérente

        Capture snapshot états finaux et transitions.
        Bloque modifications ultérieures.
        """
        if self.shared_nfa.is_frozen:
            return

        # Freeze SharedNFA core
        self.shared_nfa.freeze()

        # Capture snapshot états finaux pour compatibility
        self.frozen_final_states = self.get_final_states().copy()

        self.stats['freeze_operations'] += 1

    def unfreeze(self) -> None:
        """
        Dégèle NFA pour permettre modifications

        Restaure capacité modification après énumération.
        """
        self.shared_nfa.unfreeze()
        self.frozen_final_states = []

    def evaluate_to_final_state(self, word: str) -> Optional[str]:
        """
        Évaluation mot vers état final

        Args:
            word: Mot à évaluer

        Returns:
            ID état final ou None
        """
        if not self.shared_nfa.is_frozen:
            self.shared_nfa.freeze()

        self.stats['frozen_evaluations'] += 1

        try:
            return self.shared_nfa.evaluate_word_to_final(word)
        except Exception:
            return None

    def get_state_weights_for_measure(self, measure_id: str) -> Dict[str, Decimal]:
        """
        Récupère poids par état pour mesure donnée

        Args:
            measure_id: Identifiant mesure économique

        Returns:
            Dict state_id → weight
        """
        # Délégation directe au SharedNFA
        return self.shared_nfa.get_state_weights_for_measure(measure_id)

    def get_final_state_classifications(self) -> Dict[str, List[RegexWeight]]:
        """
        Extraction classifications pour construction LP

        Returns:
            Dict state_id → [RegexWeights]
        """
        classifications = {}

        # Conversion depuis SharedNFA classifications vers format RegexWeight
        shared_classifications = self.shared_nfa.get_final_state_classifications()

        for state_id, measures in shared_classifications.items():
            regex_weights = []

            for measure_id, weight in measures:
                if measure_id in self.regex_weights_registry:
                    regex_weights.append(self.regex_weights_registry[measure_id])

            if regex_weights:
                classifications[state_id] = regex_weights

        return classifications

    def _is_properly_anchored(self, pattern: str) -> bool:
        """Vérifie si pattern correctement ancré"""
        return pattern.endswith('$')

    def get_anchoring_stats(self) -> Dict[str, Any]:
        """Statistiques anchoring pour debugging"""
        return {
            'anchoring_enabled': self.anchoring_enabled,
            'patterns_anchored': self.stats['patterns_anchored'],
            'anchor_transformations': self.stats['anchor_transformations'],
            'frozen_evaluations': self.stats['frozen_evaluations'],
            'freeze_operations': self.stats['freeze_operations']
        }

    @property
    def is_frozen(self) -> bool:
        """Compatibility property"""
        return self.shared_nfa.is_frozen

    def __repr__(self) -> str:
        frozen_info = " [FROZEN]" if self.is_frozen else ""
        return (f"AnchoredWeightedNFA(name='{self.name}', states={len(self.shared_nfa.states)}, "
                f"transitions={len(self.shared_nfa.transitions)}, "
                f"final_states={len(self.shared_nfa.final_state_ids)}, "
                f"anchored_patterns={self.stats.get('patterns_anchored', 0)}{frozen_info})")


def create_anchored_nfa(name: str = "anchored_nfa") -> AnchoredWeightedNFA:
    """Factory AnchoredWeightedNFA v2"""
    return AnchoredWeightedNFA(name)


if __name__ == "__main__":
    # Tests AnchoredWeightedNFA v2
    print("=== AnchoredWeightedNFA v2 Tests ===")

    nfa = create_anchored_nfa("test_anchored")

    print("\n1. Test ancrage automatique...")

    # Test patterns avec et sans ancrage
    test_patterns = [
        ("N", ".*N.*$"),
        (".*N.*", ".*N.*$"),
        ("^A.*", "^A.*$"),
        (".*B$", ".*B$")  # Déjà ancré
    ]

    for original, expected in test_patterns:
        anchored = nfa._apply_automatic_anchoring(original)
        print(f"'{original}' → '{anchored}' (expected: '{expected}')")
        assert anchored == expected, f"Anchoring failed for {original}"

    print("\n2. Ajout mesures Test 16...")
    state1 = nfa.add_weighted_regex(
        "agriculture_debit", ".*N.*", Decimal('1.2'), "source_agriculture"
    )
    state2 = nfa.add_weighted_regex(
        "industry_credit", ".*N.*", Decimal('0.9'), "target_industry"
    )

    print(f"State 1: {state1}")
    print(f"State 2: {state2}")
    print(f"Anchoring stats: {nfa.get_anchoring_stats()}")

    print("\n3. Freeze et évaluation...")
    nfa.freeze()
    print(f"Frozen: {nfa.is_frozen}")

    test_words = ["N", "NB", "BN", "A", ""]
    for word in test_words:
        result = nfa.evaluate_to_final_state(word)
        print(f"'{word}' → {result}")

    print("\n4. Test get_state_weights_for_measure...")
    agri_weights = nfa.get_state_weights_for_measure("agriculture_debit")
    indu_weights = nfa.get_state_weights_for_measure("industry_credit")

    print(f"Agriculture weights: {agri_weights}")
    print(f"Industry weights: {indu_weights}")

    print("\n5. Classifications finales...")
    classifications = nfa.get_final_state_classifications()
    for state_id, weights in classifications.items():
        print(f"State {state_id}: {[str(w) for w in weights]}")

    print(f"\nFinal NFA: {nfa}")