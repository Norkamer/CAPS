"""
Test Équivalence API - Validation Ancienne vs Nouvelle API

Ce module teste rigoureusement l'équivalence entre l'API DAG originale
et la nouvelle API EnhancedDAG pour s'assurer que le refactoring ne change
AUCUN comportement fonctionnel.

OBJECTIFS CRITIQUES:
1. Résultats identiques pour configurations équivalentes
2. Performance comparable entre les deux APIs
3. Intégrité données préservée dans les deux cas
4. Couverture tous cas d'usage principaux

Niveau : Tests validation équivalence fonctionnelle
"""

import pytest
import time
from decimal import Decimal
from typing import Dict, List, Tuple

# Import du système à tester
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_core.enhanced_dag import EnhancedDAG
from icgs_core.dag import DAG, DAGConfiguration, Transaction, TransactionMeasure
from icgs_core.dag_structures import Node
from icgs_core.account_taxonomy import AccountTaxonomy


class TestBasicConfigurationEquivalence:
    """Tests équivalence configuration de base"""

    def test_equivalent_account_configuration(self):
        """Test configuration comptes identique entre les deux APIs"""
        # Configuration commune
        config = DAGConfiguration()
        account_mappings = {
            "alice_farm_source": "A",
            "alice_farm_sink": "B",
            "bob_factory_source": "C",
            "bob_factory_sink": "D"
        }

        # Setup avec API originale
        original_dag = DAG(config)
        # Configuration manuelle avec boucle (ancienne méthode)
        for tx_num in range(1):  # Une seule transaction pour équivalence
            original_dag.account_taxonomy.update_taxonomy(account_mappings, tx_num)

        # Setup avec nouvelle API
        enhanced_dag = EnhancedDAG(config)
        enhanced_result = enhanced_dag.configure_accounts_simple(account_mappings)

        # Validation équivalence résultats
        assert enhanced_result == account_mappings, "Résultat configuration équivalent"

        # Validation état système équivalent
        for account_id in account_mappings.keys():
            original_mapping = original_dag.account_taxonomy.get_character_mapping(account_id, 0)
            enhanced_mapping = enhanced_dag.get_current_account_mapping(account_id)

            assert original_mapping == enhanced_mapping, (
                f"Mapping équivalent pour {account_id}: "
                f"original={original_mapping}, enhanced={enhanced_mapping}"
            )

        # Validation registres comptes équivalents
        assert len(original_dag.account_taxonomy.account_registry) == len(enhanced_dag.account_taxonomy.account_registry), \
            "Taille registre équivalente"

    def test_equivalent_path_conversion(self):
        """Test conversion path équivalente"""
        # Setup identique
        config = DAGConfiguration()
        account_mappings = {"node1": "A", "node2": "B", "node3": "C"}
        test_path = [Node("node1"), Node("node2"), Node("node3")]

        # API originale
        original_dag = DAG(config)
        original_dag.account_taxonomy.update_taxonomy(account_mappings, 0)
        original_word = original_dag.account_taxonomy.convert_path_to_word(test_path, 0)

        # API nouvelle
        enhanced_dag = EnhancedDAG(config)
        enhanced_dag.configure_accounts_simple(account_mappings)
        enhanced_word = enhanced_dag.convert_path_simple(test_path)

        # Validation équivalence
        assert original_word == enhanced_word, (
            f"Conversion path équivalente: original='{original_word}', enhanced='{enhanced_word}'"
        )
        assert original_word == "ABC", "Conversion correcte"

    def test_equivalent_system_state(self):
        """Test état système équivalent après configuration"""
        config = DAGConfiguration()
        account_mappings = {"test_acc_1": "T", "test_acc_2": "U", "test_acc_3": "V"}

        # Configuration via les deux APIs
        original_dag = DAG(config)
        original_dag.account_taxonomy.update_taxonomy(account_mappings, 0)

        enhanced_dag = EnhancedDAG(config)
        enhanced_dag.configure_accounts_simple(account_mappings)

        # Validation états AccountTaxonomy équivalents
        original_history = original_dag.account_taxonomy.taxonomy_history
        enhanced_history = enhanced_dag.account_taxonomy.taxonomy_history

        # Au moins un snapshot dans chaque cas
        assert len(original_history) >= 1, "Historique original non vide"
        assert len(enhanced_history) >= 1, "Historique enhanced non vide"

        # Mappings équivalents dans le dernier snapshot
        original_last = original_history[-1]
        enhanced_last = enhanced_history[-1]

        for account_id in account_mappings.keys():
            assert account_id in original_last.account_mappings, f"Compte {account_id} dans original"
            assert account_id in enhanced_last.account_mappings, f"Compte {account_id} dans enhanced"

            orig_char = original_last.account_mappings[account_id]
            enh_char = enhanced_last.account_mappings[account_id]
            assert orig_char == enh_char, f"Caractères équivalents pour {account_id}"


