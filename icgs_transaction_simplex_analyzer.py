#!/usr/bin/env python3
"""
ICGS Transaction Simplex Analyzer
================================

Analyseur spécialisé pour extraire et analyser les données Simplex
d'une transaction individuelle ou d'une séquence de transactions.

Fonctionnalités:
- Analyse détaillée d'une transaction avec comptage étapes Simplex
- Extraction données animation parcours algorithme
- Génération séquence simulation complète enchaînée
- Support animation bi-phasée : résolution + transition

Integration:
- Interface avec icgs_simplex_3d_api.py pour données authentiques
- Compatible avec icgs_bridge.py pour simulation
- Fournit données pour interface 3D animation
"""

import sys
import os
import time
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# Import modules ICGS
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))
from icgs_simulation.api.icgs_bridge import EconomicSimulation, SimulationMode

# Import API Simplex 3D si disponible
try:
    from icgs_simplex_3d_api import (
        Simplex3DCollector, SimplexState3D, SimplexTransition3D,
        SimplexTransitionType, ConstraintClass3D
    )
    SIMPLEX_3D_AVAILABLE = True
except ImportError:
    SIMPLEX_3D_AVAILABLE = False
    logging.warning("⚠️  icgs_simplex_3d_api non disponible - fallback vers simulation basique")


class TransactionComplexity(Enum):
    """Classification complexité transaction pour estimation durée"""
    LOW = "LOW"          # < 5 étapes Simplex
    MEDIUM = "MEDIUM"    # 5-15 étapes
    HIGH = "HIGH"        # 15-30 étapes
    EXTREME = "EXTREME"  # > 30 étapes


class AnimationPhase(Enum):
    """Phases animation Simplex"""
    RESOLUTION = "RESOLUTION"      # Résolution transaction individuelle
    TRANSITION = "TRANSITION"      # Transition vers transaction suivante
    CASCADE = "CASCADE"            # Impact cascade sur autres comptes


@dataclass
class TransactionSimplexData:
    """Données complètes Simplex pour une transaction"""
    transaction_id: str
    step_count: int
    estimated_duration_ms: int
    complexity: TransactionComplexity

    # Données animation
    simplex_steps: List[Dict[str, Any]] = field(default_factory=list)
    optimal_solution: Optional[Dict[str, Any]] = None
    convergence_info: Optional[Dict[str, Any]] = None

    # Métadonnées économiques
    source_account: str = ""
    target_account: str = ""
    amount: Decimal = Decimal('0')
    feasible: bool = False

    # Performance metrics
    actual_solving_time_ms: float = 0.0
    iterations_used: int = 0
    pivot_count: int = 0


@dataclass
class SimulationSequenceData:
    """Séquence complète simulation avec enchaînement transactions"""
    simulation_id: str
    total_transactions: int
    total_steps: int
    estimated_duration_ms: int

    # Transactions avec leurs données Simplex
    transactions: List[TransactionSimplexData] = field(default_factory=list)

    # Points de transition inter-transactions
    transition_points: List[Dict[str, Any]] = field(default_factory=list)

    # Métriques globales
    sequence_metadata: Dict[str, Any] = field(default_factory=dict)


