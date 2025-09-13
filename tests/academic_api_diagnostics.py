"""
Module Diagnostic API pour Tests Académiques ICGS

Module de diagnostic unifié pour tracer l'utilisation des APIs
dans tous les tests académiques. Indique clairement si les tests
utilisent l'API primaire ou fallback, et si l'architecture unifiée
character-class est active.

Usage:
    from tests.academic_api_diagnostics import diagnose_nfa_evaluation

    result = diagnose_nfa_evaluation(nfa, "XIY", "TEST_CONTEXT")
    # → Affiche logs détaillés API usage + retourne métadonnées
"""

from typing import Dict, List, Set, Any, Optional
import time


class APIUsageTracker:
    """Tracker global utilisation APIs dans tests académiques"""

    def __init__(self):
        self.api_calls_log: List[Dict[str, Any]] = []
        self.session_stats = {
            'total_evaluations': 0,
            'primary_api_calls': 0,
            'fallback_api_calls': 0,
            'unified_architecture_detections': 0,
            'cache_hits_total': 0,
            'performance_optimized_calls': 0
        }

    def record_api_call(self, diagnostics: Dict[str, Any]):
        """Enregistre appel API pour statistiques globales"""
        self.api_calls_log.append(diagnostics.copy())
        self.session_stats['total_evaluations'] += 1

        if 'evaluate_to_final_state' in diagnostics.get('api_calls', {}):
            if diagnostics['api_calls']['evaluate_to_final_state'] == 'SUCCESS':
                self.session_stats['primary_api_calls'] += 1

        if 'evaluate_word' in diagnostics.get('api_calls', {}):
            if diagnostics['api_calls']['evaluate_word'] == 'SUCCESS':
                self.session_stats['fallback_api_calls'] += 1

        if diagnostics.get('unified_architecture', False):
            self.session_stats['unified_architecture_detections'] += 1

        # Performance stats
        perf_stats = diagnostics.get('performance_stats', {})
        if perf_stats:
            cache_stats = perf_stats.get('cache', {})
            if cache_stats.get('hits', 0) > 0:
                self.session_stats['cache_hits_total'] += cache_stats['hits']
            self.session_stats['performance_optimized_calls'] += 1

    def get_session_summary(self) -> Dict[str, Any]:
        """Résumé session tests académiques"""
        if self.session_stats['total_evaluations'] == 0:
            return {'status': 'NO_EVALUATIONS'}

        return {
            'total_evaluations': self.session_stats['total_evaluations'],
            'primary_api_usage_rate': self.session_stats['primary_api_calls'] / self.session_stats['total_evaluations'],
            'fallback_api_usage_rate': self.session_stats['fallback_api_calls'] / self.session_stats['total_evaluations'],
            'unified_architecture_rate': self.session_stats['unified_architecture_detections'] / self.session_stats['total_evaluations'],
            'performance_optimization_rate': self.session_stats['performance_optimized_calls'] / self.session_stats['total_evaluations'],
            'total_cache_hits': self.session_stats['cache_hits_total']
        }


# Instance globale tracker
global_api_tracker = APIUsageTracker()


