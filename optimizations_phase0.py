#!/usr/bin/env python3
"""
Phase 0 Critical Optimizations
Micro-optimizations pour bottlenecks identifiés par profiling
"""

import uuid
from typing import Dict, List, Set, Optional
from dataclasses import dataclass

# Import pour optimisations
from icgs_core.regex_parser import RegexParser, RegexToken, TokenType
from icgs_core.thompson_nfa import (
    ThompsonNFABuilder, PatternFragment, NFATransition, TransitionType
)


class OptimizedThompsonNFABuilder(ThompsonNFABuilder):
    """
    Optimized version de ThompsonNFABuilder
    Focus sur réduction allocations + réutilisation objects
    """

    def __init__(self):
        super().__init__()
        # Cache pour patterns fréquents
        self._fragment_cache = {}
        self._state_id_pool = []
        # Pre-allocate common transitions
        self._epsilon_transitions_pool = []

    def _new_state_id_optimized(self) -> str:
        """Version optimisée avec pool réutilisation"""
        if self._state_id_pool:
            return self._state_id_pool.pop()

        self.state_counter += 1
        return f"q{self.state_counter}"

    def _return_state_id(self, state_id: str):
        """Retourne state_id au pool pour réutilisation"""
        if len(self._state_id_pool) < 100:  # Limite pool size
            self._state_id_pool.append(state_id)

    def _build_base_token_optimized(self, token: RegexToken) -> PatternFragment:
        """Version optimisée _build_base_token avec moins d'allocations"""

        # Cache lookup pour patterns simples communs
        cache_key = f"{token.token_type}_{token.value}_{getattr(token, 'negated', False)}"
        if cache_key in self._fragment_cache:
            cached = self._fragment_cache[cache_key]
            # Clone avec nouveaux state IDs
            start_id = self._new_state_id_optimized()
            final_id = self._new_state_id_optimized()

            # Clone transitions avec nouveaux IDs
            new_transitions = []
            for t in cached.transitions:
                new_t = NFATransition(
                    start_id, final_id, t.transition_type,
                    character=t.character, char_set=t.char_set, negated=t.negated
                )
                new_transitions.append(new_t)

            return PatternFragment(
                pattern=cached.pattern,
                start_state_id=start_id,
                final_state_ids={final_id},
                all_state_ids={start_id, final_id},
                transitions=new_transitions
            )

        # Construction normale si pas en cache
        fragment = super()._build_base_token(token)

        # Cache pour patterns simples (< 3 states)
        if len(fragment.all_state_ids) <= 2:
            self._fragment_cache[cache_key] = fragment

        return fragment

    def _concatenate_fragments_optimized(self, fragments: List[PatternFragment]) -> PatternFragment:
        """Version optimisée concatenation avec moins de copies"""

        if len(fragments) == 1:
            return fragments[0]

        # Pre-calculate sizes pour éviter reallocations
        total_states = sum(len(f.all_state_ids) for f in fragments)
        total_transitions = sum(len(f.transitions) for f in fragments)

        # Pre-allocate collections
        all_states = set()
        all_transitions = []
        all_transitions.reserve = total_transitions + len(fragments) - 1  # Estimate connections

        pattern_parts = []

        # Single pass pour collecter states et transitions
        for fragment in fragments:
            all_states.update(fragment.all_state_ids)
            all_transitions.extend(fragment.transitions)
            pattern_parts.append(fragment.pattern)

        # Optimized connections entre fragments
        for i in range(len(fragments) - 1):
            current_fragment = fragments[i]
            next_fragment = fragments[i + 1]

            # Batch create epsilon transitions
            for final_id in current_fragment.final_state_ids:
                all_transitions.append(
                    NFATransition(final_id, next_fragment.start_state_id, TransitionType.EPSILON)
                )

        return PatternFragment(
            pattern="".join(pattern_parts),
            start_state_id=fragments[0].start_state_id,
            final_state_ids=fragments[-1].final_state_ids,
            all_state_ids=all_states,
            transitions=all_transitions
        )


