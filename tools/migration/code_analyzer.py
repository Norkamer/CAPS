#!/usr/bin/env python3
"""
Code Analyzer - Migration Tools

Analyse le code existant utilisant DAG pour identifier automatiquement
les opportunités de migration vers EnhancedDAG.

FONCTIONNALITÉS:
1. Détection patterns DAG originaux
2. Identification complexité évitable
3. Suggestions migration spécifiques
4. Estimation bénéfices migration
5. Génération rapports analyse

Usage:
    python code_analyzer.py [--path CODE_PATH] [--output REPORT_PATH]
"""

import ast
import os
import re
import argparse
import json
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class MigrationOpportunity:
    """Représente une opportunité de migration identifiée"""
    file_path: str
    line_number: int
    pattern_type: str
    description: str
    complexity_before: int
    complexity_after: int
    confidence: float
    suggested_replacement: str
    estimated_benefit: str


@dataclass
class AnalysisReport:
    """Rapport complet d'analyse migration"""
    analyzed_files: int
    total_opportunities: int
    high_confidence_opportunities: int
    estimated_total_benefit: Dict[str, int]
    opportunities_by_type: Dict[str, int]
    detailed_opportunities: List[MigrationOpportunity]


class DAGCodeAnalyzer(ast.NodeVisitor):
    """Analyseur AST pour identifier patterns DAG"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.opportunities = []
        self.current_line = 0
        self.dag_imports = set()
        self.dag_instances = set()

    def visit(self, node):
        """Visit AST node avec tracking numéro ligne"""
        if hasattr(node, 'lineno'):
            self.current_line = node.lineno
        super().visit(node)

    def visit_Import(self, node):
        """Détecte imports DAG"""
        for alias in node.names:
            if 'dag' in alias.name.lower() or 'icgs' in alias.name.lower():
                self.dag_imports.add(alias.name)

    def visit_ImportFrom(self, node):
        """Détecte imports from DAG"""
        if node.module and ('dag' in node.module.lower() or 'icgs' in node.module.lower()):
            for alias in node.names:
                self.dag_imports.add(alias.name)

    def visit_Call(self, node):
        """Détecte appels méthodes DAG problématiques"""

        # Pattern 1: DAG() construction
        if isinstance(node.func, ast.Name) and node.func.id == 'DAG':
            self.opportunities.append(MigrationOpportunity(
                file_path=self.file_path,
                line_number=self.current_line,
                pattern_type="dag_construction",
                description="Construction DAG peut être simplifiée avec EnhancedDAG",
                complexity_before=3,
                complexity_after=1,
                confidence=0.9,
                suggested_replacement="enhanced_dag = EnhancedDAG(config)",
                estimated_benefit="Configuration simplifiée"
            ))

        # Pattern 2: update_taxonomy avec boucle
        if (isinstance(node.func, ast.Attribute) and
            node.func.attr == 'update_taxonomy'):

            self.opportunities.append(MigrationOpportunity(
                file_path=self.file_path,
                line_number=self.current_line,
                pattern_type="update_taxonomy",
                description="update_taxonomy peut être remplacé par configure_accounts_simple",
                complexity_before=5,
                complexity_after=1,
                confidence=0.85,
                suggested_replacement="enhanced_dag.configure_accounts_simple(accounts)",
                estimated_benefit="Élimination boucle manuelle transaction_num"
            ))

        # Pattern 3: get_character_mapping avec transaction_num
        if (isinstance(node.func, ast.Attribute) and
            node.func.attr == 'get_character_mapping' and
            len(node.args) >= 2):

            self.opportunities.append(MigrationOpportunity(
                file_path=self.file_path,
                line_number=self.current_line,
                pattern_type="character_mapping_access",
                description="Accès mapping peut être simplifié sans transaction_num",
                complexity_before=2,
                complexity_after=1,
                confidence=0.8,
                suggested_replacement="enhanced_dag.get_current_account_mapping(account_id)",
                estimated_benefit="Élimination gestion manuelle transaction_num"
            ))

        # Pattern 4: convert_path_to_word avec transaction_num
        if (isinstance(node.func, ast.Attribute) and
            node.func.attr == 'convert_path_to_word' and
            len(node.args) >= 2):

            self.opportunities.append(MigrationOpportunity(
                file_path=self.file_path,
                line_number=self.current_line,
                pattern_type="path_conversion",
                description="Conversion path peut être simplifiée sans transaction_num",
                complexity_before=2,
                complexity_after=1,
                confidence=0.8,
                suggested_replacement="enhanced_dag.convert_path_simple(path)",
                estimated_benefit="API simplifiée conversion paths"
            ))

        self.generic_visit(node)

    def visit_For(self, node):
        """Détecte boucles transaction_num"""
        # Détection pattern: for tx_num in range(...)
        if (isinstance(node.target, ast.Name) and
            'tx' in node.target.id.lower() and 'num' in node.target.id.lower()):

            self.opportunities.append(MigrationOpportunity(
                file_path=self.file_path,
                line_number=self.current_line,
                pattern_type="transaction_num_loop",
                description="Boucle transaction_num peut être éliminée avec API simplifiée",
                complexity_before=8,
                complexity_after=2,
                confidence=0.9,
                suggested_replacement="# Boucle remplacée par configure_accounts_simple()",
                estimated_benefit="Élimination logique complexe transaction_num"
            ))

        self.generic_visit(node)


class MigrationAnalyzer:
    """Analyseur principal migration"""

    def __init__(self):
        self.total_files_analyzed = 0
        self.all_opportunities = []

    def analyze_file(self, file_path: str) -> List[MigrationOpportunity]:
        """Analyse un fichier Python pour opportunités migration"""

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            # Parse AST
            tree = ast.parse(source_code)

            # Analyse AST
            analyzer = DAGCodeAnalyzer(file_path)
            analyzer.visit(tree)

            # Analyse textuelle additionnelle
            text_opportunities = self._analyze_text_patterns(file_path, source_code)

            all_opportunities = analyzer.opportunities + text_opportunities
            self.all_opportunities.extend(all_opportunities)

            return all_opportunities

        except Exception as e:
            print(f"⚠️  Erreur analyse {file_path}: {e}")
            return []

    def _analyze_text_patterns(self, file_path: str, source_code: str) -> List[MigrationOpportunity]:
        """Analyse patterns textuels complémentaires"""
        opportunities = []
        lines = source_code.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Pattern: Commentaires indiquant complexité DAG
            if re.search(r'#.*(?:complex|difficult|transaction.*num)', line, re.IGNORECASE):
                opportunities.append(MigrationOpportunity(
                    file_path=file_path,
                    line_number=line_num,
                    pattern_type="complexity_comment",
                    description="Commentaire indique complexité pouvant être réduite",
                    complexity_before=3,
                    complexity_after=1,
                    confidence=0.6,
                    suggested_replacement="# Simplifié avec EnhancedDAG",
                    estimated_benefit="Réduction complexité cognitive"
                ))

            # Pattern: Variables transaction_num multiples
            if re.search(r'tx_num.*=|transaction_num.*=', line):
                opportunities.append(MigrationOpportunity(
                    file_path=file_path,
                    line_number=line_num,
                    pattern_type="transaction_num_variable",
                    description="Gestion manuelle transaction_num détectée",
                    complexity_before=2,
                    complexity_after=0,
                    confidence=0.7,
                    suggested_replacement="# Auto-géré par EnhancedDAG",
                    estimated_benefit="Élimination gestion manuelle"
                ))

        return opportunities

    def analyze_directory(self, directory_path: str, recursive: bool = True) -> AnalysisReport:
        """Analyse répertoire complet"""

        python_files = []

        if recursive:
            for root, dirs, files in os.walk(directory_path):
                # Skip __pycache__ et .git
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

                for file in files:
                    if file.endswith('.py'):
                        python_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory_path):
                if file.endswith('.py'):
                    python_files.append(os.path.join(directory_path, file))

        print(f"🔍 Analyse {len(python_files)} fichiers Python...")

        # Analyse tous les fichiers
        for file_path in python_files:
            print(f"   Analyse: {file_path}")
            self.analyze_file(file_path)
            self.total_files_analyzed += 1

        # Génération rapport
        return self._generate_report()

    def _generate_report(self) -> AnalysisReport:
        """Génère rapport complet d'analyse"""

        # Classification opportunités
        high_confidence = [opp for opp in self.all_opportunities if opp.confidence >= 0.8]

        # Groupement par type
        by_type = {}
        for opp in self.all_opportunities:
            by_type[opp.pattern_type] = by_type.get(opp.pattern_type, 0) + 1

        # Calcul bénéfices estimés
        total_complexity_reduction = sum(opp.complexity_before - opp.complexity_after
                                       for opp in self.all_opportunities)

        estimated_benefits = {
            'complexity_reduction_points': total_complexity_reduction,
            'lines_of_code_saved': len([opp for opp in self.all_opportunities
                                      if opp.pattern_type in ['transaction_num_loop', 'dag_construction']]),
            'error_prone_patterns_eliminated': len([opp for opp in self.all_opportunities
                                                  if opp.pattern_type in ['update_taxonomy', 'transaction_num_loop']]),
        }

        return AnalysisReport(
            analyzed_files=self.total_files_analyzed,
            total_opportunities=len(self.all_opportunities),
            high_confidence_opportunities=len(high_confidence),
            estimated_total_benefit=estimated_benefits,
            opportunities_by_type=by_type,
            detailed_opportunities=self.all_opportunities
        )

    def save_report(self, report: AnalysisReport, output_path: str):
        """Sauvegarde rapport au format JSON"""

        # Conversion en dict pour sérialisation
        report_dict = asdict(report)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        print(f"✅ Rapport sauvegardé: {output_path}")

    def print_summary(self, report: AnalysisReport):
        """Affiche résumé analyse"""

        print(f"\n📊 ANALYSE MIGRATION - RÉSUMÉ")
        print("=" * 50)
        print(f"Fichiers analysés:           {report.analyzed_files}")
        print(f"Opportunités totales:        {report.total_opportunities}")
        print(f"Haute confiance (≥80%):      {report.high_confidence_opportunities}")

        print(f"\n📈 BÉNÉFICES ESTIMÉS:")
        benefits = report.estimated_total_benefit
        print(f"  Réduction complexité:      {benefits['complexity_reduction_points']} points")
        print(f"  Lignes code économisées:   {benefits['lines_of_code_saved']}")
        print(f"  Patterns risqués éliminés: {benefits['error_prone_patterns_eliminated']}")

        print(f"\n🎯 OPPORTUNITÉS PAR TYPE:")
        for pattern_type, count in report.opportunities_by_type.items():
            print(f"  {pattern_type}: {count}")

        if report.high_confidence_opportunities > 0:
            print(f"\n✅ RECOMMANDATION: PROCÉDER MIGRATION")
            print(f"   {report.high_confidence_opportunities} opportunités haute confiance détectées")
        else:
            print(f"\n⚠️  RECOMMANDATION: ÉVALUER MANUELLEMENT")
            print(f"   Opportunités détectées mais nécessitent validation")


