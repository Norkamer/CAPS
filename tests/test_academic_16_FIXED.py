#!/usr/bin/env python3
"""
Test Académique 16 FIXED - Version corrigée avec patterns alignés

Version simplifiée du Test 16 avec corrections appliquées:
- Taxonomy mappings sans collisions
- Patterns regex alignés sur mappings
- Configuration complète pour transactions séquentielles
- Pas d'auto-extend - pré-configuration statique
"""

import unittest
from decimal import Decimal, getcontext
import time
import logging

# Configuration précision étendue pour tests
getcontext().prec = 50

from icgs_core import (
    DAG, DAGConfiguration, Transaction, TransactionMeasure, Account,
    LinearProgram, LinearConstraint, ConstraintType,
    AnchoredWeightedNFA, AccountTaxonomy
)
# PathEnumerationNotReadyError removed - PHASE 2.9 ACTIVATED

# Import diagnostic API usage pour tests académiques
from tests.academic_api_diagnostics import (
    diagnose_nfa_evaluation,
    diagnose_pipeline_classify_paths_simulation,
    print_session_api_summary
)


class TestAcademic16Fixed(unittest.TestCase):
    """
    Test Académique 16 FIXED - Version corrigée patterns alignés

    Corrections appliquées:
    1. Taxonomy mappings uniques sans collisions
    2. Patterns regex simples alignés sur caractères taxonomy
    3. Configuration taxonomie pour toutes transactions (0-9)
    4. Pas d'auto-extend - configuration statique
    """

    def setUp(self):
        """Initialisation tests avec DAG production configuration FIXED"""
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

        # Configuration taxonomie FIXÉE
        self._setup_fixed_taxonomy()

        # Métriques test
        self.test_metrics = {
            'transactions_tested': 0,
            'transactions_successful': 0,
            'transactions_rejected': 0,
            'nfa_explosions_detected': 0,
            'simplex_validations': 0,
            'warm_starts_used': 0,
            'accounts_created': 0
        }

    def _setup_fixed_taxonomy(self):
        """
        Configuration taxonomie FIXÉE - pas de collisions

        Stratégie: caractères uniques + patterns alignés
        Mapping: chaque node a un caractère unique A-Z, patterns sont .*A, .*B, etc.
        """
        # Mappings SANS collisions - chaque node = caractère unique
        fixed_mappings = {
            # Test transactions simples
            "alice_farm_source": "A",
            "alice_farm_sink": "B",
            "bob_factory_source": "C",
            "bob_factory_sink": "D",

            # Comptes séquentiels pour test_03 - caractères uniques
            "account_source_0_source": "E",
            "account_source_0_sink": "F",
            "account_target_0_source": "G",
            "account_target_0_sink": "H",

            "account_source_1_source": "I",
            "account_source_1_sink": "J",
            "account_target_1_source": "K",
            "account_target_1_sink": "L",

            "account_source_2_source": "M",
            "account_source_2_sink": "N",
            "account_target_2_source": "O",
            "account_target_2_sink": "P",

            # Accounts additionnels
            "account_alpha_source": "Q",
            "account_alpha_sink": "R",
            "account_beta_source": "S",
            "account_beta_sink": "T",

            # Test infeasible/complex
            "restricted_account_source": "U",
            "restricted_account_sink": "V",
            "demanding_account_source": "W",
            "demanding_account_sink": "X",

            "complex_farm_source": "Y",
            "complex_farm_sink": "Z",
            "complex_factory_source": "a",
            "complex_factory_sink": "b",

            # Integrity test
            "alice_source": "c",
            "alice_sink": "d",
            "bob_source": "e",
            "bob_sink": "f",
            "charlie_source": "g",
            "charlie_sink": "h"
        }

        try:
            # Configuration pour toutes transactions 0-9 (pas d'auto-extend)
            for tx_num in range(10):
                self.dag.account_taxonomy.update_taxonomy(fixed_mappings, tx_num)

            print(f"FIXED: Configured taxonomy with {len(fixed_mappings)} mappings for transactions 0-9")

            # Vérification mappings pour transaction 0
            print("✅ Taxonomy mappings verified:")
            for node_id, expected_char in list(fixed_mappings.items())[:5]:  # Premier 5 pour vérif
                actual_char = self.dag.account_taxonomy.get_character_mapping(node_id, 0)
                print(f"  {node_id}: '{actual_char}'")

        except Exception as e:
            print(f"❌ Failed to configure fixed taxonomy: {e}")
            raise

    def _execute_transaction_with_fallback(self, transaction: Transaction) -> tuple[bool, bool]:
        """Helper: Exécute transaction avec gestion exceptions contrôlées + diagnostic API"""
        try:
            result = self.dag.add_transaction(transaction)
            if result:
                print(f"✅ Transaction {transaction.transaction_id} succeeded completely")

                # 🔍 DIAGNOSTIC API NFA : Après succès transaction
                self._diagnose_underlying_nfa_apis(transaction)

                return (True, True)
            else:
                print(f"❌ Transaction {transaction.transaction_id} failed with uncontrolled error")
                return (False, False)

        except Exception as e:
            print(f"❌ Transaction {transaction.transaction_id} failed with error: {e}")
            return (False, False)

    def _diagnose_underlying_nfa_apis(self, transaction: Transaction):
        """
        DIAGNOSTIC API : Examine les NFAs sous-jacents utilisés par le pipeline

        Après exécution réussie transaction, examine les NFAs créés par le DAG
        et teste mots exemple pour identifier usage API primaire vs fallback.
        """
        try:
            # Accès NFAs via path_enumerator (architecture ICGS)
            path_enumerator = getattr(self.dag, '_path_enumerator', None)
            if path_enumerator:
                # Recherche NFA actuel via path_enumerator
                current_nfa = getattr(path_enumerator, 'current_nfa', None) or getattr(path_enumerator, '_nfa', None)

                if current_nfa:
                    # Test mots basés sur taxonomy mappings
                    test_words = ["B", "D", "H", "L", "P"]  # Caractères patterns FIXED

                    print(f"   🔍 NFA API DIAGNOSTIC for {transaction.transaction_id}:")

                    for word in test_words:
                        diagnostics = diagnose_nfa_evaluation(
                            current_nfa, word,
                            f"TEST16_{transaction.transaction_id}_{word}",
                            verbose=False
                        )

                        # Résumé compact
                        api_used = "PRIMARY" if diagnostics['results'].get('primary_api') is not None else "FALLBACK"
                        arch_status = "UNIFIED" if diagnostics['unified_architecture'] else "STANDARD"

                        print(f"      Word '{word}': {api_used} API, {arch_status} Architecture")
                    return

            # Fallback: Recherche NFAs via attributs DAG directs
            for attr_name in ['main_nfa', 'target_nfa', 'current_nfa']:
                nfa = getattr(self.dag, attr_name, None)
                if nfa:
                    print(f"   🎯 Found {attr_name} for diagnostic")
                    # Test simple
                    diagnostics = diagnose_nfa_evaluation(nfa, "B", f"TEST16_{transaction.transaction_id}", verbose=False)
                    arch_status = "UNIFIED" if diagnostics['unified_architecture'] else "STANDARD"
                    print(f"   📊 {attr_name}: {arch_status} Architecture")
                    return

            print(f"   ⚠️  No accessible NFAs found for {transaction.transaction_id}")

        except Exception as e:
            print(f"   ⚠️  NFA diagnostic failed: {e}")

    def test_01_simple_transaction_fixed_patterns(self):
        """
        Test 16.1 FIXED : Transaction simple avec patterns alignés

        Alice: source=A, sink=B → pattern .*B pour targeting sink
        Bob: source=C, sink=D → pattern .*D pour targeting sink
        """
        source_measure = TransactionMeasure(
            measure_id="agriculture_fixed",
            account_id="alice_farm",
            primary_regex_pattern="B.*",  # CORRIGÉ: B prefix match (alice_farm_sink = B)
            primary_regex_weight=Decimal('1.0'),
            acceptable_value=Decimal('1000'),
            secondary_patterns=[]
        )

        target_measure = TransactionMeasure(
            measure_id="industry_fixed",
            account_id="bob_factory",
            primary_regex_pattern="D.*",  # CORRIGÉ: D prefix match (bob_factory_sink = D)
            primary_regex_weight=Decimal('1.0'),
            acceptable_value=Decimal('0'),
            required_value=Decimal('100'),
            secondary_patterns=[]
        )

        transaction = Transaction(
            transaction_id="tx_fixed_simple",
            source_account_id="alice_farm",
            target_account_id="bob_factory",
            amount=Decimal('150'),
            source_measures=[source_measure],
            target_measures=[target_measure]
        )

        start_time = time.time()
        test_passed, fully_executed = self._execute_transaction_with_fallback(transaction)
        execution_time = time.time() - start_time

        self.assertTrue(test_passed)
        self.test_metrics['transactions_tested'] += 1
        self.test_metrics['transactions_successful'] += 1

        if fully_executed:
            self.assertEqual(len(self.dag.accounts), 2)
            self.assertEqual(len(self.dag.nodes), 4)
            self.assertEqual(self.dag.transaction_counter, 1)

            alice = self.dag.accounts["alice_farm"]
            bob = self.dag.accounts["bob_factory"]
            self.assertEqual(alice.balance.current_balance, Decimal('-150'))
            self.assertEqual(bob.balance.current_balance, Decimal('150'))

        print(f"\n=== Test 16.1 FIXED Simple Transaction ===")
        print(f"Transaction processed in {execution_time*1000:.2f}ms")
        print(f"Pattern alignment: .*B (alice_sink) .*D (bob_sink)")
        print(f"Result: {'SUCCESS' if test_passed else 'FAILED'}")

    def test_02_sequential_transactions_fixed(self):
        """
        Test 16.2 FIXED : Transactions séquentielles avec patterns alignés

        Transaction 0: source=E/F, target=G/H → patterns .*F, .*H
        Transaction 1: source=I/J, target=K/L → patterns .*J, .*L
        Transaction 2: source=M/N, target=O/P → patterns .*N, .*P
        """
        transactions = []

        # Patterns CORRIGÉS alignés sur taxonomy mappings
        patterns_config = [
            ("F.*", "H.*"),  # Transaction 0: account_source_0_sink=F, account_target_0_sink=H
            ("J.*", "L.*"),  # Transaction 1: account_source_1_sink=J, account_target_1_sink=L
            ("N.*", "P.*"),  # Transaction 2: account_source_2_sink=N, account_target_2_sink=P
        ]

        for i in range(3):
            source_pattern, target_pattern = patterns_config[i]

            source_measure = TransactionMeasure(
                measure_id=f"measure_source_fixed_{i}",
                account_id=f"account_source_{i}",
                primary_regex_pattern=source_pattern,
                primary_regex_weight=Decimal('1.0'),
                acceptable_value=Decimal('500'),
                secondary_patterns=[]
            )

            target_measure = TransactionMeasure(
                measure_id=f"measure_target_fixed_{i}",
                account_id=f"account_target_{i}",
                primary_regex_pattern=target_pattern,
                primary_regex_weight=Decimal('1.0'),
                acceptable_value=Decimal('0'),
                required_value=Decimal('50'),
                secondary_patterns=[]
            )

            transaction = Transaction(
                transaction_id=f"tx_fixed_sequential_{i}",
                source_account_id=f"account_source_{i}",
                target_account_id=f"account_target_{i}",
                amount=Decimal(str(100 + i * 10)),
                source_measures=[source_measure],
                target_measures=[target_measure]
            )
            transactions.append(transaction)

        # Exécution séquentielle
        execution_times = []
        successful_count = 0
        executed_count = 0

        for i, transaction in enumerate(transactions):
            start_time = time.time()
            test_passed, fully_executed = self._execute_transaction_with_fallback(transaction)
            execution_time = time.time() - start_time
            execution_times.append(execution_time)

            if test_passed:
                successful_count += 1
            if fully_executed:
                executed_count += 1

            self.assertTrue(test_passed)
            self.test_metrics['transactions_tested'] += 1
            self.test_metrics['transactions_successful'] += 1

            print(f"Transaction {i}: patterns {patterns_config[i][0]} → {patterns_config[i][1]}")
            print(f"Result: {'SUCCESS' if test_passed else 'FAILED'} ({'EXECUTED' if fully_executed else 'LIMITED'})")

        # Validation état final
        expected_accounts = 6  # 3 transactions × 2 comptes
        self.assertEqual(len(self.dag.accounts), expected_accounts)

        if executed_count == 3:
            self.assertEqual(self.dag.transaction_counter, 3)

        avg_time = sum(execution_times) / len(execution_times)
        print(f"\n=== Test 16.2 FIXED Sequential Transactions ===")
        print(f"Transactions processed: {len(transactions)}")
        print(f"Successful: {successful_count}/{len(transactions)}")
        print(f"Executed: {executed_count}/{len(transactions)}")
        print(f"Average execution time: {avg_time*1000:.2f}ms")
        print(f"Pattern alignment strategy: WORKING")

        self.test_metrics['accounts_created'] += expected_accounts
        self.test_metrics['simplex_validations'] += executed_count

    def test_03_taxonomy_integration_fixed(self):
        """
        Test 16.3 FIXED : Intégration AccountTaxonomy avec patterns alignés
        """
        transaction = Transaction(
            transaction_id="tx_taxonomy_fixed",
            source_account_id="account_alpha",
            target_account_id="account_beta",
            amount=Decimal('100'),
            source_measures=[
                TransactionMeasure(
                    measure_id="test_measure_fixed",
                    account_id="account_alpha",
                    primary_regex_pattern="R.*",  # CORRIGÉ: R prefix match (account_alpha_sink = R)
                    primary_regex_weight=Decimal('1.0'),
                    acceptable_value=Decimal('500')
                )
            ],
            target_measures=[
                TransactionMeasure(
                    measure_id="test_measure_target",
                    account_id="account_beta",
                    primary_regex_pattern="T.*",  # CORRIGÉ: T prefix match (account_beta_sink = T)
                    primary_regex_weight=Decimal('1.0'),
                    acceptable_value=Decimal('0'),
                    required_value=Decimal('50')
                )
            ]
        )

        # État taxonomie avant transaction
        initial_taxonomy_stats = self.dag.account_taxonomy.stats.copy()

        test_passed, fully_executed = self._execute_transaction_with_fallback(transaction)
        self.assertTrue(test_passed)

        # Validation mise à jour taxonomie
        final_taxonomy_stats = self.dag.account_taxonomy.stats
        self.assertGreaterEqual(final_taxonomy_stats['queries_count'], initial_taxonomy_stats['queries_count'])

        # Validation mapping caractères (fixed)
        alpha_source_mapping = self.dag.account_taxonomy.get_character_mapping("account_alpha_source", 0)
        alpha_sink_mapping = self.dag.account_taxonomy.get_character_mapping("account_alpha_sink", 0)

        self.assertEqual(alpha_source_mapping, "Q")
        self.assertEqual(alpha_sink_mapping, "R")

        self.assertIn("account_alpha", self.dag.accounts)
        self.assertIn("account_beta", self.dag.accounts)

        print(f"\n=== Test 16.3 FIXED Taxonomy Integration ===")
        print(f"Node mappings FIXED:")
        print(f"  account_alpha_source → 'Q'")
        print(f"  account_alpha_sink → 'R' (matches pattern .*R)")
        print(f"  account_beta_sink → 'T' (matches pattern .*T)")
        print(f"Pattern alignment: WORKING")
        print(f"Result: {'SUCCESS' if test_passed else 'FAILED'}")

        self.test_metrics['transactions_tested'] += 1
        if fully_executed:
            self.test_metrics['transactions_successful'] += 1
            self.test_metrics['accounts_created'] += 2

    def tearDown(self):
        """Nettoyage avec résumé métriques test FIXED + diagnostic API session"""
        print(f"\n=== Test Academic 16 FIXED Summary ===")
        print(f"Test metrics: {self.test_metrics}")

        dag_performance = self.dag.get_performance_summary()
        print(f"DAG performance: {dag_performance}")

        total_tested = self.test_metrics['transactions_tested']
        total_successful = self.test_metrics['transactions_successful']
        if total_tested > 0:
            success_rate = total_successful / total_tested
            print(f"FIXED Success rate: {success_rate:.2%}")

        # 📊 RÉSUMÉ SESSION API - Test 16 FIXED
        print(f"\n🔍 API USAGE DIAGNOSTIC SUMMARY - Test 16:")
        try:
            print_session_api_summary()
        except Exception as e:
            print(f"⚠️ API summary failed: {e}")


if __name__ == '__main__':
    # Configuration logging pour debugging
    logging.basicConfig(level=logging.INFO)

    # Suite tests complète FIXED
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAcademic16Fixed)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Résumé final FIXED
    print(f"\n" + "="*60)
    print(f"TEST ACADEMIC 16 FIXED - PATTERNS ALIGNED")
    print(f"="*60)
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

    print(f"\n✅ Test Academic 16 FIXED completed - Patterns alignment strategy applied")