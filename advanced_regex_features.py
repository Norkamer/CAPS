#!/usr/bin/env python3
"""
CAPS Phase 0 Semaines 3-4: Innovation Différenciatrice
Advanced Regex Features - Named Groups, Lookahead/Lookbehind
"""

import re
from typing import Dict, List, Set, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass
from icgs_core.regex_parser import RegexParser, RegexToken, TokenType


class AdvancedTokenType(Enum):
    """Types de tokens étendus pour fonctionnalités avancées"""
    NAMED_GROUP = "NAMED_GROUP"
    LOOKAHEAD_POSITIVE = "LOOKAHEAD_POSITIVE"
    LOOKAHEAD_NEGATIVE = "LOOKAHEAD_NEGATIVE"
    LOOKBEHIND_POSITIVE = "LOOKBEHIND_POSITIVE"
    LOOKBEHIND_NEGATIVE = "LOOKBEHIND_NEGATIVE"
    BACKREFERENCE = "BACKREFERENCE"
    NON_CAPTURING_GROUP = "NON_CAPTURING_GROUP"


@dataclass
class AdvancedRegexToken(RegexToken):
    """Token étendu avec support fonctionnalités avancées"""
    group_name: Optional[str] = None
    backreference_id: Optional[int] = None
    lookahead_pattern: Optional[str] = None
    is_atomic: bool = False


