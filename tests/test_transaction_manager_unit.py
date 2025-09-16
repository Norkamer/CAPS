"""
Test Unitaire TransactionManager - Validation Architecture Non-Invasive

Ce module teste exhaustivement la classe TransactionManager pour s'assurer
qu'elle respecte toutes les contraintes du refactoring :

1. NON-INVASIF : Aucune modification du système AccountTaxonomy core
2. API SIMPLIFIÉE : Gestion automatique transaction_num
3. BACKWARD COMPATIBILITY : API avancée accessible
4. INTÉGRITÉ : Données historiques strictement préservées
5. PERFORMANCE : Overhead négligeable vs système original

Niveau : Tests unitaires isolés (sans DAG)
"""

import pytest
import time
from decimal import Decimal
from typing import Dict, List

# Import du système à tester
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_core.transaction_manager import TransactionManager
from icgs_core.account_taxonomy import AccountTaxonomy


class TestTransactionManagerInitialization:
    """Tests d'initialisation et validation système core"""

    def test_transaction_manager_initialization(self):
        """Test initialisation TransactionManager avec AccountTaxonomy existant"""
        # Système core vide
        taxonomy = AccountTaxonomy()
        tm = TransactionManager(taxonomy)

        # Vérifications état initial
        assert tm._core_taxonomy is taxonomy, "Référence core taxonomy incorrecte"
        assert tm._auto_transaction_counter == 0, "Transaction counter initial incorrect"
        assert len(tm._frozen_snapshots) == 0, "Frozen snapshots initial incorrect"
        assert tm.get_current_transaction_num() == -1, "Current tx num initial incorrect"

    def test_initialization_with_existing_data(self):
        """Test initialisation avec données historiques existantes"""
        # Création données historiques
        taxonomy = AccountTaxonomy()
        historical_data = {"legacy_account_1": "L", "legacy_account_2": "M"}
        taxonomy.update_taxonomy(historical_data, 0)
        taxonomy.update_taxonomy({"newer_account": "N"}, 1)

        # Initialisation TransactionManager
        tm = TransactionManager(taxonomy)

        # Validation détection données existantes
        assert tm._auto_transaction_counter == 2, "Auto counter mal déterminé"
        assert len(tm._frozen_snapshots) == 2, "Frozen snapshots mal identifiés"
        assert tm.get_current_transaction_num() == 1, "Current tx incorrect avec données existantes"

    def test_core_system_integrity_validation(self):
        """Test validation intégrité système core lors initialisation"""
        taxonomy = AccountTaxonomy()

        # Test avec système core valide
        tm = TransactionManager(taxonomy)
        assert tm._api_calls['validation_checks'] > 0, "Validation checks pas exécutés"

        # Test détection corruption (transaction_num non-monotonic)
        # Note: Il est difficile de corrompre AccountTaxonomy car il a ses propres validations
        # Ce test vérifie que la validation est bien appelée


