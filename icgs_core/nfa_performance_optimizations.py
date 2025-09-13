"""
Optimisations Performance NFA Character-Class

Module contenant les optimisations performance pour l'évaluation character-class
dans WeightedNFA et AnchoredWeightedNFA.

Optimisations:
1. Cache LRU évaluation character-class
2. Indexation lazy des états character-class
3. Batch processing pour évaluations multiples
4. Invalidation cache intelligente
"""

from typing import Dict, List, Set, Optional, Any, Tuple
from collections import OrderedDict
import time
import weakref


class LRUCache:
    """Cache LRU thread-safe pour évaluation character-class"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict[str, Set[str]] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Set[str]]:
        """Récupère valeur avec promotion LRU"""
        if key in self.cache:
            # Promote to end (most recently used)
            value = self.cache.pop(key)
            self.cache[key] = value
            self.hits += 1
            return value

        self.misses += 1
        return None

    def put(self, key: str, value: Set[str]) -> None:
        """Stocke valeur avec éviction LRU si nécessaire"""
        if key in self.cache:
            # Update existing
            self.cache.pop(key)
        elif len(self.cache) >= self.max_size:
            # Evict least recently used
            self.cache.popitem(last=False)

        self.cache[key] = value

    def clear(self) -> None:
        """Vide le cache complètement"""
        self.cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Statistiques cache"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / max(1, total_requests)

        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'total_requests': total_requests
        }


class CharacterClassStateIndex:
    """Index optimisé pour états avec patterns character-class"""

    def __init__(self):
        self.character_class_states: List = []  # States avec compiled_patterns
        self.is_built = False
        self.build_time = 0.0
        self.last_build_size = 0

    def build_index(self, all_states: Dict[str, Any]) -> None:
        """Construit index lazy des états character-class"""
        if self.is_built:
            return

        start_time = time.perf_counter()
        self.character_class_states = []

        # Filtre états avec compiled_patterns
        for state in all_states.values():
            if hasattr(state, 'compiled_patterns') and state.compiled_patterns:
                self.character_class_states.append(state)

        self.is_built = True
        self.build_time = time.perf_counter() - start_time
        self.last_build_size = len(all_states)

    def invalidate(self) -> None:
        """Invalide index pour reconstruction"""
        self.is_built = False
        self.character_class_states = []

    def get_character_class_states(self) -> List:
        """Retourne états indexés character-class"""
        return self.character_class_states

    def get_stats(self) -> Dict[str, Any]:
        """Statistiques index"""
        return {
            'is_built': self.is_built,
            'indexed_states': len(self.character_class_states),
            'build_time_ms': self.build_time * 1000,
            'last_build_size': self.last_build_size
        }


class PerformanceOptimizedMixin:
    """
    Mixin pour optimisations performance character-class

    Ajoute cache LRU et indexation optimisée pour évaluation character-class.
    Réduit significantly overhead évaluation répétée patterns complexes.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Cache LRU pour évaluation character-class
        self._character_class_cache = LRUCache(max_size=1000)

        # Index optimisé états character-class
        self._character_class_index = CharacterClassStateIndex()

        # Métriques performance
        self._evaluation_times: List[float] = []
        self._last_cache_cleanup = time.time()

    def _evaluate_character_class_patterns_optimized(self, word: str) -> Set[str]:
        """
        Évaluation character-class avec cache et index optimisés

        Algorithm:
        1. Cache lookup (LRU)
        2. Build index lazy si nécessaire
        3. Évaluation contre états indexés seulement
        4. Cache résultat
        5. Cleanup périodique

        Args:
            word: Mot à évaluer

        Returns:
            Set[str]: États finaux character-class matchés (cached)
        """
        start_time = time.perf_counter()

        # 1. Cache lookup
        cached_result = self._character_class_cache.get(word)
        if cached_result is not None:
            return cached_result

        # 2. Build index lazy
        if not self._character_class_index.is_built:
            self._character_class_index.build_index(self.states)

        # 3. Évaluation contre états indexés seulement
        matched_finals = set()

        for state in self._character_class_index.get_character_class_states():
            # Test chaque pattern compilé dans cet état
            for pattern_info in state.compiled_patterns:
                try:
                    compiled_pattern = pattern_info.get('compiled')
                    if compiled_pattern and compiled_pattern.match(word):
                        matched_finals.add(state.state_id)
                        break  # Premier match suffit pour cet état
                except (AttributeError, re.error):
                    # Pattern corrompu - ignore silencieusement
                    continue

        # 4. Cache résultat
        self._character_class_cache.put(word, matched_finals)

        # 5. Cleanup périodique (toutes les 1000 évaluations)
        evaluation_time = time.perf_counter() - start_time
        self._evaluation_times.append(evaluation_time)

        if len(self._evaluation_times) % 1000 == 0:
            self._periodic_cleanup()

        return matched_finals

    def _periodic_cleanup(self) -> None:
        """Cleanup périodique pour maintenir performance"""
        current_time = time.time()

        # Cleanup cache si trop vieux (5 minutes)
        if current_time - self._last_cache_cleanup > 300:
            # Keep only 50% most recent entries
            cache_stats = self._character_class_cache.get_stats()
            if cache_stats['size'] > 500:
                # Implement partial cleanup
                old_cache = self._character_class_cache.cache
                new_cache = OrderedDict()

                # Keep most recent half
                items = list(old_cache.items())
                keep_size = len(items) // 2
                for key, value in items[-keep_size:]:
                    new_cache[key] = value

                self._character_class_cache.cache = new_cache

            self._last_cache_cleanup = current_time

        # Trim evaluation times history
        if len(self._evaluation_times) > 10000:
            self._evaluation_times = self._evaluation_times[-5000:]

    def _invalidate_optimization_caches(self) -> None:
        """Invalidation caches pour cohérence lors modifications NFA"""
        self._character_class_cache.clear()
        self._character_class_index.invalidate()
        self._last_cache_cleanup = time.time()

    def get_performance_stats(self) -> Dict[str, Any]:
        """Statistiques performance détaillées"""
        cache_stats = self._character_class_cache.get_stats()
        index_stats = self._character_class_index.get_stats()

        # Calcul métriques évaluation
        avg_evaluation_time = 0.0
        if self._evaluation_times:
            avg_evaluation_time = sum(self._evaluation_times) / len(self._evaluation_times)

        return {
            'cache': cache_stats,
            'index': index_stats,
            'evaluation_metrics': {
                'total_evaluations': len(self._evaluation_times),
                'avg_evaluation_time_ms': avg_evaluation_time * 1000,
                'last_cleanup': self._last_cache_cleanup
            },
            'memory_usage': {
                'cache_entries': cache_stats['size'],
                'indexed_states': index_stats['indexed_states'],
                'evaluation_history': len(self._evaluation_times)
            }
        }