class AdvancedRegexParser(RegexParser):
    """Parser regex étendu avec fonctionnalités avancées"""

    def __init__(self):
        super().__init__()
        self.named_groups: Dict[str, int] = {}
        self.group_counter = 0
        self.advanced_features_enabled = True

    def parse_advanced(self, pattern: str) -> List[AdvancedRegexToken]:
        """Parse pattern avec support fonctionnalités avancées"""

        # Pré-traitement pour identifier fonctionnalités avancées
        advanced_tokens = []
        i = 0

        while i < len(pattern):
            if pattern[i:i+3] == '(?P':
                # Named group: (?P<name>pattern)
                token, consumed = self._parse_named_group(pattern[i:])
                advanced_tokens.append(token)
                i += consumed

            elif pattern[i:i+3] == '(?=':
                # Positive lookahead: (?=pattern)
                token, consumed = self._parse_lookahead(pattern[i:], positive=True)
                advanced_tokens.append(token)
                i += consumed

            elif pattern[i:i+3] == '(?!':
                # Negative lookahead: (?!pattern)
                token, consumed = self._parse_lookahead(pattern[i:], positive=False)
                advanced_tokens.append(token)
                i += consumed

            elif pattern[i:i+4] == '(?<=':
                # Positive lookbehind: (?<=pattern)
                token, consumed = self._parse_lookbehind(pattern[i:], positive=True)
                advanced_tokens.append(token)
                i += consumed

            elif pattern[i:i+4] == '(?<!':
                # Negative lookbehind: (?<!pattern)
                token, consumed = self._parse_lookbehind(pattern[i:], positive=False)
                advanced_tokens.append(token)
                i += consumed

            elif pattern[i] == '\\' and i+1 < len(pattern) and pattern[i+1].isdigit():
                # Backreference: \1, \2, etc.
                token, consumed = self._parse_backreference(pattern[i:])
                advanced_tokens.append(token)
                i += consumed

            elif pattern[i:i+2] == '(?:':
                # Non-capturing group: (?:pattern)
                token, consumed = self._parse_non_capturing_group(pattern[i:])
                advanced_tokens.append(token)
                i += consumed

            else:
                # Token standard - déléguer au parser de base
                try:
                    base_tokens = super().parse(pattern[i])
                    if base_tokens:
                        # Convertir en AdvancedRegexToken
                        base_token = base_tokens[0]
                        advanced_token = AdvancedRegexToken(
                            token_type=base_token.token_type,
                            value=base_token.value,
                            char_set=base_token.char_set,
                            quantifier=getattr(base_token, 'quantifier', None),
                            negated=getattr(base_token, 'negated', False)
                        )
                        advanced_tokens.append(advanced_token)
                except:
                    # Caractère littéral
                    advanced_tokens.append(AdvancedRegexToken(
                        token_type=TokenType.LITERAL,
                        value=pattern[i]
                    ))
                i += 1

        return advanced_tokens

    def _parse_named_group(self, pattern: str) -> Tuple[AdvancedRegexToken, int]:
        """Parse named group (?P<name>pattern)"""
        if not pattern.startswith('(?P<'):
            raise ValueError("Invalid named group syntax")

        # Trouver nom du groupe
        name_end = pattern.find('>', 4)
        if name_end == -1:
            raise ValueError("Named group missing closing >")

        group_name = pattern[4:name_end]

        # Valider nom du groupe
        if not group_name.isidentifier():
            raise ValueError(f"Invalid group name: {group_name}")

        # Trouver pattern du groupe
        pattern_start = name_end + 1
        paren_count = 1
        pattern_end = pattern_start

        while pattern_end < len(pattern) and paren_count > 0:
            if pattern[pattern_end] == '(':
                paren_count += 1
            elif pattern[pattern_end] == ')':
                paren_count -= 1
            pattern_end += 1

        if paren_count > 0:
            raise ValueError("Unclosed named group")

        group_pattern = pattern[pattern_start:pattern_end-1]
        self.group_counter += 1
        self.named_groups[group_name] = self.group_counter

        return AdvancedRegexToken(
            token_type=AdvancedTokenType.NAMED_GROUP,
            value=group_pattern,
            group_name=group_name
        ), pattern_end

    def _parse_lookahead(self, pattern: str, positive: bool) -> Tuple[AdvancedRegexToken, int]:
        """Parse lookahead (?=pattern) ou (?!pattern)"""
        start_marker = '(?=' if positive else '(?!'
        if not pattern.startswith(start_marker):
            raise ValueError(f"Invalid lookahead syntax: {pattern[:10]}")

        # Trouver pattern lookahead
        pattern_start = len(start_marker)
        paren_count = 1
        pattern_end = pattern_start

        while pattern_end < len(pattern) and paren_count > 0:
            if pattern[pattern_end] == '(':
                paren_count += 1
            elif pattern[pattern_end] == ')':
                paren_count -= 1
            pattern_end += 1

        if paren_count > 0:
            raise ValueError("Unclosed lookahead")

        lookahead_pattern = pattern[pattern_start:pattern_end-1]
        token_type = AdvancedTokenType.LOOKAHEAD_POSITIVE if positive else AdvancedTokenType.LOOKAHEAD_NEGATIVE

        return AdvancedRegexToken(
            token_type=token_type,
            value=lookahead_pattern,
            lookahead_pattern=lookahead_pattern
        ), pattern_end

    def _parse_lookbehind(self, pattern: str, positive: bool) -> Tuple[AdvancedRegexToken, int]:
        """Parse lookbehind (?<=pattern) ou (?<!pattern)"""
        start_marker = '(?<=' if positive else '(?<!'
        if not pattern.startswith(start_marker):
            raise ValueError(f"Invalid lookbehind syntax: {pattern[:10]}")

        # Trouver pattern lookbehind
        pattern_start = len(start_marker)
        paren_count = 1
        pattern_end = pattern_start

        while pattern_end < len(pattern) and paren_count > 0:
            if pattern[pattern_end] == '(':
                paren_count += 1
            elif pattern[pattern_end] == ')':
                paren_count -= 1
            pattern_end += 1

        if paren_count > 0:
            raise ValueError("Unclosed lookbehind")

        lookbehind_pattern = pattern[pattern_start:pattern_end-1]
        token_type = AdvancedTokenType.LOOKBEHIND_POSITIVE if positive else AdvancedTokenType.LOOKBEHIND_NEGATIVE

        return AdvancedRegexToken(
            token_type=token_type,
            value=lookbehind_pattern,
            lookahead_pattern=lookbehind_pattern  # Réutilise même champ
        ), pattern_end

    def _parse_backreference(self, pattern: str) -> Tuple[AdvancedRegexToken, int]:
        """Parse backreference \\1, \\2, etc."""
        if not pattern.startswith('\\') or len(pattern) < 2:
            raise ValueError("Invalid backreference syntax")

        ref_id_str = ""
        i = 1
        while i < len(pattern) and pattern[i].isdigit():
            ref_id_str += pattern[i]
            i += 1

        if not ref_id_str:
            raise ValueError("Empty backreference")

        ref_id = int(ref_id_str)
        if ref_id <= 0 or ref_id > self.group_counter:
            raise ValueError(f"Invalid backreference: \\{ref_id}")

        return AdvancedRegexToken(
            token_type=AdvancedTokenType.BACKREFERENCE,
            value=f"\\{ref_id}",
            backreference_id=ref_id
        ), i

    def _parse_non_capturing_group(self, pattern: str) -> Tuple[AdvancedRegexToken, int]:
        """Parse non-capturing group (?:pattern)"""
        if not pattern.startswith('(?:'):
            raise ValueError("Invalid non-capturing group syntax")

        # Trouver pattern du groupe
        pattern_start = 3
        paren_count = 1
        pattern_end = pattern_start

        while pattern_end < len(pattern) and paren_count > 0:
            if pattern[pattern_end] == '(':
                paren_count += 1
            elif pattern[pattern_end] == ')':
                paren_count -= 1
            pattern_end += 1

        if paren_count > 0:
            raise ValueError("Unclosed non-capturing group")

        group_pattern = pattern[pattern_start:pattern_end-1]

        return AdvancedRegexToken(
            token_type=AdvancedTokenType.NON_CAPTURING_GROUP,
            value=group_pattern
        ), pattern_end

    def validate_advanced_pattern(self, pattern: str) -> Dict[str, Any]:
        """Valide pattern et retourne analyse des fonctionnalités"""
        try:
            tokens = self.parse_advanced(pattern)

            features = {
                'named_groups': [],
                'lookaheads': [],
                'lookbehinds': [],
                'backreferences': [],
                'non_capturing_groups': [],
                'complexity_score': 0
            }

            for token in tokens:
                if token.token_type == AdvancedTokenType.NAMED_GROUP:
                    features['named_groups'].append(token.group_name)
                    features['complexity_score'] += 2

                elif token.token_type in [AdvancedTokenType.LOOKAHEAD_POSITIVE, AdvancedTokenType.LOOKAHEAD_NEGATIVE]:
                    features['lookaheads'].append({
                        'type': 'positive' if token.token_type == AdvancedTokenType.LOOKAHEAD_POSITIVE else 'negative',
                        'pattern': token.lookahead_pattern
                    })
                    features['complexity_score'] += 3

                elif token.token_type in [AdvancedTokenType.LOOKBEHIND_POSITIVE, AdvancedTokenType.LOOKBEHIND_NEGATIVE]:
                    features['lookbehinds'].append({
                        'type': 'positive' if token.token_type == AdvancedTokenType.LOOKBEHIND_POSITIVE else 'negative',
                        'pattern': token.lookahead_pattern
                    })
                    features['complexity_score'] += 4

                elif token.token_type == AdvancedTokenType.BACKREFERENCE:
                    features['backreferences'].append(token.backreference_id)
                    features['complexity_score'] += 2

                elif token.token_type == AdvancedTokenType.NON_CAPTURING_GROUP:
                    features['non_capturing_groups'].append(token.value)
                    features['complexity_score'] += 1

            return {
                'valid': True,
                'features': features,
                'token_count': len(tokens),
                'named_groups_map': self.named_groups.copy()
            }

        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'features': None
            }


