#!/usr/bin/env python3
"""
Equivalence Validator - Migration Tools

Valide que les migrations DAG → EnhancedDAG préservent exactement
la fonctionnalité et produisent des résultats identiques.

FONCTIONNALITÉS:
1. Validation équivalence fonctionnelle
2. Tests performance comparés
3. Validation intégrité données
4. Rapports différences détaillés
5. Tests régression automatisés

Usage:
    python equivalence_validator.py --original ORIG_MODULE --migrated MIGR_MODULE
    python equivalence_validator.py --test-suite TEST_SUITE_PATH
"""

import sys
import os
import time
import json
import importlib
import traceback
from typing import Dict, List, Tuple, Any, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import argparse


@dataclass
class ValidationResult:
    """Résultat validation équivalence"""
    test_name: str
    original_result: Any
    migrated_result: Any
    equivalent: bool
    performance_ratio: float
    error_message: Optional[str]
    execution_time_original: float
    execution_time_migrated: float


@dataclass
class ValidationSuite:
    """Suite validation complète"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    average_performance_ratio: float
    detailed_results: List[ValidationResult]
    summary: str


class EquivalenceValidator:
    """Validateur principal équivalence fonctionnelle"""

    def __init__(self):
        self.test_cases = []
        self.validation_results = []

    def add_test_case(self, name: str, test_data: Dict[str, Any],
                      original_func: Callable, migrated_func: Callable):
        """Ajoute cas test validation"""

        test_case = {
            'name': name,
            'test_data': test_data,
            'original_func': original_func,
            'migrated_func': migrated_func
        }

        self.test_cases.append(test_case)

    def validate_equivalence(self, test_case: Dict[str, Any]) -> ValidationResult:
        """Valide équivalence pour un cas test"""

        name = test_case['name']
        test_data = test_case['test_data']
        original_func = test_case['original_func']
        migrated_func = test_case['migrated_func']

        try:
            # Exécution version originale
            start_time = time.perf_counter()
            original_result = original_func(**test_data)
            original_time = time.perf_counter() - start_time

            # Exécution version migrée
            start_time = time.perf_counter()
            migrated_result = migrated_func(**test_data)
            migrated_time = time.perf_counter() - start_time

            # Validation équivalence
            equivalent = self._deep_equal(original_result, migrated_result)

            # Calcul ratio performance
            performance_ratio = migrated_time / max(original_time, 0.000001)

            return ValidationResult(
                test_name=name,
                original_result=original_result,
                migrated_result=migrated_result,
                equivalent=equivalent,
                performance_ratio=performance_ratio,
                error_message=None,
                execution_time_original=original_time,
                execution_time_migrated=migrated_time
            )

        except Exception as e:
            return ValidationResult(
                test_name=name,
                original_result=None,
                migrated_result=None,
                equivalent=False,
                performance_ratio=float('inf'),
                error_message=str(e),
                execution_time_original=0,
                execution_time_migrated=0
            )

    def _deep_equal(self, obj1: Any, obj2: Any) -> bool:
        """Comparaison profonde objets"""

        # Types différents
        if type(obj1) != type(obj2):
            return False

        # None
        if obj1 is None and obj2 is None:
            return True

        # Primitives
        if isinstance(obj1, (int, float, str, bool)):
            return obj1 == obj2

        # Listes
        if isinstance(obj1, list):
            if len(obj1) != len(obj2):
                return False
            return all(self._deep_equal(a, b) for a, b in zip(obj1, obj2))

        # Dictionnaires
        if isinstance(obj1, dict):
            if set(obj1.keys()) != set(obj2.keys()):
                return False
            return all(self._deep_equal(obj1[k], obj2[k]) for k in obj1.keys())

        # Autres types - comparaison basique
        try:
            return obj1 == obj2
        except:
            return str(obj1) == str(obj2)

    def run_validation_suite(self) -> ValidationSuite:
        """Exécute suite validation complète"""

        print(f"🧪 Exécution {len(self.test_cases)} tests validation...")

        for test_case in self.test_cases:
            print(f"   Test: {test_case['name']}")
            result = self.validate_equivalence(test_case)
            self.validation_results.append(result)

            if result.equivalent:
                print(f"      ✅ ÉQUIVALENT (performance: {result.performance_ratio:.2f}x)")
            else:
                print(f"      ❌ DIFFÉRENT: {result.error_message or 'Résultats non identiques'}")

        # Génération suite complète
        passed = sum(1 for r in self.validation_results if r.equivalent)
        failed = len(self.validation_results) - passed

        avg_perf_ratio = sum(r.performance_ratio for r in self.validation_results
                           if r.performance_ratio != float('inf')) / max(len(self.validation_results), 1)

        summary = f"{passed}/{len(self.validation_results)} tests réussis"
        if failed > 0:
            summary += f", {failed} échecs détectés"
        summary += f", performance moyenne: {avg_perf_ratio:.2f}x"

        return ValidationSuite(
            total_tests=len(self.validation_results),
            passed_tests=passed,
            failed_tests=failed,
            average_performance_ratio=avg_perf_ratio,
            detailed_results=self.validation_results,
            summary=summary
        )

    def generate_report(self, suite: ValidationSuite, output_path: str):
        """Génère rapport validation détaillé"""

        # Conversion en dict pour JSON
        suite_dict = asdict(suite)

        # Simplification résultats pour JSON
        for result in suite_dict['detailed_results']:
            # Convertir résultats complexes en string
            if result['original_result'] is not None:
                result['original_result'] = str(result['original_result'])
            if result['migrated_result'] is not None:
                result['migrated_result'] = str(result['migrated_result'])

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(suite_dict, f, indent=2, ensure_ascii=False)

        print(f"📊 Rapport validation généré: {output_path}")

    def print_summary(self, suite: ValidationSuite):
        """Affiche résumé validation"""

        print(f"\n📊 VALIDATION ÉQUIVALENCE - RÉSUMÉ")
        print("=" * 50)
        print(f"Tests total:              {suite.total_tests}")
        print(f"Tests réussis:            {suite.passed_tests}")
        print(f"Tests échoués:            {suite.failed_tests}")
        print(f"Taux succès:              {suite.passed_tests/suite.total_tests*100:.1f}%")
        print(f"Performance moyenne:      {suite.average_performance_ratio:.2f}x")

        if suite.failed_tests > 0:
            print(f"\n❌ ÉCHECS DÉTECTÉS:")
            failed_results = [r for r in suite.detailed_results if not r.equivalent]

            for i, result in enumerate(failed_results[:5], 1):  # Limiter à 5
                print(f"   {i}. {result.test_name}")
                if result.error_message:
                    print(f"      Erreur: {result.error_message}")
                else:
                    print(f"      Original:  {result.original_result}")
                    print(f"      Migrated:  {result.migrated_result}")

            if len(failed_results) > 5:
                print(f"      ... et {len(failed_results) - 5} autres échecs")

        if suite.passed_tests == suite.total_tests:
            print(f"\n🎉 VALIDATION RÉUSSIE: Équivalence fonctionnelle confirmée")
        else:
            print(f"\n⚠️  VALIDATION PARTIELLE: {suite.failed_tests} différences détectées")


class DAGEquivalenceTester:
    """Testeur spécialisé équivalence DAG"""

    def __init__(self):
        self.validator = EquivalenceValidator()

    def setup_dag_tests(self, original_dag_class, enhanced_dag_class):
        """Configure tests équivalence DAG spécifiques"""

        print("🔧 Configuration tests DAG...")

        # Test 1: Configuration comptes basique
        self.validator.add_test_case(
            name="basic_account_configuration",
            test_data={
                'accounts': {"test_account_1": "T", "test_account_2": "U"}
            },
            original_func=self._test_original_config,
            migrated_func=self._test_enhanced_config
        )

        # Test 2: Accès mappings
        self.validator.add_test_case(
            name="account_mapping_access",
            test_data={
                'accounts': {"mapping_test": "M"},
                'account_id': "mapping_test"
            },
            original_func=self._test_original_mapping_access,
            migrated_func=self._test_enhanced_mapping_access
        )

        # Test 3: Conversion paths
        self.validator.add_test_case(
            name="path_conversion",
            test_data={
                'accounts': {"path_node_1": "P", "path_node_2": "Q"},
                'path': ["path_node_1", "path_node_2"]
            },
            original_func=self._test_original_path_conversion,
            migrated_func=self._test_enhanced_path_conversion
        )

        # Test 4: Configuration large échelle
        large_accounts = {f"large_{i}": chr(65 + i) for i in range(20)}  # A-T
        self.validator.add_test_case(
            name="large_scale_configuration",
            test_data={'accounts': large_accounts},
            original_func=self._test_original_config,
            migrated_func=self._test_enhanced_config
        )

        print(f"   ✅ {len(self.validator.test_cases)} tests DAG configurés")

    def _test_original_config(self, accounts: Dict[str, str]) -> Dict[str, str]:
        """Test configuration DAG original"""
        try:
            # Import dynamique pour éviter dépendances
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
            from icgs_core.dag import DAG

            dag = DAG()
            dag.account_taxonomy.update_taxonomy(accounts, 0)

            # Retourner résultat vérifiant configuration
            result = {}
            for account_id in accounts.keys():
                mapping = dag.account_taxonomy.get_character_mapping(account_id, 0)
                result[account_id] = mapping

            return result

        except Exception as e:
            raise Exception(f"Erreur DAG original: {e}")

    def _test_enhanced_config(self, accounts: Dict[str, str]) -> Dict[str, str]:
        """Test configuration EnhancedDAG"""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
            from icgs_core.enhanced_dag import EnhancedDAG

            enhanced_dag = EnhancedDAG()
            enhanced_dag.configure_accounts_simple(accounts)

            # Retourner résultat équivalent
            result = {}
            for account_id in accounts.keys():
                mapping = enhanced_dag.get_current_account_mapping(account_id)
                result[account_id] = mapping

            return result

        except Exception as e:
            raise Exception(f"Erreur EnhancedDAG: {e}")

    def _test_original_mapping_access(self, accounts: Dict[str, str], account_id: str) -> str:
        """Test accès mapping DAG original"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from icgs_core.dag import DAG

        dag = DAG()
        dag.account_taxonomy.update_taxonomy(accounts, 0)
        return dag.account_taxonomy.get_character_mapping(account_id, 0)

    def _test_enhanced_mapping_access(self, accounts: Dict[str, str], account_id: str) -> str:
        """Test accès mapping EnhancedDAG"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from icgs_core.enhanced_dag import EnhancedDAG

        enhanced_dag = EnhancedDAG()
        enhanced_dag.configure_accounts_simple(accounts)
        return enhanced_dag.get_current_account_mapping(account_id)

    def _test_original_path_conversion(self, accounts: Dict[str, str], path: List[str]) -> str:
        """Test conversion path DAG original"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from icgs_core.dag import DAG
        from icgs_core.dag_structures import Node

        dag = DAG()
        dag.account_taxonomy.update_taxonomy(accounts, 0)

        node_path = [Node(node_id) for node_id in path]
        return dag.account_taxonomy.convert_path_to_word(node_path, 0)

    def _test_enhanced_path_conversion(self, accounts: Dict[str, str], path: List[str]) -> str:
        """Test conversion path EnhancedDAG"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from icgs_core.enhanced_dag import EnhancedDAG
        from icgs_core.dag_structures import Node

        enhanced_dag = EnhancedDAG()
        enhanced_dag.configure_accounts_simple(accounts)

        node_path = [Node(node_id) for node_id in path]
        return enhanced_dag.convert_path_simple(node_path)

    def run_dag_validation(self) -> ValidationSuite:
        """Exécute validation complète DAG"""
        return self.validator.run_validation_suite()


def main():
    """Interface ligne de commande"""

    parser = argparse.ArgumentParser(
        description="Valide équivalence fonctionnelle migration DAG → EnhancedDAG"
    )

    parser.add_argument(
        '--dag-validation', '-d',
        action='store_true',
        help="Validation spécialisée DAG vs EnhancedDAG"
    )

    parser.add_argument(
        '--output', '-o',
        default='equivalence_validation_report.json',
        help="Fichier rapport validation (défaut: equivalence_validation_report.json)"
    )

    parser.add_argument(
        '--detailed', '-v',
        action='store_true',
        help="Affichage détaillé résultats"
    )

    args = parser.parse_args()

    print("🔍 VALIDATEUR ÉQUIVALENCE DAG → EnhancedDAG")
    print("=" * 60)

    if args.dag_validation:
        # Validation spécialisée DAG
        tester = DAGEquivalenceTester()

        try:
            # Configuration tests DAG automatiques
            tester.setup_dag_tests(None, None)  # Classes seront importées dynamiquement

            # Exécution validation
            suite = tester.run_dag_validation()

            # Affichage résultats
            tester.validator.print_summary(suite)

            # Sauvegarde rapport
            tester.validator.generate_report(suite, args.output)

            # Code retour basé sur succès
            return 0 if suite.failed_tests == 0 else 1

        except Exception as e:
            print(f"❌ Erreur validation DAG: {e}")
            if args.detailed:
                traceback.print_exc()
            return 1

    else:
        parser.print_help()
        print("\n💡 Conseil: Utilisez --dag-validation pour tests automatiques DAG")
        return 1


if __name__ == "__main__":
    exit(main())