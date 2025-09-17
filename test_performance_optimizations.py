#!/usr/bin/env python3
"""
Test Performance Optimizations - Validation Cache et 3D pour 65 Agents

Tests pour valider les optimisations de performance implémentées:
- PerformanceCache avec TTL et cleanup LRU
- Validation cache pour transactions
- Cache données 3D pour analyses volumineuses
- Optimisations web pour 65 agents
"""

import sys
import os
import time
from decimal import Decimal

# Import du module simulation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))
from icgs_simulation.api.icgs_bridge import EconomicSimulation, SimulationMode


def test_performance_cache_basic():
    """Test fonctionnalité de base du cache de performance"""
    print("🔍 Test cache de performance basique")

    simulation = EconomicSimulation("test_cache", agents_mode="65_agents")

    # Vérifier que le cache est initialisé
    assert hasattr(simulation, 'performance_cache'), "PerformanceCache non initialisé"

    # Statistiques cache initial
    initial_stats = simulation.performance_cache.get_cache_stats()
    assert initial_stats['hit_count'] == 0, "Hit count initial doit être 0"
    assert initial_stats['miss_count'] == 0, "Miss count initial doit être 0"

    print(f"   ✅ Cache initialisé: {initial_stats}")
    return True


def test_transaction_validation_caching():
    """Test mise en cache validation transactions"""
    print("🔍 Test cache validation transactions")

    simulation = EconomicSimulation("test_validation_cache", agents_mode="40_agents")

    # Créer quelques agents
    simulation.create_agent("FARM_01", "AGRICULTURE", Decimal('1000'))
    simulation.create_agent("INDU_01", "INDUSTRY", Decimal('800'))

    # Créer transaction
    tx_id = simulation.create_transaction("FARM_01", "INDU_01", Decimal('100'))

    # Premier appel - devrait être un cache miss
    start_time = time.time()
    result1 = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
    first_call_time = time.time() - start_time

    # Deuxième appel - devrait être un cache hit
    start_time = time.time()
    result2 = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
    second_call_time = time.time() - start_time

    # Vérifier que les résultats sont identiques
    assert result1.success == result2.success, "Résultats cache inconsistants"
    assert result1.status == result2.status, "Status cache inconsistants"

    # Vérifier statistiques cache
    cache_stats = simulation.performance_cache.get_cache_stats()
    assert cache_stats['hit_count'] >= 1, "Pas de cache hit détecté"

    print(f"   ✅ Premier appel: {first_call_time*1000:.2f}ms")
    print(f"   ✅ Deuxième appel (cache): {second_call_time*1000:.2f}ms")
    print(f"   ✅ Cache hit rate: {cache_stats['hit_rate_percent']}%")

    return True


def test_performance_stats_comprehensive():
    """Test statistiques performance complètes"""
    print("🔍 Test statistiques performance complètes")

    simulation = EconomicSimulation("test_perf_stats", agents_mode="65_agents")

    # Créer agents variés
    for i in range(5):
        simulation.create_agent(f"AGRI_{i:02d}", "AGRICULTURE", Decimal('1200'))
        simulation.create_agent(f"INDU_{i:02d}", "INDUSTRY", Decimal('900'))
        simulation.create_agent(f"SERV_{i:02d}", "SERVICES", Decimal('700'))

    # Créer transactions
    tx_ids = []
    for i in range(3):
        tx_id = simulation.create_transaction(f"AGRI_{i:02d}", f"INDU_{i:02d}", Decimal('50'))
        tx_ids.append(tx_id)

    # Validation transactions
    for tx_id in tx_ids:
        simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)

    # Obtenir statistiques complètes
    stats = simulation.get_performance_stats()

    # Vérifications
    assert 'cache_performance' in stats, "Pas de stats cache"
    assert 'simulation' in stats, "Pas de stats simulation"
    assert 'sectors_distribution' in stats, "Pas de distribution secteurs"

    assert stats['simulation']['agents_count'] == 15, f"Nombre agents incorrect: {stats['simulation']['agents_count']}"
    assert stats['simulation']['transactions_count'] == 3, f"Nombre transactions incorrect: {stats['simulation']['transactions_count']}"

    print(f"   ✅ Agents: {stats['simulation']['agents_count']}")
    print(f"   ✅ Transactions: {stats['simulation']['transactions_count']}")
    print(f"   ✅ Cache hit rate: {stats['cache_performance']['hit_rate_percent']}%")
    print(f"   ✅ Secteurs: {stats['sectors_distribution']}")

    return True