def diagnose_nfa_evaluation(nfa, word: str, test_context: str = "ACADEMIC_TEST",
                           verbose: bool = True) -> Dict[str, Any]:
    """
    Diagnostic complet évaluation NFA avec indication fallback

    Trace l'utilisation des APIs et détecte l'architecture unifiée character-class.
    Destiné aux tests académiques pour validation transparence API.

    Args:
        nfa: Instance NFA (WeightedNFA, AnchoredWeightedNFA, etc.)
        word: Mot à évaluer pour diagnostic
        test_context: Contexte test (ex: "TEST_16_TRANSACTION_1")
        verbose: Afficher logs détaillés

    Returns:
        Dict avec résultats API, métriques, et recommandations
    """
    start_time = time.perf_counter()

    diagnostics = {
        'context': test_context,
        'word': word,
        'timestamp': time.time(),
        'api_calls': {},
        'results': {},
        'fallback_used': False,
        'unified_architecture': False,
        'performance_stats': None,
        'api_recommendation': 'UNKNOWN',
        'evaluation_time_ms': 0.0
    }

    if verbose:
        print(f"🔍 ACADEMIC API DIAGNOSTIC [{test_context}]: Testing word '{word}'")

    # ═══════════════════════════════════════════════════════════
    # TEST 1: API Primaire evaluate_to_final_state
    # ═══════════════════════════════════════════════════════════
    if hasattr(nfa, 'evaluate_to_final_state'):
        try:
            result = nfa.evaluate_to_final_state(word)
            diagnostics['api_calls']['evaluate_to_final_state'] = 'SUCCESS'
            diagnostics['results']['primary_api'] = result

            if verbose:
                status = "🎯 SUCCESS" if result is not None else "🎯 NO_MATCH"
                print(f"   {status} PRIMARY API: evaluate_to_final_state('{word}') → {result}")

        except Exception as e:
            diagnostics['api_calls']['evaluate_to_final_state'] = f'ERROR: {str(e)[:50]}'
            diagnostics['fallback_used'] = True
            if verbose:
                print(f"   ❌ PRIMARY API FAILED: {e}")

    # ═══════════════════════════════════════════════════════════
    # TEST 2: API Fallback evaluate_word
    # ═══════════════════════════════════════════════════════════
    if hasattr(nfa, 'evaluate_word'):
        try:
            result = nfa.evaluate_word(word)
            diagnostics['api_calls']['evaluate_word'] = 'SUCCESS'
            diagnostics['results']['fallback_api'] = result

            if verbose:
                status = "🔄 SUCCESS" if result else "🔄 NO_MATCH"
                result_summary = f"{len(result)} states" if isinstance(result, set) and result else "empty"
                print(f"   {status} FALLBACK API: evaluate_word('{word}') → {result_summary}")

            # Détection architecture unifiée character-class
            if hasattr(nfa, '_evaluate_character_class_patterns_direct'):
                try:
                    char_class_result = nfa._evaluate_character_class_patterns_direct(word)
                    diagnostics['results']['character_class_direct'] = char_class_result
                    diagnostics['unified_architecture'] = True

                    if verbose:
                        cc_status = "🎨 SUCCESS" if char_class_result else "🎨 NO_MATCH"
                        cc_summary = f"{len(char_class_result)} states" if char_class_result else "empty"
                        print(f"   {cc_status} CHARACTER-CLASS: '{word}' → {cc_summary}")
                except Exception as e:
                    if verbose:
                        print(f"   🎨 CHARACTER-CLASS ERROR: {e}")

        except Exception as e:
            diagnostics['api_calls']['evaluate_word'] = f'ERROR: {str(e)[:50]}'
            if verbose:
                print(f"   ❌ FALLBACK API FAILED: {e}")

    # ═══════════════════════════════════════════════════════════
    # TEST 3: Performance Stats (si disponible)
    # ═══════════════════════════════════════════════════════════
    if hasattr(nfa, 'get_performance_stats'):
        try:
            stats = nfa.get_performance_stats()
            diagnostics['performance_stats'] = stats

            cache_stats = stats.get('cache', {})
            hit_rate = cache_stats.get('hit_rate', 0)
            cache_size = cache_stats.get('size', 0)

            if verbose and hit_rate > 0:
                print(f"   📈 PERFORMANCE: Cache {hit_rate:.1%} hit rate, {cache_size} entries")

        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════
    # ANALYSE & RECOMMANDATIONS
    # ═══════════════════════════════════════════════════════════
    evaluation_time = (time.perf_counter() - start_time) * 1000
    diagnostics['evaluation_time_ms'] = evaluation_time

    # Détermination statut API
    if diagnostics['unified_architecture']:
        api_status = "✅ UNIFIED"
        diagnostics['api_recommendation'] = 'UNIFIED_ARCHITECTURE_ACTIVE'
    elif diagnostics['fallback_used']:
        api_status = "⚠️ FALLBACK"
        diagnostics['api_recommendation'] = 'FALLBACK_REQUIRED'
    elif diagnostics['api_calls'].get('evaluate_to_final_state') == 'SUCCESS':
        api_status = "🎯 PRIMARY"
        diagnostics['api_recommendation'] = 'PRIMARY_API_OPTIMAL'
    else:
        api_status = "❓ UNKNOWN"
        diagnostics['api_recommendation'] = 'API_STATUS_UNCLEAR'

    if verbose:
        print(f"   📋 STATUS: {api_status} Architecture ({evaluation_time:.2f}ms)")
        print(f"   ─────────────────────────────────────────────")

    # Enregistrement global
    global_api_tracker.record_api_call(diagnostics)

    return diagnostics