class TestPerformanceEquivalence:
    """Tests équivalence performance entre APIs"""

    def test_configuration_performance_comparison(self):
        """Test performance configuration comparable"""
        config = DAGConfiguration()
        large_mappings = {f"perf_account_{i}": chr(65 + i) for i in range(20)}  # A-T

        # Mesure API originale
        start_time = time.perf_counter()

        original_dag = DAG(config)
        original_dag.account_taxonomy.update_taxonomy(large_mappings, 0)

        # Quelques accès pour mesure complète
        for account_id in list(large_mappings.keys())[:5]:
            original_dag.account_taxonomy.get_character_mapping(account_id, 0)

        original_time = time.perf_counter() - start_time

        # Mesure API nouvelle
        start_time = time.perf_counter()

        enhanced_dag = EnhancedDAG(config)
        enhanced_dag.configure_accounts_simple(large_mappings)

        # Accès équivalents
        for account_id in list(large_mappings.keys())[:5]:
            enhanced_dag.get_current_account_mapping(account_id)

        enhanced_time = time.perf_counter() - start_time

        # Validation performance comparable
        performance_ratio = enhanced_time / max(original_time, 0.001)  # Éviter division par 0
        assert performance_ratio < 2.0, f"Performance enhanced acceptable: ratio={performance_ratio:.2f}"

        print(f"Performance comparison: Original={original_time:.4f}s, Enhanced={enhanced_time:.4f}s")

    def test_access_performance_equivalence(self):
        """Test performance accès mappings équivalente"""
        config = DAGConfiguration()
        mappings = {f"access_test_{i}": chr(65 + i) for i in range(10)}

        # Setup systèmes
        original_dag = DAG(config)
        original_dag.account_taxonomy.update_taxonomy(mappings, 0)

        enhanced_dag = EnhancedDAG(config)
        enhanced_dag.configure_accounts_simple(mappings)

        # Test accès répétés - API originale
        start_time = time.perf_counter()
        for _ in range(100):
            for account_id in mappings.keys():
                original_dag.account_taxonomy.get_character_mapping(account_id, 0)
        original_access_time = time.perf_counter() - start_time

        # Test accès répétés - API nouvelle
        start_time = time.perf_counter()
        for _ in range(100):
            for account_id in mappings.keys():
                enhanced_dag.get_current_account_mapping(account_id)
        enhanced_access_time = time.perf_counter() - start_time

        # Validation performance équivalente
        access_ratio = enhanced_access_time / max(original_access_time, 0.001)
        assert access_ratio < 1.5, f"Performance accès acceptable: ratio={access_ratio:.2f}"


