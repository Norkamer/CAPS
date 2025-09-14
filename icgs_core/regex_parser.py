#!/usr/bin/env python3
"""
RegexParser pour patterns ICGS - Thompson's Construction
"""

import re
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple
from decimal import Decimal


class TokenType(Enum):
    """Types de tokens regex pour construction Thompson's"""
    LITERAL = "LITERAL"          # Caractère littéral 'a', 'b', 'N'
    DOT = "DOT"                 # . (tout caractère)
    STAR = "STAR"               # * (zéro ou plus)
    PLUS = "PLUS"               # + (un ou plus)
    QUESTION = "QUESTION"       # ? (zéro ou un)
    ANCHOR_START = "ANCHOR_START"  # ^ (début)
    ANCHOR_END = "ANCHOR_END"   # $ (fin)
    GROUP_START = "GROUP_START" # (
    GROUP_END = "GROUP_END"     # )
    CHARACTER_CLASS = "CHARACTER_CLASS" # [abc] ou [a-z]


@dataclass
class RegexToken:
    """Token regex avec métadonnées pour Thompson's"""
    token_type: TokenType
    value: Optional[str] = None  # Caractère pour LITERAL ou classe pour CHARACTER_CLASS
    quantifier: Optional[str] = None  # *, +, ?
    position: int = 0  # Position dans pattern original
    char_set: Optional[Set[str]] = None  # Caractères pour CHARACTER_CLASS
    negated: bool = False  # Pour [^abc]

    def __str__(self) -> str:
        if self.value:
            return f"{self.token_type.value}({self.value})"
        return self.token_type.value


