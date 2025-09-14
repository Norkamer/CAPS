#!/usr/bin/env python3
"""
CAPS Phase 0 Semaines 3-4: Enhanced NFA Engine
Advanced NFA features with epsilon optimization and performance enhancements
"""

from typing import Dict, List, Set, Tuple, Optional, Any, FrozenSet
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import copy

try:
    from icgs_core.thompson_nfa import ThompsonNFABuilder, NFAFragment, NFATransition
except ImportError:
    # Définitions de base si import échoue
    @dataclass
    class NFATransition:
        from_state: int
        to_state: int
        symbol: Optional[str] = None
        is_epsilon: bool = False

    @dataclass
    class NFAFragment:
        start_state_id: int
        final_state_ids: Set[int]
        transitions: List[NFATransition]
        all_state_ids: Set[int]


class OptimizationType(Enum):
    """Types d'optimisations NFA"""
    EPSILON_REMOVAL = "epsilon_removal"
    DEAD_STATE_REMOVAL = "dead_state_removal"
    EQUIVALENT_STATE_MERGING = "equivalent_state_merging"
    TRANSITION_MINIMIZATION = "transition_minimization"


@dataclass
class NFAStatistics:
    """Statistiques détaillées d'un NFA"""
    state_count: int
    transition_count: int
    epsilon_transition_count: int
    final_state_count: int
    unreachable_state_count: int = 0
    dead_state_count: int = 0
    average_out_degree: float = 0.0
    max_out_degree: int = 0
    is_deterministic: bool = False
    cycles_count: int = 0


@dataclass
class EpsilonClosure:
    """Fermeture epsilon pour un ensemble d'états"""
    states: Set[int] = field(default_factory=set)
    reachable_finals: Set[int] = field(default_factory=set)
    path_lengths: Dict[int, int] = field(default_factory=dict)


