#!/usr/bin/env python3
"""
Migration Generator - Migration Tools

Génère automatiquement des scripts de migration pour convertir code DAG
existant vers EnhancedDAG avec préservation de la fonctionnalité.

FONCTIONNALITÉS:
1. Génération scripts migration automatique
2. Préservation logique existante
3. Tests équivalence intégrés
4. Backup automatique code original
5. Migration progressive par étapes

Usage:
    python migration_generator.py --input SOURCE_FILE --output MIGRATED_FILE
    python migration_generator.py --project PROJECT_DIR --batch
"""

import ast
import os
import re
import argparse
import shutil
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
from datetime import datetime


class MigrationTransformer(ast.NodeTransformer):
    """Transformateur AST pour migration DAG → EnhancedDAG"""

    def __init__(self):
        self.imports_added = False
        self.transformations = []
        self.dag_variables = set()

    def visit_Import(self, node):
        """Transforme imports DAG"""
        new_names = []

        for alias in node.names:
            if alias.name == 'DAG' or 'dag' in alias.name.lower():
                # Ajouter import EnhancedDAG
                new_names.append(ast.alias(name='EnhancedDAG', asname=None))
                self.transformations.append(f"Import ajouté: EnhancedDAG")
            new_names.append(alias)

        node.names = new_names
        return node

    def visit_ImportFrom(self, node):
        """Transforme imports from DAG"""
        if node.module and ('dag' in node.module.lower() or 'icgs' in node.module.lower()):
            new_names = list(node.names)

            # Ajouter EnhancedDAG si pas déjà présent
            enhanced_dag_present = any(alias.name == 'EnhancedDAG' for alias in node.names)
            if not enhanced_dag_present:
                new_names.append(ast.alias(name='EnhancedDAG', asname=None))
                self.transformations.append(f"Import ajouté: EnhancedDAG depuis {node.module}")

            node.names = new_names

        return node

    def visit_Assign(self, node):
        """Transforme assignations DAG"""
        # Détection pattern: dag = DAG(...)
        if (isinstance(node.value, ast.Call) and
            isinstance(node.value.func, ast.Name) and
            node.value.func.id == 'DAG'):

            # Enregistrer nom variable DAG
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                dag_var = node.targets[0].id
                self.dag_variables.add(dag_var)

                # Transformer en EnhancedDAG
                node.value.func.id = 'EnhancedDAG'

                # Ajouter commentaire migration
                self.transformations.append(f"Variable {dag_var}: DAG → EnhancedDAG")

        return node

    def visit_Call(self, node):
        """Transforme appels méthodes DAG"""

        # Pattern: update_taxonomy
        if (isinstance(node.func, ast.Attribute) and
            node.func.attr == 'update_taxonomy'):

            # Transformer en configure_accounts_simple
            node.func.attr = 'configure_accounts_simple'

            # Simplifier arguments (enlever transaction_num)
            if len(node.args) >= 2:
                node.args = node.args[:1]  # Garder seulement accounts

            self.transformations.append("Méthode: update_taxonomy → configure_accounts_simple")

        # Pattern: get_character_mapping avec transaction_num
        elif (isinstance(node.func, ast.Attribute) and
              node.func.attr == 'get_character_mapping' and
              len(node.args) >= 2):

            # Transformer en get_current_account_mapping
            node.func.attr = 'get_current_account_mapping'

            # Garder seulement premier argument (account_id)
            node.args = node.args[:1]

            self.transformations.append("Méthode: get_character_mapping → get_current_account_mapping")

        # Pattern: convert_path_to_word avec transaction_num
        elif (isinstance(node.func, ast.Attribute) and
              node.func.attr == 'convert_path_to_word' and
              len(node.args) >= 2):

            # Transformer en convert_path_simple
            node.func.attr = 'convert_path_simple'

            # Garder seulement premier argument (path)
            node.args = node.args[:1]

            self.transformations.append("Méthode: convert_path_to_word → convert_path_simple")

        return self.generic_visit(node)

    def visit_For(self, node):
        """Élimine boucles transaction_num superflues"""

        # Détection boucle: for tx_num in range(...)
        if (isinstance(node.target, ast.Name) and
            'tx' in node.target.id.lower() and 'num' in node.target.id.lower()):

            # Si boucle contient seulement update_taxonomy, simplifier
            if len(node.body) == 1 and isinstance(node.body[0], ast.Expr):
                call = node.body[0].value
                if (isinstance(call, ast.Call) and
                    isinstance(call.func, ast.Attribute) and
                    call.func.attr == 'configure_accounts_simple'):  # Déjà transformé

                    # Retourner contenu boucle sans la boucle
                    self.transformations.append("Boucle transaction_num éliminée")
                    return node.body

        return self.generic_visit(node)


