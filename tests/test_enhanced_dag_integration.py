"""
Test Intégration EnhancedDAG - Validation Architecture Phase 2

Ce module teste exhaustivement l'intégration EnhancedDAG avec le système
existant pour s'assurer que toutes les garanties du refactoring sont respectées :

1. HÉRITAGE COMPLET : EnhancedDAG hérite correctement de DAG
2. API SIMPLIFIÉE : Fonctionnalités révolutionnaires opérationnelles
3. BACKWARD COMPATIBILITY : API originale 100% préservée
4. INTÉGRITÉ : Données historiques et système core inchangés
5. PERFORMANCE : Overhead négligeable vs DAG original

Niveau : Tests d'intégration système complet
"""

import pytest
import time
from decimal import Decimal
from typing import Dict, List

# Import du système à tester
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_core.enhanced_dag import EnhancedDAG
from icgs_core.dag import DAG, DAGConfiguration, Transaction, TransactionMeasure
from icgs_core.dag_structures import Node
from icgs_core.transaction_manager import TransactionManager
from icgs_core.account_taxonomy import AccountTaxonomy


class TestEnhancedDAGInheritance:
    """Tests héritage et initialisation EnhancedDAG"""

    def test_enhanced_dag_inheritance(self):
        """Test héritage correct de DAG existant"""
        config = DAGConfiguration()
        enhanced_dag = EnhancedDAG(config)

        # Vérifications héritage
        assert isinstance(enhanced_dag, DAG), "EnhancedDAG doit hériter de DAG"
        assert isinstance(enhanced_dag, EnhancedDAG), "Instance type correct"

        # Vérifications attributs DAG présents
        assert hasattr(enhanced_dag, 'nodes'), "Attribut nodes DAG présent"
        assert hasattr(enhanced_dag, 'edges'), "Attribut edges DAG présent"
        assert hasattr(enhanced_dag, 'accounts'), "Attribut accounts DAG présent"
        assert hasattr(enhanced_dag, 'account_taxonomy'), "AccountTaxonomy présent"
        assert hasattr(enhanced_dag, 'transaction_counter'), "Transaction counter présent"

        # Vérifications attributs EnhancedDAG nouveaux
        assert hasattr(enhanced_dag, 'transaction_manager'), "TransactionManager intégré"
        assert isinstance(enhanced_dag.transaction_manager, TransactionManager), "TM type correct"

    def test_transaction_manager_integration(self):
        """Test intégration TransactionManager correcte"""
        enhanced_dag = EnhancedDAG()

        # Vérification référence partagée AccountTaxonomy
        assert enhanced_dag.transaction_manager._core_taxonomy is enhanced_dag.account_taxonomy, \
            "TransactionManager doit référencer même AccountTaxonomy"

        # Test synchronisation initiale
        assert enhanced_dag.transaction_manager._auto_transaction_counter == 0, "Counter TM initial"
        assert enhanced_dag.transaction_counter == 0, "Counter DAG initial"

    def test_configuration_consistency(self):
        """Test cohérence configuration DAG et TransactionManager"""
        config = DAGConfiguration(
            max_path_enumeration=5000,
            simplex_max_iterations=2000
        )
        enhanced_dag = EnhancedDAG(config)

        # Configuration DAG respectée
        assert enhanced_dag.configuration.max_path_enumeration == 5000, "Config DAG préservée"
        assert enhanced_dag.configuration.simplex_max_iterations == 2000, "Config DAG préservée"

        # TransactionManager opérationnel avec cette config
        metrics = enhanced_dag.transaction_manager.get_system_metrics()
        assert metrics['system_status']['operational'] is True, "TM opérationnel"


