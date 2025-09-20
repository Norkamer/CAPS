#!/usr/bin/env python3
"""
Thompson's NFA Construction Algorithm pour ICGS
Implémentation rigoureuse règle d'or: 1 caractère = 1 transition
"""

import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from decimal import Decimal
import copy

try:
    from .regex_parser import RegexParser, RegexToken, TokenType
except ImportError:
    from regex_parser import RegexParser, RegexToken, TokenType


class TransitionType(Enum):
    """Types transitions NFA Thompson's"""
    EPSILON = "EPSILON"         # ε-transition (pas de consommation)
    CHARACTER = "CHARACTER"     # Transition caractère spécifique
    DOT = "DOT"                # . (tout caractère)
    CHARACTER_CLASS = "CHARACTER_CLASS"  # Classe caractères [abc]


@dataclass
class NFATransition:
    """Transition NFA avec respect règle d'or"""
    from_state: str
    to_state: str
    transition_type: TransitionType
    character: Optional[str] = None  # Caractère pour CHARACTER
    char_set: Optional[Set[str]] = None  # Caractères pour CHARACTER_CLASS
    negated: bool = False  # Pour classes négatives [^abc]
    transition_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def matches_character(self, char: str) -> bool:
        """Test si transition accepte caractère donné"""
        if self.transition_type == TransitionType.EPSILON:
            return False  # ε ne consomme rien
        elif self.transition_type == TransitionType.CHARACTER:
            return char == self.character
        elif self.transition_type == TransitionType.DOT:
            return len(char) == 1  # . accepte tout caractère unique
        elif self.transition_type == TransitionType.CHARACTER_CLASS:
            if self.char_set is None:
                return False
            if self.negated:
                return char not in self.char_set
            else:
                return char in self.char_set
        return False

    def __str__(self) -> str:
        if self.transition_type == TransitionType.EPSILON:
            return f"{self.from_state} --ε--> {self.to_state}"
        elif self.transition_type == TransitionType.CHARACTER:
            return f"{self.from_state} --'{self.character}'--> {self.to_state}"
        elif self.transition_type == TransitionType.DOT:
            return f"{self.from_state} --.--> {self.to_state}"
        elif self.transition_type == TransitionType.CHARACTER_CLASS:
            class_desc = "^" if self.negated else ""
            if self.char_set:
                class_desc += "".join(sorted(self.char_set))
            return f"{self.from_state} --[{class_desc}]--> {self.to_state}"


@dataclass
class NFAState:
    """État NFA Thompson's"""
    state_id: str
    is_final: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        final_marker = "(FINAL)" if self.is_final else ""
        return f"State[{self.state_id}]{final_marker}"


@dataclass
class EntryPoint:
    """Point d'entrée NFA avec poids factorisé"""
    measure_id: str
    weight: Decimal
    start_state_id: str
    pattern_hash: str
    pattern: str

    def __str__(self) -> str:
        return f"EntryPoint[{self.measure_id}: {self.weight} @ {self.start_state_id}]"


@dataclass
class PatternFragment:
    """Fragment NFA pour un pattern"""
    pattern: str
    start_state_id: str
    final_state_ids: Set[str]
    all_state_ids: Set[str]
    transitions: List[NFATransition]

    def __str__(self) -> str:
        return f"Fragment[{self.pattern}: {self.start_state_id} → {self.final_state_ids}]"