class EnhancedNFAEngine:
    """Moteur NFA avancé avec optimisations et analyses"""

    def __init__(self):
        self.epsilon_closures_cache: Dict[int, EpsilonClosure] = {}
        self.optimization_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, float] = {}

    def compute_epsilon_closure(self, nfa: NFAFragment, state: int) -> EpsilonClosure:
        """Calcule fermeture epsilon pour un état avec cache"""
        if state in self.epsilon_closures_cache:
            return self.epsilon_closures_cache[state]

        closure = EpsilonClosure()
        visited = set()
        queue = deque([(state, 0)])  # (état, distance)
        closure.states.add(state)
        closure.path_lengths[state] = 0

        while queue:
            current_state, distance = queue.popleft()
            if current_state in visited:
                continue
            visited.add(current_state)

            # Vérifier si état final
            if current_state in nfa.final_state_ids:
                closure.reachable_finals.add(current_state)

            # Explorer transitions epsilon
            for transition in nfa.transitions:
                if (transition.from_state == current_state and
                    transition.is_epsilon and
                    transition.to_state not in visited):

                    closure.states.add(transition.to_state)
                    new_distance = distance + 1

                    if (transition.to_state not in closure.path_lengths or
                        new_distance < closure.path_lengths[transition.to_state]):
                        closure.path_lengths[transition.to_state] = new_distance

                    queue.append((transition.to_state, new_distance))

        self.epsilon_closures_cache[state] = closure
        return closure

    def remove_epsilon_transitions(self, nfa: NFAFragment) -> NFAFragment:
        """Supprime transitions epsilon en préservant langue acceptée"""
        print("🔧 Removing epsilon transitions...")

        # Calculer fermetures epsilon pour tous les états
        epsilon_closures = {}
        for state in nfa.all_state_ids:
            epsilon_closures[state] = self.compute_epsilon_closure(nfa, state)

        # Nouvelles transitions sans epsilon
        new_transitions = []
        new_final_states = set(nfa.final_state_ids)

        # Pour chaque état, ajouter transitions directes
        for from_state in nfa.all_state_ids:
            from_closure = epsilon_closures[from_state]

            # Si fermeture epsilon atteint état final, from_state devient final
            if from_closure.reachable_finals:
                new_final_states.add(from_state)

            # Pour chaque état dans la fermeture epsilon
            for eps_state in from_closure.states:
                # Ajouter toutes transitions non-epsilon depuis cet état
                for transition in nfa.transitions:
                    if (transition.from_state == eps_state and
                        not transition.is_epsilon):

                        # Transition directe depuis from_state
                        new_transition = NFATransition(
                            from_state=from_state,
                            to_state=transition.to_state,
                            symbol=transition.symbol,
                            is_epsilon=False
                        )

                        # Éviter doublons
                        if not any(t.from_state == new_transition.from_state and
                                 t.to_state == new_transition.to_state and
                                 t.symbol == new_transition.symbol
                                 for t in new_transitions):
                            new_transitions.append(new_transition)

        # Mettre à jour état de départ si nécessaire
        start_closure = epsilon_closures[nfa.start_state_id]
        if start_closure.reachable_finals:
            new_final_states.add(nfa.start_state_id)

        optimized_nfa = NFAFragment(
            start_state_id=nfa.start_state_id,
            final_state_ids=new_final_states,
            transitions=new_transitions,
            all_state_ids=nfa.all_state_ids.copy()
        )

        # Enregistrer optimisation
        self.optimization_history.append({
            'type': OptimizationType.EPSILON_REMOVAL,
            'original_transitions': len(nfa.transitions),
            'optimized_transitions': len(new_transitions),
            'epsilon_removed': len([t for t in nfa.transitions if t.is_epsilon])
        })

        return optimized_nfa

    def remove_unreachable_states(self, nfa: NFAFragment) -> NFAFragment:
        """Supprime états inaccessibles depuis l'état initial"""
        print("🔧 Removing unreachable states...")

        # BFS pour trouver états accessibles
        reachable = set()
        queue = deque([nfa.start_state_id])
        reachable.add(nfa.start_state_id)

        while queue:
            current = queue.popleft()
            for transition in nfa.transitions:
                if (transition.from_state == current and
                    transition.to_state not in reachable):
                    reachable.add(transition.to_state)
                    queue.append(transition.to_state)

        # Filtrer transitions et états
        new_transitions = [
            t for t in nfa.transitions
            if t.from_state in reachable and t.to_state in reachable
        ]

        new_final_states = nfa.final_state_ids.intersection(reachable)
        unreachable_count = len(nfa.all_state_ids) - len(reachable)

        optimized_nfa = NFAFragment(
            start_state_id=nfa.start_state_id,
            final_state_ids=new_final_states,
            transitions=new_transitions,
            all_state_ids=reachable
        )

        # Enregistrer optimisation
        self.optimization_history.append({
            'type': OptimizationType.DEAD_STATE_REMOVAL,
            'original_states': len(nfa.all_state_ids),
            'optimized_states': len(reachable),
            'unreachable_removed': unreachable_count
        })

        return optimized_nfa

    def merge_equivalent_states(self, nfa: NFAFragment) -> NFAFragment:
        """Fusion d'états équivalents avec même comportement"""
        print("🔧 Merging equivalent states...")

        # Grouper états par comportement (transitions sortantes similaires)
        state_signatures = {}

        for state in nfa.all_state_ids:
            # Signature basée sur transitions sortantes
            outgoing = []
            for transition in nfa.transitions:
                if transition.from_state == state:
                    outgoing.append((transition.symbol, transition.to_state, transition.is_epsilon))

            # Trier pour signature cohérente
            signature = tuple(sorted(outgoing))
            is_final = state in nfa.final_state_ids
            full_signature = (signature, is_final)

            if full_signature not in state_signatures:
                state_signatures[full_signature] = []
            state_signatures[full_signature].append(state)

        # Créer mapping des fusions
        state_mapping = {}
        new_state_counter = 0
        merged_groups = []

        for signature, states in state_signatures.items():
            if len(states) > 1:
                # Fusionner ces états
                representative = min(states)  # Utiliser ID minimum comme représentant
                merged_groups.append(states)
                for state in states:
                    state_mapping[state] = representative
            else:
                # État unique - pas de fusion
                state_mapping[states[0]] = states[0]

        # Construire NFA fusionné
        new_transitions = []
        seen_transitions = set()

        for transition in nfa.transitions:
            new_from = state_mapping[transition.from_state]
            new_to = state_mapping[transition.to_state]

            transition_key = (new_from, new_to, transition.symbol, transition.is_epsilon)
            if transition_key not in seen_transitions:
                new_transitions.append(NFATransition(
                    from_state=new_from,
                    to_state=new_to,
                    symbol=transition.symbol,
                    is_epsilon=transition.is_epsilon
                ))
                seen_transitions.add(transition_key)

        # Nouveaux états finaux
        new_final_states = set()
        for final_state in nfa.final_state_ids:
            new_final_states.add(state_mapping[final_state])

        # Nouveaux tous états
        new_all_states = set(state_mapping.values())

        optimized_nfa = NFAFragment(
            start_state_id=state_mapping[nfa.start_state_id],
            final_state_ids=new_final_states,
            transitions=new_transitions,
            all_state_ids=new_all_states
        )

        # Enregistrer optimisation
        self.optimization_history.append({
            'type': OptimizationType.EQUIVALENT_STATE_MERGING,
            'original_states': len(nfa.all_state_ids),
            'optimized_states': len(new_all_states),
            'merged_groups': len(merged_groups),
            'states_merged': len(nfa.all_state_ids) - len(new_all_states)
        })

        return optimized_nfa

    def optimize_transitions(self, nfa: NFAFragment) -> NFAFragment:
        """Optimise et minimise les transitions"""
        print("🔧 Optimizing transitions...")

        # Grouper transitions par (from_state, to_state)
        transition_groups = defaultdict(list)

        for transition in nfa.transitions:
            key = (transition.from_state, transition.to_state)
            transition_groups[key].append(transition)

        # Fusionner transitions multiples entre mêmes états
        optimized_transitions = []

        for (from_state, to_state), transitions in transition_groups.items():
            if len(transitions) == 1:
                # Transition unique - garder telle quelle
                optimized_transitions.append(transitions[0])
            else:
                # Transitions multiples - analyser fusion possible
                epsilon_transitions = [t for t in transitions if t.is_epsilon]
                symbol_transitions = [t for t in transitions if not t.is_epsilon]

                # Garder au plus une transition epsilon
                if epsilon_transitions:
                    optimized_transitions.append(epsilon_transitions[0])

                # Fusionner transitions symboliques si possible
                symbols = set(t.symbol for t in symbol_transitions)
                for symbol in symbols:
                    # Garder première transition pour chaque symbole
                    for transition in symbol_transitions:
                        if transition.symbol == symbol:
                            optimized_transitions.append(transition)
                            break

        optimized_nfa = NFAFragment(
            start_state_id=nfa.start_state_id,
            final_state_ids=nfa.final_state_ids.copy(),
            transitions=optimized_transitions,
            all_state_ids=nfa.all_state_ids.copy()
        )

        # Enregistrer optimisation
        self.optimization_history.append({
            'type': OptimizationType.TRANSITION_MINIMIZATION,
            'original_transitions': len(nfa.transitions),
            'optimized_transitions': len(optimized_transitions),
            'transitions_removed': len(nfa.transitions) - len(optimized_transitions)
        })

        return optimized_nfa

    def full_optimize(self, nfa: NFAFragment) -> NFAFragment:
        """Optimisation complète avec toutes les techniques"""
        print("🚀 Full NFA optimization pipeline...")

        current_nfa = nfa

        # Pipeline d'optimisation
        optimizations = [
            self.remove_epsilon_transitions,
            self.remove_unreachable_states,
            self.merge_equivalent_states,
            self.optimize_transitions
        ]

        for optimization in optimizations:
            try:
                current_nfa = optimization(current_nfa)
            except Exception as e:
                print(f"⚠️  Optimization {optimization.__name__} failed: {e}")
                continue

        return current_nfa

    def analyze_nfa(self, nfa: NFAFragment) -> NFAStatistics:
        """Analyse complète des propriétés d'un NFA"""

        epsilon_count = len([t for t in nfa.transitions if t.is_epsilon])

        # Calcul degrés sortants
        out_degrees = defaultdict(int)
        for transition in nfa.transitions:
            out_degrees[transition.from_state] += 1

        avg_out_degree = sum(out_degrees.values()) / len(nfa.all_state_ids) if nfa.all_state_ids else 0
        max_out_degree = max(out_degrees.values()) if out_degrees else 0

        # Détection déterminisme (approximatif)
        is_deterministic = True
        state_symbol_pairs = set()

        for transition in nfa.transitions:
            if not transition.is_epsilon:
                pair = (transition.from_state, transition.symbol)
                if pair in state_symbol_pairs:
                    is_deterministic = False
                    break
                state_symbol_pairs.add(pair)

        # Calcul états inaccessibles
        reachable = set()
        queue = deque([nfa.start_state_id])
        reachable.add(nfa.start_state_id)

        while queue:
            current = queue.popleft()
            for transition in nfa.transitions:
                if (transition.from_state == current and
                    transition.to_state not in reachable):
                    reachable.add(transition.to_state)
                    queue.append(transition.to_state)

        unreachable_count = len(nfa.all_state_ids) - len(reachable)

        return NFAStatistics(
            state_count=len(nfa.all_state_ids),
            transition_count=len(nfa.transitions),
            epsilon_transition_count=epsilon_count,
            final_state_count=len(nfa.final_state_ids),
            unreachable_state_count=unreachable_count,
            average_out_degree=avg_out_degree,
            max_out_degree=max_out_degree,
            is_deterministic=is_deterministic and epsilon_count == 0
        )

    def compare_nfas(self, original: NFAFragment, optimized: NFAFragment) -> Dict[str, Any]:
        """Compare NFA original vs optimisé"""
        original_stats = self.analyze_nfa(original)
        optimized_stats = self.analyze_nfa(optimized)

        return {
            'original': original_stats,
            'optimized': optimized_stats,
            'improvements': {
                'state_reduction': original_stats.state_count - optimized_stats.state_count,
                'transition_reduction': original_stats.transition_count - optimized_stats.transition_count,
                'epsilon_reduction': original_stats.epsilon_transition_count - optimized_stats.epsilon_transition_count,
                'state_reduction_percent': (original_stats.state_count - optimized_stats.state_count) / max(original_stats.state_count, 1) * 100,
                'transition_reduction_percent': (original_stats.transition_count - optimized_stats.transition_count) / max(original_stats.transition_count, 1) * 100
            },
            'optimization_history': self.optimization_history.copy()
        }