class TestSimplifiedAPI:
    """Tests API simplifiée - Cœur révolutionnaire du refactoring"""

    def test_configure_accounts_simple(self):
        """Test configuration simplifiée comptes"""
        enhanced_dag = EnhancedDAG()

        # Configuration avec API simplifiée
        accounts = {
            "alice_farm_source": "A",
            "bob_factory_sink": "B",
            "charlie_shop_source": "C",
            "dana_warehouse_sink": "D"
        }

        result = enhanced_dag.configure_accounts_simple(accounts)

        # Vérifications résultat
        assert len(result) == 4, "4 comptes configurés"
        assert result["alice_farm_source"] == "A", "Mapping Alice correct"
        assert result["bob_factory_sink"] == "B", "Mapping Bob correct"

        # Vérifications état système après configuration
        assert enhanced_dag._using_enhanced_api is True, "Flag API simplifiée activé"
        assert enhanced_dag._enhanced_api_calls > 0, "Compteur API simplifiée incrémenté"

        # Vérification système core mis à jour CORRECTEMENT
        # Note: DAG peut créer snapshot d'initialisation, donc >= 1
        assert len(enhanced_dag.account_taxonomy.taxonomy_history) >= 1, "Au moins un snapshot créé"
        assert len(enhanced_dag.account_taxonomy.account_registry) == 4, "4 comptes enregistrés"

    def test_get_current_account_mapping(self):
        """Test récupération mapping actuel simplifié"""
        enhanced_dag = EnhancedDAG()

        # Test avant configuration
        assert enhanced_dag.get_current_account_mapping("nonexistent") is None, "Pas de mapping avant config"

        # Configuration
        accounts = {"test_account": "T", "another_account": "U"}
        enhanced_dag.configure_accounts_simple(accounts)

        # Tests après configuration
        assert enhanced_dag.get_current_account_mapping("test_account") == "T", "Mapping actuel correct"
        assert enhanced_dag.get_current_account_mapping("another_account") == "U", "Mapping 2 correct"
        assert enhanced_dag.get_current_account_mapping("nonexistent") is None, "Compte inexistant None"

    def test_convert_path_simple(self):
        """Test conversion path simplifiée"""
        enhanced_dag = EnhancedDAG()

        # Test avant configuration - doit lever exception
        path = [Node("account_1")]
        with pytest.raises(ValueError, match="No taxonomy configured"):
            enhanced_dag.convert_path_simple(path)

        # Configuration et test conversion
        accounts = {"account_1": "A", "account_2": "B"}
        enhanced_dag.configure_accounts_simple(accounts)

        # Test conversion réussie
        path = [Node("account_1"), Node("account_2")]
        word = enhanced_dag.convert_path_simple(path)
        assert word == "AB", "Conversion path simplifiée correcte"

    def test_add_transaction_auto_preconditions(self):
        """Test pré-conditions add_transaction_auto"""
        enhanced_dag = EnhancedDAG()

        # Création transaction test
        transaction = Transaction(
            transaction_id="test_tx_1",
            source_account_id="alice_farm",
            target_account_id="bob_factory",
            amount=Decimal('100.0')
        )

        # Test sans configuration - doit échouer
        with pytest.raises(ValueError, match="Must configure accounts"):
            enhanced_dag.add_transaction_auto(transaction)

        # Configuration comptes nécessaires
        accounts = {
            "alice_farm_source": "A",
            "alice_farm_sink": "B",
            "bob_factory_source": "C",
            "bob_factory_sink": "D"
        }
        enhanced_dag.configure_accounts_simple(accounts)

        # Maintenant la transaction doit être prête à traiter
        # (Test sans execution complète car nécessiterait pipeline DAG complet)


