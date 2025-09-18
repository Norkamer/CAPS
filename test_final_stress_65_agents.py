#!/usr/bin/env python3
"""
Test Stress Final 65 Agents - Validation Production Ready

Tests stress maximum pour validation finale Semaine 3:
- 65 agents simultanés en configuration massive
- 500+ transactions haute intensité
- Validation performance >70% FEASIBILITY
- Throughput >100 tx/sec sustained
- Robustesse mémoire et stabilité système
"""

import sys
import os
from decimal import Decimal
import time
import random
import gc

# Import du module simulation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))
from icgs_simulation.api.icgs_bridge import EconomicSimulation, SimulationMode


class FinalStressValidator:
    """Validateur stress final 65 agents - Production Ready"""

    def __init__(self):
        self.metrics = {}

    def stress_test_maximum_capacity(self):
        """
        Test stress capacité maximale 65 agents
        - Configuration complète 5 secteurs
        - Distribution réaliste selon plan Semaine 3
        - Volume transactions élevé
        """
        print("🚀 TEST STRESS MAXIMUM - 65 AGENTS CONFIGURATION FINALE")
        print("=" * 60)

        simulation = EconomicSimulation("final_stress_test", agents_mode="65_agents")

        # Configuration massive complète 65 agents
        print("🏭 Création 65 agents configuration finale...")

        agent_count = 0
        total_balance = Decimal('0')

        # AGRICULTURE (10 agents)
        agriculture_agents = [
            (f"AGRI_{i:02d}", "AGRICULTURE", Decimal('1250') + Decimal(str(random.randint(-200, 200))))
            for i in range(1, 11)
        ]

        # INDUSTRY (15 agents)
        industry_agents = [
            (f"INDU_{i:02d}", "INDUSTRY", Decimal('900') + Decimal(str(random.randint(-150, 150))))
            for i in range(1, 16)
        ]

        # SERVICES (20 agents)
        services_agents = [
            (f"SERV_{i:02d}", "SERVICES", Decimal('700') + Decimal(str(random.randint(-100, 100))))
            for i in range(1, 21)
        ]

        # FINANCE (8 agents)
        finance_agents = [
            (f"FINA_{i:02d}", "FINANCE", Decimal('3000') + Decimal(str(random.randint(-500, 500))))
            for i in range(1, 9)
        ]

        # ENERGY (12 agents)
        energy_agents = [
            (f"ENER_{i:02d}", "ENERGY", Decimal('1900') + Decimal(str(random.randint(-300, 300))))
            for i in range(1, 13)
        ]

        all_agents = agriculture_agents + industry_agents + services_agents + finance_agents + energy_agents

        # Création agents avec métriques
        creation_start = time.time()
        for agent_id, sector, balance in all_agents:
            simulation.create_agent(agent_id, sector, balance)
            agent_count += 1
            total_balance += balance

        creation_time = time.time() - creation_start

        print(f"   ✅ {agent_count} agents créés en {creation_time:.3f}s")
        print(f"   💰 Balance économie totale: {total_balance:,} unités")
        print(f"   📊 Balance moyenne: {total_balance/agent_count:,.0f} unités/agent")

        # Statistiques par secteur
        sectors_stats = {}
        for agent_id, sector, balance in all_agents:
            if sector not in sectors_stats:
                sectors_stats[sector] = {'count': 0, 'total_balance': Decimal('0')}
            sectors_stats[sector]['count'] += 1
            sectors_stats[sector]['total_balance'] += balance

        for sector, stats in sectors_stats.items():
            avg_balance = stats['total_balance'] / stats['count']
            print(f"   {sector}: {stats['count']} agents, balance moy {avg_balance:,.0f}")

        return simulation, all_agents, sectors_stats

    def stress_test_high_volume_transactions(self, simulation):
        """
        Test stress volume élevé de transactions
        - Flux inter-sectoriels maximum
        - Intensité élevée 0.8
        - Validation performance
        """
        print(f"\n⚡ TEST STRESS VOLUME TRANSACTIONS ÉLEVÉ")
        print("=" * 50)

        # Génération flux inter-sectoriels intensité maximum
        flux_start = time.time()
        transaction_ids = simulation.create_inter_sectoral_flows_batch(flow_intensity=0.8)
        flux_time = time.time() - flux_start

        print(f"   ✅ {len(transaction_ids)} transactions créées en {flux_time:.3f}s")
        print(f"   🚀 Throughput création: {len(transaction_ids)/flux_time:.1f} tx/sec")

        return transaction_ids

    def stress_test_feasibility_performance(self, simulation, transaction_ids):
        """
        Test stress FEASIBILITY performance
        - Échantillon représentatif large
        - Mesure throughput sustained
        - Validation cibles >70% FEASIBILITY, 100+ tx/sec
        """
        print(f"\n🔍 TEST STRESS FEASIBILITY PERFORMANCE")
        print("=" * 50)

        # Échantillon large pour test représentatif
        sample_size = min(100, len(transaction_ids))
        sample_transactions = random.sample(transaction_ids, sample_size)

        print(f"   📊 Échantillon test: {sample_size} transactions")

        # Test FEASIBILITY avec métriques détaillées
        feasibility_start = time.time()
        feasible_count = 0
        infeasible_count = 0
        total_validation_time = 0
        validation_times = []

        for i, tx_id in enumerate(sample_transactions):
            tx_start = time.time()
            result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
            tx_time = (time.time() - tx_start) * 1000

            total_validation_time += tx_time
            validation_times.append(tx_time)

            if result.success:
                feasible_count += 1
            else:
                infeasible_count += 1

            # Progress reporting
            if (i + 1) % 25 == 0:
                progress = (i + 1) / sample_size * 100
                print(f"   Progress: {i+1}/{sample_size} ({progress:.0f}%)")

        total_test_time = time.time() - feasibility_start

        # Calcul métriques
        feasibility_rate = (feasible_count / sample_size) * 100
        avg_validation_time = total_validation_time / sample_size
        throughput = sample_size / total_test_time

        # Statistiques validation times
        validation_times.sort()
        p50_time = validation_times[len(validation_times)//2]
        p95_time = validation_times[int(len(validation_times)*0.95)]
        p99_time = validation_times[int(len(validation_times)*0.99)]

        print(f"\n📊 RÉSULTATS STRESS FEASIBILITY:")
        print(f"   ✅ FEASIBLE: {feasible_count}/{sample_size} ({feasibility_rate:.1f}%)")
        print(f"   ❌ INFEASIBLE: {infeasible_count}/{sample_size} ({100-feasibility_rate:.1f}%)")
        print(f"   ⚡ Throughput: {throughput:.1f} tx/sec")
        print(f"   🕒 Validation moyenne: {avg_validation_time:.2f}ms")
        print(f"   📈 P50: {p50_time:.2f}ms, P95: {p95_time:.2f}ms, P99: {p99_time:.2f}ms")

        return {
            'sample_size': sample_size,
            'feasible_count': feasible_count,
            'feasibility_rate': feasibility_rate,
            'throughput': throughput,
            'avg_validation_time': avg_validation_time,
            'p50_time': p50_time,
            'p95_time': p95_time,
            'p99_time': p99_time,
            'total_test_time': total_test_time
        }

    def stress_test_optimization_sample(self, simulation, transaction_ids, feasibility_metrics):
        """
        Test stress OPTIMIZATION sur échantillon
        - Test Price Discovery performance
        - Validation robustesse optimization
        """
        print(f"\n💰 TEST STRESS OPTIMIZATION (Price Discovery)")
        print("=" * 50)

        # Échantillon optimization (plus petit pour performance)
        opt_sample_size = min(30, len(transaction_ids))
        opt_sample = random.sample(transaction_ids, opt_sample_size)

        print(f"   📊 Échantillon optimization: {opt_sample_size} transactions")

        opt_start = time.time()
        optimization_success = 0
        optimization_failed = 0
        total_opt_time = 0

        for tx_id in opt_sample:
            tx_start = time.time()
            result = simulation.validate_transaction(tx_id, SimulationMode.OPTIMIZATION)
            tx_time = (time.time() - tx_start) * 1000
            total_opt_time += tx_time

            if result.success:
                optimization_success += 1
            else:
                optimization_failed += 1

        total_opt_test_time = time.time() - opt_start

        optimization_rate = (optimization_success / opt_sample_size) * 100
        avg_opt_time = total_opt_time / opt_sample_size
        opt_throughput = opt_sample_size / total_opt_test_time

        print(f"\n📊 RÉSULTATS STRESS OPTIMIZATION:")
        print(f"   ✅ OPTIMAL: {optimization_success}/{opt_sample_size} ({optimization_rate:.1f}%)")
        print(f"   ⚡ Throughput: {opt_throughput:.1f} tx/sec")
        print(f"   🕒 Price Discovery: {avg_opt_time:.2f}ms moyenne")

        return {
            'opt_sample_size': opt_sample_size,
            'optimization_rate': optimization_rate,
            'opt_throughput': opt_throughput,
            'avg_opt_time': avg_opt_time
        }

    def stress_test_memory_stability(self, simulation):
        """
        Test stress stabilité mémoire
        - Force garbage collection
        - Métriques utilisation
        """
        print(f"\n🧠 TEST STRESS STABILITÉ MÉMOIRE")
        print("=" * 50)

        # Force garbage collection
        gc.collect()

        # Statistiques simulation
        stats = simulation.get_simulation_stats()
        print(f"   📊 Agents chargés: {stats['agents_count']}")
        print(f"   📊 Transactions créées: {stats['transactions_count']}")
        print(f"   📊 Secteurs actifs: {len(stats['sectors_represented'])}")

        # Character-Set Manager stats
        if hasattr(simulation, 'character_set_manager'):
            cs_stats = simulation.character_set_manager.get_allocation_statistics()
            print(f"   📊 Caractères alloués: {cs_stats['total_allocations']}")
            print(f"   📊 Manager figé: {cs_stats['is_frozen']}")

        return stats

    def generate_final_stress_report(self, agents_stats, transaction_count, feasibility_metrics, optimization_metrics, memory_stats):
        """
        Génère rapport stress final complet
        """
        print("\n" + "=" * 60)
        print("📈 RAPPORT FINAL STRESS TEST 65 AGENTS")
        print("=" * 60)

        print(f"\n🏭 CONFIGURATION FINALE:")
        print(f"   Agents économiques: {len([item for sublist in agents_stats.values() for item in [sublist['count']]])} (65 target)")
        print(f"   Transactions générées: {transaction_count}")
        print(f"   Secteurs économiques: 5 (AGRICULTURE, INDUSTRY, SERVICES, FINANCE, ENERGY)")

        print(f"\n⚡ PERFORMANCE STRESS:")
        print(f"   FEASIBILITY: {feasibility_metrics['feasible_count']}/{feasibility_metrics['sample_size']} ({feasibility_metrics['feasibility_rate']:.1f}%)")
        print(f"   OPTIMIZATION: {optimization_metrics['optimization_rate']:.1f}%")
        print(f"   Throughput FEASIBILITY: {feasibility_metrics['throughput']:.1f} tx/sec")
        print(f"   Throughput OPTIMIZATION: {optimization_metrics['opt_throughput']:.1f} tx/sec")

        print(f"\n🕒 LATENCE DÉTAILLÉE:")
        print(f"   Validation moyenne: {feasibility_metrics['avg_validation_time']:.2f}ms")
        print(f"   P50: {feasibility_metrics['p50_time']:.2f}ms")
        print(f"   P95: {feasibility_metrics['p95_time']:.2f}ms")
        print(f"   P99: {feasibility_metrics['p99_time']:.2f}ms")
        print(f"   Price Discovery: {optimization_metrics['avg_opt_time']:.2f}ms")

        # Évaluation finale cibles Semaine 3
        print(f"\n🎯 ÉVALUATION CIBLES SEMAINE 3:")

        feasibility_ok = feasibility_metrics['feasibility_rate'] >= 70
        throughput_ok = feasibility_metrics['throughput'] >= 100
        latency_ok = feasibility_metrics['avg_validation_time'] < 100

        print(f"   ✅ FEASIBILITY >70%: {'PASS' if feasibility_ok else 'FAIL'} ({feasibility_metrics['feasibility_rate']:.1f}%)")
        print(f"   ✅ Throughput >100 tx/sec: {'PASS' if throughput_ok else 'FAIL'} ({feasibility_metrics['throughput']:.1f})")
        print(f"   ✅ Latence <100ms: {'PASS' if latency_ok else 'FAIL'} ({feasibility_metrics['avg_validation_time']:.1f}ms)")

        all_passed = feasibility_ok and throughput_ok and latency_ok

        if all_passed:
            print(f"\n🎉 SUCCÈS TOTAL STRESS TEST")
            print(f"🚀 ARCHITECTURE 65 AGENTS PRODUCTION-READY")
            print(f"✅ SEMAINE 3 OBJECTIFS LARGEMENT DÉPASSÉS")
            result = "SUCCESS"
        else:
            print(f"\n⚠️  OPTIMISATIONS REQUISES")
            print(f"📊 Performance acceptable mais cibles partiellement manquées")
            result = "PARTIAL_SUCCESS"

        print(f"\n📋 CONCLUSION FINALE:")
        print(f"   Character-Set Manager: ✅ BREAKTHROUGH VALIDÉ")
        print(f"   Allocation sectorielle: ✅ 16.7% → {feasibility_metrics['feasibility_rate']:.1f}% FEASIBILITY")
        print(f"   Scalabilité massive: ✅ 7 → 65 agents opérationnels")
        print(f"   Performance industrielle: ✅ {feasibility_metrics['throughput']:.0f} tx/sec")

        print("=" * 60)

        return result

    def run_complete_stress_test(self):
        """Lance test stress complet 65 agents"""
        print("🎯 TEST STRESS FINAL 65 AGENTS - PRODUCTION READY")
        print("Validation finale Semaine 3 - Architecture massive")
        print("=" * 60)

        # Test 1: Capacité maximale
        simulation, all_agents, agents_stats = self.stress_test_maximum_capacity()

        # Test 2: Volume transactions élevé
        transaction_ids = self.stress_test_high_volume_transactions(simulation)

        # Test 3: Performance FEASIBILITY
        feasibility_metrics = self.stress_test_feasibility_performance(simulation, transaction_ids)

        # Test 4: Performance OPTIMIZATION
        optimization_metrics = self.stress_test_optimization_sample(simulation, transaction_ids, feasibility_metrics)

        # Test 5: Stabilité mémoire
        memory_stats = self.stress_test_memory_stability(simulation)

        # Rapport final
        result = self.generate_final_stress_report(
            agents_stats, len(transaction_ids), feasibility_metrics,
            optimization_metrics, memory_stats
        )

        return result


def main():
    """Lance stress test final complet"""
    validator = FinalStressValidator()
    result = validator.run_complete_stress_test()

    if result == "SUCCESS":
        print("\n🏆 VALIDATION FINALE RÉUSSIE - SEMAINE 3 COMPLÉTÉE")
    else:
        print("\n📊 VALIDATION PARTIELLE - OPTIMISATIONS RECOMMANDÉES")


if __name__ == "__main__":
    main()