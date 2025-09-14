#!/usr/bin/env python3
"""
ICGS Diagnostics Module - Production Ready
Fonctions diagnostic et analyse pour système ICGS en production

Migré depuis debug files pour usage productif.
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
import logging

try:
    from icgs_core import DAG, Transaction, TransactionMeasure
except ImportError:
    pass  # Handle missing imports gracefully


class ICGSDiagnostics:
    """
    Classe diagnostic pour analyse système ICGS en production

    Fournit outils diagnostic, monitoring, et analyse performance
    sans verbosité excessive des debug files.
    """

    def __init__(self, dag: Optional[Any] = None):
        """Initialize diagnostics with optional DAG instance"""
        self.dag = dag
        self.logger = logging.getLogger(__name__)

    def analyze_transaction_result(self, transaction: Any, result: bool) -> Dict[str, Any]:
        """
        Analyse résultat transaction de manière concise

        Args:
            transaction: Transaction object
            result: Résultat de add_transaction()

        Returns:
            Dictionnaire avec métriques diagnostic
        """
        analysis = {
            'transaction_id': getattr(transaction, 'transaction_id', 'unknown'),
            'success': result,
            'dag_state': {},
            'performance_metrics': {}
        }

        if self.dag:
            analysis['dag_state'] = {
                'accounts_count': len(getattr(self.dag, 'accounts', {})),
                'nodes_count': len(getattr(self.dag, 'nodes', {})),
                'edges_count': len(getattr(self.dag, 'edges', {})),
                'transaction_counter': getattr(self.dag, 'transaction_counter', 0)
            }

            # Performance summary si disponible
            if hasattr(self.dag, 'get_performance_summary'):
                try:
                    analysis['performance_metrics'] = self.dag.get_performance_summary()
                except Exception:
                    analysis['performance_metrics'] = {'error': 'performance_summary_failed'}

        return analysis

    def validate_balance_conservation(self) -> Dict[str, Any]:
        """
        Validation conservation balances dans le DAG

        Returns:
            Résultats validation avec détails erreurs si applicable
        """
        validation = {
            'total_balance': Decimal('0'),
            'account_balances': {},
            'conservation_violated': False,
            'violations': []
        }

        if not self.dag or not hasattr(self.dag, 'accounts'):
            validation['error'] = 'no_dag_or_accounts'
            return validation

        try:
            for account_id, account in self.dag.accounts.items():
                balance = getattr(account.balance, 'current_balance', Decimal('0'))
                validation['account_balances'][account_id] = balance
                validation['total_balance'] += balance

            # Conservation check (should be 0 for closed system)
            if abs(validation['total_balance']) > Decimal('1e-10'):
                validation['conservation_violated'] = True
                validation['violations'].append(f"Total balance not zero: {validation['total_balance']}")

        except Exception as e:
            validation['error'] = str(e)
            validation['conservation_violated'] = True

        return validation

    def quick_health_check(self) -> Dict[str, Any]:
        """
        Health check rapide du système ICGS

        Returns:
            État santé système avec flags critiques
        """
        health = {
            'status': 'healthy',
            'critical_issues': [],
            'warnings': [],
            'info': {}
        }

        if not self.dag:
            health['status'] = 'error'
            health['critical_issues'].append('No DAG instance provided')
            return health

        # Check basic integrity
        try:
            accounts_count = len(getattr(self.dag, 'accounts', {}))
            nodes_count = len(getattr(self.dag, 'nodes', {}))

            health['info']['accounts'] = accounts_count
            health['info']['nodes'] = nodes_count

            # Basic sanity checks
            if accounts_count > 0 and nodes_count < accounts_count * 2:
                health['warnings'].append(f"Unexpected node count: {nodes_count} nodes for {accounts_count} accounts")

            # Balance conservation
            balance_check = self.validate_balance_conservation()
            if balance_check.get('conservation_violated'):
                health['critical_issues'].append('Balance conservation violated')
                health['status'] = 'critical'

        except Exception as e:
            health['status'] = 'error'
            health['critical_issues'].append(f'Health check failed: {str(e)}')

        return health


def create_diagnostics_for_dag(dag: Any) -> ICGSDiagnostics:
    """Factory pour créer diagnostics pour DAG donné"""
    return ICGSDiagnostics(dag)


def run_quick_diagnostic(dag: Any, transaction: Any = None, result: bool = False) -> Dict[str, Any]:
    """
    Diagnostic rapide tout-en-un

    Args:
        dag: Instance DAG
        transaction: Transaction optionnelle à analyser
        result: Résultat transaction si fourni

    Returns:
        Rapport diagnostic complet
    """
    diagnostics = create_diagnostics_for_dag(dag)

    report = {
        'health_check': diagnostics.quick_health_check(),
        'balance_validation': diagnostics.validate_balance_conservation()
    }

    if transaction is not None:
        report['transaction_analysis'] = diagnostics.analyze_transaction_result(transaction, result)

    return report


if __name__ == "__main__":
    # Test diagnostics module
    print("ICGS Diagnostics Module - Production Ready")
    print("Migrated from debug files for production usage")

    # Create mock diagnostic
    diagnostics = ICGSDiagnostics()
    health = diagnostics.quick_health_check()
    print(f"Health check without DAG: {health['status']}")