class TestEdgeCasesEquivalence:
    """Tests équivalence cas limites"""

    def test_empty_configuration_equivalence(self):
        """Test comportement équivalent configuration vide"""
        config = DAGConfiguration()

        # API originale - état initial
        original_dag = DAG(config)
        original_empty_mapping = original_dag.account_taxonomy.get_character_mapping("nonexistent", 0)

        # API nouvelle - état initial
        enhanced_dag = EnhancedDAG(config)
        enhanced_empty_mapping = enhanced_dag.get_current_account_mapping("nonexistent")

        # Comportement équivalent pour compte inexistant
        assert original_empty_mapping == enhanced_empty_mapping, "Comportement vide équivalent"
        assert original_empty_mapping is None, "Résultat None attendu"

    def test_single_account_equivalence(self):
        """Test équivalence avec un seul compte"""
        config = DAGConfiguration()
        single_mapping = {"solo_account": "S"}

        # Configuration via les deux APIs
        original_dag = DAG(config)
        original_dag.account_taxonomy.update_taxonomy(single_mapping, 0)

        enhanced_dag = EnhancedDAG(config)
        enhanced_dag.configure_accounts_simple(single_mapping)

        # Validation équivalence
        original_result = original_dag.account_taxonomy.get_character_mapping("solo_account", 0)
        enhanced_result = enhanced_dag.get_current_account_mapping("solo_account")

        assert original_result == enhanced_result == "S", "Compte unique équivalent"

    def test_special_characters_equivalence(self):
        """Test équivalence avec caractères spéciaux"""
        config = DAGConfiguration()
        special_mappings = {
            "unicode_test_1": "α",  # Caractère grec
            "unicode_test_2": "β",
            "unicode_test_3": "γ"
        }

        # Configuration via les deux APIs
        original_dag = DAG(config)
        original_dag.account_taxonomy.update_taxonomy(special_mappings, 0)

        enhanced_dag = EnhancedDAG(config)
        enhanced_dag.configure_accounts_simple(special_mappings)

        # Validation équivalence caractères Unicode
        for account_id, expected_char in special_mappings.items():
            original_char = original_dag.account_taxonomy.get_character_mapping(account_id, 0)
            enhanced_char = enhanced_dag.get_current_account_mapping(account_id)

            assert original_char == enhanced_char == expected_char, (
                f"Caractère Unicode équivalent pour {account_id}: "
                f"original={original_char}, enhanced={enhanced_char}"
            )


class TestErrorHandlingEquivalence:
    """Tests équivalence gestion erreurs"""

    def test_invalid_character_error_equivalence(self):
        """Test gestion erreurs caractères invalides équivalente"""
        config = DAGConfiguration()

        # Test API originale avec caractère vide
        original_dag = DAG(config)
        with pytest.raises(ValueError):
            original_dag.account_taxonomy.update_taxonomy({"test": ""}, 0)

        # Test API nouvelle avec même erreur
        enhanced_dag = EnhancedDAG(config)
        with pytest.raises(ValueError):
            enhanced_dag.configure_accounts_simple({"test": ""})

        # Les deux doivent lever ValueError pour caractère invalide

    def test_collision_character_error_equivalence(self):
        """Test gestion collisions caractères équivalente"""
        config = DAGConfiguration()
        collision_mappings = {"acc1": "A", "acc2": "A"}  # Collision

        # Test API originale
        original_dag = DAG(config)
        with pytest.raises(ValueError, match="collision"):
            original_dag.account_taxonomy.update_taxonomy(collision_mappings, 0)

        # Test API nouvelle
        enhanced_dag = EnhancedDAG(config)
        with pytest.raises(ValueError, match="collision"):
            enhanced_dag.configure_accounts_simple(collision_mappings)

        # Comportement d'erreur équivalent

    def test_system_recovery_after_error_equivalence(self):
        """Test récupération système après erreur équivalente"""
        config = DAGConfiguration()

        # Scénario: Erreur puis configuration valide
        valid_mappings = {"recovery_test": "R"}

        # API originale
        original_dag = DAG(config)
        try:
            original_dag.account_taxonomy.update_taxonomy({"bad": ""}, 0)  # Erreur
        except ValueError:
            pass
        original_dag.account_taxonomy.update_taxonomy(valid_mappings, 0)  # Récupération
        original_result = original_dag.account_taxonomy.get_character_mapping("recovery_test", 0)

        # API nouvelle
        enhanced_dag = EnhancedDAG(config)
        try:
            enhanced_dag.configure_accounts_simple({"bad": ""})  # Erreur
        except ValueError:
            pass
        enhanced_dag.configure_accounts_simple(valid_mappings)  # Récupération
        enhanced_result = enhanced_dag.get_current_account_mapping("recovery_test")

        # Validation récupération équivalente
        assert original_result == enhanced_result == "R", "Récupération équivalente"


