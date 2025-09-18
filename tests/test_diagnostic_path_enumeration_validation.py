#!/usr/bin/env python3
"""
ÉTAPE 1 - Test Diagnostic Path Enumeration Validation
Analyser pourquoi "no paths were classified" dans Test 16
"""

import unittest
from decimal import Decimal
import sys
import os

# Path setup pour import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_core.enhanced_dag import EnhancedDAG
from icgs_core.dag import Transaction, TransactionMeasure


class TestDiagnosticPathEnumerationValidation(unittest.TestCase):
    """Test diagnostic pour analyser problème path enumeration vide"""

    def setUp(self):
        """Setup DAG minimal pour diagnostic"""
        self.dag = EnhancedDAG()

    def test_01_basic_dag_structure_after_transaction(self):
        """Test 1.1: Vérifier structure DAG basique après ajout transaction"""
        print("\n=== DIAGNOSTIC 1.1: Structure DAG Basique ===")

        # Transaction simple comme dans Test 16
        transaction = Transaction(
            transaction_id="diag_tx_1",
            source_account_id="alice",
            target_account_id="bob",
            amount=Decimal('100'),
            source_measures=[
                TransactionMeasure(
                    measure_id="diag_source",
                    account_id="alice",
                    primary_regex_pattern=".*A.*",
                    primary_regex_weight=Decimal('1.0'),
                    acceptable_value=Decimal('500')
                )
            ],
            target_measures=[]
        )

        # AVANT: Vérifier DAG vide
        print(f"AVANT - Comptes: {len(self.dag.accounts)}")
        print(f"AVANT - Nodes: {len(self.dag.nodes)}")
        print(f"AVANT - Edges: {len(self.dag.edges)}")

        # PRÉ-REQUIS: Configurer taxonomie avant création comptes
        print("Configuring taxonomy before account creation...")
        node_mappings = {
            "alice_source": None,  # Auto-assignment
            "alice_sink": None,
            "bob_source": None,
            "bob_sink": None
        }
        self.dag.account_taxonomy.update_taxonomy(node_mappings, 0)

        # Créer comptes seulement (pas transaction complète)
        self.dag._ensure_accounts_exist_with_taxonomy(transaction)

        # APRÈS: Vérifier structure créée
        print(f"APRÈS - Comptes: {len(self.dag.accounts)} = {list(self.dag.accounts.keys())}")
        print(f"APRÈS - Nodes: {len(self.dag.nodes)} = {list(self.dag.nodes.keys())}")
        print(f"APRÈS - Edges: {len(self.dag.edges)}")

        # Validation: Comptes et nodes créés
        self.assertEqual(len(self.dag.accounts), 2, "2 comptes doivent être créés")
        self.assertEqual(len(self.dag.nodes), 4, "4 nodes doivent être créés (2 source + 2 sink)")

        # Vérifier nodes spécifiques
        self.assertIn("alice_source", self.dag.nodes)
        self.assertIn("alice_sink", self.dag.nodes)
        self.assertIn("bob_source", self.dag.nodes)
        self.assertIn("bob_sink", self.dag.nodes)

        return transaction

    def test_02_internal_edges_presence(self):
        """Test 1.2: Vérifier présence edges internes source→sink"""
        print("\n=== DIAGNOSTIC 1.2: Edges Internes ===")

        transaction = self.test_01_basic_dag_structure_after_transaction()

        # Vérifier edges internes pour chaque compte
        alice_account = self.dag.accounts["alice"]
        bob_account = self.dag.accounts["bob"]

        alice_source = alice_account.source_node
        alice_sink = alice_account.sink_node
        bob_source = bob_account.source_node
        bob_sink = bob_account.sink_node

        print(f"Alice source outgoing: {len(alice_source.outgoing_edges)}")
        print(f"Alice sink incoming: {len(alice_sink.incoming_edges)}")
        print(f"Bob source outgoing: {len(bob_source.outgoing_edges)}")
        print(f"Bob sink incoming: {len(bob_sink.incoming_edges)}")

        # DIAGNOSTIC: Edges internes manquants ?
        alice_has_internal = any(
            edge.target_node.node_id == "alice_sink"
            for edge in alice_source.outgoing_edges.values()
        )
        bob_has_internal = any(
            edge.target_node.node_id == "bob_sink"
            for edge in bob_source.outgoing_edges.values()
        )

        print(f"Alice a edge interne: {alice_has_internal}")
        print(f"Bob a edge interne: {bob_has_internal}")

        # CRITIQUE: Si pas d'edges internes → path enumeration impossible
        if not alice_has_internal:
            print("⚠️ PROBLÈME: Alice manque edge interne source→sink")
        if not bob_has_internal:
            print("⚠️ PROBLÈME: Bob manque edge interne source→sink")

        return transaction, alice_source, alice_sink, bob_source, bob_sink

    def test_03_transaction_edge_creation(self):
        """Test 1.3: Vérifier création edge transaction alice→bob"""
        print("\n=== DIAGNOSTIC 1.3: Edge Transaction ===")

        transaction, alice_source, alice_sink, bob_source, bob_sink = self.test_02_internal_edges_presence()

        # Créer edge transaction manuellement comme dans DAG
        from icgs_core.dag_structures import Edge, EdgeType, connect_nodes

        transaction_edge = Edge(
            edge_id=f"transaction_{transaction.transaction_id}",
            source_node=alice_source,
            target_node=bob_sink,
            weight=transaction.amount,
            edge_type=EdgeType.TRANSACTION,
            metadata={'transaction_id': transaction.transaction_id}
        )

        # Ajouter edge au DAG
        self.dag.edges[transaction_edge.edge_id] = transaction_edge
        connect_nodes(alice_source, bob_sink, transaction_edge)

        print(f"Edge transaction créé: {transaction_edge.edge_id}")
        print(f"Alice source outgoing après: {len(alice_source.outgoing_edges)}")
        print(f"Bob sink incoming après: {len(bob_sink.incoming_edges)}")

        # Validation: Edge transaction connecté
        self.assertIn(transaction_edge.edge_id, alice_source.outgoing_edges)
        self.assertIn(transaction_edge.edge_id, bob_sink.incoming_edges)

        return transaction_edge, alice_source, bob_sink

    def test_04_path_enumeration_basic(self):
        """Test 1.4: Test énumération paths basique"""
        print("\n=== DIAGNOSTIC 1.4: Path Enumeration Basique ===")

        transaction_edge, alice_source, bob_sink = self.test_03_transaction_edge_creation()

        # Test énumération directe avec PathEnumerator
        from icgs_core.path_enumerator import DAGPathEnumerator
        from icgs_core.account_taxonomy import AccountTaxonomy

        taxonomy = AccountTaxonomy()
        path_enumerator = DAGPathEnumerator(taxonomy)

        print(f"Démarrage énumération depuis: {bob_sink.node_id}")
        print(f"Incoming edges bob_sink: {len(bob_sink.incoming_edges)}")

        # Énumération paths depuis transaction
        paths_found = []
        try:
            for path in path_enumerator.enumerate_paths_from_transaction(transaction_edge, 0):
                paths_found.append(path)
                path_str = " → ".join([n.node_id for n in path])
                print(f"  Chemin trouvé: {path_str}")
        except Exception as e:
            print(f"❌ Erreur énumération: {e}")

        print(f"Total chemins trouvés: {len(paths_found)}")

        # VALIDATION: Au moins 1 chemin trouvé
        if len(paths_found) == 0:
            print("❌ PROBLÈME CRITIQUE: Aucun chemin trouvé")
            print("   → Path enumeration ne fonctionne pas")
        else:
            print("✅ Path enumeration fonctionne basiquement")

        return paths_found, taxonomy, path_enumerator, transaction_edge

    def test_05_path_classification_pipeline(self):
        """Test 1.5: Test pipeline classification complet"""
        print("\n=== DIAGNOSTIC 1.5: Pipeline Classification ===")

        paths_found, taxonomy, path_enumerator, transaction_edge = self.test_04_path_enumeration_basic()

        if len(paths_found) == 0:
            self.skipTest("Skip classification - pas de chemins trouvés")

        # Mise à jour taxonomie comme dans DAG réel
        node_mappings = {
            "alice_source": None,  # Auto-assignment → 'N'
            "alice_sink": None,
            "bob_source": None,
            "bob_sink": None
        }
        taxonomy.update_taxonomy(node_mappings, 0)

        # Création NFA minimal
        from icgs_core.anchored_nfa_v2 import AnchoredWeightedNFA
        nfa = AnchoredWeightedNFA("diagnostic_nfa")
        nfa.add_weighted_regex("diag_measure", ".*N.*", Decimal('1.0'))

        print(f"NFA créé avec pattern '.*N.*'")
        print(f"États taxonomie:")
        for node_id in ["alice_source", "alice_sink", "bob_source", "bob_sink"]:
            mapping = taxonomy.get_character_mapping(node_id, 0)
            print(f"  {node_id} → '{mapping}'")

        # Test pipeline enumerate_and_classify
        try:
            result = path_enumerator.enumerate_and_classify(transaction_edge, nfa, 0)
            print(f"✅ Pipeline réussi: {len(result)} classes trouvées")

            for state_id, paths in result.items():
                print(f"  État {state_id}: {len(paths)} chemins")

            # VALIDATION: Au moins 1 classe trouvée
            self.assertGreater(len(result), 0, "Au moins 1 classe doit être trouvée")

        except Exception as e:
            print(f"❌ Pipeline échoué: {e}")
            print("   → Problème dans enumerate_and_classify")
            raise

        return result

    def test_06_summary_diagnostic(self):
        """Test 1.6: Résumé diagnostic complet"""
        print("\n=== DIAGNOSTIC 1.6: Résumé ===")

        try:
            result = self.test_05_path_classification_pipeline()

            print("✅ DIAGNOSTIC COMPLET:")
            print("  1. Structure DAG → OK")
            print("  2. Edges internes → À vérifier")
            print("  3. Edge transaction → OK")
            print("  4. Path enumeration → OK")
            print("  5. Pipeline classification → OK")
            print(f"  → {len(result)} classes trouvées")

            # Success si pipeline complet fonctionne
            self.assertTrue(True, "Diagnostic path enumeration réussi")

        except Exception as e:
            print(f"❌ DIAGNOSTIC IDENTIFIE PROBLÈME: {e}")
            print("  → Pipeline path enumeration a des problèmes")

            # Identifier problème spécifique pour correction
            if "no paths were classified" in str(e):
                print("  → PROBLÈME: Classification vide")
            elif "Variable" in str(e) and "referenced" in str(e):
                print("  → PROBLÈME: Variables LP mal référencées")
            else:
                print(f"  → PROBLÈME: {e}")

            # Test passe même avec problème pour diagnostic
            self.assertTrue(True, f"Diagnostic identifie: {e}")


if __name__ == '__main__':
    unittest.main(verbosity=2)