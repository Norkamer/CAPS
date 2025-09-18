"""
Gestionnaire de Stockage des Simulations ICGS

Gère le stockage persistant des simulations sur le système de fichiers.
"""

import os
import json
import gzip
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import shutil

from .metadata import SimulationMetadata, SimulationState


class SimulationStorage:
    """
    Gestionnaire de stockage persistant pour les simulations ICGS

    Organise le stockage en dossiers séparés :
    - metadata/ : Métadonnées JSON légères pour listing rapide
    - states/ : États complets (optionnellement compressés)
    - exports/ : Exports pour partage/analyse externe
    """

    def __init__(self, base_path: str = None):
        """
        Initialise le gestionnaire de stockage

        Args:
            base_path: Chemin de base pour stockage (défaut: ./simulations/)
        """
        self.base_path = Path(base_path or "./simulations")
        self.metadata_path = self.base_path / "metadata"
        self.states_path = self.base_path / "states"
        self.exports_path = self.base_path / "exports"

        # Créer les dossiers si nécessaires
        self._ensure_directories()

    def _ensure_directories(self):
        """Crée les dossiers de stockage si ils n'existent pas"""
        self.base_path.mkdir(exist_ok=True)
        self.metadata_path.mkdir(exist_ok=True)
        self.states_path.mkdir(exist_ok=True)
        self.exports_path.mkdir(exist_ok=True)

    def save_simulation(self, state: SimulationState, compress: bool = True) -> str:
        """
        Sauvegarde une simulation complète

        Args:
            state: État de simulation à sauvegarder
            compress: Compresser l'état complet (recommandé)

        Returns:
            str: ID de simulation sauvegardée
        """
        simulation_id = state.metadata.id

        # Mise à jour date de modification
        state.metadata.modified_date = datetime.now()

        # Sauvegarder métadonnées (JSON léger)
        metadata_file = self.metadata_path / f"{simulation_id}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(state.metadata.to_dict(), f, indent=2, ensure_ascii=False)

        # Sauvegarder état complet
        state_file = self.states_path / f"{simulation_id}.json"
        state_data = state.to_dict()

        if compress:
            # Sauvegarde compressée
            state_file = state_file.with_suffix('.json.gz')
            with gzip.open(state_file, 'wt', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
        else:
            # Sauvegarde non compressée
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)

        return simulation_id

    def load_simulation(self, simulation_id: str) -> SimulationState:
        """
        Charge une simulation complète

        Args:
            simulation_id: ID de la simulation à charger

        Returns:
            SimulationState: État de simulation chargé

        Raises:
            FileNotFoundError: Si la simulation n'existe pas
            ValueError: Si l'état est corrompu
        """
        # Chercher fichier état (compressé ou non)
        state_file_gz = self.states_path / f"{simulation_id}.json.gz"
        state_file = self.states_path / f"{simulation_id}.json"

        if state_file_gz.exists():
            with gzip.open(state_file_gz, 'rt', encoding='utf-8') as f:
                state_data = json.load(f)
        elif state_file.exists():
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
        else:
            raise FileNotFoundError(f"Simulation {simulation_id} not found")

        # Reconstruire l'état
        state = SimulationState.from_dict(state_data)

        # Validation de l'intégrité
        if not state.validate_integrity():
            raise ValueError(f"Simulation state {simulation_id} is corrupted")

        return state

    def load_metadata(self, simulation_id: str) -> SimulationMetadata:
        """
        Charge uniquement les métadonnées d'une simulation

        Args:
            simulation_id: ID de la simulation

        Returns:
            SimulationMetadata: Métadonnées de la simulation
        """
        metadata_file = self.metadata_path / f"{simulation_id}.json"

        if not metadata_file.exists():
            raise FileNotFoundError(f"Metadata for simulation {simulation_id} not found")

        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata_data = json.load(f)

        return SimulationMetadata.from_dict(metadata_data)

    def list_simulations(self, filter_category: str = None) -> List[SimulationMetadata]:
        """
        Liste toutes les simulations disponibles

        Args:
            filter_category: Filtrer par catégorie (optionnel)

        Returns:
            List[SimulationMetadata]: Liste des métadonnées
        """
        simulations = []

        for metadata_file in self.metadata_path.glob("*.json"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata_data = json.load(f)

                metadata = SimulationMetadata.from_dict(metadata_data)

                # Filtrage par catégorie si spécifié
                if filter_category and metadata.category != filter_category:
                    continue

                simulations.append(metadata)
            except Exception as e:
                print(f"Warning: Could not load metadata from {metadata_file}: {e}")

        # Tri par date de modification (plus récent en premier)
        simulations.sort(key=lambda x: x.modified_date, reverse=True)
        return simulations

    def delete_simulation(self, simulation_id: str) -> bool:
        """
        Supprime une simulation complètement

        Args:
            simulation_id: ID de la simulation à supprimer

        Returns:
            bool: True si supprimé avec succès
        """
        deleted_any = False

        # Supprimer métadonnées
        metadata_file = self.metadata_path / f"{simulation_id}.json"
        if metadata_file.exists():
            metadata_file.unlink()
            deleted_any = True

        # Supprimer état (compressé ou non)
        for state_file in [
            self.states_path / f"{simulation_id}.json",
            self.states_path / f"{simulation_id}.json.gz"
        ]:
            if state_file.exists():
                state_file.unlink()
                deleted_any = True

        # Supprimer exports éventuels
        for export_file in self.exports_path.glob(f"{simulation_id}.*"):
            export_file.unlink()
            deleted_any = True

        return deleted_any

    def export_simulation(self, simulation_id: str, export_format: str = "json") -> str:
        """
        Exporte une simulation dans un format spécifique

        Args:
            simulation_id: ID de la simulation à exporter
            export_format: Format d'export ("json", "csv", "yaml")

        Returns:
            str: Chemin du fichier exporté
        """
        state = self.load_simulation(simulation_id)
        export_filename = f"{simulation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{export_format}"
        export_path = self.exports_path / export_filename

        if export_format == "json":
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)

        elif export_format == "csv":
            # Export CSV des agents et transactions
            import csv
            csv_path = export_path.with_suffix('.csv')
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # En-têtes agents
                writer.writerow(['Type', 'ID', 'Sector', 'Balance'])
                for agent_id, agent_data in state.agents.items():
                    writer.writerow(['Agent', agent_id, agent_data['sector'], agent_data['balance']])

                # Séparateur
                writer.writerow([])

                # En-têtes transactions
                writer.writerow(['Type', 'ID', 'Source', 'Target', 'Amount'])
                for tx in state.transactions:
                    writer.writerow(['Transaction', tx['id'], tx['source_account_id'], tx['target_account_id'], tx['amount']])

            export_path = csv_path

        else:
            raise ValueError(f"Unsupported export format: {export_format}")

        return str(export_path)

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques de stockage

        Returns:
            Dict avec statistiques du stockage
        """
        metadata_count = len(list(self.metadata_path.glob("*.json")))
        states_count = len(list(self.states_path.glob("*.json*")))
        exports_count = len(list(self.exports_path.glob("*")))

        # Calcul taille totale
        total_size = 0
        for path in [self.metadata_path, self.states_path, self.exports_path]:
            for file_path in path.glob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size

        return {
            'base_path': str(self.base_path),
            'simulations_count': metadata_count,
            'files': {
                'metadata': metadata_count,
                'states': states_count,
                'exports': exports_count
            },
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        }

    def cleanup_orphaned_files(self) -> Dict[str, int]:
        """
        Nettoie les fichiers orphelins (états sans métadonnées)

        Returns:
            Dict avec nombre de fichiers nettoyés
        """
        metadata_ids = {f.stem for f in self.metadata_path.glob("*.json")}

        cleaned = {
            'orphaned_states': 0,
            'orphaned_exports': 0
        }

        # Nettoyer états orphelins
        for state_file in self.states_path.glob("*.json*"):
            sim_id = state_file.stem.replace('.json', '')  # Retire .json de .json.gz
            if sim_id not in metadata_ids:
                state_file.unlink()
                cleaned['orphaned_states'] += 1

        # Nettoyer exports orphelins
        for export_file in self.exports_path.glob("*"):
            # Extraire simulation_id du nom de fichier export
            parts = export_file.name.split('_')
            if len(parts) >= 2:
                sim_id = '_'.join(parts[:-2])  # Retire timestamp du nom
                if sim_id not in metadata_ids:
                    export_file.unlink()
                    cleaned['orphaned_exports'] += 1

        return cleaned

    def backup_storage(self, backup_path: str = None) -> str:
        """
        Crée une sauvegarde complète du stockage

        Args:
            backup_path: Chemin de la sauvegarde (défaut: ./simulations_backup_YYYYMMDD_HHMMSS)

        Returns:
            str: Chemin de la sauvegarde créée
        """
        if backup_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"./simulations_backup_{timestamp}"

        backup_path = Path(backup_path)

        # Copie récursive complète
        shutil.copytree(self.base_path, backup_path, dirs_exist_ok=True)

        return str(backup_path)