class AdvancedRegexMatcher:
    """Matcher pour patterns regex avancés avec support des fonctionnalités"""

    def __init__(self, parser: AdvancedRegexParser):
        self.parser = parser
        self.compiled_patterns: Dict[str, re.Pattern] = {}

    def compile_advanced_pattern(self, pattern: str) -> re.Pattern:
        """Compile pattern avancé en regex Python standard"""
        if pattern in self.compiled_patterns:
            return self.compiled_patterns[pattern]

        try:
            # Validation du pattern
            validation = self.parser.validate_advanced_pattern(pattern)
            if not validation['valid']:
                raise ValueError(f"Invalid pattern: {validation['error']}")

            # Compilation avec support groupes nommés
            compiled = re.compile(pattern)
            self.compiled_patterns[pattern] = compiled
            return compiled

        except Exception as e:
            raise ValueError(f"Failed to compile pattern '{pattern}': {e}")

    def match_with_groups(self, pattern: str, text: str) -> Dict[str, Any]:
        """Match avec extraction des groupes nommés et numérotés"""
        compiled = self.compile_advanced_pattern(pattern)
        match = compiled.search(text)

        if not match:
            return {'matched': False, 'groups': {}, 'named_groups': {}}

        result = {
            'matched': True,
            'start': match.start(),
            'end': match.end(),
            'full_match': match.group(0),
            'groups': {},
            'named_groups': {}
        }

        # Groupes numérotés
        for i in range(1, len(match.groups()) + 1):
            try:
                result['groups'][i] = match.group(i)
            except IndexError:
                result['groups'][i] = None

        # Groupes nommés
        result['named_groups'] = match.groupdict()

        return result

    def test_lookaround(self, pattern: str, text: str, position: int = 0) -> Dict[str, Any]:
        """Test spécialisé pour lookahead/lookbehind à une position"""
        try:
            compiled = self.compile_advanced_pattern(pattern)

            # Test match à position spécifique
            match = compiled.match(text, position)

            return {
                'matches': match is not None,
                'position': position,
                'text_length': len(text),
                'pattern_analyzed': True
            }

        except Exception as e:
            return {
                'matches': False,
                'error': str(e),
                'pattern_analyzed': False
            }


