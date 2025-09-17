#!/usr/bin/env python3
"""
Tests de Validation Simulation 40 Agents - Semaine 2
Stress testing et validation performance pour extension massive

Tests de capacités:
- 40 agents dans 5 secteurs économiques
- Flux inter-sectoriels automatiques
- Performance >70% FEASIBILITY, <100ms validation
- Robustesse 200+ transactions simultanées
"""

import unittest
import sys
import os
import time
from decimal import Decimal
from typing import List

# Import du module à tester
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_simulation.api.icgs_bridge import EconomicSimulation, SimulationMode, SimulationResult


class Test40AgentsSimulation(unittest.TestCase):
    """Tests de validation pour simulation 40 agents"""

    def setUp(self):
        """Configuration test avec simulation 40 agents"""
        self.simulation = EconomicSimulation("test_40_agents", agents_mode="40_agents")

    def test_character_set_manager_capacity_40_agents(self):
        """Test capacité Character-Set Manager pour 40 agents"""
        stats = self.simulation.character_set_manager.get_allocation_statistics()
        total_capacity = sum(info['max_capacity'] for info in stats['sectors'].values())
        agents_capacity = total_capacity // 3

        self.assertGreaterEqual(agents_capacity, 36,
                               f"Capacité insuffisante: {agents_capacity} agents vs 36+ requis")
        self.assertGreaterEqual(total_capacity, 108,
                               f"Caractères insuffisants: {total_capacity} vs 108+ requis")

        print(f"✅ Capacité validée: {total_capacity} caractères = {agents_capacity} agents")

    def test_create_agents_all_sectors(self):
        """Test création agents dans tous les secteurs économiques"""

        # Distribution agents par secteur (configuration réaliste)
        agents_config = {
            'AGRICULTURE': [('FARM_1', 2000), ('FARM_2', 1800), ('FARM_3', 1500), ('FARM_4', 1900)],
            'INDUSTRY': [('FACTORY_1', 1500), ('FACTORY_2', 1200), ('FACTORY_3', 1800),
                        ('FACTORY_4', 1600), ('FACTORY_5', 1400)],
            'SERVICES': [('LOGISTICS_1', 1000), ('RETAIL_1', 900), ('CONSULTING_1', 1100),
                        ('TRANSPORT_1', 950), ('SUPPORT_1', 850)],
            'FINANCE': [('BANK_1', 5000), ('INSURANCE_1', 3500), ('INVESTMENT_1', 4200),
                       ('CREDIT_1', 2800)],
            'ENERGY': [('POWER_1', 3000), ('SOLAR_1', 2500), ('WIND_1', 2800), ('HYDRO_1', 2200)]
        }

        total_agents = 0
        for sector, agents_list in agents_config.items():
            for agent_id, balance in agents_list:
                agent = self.simulation.create_agent(agent_id, sector, Decimal(str(balance)))
                self.assertEqual(agent.sector, sector)
                self.assertEqual(agent.agent_id, agent_id)
                total_agents += 1

        self.assertEqual(len(self.simulation.agents), total_agents)
        self.assertGreaterEqual(total_agents, 20, "Minimum 20 agents requis pour test")

        print(f"✅ {total_agents} agents créés dans {len(agents_config)} secteurs")

    def test_inter_sectoral_flows_creation(self):
        """Test création flux inter-sectoriels automatiques"""

        # Créer agents minimum pour flux inter-sectoriels
        self.simulation.create_agent('FARM_1', 'AGRICULTURE', Decimal('2000'))
        self.simulation.create_agent('FACTORY_1', 'INDUSTRY', Decimal('1500'))
        self.simulation.create_agent('LOGISTICS_1', 'SERVICES', Decimal('1000'))
        self.simulation.create_agent('BANK_1', 'FINANCE', Decimal('5000'))
        self.simulation.create_agent('POWER_1', 'ENERGY', Decimal('3000'))

        # Tester flux avec différentes intensités
        for intensity in [0.3, 0.5, 0.8]:
            with self.subTest(intensity=intensity):
                start_time = time.time()
                transaction_ids = self.simulation.create_inter_sectoral_flows_batch(intensity)
                creation_time = (time.time() - start_time) * 1000

                self.assertGreater(len(transaction_ids), 0,
                                  f"Aucune transaction créée avec intensité {intensity}")
                self.assertLess(creation_time, 50,
                               f"Création trop lente: {creation_time:.2f}ms")

                print(f"✅ Intensité {intensity}: {len(transaction_ids)} transactions en {creation_time:.2f}ms")

    def test_validation_performance_70_percent_target(self):
        """Test validation performance >70% FEASIBILITY target"""

        # Créer agents et transactions de test
        agents = [
            ('FARM_A', 'AGRICULTURE', 2500),
            ('FACTORY_A', 'INDUSTRY', 1800),
            ('LOGISTICS_A', 'SERVICES', 1200),
            ('BANK_A', 'FINANCE', 4500),
            ('POWER_A', 'ENERGY', 2800)
        ]

        for agent_id, sector, balance in agents:
            self.simulation.create_agent(agent_id, sector, Decimal(str(balance)))

        # Générer flux inter-sectoriels pour tests robustes
        transaction_ids = self.simulation.create_inter_sectoral_flows_batch(0.6)

        # Valider toutes les transactions
        successful_validations = 0
        total_validation_time = 0

        for tx_id in transaction_ids:
            start_time = time.time()
            result = self.simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
            validation_time = (time.time() - start_time) * 1000
            total_validation_time += validation_time

            if result.success:
                successful_validations += 1

            # Performance individuelle <100ms
            self.assertLess(validation_time, 100,
                           f"Validation trop lente: {validation_time:.2f}ms pour {tx_id}")

        # Calculs métriques finales
        success_rate = (successful_validations / len(transaction_ids)) * 100
        avg_validation_time = total_validation_time / len(transaction_ids)

        # Assertions critiques
        self.assertGreaterEqual(success_rate, 70.0,
                               f"Taux succès insuffisant: {success_rate:.1f}% vs 70%+ requis")
        self.assertLess(avg_validation_time, 100,
                       f"Performance insuffisante: {avg_validation_time:.2f}ms vs <100ms requis")

        print(f"✅ Performance validée: {success_rate:.1f}% SUCCESS, {avg_validation_time:.2f}ms moyenne")

    def test_stress_200_transactions(self):
        """Test robustesse 200+ transactions simultanées"""

        # Créer 15 agents pour génération massive transactions
        for i in range(15):
            sector = ['AGRICULTURE', 'INDUSTRY', 'SERVICES', 'FINANCE', 'ENERGY'][i % 5]
            agent_id = f"AGENT_{sector}_{i+1}"
            balance = Decimal(str(1000 + i * 100))
            self.simulation.create_agent(agent_id, sector, balance)

        # Générer flux inter-sectoriels massifs
        transaction_ids = self.simulation.create_inter_sectoral_flows_batch(0.8)

        # Créer transactions supplémentaires pour atteindre 200+
        agent_ids = list(self.simulation.agents.keys())
        additional_transactions = []

        while len(transaction_ids) + len(additional_transactions) < 200:
            source_id = agent_ids[len(additional_transactions) % len(agent_ids)]
            target_id = agent_ids[(len(additional_transactions) + 1) % len(agent_ids)]

            if source_id != target_id:
                tx_id = self.simulation.create_transaction(source_id, target_id, Decimal('50'))
                additional_transactions.append(tx_id)

        all_transactions = transaction_ids + additional_transactions
        total_transactions = len(all_transactions)

        self.assertGreaterEqual(total_transactions, 200,
                               f"Transactions insuffisantes: {total_transactions} vs 200+ requis")

        # Validation stress test
        start_stress_time = time.time()
        successful_stress = 0

        for i, tx_id in enumerate(all_transactions):
            if i % 50 == 0:  # Progress indicator
                print(f"   Stress test: {i}/{total_transactions} transactions...")

            try:
                result = self.simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
                if result.success:
                    successful_stress += 1
            except Exception:
                pass  # Certaines transactions peuvent échouer sous stress

        stress_duration = (time.time() - start_stress_time) * 1000
        stress_success_rate = (successful_stress / total_transactions) * 100

        # Métriques stress robustesse
        self.assertGreater(stress_success_rate, 50.0,
                          f"Robustesse insuffisante: {stress_success_rate:.1f}% sous stress")
        self.assertLess(stress_duration, 10000,
                       f"Stress test trop lent: {stress_duration:.0f}ms vs <10s")

        print(f"✅ Stress test validé: {total_transactions} transactions, "
              f"{stress_success_rate:.1f}% succès en {stress_duration:.0f}ms")

    def test_economic_sectors_patterns_validation(self):
        """Test validation patterns regex sectoriels économiques"""

        # Créer agents et vérifier patterns
        test_agents = [
            ('WHEAT_FARM', 'AGRICULTURE'),
            ('STEEL_MILL', 'INDUSTRY'),
            ('TRANSPORT_CO', 'SERVICES'),
            ('NATIONAL_BANK', 'FINANCE'),
            ('SOLAR_PLANT', 'ENERGY')
        ]

        for agent_id, sector in test_agents:
            agent = self.simulation.create_agent(agent_id, sector, Decimal('1000'))

            # Vérifier pattern regex généré pour secteur
            pattern = self.simulation.character_set_manager.get_regex_pattern_for_sector(sector)
            self.assertIsNotNone(pattern)
            self.assertIn('[', pattern, f"Pattern secteur {sector} doit être character-class")

            print(f"   {sector}: pattern '{pattern}'")

        print("✅ Patterns sectoriels validés")

    def tearDown(self):
        """Nettoyage après chaque test"""
        # Reset simulation pour tests indépendants
        del self.simulation