class RegexParser:
    """
    Parser regex vers tokens Thompson's pour ICGS

    Supporte patterns économiques typiques:
    - ".*N.*" (tout contenant N)
    - "^A.*" (commençant par A)
    - ".*B$" (finissant par B)
    - "[A-Z]+" (majuscules)
    """

    def __init__(self):
        self.position = 0
        self.pattern = ""
        self.length = 0

    def parse(self, pattern: str) -> List[RegexToken]:
        """
        Parse pattern regex en tokens Thompson's

        Args:
            pattern: Pattern regex (ex: ".*N.*")

        Returns:
            Liste tokens pour construction NFA
        """
        self.pattern = pattern
        self.length = len(pattern)
        self.position = 0

        tokens = []

        while self.position < self.length:
            char = self.pattern[self.position]

            if char == '.':
                tokens.append(RegexToken(TokenType.DOT, position=self.position))
            elif char == '*':
                # Quantificateur - modifier le token précédent
                if tokens and tokens[-1].quantifier is None:
                    tokens[-1].quantifier = '*'
                else:
                    raise ValueError(f"Invalid * at position {self.position}")
            elif char == '+':
                if tokens and tokens[-1].quantifier is None:
                    tokens[-1].quantifier = '+'
                else:
                    raise ValueError(f"Invalid + at position {self.position}")
            elif char == '?':
                if tokens and tokens[-1].quantifier is None:
                    tokens[-1].quantifier = '?'
                else:
                    raise ValueError(f"Invalid ? at position {self.position}")
            elif char == '^':
                tokens.append(RegexToken(TokenType.ANCHOR_START, position=self.position))
            elif char == '$':
                tokens.append(RegexToken(TokenType.ANCHOR_END, position=self.position))
            elif char == '(':
                tokens.append(RegexToken(TokenType.GROUP_START, position=self.position))
            elif char == ')':
                tokens.append(RegexToken(TokenType.GROUP_END, position=self.position))
            elif char == '\\':
                # Échappement - caractère littéral suivant
                self.position += 1
                if self.position < self.length:
                    escaped_char = self.pattern[self.position]
                    tokens.append(RegexToken(TokenType.LITERAL, escaped_char, position=self.position-1))
                else:
                    raise ValueError("Invalid escape at end of pattern")
            elif char == '[':
                # Classes de caractères [abc] ou [a-z]
                token = self._parse_character_class()
                tokens.append(token)
            elif char == '{':
                # Quantificateurs {2,5} - pas supportés pour l'instant
                raise NotImplementedError(f"Quantifiers not implemented: {char}")
            else:
                # Caractère littéral
                tokens.append(RegexToken(TokenType.LITERAL, char, position=self.position))

            self.position += 1

        return tokens

    def validate_pattern(self, pattern: str) -> bool:
        """
        Validation pattern supporté par ICGS

        Returns:
            True si pattern supporté, False sinon
        """
        try:
            # Test compilation regex Python standard
            re.compile(pattern)

            # Test parsing tokens
            tokens = self.parse(pattern)

            # Validation combinaisons supportées
            return self._validate_token_sequence(tokens)

        except Exception:
            return False

    def _validate_token_sequence(self, tokens: List[RegexToken]) -> bool:
        """Validation séquence tokens supportée"""

        # Patterns trop complexes pas supportés
        group_depth = 0
        for token in tokens:
            if token.token_type == TokenType.GROUP_START:
                group_depth += 1
            elif token.token_type == TokenType.GROUP_END:
                group_depth -= 1

            # Pas de groupes imbriqués pour l'instant
            if group_depth > 1:
                return False

        # Groupes balancés
        if group_depth != 0:
            return False

        return True

    def get_pattern_complexity(self, pattern: str) -> int:
        """
        Estime complexité pattern pour optimisations

        Returns:
            Score complexité (plus haut = plus complexe)
        """
        try:
            tokens = self.parse(pattern)
            complexity = 0

            for token in tokens:
                if token.token_type == TokenType.DOT:
                    complexity += 2  # . coûteux (tout caractère)
                elif token.quantifier == '*':
                    complexity += 3  # * coûteux (répétition)
                elif token.quantifier == '+':
                    complexity += 2  # + moins coûteux
                elif token.token_type == TokenType.LITERAL:
                    complexity += 1  # Littéral simple

            return complexity

        except Exception:
            return float('inf')  # Pattern invalide = complexité infinie

    def extract_literals(self, pattern: str) -> Set[str]:
        """
        Extrait caractères littéraux d'un pattern

        Utile pour optimisations et cache.

        Returns:
            Set caractères littéraux dans pattern
        """
        try:
            tokens = self.parse(pattern)
            literals = set()

            for token in tokens:
                if token.token_type == TokenType.LITERAL:
                    literals.add(token.value)

            return literals

        except Exception:
            return set()

    def _parse_character_class(self) -> RegexToken:
        """
        Parse classe de caractères [abc] ou [a-z] ou [^abc]

        Returns:
            Token CHARACTER_CLASS avec char_set
        """
        start_pos = self.position
        self.position += 1  # Skip '['

        if self.position >= self.length:
            raise ValueError("Unterminated character class")

        # Check for negation [^...]
        negated = False
        if self.position < self.length and self.pattern[self.position] == '^':
            negated = True
            self.position += 1

        char_set = set()
        class_str = "["

        if negated:
            class_str += "^"

        # Parse characters until ]
        while self.position < self.length and self.pattern[self.position] != ']':
            char = self.pattern[self.position]

            # Handle ranges like a-z
            if (self.position + 2 < self.length and
                self.pattern[self.position + 1] == '-' and
                self.pattern[self.position + 2] != ']'):

                start_char = char
                end_char = self.pattern[self.position + 2]

                # Add range to set
                for code in range(ord(start_char), ord(end_char) + 1):
                    char_set.add(chr(code))

                class_str += f"{start_char}-{end_char}"
                self.position += 3
            else:
                # Single character
                char_set.add(char)
                class_str += char
                self.position += 1

        if self.position >= self.length or self.pattern[self.position] != ']':
            raise ValueError("Unterminated character class")

        class_str += "]"

        return RegexToken(
            TokenType.CHARACTER_CLASS,
            value=class_str,
            position=start_pos,
            char_set=char_set,
            negated=negated
        )

    def simplify_anchored_pattern(self, pattern: str) -> str:
        """
        Simplifie patterns ancrés automatiquement

        ".*N.*$" → ".*N.*" ($ redondant après transformation ICGS)

        Returns:
            Pattern simplifié
        """
        # Suppression ancres redondantes après auto-anchoring ICGS
        simplified = pattern

        # Pattern déjà ancré avec .* au début et $ à la fin
        if simplified.startswith(".*") and simplified.endswith("$"):
            # Remove redundant $ anchor
            simplified = simplified[:-1]

        return simplified


def create_icgs_regex_parser() -> RegexParser:
    """Factory pour parser ICGS standard"""
    return RegexParser()


if __name__ == "__main__":
    # Tests parser
    parser = create_icgs_regex_parser()

    test_patterns = [
        ".*N.*",
        "^A.*",
        ".*B$",
        "N",
        "ABC",
        "A.*B",
        "[A-Z]+",  # Pas supporté
        "a{2,5}",  # Pas supporté
    ]

    for pattern in test_patterns:
        print(f"\n=== Pattern: {pattern} ===")

        if parser.validate_pattern(pattern):
            try:
                tokens = parser.parse(pattern)
                print(f"✅ Tokens: {[str(t) for t in tokens]}")
                print(f"Complexity: {parser.get_pattern_complexity(pattern)}")
                print(f"Literals: {parser.extract_literals(pattern)}")
            except NotImplementedError as e:
                print(f"⚠️  Not implemented: {e}")
        else:
            print("❌ Pattern not supported")