class ThompsonNFABuilder:
    """
    Constructeur NFA Thompson's avec règle d'or

    Algorithme classique:
    - 1 caractère = 1 transition
    - ε-transitions pour structure
    - Construction incrémentale
    """

    def __init__(self):
        self.state_counter = 0
        self.regex_parser = RegexParser()

    def _new_state_id(self) -> str:
        """Génère ID état unique"""
        self.state_counter += 1
        return f"q{self.state_counter}"

    def build_fragment_from_tokens(self, tokens: List[RegexToken]) -> PatternFragment:
        """
        Construction fragment NFA depuis tokens regex

        Args:
            tokens: Tokens regex du parser

        Returns:
            Fragment NFA avec états et transitions
        """
        if not tokens:
            # Fragment vide - accept epsilon
            start_id = self._new_state_id()
            final_id = self._new_state_id()

            return PatternFragment(
                pattern="",
                start_state_id=start_id,
                final_state_ids={final_id},
                all_state_ids={start_id, final_id},
                transitions=[NFATransition(start_id, final_id, TransitionType.EPSILON)]
            )

        # Construction séquentielle
        return self._build_sequence(tokens)

    def _build_sequence(self, tokens: List[RegexToken]) -> PatternFragment:
        """Construction séquence tokens avec concaténation"""

        if len(tokens) == 1:
            return self._build_single_token(tokens[0])

        # Construction par concaténation
        fragments = []
        i = 0

        while i < len(tokens):
            token = tokens[i]

            # Construction token avec quantificateur potentiel
            fragment = self._build_single_token(token)
            fragments.append(fragment)
            i += 1

        # Concaténation de tous fragments
        return self._concatenate_fragments(fragments)

    def _build_single_token(self, token: RegexToken) -> PatternFragment:
        """Construction fragment pour token unique"""

        base_fragment = self._build_base_token(token)

        # Application quantificateurs
        if token.quantifier == '*':
            return self._apply_star(base_fragment)
        elif token.quantifier == '+':
            return self._apply_plus(base_fragment)
        elif token.quantifier == '?':
            return self._apply_question(base_fragment)

        return base_fragment

    def _build_base_token(self, token: RegexToken) -> PatternFragment:
        """Construction fragment base sans quantificateurs"""

        start_id = self._new_state_id()
        final_id = self._new_state_id()

        if token.token_type == TokenType.LITERAL:
            # Caractère littéral: q1 --'a'--> q2
            transition = NFATransition(
                start_id, final_id,
                TransitionType.CHARACTER,
                token.value
            )

            return PatternFragment(
                pattern=token.value,
                start_state_id=start_id,
                final_state_ids={final_id},
                all_state_ids={start_id, final_id},
                transitions=[transition]
            )

        elif token.token_type == TokenType.DOT:
            # . (tout caractère): q1 --.--> q2
            transition = NFATransition(
                start_id, final_id,
                TransitionType.DOT
            )

            return PatternFragment(
                pattern=".",
                start_state_id=start_id,
                final_state_ids={final_id},
                all_state_ids={start_id, final_id},
                transitions=[transition]
            )

        elif token.token_type == TokenType.ANCHOR_START:
            # ^ - pas de consommation, juste validation position
            return PatternFragment(
                pattern="^",
                start_state_id=start_id,
                final_state_ids={final_id},
                all_state_ids={start_id, final_id},
                transitions=[NFATransition(start_id, final_id, TransitionType.EPSILON)]
            )

        elif token.token_type == TokenType.ANCHOR_END:
            # $ - pas de consommation, validation fin
            return PatternFragment(
                pattern="$",
                start_state_id=start_id,
                final_state_ids={final_id},
                all_state_ids={start_id, final_id},
                transitions=[NFATransition(start_id, final_id, TransitionType.EPSILON)]
            )

        elif token.token_type == TokenType.CHARACTER_CLASS:
            # [abc] ou [a-z] - classe de caractères
            transition = NFATransition(
                start_id, final_id,
                TransitionType.CHARACTER_CLASS,
                char_set=token.char_set,
                negated=token.negated
            )

            return PatternFragment(
                pattern=token.value or "[...]",
                start_state_id=start_id,
                final_state_ids={final_id},
                all_state_ids={start_id, final_id},
                transitions=[transition]
            )

        elif token.token_type == TokenType.GROUP_START:
            # ( - début de groupe, pas de consommation
            return PatternFragment(
                pattern="(",
                start_state_id=start_id,
                final_state_ids={final_id},
                all_state_ids={start_id, final_id},
                transitions=[NFATransition(start_id, final_id, TransitionType.EPSILON)]
            )

        elif token.token_type == TokenType.GROUP_END:
            # ) - fin de groupe, pas de consommation
            return PatternFragment(
                pattern=")",
                start_state_id=start_id,
                final_state_ids={final_id},
                all_state_ids={start_id, final_id},
                transitions=[NFATransition(start_id, final_id, TransitionType.EPSILON)]
            )

        else:
            # Tous les TokenType définis sont implémentés. Ceci ne devrait jamais arriver.
            raise ValueError(f"Unknown token type {token.token_type}. All defined TokenType values are implemented.")

    def _apply_star(self, fragment: PatternFragment) -> PatternFragment:
        """Application quantificateur * (zéro ou plus)"""

        new_start = self._new_state_id()
        new_final = self._new_state_id()

        transitions = list(fragment.transitions)
        all_states = set(fragment.all_state_ids)
        all_states.update({new_start, new_final})

        # ε-transitions pour structure *
        transitions.extend([
            # new_start -> fragment_start (une ou plus fois)
            NFATransition(new_start, fragment.start_state_id, TransitionType.EPSILON),
            # new_start -> new_final (zéro fois)
            NFATransition(new_start, new_final, TransitionType.EPSILON),
            # fragment_finals -> new_final (fin)
            *[NFATransition(final_id, new_final, TransitionType.EPSILON)
              for final_id in fragment.final_state_ids],
            # fragment_finals -> fragment_start (répétition)
            *[NFATransition(final_id, fragment.start_state_id, TransitionType.EPSILON)
              for final_id in fragment.final_state_ids]
        ])

        return PatternFragment(
            pattern=f"({fragment.pattern})*",
            start_state_id=new_start,
            final_state_ids={new_final},
            all_state_ids=all_states,
            transitions=transitions
        )

    def _apply_plus(self, fragment: PatternFragment) -> PatternFragment:
        """Application quantificateur + (un ou plus)"""

        new_final = self._new_state_id()

        transitions = list(fragment.transitions)
        all_states = set(fragment.all_state_ids)
        all_states.add(new_final)

        # ε-transitions pour structure +
        transitions.extend([
            # fragment_finals -> new_final (fin)
            *[NFATransition(final_id, new_final, TransitionType.EPSILON)
              for final_id in fragment.final_state_ids],
            # fragment_finals -> fragment_start (répétition)
            *[NFATransition(final_id, fragment.start_state_id, TransitionType.EPSILON)
              for final_id in fragment.final_state_ids]
        ])

        return PatternFragment(
            pattern=f"({fragment.pattern})+",
            start_state_id=fragment.start_state_id,  # Commence par fragment original
            final_state_ids={new_final},
            all_state_ids=all_states,
            transitions=transitions
        )

    def _apply_question(self, fragment: PatternFragment) -> PatternFragment:
        """Application quantificateur ? (zéro ou un)"""

        new_start = self._new_state_id()
        new_final = self._new_state_id()

        transitions = list(fragment.transitions)
        all_states = set(fragment.all_state_ids)
        all_states.update({new_start, new_final})

        # ε-transitions pour structure ?
        transitions.extend([
            # new_start -> fragment_start (une fois)
            NFATransition(new_start, fragment.start_state_id, TransitionType.EPSILON),
            # new_start -> new_final (zéro fois)
            NFATransition(new_start, new_final, TransitionType.EPSILON),
            # fragment_finals -> new_final (fin)
            *[NFATransition(final_id, new_final, TransitionType.EPSILON)
              for final_id in fragment.final_state_ids]
        ])

        return PatternFragment(
            pattern=f"({fragment.pattern})?",
            start_state_id=new_start,
            final_state_ids={new_final},
            all_state_ids=all_states,
            transitions=transitions
        )

    def _concatenate_fragments(self, fragments: List[PatternFragment]) -> PatternFragment:
        """Concaténation fragments par ε-transitions"""

        if len(fragments) == 1:
            return fragments[0]

        all_states = set()
        all_transitions = []
        pattern_parts = []

        # États et transitions de tous fragments
        for fragment in fragments:
            all_states.update(fragment.all_state_ids)
            all_transitions.extend(fragment.transitions)
            pattern_parts.append(fragment.pattern)

        # Connections entre fragments consécutifs
        for i in range(len(fragments) - 1):
            current_fragment = fragments[i]
            next_fragment = fragments[i + 1]

            # final_states(current) -> start_state(next)
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

    def build_pattern_fragment(self, pattern: str) -> PatternFragment:
        """Interface principale: pattern → fragment NFA"""

        tokens = self.regex_parser.parse(pattern)
        return self.build_fragment_from_tokens(tokens)


def create_thompson_builder() -> ThompsonNFABuilder:
    """Factory builder Thompson's standard"""
    return ThompsonNFABuilder()


if __name__ == "__main__":
    # Tests construction Thompson's
    builder = create_thompson_builder()

    test_patterns = [
        "N",           # Simple literal
        ".*",          # Dot star
        ".*N.*",       # Complex pattern Test 16
        "A+",          # Plus quantifier
        "B?",          # Question quantifier
    ]

    for pattern in test_patterns:
        print(f"\n=== Pattern: {pattern} ===")
        try:
            fragment = builder.build_pattern_fragment(pattern)
            print(f"States: {len(fragment.all_state_ids)}")
            print(f"Transitions: {len(fragment.transitions)}")
            print(f"Start: {fragment.start_state_id}")
            print(f"Finals: {fragment.final_state_ids}")

            for transition in fragment.transitions:
                print(f"  {transition}")

        except Exception as e:
            print(f"❌ Error: {e}")