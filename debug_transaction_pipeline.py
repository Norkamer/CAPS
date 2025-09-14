#!/usr/bin/env python3
"""
Debug Transaction Pipeline - Mode verbeux pour analyse Test 16

Wrapper debugging pour tracer chaque étape du pipeline add_transaction()
avec inspection d'état détaillée et identification précise des échecs.
"""

import sys
import time
import traceback
from typing import Dict, Any, Optional, Tuple, List
from decimal import Decimal, getcontext

# Configuration précision étendue
getcontext().prec = 50

try:
    from icgs_core import (
        DAG, DAGConfiguration, Transaction, TransactionMeasure, Account,
        LinearProgram, LinearConstraint, ConstraintType,
        AnchoredWeightedNFA, AccountTaxonomy
    )
    from icgs_core.exceptions import PathEnumerationNotReadyError
except ImportError as e:
    print(f"IMPORT ERROR: {e}")
    sys.exit(1)


class TransactionPipelineDebugger:
    """
    Debugger verbeux pour pipeline add_transaction()

    Trace chaque étape:
    1. État initial DAG
    2. Création comptes + validation taxonomy
    3. Construction/mise à jour NFA
    4. Path enumeration + word generation
    5. Classification NFA
    6. Construction + résolution Simplex
    7. Commit atomique + pivot storage
    """

    def __init__(self, dag: DAG):
        self.dag = dag
        self.debug_log: List[str] = []
        self.step_timings: Dict[str, float] = {}
        self.state_snapshots: Dict[str, Dict[str, Any]] = {}
        self.error_context: Dict[str, Any] = {}

    def log(self, message: str, level: str = "INFO"):
        """Log avec timestamp et niveau"""
        timestamp = time.strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] {level}: {message}"
        self.debug_log.append(log_entry)
        print(log_entry)

    def capture_state_snapshot(self, step_name: str):
        """Capture état DAG complet pour step donné"""
        snapshot = {
            'step': step_name,
            'timestamp': time.time(),
            'dag_state': {
                'transaction_counter': self.dag.transaction_counter,
                'accounts_count': len(self.dag.accounts),
                'accounts_list': list(self.dag.accounts.keys()),
                'nodes_count': len(self.dag.nodes),
                'edges_count': len(self.dag.edges),
                'stored_pivot_exists': self.dag.stored_pivot is not None
            },
            'taxonomy_state': {
                'history_length': len(self.dag.account_taxonomy.taxonomy_history),
                'latest_transaction_num': self.dag.account_taxonomy.taxonomy_history[-1].transaction_num if self.dag.account_taxonomy.taxonomy_history else None,
                'total_mappings': len(self.dag.account_taxonomy.taxonomy_history[-1].account_mappings) if self.dag.account_taxonomy.taxonomy_history else 0,
                'stats': self.dag.account_taxonomy.stats.copy()
            }
        }

        # NFA state si disponible
        if hasattr(self.dag, 'anchored_nfa') and self.dag.anchored_nfa:
            try:
                nfa_stats = self.dag.anchored_nfa.get_anchoring_statistics()
                snapshot['nfa_state'] = {
                    'exists': True,
                    'is_frozen': nfa_stats.get('is_frozen', False),
                    'patterns_count': nfa_stats.get('total_patterns', 0),
                    'final_states_count': nfa_stats.get('final_states_count', 0)
                }
            except Exception as e:
                snapshot['nfa_state'] = {'exists': False, 'error': str(e)}
        else:
            snapshot['nfa_state'] = {'exists': False}

        self.state_snapshots[step_name] = snapshot
        self.log(f"STATE SNAPSHOT [{step_name}]: {snapshot}")

    def debug_transaction_execution(self, transaction: Transaction) -> Tuple[bool, bool, Dict[str, Any]]:
        """
        Exécute transaction avec debugging verbeux complet

        Returns:
            (success, fully_executed, debug_info)
        """
        self.log(f"=== DÉBUT DEBUG TRANSACTION {transaction.transaction_id} ===", "DEBUG")

        debug_info = {
            'transaction_id': transaction.transaction_id,
            'steps_completed': [],
            'steps_failed': [],
            'error_details': {},
            'performance_metrics': {}
        }

        try:
            # STEP 0: État initial
            step_start = time.time()
            self.capture_state_snapshot("STEP_0_INITIAL")
            self.log(f"STEP 0: État initial DAG")
            self.log(f"  - Transaction counter: {self.dag.transaction_counter}")
            self.log(f"  - Accounts existants: {list(self.dag.accounts.keys())}")
            self.log(f"  - Taxonomy history: {len(self.dag.account_taxonomy.taxonomy_history)} entries")

            self.step_timings["step_0_initial"] = time.time() - step_start
            debug_info['steps_completed'].append("step_0_initial")

            # STEP 1: Validation taxonomy avant création comptes
            step_start = time.time()
            self.log(f"STEP 1: Validation taxonomy pour transaction_counter={self.dag.transaction_counter}")

            # Vérifier si taxonomy configurée pour transaction courante
            try:
                current_tx_num = self.dag.transaction_counter
                if self.dag.account_taxonomy.taxonomy_history:
                    latest_config_tx = self.dag.account_taxonomy.taxonomy_history[-1].transaction_num
                    self.log(f"  - Latest taxonomy config: transaction_num={latest_config_tx}")
                    self.log(f"  - Current transaction_counter: {current_tx_num}")

                    if current_tx_num > latest_config_tx:
                        self.log(f"  - ❌ TAXONOMY GAP DETECTED: current_tx={current_tx_num} > latest_config={latest_config_tx}")
                        debug_info['error_details']['taxonomy_gap'] = {
                            'current_transaction': current_tx_num,
                            'latest_configured': latest_config_tx,
                            'gap_size': current_tx_num - latest_config_tx
                        }
                else:
                    self.log(f"  - ❌ NO TAXONOMY HISTORY")
                    debug_info['error_details']['no_taxonomy'] = True

            except Exception as e:
                self.log(f"  - ❌ TAXONOMY VALIDATION ERROR: {e}")
                debug_info['error_details']['taxonomy_validation'] = str(e)

            self.step_timings["step_1_taxonomy_validation"] = time.time() - step_start
            debug_info['steps_completed'].append("step_1_taxonomy_validation")

            # STEP 2: Création comptes
            step_start = time.time()
            self.log(f"STEP 2: Tentative création comptes")

            source_account_id = transaction.source_account_id
            target_account_id = transaction.target_account_id
            self.log(f"  - Source account: {source_account_id}")
            self.log(f"  - Target account: {target_account_id}")

            # Tester mappings taxonomy pour nodes requis
            required_nodes = [
                f"{source_account_id}_source",
                f"{source_account_id}_sink",
                f"{target_account_id}_source",
                f"{target_account_id}_sink"
            ]

            current_tx_num = self.dag.transaction_counter
            for node_id in required_nodes:
                try:
                    mapping = self.dag.account_taxonomy.get_character_mapping(node_id, current_tx_num)
                    self.log(f"  - Node {node_id}: mapping='{mapping}'")
                except Exception as e:
                    self.log(f"  - ❌ Node {node_id}: mapping error: {e}")
                    debug_info['error_details'].setdefault('missing_mappings', []).append({
                        'node_id': node_id,
                        'transaction_num': current_tx_num,
                        'error': str(e)
                    })

            self.step_timings["step_2_account_preparation"] = time.time() - step_start
            debug_info['steps_completed'].append("step_2_account_preparation")

            # STEP 3: Exécution transaction réelle
            step_start = time.time()
            self.log(f"STEP 3: Exécution add_transaction() réelle")

            try:
                result = self.dag.add_transaction(transaction)
                self.log(f"  - ✅ Transaction result: {result}")

                self.capture_state_snapshot("STEP_3_AFTER_EXECUTION")

                if result:
                    debug_info['execution_result'] = 'success'
                    self.log(f"  - ✅ Transaction complètement exécutée")
                    return (True, True, debug_info)
                else:
                    debug_info['execution_result'] = 'failed'
                    self.log(f"  - ❌ Transaction échouée avec result=False")
                    return (False, False, debug_info)

            except PathEnumerationNotReadyError as e:
                debug_info['execution_result'] = 'path_enumeration_limitation'
                debug_info['error_details']['path_enumeration'] = {
                    'error_code': e.error_code,
                    'message': str(e)
                }
                self.log(f"  - ✅ Transaction limitée par Path Enumeration (PHASE 2.9): {e.error_code}")
                self.log(f"    Message: {e}")
                return (True, False, debug_info)  # Test passé mais pas exécuté

            except Exception as e:
                debug_info['execution_result'] = 'unexpected_error'
                debug_info['error_details']['unexpected'] = {
                    'type': type(e).__name__,
                    'message': str(e),
                    'traceback': traceback.format_exc()
                }
                self.log(f"  - ❌ Transaction échouée avec erreur inattendue: {type(e).__name__}: {e}")
                self.log(f"  - Traceback: {traceback.format_exc()}")
                return (False, False, debug_info)

            finally:
                self.step_timings["step_3_execution"] = time.time() - step_start
                debug_info['steps_completed'].append("step_3_execution")

        except Exception as e:
            self.log(f"❌ ERREUR CRITIQUE DANS DEBUG PIPELINE: {type(e).__name__}: {e}")
            debug_info['error_details']['critical_debug_error'] = {
                'type': type(e).__name__,
                'message': str(e),
                'traceback': traceback.format_exc()
            }
            return (False, False, debug_info)

        finally:
            # Performance summary
            total_time = sum(self.step_timings.values())
            debug_info['performance_metrics'] = {
                'total_time_ms': total_time * 1000,
                'step_timings_ms': {k: v * 1000 for k, v in self.step_timings.items()}
            }

            self.log(f"=== FIN DEBUG TRANSACTION {transaction.transaction_id} ===", "DEBUG")
            self.log(f"Performance: Total {total_time*1000:.2f}ms")
            for step, timing in self.step_timings.items():
                self.log(f"  - {step}: {timing*1000:.2f}ms")