class TransactionSimplexAnalyzer:
    """
    Analyseur principal pour extraction données Simplex transactions

    Features:
    - Analyse transaction individuelle avec comptage étapes précis
    - Génération données animation 3D compatibles Three.js
    - Support séquence simulation complète
    - Estimation durée et complexité automatique
    """

    def __init__(self, simulation: Optional[EconomicSimulation] = None):
        self.simulation = simulation
        self.simplex_3d_collector = None

        # Initialiser collecteur 3D si disponible
        if SIMPLEX_3D_AVAILABLE and simulation:
            self.simplex_3d_collector = Simplex3DCollector()
            # Connecter au solver si possible
            if hasattr(simulation, 'bridge') and hasattr(simulation.bridge, 'simplex_solver'):
                self.simplex_3d_collector.attach_to_solver(simulation.bridge.simplex_solver)

        # Cache pour éviter recalculs
        self._transaction_cache: Dict[str, TransactionSimplexData] = {}
        self._simulation_sequence_cache: Optional[SimulationSequenceData] = None

    def get_transaction_step_count(self, transaction_id: str) -> int:
        """
        Compte le nombre d'étapes Simplex pour une transaction

        Args:
            transaction_id: ID de la transaction à analyser

        Returns:
            Nombre d'étapes du parcours Simplex (pivots + convergence)
        """
        if not self.simulation:
            return 0

        try:
            # Valider transaction et capturer étapes
            validation_result = self.simulation.validate_transaction(
                transaction_id, SimulationMode.FEASIBILITY
            )

            if not validation_result.success:
                return 0

            # Extraire étapes depuis collecteur 3D si disponible
            if self.simplex_3d_collector and self.simplex_3d_collector.states_history:
                return len(self.simplex_3d_collector.states_history)

            # Fallback: estimation basée sur complexité transaction
            return self._estimate_step_count_fallback(transaction_id)

        except Exception as e:
            logging.error(f"❌ Erreur comptage étapes transaction {transaction_id}: {e}")
            return 0

    def analyze_single_transaction(self, transaction_id: str) -> TransactionSimplexData:
        """
        Analyse complète d'une transaction avec données Simplex

        Args:
            transaction_id: ID transaction à analyser

        Returns:
            Données complètes pour animation 3D
        """
        # Vérifier cache
        if transaction_id in self._transaction_cache:
            return self._transaction_cache[transaction_id]

        if not self.simulation:
            return self._create_empty_transaction_data(transaction_id)

        start_time = time.time()

        try:
            # Reset collecteur pour cette transaction
            if self.simplex_3d_collector:
                self.simplex_3d_collector.reset()

            # Valider transaction et capturer données Simplex
            validation_result = self.simulation.validate_transaction(
                transaction_id, SimulationMode.FEASIBILITY
            )

            solving_time_ms = (time.time() - start_time) * 1000

            # Extraire informations transaction
            tx_info = self._get_transaction_info(transaction_id)
            step_count = self.get_transaction_step_count(transaction_id)
            complexity = self._classify_complexity(step_count)

            # Construire données animation
            simplex_steps = []
            optimal_solution = None
            convergence_info = None

            if self.simplex_3d_collector and self.simplex_3d_collector.states_history:
                # Utiliser vraies données Simplex 3D
                animation_data = self.simplex_3d_collector.export_animation_data()
                simplex_steps = animation_data['simplex_states']

                # Solution optimale = dernier état
                if simplex_steps:
                    last_state = simplex_steps[-1]
                    optimal_solution = {
                        'coordinates_3d': last_state['coordinates'],
                        'variables_fi': last_state['variables_fi'],
                        'is_optimal': last_state['is_optimal'],
                        'objective_value': None  # À extraire du résultat
                    }

                convergence_info = {
                    'total_states': len(simplex_steps),
                    'algorithm_steps': animation_data['metadata']['algorithm_steps'],
                    'converged': validation_result.success
                }
            else:
                # Fallback: générer données approximatives
                simplex_steps = self._generate_fallback_steps(transaction_id, step_count)

            # Créer objet TransactionSimplexData
            transaction_data = TransactionSimplexData(
                transaction_id=transaction_id,
                step_count=step_count,
                estimated_duration_ms=int(step_count * 200),  # 200ms par étape
                complexity=complexity,
                simplex_steps=simplex_steps,
                optimal_solution=optimal_solution,
                convergence_info=convergence_info,
                source_account=tx_info.get('source', ''),
                target_account=tx_info.get('target', ''),
                amount=tx_info.get('amount', Decimal('0')),
                feasible=validation_result.success,
                actual_solving_time_ms=solving_time_ms,
                iterations_used=len(simplex_steps),
                pivot_count=self._count_pivots(simplex_steps)
            )

            # Mettre en cache
            self._transaction_cache[transaction_id] = transaction_data

            return transaction_data

        except Exception as e:
            logging.error(f"❌ Erreur analyse transaction {transaction_id}: {e}")
            return self._create_empty_transaction_data(transaction_id)

    def prepare_simulation_sequence(self) -> SimulationSequenceData:
        """
        Prépare séquence complète simulation avec toutes transactions

        Returns:
            Données pour animation simulation enchaînée
        """
        if self._simulation_sequence_cache:
            return self._simulation_sequence_cache

        if not self.simulation:
            return SimulationSequenceData(
                simulation_id="empty",
                total_transactions=0,
                total_steps=0,
                estimated_duration_ms=0
            )

        start_time = time.time()

        try:
            # Obtenir toutes transactions disponibles
            all_transactions = self._get_all_transaction_ids()

            transactions_data = []
            total_steps = 0

            # Analyser chaque transaction
            for tx_id in all_transactions:
                tx_data = self.analyze_single_transaction(tx_id)
                transactions_data.append(tx_data)
                total_steps += tx_data.step_count

            # Générer points transition
            transition_points = self._generate_transition_points(transactions_data)

            # Créer séquence
            sequence_data = SimulationSequenceData(
                simulation_id=f"sim_{int(time.time())}",
                total_transactions=len(transactions_data),
                total_steps=total_steps,
                estimated_duration_ms=int(total_steps * 200 + len(transition_points) * 500),
                transactions=transactions_data,
                transition_points=transition_points,
                sequence_metadata={
                    'generation_time_ms': (time.time() - start_time) * 1000,
                    'analysis_timestamp': time.time(),
                    'average_steps_per_transaction': total_steps / max(1, len(transactions_data)),
                    'complexity_distribution': self._analyze_complexity_distribution(transactions_data)
                }
            )

            # Mettre en cache
            self._simulation_sequence_cache = sequence_data

            return sequence_data

        except Exception as e:
            logging.error(f"❌ Erreur préparation séquence simulation: {e}")
            return SimulationSequenceData(
                simulation_id="error",
                total_transactions=0,
                total_steps=0,
                estimated_duration_ms=0
            )

    def _estimate_step_count_fallback(self, transaction_id: str) -> int:
        """Estimation fallback nombre étapes basée sur heuristiques"""
        try:
            tx_info = self._get_transaction_info(transaction_id)
            amount = tx_info.get('amount', Decimal('0'))

            # Heuristique simple: plus gros montant = plus d'étapes
            if amount > Decimal('1000'):
                return 12  # Complexité élevée
            elif amount > Decimal('500'):
                return 8   # Complexité moyenne
            else:
                return 5   # Complexité faible

        except Exception:
            return 6  # Default

    def _classify_complexity(self, step_count: int) -> TransactionComplexity:
        """Classification complexité basée sur nombre étapes"""
        if step_count < 5:
            return TransactionComplexity.LOW
        elif step_count < 15:
            return TransactionComplexity.MEDIUM
        elif step_count < 30:
            return TransactionComplexity.HIGH
        else:
            return TransactionComplexity.EXTREME

    def _get_transaction_info(self, transaction_id: str) -> Dict[str, Any]:
        """Extrait informations basiques transaction"""
        try:
            # Obtenir transaction depuis simulation
            if hasattr(self.simulation, 'enhanced_dag') and self.simulation.enhanced_dag:
                for tx in self.simulation.enhanced_dag.transactions:
                    if tx.transaction_id == transaction_id:
                        return {
                            'source': tx.source_account,
                            'target': tx.target_account,
                            'amount': tx.amount,
                            'status': getattr(tx, 'status', 'unknown')
                        }
            return {}
        except Exception:
            return {}

    def _get_all_transaction_ids(self) -> List[str]:
        """Obtient liste tous IDs transactions disponibles"""
        try:
            if hasattr(self.simulation, 'enhanced_dag') and self.simulation.enhanced_dag:
                return [tx.transaction_id for tx in self.simulation.enhanced_dag.transactions]
            return []
        except Exception:
            return []

    def _generate_fallback_steps(self, transaction_id: str, step_count: int) -> List[Dict[str, Any]]:
        """Génère étapes Simplex approximatives pour fallback"""
        steps = []

        for i in range(step_count):
            # Coordonnées 3D simulées
            x = 1.0 + i * 0.3
            y = 0.8 + i * 0.2
            z = 0.5 + i * 0.1

            step = {
                'step': i + 1,
                'coordinates': [x, y, z],
                'variables_fi': {f'f_{transaction_id}_{j}': float(1.0 + i * 0.1 + j * 0.05) for j in range(3)},
                'is_feasible': True,
                'is_optimal': i == step_count - 1,
                'basic_variables': [f'f_{transaction_id}_basic_{j}' for j in range(2)],
                'iterations': i + 1,
                'solving_time_ms': (i + 1) * 50,
                'constraint_contributions': {
                    'SOURCE': float(x),
                    'TARGET': float(y),
                    'SECONDARY': float(z)
                }
            }
            steps.append(step)

        return steps

    def _count_pivots(self, simplex_steps: List[Dict[str, Any]]) -> int:
        """Compte nombre de pivots dans les étapes Simplex"""
        pivot_count = 0

        for i in range(1, len(simplex_steps)):
            prev_basic = set(simplex_steps[i-1].get('basic_variables', []))
            curr_basic = set(simplex_steps[i].get('basic_variables', []))

            # Si changement variables basiques = pivot
            if prev_basic != curr_basic:
                pivot_count += 1

        return pivot_count

    def _generate_transition_points(self, transactions_data: List[TransactionSimplexData]) -> List[Dict[str, Any]]:
        """Génère points transition entre transactions"""
        transitions = []

        for i in range(len(transactions_data) - 1):
            current_tx = transactions_data[i]
            next_tx = transactions_data[i + 1]

            transition = {
                'from_transaction': current_tx.transaction_id,
                'to_transaction': next_tx.transaction_id,
                'transition_type': 'CASCADE_IMPACT',
                'affected_accounts': [current_tx.target_account, next_tx.source_account],
                'estimated_duration_ms': 500,
                'flux_changes': {
                    'redistributed_amount': float(current_tx.amount * Decimal('0.1')),
                    'impact_coefficient': 0.15
                }
            }
            transitions.append(transition)

        return transitions

    def _analyze_complexity_distribution(self, transactions_data: List[TransactionSimplexData]) -> Dict[str, int]:
        """Analyse distribution complexité transactions"""
        distribution = {complexity.value: 0 for complexity in TransactionComplexity}

        for tx_data in transactions_data:
            distribution[tx_data.complexity.value] += 1

        return distribution

    def _create_empty_transaction_data(self, transaction_id: str) -> TransactionSimplexData:
        """Crée TransactionSimplexData vide pour cas d'erreur"""
        return TransactionSimplexData(
            transaction_id=transaction_id,
            step_count=0,
            estimated_duration_ms=0,
            complexity=TransactionComplexity.LOW,
            feasible=False
        )

    def reset_cache(self):
        """Reset tous les caches"""
        self._transaction_cache.clear()
        self._simulation_sequence_cache = None

        if self.simplex_3d_collector:
            self.simplex_3d_collector.reset()


def create_transaction_simplex_analyzer(simulation: Optional[EconomicSimulation] = None) -> TransactionSimplexAnalyzer:
    """Factory function pour créer analyseur"""
    return TransactionSimplexAnalyzer(simulation)


if __name__ == '__main__':
    # Test basic functionality
    print("🎯 ICGS Transaction Simplex Analyzer")
    print("=" * 50)
    print("Analyseur spécialisé extraction données Simplex transactions")
    print("Features:")
    print("- Analyse transaction individuelle + comptage étapes")
    print("- Génération séquence simulation complète")
    print("- Support animation 3D avec données authentiques")
    print("- Classification complexité automatique")
    print("\n✅ Analyseur prêt pour intégration")