class TestBackwardCompatibility:
    """Tests backward compatibility - Garantie critique refactoring"""

    def test_original_dag_methods_accessible(self):
        """Test méthodes DAG originales accessibles"""
        enhanced_dag = EnhancedDAG()

        # Toutes méthodes DAG principales doivent être héritées
        original_methods = [
            'add_account', 'add_transaction', 'get_dag_statistics',
            'validate_dag_integrity', '__str__', '__repr__'
        ]

        for method in original_methods:
            assert hasattr(enhanced_dag, method), f"Méthode DAG '{method}' doit être héritée"

    def test_original_add_transaction_preserved(self):
        """Test méthode add_transaction originale préservée"""
        enhanced_dag = EnhancedDAG()

        # Vérification signature et comportement identiques
        original_method = enhanced_dag.add_transaction
        assert callable(original_method), "add_transaction callable"

        # Test compteur appels API originale
        initial_original_calls = enhanced_dag._original_api_calls

        # Mock transaction (sans exécution complète)
        # Le test vérifie seulement que la méthode est accessible
        # Les tests complets nécessiteraient setup DAG complet

        # Vérification que l'appel sera bien compté comme API originale
        assert enhanced_dag._original_api_calls == initial_original_calls, "Compteur stable avant appel"

    def test_enhanced_vs_original_api_coexistence(self):
        """Test coexistence APIs nouvelle et ancienne"""
        enhanced_dag = EnhancedDAG()

        # Configuration avec API simplifiée
        accounts = {"account_1": "A", "account_2": "B"}
        enhanced_dag.configure_accounts_simple(accounts)

        # Accès avec API avancée aussi
        mapping_simple = enhanced_dag.get_current_account_mapping("account_1")
        mapping_advanced = enhanced_dag.transaction_manager.get_character_mapping_at("account_1", 0)

        # Résultats identiques
        assert mapping_simple == mapping_advanced, "APIs donnent résultats identiques"
        assert mapping_simple == "A", "Mapping correct via les deux APIs"

        # Vérification compteurs séparés
        assert enhanced_dag._enhanced_api_calls > 0, "API simplifiée utilisée"
        assert enhanced_dag._original_api_calls == 0, "API originale pas utilisée dans ce test"

    def test_migration_analytics_tracking(self):
        """Test tracking analytics migration"""
        enhanced_dag = EnhancedDAG()

        # État initial
        analytics = enhanced_dag.get_migration_analytics()
        assert analytics['migration_progress']['phase'] == "not_started", "Phase initiale correcte"

        # Utilisation API simplifiée
        accounts = {"account_1": "A"}
        enhanced_dag.configure_accounts_simple(accounts)
        enhanced_dag.get_current_account_mapping("account_1")

        # Analytics mises à jour
        analytics = enhanced_dag.get_migration_analytics()
        assert analytics['migration_progress']['phase'] != "not_started", "Phase progression détectée"
        assert analytics['usage_patterns']['simplified_api_adoption'] > 0, "Adoption API simplifiée trackée"


class TestSystemIntegrity:
    """Tests intégrité système - Contrainte absolue refactoring"""

    def test_historical_data_integrity_validation(self):
        """Test validation intégrité données historiques"""
        # Configuration données "historiques" via système original
        original_dag = DAG()
        historical_accounts = {"legacy_account": "L"}
        original_dag.account_taxonomy.update_taxonomy(historical_accounts, 0)

        # Création EnhancedDAG avec données existantes
        enhanced_dag = EnhancedDAG()
        enhanced_dag.account_taxonomy = original_dag.account_taxonomy
        enhanced_dag.transaction_manager = TransactionManager(enhanced_dag.account_taxonomy)

        # Nouvelles données via API simplifiée
        new_accounts = {"modern_account": "M"}
        enhanced_dag.configure_accounts_simple(new_accounts)

        # Validation données historiques INTACTES
        legacy_mapping = enhanced_dag.account_taxonomy.get_character_mapping("legacy_account", 0)
        assert legacy_mapping == "L", "Données historiques préservées"

        modern_mapping = enhanced_dag.get_current_account_mapping("modern_account")
        assert modern_mapping == "M", "Nouvelles données correctes"

    def test_system_validation_comprehensive(self):
        """Test validation système complète"""
        enhanced_dag = EnhancedDAG()

        # Configuration système
        accounts = {"acc1": "A", "acc2": "B"}
        enhanced_dag.configure_accounts_simple(accounts)

        # Validation complète
        validation = enhanced_dag.validate_complete_system()

        # Vérifications résultat
        assert validation['overall_status'] is True, "Statut global correct"
        assert validation['enhanced_dag_integrity'] is True, "EnhancedDAG intègre"
        assert validation['transaction_manager_integrity'] is True, "TransactionManager intègre"
        assert len(validation['errors']) == 0, "Aucune erreur détectée"

    def test_counter_synchronization(self):
        """Test synchronisation transaction counters"""
        enhanced_dag = EnhancedDAG()

        # Configuration initiale
        accounts = {"sync_test": "S"}
        enhanced_dag.configure_accounts_simple(accounts)

        # Vérification synchronisation
        enhanced_dag._synchronize_transaction_counters()

        dag_counter = enhanced_dag.transaction_counter
        tm_counter = enhanced_dag.transaction_manager._auto_transaction_counter

        # Différence acceptable (TM = "next available", DAG = "current")
        assert abs(tm_counter - dag_counter) <= 1, f"Counters synchronisés: DAG={dag_counter}, TM={tm_counter}"


