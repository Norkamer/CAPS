"""
Test diagnostique spécifique pour Test 16 - Debug pipeline complet
Reproduction exacte des étapes Test 16 avec logging détaillé pour identifier problème
"""

import unittest
from decimal import Decimal
from icgs_core import DAG, DAGConfiguration, Transaction, TransactionMeasure

class TestDiagnosticPipeline16(unittest.TestCase):
    """Diagnostic détaillé pipeline Test 16"""
    
    def setUp(self):
        """Setup identique Test 16"""
        self.config = DAGConfiguration(
            max_path_enumeration=1000,
            simplex_max_iterations=500,
            simplex_tolerance=Decimal('1e-10'),
            nfa_explosion_threshold=100,
            enable_warm_start=True,
            enable_cross_validation=True,
            validation_mode="STRICT"
        )
        self.dag = DAG(self.config)
        print(f"\n=== DIAGNOSTIC PIPELINE 16 ===")
        print(f"DAG créé avec config: {self.config.validation_mode}")
    
    def test_pipeline_step_by_step(self):
        """Debug étape par étape du pipeline add_transaction()"""
        
        # ÉTAPE 1: Création transaction identique Test 16
        source_measure = TransactionMeasure(
            measure_id="agriculture_debit",
            account_id="alice_farm",
            primary_regex_pattern=".*N.*",
            primary_regex_weight=Decimal('1.2'),
            acceptable_value=Decimal('1000'),
            secondary_patterns=[]
        )
        
        target_measure = TransactionMeasure(
            measure_id="industry_credit", 
            account_id="bob_factory",
            primary_regex_pattern=".*N.*",
            primary_regex_weight=Decimal('0.9'),
            acceptable_value=Decimal('0'),
            required_value=Decimal('100'),
            secondary_patterns=[]
        )
        
        transaction = Transaction(
            transaction_id="tx_agriculture_to_industry_001",
            source_account_id="alice_farm",
            target_account_id="bob_factory", 
            amount=Decimal('150'),
            source_measures=[source_measure],
            target_measures=[target_measure]
        )
        
        print(f"\nTransaction créée: {transaction.transaction_id}")
        print(f"  Source: {transaction.source_account_id} → Target: {transaction.target_account_id}")
        print(f"  Amount: {transaction.amount}")
        print(f"  Source measures: {len(transaction.source_measures)}")
        print(f"  Target measures: {len(transaction.target_measures)}")
        
        # ÉTAPE 2: État DAG avant transaction
        print(f"\nÉtat DAG AVANT transaction:")
        print(f"  Accounts: {len(self.dag.accounts)}")
        print(f"  Nodes: {len(self.dag.nodes)}")
        print(f"  Edges: {len(self.dag.edges)}")
        print(f"  Transaction counter: {self.dag.transaction_counter}")
        
        # ÉTAPE 3: Test méthode ensure_accounts_exist
        print(f"\nÉTAPE 3: Test _ensure_accounts_exist_with_taxonomy")
        try:
            self.dag._ensure_accounts_exist_with_taxonomy(transaction)
            print(f"✅ Accounts created successfully")
        except Exception as e:
            print(f"❌ Accounts creation failed: {e}")
            raise
        
        print(f"État DAG APRÈS création accounts:")
        print(f"  Accounts: {len(self.dag.accounts)} = {list(self.dag.accounts.keys())}")
        print(f"  Nodes: {len(self.dag.nodes)} = {list(self.dag.nodes.keys())}")
        print(f"  Edges: {len(self.dag.edges)}")
        
        # Validation accounts créés
        alice = self.dag.accounts.get("alice_farm")
        bob = self.dag.accounts.get("bob_factory")
        
        if alice and bob:
            print(f"  Alice nodes: source={alice.source_node.node_id}, sink={alice.sink_node.node_id}")
            print(f"  Bob nodes: source={bob.source_node.node_id}, sink={bob.sink_node.node_id}")
        
        # ÉTAPE 4: Test création transaction edge
        print(f"\nÉTAPE 4: Test création transaction edge")
        
        if alice and bob:
            from icgs_core.dag_structures import Edge, EdgeType, connect_nodes
            
            transaction_edge = Edge(
                edge_id=f"transaction_{transaction.transaction_id}",
                source_node=alice.source_node,
                target_node=bob.sink_node,
                weight=transaction.amount,
                edge_type=EdgeType.TRANSACTION,
                metadata={'transaction_id': transaction.transaction_id}
            )
            
            # Ajout edge au DAG
            self.dag.edges[transaction_edge.edge_id] = transaction_edge
            connect_nodes(alice.source_node, bob.sink_node, transaction_edge)
            
            print(f"✅ Transaction edge créé: {transaction_edge.edge_id}")
            print(f"  Source: {alice.source_node.node_id}")
            print(f"  Target: {bob.sink_node.node_id}")
            print(f"  Weight: {transaction_edge.weight}")
            
            print(f"État DAG APRÈS création edge:")
            print(f"  Edges: {len(self.dag.edges)} = {list(self.dag.edges.keys())}")
            print(f"  alice_source outgoing: {len(alice.source_node.outgoing_edges)}")
            print(f"  bob_sink incoming: {len(bob.sink_node.incoming_edges)}")
        
        # ÉTAPE 5: Test path enumeration directe
        print(f"\nÉTAPE 5: Test path enumeration directe")
        
        if alice and bob and transaction_edge:
            paths_found = []
            try:
                for path in self.dag.path_enumerator.enumerate_paths_from_transaction(transaction_edge, 0):
                    paths_found.append(path)
                    path_str = " → ".join([n.node_id for n in path])
                    print(f"  ✅ Chemin trouvé: {path_str}")
                
                print(f"Total paths trouvés: {len(paths_found)}")
                
                if not paths_found:
                    print(f"❌ PROBLÈME: Aucun chemin trouvé par énumération")
                    print(f"Debug edge connections:")
                    print(f"  transaction_edge source: {transaction_edge.source_node.node_id}")
                    print(f"  transaction_edge target: {transaction_edge.target_node.node_id}")
                    print(f"  bob_sink incoming edges: {list(bob.sink_node.incoming_edges.keys())}")
                    
            except Exception as e:
                print(f"❌ Path enumeration failed: {e}")
                
        # ÉTAPE 6: Test taxonomie state
        print(f"\nÉTAPE 6: État taxonomie")
        if alice and bob:
            for node_id in [alice.source_node.node_id, alice.sink_node.node_id, 
                           bob.source_node.node_id, bob.sink_node.node_id]:
                try:
                    mapping = self.dag.account_taxonomy.get_character_mapping(node_id, 0)
                    print(f"  {node_id} → '{mapping}'")
                except Exception as e:
                    print(f"  {node_id} → ERROR: {e}")
        
        # ÉTAPE 7: Test word generation depuis path trouvé
        print(f"\nÉTAPE 7: Test word generation")
        if paths_found:
            path = paths_found[0]
            try:
                word = self.dag.path_enumerator._convert_single_path_to_word(path, 0)
                print(f"  Path: {' → '.join([n.node_id for n in path])}")
                print(f"  Word: '{word}'")
                if word:
                    print(f"  Word matches '.*N.*': {'N' in word}")
                    
                    # Test pattern matching explicite
                    import re
                    pattern = ".*N.*"
                    matches = re.match(pattern, word)
                    print(f"  Regex match result: {matches is not None}")
                else:
                    print(f"  ❌ Word est None")
                
            except Exception as e:
                print(f"  ❌ Word generation failed: {e}")
        
        # ÉTAPE 8: Test enumerate_and_classify pipeline complet
        print(f"\nÉTAPE 8: Test enumerate_and_classify")
        if alice and bob and transaction_edge:
            try:
                # Création NFA temporaire comme dans le vrai pipeline
                from icgs_core import AnchoredWeightedNFA
                temp_nfa = AnchoredWeightedNFA(f"temp_{transaction.transaction_id}")
                
                # Ajout patterns source et target measures
                temp_nfa.add_weighted_regex(
                    "agriculture_debit", 
                    source_measure.primary_regex_pattern, 
                    source_measure.primary_regex_weight
                )
                temp_nfa.add_weighted_regex(
                    "industry_credit",
                    target_measure.primary_regex_pattern,
                    target_measure.primary_regex_weight
                )
                
                print(f"  NFA temporaire créé avec patterns:")
                print(f"    agriculture_debit: '{source_measure.primary_regex_pattern}' (weight: {source_measure.primary_regex_weight})")
                print(f"    industry_credit: '{target_measure.primary_regex_pattern}' (weight: {target_measure.primary_regex_weight})")
                
                # Test enumerate_and_classify
                result = self.dag.path_enumerator.enumerate_and_classify(transaction_edge, temp_nfa, 0)
                print(f"  ✅ enumerate_and_classify réussi: {len(result)} classes")
                for state_id, paths in result.items():
                    print(f"    État {state_id}: {len(paths)} chemins")
                    
                if not result:
                    print(f"  ❌ PROBLÈME: enumerate_and_classify retourne résultat vide")
                    
            except Exception as e:
                print(f"  ❌ enumerate_and_classify failed: {e}")

if __name__ == '__main__':
    unittest.main(verbosity=2)