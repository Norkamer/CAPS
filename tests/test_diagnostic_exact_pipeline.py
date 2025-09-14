"""
Test diagnostique reproduisant EXACTEMENT l'ordre du pipeline DAG.add_transaction()
Pour identifier le problème précis dans la séquence d'opérations
"""

import unittest
from decimal import Decimal
from icgs_core import DAG, DAGConfiguration, Transaction, TransactionMeasure

class TestDiagnosticExactPipeline(unittest.TestCase):
    """Diagnostic reproduisant exactement l'ordre add_transaction()"""
    
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
        print(f"\n=== DIAGNOSTIC EXACT PIPELINE ===")
    
    def test_exact_add_transaction_sequence(self):
        """Reproduction EXACTE de la séquence add_transaction()"""
        
        # Transaction identique Test 16
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
        
        print(f"\nTransaction: {transaction.transaction_id}")
        print(f"Transaction counter AVANT: {self.dag.transaction_counter}")
        
        # SÉQUENCE EXACTE add_transaction() ÉTAPE PAR ÉTAPE
        
        # ÉTAPE 1: _extract_accounts_from_transaction() 
        print(f"\nÉTAPE 1: _extract_accounts_from_transaction()")
        try:
            new_accounts = self.dag._extract_accounts_from_transaction(transaction)
            print(f"✅ Accounts extraits: {list(new_accounts.keys())}")
            print(f"  DAG accounts: {list(self.dag.accounts.keys())}")
            print(f"  DAG nodes: {list(self.dag.nodes.keys())}")
        except Exception as e:
            print(f"❌ Failed: {e}")
            raise
        
        # ÉTAPE 2: _create_temporary_nfa_for_transaction()
        print(f"\nÉTAPE 2: _create_temporary_nfa_for_transaction()")
        try:
            temp_nfa = self.dag._create_temporary_nfa_for_transaction(transaction)
            temp_nfa.freeze()
            print(f"✅ NFA temporaire créé et frozen avec {len(temp_nfa.get_final_states())} final states")
        except Exception as e:
            print(f"❌ Failed: {e}")
            raise
        
        # ÉTAPE 3: _create_temporary_transaction_edge()
        print(f"\nÉTAPE 3: _create_temporary_transaction_edge()")
        try:
            transaction_edge = self.dag._create_temporary_transaction_edge(transaction)
            print(f"✅ Transaction edge créé: {transaction_edge.edge_id}")
            print(f"  Source: {transaction_edge.source_node.node_id}")
            print(f"  Target: {transaction_edge.target_node.node_id}")
            print(f"  Weight: {transaction_edge.weight}")
            print(f"  Type: {getattr(transaction_edge, 'edge_type', 'UNKNOWN')}")
        except Exception as e:
            print(f"❌ Failed: {e}")
            raise
        
        # ÉTAPE 4: enumerate_and_classify() EXACTEMENT comme pipeline
        print(f"\nÉTAPE 4: enumerate_and_classify() avec transaction_counter={self.dag.transaction_counter}")
        try:
            path_classes = self.dag.path_enumerator.enumerate_and_classify(
                transaction_edge, temp_nfa, self.dag.transaction_counter
            )
            print(f"✅ enumerate_and_classify réussi: {len(path_classes)} classes")
            for state_id, paths in path_classes.items():
                print(f"    État {state_id}: {len(paths)} chemins")
                
            if not path_classes:
                print(f"❌ PROBLÈME: enumerate_and_classify retourne résultat vide")
                
                # DEBUG: État taxonomie au moment de l'enumeration
                print(f"\nDEBUG: État taxonomie transaction_num={self.dag.transaction_counter}")
                for node_id in self.dag.nodes:
                    try:
                        mapping = self.dag.account_taxonomy.get_character_mapping(node_id, self.dag.transaction_counter)
                        print(f"  {node_id} → '{mapping}'")
                    except Exception as e:
                        print(f"  {node_id} → ERROR: {e}")
                
                # DEBUG: Test énumération directe
                print(f"\nDEBUG: Test énumération directe depuis transaction edge")
                direct_paths = []
                for path in self.dag.path_enumerator.enumerate_paths_from_transaction(transaction_edge, self.dag.transaction_counter):
                    direct_paths.append(path)
                    path_str = " → ".join([n.node_id for n in path])
                    print(f"  Chemin direct: {path_str}")
                print(f"  Total chemins directs: {len(direct_paths)}")
                
        except Exception as e:
            print(f"❌ enumerate_and_classify failed: {e}")
            raise

if __name__ == '__main__':
    unittest.main(verbosity=2)