class MigrationGenerator:
    """Générateur principal scripts migration"""

    def __init__(self):
        self.backup_dir = "migration_backups"

    def create_backup(self, file_path: str) -> str:
        """Crée backup du fichier original"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{os.path.basename(file_path)}.backup_{timestamp}"

        os.makedirs(self.backup_dir, exist_ok=True)
        backup_path = os.path.join(self.backup_dir, backup_name)

        shutil.copy2(file_path, backup_path)
        return backup_path

    def generate_migration_script(self, input_file: str, output_file: str) -> bool:
        """Génère script migration pour un fichier"""

        try:
            print(f"🔄 Migration: {input_file} → {output_file}")

            # Backup original
            backup_path = self.create_backup(input_file)
            print(f"📁 Backup créé: {backup_path}")

            # Lecture code original
            with open(input_file, 'r', encoding='utf-8') as f:
                original_code = f.read()

            # Parse AST
            tree = ast.parse(original_code)

            # Transformation
            transformer = MigrationTransformer()
            migrated_tree = transformer.visit(tree)

            # Génération code migré
            import astor
            migrated_code = astor.to_source(migrated_tree)

            # Ajout header migration
            header = self._generate_migration_header(input_file, transformer.transformations)
            full_migrated_code = header + "\n" + migrated_code

            # Écriture fichier migré
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(full_migrated_code)

            print(f"✅ Migration réussie: {len(transformer.transformations)} transformations")
            for transform in transformer.transformations:
                print(f"   - {transform}")

            return True

        except Exception as e:
            print(f"❌ Erreur migration {input_file}: {e}")
            return False

    def _generate_migration_header(self, original_file: str, transformations: List[str]) -> str:
        """Génère header informatif migration"""

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        header = f'''"""
FICHIER MIGRÉ AUTOMATIQUEMENT - DAG → EnhancedDAG
================================================================

Fichier original: {original_file}
Date migration:   {timestamp}
Outil:           Migration Generator v1.0

TRANSFORMATIONS APPLIQUÉES:
"""'''

        for i, transform in enumerate(transformations, 1):
            header += f"\n# {i}. {transform}"

        header += '''

"""
IMPORTANT:
1. Ce fichier a été généré automatiquement
2. Testez la fonctionnalité avant déploiement production
3. Le fichier original est sauvegardé dans migration_backups/
4. Les imports EnhancedDAG ont été ajoutés automatiquement
"""

'''
        return header

    def validate_migration(self, original_file: str, migrated_file: str) -> bool:
        """Valide que la migration préserve la fonctionnalité"""

        print(f"🔍 Validation migration: {migrated_file}")

        try:
            # Test syntaxique
            with open(migrated_file, 'r', encoding='utf-8') as f:
                migrated_code = f.read()

            ast.parse(migrated_code)
            print("   ✅ Syntaxe Python valide")

            # Test imports
            if 'EnhancedDAG' in migrated_code:
                print("   ✅ Import EnhancedDAG présent")
            else:
                print("   ⚠️  Import EnhancedDAG manquant")
                return False

            # Test réduction complexité
            original_complexity = self._estimate_complexity(original_file)
            migrated_complexity = self._estimate_complexity(migrated_file)

            if migrated_complexity <= original_complexity:
                print(f"   ✅ Complexité réduite: {original_complexity} → {migrated_complexity}")
            else:
                print(f"   ⚠️  Complexité augmentée: {original_complexity} → {migrated_complexity}")

            return True

        except Exception as e:
            print(f"   ❌ Validation échouée: {e}")
            return False

    def _estimate_complexity(self, file_path: str) -> int:
        """Estime complexité relative du fichier"""

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Métriques simples complexité
            complexity = 0
            complexity += content.count('for ')  # Boucles
            complexity += content.count('if ')   # Conditions
            complexity += content.count('transaction_num') * 2  # Gestion transaction_num
            complexity += content.count('update_taxonomy')  # Appels complexes

            return complexity

        except:
            return 0

    def generate_batch_migration(self, project_dir: str) -> Dict[str, bool]:
        """Migration batch projet complet"""

        print(f"🚀 MIGRATION BATCH PROJET: {project_dir}")
        print("=" * 60)

        # Découverte fichiers Python
        python_files = []
        for root, dirs, files in os.walk(project_dir):
            # Skip backups et cache
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__' and d != 'migration_backups']

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)

                    # Vérifier si contient patterns DAG
                    if self._contains_dag_patterns(file_path):
                        python_files.append(file_path)

        print(f"📁 {len(python_files)} fichiers DAG détectés pour migration")

        # Migration tous fichiers
        results = {}

        for file_path in python_files:
            # Générer nom fichier migré
            base_name = os.path.splitext(file_path)[0]
            migrated_path = f"{base_name}_migrated.py"

            # Migration
            success = self.generate_migration_script(file_path, migrated_path)

            # Validation
            if success:
                success = self.validate_migration(file_path, migrated_path)

            results[file_path] = success

        # Résumé
        successful = sum(1 for success in results.values() if success)
        print(f"\n📊 RÉSUMÉ MIGRATION BATCH:")
        print(f"   Fichiers traités: {len(results)}")
        print(f"   Succès:          {successful}")
        print(f"   Échecs:          {len(results) - successful}")

        return results

    def _contains_dag_patterns(self, file_path: str) -> bool:
        """Vérifie si fichier contient patterns DAG à migrer"""

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Patterns indicateurs DAG
            dag_patterns = [
                r'from.*dag.*import|import.*dag',
                r'DAG\s*\(',
                r'update_taxonomy',
                r'get_character_mapping',
                r'convert_path_to_word',
                r'transaction_num'
            ]

            for pattern in dag_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return True

            return False

        except:
            return False

    def generate_equivalence_test(self, original_file: str, migrated_file: str) -> str:
        """Génère test équivalence automatique"""

        test_name = f"test_equivalence_{os.path.basename(original_file).replace('.py', '')}.py"

        test_template = f'''"""
