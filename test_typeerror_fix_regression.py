#!/usr/bin/env python3
"""
Tests de Non-Régression: Fix TypeError Transaction Creation
============================================================

Suite de tests comprehensive pour valider le fix du TypeError
et s'assurer qu'aucune régression n'est introduite.
"""

import sys
import os
from decimal import Decimal
import unittest

# Add CAPS to path
sys.path.insert(0, '/home/norkamer/ClaudeCode/CAPS')

from icgs_simulation.api.icgs_bridge import EconomicSimulation, SimulationMode

class TestTypeErrorFixRegression(unittest.TestCase):
    """Tests de non-régression pour fix TypeError float * Decimal"""

    def setUp(self):
        """Setup commun pour tous les tests"""
        self.simulation = EconomicSimulation("regression_test", agents_mode="7_agents")

    def test_float_balance_input(self):
        """Test Case 1: Float Balance Input (reproduisait le bug)"""
        print("\n🧪 Test 1: Float Balance Input")

        # Créer agents avec balance float (source du bug original)
        agent1 = self.simulation.create_agent("FARM_01", "AGRICULTURE", 1000.0)
        agent2 = self.simulation.create_agent("FACTORY_01", "INDUSTRY", 800.0)

        # Vérifier conversion automatique vers Decimal
        self.assertIsInstance(agent1.balance, Decimal)
        self.assertIsInstance(agent2.balance, Decimal)
        self.assertEqual(agent1.balance, Decimal('1000.0'))
        self.assertEqual(agent2.balance, Decimal('800.0'))

        # Test batch flows (échouait avant le fix avec TypeError)
        tx_ids = self.simulation.create_inter_sectoral_flows_batch(flow_intensity=0.3)

        # Doit réussir maintenant (au moins une transaction AGRICULTURE → INDUSTRY)
        self.assertGreater(len(tx_ids), 0)
        print(f"   ✅ {len(tx_ids)} transactions créées avec succès")

    def test_decimal_balance_input(self):
        """Test Case 2: Decimal Balance Input (cas existant)"""
        print("\n🧪 Test 2: Decimal Balance Input")

        # Créer agent avec balance Decimal (cas existant)
        agent = self.simulation.create_agent("INDUSTRY_01", "INDUSTRY", Decimal('800'))

        # Vérifier préservation type Decimal
        self.assertIsInstance(agent.balance, Decimal)
        self.assertEqual(agent.balance, Decimal('800'))

        print("   ✅ Balance Decimal préservée correctement")

    def test_int_balance_input(self):
        """Test Case 3: Int Balance Input (nouveau cas supporté)"""
        print("\n🧪 Test 3: Int Balance Input")

        # Créer agent avec balance int
        agent = self.simulation.create_agent("SERVICES_01", "SERVICES", 600)

        # Vérifier conversion automatique vers Decimal
        self.assertIsInstance(agent.balance, Decimal)
        self.assertEqual(agent.balance, Decimal('600'))

        print("   ✅ Balance int convertie en Decimal")

    def test_mixed_type_inputs(self):
        """Test Case 4: Mixed Type Inputs (cas réel d'usage)"""
        print("\n🧪 Test 4: Mixed Type Inputs")

        # Créer agents avec types différents
        agent1 = self.simulation.create_agent("FINANCE_01", "FINANCE", 2000.0)    # float
        agent2 = self.simulation.create_agent("ENERGY_01", "ENERGY", Decimal('1500'))  # Decimal
        agent3 = self.simulation.create_agent("AGRICULTURE_02", "AGRICULTURE", 900)     # int

        # Vérifier tous convertis en Decimal
        self.assertIsInstance(agent1.balance, Decimal)
        self.assertIsInstance(agent2.balance, Decimal)
        self.assertIsInstance(agent3.balance, Decimal)

        # Test batch flows avec types mixtes
        tx_ids = self.simulation.create_inter_sectoral_flows_batch(flow_intensity=0.4)
        self.assertGreater(len(tx_ids), 0)

        print(f"   ✅ Types mixtes gérés - {len(tx_ids)} transactions créées")

    def test_transaction_validation_regression(self):
        """Test Case 5: Transaction Validation Regression"""
        print("\n🧪 Test 5: Transaction Validation Regression")

        # Setup agents
        alice = self.simulation.create_agent("ALICE_FARM", "AGRICULTURE", 1200.0)
        bob = self.simulation.create_agent("BOB_FACTORY", "INDUSTRY", 800.0)

        # Créer transaction manuelle
        tx_id = self.simulation.create_transaction(
            source_agent_id="ALICE_FARM",
            target_agent_id="BOB_FACTORY",
            amount=Decimal('300')
        )

        # Test validation FEASIBILITY
        result_feasibility = self.simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
        self.assertTrue(result_feasibility.success)

        # Test validation OPTIMIZATION
        result_optimization = self.simulation.validate_transaction(tx_id, SimulationMode.OPTIMIZATION)
        # Note: OPTIMIZATION peut échouer pour d'autres raisons, mais pas TypeError

        print("   ✅ Validations de transaction fonctionnelles")

    def test_scalability_regression(self):
        """Test Case 6: Scalability Regression (extended agents)"""
        print("\n🧪 Test 6: Scalability Regression")

        # Test avec plus d'agents (simuler extended scalability)
        sectors = ["AGRICULTURE", "INDUSTRY", "SERVICES", "FINANCE", "ENERGY"]

        for i in range(15):  # 15 agents - au-delà du test basique
            sector = sectors[i % len(sectors)]
            agent_name = f"{sector}_{i+1}"
            balance = 800.0 + (i * 10.0)  # float balance

            agent = self.simulation.create_agent(agent_name, sector, balance)
            self.assertIsInstance(agent.balance, Decimal)

        # Test batch flows avec 15 agents
        tx_ids = self.simulation.create_inter_sectoral_flows_batch(flow_intensity=0.25)
        self.assertGreater(len(tx_ids), 0)

        print(f"   ✅ 15 agents supportés - {len(tx_ids)} transactions")

    def test_edge_cases(self):
        """Test Case 7: Edge Cases"""
        print("\n🧪 Test 7: Edge Cases")

        # Test avec balance 0
        agent_zero = self.simulation.create_agent("ZERO_BALANCE", "SERVICES", 0.0)
        self.assertEqual(agent_zero.balance, Decimal('0'))

        # Test avec balance très petite
        agent_small = self.simulation.create_agent("SMALL_BALANCE", "FINANCE", 0.01)
        self.assertEqual(agent_small.balance, Decimal('0.01'))

        # Test avec balance grande
        agent_large = self.simulation.create_agent("LARGE_BALANCE", "ENERGY", 999999.99)
        self.assertEqual(agent_large.balance, Decimal('999999.99'))

        print("   ✅ Edge cases gérés correctement")

def run_regression_tests():
    """Exécute tous les tests de non-régression"""
    print("🔬 TESTS DE NON-RÉGRESSION: Fix TypeError Transaction Creation")
    print("=" * 70)

    # Configuration unittest
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestTypeErrorFixRegression)

    # Exécution avec rapport détaillé
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    # Résumé final
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ TESTS DE NON-RÉGRESSION")
    print(f"   Tests exécutés: {result.testsRun}")
    print(f"   Échecs: {len(result.failures)}")
    print(f"   Erreurs: {len(result.errors)}")

    if result.wasSuccessful():
        print("   ✅ TOUS LES TESTS PASSENT - Fix validé sans régression")
        return True
    else:
        print("   ❌ ÉCHECS DÉTECTÉS - Révision nécessaire")
        for failure in result.failures:
            print(f"      Échec: {failure[0]}")
        for error in result.errors:
            print(f"      Erreur: {error[0]}")
        return False

if __name__ == "__main__":
    success = run_regression_tests()
    exit(0 if success else 1)