#!/usr/bin/env python3
"""
Tests unitaires pour l'optimisation DFS causale

Valide les nouvelles fonctionnalités d'optimisation causale implémentées dans PathEnumerator:
- Détection nœud source transaction (AliceT3)
- Alternance incoming/outgoing selon profondeur
- Filtrage nœuds transactionnels
- Exclusion arêtes sortantes pour nœud source
"""

import unittest
from decimal import Decimal
from unittest.mock import Mock, MagicMock

from icgs_core import (
    DAG, DAGConfiguration, Transaction, TransactionMeasure, Account,
    Node, NodeType, Edge, EdgeType
)
from icgs_core.path_enumerator import DAGPathEnumerator


class TestCausalDFSOptimization(unittest.TestCase):
    """Tests pour l'optimisation DFS causale"""

    def setUp(self):
        """Configuration test avec DAG minimal"""
        config = DAGConfiguration(
            max_path_enumeration=100,
            simplex_max_iterations=50
        )

        self.dag = DAG(config)
        # Créer enumerator avec taxonomy du DAG
        self.enumerator = DAGPathEnumerator(
            taxonomy=self.dag.account_taxonomy,
            max_paths=50,
            batch_size=20
        )

        # Setup mock transaction edge pour tests
        self.mock_transaction_edge = Mock(spec=Edge)

        # Mock nodes avec pattern transactionnel
        self.alice_source = Mock(spec=Node)
        self.alice_source.node_id = "alice_source"
        self.alice_source.incoming_edges = {}
        self.alice_source.outgoing_edges = {}

        self.alice_sink = Mock(spec=Node)
        self.alice_sink.node_id = "alice_sink"
        self.alice_sink.incoming_edges = {}
        self.alice_sink.outgoing_edges = {}

        self.bob_source = Mock(spec=Node)
        self.bob_source.node_id = "bob_source"
        self.bob_source.incoming_edges = {}
        self.bob_source.outgoing_edges = {}

        self.bob_sink = Mock(spec=Node)
        self.bob_sink.node_id = "bob_sink"
        self.bob_sink.incoming_edges = {}
        self.bob_sink.outgoing_edges = {}

        # Configuration transaction edge pour Alice->Bob
        self.mock_transaction_edge.source_node = self.alice_source
        self.mock_transaction_edge.target_node = self.bob_sink
        self.mock_transaction_edge.edge_id = "tx_alice_bob"

    def test_is_transaction_source_node_detection(self):
        """Test détection nœud source de transaction (CORRIGÉ: alice_sink, pas alice_source)"""
        # Configuration enumerator avec transaction courante
        self.enumerator.current_transaction_edge = self.mock_transaction_edge

        # CORRECTION: Dans l'optimisation causale, le nœud origin est alice_sink (sink du compte source)
        self.assertTrue(
            self.enumerator._is_transaction_source_node(self.alice_sink),
            "alice_sink devrait être détecté comme nœud origin (sink du compte source)"
        )

        # Test: alice_source ne devrait PAS être détecté comme nœud origin
        self.assertFalse(
            self.enumerator._is_transaction_source_node(self.alice_source),
            "alice_source ne devrait pas être nœud origin"
        )

        # Test: bob_sink ne devrait PAS être détecté comme nœud origin
        self.assertFalse(
            self.enumerator._is_transaction_source_node(self.bob_sink),
            "bob_sink ne devrait pas être nœud origin"
        )

    def test_is_transaction_node_filtering(self):
        """Test filtrage nœuds transactionnels vs non-transactionnels"""
        # Nœuds transactionnels (finissent par _source ou _sink)
        self.assertTrue(self.enumerator._is_transaction_node(self.alice_source))
        self.assertTrue(self.enumerator._is_transaction_node(self.alice_sink))
        self.assertTrue(self.enumerator._is_transaction_node(self.bob_source))
        self.assertTrue(self.enumerator._is_transaction_node(self.bob_sink))

        # Mock nœud non-transactionnel
        non_tx_node = Mock(spec=Node)
        non_tx_node.node_id = "pure_source_node"
        self.assertFalse(
            self.enumerator._is_transaction_node(non_tx_node),
            "Nœud 'pure_source_node' ne devrait pas être transactionnel"
        )

        # Test cas limites
        self.assertFalse(self.enumerator._is_transaction_node(None))

        empty_node = Mock(spec=Node)
        empty_node.node_id = ""
        self.assertFalse(self.enumerator._is_transaction_node(empty_node))

    def test_causal_traversal_transaction_source_incoming_only(self):
        """Test exclusion arêtes sortantes pour nœud source transaction"""
        # Setup: alice_source est le nœud source transaction
        self.enumerator.current_transaction_edge = self.mock_transaction_edge

        # Mock edges pour alice_source
        incoming_edge1 = Mock(spec=Edge)
        incoming_edge1.source_node = self.bob_source  # Nœud transactionnel
        incoming_edge1.target_node = self.alice_source

        outgoing_edge1 = Mock(spec=Edge)
        outgoing_edge1.source_node = self.alice_source
        outgoing_edge1.target_node = self.alice_sink  # Nœud transactionnel

        self.alice_source.incoming_edges = {"in1": incoming_edge1}
        self.alice_source.outgoing_edges = {"out1": outgoing_edge1}

        # Test: nœud source transaction devrait utiliser UNIQUEMENT incoming edges
        edges = self.enumerator._get_edges_for_causal_traversal(self.alice_source, 0)

        # Vérification: seulement l'arête entrante devrait être retournée
        self.assertEqual(len(edges), 1, "Nœud source transaction: seulement arêtes entrantes")
        self.assertEqual(edges[0], incoming_edge1, "Arête entrante devrait être présente")

    def test_causal_traversal_alternance_depth(self):
        """Test alternance incoming/outgoing selon profondeur"""
        # Setup: bob_source n'est PAS le nœud source transaction
        self.enumerator.current_transaction_edge = self.mock_transaction_edge

        # Mock edges pour bob_source
        incoming_edge = Mock(spec=Edge)
        incoming_edge.source_node = self.alice_source  # Transactionnel
        incoming_edge.target_node = self.bob_source

        outgoing_edge = Mock(spec=Edge)
        outgoing_edge.source_node = self.bob_source
        outgoing_edge.target_node = self.bob_sink  # Transactionnel

        self.bob_source.incoming_edges = {"in": incoming_edge}
        self.bob_source.outgoing_edges = {"out": outgoing_edge}

        # Test profondeur paire (0, 2, 4...) -> INCOMING edges
        edges_depth_0 = self.enumerator._get_edges_for_causal_traversal(self.bob_source, 0)
        self.assertEqual(len(edges_depth_0), 1)
        self.assertEqual(edges_depth_0[0], incoming_edge, "Profondeur 0: incoming edge")

        edges_depth_2 = self.enumerator._get_edges_for_causal_traversal(self.bob_source, 2)
        self.assertEqual(len(edges_depth_2), 1)
        self.assertEqual(edges_depth_2[0], incoming_edge, "Profondeur 2: incoming edge")

        # Test profondeur impaire (1, 3, 5...) -> OUTGOING edges
        edges_depth_1 = self.enumerator._get_edges_for_causal_traversal(self.bob_source, 1)
        self.assertEqual(len(edges_depth_1), 1)
        self.assertEqual(edges_depth_1[0], outgoing_edge, "Profondeur 1: outgoing edge")

        edges_depth_3 = self.enumerator._get_edges_for_causal_traversal(self.bob_source, 3)
        self.assertEqual(len(edges_depth_3), 1)
        self.assertEqual(edges_depth_3[0], outgoing_edge, "Profondeur 3: outgoing edge")

    def test_causal_traversal_non_transactional_filtering(self):
        """Test filtrage exclusion nœuds non-transactionnels"""
        # Utiliser un nœud différent pour éviter confusion avec transaction edge
        test_node = Mock(spec=Node)
        test_node.node_id = "test_node_sink"  # Nœud transactionnel
        test_node.incoming_edges = {}
        test_node.outgoing_edges = {}

        # Mock nœud non-transactionnel (ne finit PAS par _source ou _sink)
        non_tx_node = Mock(spec=Node)
        non_tx_node.node_id = "pure_node"  # Non-transactionnel

        # Mock edge vers nœud non-transactionnel
        edge_to_non_tx = Mock(spec=Edge)
        edge_to_non_tx.source_node = non_tx_node  # Non-transactionnel -> devrait être filtré
        edge_to_non_tx.target_node = test_node

        # Mock edge vers nœud transactionnel
        edge_to_tx = Mock(spec=Edge)
        edge_to_tx.source_node = self.alice_source  # Transactionnel -> devrait être gardé
        edge_to_tx.target_node = test_node

        test_node.incoming_edges = {
            "non_tx": edge_to_non_tx,
            "tx": edge_to_tx
        }

        # Test: seulement l'arête vers nœud transactionnel devrait être retournée
        edges = self.enumerator._get_edges_for_causal_traversal(test_node, 0)

        self.assertEqual(len(edges), 1, "Filtrage: seulement nœuds transactionnels")
        self.assertEqual(edges[0], edge_to_tx, "Arête vers nœud transactionnel gardée")

    def test_causal_traversal_error_handling(self):
        """Test gestion erreurs dans traversal causal"""
        # Test avec nœud None - devrait retourner liste vide via fallback
        edges = self.enumerator._get_edges_for_causal_traversal(None, 0)
        self.assertEqual(len(edges), 0, "Nœud None -> aucune arête via fallback")

        # Test avec nœud valide mais sans edges
        empty_node = Mock(spec=Node)
        empty_node.node_id = "empty_node"
        empty_node.incoming_edges = {}
        empty_node.outgoing_edges = {}

        edges = self.enumerator._get_edges_for_causal_traversal(empty_node, 0)
        self.assertEqual(len(edges), 0, "Nœud vide -> aucune arête")