def main():
    """Interface ligne commande"""

    parser = argparse.ArgumentParser(
        description="Analyse code DAG pour opportunités migration EnhancedDAG"
    )

    parser.add_argument(
        '--path', '-p',
        default='.',
        help="Chemin code à analyser (défaut: répertoire courant)"
    )

    parser.add_argument(
        '--output', '-o',
        default='migration_analysis_report.json',
        help="Chemin rapport sortie (défaut: migration_analysis_report.json)"
    )

    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help="Analyse récursive sous-répertoires"
    )

    parser.add_argument(
        '--detailed', '-d',
        action='store_true',
        help="Affichage détaillé opportunités"
    )

    args = parser.parse_args()

    print("🚀 ANALYSEUR MIGRATION DAG → EnhancedDAG")
    print("=" * 60)

    # Validation chemin
    if not os.path.exists(args.path):
        print(f"❌ Erreur: Chemin {args.path} n'existe pas")
        return 1

    # Analyse
    analyzer = MigrationAnalyzer()

    if os.path.isfile(args.path):
        # Analyse fichier unique
        opportunities = analyzer.analyze_file(args.path)
        analyzer.total_files_analyzed = 1
        report = analyzer._generate_report()
    else:
        # Analyse répertoire
        report = analyzer.analyze_directory(args.path, args.recursive)

    # Affichage résumé
    analyzer.print_summary(report)

    # Affichage détaillé si demandé
    if args.detailed and report.detailed_opportunities:
        print(f"\n🔍 OPPORTUNITÉS DÉTAILLÉES:")
        print("-" * 60)

        for i, opp in enumerate(report.detailed_opportunities[:10], 1):  # Limiter à 10
            print(f"{i}. {opp.file_path}:{opp.line_number}")
            print(f"   Type: {opp.pattern_type}")
            print(f"   Description: {opp.description}")
            print(f"   Confiance: {opp.confidence:.0%}")
            print(f"   Suggestion: {opp.suggested_replacement}")
            print()

        if len(report.detailed_opportunities) > 10:
            print(f"   ... et {len(report.detailed_opportunities) - 10} autres opportunités")

    # Sauvegarde rapport
    analyzer.save_report(report, args.output)

    return 0


if __name__ == "__main__":
    exit(main())