def test_web_load_optimization():
    """Test optimisations pour charge web"""
    print("🔍 Test optimisations charge web")

    simulation = EconomicSimulation("test_web_opt", agents_mode="65_agents")

    # Créer agents massifs (simulation 65 agents) - besoin >= 40 pour optimisation
    # Distribution respectant limites sectorielles: AGRICULTURE(10), INDUSTRY(15), SERVICES(20), FINANCE(8), ENERGY(12)
    sectors_config = [
        ("AGRICULTURE", 10), ("INDUSTRY", 15), ("SERVICES", 20),
        ("FINANCE", 8), ("ENERGY", 12)
    ]

    agent_count = 0
    for sector_name, max_agents in sectors_config:
        for i in range(max_agents):
            simulation.create_agent(f"{sector_name}_{i:02d}", sector_name, Decimal('500'))
            agent_count += 1

    # Appliquer optimisations web
    simulation.optimize_for_web_load()

    # Vérifier que taxonomie est configurée
    assert simulation.taxonomy_configured, "Taxonomie pas configurée après optimisation"

    # Vérifier ajustements TTL cache
    assert simulation.performance_cache.validation_ttl <= 200.0, "TTL validation pas ajusté"
    assert simulation.performance_cache.data_3d_ttl <= 350.0, "TTL 3D pas ajusté"

    print(f"   ✅ Taxonomie configurée: {simulation.taxonomy_configured}")
    print(f"   ✅ TTL validation: {simulation.performance_cache.validation_ttl}s")
    print(f"   ✅ TTL données 3D: {simulation.performance_cache.data_3d_ttl}s")

    return True


def test_cache_cleanup_lru():
    """Test nettoyage LRU du cache"""
    print("🔍 Test cleanup LRU cache")

    # Créer simulation avec cache petit pour test
    simulation = EconomicSimulation("test_lru", agents_mode="7_agents")
    simulation.performance_cache.max_validation_cache = 5  # Limite très basse

    # Créer agents
    simulation.create_agent("FARM_01", "AGRICULTURE", Decimal('1000'))
    simulation.create_agent("INDU_01", "INDUSTRY", Decimal('800'))

    # Créer et valider plus de transactions que la limite cache
    tx_ids = []
    for i in range(8):  # Plus que max_validation_cache
        tx_id = simulation.create_transaction("FARM_01", "INDU_01", Decimal(f'{100+i*10}'))
        tx_ids.append(tx_id)
        simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)

    # Vérifier que le cache ne dépasse pas sa limite
    cache_stats = simulation.performance_cache.get_cache_stats()
    assert cache_stats['validation_cache_size'] <= 5, f"Cache trop grand: {cache_stats['validation_cache_size']}"

    print(f"   ✅ Cache size après cleanup: {cache_stats['validation_cache_size']}/5")
    print(f"   ✅ Transactions traitées: {len(tx_ids)}")

    return True


def test_65_agents_stress_performance():
    """Test stress performance avec configuration 65 agents"""
    print("🔍 Test stress performance 65 agents")

    simulation = EconomicSimulation("test_65_stress", agents_mode="65_agents")

    # Créer 20 agents pour simulation stress
    start_agents = time.time()
    for i in range(20):
        sector = ["AGRICULTURE", "INDUSTRY", "SERVICES", "FINANCE", "ENERGY"][i % 5]
        simulation.create_agent(f"AGENT_{i:02d}", sector, Decimal('1000'))
    agents_time = time.time() - start_agents

    # Créer 10 transactions
    start_tx = time.time()
    tx_ids = []
    for i in range(10):
        source = f"AGENT_{i:02d}"
        target = f"AGENT_{(i+5)%20:02d}"
        tx_id = simulation.create_transaction(source, target, Decimal('100'))
        tx_ids.append(tx_id)
    tx_time = time.time() - start_tx

    # Validation avec mesure performance
    start_validation = time.time()
    feasible_count = 0
    for tx_id in tx_ids:
        result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
        if result.success:
            feasible_count += 1
    validation_time = time.time() - start_validation

    # Statistiques finales
    stats = simulation.get_performance_stats()

    print(f"   ✅ Création agents: {agents_time*1000:.1f}ms (20 agents)")
    print(f"   ✅ Création transactions: {tx_time*1000:.1f}ms (10 tx)")
    print(f"   ✅ Validation: {validation_time*1000:.1f}ms ({feasible_count}/10 feasible)")
    print(f"   ✅ Cache hit rate: {stats['cache_performance']['hit_rate_percent']}%")
    print(f"   ✅ Character-Set capacity: {stats['character_set_manager']['total_allocations']} chars")

    return True


def main():
    """Lance tous les tests performance"""
    print("🚀 TESTS OPTIMISATIONS PERFORMANCE - 65 AGENTS")
    print("=" * 60)

    tests = [
        test_performance_cache_basic,
        test_transaction_validation_caching,
        test_performance_stats_comprehensive,
        test_web_load_optimization,
        test_cache_cleanup_lru,
        test_65_agents_stress_performance
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            result = test()
            if result:
                passed += 1
                print("✅ PASS\n")
            else:
                failed += 1
                print("❌ FAIL\n")
        except Exception as e:
            failed += 1
            print(f"❌ FAIL - Exception: {e}\n")

    print("=" * 60)
    print(f"📊 RÉSULTATS: {passed} PASS, {failed} FAIL")

    if failed == 0:
        print("🎉 SUCCÈS TOTAL - Optimisations performance validées")
        print("✅ Cache LRU avec TTL fonctionnel")
        print("✅ Validation transactions cachée")
        print("✅ Optimisations web 65 agents opérationnelles")
    else:
        print("⚠️  Certains tests échouent - Investigation requise")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)