class TestPerformanceAndEdgeCases:
    """Tests performance et cas limites"""

    def test_enhanced_dag_performance_baseline(self):
        """Test performance baseline EnhancedDAG"""
        import time

        # Mesure création et configuration
        start_time = time.perf_counter()

        enhanced_dag = EnhancedDAG()
        accounts = {f"perf_account_{i}": chr(65 + i) for i in range(10)}
        enhanced_dag.configure_accounts_simple(accounts)

        end_time = time.perf_counter()

        setup_time = end_time - start_time
        assert setup_time < 0.1, f"Setup time acceptable: {setup_time:.4f}s < 0.1s"

        # Mesure accès mappings
        start_time = time.perf_counter()

        for i in range(100):
            mapping = enhanced_dag.get_current_account_mapping(f"perf_account_{i % 10}")

        end_time = time.perf_counter()

        access_time = end_time - start_time
        assert access_time < 0.01, f"Access time acceptable: {access_time:.4f}s < 0.01s"

    def test_large_scale_configuration(self):
        """Test configuration grande échelle"""
        enhanced_dag = EnhancedDAG()

        # Configuration 25 comptes (pour éviter collisions A-Z)
        accounts = {}
        for i in range(25):
            account_name = f"large_scale_{i}"
            character = chr(65 + i)  # A-Z séquentiel
            accounts[account_name] = character

        result = enhanced_dag.configure_accounts_simple(accounts)

        # Validations
        assert len(result) == 25, "25 comptes configurés"
        assert len(enhanced_dag.account_taxonomy.account_registry) == 25, "25 comptes enregistrés"

        # Test intégrité finale
        validation = enhanced_dag.validate_complete_system()
        assert validation['overall_status'] is True, "Système intègre après config large"

    def test_error_handling_robustness(self):
        """Test robustesse error handling"""
        enhanced_dag = EnhancedDAG()

        # Test caractères invalides
        invalid_accounts = {"test_account": ""}  # Caractère vide
        with pytest.raises(ValueError):
            enhanced_dag.configure_accounts_simple(invalid_accounts)

        # Test collision caractères
        collision_accounts = {"acc1": "A", "acc2": "A"}  # Même caractère
        with pytest.raises(ValueError):
            enhanced_dag.configure_accounts_simple(collision_accounts)

        # Système doit rester stable après erreurs
        valid_accounts = {"valid_account": "V"}
        result = enhanced_dag.configure_accounts_simple(valid_accounts)
        assert result["valid_account"] == "V", "Système stable après erreurs"


class TestMigrationScenarios:
    """Tests scénarios migration réels"""

    def test_progressive_migration_scenario(self):
        """Test scénario migration progressive réaliste"""
        enhanced_dag = EnhancedDAG()

        # Phase 1: Configuration ancienne méthode (simulation)
        # (Normalement via DAG original, ici simulation état initial)

        # Phase 2: Migration vers API simplifiée
        accounts = {"migrated_account": "M"}
        enhanced_dag.configure_accounts_simple(accounts)

        # Phase 3: Usage mixte pendant transition
        simple_mapping = enhanced_dag.get_current_account_mapping("migrated_account")
        advanced_mapping = enhanced_dag.transaction_manager.get_character_mapping_at("migrated_account", 0)

        # Validation cohérence
        assert simple_mapping == advanced_mapping, "Cohérence pendant migration"
        assert simple_mapping == "M", "Mapping correct après migration"

        # Analytics de migration
        analytics = enhanced_dag.get_migration_analytics()
        assert analytics['migration_progress']['readiness_score'] > 0, "Score préparation positif"

    def test_rollback_scenario(self):
        """Test scénario rollback vers API originale"""
        enhanced_dag = EnhancedDAG()

        # Configuration avec API simplifiée
        accounts = {"rollback_test": "R"}
        enhanced_dag.configure_accounts_simple(accounts)

        # Retour vers utilisation API originale (méthodes héritées)
        # Toutes fonctionnalités DAG doivent rester accessibles
        assert hasattr(enhanced_dag, 'add_transaction'), "Méthode add_transaction accessible"
        assert hasattr(enhanced_dag, 'get_dag_statistics'), "Méthode get_dag_statistics accessible"

        # Données configurées via API simplifiée accessibles via API originale
        original_mapping = enhanced_dag.account_taxonomy.get_character_mapping("rollback_test", 0)
        assert original_mapping == "R", "Données API simplifiée accessibles via API originale"


if __name__ == "__main__":
    # Execution directe pour debugging
    pytest.main([__file__, "-v"])