def run_advanced_regex_tests():
    """Tests validation fonctionnalités avancées"""
    print("🚀 ADVANCED REGEX FEATURES VALIDATION")
    print("=" * 50)

    parser = AdvancedRegexParser()
    matcher = AdvancedRegexMatcher(parser)

    test_cases = [
        # Named groups
        {
            'pattern': r'(?P<word>[A-Za-z]+)_(?P<number>\d+)',
            'text': 'test_123',
            'description': 'Named groups extraction'
        },

        # Positive lookahead
        {
            'pattern': r'hello(?=\sworld)',
            'text': 'hello world',
            'description': 'Positive lookahead'
        },

        # Negative lookahead
        {
            'pattern': r'hello(?!\sworld)',
            'text': 'hello there',
            'description': 'Negative lookahead'
        },

        # Positive lookbehind
        {
            'pattern': r'(?<=hello\s)world',
            'text': 'hello world',
            'description': 'Positive lookbehind'
        },

        # Non-capturing group
        {
            'pattern': r'(?:abc|def)_(\d+)',
            'text': 'abc_456',
            'description': 'Non-capturing group'
        }
    ]

    passed_tests = 0
    total_tests = len(test_cases)

    for i, test_case in enumerate(test_cases):
        try:
            print(f"\nTest {i+1}: {test_case['description']}")
            print(f"Pattern: {test_case['pattern']}")
            print(f"Text: {test_case['text']}")

            # Validation du pattern
            validation = parser.validate_advanced_pattern(test_case['pattern'])
            print(f"Pattern valid: {validation['valid']}")

            if validation['valid']:
                # Test matching
                result = matcher.match_with_groups(test_case['pattern'], test_case['text'])
                print(f"Match result: {result['matched']}")

                if result['matched']:
                    if result['named_groups']:
                        print(f"Named groups: {result['named_groups']}")
                    if result['groups']:
                        print(f"Numbered groups: {result['groups']}")

                passed_tests += 1
                print("✅ PASSED")
            else:
                print(f"❌ FAILED - {validation.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"❌ FAILED - Exception: {e}")

    print(f"\n📊 TEST SUMMARY: {passed_tests}/{total_tests} passed")
    print(f"Success rate: {passed_tests/total_tests*100:.1f}%")

    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_advanced_regex_tests()
    if success:
        print("\n🎉 ADVANCED REGEX FEATURES: ALL TESTS PASSED")
    else:
        print("\n⚠️  ADVANCED REGEX FEATURES: SOME TESTS FAILED")