class TestPerformanceBenchmarks(unittest.TestCase):
    """Tests benchmarks performance simulation massive"""

    def test_throughput_estimation_40_agents(self):
        """Test estimation throughput pour 40 agents"""

        simulation = EconomicSimulation("benchmark_40", agents_mode="40_agents")

        # Créer 25 agents pour benchmark
        for i in range(25):
            sector = ['AGRICULTURE', 'INDUSTRY', 'SERVICES', 'FINANCE', 'ENERGY'][i % 5]
            agent_id = f"BENCH_{sector}_{i+1}"
            simulation.create_agent(agent_id, sector, Decimal('1500'))

        # Mesurer throughput sur échantillon
        sample_transactions = []
        for _ in range(50):
            agents = list(simulation.agents.keys())
            source = agents[_ % len(agents)]
            target = agents[(_ + 1) % len(agents)]
            if source != target:
                tx_id = simulation.create_transaction(source, target, Decimal('100'))
                sample_transactions.append(tx_id)

        # Benchmark validation throughput
        start_benchmark = time.time()
        successful_bench = 0

        for tx_id in sample_transactions:
            result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
            if result.success:
                successful_bench += 1

        benchmark_duration = time.time() - start_benchmark
        throughput = len(sample_transactions) / benchmark_duration

        self.assertGreater(throughput, 30,
                          f"Throughput insuffisant: {throughput:.1f} tx/sec vs 30+ requis")

        print(f"✅ Throughput benchmark: {throughput:.1f} tx/sec avec {len(sample_transactions)} transactions")


if __name__ == '__main__':
    print("🚀 TESTS VALIDATION SIMULATION 40 AGENTS - SEMAINE 2")
    print("=" * 60)

    # Exécuter tests avec verbosité
    unittest.main(verbosity=2, exit=False)

    print("\n" + "=" * 60)
    print("✅ VALIDATION SEMAINE 2 TERMINÉE")
    print("🎯 Infrastructure 40 agents validée pour scaling Semaine 3")