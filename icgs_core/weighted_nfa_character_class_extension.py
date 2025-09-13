"""
Extension WeightedNFA pour Support Character-Class Unifié

Cette extension ajoute le support character-class à evaluate_word() de manière
transparente, préservant la compatibilité API complète avec le pipeline existant.

Architecture:
- Extension de WeightedNFA.evaluate_word() existant
- Support hybride: patterns standards + character-class consolidés
- API identique: signature Set[str] préservée
- Performance optimisée: cache et indexation
"""

from typing import Dict, List, Set, Optional, Any
from decimal import Decimal
import re
import time
from dataclasses import dataclass

from .weighted_nfa import WeightedNFA, NFAState


class CharacterClassEvaluationMixin:
    """
    Mixin pour étendre WeightedNFA avec support character-class unifié

    Architecture:
    1. Extension evaluate_word() hybride (standard + character-class)
    2. Cache optimisé pour performance
    3. Indexation états character-class pré-compilée
    4. Métadonnées enrichies pour debugging
    """

    def __init__(self):
        super().__init__()

        # Cache évaluation character-class
        self._character_class_cache: Dict[str, Set[str]] = {}
        self._character_class_states: List[NFAState] = []
        self._cache_hits: int = 0
        self._cache_misses: int = 0

        # Index pre-build pour performance
        self._character_class_index_built: bool = False

    def evaluate_word_unified(self, word: str) -> Set[str]:
        """
        NOUVELLE API UNIFIÉE: Évaluation hybride standard + character-class

        Extension transparente de evaluate_word() avec support character-class.
        Préserve compatibilité totale API existante.

        Algorithm:
        1. Évaluation standard WeightedNFA (existante)
        2. Évaluation character-class patterns (nouvelle)
        3. Union résultats pour ensemble complet
        4. Cache intelligent pour performance

        Args:
            word: Mot à évaluer

        Returns:
            Set[str]: États finaux atteints (standard + character-class)
        """
        # 1. Évaluation standard (méthode parent)
        standard_finals = super().evaluate_word(word)

        # 2. Évaluation character-class avec cache
        character_class_finals = self._evaluate_word_character_class_cached(word)

        # 3. Union résultats
        unified_finals = standard_finals.union(character_class_finals)

        return unified_finals

    def _evaluate_word_character_class_cached(self, word: str) -> Set[str]:
        """
        Évaluation character-class avec cache intelligent

        Performance:
        - Cache LRU automatique
        - Limite 1000 entrées max
        - Invalidation sur freeze/unfreeze

        Args:
            word: Mot à évaluer

        Returns:
            Set[str]: États finaux character-class matchés
        """
        # Cache lookup
        if word in self._character_class_cache:
            self._cache_hits += 1
            return self._character_class_cache[word]

        # Cache miss - évaluation complète
        self._cache_misses += 1
        result = self._evaluate_word_character_class(word)

        # Cache storage avec limite
        if len(self._character_class_cache) >= 1000:
            # LRU: remove oldest entry
            oldest_key = next(iter(self._character_class_cache))
            del self._character_class_cache[oldest_key]

        self._character_class_cache[word] = result
        return result

    def _evaluate_word_character_class(self, word: str) -> Set[str]:
        """
        Évaluation core character-class patterns

        Algorithm:
        1. Build index si pas encore fait
        2. Iterate États avec compiled_patterns
        3. Test chaque pattern compilé
        4. Collect états finaux matchés

        Args:
            word: Mot à évaluer

        Returns:
            Set[str]: États finaux avec patterns character-class matchés
        """
        # Build index lazy si nécessaire
        if not self._character_class_index_built:
            self._build_character_class_index()

        matched_finals = set()

        # Test contre chaque état character-class indexé
        for state in self._character_class_states:
            if hasattr(state, 'compiled_patterns'):
                for pattern_info in state.compiled_patterns:
                    compiled_pattern = pattern_info['compiled']
                    try:
                        if compiled_pattern.match(word):
                            matched_finals.add(state.state_id)
                            break  # Premier match suffit pour cet état
                    except re.error:
                        # Pattern corrompu - ignore silencieusement
                        continue

        return matched_finals

    def _build_character_class_index(self):
        """
        Construction index États character-class pour performance

        Pré-indexe tous états ayant compiled_patterns pour éviter
        iteration complète états lors de chaque évaluation.

        Appelé lazy lors première évaluation character-class.
        """
        self._character_class_states = []

        all_states = []

        # Collect depuis states dict ou via get_final_states()
        if hasattr(self, 'states') and self.states:
            all_states = list(self.states.values())
        elif hasattr(self, 'get_final_states'):
            all_states = list(self.get_final_states())

        # Filtre États avec compiled_patterns
        for state in all_states:
            if hasattr(state, 'compiled_patterns') and state.compiled_patterns:
                self._character_class_states.append(state)

        self._character_class_index_built = True

        # Log pour debugging
        if hasattr(self, 'logger'):
            self.logger.debug(f"Character-class index built: {len(self._character_class_states)} states")

    def _invalidate_character_class_cache(self):
        """
        Invalidation cache pour cohérence

        Appelé lors:
        - freeze/unfreeze NFA
        - Ajout nouveaux patterns
        - Modification structure NFA
        """
        self._character_class_cache.clear()
        self._character_class_index_built = False
        self._cache_hits = 0
        self._cache_misses = 0

    def get_character_class_evaluation_stats(self) -> Dict[str, Any]:
        """
        Métriques performance évaluation character-class

        Returns:
            Dict avec cache hits/misses, états indexés, etc.
        """
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_hit_ratio': self._cache_hits / max(1, self._cache_hits + self._cache_misses),
            'cache_size': len(self._character_class_cache),
            'indexed_states': len(self._character_class_states),
            'index_built': self._character_class_index_built
        }