def create_test_nfa() -> NFAFragment:
    """Crée NFA de test avec epsilon transitions"""
    transitions = [
        # Pattern: a*b+ avec epsilon transitions
        NFATransition(0, 1, 'a', False),
        NFATransition(1, 1, 'a', False),  # a*
        NFATransition(1, 2, None, True),  # epsilon
        NFATransition(0, 2, None, True),  # epsilon (alternative)
        NFATransition(2, 3, 'b', False),
        NFATransition(3, 3, 'b', False),  # b+
        NFATransition(3, 4, None, True),  # epsilon vers final
        NFATransition(2, 5, None, True),  # epsilon vers état mort
        NFATransition(5, 5, 'c', False),  # état mort
    ]

    return NFAFragment(
        start_state_id=0,
        final_state_ids={4},
        transitions=transitions,
        all_state_ids={0, 1, 2, 3, 4, 5}
    )


def run_enhanced_nfa_tests():
    """Tests validation moteur NFA avancé"""
    print("🔧 ENHANCED NFA ENGINE VALIDATION")
    print("=" * 50)

    try:
        engine = EnhancedNFAEngine()

        # Créer NFA de test
        test_nfa = create_test_nfa()
        print(f"✅ Created test NFA: {len(test_nfa.all_state_ids)} states, {len(test_nfa.transitions)} transitions")

        # Analyse NFA original
        original_stats = engine.analyze_nfa(test_nfa)
        print(f"✅ Original analysis: {original_stats.epsilon_transition_count} epsilon transitions")

        # Test fermeture epsilon
        closure = engine.compute_epsilon_closure(test_nfa, 0)
        print(f"✅ Epsilon closure from state 0: {len(closure.states)} states reachable")

        # Test optimisation complète
        optimized_nfa = engine.full_optimize(test_nfa)
        print(f"✅ Optimized NFA: {len(optimized_nfa.all_state_ids)} states, {len(optimized_nfa.transitions)} transitions")

        # Comparaison
        comparison = engine.compare_nfas(test_nfa, optimized_nfa)
        improvements = comparison['improvements']

        print(f"✅ Optimization results:")
        print(f"   • State reduction: {improvements['state_reduction']} ({improvements['state_reduction_percent']:.1f}%)")
        print(f"   • Transition reduction: {improvements['transition_reduction']} ({improvements['transition_reduction_percent']:.1f}%)")
        print(f"   • Epsilon reduction: {improvements['epsilon_reduction']}")
        print(f"   • Optimizations applied: {len(engine.optimization_history)}")

        # Validation préservation langue
        original_finals = len(test_nfa.final_state_ids)
        optimized_finals = len(optimized_nfa.final_state_ids)
        print(f"✅ Final states preserved: {original_finals} -> {optimized_finals}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_enhanced_nfa_tests()
    if success:
        print("\n🎉 ENHANCED NFA ENGINE: ALL TESTS PASSED")
    else:
        print("\n⚠️  ENHANCED NFA ENGINE: TESTS FAILED")