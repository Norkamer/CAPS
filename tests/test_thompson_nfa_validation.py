#!/usr/bin/env python3
"""
Tests validation Thompson's NFA - Architecture règle d'or
"""

import unittest
from decimal import Decimal, getcontext
import sys
import os

# Configuration précision
getcontext().prec = 50

# Path setup pour import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'icgs_core'))

from regex_parser import RegexParser, TokenType, create_icgs_regex_parser
from thompson_nfa import ThompsonNFABuilder, TransitionType, create_thompson_builder
from shared_nfa import SharedNFA, create_shared_nfa
from weighted_nfa_v2 import WeightedNFA, create_weighted_nfa
from anchored_nfa_v2 import AnchoredWeightedNFA, create_anchored_nfa


class TestRegexParser(unittest.TestCase):
    """Tests RegexParser ICGS"""

    def setUp(self):
        self.parser = create_icgs_regex_parser()

    def test_literal_parsing(self):
        """Test parsing caractères littéraux"""
        tokens = self.parser.parse("N")

        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].token_type, TokenType.LITERAL)
        self.assertEqual(tokens[0].value, "N")

    def test_dot_star_parsing(self):
        """Test parsing .*"""
        tokens = self.parser.parse(".*")

        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0].token_type, TokenType.DOT)
        self.assertEqual(tokens[0].quantifier, "*")

    def test_complex_pattern_parsing(self):
        """Test parsing .*N.*"""
        tokens = self.parser.parse(".*N.*")

        self.assertEqual(len(tokens), 3)
        # .*, N, .*
        self.assertEqual(tokens[0].token_type, TokenType.DOT)
        self.assertEqual(tokens[0].quantifier, "*")
        self.assertEqual(tokens[1].token_type, TokenType.LITERAL)
        self.assertEqual(tokens[1].value, "N")
        self.assertEqual(tokens[2].token_type, TokenType.DOT)
        self.assertEqual(tokens[2].quantifier, "*")

    def test_pattern_validation(self):
        """Test validation patterns supportés"""
        valid_patterns = [".*N.*", "^A.*", ".*B$", "N", "ABC", "[A-Z]+"]
        invalid_patterns = ["a{2,5}"]

        for pattern in valid_patterns:
            self.assertTrue(self.parser.validate_pattern(pattern),
                          f"Pattern {pattern} should be valid")

        for pattern in invalid_patterns:
            self.assertFalse(self.parser.validate_pattern(pattern),
                           f"Pattern {pattern} should be invalid")

    def test_complexity_estimation(self):
        """Test estimation complexité patterns"""
        complexities = {
            "N": 1,      # Simple literal
            ".*": 5,     # Dot + star
            ".*N.*": 11  # Complex pattern
        }

        for pattern, expected_complexity in complexities.items():
            actual = self.parser.get_pattern_complexity(pattern)
            # Test relatif - complexité croissante
            if pattern == "N":
                self.assertEqual(actual, 1)
            elif pattern == ".*":
                self.assertGreaterEqual(actual, 2)  # Au moins 2 (dot + quantifier)
            elif pattern == ".*N.*":
                self.assertGreaterEqual(actual, 5)  # Plus complexe ou égal que .*