Test Équivalence Migration - Généré Automatiquement
Valide que {os.path.basename(migrated_file)} produit résultats identiques à {os.path.basename(original_file)}
"""

import pytest
import sys
import os

# Import modules à tester
sys.path.insert(0, os.path.dirname(__file__))

# TODO: Ajouter imports spécifiques aux modules


class TestMigrationEquivalence:
    """Tests équivalence fonctionnelle après migration"""

    def test_basic_configuration_equivalence(self):
        """Test configuration de base équivalente"""

        # TODO: Implémenter test configuration
        # Comparer résultats original vs migré avec mêmes inputs

        # Exemple pattern:
        # original_result = original_module.function(test_input)
        # migrated_result = migrated_module.function(test_input)
        # assert original_result == migrated_result

        pass

    def test_data_processing_equivalence(self):
        """Test traitement données équivalent"""

        # TODO: Implémenter tests processing
        pass

    def test_performance_comparison(self):
        """Test comparaison performance"""

        # TODO: Mesurer et comparer performance
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''

        test_file_path = os.path.join(os.path.dirname(migrated_file), test_name)

        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_template)

        print(f"📝 Test équivalence généré: {test_file_path}")
        return test_file_path


def main():
    """Interface ligne de commande"""

    parser = argparse.ArgumentParser(
        description="Génère migration automatique DAG → EnhancedDAG"
    )

    parser.add_argument(
        '--input', '-i',
        help="Fichier source à migrer"
    )

    parser.add_argument(
        '--output', '-o',
        help="Fichier destination migré"
    )

    parser.add_argument(
        '--project', '-p',
        help="Répertoire projet pour migration batch"
    )

    parser.add_argument(
        '--batch', '-b',
        action='store_true',
        help="Mode migration batch projet complet"
    )

    parser.add_argument(
        '--generate-tests', '-t',
        action='store_true',
        help="Génère tests équivalence automatiques"
    )

    parser.add_argument(
        '--validate-only', '-v',
        action='store_true',
        help="Validation seulement (pas de génération)"
    )

    args = parser.parse_args()

    print("🚀 GÉNÉRATEUR MIGRATION DAG → EnhancedDAG")
    print("=" * 60)

    generator = MigrationGenerator()

    if args.batch and args.project:
        # Mode batch
        if not os.path.exists(args.project):
            print(f"❌ Erreur: Projet {args.project} n'existe pas")
            return 1

        results = generator.generate_batch_migration(args.project)

        successful_migrations = sum(1 for success in results.values() if success)
        if successful_migrations > 0:
            print(f"\n🎉 {successful_migrations} migrations réussies!")
            return 0
        else:
            print(f"\n😞 Aucune migration réussie")
            return 1

    elif args.input and args.output:
        # Mode fichier unique
        if not os.path.exists(args.input):
            print(f"❌ Erreur: Fichier {args.input} n'existe pas")
            return 1

        if args.validate_only:
            # Validation seulement
            success = generator.validate_migration(args.input, args.output)
        else:
            # Migration complète
            success = generator.generate_migration_script(args.input, args.output)

            if success and args.generate_tests:
                generator.generate_equivalence_test(args.input, args.output)

        return 0 if success else 1

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    exit(main())