"""
Sérialiseur de Simulations ICGS

Gère la sérialisation/désérialisation des objets EconomicSimulation
vers/depuis l'état persistant SimulationState.
"""

from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime

from .metadata import SimulationMetadata, SimulationState
from ..api.icgs_bridge import EconomicSimulation


class SimulationSerializer:
    """
    Sérialiseur pour les simulations économiques ICGS

    Responsable de la conversion bidirectionnelle entre:
    - EconomicSimulation (objet actif en mémoire)
    - SimulationState (état sérialisable pour persistance)
    """

    def serialize(self, simulation: EconomicSimulation, metadata: SimulationMetadata = None) -> SimulationState:
        """
        Sérialise une simulation vers un état persistant

        Args:
            simulation: Instance EconomicSimulation à sérialiser
            metadata: Métadonnées optionnelles (créées automatiquement si None)

        Returns:
            SimulationState: État sérialisable complet
        """
        if metadata is None:
            metadata = SimulationMetadata()
            metadata.update_from_simulation(simulation)
        else:
            metadata.update_from_simulation(simulation)

        # Sérialisation des agents
        agents_data = {}
        for agent_id, agent in simulation.agents.items():
            agents_data[agent_id] = {
                'id': agent.agent_id,
                'balance': str(agent.balance),
                'sector': agent.sector,
                'transactions_sent': len([tx for tx in simulation.transactions if tx.source_account_id == agent_id]),
                'transactions_received': len([tx for tx in simulation.transactions if tx.target_account_id == agent_id])
            }

        # Sérialisation des transactions
        transactions_data = []
        for transaction in simulation.transactions:
            tx_data = {
                'id': transaction.transaction_id,
                'source_account_id': transaction.source_account_id,
                'target_account_id': transaction.target_account_id,
                'amount': str(transaction.amount),
                'timestamp': transaction.timestamp.isoformat() if hasattr(transaction, 'timestamp') else datetime.now().isoformat(),
                'status': getattr(transaction, 'status', 'pending')
            }
            transactions_data.append(tx_data)

        # Sérialisation Character Set Manager
        character_set_state = {}
        if hasattr(simulation, 'character_set_manager') and simulation.character_set_manager:
            csm = simulation.character_set_manager
            character_set_state = {
                'is_frozen': getattr(csm, 'is_frozen', False),
                'total_capacity': getattr(csm, 'total_capacity', 0),
            }
            # Sérialiser les statistiques si disponibles
            try:
                character_set_state['statistics'] = csm.get_allocation_statistics()
            except:
                character_set_state['statistics'] = {}

        # Sérialisation DAG state (si disponible)
        dag_state = {}
        if hasattr(simulation, 'dag') and simulation.dag:
            dag_state = {
                'nodes_count': len(getattr(simulation.dag, 'nodes', {})),
                'edges_count': len(getattr(simulation.dag, 'edges', {})),
                'validation_cache_size': len(getattr(simulation.dag, '_validation_cache', {})) if hasattr(simulation.dag, '_validation_cache') else 0
            }

        # Sérialisation taxonomie (si disponible)
        taxonomy_state = {}
        if hasattr(simulation, '_taxonomy_configured') and simulation._taxonomy_configured:
            taxonomy_state = {
                'configured': True,
                'patterns_count': len(getattr(simulation, 'character_set_manager', {}).get('patterns', {})) if hasattr(simulation, 'character_set_manager') else 0
            }

        # Métriques de performance
        performance_metrics = {}
        try:
            if hasattr(simulation, 'get_simulation_metrics'):
                performance_metrics = simulation.get_simulation_metrics()
        except:
            # Si les métriques ne sont pas disponibles, calculer des métriques basiques
            performance_metrics = {
                'agents_count': len(simulation.agents),
                'transactions_count': len(simulation.transactions),
                'total_balance': str(sum(agent.balance for agent in simulation.agents.values())),
                'serialization_timestamp': datetime.now().isoformat()
            }

        return SimulationState(
            metadata=metadata,
            agents=agents_data,
            transactions=transactions_data,
            character_set_state=character_set_state,
            dag_state=dag_state,
            taxonomy_state=taxonomy_state,
            performance_metrics=performance_metrics
        )

    def deserialize(self, state: SimulationState) -> EconomicSimulation:
        """
        Désérialise un état persistant vers une simulation active

        Args:
            state: État sérialisé à restaurer

        Returns:
            EconomicSimulation: Instance restaurée
        """
        # Créer nouvelle simulation avec la configuration appropriée
        simulation = EconomicSimulation(
            simulation_id=state.metadata.name or f"restored_{state.metadata.id[:8]}",
            agents_mode=state.metadata.agents_mode
        )

        # Restaurer les agents
        for agent_id, agent_data in state.agents.items():
            try:
                balance = Decimal(agent_data['balance'])
                simulation.create_agent(
                    agent_id=agent_id,
                    sector=agent_data['sector'],
                    balance=balance
                )
            except Exception as e:
                print(f"Warning: Could not restore agent {agent_id}: {e}")

        # Restaurer Character Set Manager state si disponible
        if state.character_set_state and hasattr(simulation, 'character_set_manager'):
            csm = simulation.character_set_manager
            if 'is_frozen' in state.character_set_state:
                if hasattr(csm, 'is_frozen'):
                    csm.is_frozen = state.character_set_state['is_frozen']

        # Configurer la taxonomie si elle était configurée
        if state.taxonomy_state.get('configured', False):
            try:
                simulation._configure_taxonomy_batch()
            except Exception as e:
                print(f"Warning: Could not restore taxonomy configuration: {e}")

        # Restaurer les transactions (après configuration taxonomie)
        for tx_data in state.transactions:
            try:
                source_id = tx_data['source_account_id']
                target_id = tx_data['target_account_id']
                amount = Decimal(tx_data['amount'])

                # Vérifier que les agents existent
                if source_id in simulation.agents and target_id in simulation.agents:
                    tx_id = simulation.create_transaction(source_id, target_id, amount)
                    # Note: Les IDs de transaction peuvent être différents après restauration

            except Exception as e:
                print(f"Warning: Could not restore transaction {tx_data.get('id', 'unknown')}: {e}")

        return simulation

    def validate_serialization(self, original: EconomicSimulation, deserialized: EconomicSimulation) -> Dict[str, bool]:
        """
        Valide qu'une sérialisation/désérialisation préserve l'intégrité

        Args:
            original: Simulation originale
            deserialized: Simulation après sérialisation/désérialisation

        Returns:
            Dict avec résultats de validation
        """
        validation_results = {
            'agents_count_match': len(original.agents) == len(deserialized.agents),
            'agents_ids_match': set(original.agents.keys()) == set(deserialized.agents.keys()),
            'transactions_count_match': len(original.transactions) == len(deserialized.transactions),
            'total_balance_match': True,
            'sectors_match': True
        }

        # Validation balances
        try:
            original_total = sum(agent.balance for agent in original.agents.values())
            deserialized_total = sum(agent.balance for agent in deserialized.agents.values())
            validation_results['total_balance_match'] = original_total == deserialized_total
        except Exception:
            validation_results['total_balance_match'] = False

        # Validation secteurs
        try:
            original_sectors = {agent.sector for agent in original.agents.values()}
            deserialized_sectors = {agent.sector for agent in deserialized.agents.values()}
            validation_results['sectors_match'] = original_sectors == deserialized_sectors
        except Exception:
            validation_results['sectors_match'] = False

        # Score global
        validation_results['overall_success'] = all(validation_results.values())

        return validation_results

    def get_serialization_info(self, state: SimulationState) -> Dict[str, Any]:
        """
        Retourne des informations sur un état sérialisé

        Args:
            state: État sérialisé à analyser

        Returns:
            Dict avec informations sur l'état
        """
        return {
            'metadata': {
                'id': state.metadata.id,
                'name': state.metadata.name,
                'agents_mode': state.metadata.agents_mode,
                'created_date': state.metadata.created_date.isoformat(),
                'format_version': state.metadata.format_version
            },
            'data_summary': {
                'agents_count': len(state.agents),
                'transactions_count': len(state.transactions),
                'has_character_set_state': bool(state.character_set_state),
                'has_dag_state': bool(state.dag_state),
                'has_taxonomy_state': bool(state.taxonomy_state)
            },
            'integrity_status': state.validate_integrity()
        }