class TestSimplifiedAPI:
    """Tests API simplifiée - cœur du refactoring"""

    def test_add_accounts_auto_basic(self):
        """Test ajout comptes avec gestion automatique transaction_num"""
        taxonomy = AccountTaxonomy()
        tm = TransactionManager(taxonomy)

        # Ajout comptes avec API simplifiée
        accounts = {
            "alice_farm_source": "A",
            "bob_factory_sink": "B",
            "charlie_shop_source": "C"
        }

        result = tm.add_accounts_auto(accounts)

        # Vérifications résultat
        assert len(result) == 3, "Résultat mapping incorrect"
        assert result["alice_farm_source"] == "A", "Mapping Alice incorrect"
        assert result["bob_factory_sink"] == "B", "Mapping Bob incorrect"
        assert result["charlie_shop_source"] == "C", "Mapping Charlie incorrect"

        # Vérifications état TransactionManager
        assert tm._auto_transaction_counter == 1, "Auto counter pas incrémenté"
        assert tm.get_current_transaction_num() == 0, "Current tx incorrect après ajout"

        # Vérifications système core MIS À JOUR CORRECTEMENT
        assert len(taxonomy.taxonomy_history) == 1, "Core taxonomy pas mis à jour"
        assert len(taxonomy.account_registry) == 3, "Core registry pas mis à jour"

    def test_add_accounts_auto_multiple_calls(self):
        """Test appels multiples add_accounts_auto"""
        taxonomy = AccountTaxonomy()
        tm = TransactionManager(taxonomy)

        # Premier lot
        first_accounts = {"account_1": "A", "account_2": "B"}
        result1 = tm.add_accounts_auto(first_accounts)

        # Deuxième lot
        second_accounts = {"account_3": "C", "account_4": "D"}
        result2 = tm.add_accounts_auto(second_accounts)

        # Vérifications progression transaction_num
        assert tm._auto_transaction_counter == 2, "Auto counter progression incorrecte"
        assert tm.get_current_transaction_num() == 1, "Current tx après 2 appels incorrect"

        # Vérifications core system
        assert len(taxonomy.taxonomy_history) == 2, "2 snapshots attendus"
        assert len(taxonomy.account_registry) == 4, "4 comptes attendus"

        # Vérifications accès mappings actuels
        assert tm.get_current_mapping("account_3") == "C", "Mapping récent inaccessible"
        assert tm.get_current_mapping("account_1") == "A", "Mapping ancien inaccessible"

    def test_get_current_mapping(self):
        """Test récupération mapping actuel sans spécifier transaction_num"""
        taxonomy = AccountTaxonomy()
        tm = TransactionManager(taxonomy)

        # Test avant configuration
        assert tm.get_current_mapping("nonexistent") is None, "Mapping avant config pas None"

        # Configuration comptes
        accounts = {"test_account": "T", "another_account": "U"}
        tm.add_accounts_auto(accounts)

        # Test après configuration
        assert tm.get_current_mapping("test_account") == "T", "Current mapping incorrect"
        assert tm.get_current_mapping("another_account") == "U", "Current mapping 2 incorrect"
        assert tm.get_current_mapping("nonexistent") is None, "Compte inexistant pas None"

    def test_convert_path_current(self):
        """Test conversion path avec état actuel automatique"""
        taxonomy = AccountTaxonomy()
        tm = TransactionManager(taxonomy)

        # Test avant configuration - doit lever exception
        from icgs_core.dag_structures import Node
        path = [Node("account_1")]

        with pytest.raises(ValueError, match="No taxonomy configured"):
            tm.convert_path_current(path)

        # Configuration et test conversion
        accounts = {"account_1": "A", "account_2": "B"}
        tm.add_accounts_auto(accounts)

        # Test conversion réussie
        path = [Node("account_1"), Node("account_2")]
        word = tm.convert_path_current(path)
        assert word == "AB", "Conversion path incorrecte"


class TestAdvancedAPI:
    """Tests API avancée - backward compatibility"""

    def test_get_character_mapping_at(self):
        """Test accès historique explicite"""
        taxonomy = AccountTaxonomy()
        tm = TransactionManager(taxonomy)

        # Configuration historique
        tm.add_accounts_auto({"account_1": "A"})  # tx=0
        tm.add_accounts_auto({"account_2": "B"})  # tx=1

        # Tests accès historique
        assert tm.get_character_mapping_at("account_1", 0) == "A", "Accès historique tx=0 incorrect"
        assert tm.get_character_mapping_at("account_1", 1) == "A", "Héritage tx=1 incorrect"
        assert tm.get_character_mapping_at("account_2", 0) is None, "Accès avant création incorrect"
        assert tm.get_character_mapping_at("account_2", 1) == "B", "Accès historique tx=1 incorrect"

    def test_convert_path_at(self):
        """Test conversion à transaction spécifique"""
        taxonomy = AccountTaxonomy()
        tm = TransactionManager(taxonomy)

        # Configuration
        tm.add_accounts_auto({"acc1": "A", "acc2": "B"})

        # Test conversion historique
        from icgs_core.dag_structures import Node
        path = [Node("acc1"), Node("acc2")]
        word = tm.convert_path_at(path, 0)
        assert word == "AB", "Conversion historique incorrecte"

    def test_update_taxonomy_explicit(self):
        """Test contrôle explicite transaction_num"""
        taxonomy = AccountTaxonomy()
        tm = TransactionManager(taxonomy)

        # Test ajout explicite à transaction spécifique
        accounts = {"explicit_account": "E"}
        result = tm.update_taxonomy_explicit(accounts, 5)

        assert result["explicit_account"] == "E", "Explicit update result incorrect"
        assert len(taxonomy.taxonomy_history) == 1, "Explicit update core pas mis à jour"

        # Vérification transaction_num explicite respecté
        snapshot = taxonomy.taxonomy_history[0]
        assert snapshot.transaction_num == 5, "Transaction_num explicite pas respecté"

    def test_explicit_frozen_snapshot_protection(self):
        """Test protection snapshots figés"""
        taxonomy = AccountTaxonomy()

        # Création donnée "historique"
        taxonomy.update_taxonomy({"legacy": "L"}, 0)

        tm = TransactionManager(taxonomy)

        # Tentative modification snapshot figé doit échouer
        with pytest.raises(ValueError, match="Cannot modify frozen snapshot"):
            tm.update_taxonomy_explicit({"new_account": "N"}, 0)


