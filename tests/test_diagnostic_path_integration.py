"""
Test diagnostique pour Phase 2.9 - Intégration Path-NFA
Test unitaire pour identifier problème énumération path exacte
"""

import unittest
from decimal import Decimal
from icgs_core import DAG, Transaction, TransactionMeasure, AccountTaxonomy
from icgs_core.path_enumerator import DAGPathEnumerator


class TestDiagnosticPathIntegration(unittest.TestCase):
    """Tests diagnostiques Path-NFA Integration"""
    
    def setUp(self):
        """Setup DAG minimal pour diagnostic"""
        self.dag = DAG()
        self.taxonomy = AccountTaxonomy()
        self.path_enumerator = DAGPathEnumerator(self.taxonomy)
    
    def test_simple_transaction_dag_structure(self):
        """Test 1: Vérification structure DAG après transaction simple"""
        print("\n=== DIAGNOSTIC 1: Structure DAG ===")
        
        # Transaction simple
        transaction = Transaction(
            transaction_id="diagnostic_tx_1",
            source_account_id="alice",
            target_account_id="bob",
            amount=Decimal('100'),
            source_measures=[
                TransactionMeasure(
                    measure_id="diag_measure",
                    account_id="alice",
                    primary_regex_pattern=".*A.*",  # Comme Test 16
                    primary_regex_weight=Decimal('1.0'),
                    acceptable_value=Decimal('500')
                )
            ],
            target_measures=[]
        )
        
        # AVANT transaction : Vérifier DAG vide
        print(f"Avant transaction:")
        print(f"  Comptes: {len(self.dag.accounts)}")
        print(f"  Nodes: {len(self.dag.nodes)}")
        print(f"  Edges: {len(self.dag.edges)}")
        
        # ÉTAPE 1: Création comptes seulement
        self.dag._ensure_accounts_exist_with_taxonomy(transaction)
        
        print(f"Après création comptes:")
        print(f"  Comptes: {len(self.dag.accounts)} = {list(self.dag.accounts.keys())}")
        print(f"  Nodes: {len(self.dag.nodes)} = {list(self.dag.nodes.keys())}")
        print(f"  Edges: {len(self.dag.edges)}")
        
        # Vérifier nodes créés
        alice_source = self.dag.nodes.get("alice_source")
        alice_sink = self.dag.nodes.get("alice_sink")
        bob_source = self.dag.nodes.get("bob_source")
        bob_sink = self.dag.nodes.get("bob_sink")
        
        self.assertIsNotNone(alice_source, "alice_source node missing")
        self.assertIsNotNone(alice_sink, "alice_sink node missing")
        self.assertIsNotNone(bob_source, "bob_source node missing")
        self.assertIsNotNone(bob_sink, "bob_sink node missing")
        
        print(f"  alice_source edges: in={len(alice_source.incoming_edges)}, out={len(alice_source.outgoing_edges)}")
        print(f"  alice_sink edges: in={len(alice_sink.incoming_edges)}, out={len(alice_sink.outgoing_edges)}")
        print(f"  bob_source edges: in={len(bob_source.incoming_edges)}, out={len(bob_source.outgoing_edges)}")
        print(f"  bob_sink edges: in={len(bob_sink.incoming_edges)}, out={len(bob_sink.outgoing_edges)}")
        
        # ÉTAPE 2: Ajout transaction edge manuellement
        source_account = self.dag.accounts["alice"]
        target_account = self.dag.accounts["bob"]
        
        from icgs_core.dag_structures import Edge, EdgeType, connect_nodes
        import time
        
        transaction_edge = Edge(
            edge_id=f"transaction_{transaction.transaction_id}",
            source_node=source_account.source_node,
            target_node=target_account.sink_node,
            weight=transaction.amount,
            edge_type=EdgeType.TRANSACTION,
            metadata={'transaction_id': transaction.transaction_id}
        )
        
        # Ajout edge au DAG
        self.dag.edges[transaction_edge.edge_id] = transaction_edge
        connect_nodes(source_account.source_node, target_account.sink_node, transaction_edge)
        
        print(f"Après création edge:")
        print(f"  Edges: {len(self.dag.edges)} = {list(self.dag.edges.keys())}")
        print(f"  alice_source edges: in={len(alice_source.incoming_edges)}, out={len(alice_source.outgoing_edges)}")
        print(f"  bob_sink edges: in={len(bob_sink.incoming_edges)}, out={len(bob_sink.outgoing_edges)}")
        
        # Validation edge correctement connecté
        self.assertEqual(len(alice_source.outgoing_edges), 1)
        self.assertEqual(len(bob_sink.incoming_edges), 1)
        
        edge_in_bob = list(bob_sink.incoming_edges.values())[0]
        print(f"  Edge dans bob_sink: {edge_in_bob.edge_id}")
        print(f"  Edge source: {edge_in_bob.source_node.node_id}")
        print(f"  Edge target: {edge_in_bob.target_node.node_id}")
        
        return transaction_edge, alice_source, bob_sink
    
    def test_path_enumeration_direct(self):
        """Test 2: Énumération directe avec structure DAG valide"""
        print("\n=== DIAGNOSTIC 2: Énumération Path ===")
        
        transaction_edge, alice_source, bob_sink = self.test_simple_transaction_dag_structure()
        
        # Test énumération directe
        print(f"Début énumération depuis: {bob_sink.node_id}")
        print(f"Incoming edges de {bob_sink.node_id}: {len(bob_sink.incoming_edges)}")
        
        paths_found = []
        for path in self.path_enumerator.enumerate_paths_from_transaction(transaction_edge, 0):
            paths_found.append(path)
            path_str = " -> ".join([n.node_id for n in path])
            print(f"  Chemin trouvé: {path_str}")
        
        print(f"Total chemins trouvés: {len(paths_found)}")
        
        # Validation : devrait trouver au moins 1 chemin
        self.assertGreater(len(paths_found), 0, "Aucun chemin trouvé par énumération")
        
        # Le chemin devrait être : bob_sink -> alice_source  
        expected_path = [bob_sink, alice_source]
        if paths_found:
            actual_path = paths_found[0]
            print(f"Premier chemin: {[n.node_id for n in actual_path]}")
            print(f"Attendu: {[n.node_id for n in expected_path]}")
        
        return paths_found
    
    def test_full_enumerate_and_classify(self):
        """Test 3: Pipeline complet enumerate_and_classify"""
        print("\n=== DIAGNOSTIC 3: Pipeline Complet ===")
        
        transaction_edge, alice_source, bob_sink = self.test_simple_transaction_dag_structure()
        
        # Mise à jour taxonomie comme dans le vrai DAG
        node_mappings = {
            "alice_source": None,  # Auto-assignment → 'N'
            "alice_sink": None,
            "bob_source": None,
            "bob_sink": None
        }
        
        self.taxonomy.update_taxonomy(node_mappings, 0)
        print(f"Taxonomie mise à jour avec {len(node_mappings)} node mappings")
        
        # Création NFA minimal avec pattern adapté pour caractères neutres
        from icgs_core import AnchoredWeightedNFA
        nfa = AnchoredWeightedNFA("diagnostic_nfa")
        # Pattern qui matche les caractères neutres 'N' générés par auto-assignment
        nfa.add_weighted_regex("diag_measure", ".*N.*", Decimal('1.0'))
        
        print(f"NFA créé avec {len(nfa.states)} états")
        
        # Test pipeline complet avec diagnostic détaillé
        print(f"État taxonomie avant pipeline:")
        for node_id in ["alice_source", "alice_sink", "bob_source", "bob_sink"]:
            mapping = self.taxonomy.get_character_mapping(node_id, 0)
            print(f"  {node_id} → '{mapping}'")
        
        try:
            result = self.path_enumerator.enumerate_and_classify(transaction_edge, nfa, 0)
            print(f"Pipeline réussi: {len(result)} classes trouvées")
            for state_id, paths in result.items():
                print(f"  État {state_id}: {len(paths)} chemins")
        except Exception as e:
            print(f"Pipeline échoué: {e}")
            raise
        
        return result


if __name__ == '__main__':
    unittest.main(verbosity=2)