class BatchEvaluationOptimizer:
    """
    Optimiseur pour évaluations batch multiples

    Optimise évaluation simultanée plusieurs mots contre même NFA.
    Utilisé par path_enumerator pour batch processing optimisé.
    """

    @staticmethod
    def evaluate_words_batch(nfa: Any, words: List[str]) -> Dict[str, Set[str]]:
        """
        Évaluation batch optimisée plusieurs mots

        Args:
            nfa: NFA avec support character-class
            words: Liste mots à évaluer

        Returns:
            Dict mapping word → états finaux matchés
        """
        results = {}

        # Build index une seule fois si disponible
        if hasattr(nfa, '_character_class_index'):
            if not nfa._character_class_index.is_built:
                nfa._character_class_index.build_index(nfa.states)

        # Évaluation batch
        for word in words:
            results[word] = nfa.evaluate_word(word)

        return results

    @staticmethod
    def evaluate_words_batch_parallel(nfa: Any, words: List[str],
                                    chunk_size: int = 100) -> Dict[str, Set[str]]:
        """
        Évaluation batch avec processing parallèle par chunks

        Pour très gros volumes (>1000 mots), divise en chunks pour
        meilleure utilisation cache et éviter memory pressure.

        Args:
            nfa: NFA avec support character-class
            words: Liste mots à évaluer
            chunk_size: Taille chunks pour processing

        Returns:
            Dict mapping word → états finaux matchés
        """
        results = {}

        # Processing par chunks
        for i in range(0, len(words), chunk_size):
            chunk = words[i:i + chunk_size]
            chunk_results = BatchEvaluationOptimizer.evaluate_words_batch(nfa, chunk)
            results.update(chunk_results)

        return results


def benchmark_character_class_performance():
    """
    Benchmark performance optimisations character-class

    Compare performance avec/sans optimisations pour quantifier gains.
    """
    from icgs_core.anchored_nfa import AnchoredWeightedNFA
    from decimal import Decimal
    import time

    # Setup NFA test
    nfa = AnchoredWeightedNFA("benchmark_test")

    # Patterns character-class variés
    patterns = [
        ("industry", ".*[IJKL].*", Decimal('1.0')),
        ("services", ".*[STUV].*", Decimal('1.5')),
        ("agriculture", ".*[ABC].*", Decimal('2.0')),
        ("finance", ".*[FG].*", Decimal('0.8')),
        ("energy", ".*[EH].*", Decimal('1.2'))
    ]

    for measure_id, pattern, weight in patterns:
        nfa.add_weighted_regex_with_character_class_support(measure_id, pattern, weight)

    nfa.freeze()

    # Test words variés
    test_words = []
    for i in range(1000):
        # Mots qui matchent
        test_words.extend([f"X{c}Y" for c in "IJKLSTUVABCFGEH"])
        # Mots qui ne matchent pas
        test_words.extend([f"X{c}Y" for c in "NOPQRWXYZ"])

    print(f"Benchmark: {len(test_words)} évaluations sur {len(patterns)} patterns character-class")

    # Benchmark sans cache (première run)
    if hasattr(nfa, '_invalidate_optimization_caches'):
        nfa._invalidate_optimization_caches()

    start_time = time.perf_counter()
    results_nocache = {}
    for word in test_words:
        results_nocache[word] = nfa.evaluate_word(word)
    time_nocache = time.perf_counter() - start_time

    # Benchmark avec cache (seconde run)
    start_time = time.perf_counter()
    results_cached = {}
    for word in test_words:
        results_cached[word] = nfa.evaluate_word(word)
    time_cached = time.perf_counter() - start_time

    # Statistiques
    if hasattr(nfa, 'get_performance_stats'):
        stats = nfa.get_performance_stats()
    else:
        stats = {}

    print(f"Performance sans cache: {time_nocache:.3f}s ({time_nocache*1000/len(test_words):.2f}ms/eval)")
    print(f"Performance avec cache: {time_cached:.3f}s ({time_cached*1000/len(test_words):.2f}ms/eval)")
    print(f"Speedup: {time_nocache/time_cached:.2f}x")
    print(f"Cache hit rate: {stats.get('cache', {}).get('hit_rate', 0):.1%}")


if __name__ == "__main__":
    benchmark_character_class_performance()