class TestDataIntegrity:
    """Tests intégrité données - contrainte absolue"""

    def test_no_core_modification(self):
        """Test CRITIQUE: aucune modification système core"""
        taxonomy = AccountTaxonomy()

        # État initial core
        initial_history_length = len(taxonomy.taxonomy_history)
        initial_registry_size = len(taxonomy.account_registry)
        initial_next_char = taxonomy.next_character

        # Création TransactionManager
        tm = TransactionManager(taxonomy)

        # Vérification AUCUNE modification
        assert len(taxonomy.taxonomy_history) == initial_history_length, "Histoire modifiée lors création TM"
        assert len(taxonomy.account_registry) == initial_registry_size, "Registry modifié lors création TM"
        assert taxonomy.next_character == initial_next_char, "Next character modifié lors création TM"

        # Même test après opérations TransactionManager
        tm.add_accounts_auto({"test": "T"})

        # Les modifications doivent passer PAR le core system (c'est attendu)
        assert len(taxonomy.taxonomy_history) == 1, "Core system mis à jour via TM"
        assert len(taxonomy.account_registry) == 1, "Registry mis à jour via TM"

    def test_historical_data_preservation(self):
        """Test préservation données historiques existantes"""
        taxonomy = AccountTaxonomy()

        # Création données "historiques"
        historical_data = {"historical_1": "H", "historical_2": "I"}
        taxonomy.update_taxonomy(historical_data, 0)

        # Copie état historique pour validation
        original_snapshot = taxonomy.taxonomy_history[0]
        original_mappings = original_snapshot.account_mappings.copy()
        original_timestamp = original_snapshot.timestamp
        original_tx_num = original_snapshot.transaction_num

        # Opérations via TransactionManager
        tm = TransactionManager(taxonomy)
        tm.add_accounts_auto({"modern_account": "M"})

        # Validation données historiques INTACTES
        preserved_snapshot = taxonomy.taxonomy_history[0]  # Premier snapshot
        assert preserved_snapshot.account_mappings == original_mappings, "Mappings historiques corrompus"
        assert preserved_snapshot.timestamp == original_timestamp, "Timestamp historique corrompu"
        assert preserved_snapshot.transaction_num == original_tx_num, "Transaction_num historique corrompu"

        # Validation nouvelles données correctes
        modern_snapshot = taxonomy.taxonomy_history[1]  # Deuxième snapshot
        assert "modern_account" in modern_snapshot.account_mappings, "Nouvelles données pas ajoutées"
        assert modern_snapshot.account_mappings["modern_account"] == "M", "Nouveau mapping incorrect"

    def test_validate_integrity_comprehensive(self):
        """Test validation intégrité complète"""
        taxonomy = AccountTaxonomy()
        tm = TransactionManager(taxonomy)

        # Configuration système
        tm.add_accounts_auto({"acc1": "A", "acc2": "B"})
        tm.add_accounts_auto({"acc3": "C"})

        # Validation intégrité
        integrity_result = tm.validate_integrity()

        # Vérifications résultat
        assert integrity_result["overall_status"] is True, "Overall status incorrect"
        assert integrity_result["core_integrity"] is True, "Core integrity incorrect"
        assert integrity_result["monotonic_transactions"] is True, "Monotonic check incorrect"
        assert len(integrity_result["errors"]) == 0, "Erreurs détectées"
        assert "timestamp" in integrity_result, "Timestamp manquant"


