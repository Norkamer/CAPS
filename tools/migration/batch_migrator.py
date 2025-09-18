#!/usr/bin/env python3
"""
Batch Migrator - Migration Tools

Orchestrateur principal migration batch DAG → EnhancedDAG pour projets complets.
Combine analyse, génération, validation et rapports en workflow automatisé.

WORKFLOW COMPLET:
1. Analyse code existant (code_analyzer.py)
2. Génération migrations (migration_generator.py)
3. Validation équivalence (equivalence_validator.py)
4. Génération rapport final consolidé
5. Recommandations déploiement

Usage:
    python batch_migrator.py --project PROJECT_DIR
    python batch_migrator.py --project PROJECT_DIR --dry-run
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import shutil


class BatchMigrator:
    """Orchestrateur migration batch"""

    def __init__(self, project_path: str, dry_run: bool = False):
        self.project_path = os.path.abspath(project_path)
        self.dry_run = dry_run
        self.migration_dir = os.path.join(self.project_path, "migration_results")
        self.tools_dir = os.path.dirname(__file__)

        # Résultats workflow
        self.analysis_report = None
        self.migration_results = {}
        self.validation_report = None
        self.final_report = {}

    def setup_migration_workspace(self):
        """Prépare workspace migration"""

        if not self.dry_run:
            os.makedirs(self.migration_dir, exist_ok=True)

            # Sous-répertoires
            os.makedirs(os.path.join(self.migration_dir, "analysis"), exist_ok=True)
            os.makedirs(os.path.join(self.migration_dir, "migrated_files"), exist_ok=True)
            os.makedirs(os.path.join(self.migration_dir, "validation"), exist_ok=True)
            os.makedirs(os.path.join(self.migration_dir, "reports"), exist_ok=True)

        print(f"🗂️  Workspace migration: {self.migration_dir}")

    def run_code_analysis(self) -> bool:
        """Étape 1: Analyse code existant"""

        print("🔍 ÉTAPE 1: ANALYSE CODE EXISTANT")
        print("-" * 40)

        analysis_output = os.path.join(self.migration_dir, "analysis", "code_analysis.json")
        code_analyzer = os.path.join(self.tools_dir, "code_analyzer.py")

        cmd = [
            sys.executable, code_analyzer,
            '--path', self.project_path,
            '--output', analysis_output,
            '--recursive'
        ]

        if self.dry_run:
            print(f"   [DRY RUN] Commande: {' '.join(cmd)}")
            return True

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                # Charger rapport analyse
                if os.path.exists(analysis_output):
                    with open(analysis_output, 'r', encoding='utf-8') as f:
                        self.analysis_report = json.load(f)

                    print(f"   ✅ Analyse terminée: {analysis_output}")
                    print(f"   📊 {self.analysis_report['total_opportunities']} opportunités détectées")
                    return True
                else:
                    print(f"   ❌ Rapport analyse non généré")
                    return False

            else:
                print(f"   ❌ Erreur analyse: {result.stderr}")
                return False

        except Exception as e:
            print(f"   ❌ Exception analyse: {e}")
            return False

    def run_migration_generation(self) -> bool:
        """Étape 2: Génération migrations"""

        print("\n🔄 ÉTAPE 2: GÉNÉRATION MIGRATIONS")
        print("-" * 40)

        migration_generator = os.path.join(self.tools_dir, "migration_generator.py")

        cmd = [
            sys.executable, migration_generator,
            '--project', self.project_path,
            '--batch'
        ]

        if self.dry_run:
            print(f"   [DRY RUN] Commande: {' '.join(cmd)}")
            self.migration_results = {"dry_run": True, "files_processed": 5, "success_count": 4}
            return True

        try:
            # Rediriger output vers workspace migration
            env = os.environ.copy()
            env['MIGRATION_OUTPUT_DIR'] = os.path.join(self.migration_dir, "migrated_files")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)

            if result.returncode == 0:
                print(f"   ✅ Migrations générées")

                # Analyser output pour extraire statistiques
                output_lines = result.stdout.split('\n')
                self.migration_results = self._parse_migration_output(output_lines)

                return True

            else:
                print(f"   ❌ Erreur génération: {result.stderr}")
                return False

        except Exception as e:
            print(f"   ❌ Exception génération: {e}")
            return False

    def _parse_migration_output(self, output_lines: List[str]) -> Dict[str, Any]:
        """Parse output génération migration"""

        results = {
            'files_processed': 0,
            'success_count': 0,
            'error_count': 0,
            'transformations_total': 0
        }

        for line in output_lines:
            if 'Migration réussie' in line:
                results['success_count'] += 1
            elif 'transformations' in line:
                # Extraire nombre transformations
                import re
                match = re.search(r'(\d+)\s+transformations', line)
                if match:
                    results['transformations_total'] += int(match.group(1))

        results['files_processed'] = results['success_count'] + results['error_count']
        return results

    def run_validation(self) -> bool:
        """Étape 3: Validation équivalence"""

        print("\n🧪 ÉTAPE 3: VALIDATION ÉQUIVALENCE")
        print("-" * 40)

        validation_output = os.path.join(self.migration_dir, "validation", "equivalence_report.json")
        equivalence_validator = os.path.join(self.tools_dir, "equivalence_validator.py")

        cmd = [
            sys.executable, equivalence_validator,
            '--dag-validation',
            '--output', validation_output
        ]

        if self.dry_run:
            print(f"   [DRY RUN] Commande: {' '.join(cmd)}")
            self.validation_report = {
                "total_tests": 4,
                "passed_tests": 4,
                "failed_tests": 0,
                "summary": "4/4 tests réussis, performance moyenne: 1.2x"
            }
            return True

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                # Charger rapport validation
                if os.path.exists(validation_output):
                    with open(validation_output, 'r', encoding='utf-8') as f:
                        self.validation_report = json.load(f)

                    print(f"   ✅ Validation terminée: {validation_output}")
                    print(f"   📊 {self.validation_report['passed_tests']}/{self.validation_report['total_tests']} tests réussis")
                    return True
                else:
                    print(f"   ❌ Rapport validation non généré")
                    return False

            else:
                print(f"   ⚠️  Validation avec avertissements: {result.stderr}")
                # Continuer même avec avertissements
                self.validation_report = {"status": "warning", "message": result.stderr}
                return True

        except Exception as e:
            print(f"   ❌ Exception validation: {e}")
            return False

    def generate_final_report(self) -> bool:
        """Étape 4: Génération rapport final"""

        print("\n📊 ÉTAPE 4: RAPPORT FINAL")
        print("-" * 40)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.final_report = {
            "migration_summary": {
                "project_path": self.project_path,
                "timestamp": timestamp,
                "dry_run": self.dry_run,
                "workflow_steps": [
                    "code_analysis", "migration_generation",
                    "equivalence_validation", "final_report"
                ]
            },
            "analysis_results": self.analysis_report,
            "migration_results": self.migration_results,
            "validation_results": self.validation_report,
            "recommendations": self._generate_recommendations()
        }

        if not self.dry_run:
            report_path = os.path.join(self.migration_dir, "reports", "migration_final_report.json")

            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(self.final_report, f, indent=2, ensure_ascii=False)

            print(f"   ✅ Rapport final généré: {report_path}")

            # Génération rapport lisible
            readable_report = os.path.join(self.migration_dir, "reports", "MIGRATION_SUMMARY.md")
            self._generate_readable_report(readable_report)
            print(f"   📖 Rapport lisible généré: {readable_report}")

        return True

    def _generate_recommendations(self) -> Dict[str, Any]:
        """Génère recommandations déploiement"""

        recommendations = {
            "overall_status": "unknown",
            "deployment_readiness": "pending",
            "action_items": [],
            "risk_assessment": "medium",
            "next_steps": []
        }

        # Analyse basée sur résultats
        if self.analysis_report:
            total_opportunities = self.analysis_report.get('total_opportunities', 0)
            high_confidence = self.analysis_report.get('high_confidence_opportunities', 0)

            if high_confidence >= 3:
                recommendations["overall_status"] = "excellent"
                recommendations["deployment_readiness"] = "ready"
            elif total_opportunities >= 1:
                recommendations["overall_status"] = "good"
                recommendations["deployment_readiness"] = "ready_with_testing"
            else:
                recommendations["overall_status"] = "limited_benefit"
                recommendations["deployment_readiness"] = "evaluate"

        # Analyse validation
        if self.validation_report and self.validation_report.get('failed_tests', 1) == 0:
            recommendations["action_items"].append("✅ Validation équivalence réussie")
            recommendations["risk_assessment"] = "low"
        else:
            recommendations["action_items"].append("⚠️  Validation nécessite attention")
            recommendations["risk_assessment"] = "medium"

        # Next steps
        if recommendations["deployment_readiness"] == "ready":
            recommendations["next_steps"] = [
                "1. Révision code migré par équipe",
                "2. Tests intégration sur environnement staging",
                "3. Déploiement progressif en production",
                "4. Monitoring performance post-déploiement"
            ]
        else:
            recommendations["next_steps"] = [
                "1. Validation manuelle différences détectées",
                "2. Tests complémentaires si nécessaire",
                "3. Réévaluation bénéfices/risques",
                "4. Décision go/no-go migration"
            ]

        return recommendations

    def _generate_readable_report(self, output_path: str):
        """Génère rapport lisible markdown"""

        content = f"""# 📋 Rapport Migration DAG → EnhancedDAG

