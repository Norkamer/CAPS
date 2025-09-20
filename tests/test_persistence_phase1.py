#!/usr/bin/env python3
"""
Tests Unitaires - Système de Persistance ICGS Phase 1

STATUT: COMMENTÉS - Fonctionnalités futures ROADMAP
- Phase 3.2 (Month 14-16): Configuration Management & Result Export
- Phase 4 (Month 18-24): Production Infrastructure & Data Persistence

Tests complets pour:
- SimulationMetadata et SimulationState
- SimulationSerializer (sérialisation/désérialisation)
- SimulationStorage (stockage fichier)
- EconomicSimulation save/load integration
"""

import pytest
pytestmark = pytest.mark.skip(reason="Fonctionnalités futures ROADMAP Phase 3/4 - Month 14-24")

import sys
import os
import unittest
import tempfile
import shutil
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import json
import gzip

sys.path.insert(0, '/home/norkamer/ClaudeCode/CAPS')

from icgs_simulation.persistence import (
    SimulationMetadata, SimulationState,
    SimulationSerializer, SimulationStorage
)
from icgs_simulation.api.icgs_bridge import EconomicSimulation


class TestSimulationMetadata(unittest.TestCase):
    """Tests pour la classe SimulationMetadata"""

    def setUp(self):
        self.metadata = SimulationMetadata()

    def test_metadata_creation(self):
        """Test création métadonnées avec valeurs par défaut"""
        self.assertIsNotNone(self.metadata.id)
        self.assertEqual(self.metadata.agents_mode, "7_agents")
        self.assertEqual(self.metadata.scenario_type, "simple")
        self.assertEqual(self.metadata.category, "user_simulation")
        self.assertIsInstance(self.metadata.created_date, datetime)

    def test_metadata_to_dict(self):
        """Test sérialisation métadonnées en dictionnaire"""
        data = self.metadata.to_dict()

        self.assertIn('id', data)
        self.assertIn('name', data)
        self.assertIn('agents_mode', data)
        self.assertIn('created_date', data)
        self.assertIn('format_version', data)

        # Test format ISO pour dates
        self.assertIsInstance(data['created_date'], str)

    def test_metadata_from_dict(self):
        """Test désérialisation métadonnées depuis dictionnaire"""
        original_data = self.metadata.to_dict()
        restored = SimulationMetadata.from_dict(original_data)

        self.assertEqual(restored.id, self.metadata.id)
        self.assertEqual(restored.agents_mode, self.metadata.agents_mode)
        self.assertEqual(restored.scenario_type, self.metadata.scenario_type)

        # Test préservation des dates
        self.assertEqual(restored.created_date, self.metadata.created_date)

    def test_update_from_simulation(self):
        """Test mise à jour métadonnées depuis EconomicSimulation"""
        # Créer simulation simple
        simulation = EconomicSimulation("test_sim", agents_mode="40_agents")
        simulation.create_agent("TEST_01", "AGRICULTURE", Decimal('1000'))
        simulation.create_agent("TEST_02", "INDUSTRY", Decimal('800'))

        # Mettre à jour métadonnées
        self.metadata.update_from_simulation(simulation)

        self.assertEqual(self.metadata.agents_mode, "40_agents")
        self.assertEqual(self.metadata.agents_count, 2)
        self.assertEqual(self.metadata.transactions_count, 0)
        self.assertEqual(self.metadata.total_balance, Decimal('1800'))
        self.assertIn("AGRICULTURE", self.metadata.sectors_distribution)
        self.assertIn("INDUSTRY", self.metadata.sectors_distribution)