class TestMetricsAndMonitoring:
    """Tests métriques et monitoring"""

    def test_system_metrics(self):
        """Test métriques système complètes"""
        taxonomy = AccountTaxonomy()
        tm = TransactionManager(taxonomy)

        # Configuration pour générer métriques
        tm.add_accounts_auto({"acc1": "A"})
        tm.get_character_mapping_at("acc1", 0)  # API avancée

        metrics = tm.get_system_metrics()

        # Vérification structure métriques
        assert "transaction_manager" in metrics, "Section TM manquante"
        assert "core_taxonomy" in metrics, "Section core manquante"
        assert "system_status" in metrics, "Section status manquante"

        # Vérification valeurs TransactionManager
        tm_metrics = metrics["transaction_manager"]
        assert tm_metrics["current_transaction_counter"] == 1, "Current counter incorrect"
        assert tm_metrics["frozen_snapshots_count"] == 0, "Frozen count initial incorrect"

        # Vérification valeurs core taxonomy
        core_metrics = metrics["core_taxonomy"]
        assert core_metrics["total_snapshots"] == 1, "Total snapshots incorrect"
        assert core_metrics["account_registry_size"] == 1, "Registry size incorrect"

    def test_usage_statistics(self):
        """Test statistiques d'usage pour migration tracking"""
        taxonomy = AccountTaxonomy()
        tm = TransactionManager(taxonomy)

        # Utilisation API mixte
        tm.add_accounts_auto({"acc1": "A"})  # API simplifiée
        tm.add_accounts_auto({"acc2": "B"})  # API simplifiée
        tm.get_character_mapping_at("acc1", 0)  # API avancée

        usage = tm.get_usage_statistics()

        # Vérification compteurs
        assert usage["api_usage"]["auto_api_calls"] == 2, "Auto API calls incorrect"
        assert usage["api_usage"]["advanced_api_calls"] == 1, "Advanced API calls incorrect"
        assert usage["api_usage"]["total_calls"] >= 3, "Total calls incorrect"

        # Vérification ratios migration
        assert usage["api_usage"]["auto_api_ratio"] > 0, "Auto ratio nul"
        assert usage["migration_progress"]["backward_compatibility_used"] is True, "BC flag incorrect"


class TestPerformanceAndEdgeCases:
    """Tests performance et cas limites"""

    def test_performance_overhead_measurement(self):
        """Test mesure overhead performance vs système original"""
        import time

        # Test système original
        original_taxonomy = AccountTaxonomy()
        accounts = {"perf_test": "P"}

        start_time = time.perf_counter()
        for _ in range(100):  # 100 opérations
            original_taxonomy.update_taxonomy(accounts, _)
        original_time = time.perf_counter() - start_time

        # Test avec TransactionManager
        tm_taxonomy = AccountTaxonomy()
        tm = TransactionManager(tm_taxonomy)

        start_time = time.perf_counter()
        for i in range(100):
            tm.add_accounts_auto({f"perf_test_{i}": chr(65 + (i % 26))})
        tm_time = time.perf_counter() - start_time

        # Calcul overhead - doit être < 50% (très généreux pour test unitaire)
        overhead_ratio = tm_time / max(original_time, 0.001)  # Éviter division par 0
        assert overhead_ratio < 1.5, f"Overhead trop élevé: {overhead_ratio:.2f}x"

    def test_empty_system_edge_cases(self):
        """Test cas limites système vide"""
        taxonomy = AccountTaxonomy()
        tm = TransactionManager(taxonomy)

        # Tests avant configuration
        assert tm.get_current_mapping("anything") is None, "Empty system mapping pas None"
        assert tm.get_current_transaction_num() == -1, "Empty system tx num incorrect"

        # Métriques système vide
        metrics = tm.get_system_metrics()
        assert metrics["core_taxonomy"]["total_snapshots"] == 0, "Empty snapshots incorrect"

    def test_large_scale_simulation(self):
        """Test simulation échelle moyenne"""
        taxonomy = AccountTaxonomy()
        tm = TransactionManager(taxonomy)

        # Simulation 25 comptes sur 5 transactions avec caractères ASCII étendus
        base_char = 65  # Commence à 'A'

        for tx_batch in range(5):
            batch_accounts = {}
            for acc_id in range(5):  # 5 comptes par batch
                account_name = f"account_{tx_batch}_{acc_id}"
                # Utiliser index global pour éviter collisions
                char_index = tx_batch * 5 + acc_id
                character = chr(base_char + char_index)
                batch_accounts[account_name] = character

            tm.add_accounts_auto(batch_accounts)

        # Validations finales
        assert tm._auto_transaction_counter == 5, "Counter final incorrect"
        assert len(taxonomy.account_registry) == 25, "Registry final incorrect"
        assert len(taxonomy.taxonomy_history) == 5, "History final incorrect"

        # Test intégrité après opérations massives
        integrity = tm.validate_integrity()
        if not integrity["overall_status"]:
            # Debug si échec
            print(f"Integrity errors: {integrity['errors'][:3]}...")  # Premiers 3 pour debug
        assert integrity["overall_status"] is True, "Intégrité après mass ops incorrecte"


if __name__ == "__main__":
    # Execution directe pour debugging
    pytest.main([__file__, "-v"])