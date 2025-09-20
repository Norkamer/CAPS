#!/usr/bin/env python3
"""
Test Quick Win: Suppression Limite 3 Agents/Secteur
===================================================

Validation que la limite arbitraire AGENTS_PER_SECTOR = 3 a été supprimée
et que le système supporte maintenant agents illimités par secteur.
"""

import sys
import os
from decimal import Decimal
import unittest

# Add CAPS to path
sys.path.insert(0, '/home/norkamer/ClaudeCode/CAPS')

from icgs_simulation.api.icgs_bridge import EconomicSimulation, SimulationMode

class TestQuickWinAgentLimitRemoval(unittest.TestCase):
    """Tests validation suppression limite agents par secteur"""

    def setUp(self):
        """Setup simulation pour tests"""
        self.simulation = EconomicSimulation("agent_limit_test", agents_mode="7_agents")

    def test_single_sector_multiple_agents(self):
        """Test Case 1: Multiple agents dans un seul secteur (était impossible)"""
        print("\n🧪 Test 1: Multiple Agents Même Secteur")

        # Créer 5 agents AGRICULTURE (était limité à 1 agent avant)
        agents = []
        for i in range(1, 6):  # 5 agents
            agent = self.simulation.create_agent(f"FARM_{i:02d}", "AGRICULTURE", Decimal('1000'))
            agents.append(agent)

        self.assertEqual(len(agents), 5)

        # Vérifier tous dans même secteur
        for agent in agents:
            self.assertEqual(agent.sector, "AGRICULTURE")

        print(f"   ✅ 5 agents AGRICULTURE créés avec succès (vs 1 max avant)")

    def test_realistic_economic_distribution(self):
        """Test Case 2: Distribution économique réaliste"""
        print("\n🧪 Test 2: Distribution Économique Réaliste")

        # Distribution réaliste inspirée du plan 65 agents
        distribution = {
            'AGRICULTURE': 10,   # Était limité à 1
            'INDUSTRY': 15,      # Était limité à 2
            'SERVICES': 15,      # Était limité à 2 (on teste 15 pour rester dans limite pool)
            'FINANCE': 8,        # Était limité à 1
            'ENERGY': 12         # Était limité à 1
        }

        created_agents = {}
        total_agents = 0

        for sector, count in distribution.items():
            created_agents[sector] = []
            for i in range(1, count + 1):
                agent_name = f"{sector}_{i:02d}"
                balance = Decimal('1000') + Decimal(str(i * 10))

                agent = self.simulation.create_agent(agent_name, sector, balance)
                created_agents[sector].append(agent)
                total_agents += 1

        # Validation distribution
        for sector, expected_count in distribution.items():
            actual_count = len(created_agents[sector])
            self.assertEqual(actual_count, expected_count,
                           f"Secteur {sector}: {actual_count} agents créés != {expected_count} attendus")

        self.assertEqual(total_agents, sum(distribution.values()))
        print(f"   ✅ {total_agents} agents créés selon distribution réaliste")
        print(f"      AGRICULTURE: {len(created_agents['AGRICULTURE'])} agents")
        print(f"      INDUSTRY: {len(created_agents['INDUSTRY'])} agents")
        print(f"      SERVICES: {len(created_agents['SERVICES'])} agents")
        print(f"      FINANCE: {len(created_agents['FINANCE'])} agents")
        print(f"      ENERGY: {len(created_agents['ENERGY'])} agents")

    def test_character_allocation_scalability(self):
        """Test Case 3: Scalabilité allocation caractères"""
        print("\n🧪 Test 3: Scalabilité Allocation Caractères")

        # Test allocation progressive pour vérifier que Character-Set Manager
        # peut gérer allocation dynamique sans épuiser pool
        sector = "INDUSTRY"
        agents_created = []

        # Créer agents progressivement jusqu'à 12 (test conservative)
        for i in range(1, 13):
            agent_name = f"FACTORY_{i:02d}"
            agent = self.simulation.create_agent(agent_name, sector, Decimal('800'))
            agents_created.append(agent)

            # Vérifier que l'agent est correctement configuré
            self.assertEqual(agent.sector, sector)
            self.assertIsInstance(agent.balance, Decimal)

        self.assertEqual(len(agents_created), 12)
        print(f"   ✅ 12 agents {sector} créés avec allocation caractères dynamique")

    def test_cross_sector_scalability(self):
        """Test Case 4: Scalabilité cross-secteur"""
        print("\n🧪 Test 4: Scalabilité Cross-Secteur")

        # Créer agents répartis sur tous secteurs pour valider
        # que la suppression de limite fonctionne globalement
        agents_per_sector = 8  # Conservative test
        sectors = ["AGRICULTURE", "INDUSTRY", "SERVICES", "FINANCE", "ENERGY"]

        total_created = 0
        for sector in sectors:
            for i in range(1, agents_per_sector + 1):
                agent_name = f"{sector}_{i:02d}"
                agent = self.simulation.create_agent(agent_name, sector, Decimal('1000'))
                total_created += 1

        expected_total = len(sectors) * agents_per_sector
        self.assertEqual(total_created, expected_total)

        print(f"   ✅ {total_created} agents créés cross-secteur ({agents_per_sector} par secteur)")

    def test_transaction_creation_with_many_agents(self):
        """Test Case 5: Création transactions avec nombreux agents"""
        print("\n🧪 Test 5: Transaction Creation Avec Nombreux Agents")

        # Créer plusieurs agents par secteur et valider transactions
        for sector in ["AGRICULTURE", "INDUSTRY"]:
            for i in range(1, 4):  # 3 agents par secteur
                agent_name = f"{sector}_{i:02d}"
                agent = self.simulation.create_agent(agent_name, sector, Decimal('1200'))

        # Test batch flows avec plus d'agents
        tx_ids = self.simulation.create_inter_sectoral_flows_batch(flow_intensity=0.3)

        # Doit réussir sans erreur (plus de combinations possibles)
        self.assertGreater(len(tx_ids), 0)

        # Test validation d'une transaction
        if tx_ids:
            result = self.simulation.validate_transaction(tx_ids[0], SimulationMode.FEASIBILITY)
            self.assertTrue(result.success)

        print(f"   ✅ {len(tx_ids)} transactions créées et validées avec nombreux agents")

    def test_capacity_statistics(self):
        """Test Case 6: Statistiques capacité système"""
        print("\n🧪 Test 6: Statistiques Capacité Système")

        # Vérifier que les nouvelles capacités sont correctement reportées
        stats = self.simulation.character_set_manager.get_allocation_statistics()

        # Chaque secteur doit avoir capacité > 3 caractères maintenant
        for sector, info in stats['sectors'].items():
            max_capacity = info['max_capacity']
            agents_capacity = max_capacity // 3  # 3 chars par agent

            self.assertGreater(agents_capacity, 1,
                             f"Secteur {sector}: capacité {agents_capacity} agents <= 1 (limite pas supprimée)")

            print(f"      {sector}: {max_capacity} chars = {agents_capacity} agents max")

        # Capacité totale doit être > 21 caractères (ancienne limite)
        total_capacity = sum(info['max_capacity'] for info in stats['sectors'].values())
        self.assertGreater(total_capacity, 21)

        total_agents_capacity = total_capacity // 3
        print(f"   ✅ Capacité totale: {total_capacity} chars = {total_agents_capacity} agents (vs 7 avant)")

def run_agent_limit_removal_tests():
    """Execute tous les tests suppression limite agents"""
    print("🚀 TESTS QUICK WIN: Suppression Limite Agents/Secteur")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestQuickWinAgentLimitRemoval)

    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ TESTS QUICK WIN")
    print(f"   Tests exécutés: {result.testsRun}")
    print(f"   Échecs: {len(result.failures)}")
    print(f"   Erreurs: {len(result.errors)}")

    if result.wasSuccessful():
        print("   ✅ QUICK WIN VALIDÉ - Limite agents/secteur supprimée avec succès")
        return True
    else:
        print("   ❌ ÉCHECS DÉTECTÉS - Quick Win nécessite révision")
        for failure in result.failures:
            print(f"      Échec: {failure[0]}")
        for error in result.errors:
            print(f"      Erreur: {error[0]}")
        return False

if __name__ == "__main__":
    success = run_agent_limit_removal_tests()
    exit(0 if success else 1)