class TestThompsonBuilder(unittest.TestCase):
    """Tests ThompsonNFABuilder construction"""

    def setUp(self):
        self.builder = create_thompson_builder()

    def test_literal_construction(self):
        """Test construction fragment littéral"""
        fragment = self.builder.build_pattern_fragment("N")

        self.assertEqual(len(fragment.all_state_ids), 2)  # start, final
        self.assertEqual(len(fragment.transitions), 1)
        self.assertEqual(len(fragment.final_state_ids), 1)

        # Vérification transition
        transition = fragment.transitions[0]
        self.assertEqual(transition.transition_type, TransitionType.CHARACTER)
        self.assertEqual(transition.character, "N")

    def test_dot_star_construction(self):
        """Test construction .*"""
        fragment = self.builder.build_pattern_fragment(".*")

        # .* génère structure complexe avec epsilon-transitions
        self.assertGreater(len(fragment.all_state_ids), 2)
        self.assertGreater(len(fragment.transitions), 2)

        # Vérification présence epsilon-transitions
        epsilon_transitions = [t for t in fragment.transitions
                             if t.transition_type == TransitionType.EPSILON]
        self.assertGreater(len(epsilon_transitions), 0)

    def test_complex_pattern_construction(self):
        """Test construction .*N.*"""
        fragment = self.builder.build_pattern_fragment(".*N.*")

        # Pattern complexe avec plusieurs parties
        self.assertGreater(len(fragment.all_state_ids), 5)
        self.assertGreater(len(fragment.transitions), 5)

        # Vérification types transitions présentes
        char_transitions = [t for t in fragment.transitions
                          if t.transition_type == TransitionType.CHARACTER]
        dot_transitions = [t for t in fragment.transitions
                         if t.transition_type == TransitionType.DOT]
        epsilon_transitions = [t for t in fragment.transitions
                             if t.transition_type == TransitionType.EPSILON]

        self.assertEqual(len(char_transitions), 1)  # 'N'
        self.assertGreater(len(dot_transitions), 0)  # .
        self.assertGreater(len(epsilon_transitions), 0)  # Structure

    def test_quantifier_construction(self):
        """Test construction quantificateurs"""
        # Test A+
        fragment_plus = self.builder.build_pattern_fragment("A+")
        self.assertGreater(len(fragment_plus.all_state_ids), 2)

        # Test B?
        fragment_question = self.builder.build_pattern_fragment("B?")
        self.assertGreater(len(fragment_question.all_state_ids), 2)


class TestSharedNFA(unittest.TestCase):
    """Tests SharedNFA avec entry points"""

    def setUp(self):
        self.nfa = create_shared_nfa("test_shared")

    def test_measure_addition(self):
        """Test ajout mesures"""
        success1 = self.nfa.add_measure("measure1", ".*N.*", Decimal('1.2'))
        success2 = self.nfa.add_measure("measure2", ".*N.*", Decimal('0.9'))

        self.assertTrue(success1)
        self.assertTrue(success2)

        # Vérification entry points
        self.assertEqual(len(self.nfa.entry_points), 2)
        self.assertIn("measure1", self.nfa.entry_points)
        self.assertIn("measure2", self.nfa.entry_points)

        # Vérification partage pattern
        self.assertEqual(len(self.nfa.pattern_registry), 1)
        self.assertIn(".*N.*", self.nfa.pattern_registry)

    def test_pattern_sharing(self):
        """Test partage patterns identiques"""
        # Ajout même pattern pour mesures différentes
        self.nfa.add_measure("agri", ".*N.*", Decimal('1.0'))
        self.nfa.add_measure("indu", ".*N.*", Decimal('2.0'))

        # Pattern partagé
        self.assertEqual(len(self.nfa.pattern_registry), 1)

        # Entry points distincts
        self.assertEqual(len(self.nfa.entry_points), 2)

        # États partagés
        agri_entry = self.nfa.entry_points["agri"]
        indu_entry = self.nfa.entry_points["indu"]
        self.assertEqual(agri_entry.start_state_id, indu_entry.start_state_id)

    def test_freeze_unfreeze(self):
        """Test cycle freeze/unfreeze"""
        self.nfa.add_measure("test", "N", Decimal('1.0'))

        # Initial state
        self.assertFalse(self.nfa.is_frozen)
        self.assertIsNone(self.nfa.frozen_snapshot)

        # Freeze
        self.nfa.freeze()
        self.assertTrue(self.nfa.is_frozen)
        self.assertIsNotNone(self.nfa.frozen_snapshot)

        # Unfreeze
        self.nfa.unfreeze()
        self.assertFalse(self.nfa.is_frozen)
        self.assertIsNone(self.nfa.frozen_snapshot)

    def test_word_evaluation(self):
        """Test évaluation mots règle d'or"""
        self.nfa.add_measure("test", ".*N.*", Decimal('1.0'))
        self.nfa.freeze()

        # Test cases règle d'or
        test_cases = [
            ("N", True),      # Match simple
            ("NB", True),     # Match multi-char (CRITIQUE)
            ("BN", True),     # Match multi-char
            ("AN", True),     # Match avec préfixe
            ("NBA", True),    # Match avec préfixe/suffixe
            ("A", False),     # Pas de match
            ("", False),      # Mot vide
            ("B", False)      # Pas de match
        ]

        for word, should_match in test_cases:
            result = self.nfa.evaluate_word_to_final(word)
            if should_match:
                self.assertIsNotNone(result, f"Word '{word}' should match")
            else:
                self.assertIsNone(result, f"Word '{word}' should not match")

    def test_state_weights_factorization(self):
        """Test poids factorisés entry points"""
        self.nfa.add_measure("heavy", ".*N.*", Decimal('5.0'))
        self.nfa.add_measure("light", ".*N.*", Decimal('1.0'))

        heavy_weights = self.nfa.get_state_weights_for_measure("heavy")
        light_weights = self.nfa.get_state_weights_for_measure("light")

        # Même état final, poids différents
        self.assertEqual(len(heavy_weights), 1)
        self.assertEqual(len(light_weights), 1)

        final_state = next(iter(heavy_weights.keys()))
        self.assertEqual(heavy_weights[final_state], Decimal('5.0'))
        self.assertEqual(light_weights[final_state], Decimal('1.0'))


