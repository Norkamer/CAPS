#!/usr/bin/env python3
"""
SharedNFA ICGS - NFA partagé avec entry points factorisés
Architecture centrale respectant règle d'or: 1 caractère = 1 transition
"""

import time
import copy
from typing import Dict, List, Optional, Set, Tuple, Any
from decimal import Decimal
from dataclasses import dataclass, field

try:
    from .thompson_nfa import (
        ThompsonNFABuilder, PatternFragment, NFAState, NFATransition,
        TransitionType, EntryPoint, create_thompson_builder
    )
except ImportError:
    from thompson_nfa import (
        ThompsonNFABuilder, PatternFragment, NFAState, NFATransition,
        TransitionType, EntryPoint, create_thompson_builder
    )


@dataclass
class FrozenSnapshot:
    """Snapshot frozen pour évaluation cohérente"""
    states: Dict[str, NFAState]
    transitions: List[NFATransition]
    entry_points: Dict[str, EntryPoint]
    final_state_ids: Set[str]
    frozen_at: float = field(default_factory=time.time)


class SharedNFA:
    """
    NFA partagé ICGS avec règle d'or stricte

    Fonctionnalités:
    - États Thompson's mutualisés entre patterns
    - Entry points avec poids factorisés
    - Extension incrémentale single-threaded
    - Frozen snapshots pour cohérence énumération
    - Évaluation caractère par caractère rigoureuse
    """

    def __init__(self, name: str = "shared_nfa"):
        self.name = name

        # Core Thompson's states
        self.states: Dict[str, NFAState] = {}
        self.transitions: List[NFATransition] = []
        self.initial_state_id: Optional[str] = None

        # ICGS Extensions
        self.entry_points: Dict[str, EntryPoint] = {}  # measure_id → EntryPoint
        self.pattern_registry: Dict[str, PatternFragment] = {}  # pattern → fragment
        self.final_state_ids: Set[str] = set()

        # Lifecycle management
        self.is_frozen: bool = False
        self.frozen_snapshot: Optional[FrozenSnapshot] = None

        # Construction tools
        self.thompson_builder = create_thompson_builder()

        # Stats
        self.stats = {
            'patterns_added': 0,
            'measures_added': 0,
            'states_created': 0,
            'transitions_created': 0,
            'freeze_operations': 0,
            'evaluations_performed': 0
        }

    def add_measure(self, measure_id: str, pattern: str, weight: Decimal) -> bool:
        """
        Ajoute mesure économique avec extension incrémentale NFA

        Args:
            measure_id: Identifiant mesure unique
            pattern: Pattern regex (ex: ".*N.*")
            weight: Poids économique factorisé

        Returns:
            True si ajout réussi, False si erreur
        """
        if self.is_frozen:
            self.unfreeze()

        try:
            # Pattern déjà présent → réutiliser fragment
            if pattern in self.pattern_registry:
                existing_fragment = self.pattern_registry[pattern]

                entry_point = EntryPoint(
                    measure_id=measure_id,
                    weight=weight,
                    start_state_id=existing_fragment.start_state_id,
                    pattern_hash=str(hash(pattern)),
                    pattern=pattern
                )

                self.entry_points[measure_id] = entry_point
                self.stats['measures_added'] += 1

                return True

            # Nouveau pattern → extension Thompson's incrémentale
            return self._extend_with_new_pattern(measure_id, pattern, weight)

        except Exception as e:
            print(f"Error adding measure {measure_id}: {e}")
            return False

    def _extend_with_new_pattern(self, measure_id: str, pattern: str, weight: Decimal) -> bool:
        """Extension NFA avec nouveau pattern Thompson's"""

        # Construction fragment Thompson's
        fragment = self.thompson_builder.build_pattern_fragment(pattern)

        # Intégration fragment dans NFA partagé
        self._integrate_fragment(fragment)

        # Enregistrement pattern
        self.pattern_registry[pattern] = fragment

        # Création entry point
        entry_point = EntryPoint(
            measure_id=measure_id,
            weight=weight,
            start_state_id=fragment.start_state_id,
            pattern_hash=str(hash(pattern)),
            pattern=pattern
        )

        self.entry_points[measure_id] = entry_point

        # Mise à jour stats
        self.stats['patterns_added'] += 1
        self.stats['measures_added'] += 1
        self.stats['states_created'] += len(fragment.all_state_ids)
        self.stats['transitions_created'] += len(fragment.transitions)

        return True

    def _integrate_fragment(self, fragment: PatternFragment) -> None:
        """Intègre fragment Thompson's dans NFA partagé"""

        # Ajout états
        for state_id in fragment.all_state_ids:
            if state_id not in self.states:
                is_final = state_id in fragment.final_state_ids
                self.states[state_id] = NFAState(state_id, is_final)

                if is_final:
                    self.final_state_ids.add(state_id)

        # Ajout transitions
        for transition in fragment.transitions:
            # Éviter doublons
            existing = any(
                t.from_state == transition.from_state and
                t.to_state == transition.to_state and
                t.transition_type == transition.transition_type and
                t.character == transition.character
                for t in self.transitions
            )

            if not existing:
                self.transitions.append(transition)

        # État initial global si pas encore défini
        if self.initial_state_id is None:
            self.initial_state_id = fragment.start_state_id

    def freeze(self) -> None:
        """
        Fige NFA pour énumération cohérente

        Crée snapshot immuable états/transitions/entry_points
        pour garantir cohérence pendant path enumeration.
        """
        if self.is_frozen:
            return

        # Deep copy pour immutabilité
        frozen_states = {}
        for state_id, state in self.states.items():
            frozen_states[state_id] = copy.deepcopy(state)

        frozen_transitions = copy.deepcopy(self.transitions)
        frozen_entry_points = copy.deepcopy(self.entry_points)

        self.frozen_snapshot = FrozenSnapshot(
            states=frozen_states,
            transitions=frozen_transitions,
            entry_points=frozen_entry_points,
            final_state_ids=self.final_state_ids.copy()
        )

        self.is_frozen = True
        self.stats['freeze_operations'] += 1

    def unfreeze(self) -> None:
        """Dégèle NFA pour permettre modifications"""
        self.is_frozen = False
        self.frozen_snapshot = None

    def evaluate_word_to_final(self, word: str) -> Optional[str]:
        """
        Évaluation mot avec règle d'or: 1 caractère = 1 transition

        Args:
            word: Mot à évaluer (ex: "NB")

        Returns:
            ID état final atteint ou None si rejet
        """
        if not self.is_frozen or not self.frozen_snapshot:
            raise RuntimeError("NFA must be frozen before evaluation")

        self.stats['evaluations_performed'] += 1

        # États initiaux depuis entry points
        if self.initial_state_id is None:
            return None

        current_states = self._epsilon_closure({self.initial_state_id})

        # Évaluation caractère par caractère
        for char in word:
            next_states = set()

            for state_id in current_states:
                for transition in self.frozen_snapshot.transitions:
                    if (transition.from_state == state_id and
                        transition.matches_character(char)):
                        next_states.add(transition.to_state)

            current_states = self._epsilon_closure(next_states)

            # Early termination si plus d'états
            if not current_states:
                return None

        # Vérification états finaux atteints
        final_reached = current_states & self.frozen_snapshot.final_state_ids

        if final_reached:
            # Retourne premier état final trouvé
            return next(iter(final_reached))

        return None

    def _epsilon_closure(self, states: Set[str]) -> Set[str]:
        """Calcul epsilon-closure avec frozen transitions"""
        if not self.frozen_snapshot:
            return states

        closure = set(states)
        stack = list(states)

        while stack:
            current = stack.pop()

            for transition in self.frozen_snapshot.transitions:
                if (transition.from_state == current and
                    transition.transition_type == TransitionType.EPSILON and
                    transition.to_state not in closure):
                    closure.add(transition.to_state)
                    stack.append(transition.to_state)

        return closure

    def get_state_weights_for_measure(self, measure_id: str) -> Dict[str, Decimal]:
        """
        Récupère poids pour mesure depuis entry points factorisés

        Args:
            measure_id: Identifiant mesure économique

        Returns:
            Dict state_id → weight (poids factorisé à l'entry point)
        """
        if measure_id not in self.entry_points:
            return {}

        entry_point = self.entry_points[measure_id]

        # Trouve états finaux atteignables depuis entry point
        reachable_finals = self._find_reachable_finals(entry_point.start_state_id)

        # Poids unique factorisé appliqué à tous états finaux atteignables
        return {
            final_state_id: entry_point.weight
            for final_state_id in reachable_finals
        }

    def _find_reachable_finals(self, start_state_id: str) -> Set[str]:
        """Trouve états finaux atteignables depuis état donné"""
        visited = set()
        reachable_finals = set()
        stack = [start_state_id]

        # Utilise transitions courantes ou frozen selon contexte
        transitions = (self.frozen_snapshot.transitions if self.frozen_snapshot
                      else self.transitions)
        final_states = (self.frozen_snapshot.final_state_ids if self.frozen_snapshot
                       else self.final_state_ids)

        while stack:
            current = stack.pop()
            if current in visited:
                continue

            visited.add(current)

            # Si état final, l'ajouter
            if current in final_states:
                reachable_finals.add(current)

            # Explorer transitions sortantes
            for transition in transitions:
                if (transition.from_state == current and
                    transition.to_state not in visited):
                    stack.append(transition.to_state)

        return reachable_finals

    def get_final_state_classifications(self) -> Dict[str, List[Tuple[str, Decimal]]]:
        """
        Extraction classifications pour construction LP

        Returns:
            Dict state_id → [(measure_id, weight), ...]
        """
        classifications = {}

        for measure_id, entry_point in self.entry_points.items():
            reachable_finals = self._find_reachable_finals(entry_point.start_state_id)

            for final_state_id in reachable_finals:
                if final_state_id not in classifications:
                    classifications[final_state_id] = []

                classifications[final_state_id].append((measure_id, entry_point.weight))

        return classifications

    def get_stats(self) -> Dict[str, Any]:
        """Statistiques SharedNFA pour monitoring"""
        return {
            **self.stats,
            'current_states': len(self.states),
            'current_transitions': len(self.transitions),
            'entry_points': len(self.entry_points),
            'patterns_registered': len(self.pattern_registry),
            'final_states': len(self.final_state_ids),
            'is_frozen': self.is_frozen,
            'initial_state': self.initial_state_id
        }

    def __str__(self) -> str:
        frozen_info = " [FROZEN]" if self.is_frozen else ""
        return (f"SharedNFA(name='{self.name}', states={len(self.states)}, "
                f"transitions={len(self.transitions)}, patterns={len(self.pattern_registry)}, "
                f"entry_points={len(self.entry_points)}{frozen_info})")