class OptimizedRegexParser(RegexParser):
    """
    Optimized version RegexParser
    Focus sur parsing performance character classes
    """

    def __init__(self):
        super().__init__()
        # Pre-compiled common character sets
        self._common_char_sets = {
            'A-Z': set(chr(i) for i in range(ord('A'), ord('Z') + 1)),
            'a-z': set(chr(i) for i in range(ord('a'), ord('z') + 1)),
            '0-9': set(chr(i) for i in range(ord('0'), ord('9') + 1)),
        }
        # Token objects pool
        self._token_pool = []

    def _get_token_from_pool(self, token_type: TokenType, value: str = None, **kwargs) -> RegexToken:
        """Get token from pool ou create new"""
        if self._token_pool:
            token = self._token_pool.pop()
            # Reset token
            token.token_type = token_type
            token.value = value
            for key, val in kwargs.items():
                setattr(token, key, val)
            return token
        else:
            return RegexToken(token_type, value, **kwargs)

    def _return_token(self, token: RegexToken):
        """Return token to pool"""
        if len(self._token_pool) < 50:  # Pool size limit
            self._token_pool.append(token)

    def _parse_character_class_optimized(self) -> RegexToken:
        """
        Version optimisée character class parsing
        Utilise pre-compiled sets pour ranges communs
        """
        start_pos = self.position
        self.position += 1  # Skip '['

        if self.position >= self.length:
            raise ValueError("Unterminated character class")

        # Check negation
        negated = False
        if self.position < self.length and self.pattern[self.position] == '^':
            negated = True
            self.position += 1

        char_set = set()
        class_str = "["
        if negated:
            class_str += "^"

        # Fast path pour ranges communs
        remaining_pattern = self.pattern[self.position:]

        # Check common patterns first
        if remaining_pattern.startswith('A-Z]'):
            char_set = self._common_char_sets['A-Z'].copy()
            class_str += "A-Z]"
            self.position += 4
        elif remaining_pattern.startswith('a-z]'):
            char_set = self._common_char_sets['a-z'].copy()
            class_str += "a-z]"
            self.position += 4
        elif remaining_pattern.startswith('0-9]'):
            char_set = self._common_char_sets['0-9'].copy()
            class_str += "0-9]"
            self.position += 4
        elif remaining_pattern.startswith('A-Za-z0-9]'):
            char_set = (self._common_char_sets['A-Z'] |
                       self._common_char_sets['a-z'] |
                       self._common_char_sets['0-9'])
            class_str += "A-Za-z0-9]"
            self.position += 11
        else:
            # Fallback vers parsing original
            return super()._parse_character_class()

        return self._get_token_from_pool(
            TokenType.CHARACTER_CLASS,
            value=class_str,
            position=start_pos,
            char_set=char_set,
            negated=negated
        )


def benchmark_optimizations(iterations: int = 1000):
    """Benchmark optimizations vs original"""
    import time

    print("🚀 BENCHMARKING OPTIMIZATIONS")
    print("="*50)

    # Test patterns (bottlenecks identifiés)
    test_patterns = [
        "[A-Za-z0-9]+",      # Regex parser bottleneck
        "[A-Z][a-z]*[0-9]?", # NFA construction bottleneck
        "[A-Z]",             # Simple comparison
        ".*N.*",             # Complex comparison
    ]

    # Original implementations
    original_parser = RegexParser()
    original_builder = ThompsonNFABuilder()

    # Optimized implementations
    opt_parser = OptimizedRegexParser()
    opt_builder = OptimizedThompsonNFABuilder()

    results = {}

    for pattern in test_patterns:
        print(f"\n📊 Testing pattern: {pattern}")

        # Test parser performance
        print("  Parser performance:")

        # Original parser
        start = time.perf_counter()
        for _ in range(iterations):
            try:
                tokens = original_parser.parse(pattern)
            except NotImplementedError:
                print("    Original: NotImplementedError")
                break
        else:
            original_parser_time = time.perf_counter() - start
            print(f"    Original: {original_parser_time:.6f}s ({original_parser_time/iterations*1000:.3f}ms per parse)")

        # Optimized parser
        start = time.perf_counter()
        for _ in range(iterations):
            try:
                tokens = opt_parser.parse(pattern)
            except NotImplementedError:
                print("    Optimized: NotImplementedError")
                break
        else:
            opt_parser_time = time.perf_counter() - start
            print(f"    Optimized: {opt_parser_time:.6f}s ({opt_parser_time/iterations*1000:.3f}ms per parse)")

            if 'original_parser_time' in locals():
                speedup = original_parser_time / opt_parser_time
                print(f"    Speedup: {speedup:.2f}x")

        # Test NFA construction
        print("  NFA construction performance:")

        # Original NFA builder
        start = time.perf_counter()
        for _ in range(iterations//2):  # Less iterations for NFA (more expensive)
            try:
                fragment = original_builder.build_pattern_fragment(pattern)
            except NotImplementedError:
                print("    Original NFA: NotImplementedError")
                break
        else:
            original_nfa_time = time.perf_counter() - start
            print(f"    Original: {original_nfa_time:.6f}s ({original_nfa_time/(iterations//2)*1000:.3f}ms per build)")

        # Optimized NFA builder
        start = time.perf_counter()
        for _ in range(iterations//2):
            try:
                fragment = opt_builder.build_pattern_fragment(pattern)
            except NotImplementedError:
                print("    Optimized NFA: NotImplementedError")
                break
        else:
            opt_nfa_time = time.perf_counter() - start
            print(f"    Optimized: {opt_nfa_time:.6f}s ({opt_nfa_time/(iterations//2)*1000:.3f}ms per build)")

            if 'original_nfa_time' in locals():
                speedup = original_nfa_time / opt_nfa_time
                print(f"    Speedup: {speedup:.2f}x")


if __name__ == "__main__":
    benchmark_optimizations()