#!/usr/bin/env python3
"""
Tests de Non-Régression - Option A : Contrôle Taxonomique Explicite

Suite complète validation que les modifications ICGS Core n'ont pas introduit
de régressions et que les nouvelles fonctionnalités fonctionnent correctement.

Tests couverts :
1. Rétrocompatibilité API existante
2. Nouvelle API taxonomie explicite
3. Performance et robustesse
4. Intégration WebNativeICGS
5. Edge cases et validation erreurs
"""

import unittest
import time
import sys
import os
from decimal import Decimal
from typing import Dict, List

# Setup path
sys.path.insert(0, os.path.dirname(__file__))

# ICGS Core imports
from icgs_core import DAG, Account
from icgs_core.dag import DAGConfiguration

# WebNativeICGS import
from icgs_web_native import WebNativeICGS

# EconomicSimulation import
from icgs_simulation import EconomicSimulation


class TestNonRegressionOptionA(unittest.TestCase):
    """Suite tests de non-régression Option A"""

    def setUp(self):
        """Setup pour chaque test"""
        self.start_time = time.time()

    def tearDown(self):
        """Cleanup après chaque test"""
        elapsed = (time.time() - self.start_time) * 1000
        print(f"  Test completed in {elapsed:.2f}ms")

    # ===== TESTS RÉTROCOMPATIBILITÉ =====

    def test_legacy_dag_add_account_compatibility(self):
        """Test 1: API legacy DAG.add_account() fonctionne toujours"""
        print("\n=== TEST 1: Rétrocompatibilité DAG.add_account ===")

        dag = DAG()

        # Utilisation API legacy (sans taxonomic_chars)
        account = Account(
            account_id="legacy_test_account",
            initial_balance=Decimal('500'),
            metadata={'test': 'legacy'}
        )

        # Ne doit PAS échouer - rétrocompatibilité
        try:
            success = dag.add_account(account)  # Ancien appel sans paramètre
            self.assertTrue(success, "Legacy add_account should work")

            # Vérifier compte ajouté
            self.assertIn("legacy_test_account", dag.accounts)
            self.assertEqual(dag.accounts["legacy_test_account"].account_id, "legacy_test_account")

            print("✅ Legacy API fonctionne")

        except Exception as e:
            self.fail(f"Legacy API should not fail: {e}")

    def test_legacy_economic_simulation_compatibility(self):
        """Test 2: EconomicSimulation legacy fonctionne toujours"""
        print("\n=== TEST 2: Rétrocompatibilité EconomicSimulation ===")

        # Test simulation classique sans modifications
        sim = EconomicSimulation("legacy_test")

        try:
            # Création agents classique
            alice = sim.create_agent("ALICE_LEGACY", "AGRICULTURE", Decimal('1000'))
            bob = sim.create_agent("BOB_LEGACY", "INDUSTRY", Decimal('1000'))

            self.assertIsNotNone(alice)
            self.assertIsNotNone(bob)
            self.assertEqual(len(sim.agents), 2)

            print("✅ EconomicSimulation legacy fonctionne")

        except Exception as e:
            self.fail(f"Legacy EconomicSimulation should not fail: {e}")

    # ===== TESTS NOUVELLE API OPTION A =====

    def test_explicit_taxonomic_chars_api(self):
        """Test 3: Nouvelle API taxonomie explicite fonctionne"""
        print("\n=== TEST 3: API Taxonomie Explicite ===")

        dag = DAG()

        # Test avec caractères taxonomiques explicites
        account = Account(
            account_id="explicit_test_account",
            initial_balance=Decimal('750'),
            metadata={'test': 'explicit'}
        )

        # Caractères taxonomiques explicites
        taxonomic_chars = {'source': 'X', 'sink': 'Y'}

        try:
            success = dag.add_account(account, taxonomic_chars=taxonomic_chars)
            self.assertTrue(success, "Explicit taxonomic API should work")

            # Vérifier compte ajouté
            self.assertIn("explicit_test_account", dag.accounts)

            # Vérifier configuration taxonomique réussie
            # (pas d'exception levée = configuration réussie)

            print("✅ API Taxonomie explicite fonctionne")

        except Exception as e:
            self.fail(f"Explicit taxonomic API should not fail: {e}")

    def test_taxonomic_collision_prevention(self):
        """Test 4: Prévention collisions taxonomiques"""
        print("\n=== TEST 4: Prévention Collisions Taxonomiques ===")

        dag = DAG()

        # Créer deux comptes avec caractères explicites différents
        account1 = Account("account1", Decimal('100'))
        account2 = Account("account2", Decimal('200'))

        # Caractères distincts - doit réussir
        success1 = dag.add_account(account1, taxonomic_chars={'source': 'A', 'sink': 'B'})
        success2 = dag.add_account(account2, taxonomic_chars={'source': 'C', 'sink': 'D'})

        self.assertTrue(success1, "First account should be added")
        self.assertTrue(success2, "Second account should be added")

        print("✅ Comptes multiples avec taxonomie explicite unique fonctionnent")

    def test_taxonomic_validation(self):
        """Test 5: Validation erreurs taxonomie explicite"""
        print("\n=== TEST 5: Validation Erreurs Taxonomie ===")

        dag = DAG()
        account = Account("validation_test", Decimal('100'))

        # Test caractères dupliqués - doit échouer
        with self.assertRaises(ValueError, msg="Duplicate chars should raise ValueError"):
            dag.add_account(account, taxonomic_chars={'source': 'X', 'sink': 'X'})

        # Test format invalide - doit échouer
        with self.assertRaises(ValueError, msg="Invalid format should raise ValueError"):
            dag.add_account(account, taxonomic_chars={'wrong_key': 'X'})

        print("✅ Validation taxonomique fonctionne correctement")

    # ===== TESTS INTÉGRATION WEBNATIVEICGS =====

    def test_webnative_icgs_integration(self):
        """Test 6: Intégration WebNativeICGS avec Option A"""
        print("\n=== TEST 6: Intégration WebNativeICGS ===")

        try:
            # Initialisation WebNativeICGS (utilise Option A en interne)
            manager = WebNativeICGS()

            # Vérifier slots créés avec taxonomie explicite
            capacities = manager.get_pool_capacities()
            self.assertGreater(sum(cap['total'] for cap in capacities.values()), 10, "Pool should have multiple slots")

            # Test ajout agents
            agent_info = manager.add_agent("TEST_FARM", "AGRICULTURE", Decimal('1000'))
            self.assertIsNotNone(agent_info)
            self.assertEqual(agent_info.real_id, "TEST_FARM")

            print(f"✅ WebNativeICGS intégration fonctionne - {len(capacities)} secteurs")

        except Exception as e:
            self.fail(f"WebNativeICGS integration should not fail: {e}")

    def test_demo_simulation_functionality(self):
        """Test 7: Fonctionnalité simulation demo"""
        print("\n=== TEST 7: Fonctionnalité Simulation Demo ===")

        try:
            manager = WebNativeICGS()

            # Créer agents demo
            manager.add_agent("DEMO_ALICE", "AGRICULTURE", Decimal('1000'))
            manager.add_agent("DEMO_BOB", "INDUSTRY", Decimal('1000'))

            # Test transaction (ne devrait pas échouer avec collision taxonomique)
            result = manager.process_transaction("DEMO_ALICE", "DEMO_BOB", Decimal('100'))

            # Transaction peut échouer pour validation business, mais PAS pour collision taxonomique
            self.assertIsInstance(result, dict, "Transaction should return dict result")
            self.assertIn('success', result, "Result should have success field")

            # Si échec, vérifier que ce n'est PAS pour collision taxonomique
            if not result['success']:
                error_msg = result.get('error', '').lower()
                self.assertNotIn('collision', error_msg, "Should not fail due to taxonomic collision")
                self.assertNotIn('character', error_msg, "Should not fail due to character issues")

            print(f"✅ Demo simulation fonctionne - résultat: {result.get('success', 'unknown')}")

        except Exception as e:
            self.fail(f"Demo simulation should not fail with taxonomic errors: {e}")

    # ===== TESTS PERFORMANCE =====

    def test_performance_no_regression(self):
        """Test 8: Performance - pas de régression majeure"""
        print("\n=== TEST 8: Performance Non-Régression ===")

        # Test performance création multiple comptes
        dag = DAG()

        # Mesurer temps création legacy
        start_legacy = time.time()
        for i in range(10):
            account = Account(f"legacy_perf_{i}", Decimal('100'))
            dag.add_account(account)  # Legacy API
        legacy_time = time.time() - start_legacy

        # Mesurer temps création avec taxonomie explicite
        dag2 = DAG()
        start_explicit = time.time()
        for i in range(10):
            account = Account(f"explicit_perf_{i}", Decimal('100'))
            # Générer caractères uniques
            source_char = chr(ord('a') + (i * 2))
            sink_char = chr(ord('A') + (i * 2))
            dag2.add_account(account, taxonomic_chars={'source': source_char, 'sink': sink_char})
        explicit_time = time.time() - start_explicit

        # Vérifier overhead acceptable (<100% regression) - réaliste pour nouvelle fonctionnalité
        overhead_ratio = explicit_time / legacy_time if legacy_time > 0 else 1
        self.assertLess(overhead_ratio, 2.0, f"Performance overhead should be <100%, got {overhead_ratio:.2f}")

        print(f"✅ Performance - Legacy: {legacy_time*1000:.2f}ms, Explicit: {explicit_time*1000:.2f}ms")
        print(f"   Overhead: {(overhead_ratio-1)*100:.1f}% (acceptable)")

    # ===== TESTS EDGE CASES =====

    def test_edge_case_empty_taxonomic_chars(self):
        """Test 9: Edge case - taxonomic_chars vide"""
        print("\n=== TEST 9: Edge Cases ===")

        dag = DAG()
        account = Account("edge_test", Decimal('100'))

        # Test dict vide - doit échouer
        with self.assertRaises(ValueError):
            dag.add_account(account, taxonomic_chars={})

        # Test None explicite - doit utiliser legacy mode
        try:
            success = dag.add_account(account, taxonomic_chars=None)
            self.assertTrue(success, "None taxonomic_chars should work (legacy mode)")
            print("✅ Edge cases handled correctly")
        except Exception as e:
            self.fail(f"None taxonomic_chars should work: {e}")

    def test_stress_multiple_sectors(self):
        """Test 10: Stress test - multiples secteurs sans collision"""
        print("\n=== TEST 10: Stress Test Multi-Secteurs ===")

        try:
            manager = WebNativeICGS()

            # Créer agents dans tous les secteurs disponibles
            sectors = ['AGRICULTURE', 'INDUSTRY', 'SERVICES', 'FINANCE', 'ENERGY']
            created_agents = []

            for i, sector in enumerate(sectors):
                for j in range(2):  # 2 agents par secteur
                    agent_id = f"STRESS_{sector}_{j}"
                    try:
                        agent_info = manager.add_agent(agent_id, sector, Decimal('1000'))
                        created_agents.append(agent_info)
                    except Exception as e:
                        # Capacité dépassée acceptable, collision taxonomique PAS acceptable
                        if 'complet' in str(e) or 'capacity' in str(e):
                            continue  # Capacité dépassée - acceptable
                        else:
                            self.fail(f"Unexpected error (not capacity): {e}")

            self.assertGreater(len(created_agents), 5, "Should create agents in multiple sectors")
            print(f"✅ Stress test réussi - {len(created_agents)} agents créés dans {len(sectors)} secteurs")

        except Exception as e:
            self.fail(f"Multi-sector stress test failed: {e}")