def debug_failing_test():
    """
    Exécute test 16.3 (transactions séquentielles) avec debugging verbeux
    pour identifier exactement où ça échoue
    """
    print("=== DEBUGGING MODE VERBEUX - TEST 16.3 SEQUENTIAL TRANSACTIONS ===")

    # Configuration DAG identique au test
    config = DAGConfiguration(
        max_path_enumeration=1000,
        simplex_max_iterations=500,
        simplex_tolerance=Decimal('1e-10'),
        nfa_explosion_threshold=100,
        enable_warm_start=True,
        enable_cross_validation=True,
        validation_mode="STRICT"
    )

    dag = DAG(config)
    debugger = TransactionPipelineDebugger(dag)

    # Configuration taxonomie manuelle (comme dans test original)
    explicit_mappings = {
        # Mappings UTF-32 étendus pour éviter collisions
        "account_source_0_source": "Ω",  # Source 0
        "account_source_0_sink": "Ψ",   # Sink 0
        "account_target_0_source": "Χ", # Target 0
        "account_target_0_sink": "Φ",   # Sink 0
        "account_source_1_source": "Υ", # Source 1
        "account_source_1_sink": "Τ",   # Sink 1
        "account_target_1_source": "Σ", # Target 1
        "account_target_1_sink": "Ρ",   # Sink 1
        "account_source_2_source": "Π", # Source 2
        "account_source_2_sink": "Ξ",   # Sink 2
        "account_target_2_source": "Ν", # Target 2
        "account_target_2_sink": "Μ"    # Sink 2
    }

    debugger.log(f"Configuration taxonomie avec {len(explicit_mappings)} mappings")
    dag.account_taxonomy.update_taxonomy(explicit_mappings, 0)
    debugger.log(f"Taxonomie configurée pour transaction_num=0")

    # Création transactions identiques au test original
    transactions = []
    for i in range(3):
        # Patterns alignés avec taxonomie UTF-32 grecque étendue
        source_pattern = [".*Ω.*", ".*Υ.*", ".*Π.*"][i]  # Patterns pour sources (Ω,Υ,Π)
        target_pattern = [".*Χ.*", ".*Σ.*", ".*Ν.*"][i]  # Patterns pour targets (Χ,Σ,Ν)

        source_measure = TransactionMeasure(
            measure_id=f"measure_source_{i}",
            account_id=f"account_source_{i}",
            primary_regex_pattern=source_pattern,
            primary_regex_weight=Decimal('1.0'),
            acceptable_value=Decimal('500'),
            secondary_patterns=[]
        )

        target_measure = TransactionMeasure(
            measure_id=f"measure_target_{i}",
            account_id=f"account_target_{i}",
            primary_regex_pattern=target_pattern,
            primary_regex_weight=Decimal('1.0'),
            acceptable_value=Decimal('0'),
            required_value=Decimal('50'),
            secondary_patterns=[]
        )

        transaction = Transaction(
            transaction_id=f"tx_debug_sequential_{i}",
            source_account_id=f"account_source_{i}",
            target_account_id=f"account_target_{i}",
            amount=Decimal(str(100 + i * 10)),
            source_measures=[source_measure],
            target_measures=[target_measure]
        )
        transactions.append(transaction)

    debugger.log(f"Créé {len(transactions)} transactions pour test séquentiel")

    # Exécution séquentielle avec debugging verbeux
    results = []
    for i, transaction in enumerate(transactions):
        debugger.log(f"\n>>> DÉBUT TRANSACTION {i} - {transaction.transaction_id} <<<")

        success, fully_executed, debug_info = debugger.debug_transaction_execution(transaction)

        result_summary = {
            'transaction_index': i,
            'transaction_id': transaction.transaction_id,
            'success': success,
            'fully_executed': fully_executed,
            'debug_info': debug_info
        }
        results.append(result_summary)

        debugger.log(f">>> FIN TRANSACTION {i} - Success: {success}, Executed: {fully_executed} <<<\n")

        # Arrêt au premier échec pour analyse
        if not success:
            debugger.log(f"❌ ARRÊT DEBUG - Première transaction échouée: {i}")
            break

    # Analyse finale
    debugger.log("\n=== ANALYSE FINALE RÉSULTATS DEBUG ===")

    for i, result in enumerate(results):
        debugger.log(f"Transaction {i}: Success={result['success']}, Executed={result['fully_executed']}")

        error_details = result['debug_info'].get('error_details', {})
        if error_details:
            debugger.log(f"  Erreurs détectées: {list(error_details.keys())}")
            for error_type, error_info in error_details.items():
                debugger.log(f"    - {error_type}: {error_info}")

    return results, debugger


if __name__ == "__main__":
    try:
        results, debugger = debug_failing_test()

        print(f"\n=== SUMMARY DEBUG RESULTS ===")
        print(f"Transactions testées: {len(results)}")

        success_count = sum(1 for r in results if r['success'])
        executed_count = sum(1 for r in results if r['fully_executed'])

        print(f"Succès: {success_count}/{len(results)}")
        print(f"Exécutées complètement: {executed_count}/{len(results)}")

        # Sauvegarde log debug pour analyse
        with open("/home/norkamer/ClaudeCode/CAPS/debug_test16_results.log", "w") as f:
            f.write("\n".join(debugger.debug_log))

        print(f"\nLog debug sauvegardé: debug_test16_results.log")

    except Exception as e:
        print(f"ERREUR CRITIQUE DEBUG: {e}")
        traceback.print_exc()