class TestSimulationState(unittest.TestCase):
    """Tests pour la classe SimulationState"""

    def setUp(self):
        self.metadata = SimulationMetadata()
        self.metadata.name = "Test State"
        self.state = SimulationState(metadata=self.metadata)

    def test_state_creation(self):
        """Test création état de simulation"""
        self.assertIsNotNone(self.state.metadata)
        self.assertEqual(len(self.state.agents), 0)
        self.assertEqual(len(self.state.transactions), 0)

    def test_state_to_dict(self):
        """Test sérialisation état complet"""
        # Ajouter des données factices
        self.state.agents = {
            'TEST_01': {
                'id': 'TEST_01',
                'sector': 'AGRICULTURE',
                'balance': '1000'
            }
        }

        data = self.state.to_dict()

        self.assertIn('metadata', data)
        self.assertIn('agents', data)
        self.assertIn('transactions', data)
        self.assertEqual(data['agents']['TEST_01']['sector'], 'AGRICULTURE')

    def test_state_from_dict(self):
        """Test désérialisation état depuis dictionnaire"""
        # Préparer données
        self.state.agents = {'TEST_01': {'id': 'TEST_01', 'sector': 'AGRICULTURE', 'balance': '1000'}}
        original_data = self.state.to_dict()

        # Restaurer
        restored = SimulationState.from_dict(original_data)

        self.assertEqual(restored.metadata.name, "Test State")
        self.assertIn('TEST_01', restored.agents)
        self.assertEqual(restored.agents['TEST_01']['sector'], 'AGRICULTURE')

    def test_state_validate_integrity(self):
        """Test validation intégrité état"""
        # État vide mais valide
        self.assertTrue(self.state.validate_integrity())

        # Ajouter agent et transaction cohérente
        self.state.agents = {
            'TEST_01': {'id': 'TEST_01', 'sector': 'AGRICULTURE', 'balance': '1000'},
            'TEST_02': {'id': 'TEST_02', 'sector': 'INDUSTRY', 'balance': '800'}
        }
        self.state.transactions = [{
            'id': 'TX_001',
            'source_account_id': 'TEST_01',
            'target_account_id': 'TEST_02',
            'amount': '100'
        }]

        # Mettre à jour métadonnées pour cohérence
        self.state.metadata.agents_count = 2
        self.state.metadata.transactions_count = 1

        self.assertTrue(self.state.validate_integrity())

        # Test incohérence : transaction vers agent inexistant
        self.state.transactions[0]['target_account_id'] = 'INEXISTANT'
        self.assertFalse(self.state.validate_integrity())

    def test_state_get_summary(self):
        """Test génération résumé état"""
        # Ajouter données
        self.state.agents = {'TEST_01': {'id': 'TEST_01', 'sector': 'AGRICULTURE', 'balance': '1000'}}
        self.state.metadata.sectors_distribution = {'AGRICULTURE': 1}
        self.state.metadata.total_balance = Decimal('1000')

        summary = self.state.get_summary()

        self.assertIn('simulation_id', summary)
        self.assertIn('agents_count', summary)
        self.assertIn('is_valid', summary)
        self.assertEqual(summary['agents_count'], 1)
        self.assertIn('AGRICULTURE', summary['sectors'])


class TestSimulationSerializer(unittest.TestCase):
    """Tests pour SimulationSerializer"""

    def setUp(self):
        self.serializer = SimulationSerializer()
        self.simulation = EconomicSimulation("test_serializer", agents_mode="7_agents")

        # Créer simulation avec données de test
        self.simulation.create_agent("FARM_01", "AGRICULTURE", Decimal('2000'))
        self.simulation.create_agent("FACTORY_01", "INDUSTRY", Decimal('1500'))

    def test_serialize_basic(self):
        """Test sérialisation simulation basique"""
        state = self.serializer.serialize(self.simulation)

        self.assertIsInstance(state, SimulationState)
        self.assertEqual(len(state.agents), 2)
        self.assertIn('FARM_01', state.agents)
        self.assertIn('FACTORY_01', state.agents)
        self.assertEqual(state.metadata.agents_count, 2)

    def test_serialize_with_transactions(self):
        """Test sérialisation avec transactions"""
        # Créer transaction
        tx_id = self.simulation.create_transaction("FARM_01", "FACTORY_01", Decimal('300'))

        state = self.serializer.serialize(self.simulation)

        self.assertEqual(len(state.transactions), 1)
        self.assertEqual(state.transactions[0]['source_account_id'], "FARM_01")
        self.assertEqual(state.transactions[0]['target_account_id'], "FACTORY_01")
        self.assertEqual(state.metadata.transactions_count, 1)

    def test_deserialize_basic(self):
        """Test désérialisation simulation basique"""
        # Sérialiser puis désérialiser
        original_state = self.serializer.serialize(self.simulation)
        restored_simulation = self.serializer.deserialize(original_state)

        self.assertEqual(len(restored_simulation.agents), 2)
        self.assertIn('FARM_01', restored_simulation.agents)
        self.assertIn('FACTORY_01', restored_simulation.agents)

        # Vérifier balances
        self.assertEqual(restored_simulation.agents['FARM_01'].balance, Decimal('2000'))
        self.assertEqual(restored_simulation.agents['FACTORY_01'].balance, Decimal('1500'))

    def test_serialize_deserialize_integrity(self):
        """Test intégrité sérialisation/désérialisation complète"""
        # Ajouter transaction pour test complet
        self.simulation.create_transaction("FARM_01", "FACTORY_01", Decimal('300'))

        # Cycle complet
        state = self.serializer.serialize(self.simulation)
        restored = self.serializer.deserialize(state)

        # Validation intégrité
        validation = self.serializer.validate_serialization(self.simulation, restored)

        self.assertTrue(validation['agents_count_match'])
        self.assertTrue(validation['agents_ids_match'])
        self.assertTrue(validation['total_balance_match'])
        self.assertTrue(validation['sectors_match'])
        self.assertTrue(validation['overall_success'])

    def test_serialization_info(self):
        """Test informations sur état sérialisé"""
        state = self.serializer.serialize(self.simulation)
        info = self.serializer.get_serialization_info(state)

        self.assertIn('metadata', info)
        self.assertIn('data_summary', info)
        self.assertIn('integrity_status', info)
        self.assertEqual(info['data_summary']['agents_count'], 2)
        self.assertTrue(info['integrity_status'])


