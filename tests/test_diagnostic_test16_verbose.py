"""
Test diagnostique spécifique pour Test 16 avec output verbose
Isole spécifiquement le problème enumerate_and_classify avec taxonomie Test 16
"""

import unittest
from decimal import Decimal
from icgs_core import DAG, DAGConfiguration, Transaction, TransactionMeasure

class TestDiagnosticTest16Verbose(unittest.TestCase):
    """Diagnostic verbose Test 16 avec taxonomie explicite"""
    
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
        
        # Configuration taxonomie identique Test 16
        self._setup_test16_taxonomy()
        
        print(f"\n=== DIAGNOSTIC TEST 16 VERBOSE ===")
    
    def _setup_test16_taxonomy(self):
        """Configuration taxonomie EXACTEMENT comme Test 16"""
        explicit_mappings = {
            # Alice farm
            "alice_farm_source": "N",   # Source = N pour pattern match
            "alice_farm_sink": "A",     # Sink = A (word "AN" ou "NA" contient N)
            
            # Bob factory  
            "bob_factory_source": "B",  # Source = B 
            "bob_factory_sink": "C",    # Sink = C (word "CN" ou "NC" contient N)
            
            # Autres comptes pour éviter erreurs
            "account_alpha_source": "D",
            "account_alpha_sink": "E",
            "account_beta_source": "F", 
            "account_beta_sink": "G",
            "complex_farm_source": "H",
            "complex_farm_sink": "I",
            "alice_source": "J",
            "alice_sink": "K",
            "bob_source": "L",
            "bob_sink": "M", 
            "charlie_source": "O",
            "charlie_sink": "P"
        }
        
        # Configuration pour transaction_num=0 (comme Test 16)
        self.dag.account_taxonomy.update_taxonomy(explicit_mappings, 0)
        print(f"Configured taxonomy for transaction_num=0 with {len(explicit_mappings)} mappings")
        
        # Vérification mappings clés
        alice_source_char = self.dag.account_taxonomy.get_character_mapping("alice_farm_source", 0)
        bob_sink_char = self.dag.account_taxonomy.get_character_mapping("bob_factory_sink", 0)
        print(f"Key mappings: alice_farm_source='{alice_source_char}', bob_factory_sink='{bob_sink_char}'")
    
    def test_enumerate_and_classify_verbose(self):
        """Test enumerate_and_classify avec output détaillé identique Test 16"""
        
        # Transaction EXACTEMENT identique Test 16
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
        print(f"DAG transaction_counter: {self.dag.transaction_counter}")
        
        # ÉTAPE 1: Créer accounts (pas dans enumerate_and_classify mais nécessaire pour edge)
        print(f"\nÉTAPE 1: Création accounts")
        self.dag._extract_accounts_from_transaction(transaction)
        print(f"Accounts créés: {list(self.dag.accounts.keys())}")
        
        # ÉTAPE 2: Créer NFA temporaire (comme dans vrai pipeline)
        print(f"\nÉTAPE 2: Création NFA temporaire")
        temp_nfa = self.dag._create_temporary_nfa_for_transaction(transaction)
        temp_nfa.freeze()
        print(f"NFA frozen avec {len(temp_nfa.get_final_states())} final states")
        
        # ÉTAPE 3: Créer transaction edge
        print(f"\nÉTAPE 3: Création transaction edge")
        transaction_edge = self.dag._create_temporary_transaction_edge(transaction)
        print(f"Edge: {transaction_edge.source_node.node_id} → {transaction_edge.target_node.node_id}")
        
        # ÉTAPE 4: Test enumerate_and_classify avec VERBOSE
        print(f"\nÉTAPE 4: enumerate_and_classify VERBOSE")
        print(f"Input: transaction_edge={transaction_edge.edge_id}, transaction_num={self.dag.transaction_counter}")
        
        # Test path enumeration direct d'abord
        print(f"\nSub-test 4a: Path enumeration direct")
        direct_paths = []
        for path in self.dag.path_enumerator.enumerate_paths_from_transaction(transaction_edge, self.dag.transaction_counter):
            direct_paths.append(path)
            path_str = " → ".join([n.node_id for n in path])
            print(f"  Path direct: {path_str}")
        print(f"Total direct paths: {len(direct_paths)}")
        
        # Test word conversion pour chaque path
        if direct_paths:
            print(f"\nSub-test 4b: Word conversion pour chaque path")
            for i, path in enumerate(direct_paths):
                word = self.dag.path_enumerator._convert_single_path_to_word(path, self.dag.transaction_counter)
                path_str = " → ".join([n.node_id for n in path])
                print(f"  Path {i}: {path_str} → word '{word}'")
                
                # Test pattern matching pour chaque word
                if word:
                    pattern1 = ".*N.*"
                    import re
                    match1 = re.match(pattern1, word)
                    print(f"    Word '{word}' matches '{pattern1}': {match1 is not None}")
        
        # Test enumerate_and_classify complet
        print(f"\nSub-test 4c: enumerate_and_classify complet")
        try:
            result = self.dag.path_enumerator.enumerate_and_classify(transaction_edge, temp_nfa, self.dag.transaction_counter)
            print(f"✅ Result: {len(result)} classes")
            for state_id, paths in result.items():
                print(f"  State '{state_id}': {len(paths)} paths")
                for path in paths:
                    path_str = " → ".join([n.node_id for n in path])
                    print(f"    Path: {path_str}")
        except Exception as e:
            print(f"❌ enumerate_and_classify failed: {e}")
            raise

        # ASSERTIONS pour validation diagnostic Test 16 verbose
        self.assertIsNotNone(transaction_edge, "Transaction edge should be created")
        self.assertIsNotNone(temp_nfa, "Temporary NFA should be created")
        self.assertIsNotNone(result, "enumerate_and_classify should return result")
        self.assertIsInstance(result, dict, "Result should be dictionary")

        # Validation DAG état après diagnostic
        self.assertEqual(len(self.dag.accounts), 2, "Should have 2 accounts after setup")
        self.assertGreaterEqual(len(self.dag.nodes), 4, "Should have at least 4 nodes (source/sink pairs)")

if __name__ == '__main__':
    unittest.main(verbosity=2)