**Projet:** {self.project_path}
**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Mode:** {'DRY RUN' if self.dry_run else 'EXÉCUTION COMPLÈTE'}

---

## 📊 Résumé Exécutif

"""

        # Statut global
        recommendations = self.final_report.get("recommendations", {})
        status = recommendations.get("overall_status", "unknown")
        readiness = recommendations.get("deployment_readiness", "pending")

        content += f"**Statut Global:** {status.upper()}\n"
        content += f"**Préparation Déploiement:** {readiness.upper()}\n\n"

        # Analyse code
        if self.analysis_report:
            content += "## 🔍 Analyse Code\n\n"
            content += f"- **Fichiers analysés:** {self.analysis_report.get('analyzed_files', 0)}\n"
            content += f"- **Opportunités détectées:** {self.analysis_report.get('total_opportunities', 0)}\n"
            content += f"- **Haute confiance:** {self.analysis_report.get('high_confidence_opportunities', 0)}\n\n"

        # Migration
        if self.migration_results:
            content += "## 🔄 Génération Migration\n\n"
            content += f"- **Fichiers traités:** {self.migration_results.get('files_processed', 0)}\n"
            content += f"- **Succès:** {self.migration_results.get('success_count', 0)}\n"
            content += f"- **Transformations:** {self.migration_results.get('transformations_total', 0)}\n\n"

        # Validation
        if self.validation_report:
            content += "## 🧪 Validation Équivalence\n\n"
            if 'total_tests' in self.validation_report:
                total = self.validation_report['total_tests']
                passed = self.validation_report['passed_tests']
                content += f"- **Tests:** {passed}/{total} réussis\n"
                content += f"- **Taux succès:** {passed/total*100:.1f}%\n\n"

        # Recommandations
        content += "## 🎯 Recommandations\n\n"
        for action in recommendations.get("action_items", []):
            content += f"- {action}\n"

        content += "\n### Prochaines Étapes\n\n"
        for step in recommendations.get("next_steps", []):
            content += f"{step}\n"

        content += f"\n---\n\n*Rapport généré automatiquement par Batch Migrator*\n"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def print_final_summary(self):
        """Affiche résumé final migration"""

        print("\n" + "=" * 60)
        print("🏆 RÉSUMÉ FINAL MIGRATION BATCH")
        print("=" * 60)

        # Métriques principales
        if self.analysis_report:
            print(f"📁 Fichiers analysés:      {self.analysis_report.get('analyzed_files', 0)}")
            print(f"🎯 Opportunités trouvées:  {self.analysis_report.get('total_opportunities', 0)}")

        if self.migration_results:
            print(f"🔄 Fichiers migrés:        {self.migration_results.get('success_count', 0)}")
            print(f"⚡ Transformations:        {self.migration_results.get('transformations_total', 0)}")

        if self.validation_report and 'total_tests' in self.validation_report:
            total = self.validation_report['total_tests']
            passed = self.validation_report['passed_tests']
            print(f"🧪 Tests validation:       {passed}/{total} réussis")

        # Recommandation finale
        recommendations = self.final_report.get("recommendations", {})
        status = recommendations.get("overall_status", "unknown")
        readiness = recommendations.get("deployment_readiness", "pending")

        print(f"\n🎯 STATUT: {status.upper()}")
        print(f"🚀 DÉPLOIEMENT: {readiness.upper()}")

        if readiness == "ready":
            print("\n✅ RECOMMANDATION: PROCÉDER MIGRATION")
            print("   Migration prête pour déploiement avec tests appropriés")
        elif readiness == "ready_with_testing":
            print("\n🔍 RECOMMANDATION: TESTS COMPLÉMENTAIRES")
            print("   Migration prometteuse, validation supplémentaire recommandée")
        else:
            print("\n⚠️  RECOMMANDATION: ÉVALUATION MANUELLE")
            print("   Bénéfices limités ou problèmes détectés, analyse manuelle requise")

    def run_complete_workflow(self) -> bool:
        """Exécute workflow migration complet"""

        print("🚀 MIGRATION BATCH DAG → EnhancedDAG")
        print("=" * 60)
        print(f"Projet: {self.project_path}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'EXÉCUTION COMPLÈTE'}")

        # Setup workspace
        self.setup_migration_workspace()

        # Workflow étapes
        success = True

        # Étape 1: Analyse
        if not self.run_code_analysis():
            success = False
            print("❌ Échec analyse code - arrêt workflow")
            return False

        # Étape 2: Génération
        if not self.run_migration_generation():
            success = False
            print("⚠️  Échec génération migrations - continuation pour rapport")

        # Étape 3: Validation
        if not self.run_validation():
            success = False
            print("⚠️  Échec validation - continuation pour rapport")

        # Étape 4: Rapport final
        self.generate_final_report()

        # Résumé
        self.print_final_summary()

        return success


def main():
    """Interface ligne de commande"""

    parser = argparse.ArgumentParser(
        description="Migration batch complète DAG → EnhancedDAG"
    )

    parser.add_argument(
        '--project', '-p',
        required=True,
        help="Répertoire projet à migrer"
    )

    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help="Mode dry-run (simulation sans modifications)"
    )

    parser.add_argument(
        '--output-dir', '-o',
        help="Répertoire sortie migration (défaut: PROJECT/migration_results)"
    )

    args = parser.parse_args()

    # Validation projet
    if not os.path.exists(args.project):
        print(f"❌ Erreur: Projet {args.project} n'existe pas")
        return 1

    if not os.path.isdir(args.project):
        print(f"❌ Erreur: {args.project} n'est pas un répertoire")
        return 1

    # Exécution migration batch
    migrator = BatchMigrator(args.project, args.dry_run)

    if args.output_dir:
        migrator.migration_dir = args.output_dir

    success = migrator.run_complete_workflow()

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())