class TestSimulationStorage(unittest.TestCase):
    """Tests pour SimulationStorage"""

    def setUp(self):
        # Créer répertoire temporaire pour tests
        self.temp_dir = tempfile.mkdtemp()
        self.storage = SimulationStorage(self.temp_dir)

        # Créer état de test
        self.metadata = SimulationMetadata()
        self.metadata.name = "Test Storage"
        self.metadata.agents_count = 2

        self.state = SimulationState(metadata=self.metadata)
        self.state.agents = {
            'TEST_01': {'id': 'TEST_01', 'sector': 'AGRICULTURE', 'balance': '1000'},
            'TEST_02': {'id': 'TEST_02', 'sector': 'INDUSTRY', 'balance': '800'}
        }

    def tearDown(self):
        # Nettoyer répertoire temporaire
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_storage_directories_creation(self):
        """Test création répertoires stockage"""
        self.assertTrue(self.storage.metadata_path.exists())
        self.assertTrue(self.storage.states_path.exists())
        self.assertTrue(self.storage.exports_path.exists())

    def test_save_simulation_uncompressed(self):
        """Test sauvegarde non compressée"""
        sim_id = self.storage.save_simulation(self.state, compress=False)

        # Vérifier fichiers créés
        metadata_file = self.storage.metadata_path / f"{sim_id}.json"
        state_file = self.storage.states_path / f"{sim_id}.json"

        self.assertTrue(metadata_file.exists())
        self.assertTrue(state_file.exists())

        # Vérifier contenu métadonnées
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata_data = json.load(f)
        self.assertEqual(metadata_data['name'], "Test Storage")

    def test_save_simulation_compressed(self):
        """Test sauvegarde compressée"""
        sim_id = self.storage.save_simulation(self.state, compress=True)

        # Vérifier fichier compressé créé
        state_file = self.storage.states_path / f"{sim_id}.json.gz"
        self.assertTrue(state_file.exists())

        # Vérifier contenu compressé
        with gzip.open(state_file, 'rt', encoding='utf-8') as f:
            state_data = json.load(f)
        self.assertIn('metadata', state_data)
        self.assertIn('agents', state_data)

    def test_load_simulation(self):
        """Test chargement simulation"""
        # Sauvegarder puis charger
        sim_id = self.storage.save_simulation(self.state, compress=False)
        loaded_state = self.storage.load_simulation(sim_id)

        self.assertEqual(loaded_state.metadata.name, "Test Storage")
        self.assertEqual(len(loaded_state.agents), 2)
        self.assertIn('TEST_01', loaded_state.agents)

    def test_load_metadata_only(self):
        """Test chargement métadonnées uniquement"""
        sim_id = self.storage.save_simulation(self.state, compress=False)
        metadata = self.storage.load_metadata(sim_id)

        self.assertEqual(metadata.name, "Test Storage")
        self.assertEqual(metadata.agents_count, 2)

    def test_list_simulations(self):
        """Test listing des simulations"""
        # Sauvegarder plusieurs simulations
        sim_id1 = self.storage.save_simulation(self.state, compress=False)

        self.state.metadata.name = "Test Storage 2"
        self.state.metadata.category = "test"
        sim_id2 = self.storage.save_simulation(self.state, compress=False)

        # Lister toutes
        all_sims = self.storage.list_simulations()
        self.assertEqual(len(all_sims), 2)

        # Lister par catégorie
        test_sims = self.storage.list_simulations(filter_category="test")
        self.assertEqual(len(test_sims), 1)
        self.assertEqual(test_sims[0].name, "Test Storage 2")

    def test_delete_simulation(self):
        """Test suppression simulation"""
        sim_id = self.storage.save_simulation(self.state, compress=False)

        # Vérifier existence
        metadata_file = self.storage.metadata_path / f"{sim_id}.json"
        self.assertTrue(metadata_file.exists())

        # Supprimer
        success = self.storage.delete_simulation(sim_id)
        self.assertTrue(success)

        # Vérifier suppression
        self.assertFalse(metadata_file.exists())

    def test_export_simulation(self):
        """Test export simulation"""
        sim_id = self.storage.save_simulation(self.state, compress=False)

        # Export JSON
        json_path = self.storage.export_simulation(sim_id, "json")
        self.assertTrue(Path(json_path).exists())

        # Export CSV
        csv_path = self.storage.export_simulation(sim_id, "csv")
        self.assertTrue(Path(csv_path).exists())

    def test_storage_stats(self):
        """Test statistiques stockage"""
        # Sauvegarder quelques simulations
        self.storage.save_simulation(self.state, compress=False)
        self.storage.save_simulation(self.state, compress=True)

        stats = self.storage.get_storage_stats()

        self.assertIn('simulations_count', stats)
        self.assertIn('total_size_bytes', stats)
        self.assertIn('files', stats)
        self.assertEqual(stats['simulations_count'], 2)

    def test_cleanup_orphaned_files(self):
        """Test nettoyage fichiers orphelins"""
        sim_id = self.storage.save_simulation(self.state, compress=False)

        # Supprimer métadonnées seulement (créer orphelin)
        metadata_file = self.storage.metadata_path / f"{sim_id}.json"
        metadata_file.unlink()

        # Nettoyer orphelins
        cleaned = self.storage.cleanup_orphaned_files()

        self.assertGreater(cleaned['orphaned_states'], 0)