def run_non_regression_suite():
    """Exécuter suite complète tests de non-régression"""
    print("=" * 80)
    print("SUITE TESTS DE NON-RÉGRESSION - OPTION A")
    print("Validation modifications ICGS Core taxonomie explicite")
    print("=" * 80)

    # Configuration unittest
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNonRegressionOptionA)
    runner = unittest.TextTestRunner(verbosity=2)

    # Exécution
    start_time = time.time()
    result = runner.run(suite)
    total_time = time.time() - start_time

    # Rapport final
    print("\n" + "=" * 80)
    print("RAPPORT FINAL NON-RÉGRESSION")
    print("=" * 80)
    print(f"Tests exécutés: {result.testsRun}")
    print(f"Succès: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Échecs: {len(result.failures)}")
    print(f"Erreurs: {len(result.errors)}")
    print(f"Temps total: {total_time:.2f}s")

    if result.failures:
        print("\nÉCHECS:")
        for test, trace in result.failures:
            print(f"  - {test}: {trace}")

    if result.errors:
        print("\nERREURS:")
        for test, trace in result.errors:
            print(f"  - {test}: {trace}")

    success = len(result.failures) == 0 and len(result.errors) == 0
    status = "✅ SUCCÈS - Aucune régression détectée" if success else "❌ ÉCHEC - Régressions détectées"
    print(f"\nRÉSULTAT: {status}")

    return success


if __name__ == '__main__':
    success = run_non_regression_suite()
    sys.exit(0 if success else 1)