class TestCausalDFSIntegration(unittest.TestCase):
    """Tests d'intégration pour optimisation DFS causale"""

    def setUp(self):
        """Configuration intégration avec vrais objets DAG"""
        config = DAGConfiguration(
            max_path_enumeration=50,
            simplex_max_iterations=25
        )

        self.dag = DAG(config)

        # Configuration taxonomie pour éviter collisions
        fixed_mappings = {
            "alice_source": "A",
            "alice_sink": "B",
            "bob_source": "C",
            "bob_sink": "D"
        }

        # Configuration taxonomie pour transaction 0
        self.dag.account_taxonomy.update_taxonomy(fixed_mappings, 0)

    def test_causal_dfs_with_real_transaction(self):
        """Test optimisation causale avec vraie transaction"""
        transaction = Transaction(
            transaction_id="tx_causal_test",
            source_account_id="alice",
            target_account_id="bob",
            amount=Decimal('100'),
            source_measures=[
                TransactionMeasure(
                    measure_id="alice_measure",
                    account_id="alice",
                    primary_regex_pattern="B.*",  # Match alice_sink
                    primary_regex_weight=Decimal('1.0'),
                    acceptable_value=Decimal('500')
                )
            ],
            target_measures=[
                TransactionMeasure(
                    measure_id="bob_measure",
                    account_id="bob",
                    primary_regex_pattern="D.*",  # Match bob_sink
                    primary_regex_weight=Decimal('1.0'),
                    acceptable_value=Decimal('0'),
                    required_value=Decimal('50')
                )
            ]
        )

        # Processus transaction avec optimisation causale
        result = self.dag.add_transaction(transaction)

        # Validation: transaction devrait réussir avec optimisation
        self.assertTrue(result, "Transaction avec optimisation causale devrait réussir")

        # Validation: comptes créés
        self.assertIn("alice", self.dag.accounts)
        self.assertIn("bob", self.dag.accounts)

        # Validation: balances mises à jour
        alice = self.dag.accounts["alice"]
        bob = self.dag.accounts["bob"]
        self.assertEqual(alice.balance.current_balance, Decimal('-100'))
        self.assertEqual(bob.balance.current_balance, Decimal('100'))


if __name__ == '__main__':
    import logging

    # Configuration logging pour debug
    logging.basicConfig(level=logging.DEBUG)

    # Suite complète tests
    suite = unittest.TestSuite()

    # Tests unitaires optimisation causale
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestCausalDFSOptimization))

    # Tests intégration
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestCausalDFSIntegration))

    # Exécution
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Résumé
    print(f"\n" + "="*50)
    print(f"TESTS OPTIMISATION DFS CAUSALE")
    print(f"="*50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.testsRun > 0:
        success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100)
        print(f"Success rate: {success_rate:.1f}%")

    if result.failures:
        print(f"\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")

    if result.errors:
        print(f"\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")

    print(f"\n✅ Tests optimisation DFS causale terminés")