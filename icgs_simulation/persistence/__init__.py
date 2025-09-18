"""
Module de Persistance ICGS - Sauvegarde et Chargement des Simulations

Ce module fournit les fonctionnalités de sérialisation, stockage et chargement
des simulations économiques ICGS.

Composants principaux:
- SimulationMetadata : Métadonnées des simulations
- SimulationState : État complet sérialisable
- SimulationSerializer : Sérialisation/désérialisation
- SimulationStorage : Gestionnaire stockage persistant

Usage:
    from icgs_simulation.persistence import SimulationStorage, SimulationSerializer

    storage = SimulationStorage()
    serializer = SimulationSerializer()

    # Sauvegarder simulation
    state = serializer.serialize(simulation)
    sim_id = storage.save_simulation(state, metadata)

    # Charger simulation
    loaded_state = storage.load_simulation(sim_id)
    simulation = serializer.deserialize(loaded_state)
"""

from .metadata import SimulationMetadata, SimulationState
from .simulation_serializer import SimulationSerializer
from .simulation_storage import SimulationStorage

__all__ = [
    'SimulationMetadata',
    'SimulationState',
    'SimulationSerializer',
    'SimulationStorage'
]

__version__ = "1.0.0"