class UnifiedWeightedNFA(CharacterClassEvaluationMixin, WeightedNFA):
    """
    WeightedNFA Unifié avec Support Character-Class Transparent

    Hérite de WeightedNFA standard + CharacterClassEvaluationMixin
    Override evaluate_word() pour utiliser version unifiée

    Usage:
        # API identique - upgrade transparent
        nfa = UnifiedWeightedNFA("unified_nfa")

        # Patterns standards (fonctionnent comme avant)
        nfa.add_weighted_regex_simple("measure1", ".*A.*", Decimal('1.0'))

        # Character-class patterns (nouveaux - si disponible)
        if hasattr(nfa, 'add_weighted_regex_with_character_class_support'):
            nfa.add_weighted_regex_with_character_class_support("measure2", ".*[BC].*", Decimal('2.0'))

        # Évaluation unifiée (API identique)
        results = nfa.evaluate_word("XABY")  # ✅ Matchs standards + character-class
    """

    def __init__(self, nfa_id: str):
        super().__init__(nfa_id)

    def evaluate_word(self, word: str) -> Set[str]:
        """
        Override evaluate_word() pour version unifiée

        API identical à WeightedNFA.evaluate_word() mais avec
        support character-class transparent ajouté.

        Args:
            word: Mot à évaluer

        Returns:
            Set[str]: États finaux atteints (standard + character-class)
        """
        return self.evaluate_word_unified(word)

    def freeze(self):
        """Override freeze() pour invalidation cache"""
        super().freeze()
        if hasattr(self, '_invalidate_character_class_cache'):
            self._invalidate_character_class_cache()

    def unfreeze(self):
        """Override unfreeze() pour invalidation cache"""
        super().unfreeze()
        if hasattr(self, '_invalidate_character_class_cache'):
            self._invalidate_character_class_cache()


def create_unified_anchored_nfa(nfa_id: str) -> 'UnifiedAnchoredWeightedNFA':
    """
    Factory function pour création AnchoredWeightedNFA unifié

    Returns:
        AnchoredWeightedNFA avec support character-class unifié
    """
    from .anchored_nfa import AnchoredWeightedNFA

    class UnifiedAnchoredWeightedNFA(CharacterClassEvaluationMixin, AnchoredWeightedNFA):
        """AnchoredWeightedNFA avec support character-class unifié"""

        def __init__(self, nfa_id: str):
            super().__init__(nfa_id)

        def evaluate_word(self, word: str) -> Set[str]:
            """Override avec version unifiée"""
            return self.evaluate_word_unified(word)

        def freeze(self):
            """Override avec invalidation cache"""
            super().freeze()
            if hasattr(self, '_invalidate_character_class_cache'):
                self._invalidate_character_class_cache()

    return UnifiedAnchoredWeightedNFA(nfa_id)


# Test Integration Examples
def example_unified_usage():
    """
    Exemples d'utilisation architecture unifiée

    Démontre compatibilité API + nouvelles fonctionnalités
    """
    # Création NFA unifié
    nfa = create_unified_anchored_nfa("example_unified")

    # Patterns standards (API existante)
    nfa.add_weighted_regex("measure_I", ".*I.*", Decimal('1.0'))
    nfa.add_weighted_regex("measure_J", ".*J.*", Decimal('1.0'))

    # Character-class pattern (API nouvelle)
    nfa.add_weighted_regex_with_character_class_support("industry", ".*[IJ].*", Decimal('2.0'))

    nfa.freeze()

    # Évaluation unifiée (API identique)
    word_test = "XIY"
    final_states = nfa.evaluate_word(word_test)

    # Résultat: {"measure_I_final", "industry_character_class_final"}
    print(f"Word '{word_test}' matched states: {final_states}")

    # Métriques performance
    stats = nfa.get_character_class_evaluation_stats()
    print(f"Performance stats: {stats}")

if __name__ == "__main__":
    example_unified_usage()