def diagnose_pipeline_classify_paths_simulation(nfa, paths: List[str], test_context: str) -> Dict[str, Any]:
    """
    Diagnostic spécialisé simulation pipeline classify_paths_with_nfa

    Simule le comportement du pipeline ICGS path_enumerator.enumerate_and_classify()
    avec diagnostic détaillé de l'usage des APIs primaire vs fallback.

    Args:
        nfa: Instance NFA
        paths: Liste mots/paths à classifier
        test_context: Contexte test académique

    Returns:
        Dict avec classification results + API usage analysis
    """
    print(f"🔄 PIPELINE SIMULATION [{test_context}]: Classifying {len(paths)} paths")

    classification_results = {}
    api_usage_summary = {
        'primary_api_successes': 0,
        'fallback_api_usages': 0,
        'unified_architecture_detections': 0,
        'total_paths': len(paths),
        'classification_rate': 0.0
    }

    for i, path in enumerate(paths):
        # Diagnostic complet pour chaque path
        diagnostics = diagnose_nfa_evaluation(nfa, path, f"{test_context}_PATH_{i}", verbose=False)

        # Simulation logique pipeline classify_paths_with_nfa
        classified_state = None

        # 1. Tentative API primaire (utilisée en premier par pipeline)
        primary_result = diagnostics['results'].get('primary_api')
        if primary_result is not None:
            classified_state = primary_result
            api_usage_summary['primary_api_successes'] += 1

        # 2. Fallback API si primaire échoue
        elif 'fallback_api' in diagnostics['results']:
            fallback_result = diagnostics['results']['fallback_api']
            if fallback_result:
                classified_state = next(iter(fallback_result))  # Premier état
                api_usage_summary['fallback_api_usages'] += 1

        if diagnostics['unified_architecture']:
            api_usage_summary['unified_architecture_detections'] += 1

        classification_results[path] = {
            'classified_state': classified_state,
            'api_used': 'PRIMARY' if primary_result is not None else 'FALLBACK',
            'unified_architecture': diagnostics['unified_architecture']
        }

    # Calcul métriques finales
    classified_count = sum(1 for r in classification_results.values() if r['classified_state'] is not None)
    api_usage_summary['classification_rate'] = classified_count / len(paths) if paths else 0.0

    # Résumé
    primary_rate = api_usage_summary['primary_api_successes'] / len(paths) if paths else 0.0
    unified_rate = api_usage_summary['unified_architecture_detections'] / len(paths) if paths else 0.0

    print(f"   🎯 PRIMARY API: {api_usage_summary['primary_api_successes']}/{len(paths)} ({primary_rate:.1%})")
    print(f"   🔄 FALLBACK API: {api_usage_summary['fallback_api_usages']}/{len(paths)}")
    print(f"   ✅ UNIFIED ARCH: {api_usage_summary['unified_architecture_detections']}/{len(paths)} ({unified_rate:.1%})")
    print(f"   📊 CLASSIFICATION: {classified_count}/{len(paths)} ({api_usage_summary['classification_rate']:.1%})")

    return {
        'classification_results': classification_results,
        'api_usage_summary': api_usage_summary,
        'test_context': test_context
    }


def print_session_api_summary():
    """
    Affiche résumé global session tests académiques

    À appeler en fin de session tests pour récapitulatif usage APIs
    """
    summary = global_api_tracker.get_session_summary()

    if summary.get('status') == 'NO_EVALUATIONS':
        print("📊 SESSION SUMMARY: No API evaluations recorded")
        return

    print("\n" + "="*60)
    print("📊 SESSION API USAGE SUMMARY - TESTS ACADÉMIQUES")
    print("="*60)
    print(f"Total Evaluations: {summary['total_evaluations']}")
    print(f"Primary API Usage: {summary['primary_api_usage_rate']:.1%}")
    print(f"Fallback API Usage: {summary['fallback_api_usage_rate']:.1%}")
    print(f"Unified Architecture: {summary['unified_architecture_rate']:.1%}")
    print(f"Performance Optimized: {summary['performance_optimization_rate']:.1%}")
    print(f"Total Cache Hits: {summary['total_cache_hits']}")

    # Recommandations
    print("\n🎯 RECOMMANDATIONS:")
    if summary['unified_architecture_rate'] > 0.8:
        print("   ✅ Architecture unifiée bien adoptée")
    elif summary['fallback_api_usage_rate'] > 0.5:
        print("   ⚠️  Usage fallback élevé - vérifier API primaire")

    if summary['performance_optimization_rate'] > 0.5:
        print("   📈 Optimisations performance actives")

    print("="*60)


if __name__ == "__main__":
    # Test du module diagnostic
    print("🧪 Test module diagnostic APIs académiques")

    # Simulation test
    class MockNFA:
        def evaluate_to_final_state(self, word):
            return "mock_state" if "I" in word else None

        def evaluate_word(self, word):
            return {"mock_state"} if "I" in word else set()

    mock_nfa = MockNFA()
    result = diagnose_nfa_evaluation(mock_nfa, "XIY", "MOCK_TEST")
    print(f"\nRésultat diagnostic: {result['api_recommendation']}")

    print_session_api_summary()