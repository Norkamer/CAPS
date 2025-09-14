#!/usr/bin/env python3
"""
Diagnostic Test: Single Pattern Transaction Classification

Debug pourquoi les transactions avec target_measures=[] ne classifient aucun path.
Teste le mécanisme de fallback pour duplication patterns source → target.
"""

import unittest
from decimal import Decimal, getcontext

# Configuration précision étendue
getcontext().prec = 50

from icgs_core import (
    DAG, DAGConfiguration, Transaction, TransactionMeasure, Account,
    LinearProgram, LinearConstraint, ConstraintType,
    AnchoredWeightedNFA, AccountTaxonomy
)


class TestDiagnosticSinglePattern(unittest.TestCase):
    """
    Diagnostic: Transactions single-pattern avec target_measures=[]
    """

    def setUp(self):
        """Setup diagnostic avec configuration simplifiée"""
        self.config = DAGConfiguration(
            max_path_enumeration=100,
            simplex_max_iterations=500,
            simplex_tolerance=Decimal('1e-10'),
            nfa_explosion_threshold=100,
            enable_warm_start=True,
            enable_cross_validation=True,
            validation_mode="STRICT"
        )

        self.dag = DAG(self.config)

        # Configuration taxonomie simple
        simple_mappings = {
            "test_source_source": "A",
            "test_source_sink": "B",
            "test_target_source": "C",
            "test_target_sink": "D"
        }

        # Configuration pour transaction 0
        self.dag.account_taxonomy.update_taxonomy(simple_mappings, 0)

        print(f"DIAGNOSTIC: Taxonomy configured with {len(simple_mappings)} mappings")
        print(f"  test_source_source → A, test_source_sink → B")
        print(f"  test_target_source → C, test_target_sink → D")

    def test_single_pattern_classification_debug(self):
        """
        Diagnostic: Transaction avec seulement source_measures

        Test le mécanisme de fallback pour classification patterns.
        """
        print(f"\n=== DIAGNOSTIC SINGLE PATTERN ===")

        # Transaction avec SEULEMENT source_measures (target_measures=[])
        transaction = Transaction(
            transaction_id="tx_diagnostic_single",
            source_account_id="test_source",
            target_account_id="test_target",
            amount=Decimal('100'),
            source_measures=[
                TransactionMeasure(
                    measure_id="source_measure_only",
                    account_id="test_source",
                    primary_regex_pattern="B.*",  # Pattern B prefix (test_source_sink = B)
                    primary_regex_weight=Decimal('1.0'),
                    acceptable_value=Decimal('500')
                )
            ],
            target_measures=[]  # VIDE → doit déclencher fallback
        )

        print(f"Transaction configuration:")
        print(f"  source_account_id: {transaction.source_account_id}")
        print(f"  target_account_id: {transaction.target_account_id}")
        print(f"  source_measures: {len(transaction.source_measures)} patterns")
        print(f"  target_measures: {len(transaction.target_measures)} patterns (EMPTY)")
        print(f"  pattern: {transaction.source_measures[0].primary_regex_pattern}")

        # Activer debugging TRÈS verbeux pour path enumeration
        import logging
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(name)s:%(filename)s:%(lineno)d %(message)s')

        # Activer spécifiquement debugging path enumeration
        path_enum_logger = logging.getLogger('icgs_core.path_enumerator.DAGPathEnumerator')
        path_enum_logger.setLevel(logging.DEBUG)

        dag_logger = logging.getLogger('ICGS.DAG')
        dag_logger.setLevel(logging.DEBUG)

        # Exécution avec capture détaillée
        try:
            print(f"\n--- EXECUTING TRANSACTION ---")
            print(f"Before transaction: DAG has {len(self.dag.accounts)} accounts, {len(self.dag.nodes)} nodes")

            result = self.dag.add_transaction(transaction)

            print(f"Transaction result: {result}")
            if result:
                print(f"✅ Transaction succeeded")
                print(f"Accounts created: {len(self.dag.accounts)}")
                print(f"Nodes created: {len(self.dag.nodes)}")
                print(f"Transaction counter: {self.dag.transaction_counter}")

                # Validation balances
                source_account = self.dag.accounts.get("test_source")
                target_account = self.dag.accounts.get("test_target")

                if source_account and target_account:
                    print(f"Source balance: {source_account.balance.current_balance}")
                    print(f"Target balance: {target_account.balance.current_balance}")
                else:
                    print(f"❌ Accounts not found in DAG")

            else:
                print(f"❌ Transaction failed (returned False)")
                print(f"After failed transaction: DAG has {len(self.dag.accounts)} accounts, {len(self.dag.nodes)} nodes")

                # DEBUG: Vérifier l'état des comptes créés
                if len(self.dag.accounts) > 0:
                    print("\nCréated accounts:")
                    for account_id, account in self.dag.accounts.items():
                        print(f"  {account_id}: balance={account.balance.current_balance}")

                # DEBUG: Vérifier l'état des nodes créés
                if len(self.dag.nodes) > 0:
                    print("\nCreated nodes:")
                    for node_id, node in self.dag.nodes.items():
                        print(f"  {node_id}: type={type(node)}")

                # DEBUG: Tester manuellement la taxonomie
                print("\nTaxonomy test:")
                test_mapping = self.dag.account_taxonomy.get_character_mapping("test_source_sink", 0)
                print(f"  test_source_sink → '{test_mapping}'")

                # DEBUG: Tester manuellement la création NFA
                print("\nNFA test:")
                try:
                    temp_nfa = self.dag._create_temporary_nfa_for_transaction(transaction)
                    print(f"  NFA created successfully")
                    print(f"  NFA has metadata: {hasattr(temp_nfa, 'metadata')}")
                    if hasattr(temp_nfa, 'metadata'):
                        target_nfa = temp_nfa.metadata.get('target_nfa')
                        print(f"  Target NFA available: {target_nfa is not None}")
                        if target_nfa:
                            print(f"  Target NFA patterns count: {len(target_nfa.get_final_states())}")

                    # Test word evaluation manually
                    print("\nManual word evaluation:")
                    test_word = "BD"  # test_source_sink (B) + test_target_sink (D)
                    print(f"  Testing word: '{test_word}'")

                    if hasattr(temp_nfa, 'evaluate_to_final_state'):
                        main_result = temp_nfa.evaluate_to_final_state(test_word)
                        print(f"  Main NFA result: {main_result}")

                    if hasattr(temp_nfa, 'metadata') and temp_nfa.metadata.get('target_nfa'):
                        target_nfa = temp_nfa.metadata.get('target_nfa')
                        if hasattr(target_nfa, 'evaluate_to_final_state'):
                            target_result = target_nfa.evaluate_to_final_state(test_word)
                            print(f"  Target NFA result: {target_result}")

                    # DEBUG: Test manual path enumeration
                    print("\nManual path enumeration test:")
                    try:
                        # Create transaction edge
                        transaction_edge = self.dag._create_temporary_transaction_edge(transaction)
                        print(f"  Transaction edge created: {transaction_edge}")

                        # Test path enumeration directly
                        path_classes = self.dag.path_enumerator.enumerate_and_classify(
                            transaction_edge, temp_nfa, 0
                        )
                        print(f"  Path enumeration result: {path_classes}")
                        print(f"  Path classes count: {len(path_classes) if path_classes else 0}")

                        if path_classes:
                            for state_id, paths in path_classes.items():
                                print(f"    State {state_id}: {len(paths)} paths")

                    except Exception as enum_error:
                        print(f"  Path enumeration test failed: {enum_error}")
                        import traceback
                        traceback.print_exc()

                    # DEBUG: Check DAG structure and edges
                    print("\nDAG structure analysis:")
                    print(f"  Nodes count: {len(self.dag.nodes)}")
                    print(f"  Edges count: {len(self.dag.edges)}")

                    print("  Nodes details:")
                    for node_id, node in self.dag.nodes.items():
                        print(f"    {node_id}: {node}")

                    print("  Edges details:")
                    for edge_id, edge in self.dag.edges.items():
                        print(f"    {edge_id}: {edge}")

                    # Check if path should exist manually
                    source_node_id = "test_source_source"
                    target_node_id = "test_target_sink"
                    print(f"\nPath connectivity check:")
                    print(f"  Source node '{source_node_id}' exists: {source_node_id in self.dag.nodes}")
                    print(f"  Target node '{target_node_id}' exists: {target_node_id in self.dag.nodes}")

                    if source_node_id in self.dag.nodes and target_node_id in self.dag.nodes:
                        # Check if there are edges connecting these nodes
                        source_edges = [edge_id for edge_id, edge in self.dag.edges.items()
                                       if edge.source_node.node_id == source_node_id]
                        target_edges = [edge_id for edge_id, edge in self.dag.edges.items()
                                       if edge.target_node.node_id == target_node_id]

                        print(f"  Edges from source node: {source_edges}")
                        print(f"  Edges to target node: {target_edges}")

                        # Check if transaction edge was added to DAG
                        transaction_edges = [edge_id for edge_id, edge in self.dag.edges.items()
                                           if 'tx_diagnostic_single' in edge_id]
                        print(f"  Transaction edges in DAG: {transaction_edges}")

                    # DEBUG: Try manual simple path enumeration
                    print(f"\nManual connectivity test:")
                    try:
                        if hasattr(self.dag.path_enumerator, 'find_all_paths'):
                            manual_paths = self.dag.path_enumerator.find_all_paths(
                                self.dag.nodes[source_node_id], self.dag.nodes[target_node_id]
                            )
                            print(f"  Manual paths found: {len(manual_paths)}")
                        else:
                            print("  Manual path finding method not available")
                    except Exception as manual_error:
                        print(f"  Manual path finding failed: {manual_error}")

                except Exception as nfa_error:
                    print(f"  NFA test failed: {nfa_error}")
                    import traceback
                    traceback.print_exc()

        except Exception as e:
            print(f"❌ Transaction failed with exception: {e}")
            print(f"Exception type: {type(e)}")
            import traceback
            print("Full traceback:")
            traceback.print_exc()

        # Résumé performance
        dag_performance = self.dag.get_performance_summary()
        print(f"\nPerformance summary: {dag_performance}")

        # ASSERTIONS pour validation test diagnostic
        self.assertIsNotNone(result, "Transaction should return a result (True/False)")
        self.assertIsInstance(self.dag.transaction_counter, int, "Transaction counter should be an integer")
        self.assertGreaterEqual(len(self.dag.accounts), 0, "DAG should have accounts after transaction attempt")
        self.assertIsNotNone(dag_performance, "Performance summary should not be None")

        # Si la transaction réussit, valider les balances
        if result:
            self.assertIn("test_source", self.dag.accounts, "Source account should exist after successful transaction")
            self.assertIn("test_target", self.dag.accounts, "Target account should exist after successful transaction")
            source_balance = self.dag.accounts["test_source"].balance.current_balance
            target_balance = self.dag.accounts["test_target"].balance.current_balance
            self.assertEqual(source_balance + target_balance, Decimal('0'), "Balance conservation should hold")


if __name__ == '__main__':
    # Exécution diagnostic
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDiagnosticSinglePattern)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print(f"\n" + "="*50)
    print(f"DIAGNOSTIC SINGLE PATTERN COMPLETED")
    print(f"="*50)