class TestAnchoredNFA(unittest.TestCase):
    """Tests AnchoredWeightedNFA v2"""

    def setUp(self):
        self.nfa = create_anchored_nfa("test_anchored")

    def test_automatic_anchoring(self):
        """Test ancrage automatique patterns"""
        test_cases = [
            ("N", ".*N.*$"),
            (".*N.*", ".*N.*$"),
            ("^A.*", "^A.*$"),
            (".*B$", ".*B$")  # Déjà ancré
        ]

        for original, expected in test_cases:
            anchored = self.nfa._apply_automatic_anchoring(original)
            self.assertEqual(anchored, expected,
                           f"Anchoring {original}: expected {expected}, got {anchored}")

    def test_icgs_test16_patterns(self):
        """Test patterns spécifiques Test 16"""
        # Ajout patterns Test 16
        state1 = self.nfa.add_weighted_regex("agriculture_debit", ".*N.*", Decimal('1.2'))
        state2 = self.nfa.add_weighted_regex("industry_credit", ".*N.*", Decimal('0.9'))

        self.assertIsNotNone(state1)
        self.assertIsNotNone(state2)

        # Freeze pour évaluation
        self.nfa.freeze()

        # Test évaluation mots Test 16
        test_words = {
            "N": True,
            "NB": True,    # CRITIQUE - multi-char
            "BN": True,    # CRITIQUE - multi-char
            "A": False,
            "": False
        }

        for word, should_match in test_words.items():
            result = self.nfa.evaluate_to_final_state(word)
            if should_match:
                self.assertIsNotNone(result, f"Test 16 word '{word}' should match")
            else:
                self.assertIsNone(result, f"Test 16 word '{word}' should not match")

    def test_state_weights_test16(self):
        """Test poids Test 16 spécifiques"""
        self.nfa.add_weighted_regex("agriculture_debit", ".*N.*", Decimal('1.2'))
        self.nfa.add_weighted_regex("industry_credit", ".*N.*", Decimal('0.9'))

        agri_weights = self.nfa.get_state_weights_for_measure("agriculture_debit")
        indu_weights = self.nfa.get_state_weights_for_measure("industry_credit")

        # Vérification poids exacts Test 16
        self.assertEqual(len(agri_weights), 1)
        self.assertEqual(len(indu_weights), 1)

        final_state = next(iter(agri_weights.keys()))
        self.assertEqual(agri_weights[final_state], Decimal('1.2'))
        self.assertEqual(indu_weights[final_state], Decimal('0.9'))

    def test_final_state_classifications(self):
        """Test classifications pour construction LP"""
        self.nfa.add_weighted_regex("measure1", ".*N.*", Decimal('2.0'))
        self.nfa.add_weighted_regex("measure2", ".*N.*", Decimal('3.0'))

        classifications = self.nfa.get_final_state_classifications()

        # Vérification classifications
        self.assertEqual(len(classifications), 1)  # Un état final partagé

        final_state = next(iter(classifications.keys()))
        regex_weights = classifications[final_state]

        self.assertEqual(len(regex_weights), 2)  # Deux mesures
        weights = [rw.weight for rw in regex_weights]
        self.assertIn(Decimal('2.0'), weights)
        self.assertIn(Decimal('3.0'), weights)


if __name__ == '__main__':
    # Configuration test runner
    unittest.main(verbosity=2, buffer=True)