class TestRegressionValidation:
    """Tests validation non-régression"""

    def test_existing_functionality_preserved(self):
        """Test fonctionnalités existantes préservées"""
        # Configuration avec API nouvelle
        enhanced_dag = EnhancedDAG()
        mappings = {"regression_test": "G"}
        enhanced_dag.configure_accounts_simple(mappings)

        # Vérification que toutes fonctionnalités DAG originales fonctionnent
        # Test accès direct AccountTaxonomy
        direct_mapping = enhanced_dag.account_taxonomy.get_character_mapping("regression_test", 0)
        assert direct_mapping == "G", "Accès direct AccountTaxonomy fonctionne"

        # Test méthodes DAG héritées accessibles
        assert hasattr(enhanced_dag, 'add_account'), "Méthode add_account héritée"
        assert hasattr(enhanced_dag, 'validate_dag_integrity'), "Méthode validate_dag_integrity héritée"

        # Test transaction_counter accessible
        assert isinstance(enhanced_dag.transaction_counter, int), "Transaction counter accessible"

    def test_no_side_effects_on_original_api(self):
        """Test aucun effet de bord sur API originale"""
        # Utilisation API nouvelle ne doit pas affecter API originale
        enhanced_dag = EnhancedDAG()
        enhanced_dag.configure_accounts_simple({"side_effect_test": "E"})

        # Création DAG original séparé
        original_dag = DAG()
        original_dag.account_taxonomy.update_taxonomy({"original_test": "O"}, 0)

        # Vérification aucune interférence
        original_mapping = original_dag.account_taxonomy.get_character_mapping("original_test", 0)
        assert original_mapping == "O", "API originale non affectée"

        # Enhanced ne doit pas voir les données original
        enhanced_mapping = enhanced_dag.get_current_account_mapping("original_test")
        assert enhanced_mapping is None, "Isolation entre instances"

    def test_configuration_isolation(self):
        """Test isolation configuration entre instances"""
        config1 = DAGConfiguration(max_path_enumeration=1000)
        config2 = DAGConfiguration(max_path_enumeration=2000)

        # Deux instances Enhanced avec configs différentes
        enhanced_dag1 = EnhancedDAG(config1)
        enhanced_dag2 = EnhancedDAG(config2)

        # Configurations préservées indépendamment
        assert enhanced_dag1.configuration.max_path_enumeration == 1000, "Config 1 préservée"
        assert enhanced_dag2.configuration.max_path_enumeration == 2000, "Config 2 préservée"

        # Données isolées
        enhanced_dag1.configure_accounts_simple({"dag1": "A"})
        enhanced_dag2.configure_accounts_simple({"dag2": "B"})

        assert enhanced_dag1.get_current_account_mapping("dag1") == "A", "Données DAG1 isolées"
        assert enhanced_dag1.get_current_account_mapping("dag2") is None, "Isolation DAG1"

        assert enhanced_dag2.get_current_account_mapping("dag2") == "B", "Données DAG2 isolées"
        assert enhanced_dag2.get_current_account_mapping("dag1") is None, "Isolation DAG2"


if __name__ == "__main__":
    # Execution directe pour debugging
    pytest.main([__file__, "-v"])