def create_shared_nfa(name: str = "icgs_shared_nfa") -> SharedNFA:
    """Factory SharedNFA pour ICGS"""
    return SharedNFA(name)


if __name__ == "__main__":
    # Tests SharedNFA ICGS
    nfa = create_shared_nfa("test_nfa")

    print("=== Test SharedNFA ===")

    # Ajout mesures Test 16
    print("\n1. Ajout mesures...")
    success1 = nfa.add_measure("agriculture_debit", ".*N.*", Decimal('1.2'))
    success2 = nfa.add_measure("industry_credit", ".*N.*", Decimal('0.9'))

    print(f"Agriculture added: {success1}")
    print(f"Industry added: {success2}")
    print(f"NFA stats: {nfa.get_stats()}")

    # Test freeze
    print("\n2. Freeze NFA...")
    nfa.freeze()
    print(f"Frozen: {nfa.is_frozen}")

    # Test évaluation
    print("\n3. Évaluation mots...")
    test_words = ["N", "NB", "BN", "A", ""]

    for word in test_words:
        result = nfa.evaluate_word_to_final(word)
        print(f"'{word}' → {result}")

    # Test weights
    print("\n4. Test get_state_weights_for_measure...")
    agri_weights = nfa.get_state_weights_for_measure("agriculture_debit")
    indu_weights = nfa.get_state_weights_for_measure("industry_credit")

    print(f"Agriculture weights: {agri_weights}")
    print(f"Industry weights: {indu_weights}")

    print(f"\nFinal NFA: {nfa}")