"""
Métadonnées et Structure d'État des Simulations ICGS

Classes pour gérer les métadonnées des simulations sauvegardées
et la structure complète de l'état sérialisable.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional
from decimal import Decimal


@dataclass
class SimulationMetadata:
    """
    Métadonnées complètes d'une simulation sauvegardée

    Contient toutes les informations nécessaires pour identifier,
    organiser et prévisualiser une simulation sans charger son état complet.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    created_date: datetime = field(default_factory=datetime.now)
    modified_date: datetime = field(default_factory=datetime.now)

    # Configuration simulation
    agents_mode: str = "7_agents"
    scenario_type: str = "simple"
    flow_intensity: float = 0.7

    # Statistiques simulation
    agents_count: int = 0
    transactions_count: int = 0
    total_balance: Decimal = field(default_factory=lambda: Decimal('0'))
    sectors_distribution: Dict[str, int] = field(default_factory=dict)

    # Métriques performance
    performance_metrics: Dict[str, Any] = field(default_factory=dict)

    # Organisation et tags
    tags: List[str] = field(default_factory=list)
    category: str = "user_simulation"  # user_simulation, template, test

    # Version et compatibilité
    format_version: str = "1.0"
    icgs_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convertit les métadonnées en dictionnaire sérialisable"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_date': self.created_date.isoformat(),
            'modified_date': self.modified_date.isoformat(),
            'agents_mode': self.agents_mode,
            'scenario_type': self.scenario_type,
            'flow_intensity': self.flow_intensity,
            'agents_count': self.agents_count,
            'transactions_count': self.transactions_count,
            'total_balance': str(self.total_balance),
            'sectors_distribution': self.sectors_distribution,
            'performance_metrics': self.performance_metrics,
            'tags': self.tags,
            'category': self.category,
            'format_version': self.format_version,
            'icgs_version': self.icgs_version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimulationMetadata':
        """Crée une instance depuis un dictionnaire"""
        metadata = cls()
        metadata.id = data.get('id', str(uuid.uuid4()))
        metadata.name = data.get('name', '')
        metadata.description = data.get('description', '')

        # Dates
        if 'created_date' in data:
            metadata.created_date = datetime.fromisoformat(data['created_date'])
        if 'modified_date' in data:
            metadata.modified_date = datetime.fromisoformat(data['modified_date'])

        # Configuration
        metadata.agents_mode = data.get('agents_mode', '7_agents')
        metadata.scenario_type = data.get('scenario_type', 'simple')
        metadata.flow_intensity = data.get('flow_intensity', 0.7)

        # Statistiques
        metadata.agents_count = data.get('agents_count', 0)
        metadata.transactions_count = data.get('transactions_count', 0)
        metadata.total_balance = Decimal(data.get('total_balance', '0'))
        metadata.sectors_distribution = data.get('sectors_distribution', {})
        metadata.performance_metrics = data.get('performance_metrics', {})

        # Organisation
        metadata.tags = data.get('tags', [])
        metadata.category = data.get('category', 'user_simulation')

        # Version
        metadata.format_version = data.get('format_version', '1.0')
        metadata.icgs_version = data.get('icgs_version', '1.0')

        return metadata

    def update_from_simulation(self, simulation):
        """Met à jour les métadonnées depuis une instance EconomicSimulation"""
        from ..api.icgs_bridge import EconomicSimulation

        if not isinstance(simulation, EconomicSimulation):
            raise ValueError("L'objet fourni n'est pas une EconomicSimulation")

        # Configuration
        self.agents_mode = simulation.agents_mode

        # Statistiques
        self.agents_count = len(simulation.agents)
        self.transactions_count = len(simulation.transactions)

        # Calcul balance totale
        total_balance = Decimal('0')
        sectors_dist = {}

        for agent in simulation.agents.values():
            total_balance += agent.balance
            sector = agent.sector
            sectors_dist[sector] = sectors_dist.get(sector, 0) + 1

        self.total_balance = total_balance
        self.sectors_distribution = sectors_dist

        # Métriques performance si disponibles
        try:
            self.performance_metrics = simulation.get_simulation_metrics()
        except:
            self.performance_metrics = {}

        # Mise à jour date modification
        self.modified_date = datetime.now()


@dataclass
class SimulationState:
    """
    État complet sérialisable d'une simulation

    Contient toutes les données nécessaires pour restaurer complètement
    une simulation : agents, transactions, état DAG, etc.
    """
    metadata: SimulationMetadata

    # État agents
    agents: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # État transactions
    transactions: List[Dict[str, Any]] = field(default_factory=list)

    # État Character Set Manager
    character_set_state: Dict[str, Any] = field(default_factory=dict)

    # État DAG
    dag_state: Dict[str, Any] = field(default_factory=dict)

    # Configuration taxonomie
    taxonomy_state: Dict[str, Any] = field(default_factory=dict)

    # Métriques et cache (optionnel)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'état complet en dictionnaire sérialisable"""
        return {
            'metadata': self.metadata.to_dict(),
            'agents': self.agents,
            'transactions': self.transactions,
            'character_set_state': self.character_set_state,
            'dag_state': self.dag_state,
            'taxonomy_state': self.taxonomy_state,
            'performance_metrics': self.performance_metrics
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimulationState':
        """Crée une instance depuis un dictionnaire"""
        metadata = SimulationMetadata.from_dict(data.get('metadata', {}))

        return cls(
            metadata=metadata,
            agents=data.get('agents', {}),
            transactions=data.get('transactions', []),
            character_set_state=data.get('character_set_state', {}),
            dag_state=data.get('dag_state', {}),
            taxonomy_state=data.get('taxonomy_state', {}),
            performance_metrics=data.get('performance_metrics', {})
        )

    def validate_integrity(self) -> bool:
        """
        Valide l'intégrité de l'état de simulation

        Returns:
            bool: True si l'état est cohérent, False sinon
        """
        try:
            # Validation métadonnées
            if not self.metadata.id or not self.metadata.format_version:
                return False

            # Validation cohérence agents/transactions
            agent_ids = set(self.agents.keys())
            for transaction in self.transactions:
                source_id = transaction.get('source_account_id')
                target_id = transaction.get('target_account_id')

                # Vérifier que les agents des transactions existent
                if source_id and source_id not in agent_ids:
                    return False
                if target_id and target_id not in agent_ids:
                    return False

            # Validation métadonnées vs données
            if self.metadata.agents_count != len(self.agents):
                return False
            if self.metadata.transactions_count != len(self.transactions):
                return False

            return True

        except Exception:
            return False

    def get_summary(self) -> Dict[str, Any]:
        """Retourne un résumé de l'état pour prévisualisation"""
        return {
            'simulation_id': self.metadata.id,
            'name': self.metadata.name,
            'agents_mode': self.metadata.agents_mode,
            'agents_count': len(self.agents),
            'transactions_count': len(self.transactions),
            'sectors': list(self.metadata.sectors_distribution.keys()),
            'total_balance': str(self.metadata.total_balance),
            'created_date': self.metadata.created_date.isoformat(),
            'is_valid': self.validate_integrity()
        }