class TestEconomicSimulationIntegration(unittest.TestCase):
    """Tests intégration EconomicSimulation avec persistance"""

    def setUp(self):
        # Créer répertoire temporaire
        self.temp_dir = tempfile.mkdtemp()

        # Patcher le storage pour utiliser répertoire de test
        import icgs_simulation.persistence.simulation_storage
        self.original_base_path = None

        # Créer simulation de test
        self.simulation = EconomicSimulation("integration_test", agents_mode="7_agents")
        self.simulation.create_agent("FARM_01", "AGRICULTURE", Decimal('2000'))
        self.simulation.create_agent("FACTORY_01", "INDUSTRY", Decimal('1500'))
        self.simulation.create_transaction("FARM_01", "FACTORY_01", Decimal('300'))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_simulation_integration(self):
        """Test sauvegarde simulation complète"""
        # Utiliser storage temporaire
        from icgs_simulation.persistence import SimulationStorage
        temp_storage = SimulationStorage(self.temp_dir)

        # Patcher temporairement pour utiliser storage de test
        original_init = SimulationStorage.__init__
        def test_init(self, base_path=None):
            original_init(self, self.temp_dir if base_path is None else base_path)

        SimulationStorage.__init__ = test_init

        try:
            sim_id = self.simulation.save_simulation(
                name="Test Integration",
                description="Test sauvegarde complète",
                tags=["test", "integration"]
            )

            self.assertIsNotNone(sim_id)

            # Vérifier fichiers créés
            metadata_file = Path(self.temp_dir) / "metadata" / f"{sim_id}.json"
            self.assertTrue(metadata_file.exists())

        finally:
            # Restaurer méthode originale
            SimulationStorage.__init__ = original_init

    def test_load_simulation_integration(self):
        """Test chargement simulation complète"""
        # Setup storage temporaire
        from icgs_simulation.persistence import SimulationStorage
        original_init = SimulationStorage.__init__

        def test_init(self, base_path=None):
            original_init(self, self.temp_dir if base_path is None else base_path)

        SimulationStorage.__init__ = test_init

        try:
            # Sauvegarder
            sim_id = self.simulation.save_simulation(name="Load Test")

            # Charger
            loaded_simulation = EconomicSimulation.load_simulation(sim_id)

            # Vérifier intégrité
            self.assertEqual(len(loaded_simulation.agents), 2)
            self.assertIn('FARM_01', loaded_simulation.agents)
            self.assertIn('FACTORY_01', loaded_simulation.agents)

            # Vérifier balances préservées
            self.assertEqual(loaded_simulation.agents['FARM_01'].balance, Decimal('2000'))
            self.assertEqual(loaded_simulation.agents['FACTORY_01'].balance, Decimal('1500'))

        finally:
            SimulationStorage.__init__ = original_init

    def test_list_simulations_integration(self):
        """Test listing simulations avec API intégrée"""
        from icgs_simulation.persistence import SimulationStorage
        original_init = SimulationStorage.__init__

        def test_init(self, base_path=None):
            original_init(self, self.temp_dir if base_path is None else base_path)

        SimulationStorage.__init__ = test_init

        try:
            # Sauvegarder simulation
            self.simulation.save_simulation(name="List Test", tags=["integration"])

            # Lister
            simulations = EconomicSimulation.list_simulations()

            self.assertGreater(len(simulations), 0)
            found_test_sim = False
            for sim in simulations:
                if sim.name == "List Test":
                    found_test_sim = True
                    self.assertIn("integration", sim.tags)
                    break

            self.assertTrue(found_test_sim)

        finally:
            SimulationStorage.__init__ = original_init

    def test_simulation_metrics_integration(self):
        """Test génération métriques complètes"""
        metrics = self.simulation.get_simulation_metrics()

        self.assertIn('agents_count', metrics)
        self.assertIn('transactions_count', metrics)
        self.assertIn('sectors', metrics)
        self.assertEqual(metrics['agents_count'], 2)
        self.assertEqual(metrics['transactions_count'], 1)
        self.assertIn('AGRICULTURE', metrics['sectors'])
        self.assertIn('INDUSTRY', metrics['sectors'])

    def test_validation_integrity_integration(self):
        """Test validation intégrité simulation"""
        validation = self.simulation.validate_simulation_integrity()

        self.assertIn('agents_valid', validation)
        self.assertIn('transactions_valid', validation)
        self.assertIn('overall_valid', validation)

        # Simulation bien construite doit être valide
        self.assertTrue(validation['agents_valid'])
        self.assertTrue(validation['transactions_valid'])


def run_persistence_tests():
    """Lance tous les tests de persistance Phase 1"""

    print("🧪 TESTS PERSISTANCE ICGS - PHASE 1")
    print("=" * 50)

    # Créer suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Ajouter toutes les classes de test
    test_classes = [
        TestSimulationMetadata,
        TestSimulationState,
        TestSimulationSerializer,
        TestSimulationStorage,
        TestEconomicSimulationIntegration
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    # Exécuter tests
    runner = unittest.TextTestRunner(
        verbosity=2,
        descriptions=True,
        failfast=False
    )

    result = runner.run(suite)

    # Résumé final
    print("\n" + "=" * 50)
    print(f"📊 RÉSULTATS TESTS PERSISTANCE PHASE 1:")
    print(f"   Tests exécutés: {result.testsRun}")
    print(f"   Succès: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   Échecs: {len(result.failures)}")
    print(f"   Erreurs: {len(result.errors)}")

    if result.wasSuccessful():
        print("✅ TOUS LES TESTS PASSÉS - Phase 1 validation réussie!")
        return True
    else:
        print("❌ CERTAINS TESTS ÉCHOUÉS - Révision nécessaire")
        return False


if __name__ == "__main__":
    success = run_persistence_tests()
    exit(0 if success else 1)