"""
ICGS Bridge API - Composant Central

Bridge principal masquant la complexité d'icgs_core pour
les simulations économiques. Gère automatiquement:
- Configuration taxonomie
- Initialisation DAG
- Création agents économiques
- Validation transactions avec Price Discovery
"""

import sys
import os
import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Import icgs_core depuis parent directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from icgs_core import (
    Account, Transaction, TransactionMeasure,
    TripleValidationOrientedSimplex, ValidationMode, SolutionStatus
)
from icgs_core.enhanced_dag import EnhancedDAG
from icgs_core.character_set_manager import create_default_character_set_manager
from ..domains.base import get_sector_info, get_recommended_balance

# Import API Simplex 3D (optionnel)
try:
    from icgs_simplex_3d_api import Simplex3DCollector
    SIMPLEX_3D_API_AVAILABLE = True
except ImportError:
    SIMPLEX_3D_API_AVAILABLE = False


class SimulationMode(Enum):
    """Modes de simulation disponibles"""
    FEASIBILITY = "FEASIBILITY"      # Validation faisabilité seulement
    OPTIMIZATION = "OPTIMIZATION"    # Price Discovery complet


@dataclass
class SimulationAgent:
    """
    Agent économique simplifié pour simulations

    Encapsule un Account icgs_core avec métadonnées
    secteur et interface simplifiée.
    """
    agent_id: str
    account: Account
    sector: str
    balance: Decimal
    metadata: Dict[str, Any]

    def get_balance(self) -> Decimal:
        """Balance actuelle de l'agent"""
        return self.account.balance.current_balance

    def get_sector_info(self):
        """Informations secteur économique de l'agent"""
        return get_sector_info(self.sector)


@dataclass
class SimulationResult:
    """
    Résultat de simulation avec métriques
    """
    success: bool
    mode: SimulationMode
    transaction_id: str
    status: Optional[SolutionStatus] = None
    optimal_price: Optional[Decimal] = None
    validation_time_ms: float = 0.0
    error_message: Optional[str] = None
    dag_stats: Dict[str, Any] = None


class EconomicSimulation:
    """
    Simulateur Économique Principal - API Bridge ICGS

    Interface simplifiée pour créer et exécuter des simulations
    économiques avec garanties mathématiques ICGS.

    Features:
    - Auto-configuration icgs_core
    - Agents économiques par secteur
    - Validation + Price Discovery
    - Gestion erreurs transparente
    """

    def __init__(self, simulation_id: str = "default_simulation"):
        """
        Initialise simulateur avec configuration automatique

        Args:
            simulation_id: Identifiant unique de la simulation
        """
        self.simulation_id = simulation_id
        self.logger = logging.getLogger(f"icgs_simulation.{simulation_id}")

        # Composants icgs_core avec EnhancedDAG
        self.dag = EnhancedDAG()
        self.simplex_solver = TripleValidationOrientedSimplex(
            max_iterations=1000,
            tolerance=Decimal('1e-10')
        )

        # État simulation
        self.agents: Dict[str, SimulationAgent] = {}
        self.transactions: List[Transaction] = []
        self.taxonomy_configured = False  # Flag pour update batch unique

        # Character-Set Manager pour allocation sectorielle (capacité étendue)
        self.character_set_manager = self._create_extended_character_set_manager()

        # API Simplex 3D (optionnel)
        self.simplex_3d_collector = None
        if SIMPLEX_3D_API_AVAILABLE:
            self.simplex_3d_collector = Simplex3DCollector()

        self._current_linear_program = None  # Cache LinearProgram pour API 3D

        self.logger.info(f"EconomicSimulation '{simulation_id}' initialisée")

    def _create_extended_character_set_manager(self):
        """
        Créer Character-Set Manager avec capacités étendues pour 15+ agents

        Capacités par secteur étendues pour simulation massive.
        """
        from icgs_core.character_set_manager import NamedCharacterSetManager

        manager = NamedCharacterSetManager()

        # Configuration pour 7 agents actuels (21 caractères total)
        # Chaque agent nécessite 3 caractères (principal + source + sink)
        extended_sectors = {
            'AGRICULTURE': ['A', 'B', 'C'],                             # 1 agent × 3 = 3 chars
            'INDUSTRY': ['I', 'J', 'K', 'L', 'M', 'N'],                 # 2 agents × 3 = 6 chars
            'SERVICES': ['S', 'T', 'U', 'V', 'W', 'X'],                 # 2 agents × 3 = 6 chars
            'FINANCE': ['F', 'G', 'H'],                                 # 1 agent × 3 = 3 chars
            'ENERGY': ['E', 'Q', 'R'],                                  # 1 agent × 3 = 3 chars
        }

        for sector_name, characters in extended_sectors.items():
            manager.define_character_set(sector_name, characters)

        return manager

    def create_agent(self, agent_id: str, sector: str,
                    balance: Optional[Decimal] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> SimulationAgent:
        """
        Crée un agent économique dans le secteur spécifié

        Args:
            agent_id: Identifiant unique de l'agent
            sector: Secteur économique (AGRICULTURE, INDUSTRY, SERVICES, etc.)
            balance: Balance initiale (optionnel, utilise valeur recommandée)
            metadata: Métadonnées supplémentaires

        Returns:
            SimulationAgent configuré et ajouté au DAG
        """
        if agent_id in self.agents:
            raise ValueError(f"Agent '{agent_id}' existe déjà")

        # Utiliser balance recommandée si non spécifiée
        if balance is None:
            balance = get_recommended_balance(sector)

        # Récupérer informations secteur
        sector_info = get_sector_info(sector)

        # Créer Account icgs_core
        account_metadata = {
            'sector': sector,
            'simulation_id': self.simulation_id,
            **(metadata or {})
        }

        account = Account(
            account_id=agent_id,
            initial_balance=balance,
            metadata=account_metadata
        )

        # Ajouter au DAG
        success = self.dag.add_account(account)
        if not success:
            raise RuntimeError(f"Échec ajout agent '{agent_id}' au DAG")

        # Créer SimulationAgent
        agent = SimulationAgent(
            agent_id=agent_id,
            account=account,
            sector=sector,
            balance=balance,
            metadata=account_metadata
        )

        self.agents[agent_id] = agent

        # Ne pas configurer taxonomie pendant création agents
        # (sera fait en batch avant première transaction)

        self.logger.info(f"Agent créé: {agent_id} ({sector}, balance={balance})")
        return agent

    def _configure_taxonomy_batch(self):
        """
        Configuration batch unique de la taxonomie avec Character-Set Manager sectoriel

        Utilise Character-Set Manager pour allocation sectorielle intelligente + EnhancedDAG.
        """
        try:
            # Allocation sectorielle intelligente via Character-Set Manager
            all_accounts = {}

            for agent_id, agent in self.agents.items():
                # Allocation 3 caractères uniques par agent dans son secteur
                char1 = self.character_set_manager.allocate_character_for_sector(agent.sector)
                char2 = self.character_set_manager.allocate_character_for_sector(agent.sector)
                char3 = self.character_set_manager.allocate_character_for_sector(agent.sector)

                # Configuration standard DAG : compte principal + source + sink
                all_accounts[agent_id] = char1
                all_accounts[f"{agent_id}_source"] = char2
                all_accounts[f"{agent_id}_sink"] = char3

            # Configuration avec EnhancedDAG (préservé)
            self.dag.configure_accounts_simple(all_accounts)

            # Freeze Character-Set Manager après première configuration
            self.character_set_manager.freeze()

            self.logger.info(f"Taxonomie sectorielle configurée pour {len(all_accounts)} comptes")
            self.logger.info(f"Secteurs allocation: {self.character_set_manager.get_allocation_statistics()}")
            self.logger.debug(f"Mappings sectoriels: {all_accounts}")
        except Exception as e:
            self.logger.error(f"Configuration taxonomie sectorielle échouée: {e}")
            raise RuntimeError(f"Impossible de configurer taxonomie sectorielle: {e}")

    def create_transaction(self, source_agent_id: str, target_agent_id: str,
                         amount: Decimal,
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Crée une transaction entre deux agents

        Args:
            source_agent_id: Agent source (qui donne)
            target_agent_id: Agent cible (qui reçoit)
            amount: Montant du transfert
            metadata: Métadonnées transaction

        Returns:
            transaction_id: ID de la transaction créée
        """
        # Validation agents existent
        if source_agent_id not in self.agents:
            raise ValueError(f"Agent source '{source_agent_id}' non trouvé")
        if target_agent_id not in self.agents:
            raise ValueError(f"Agent cible '{target_agent_id}' non trouvé")

        source_agent = self.agents[source_agent_id]
        target_agent = self.agents[target_agent_id]

        # Générer ID transaction (utilise compteur séparé pour ne pas interférer avec taxonomie)
        transaction_num = len(self.transactions) + 1  # Simple compteur séquentiel
        transaction_id = f"TX_{self.simulation_id}_{transaction_num:03d}"

        # Patterns sectoriels économiques utilisant Character-Set Manager
        source_sector_pattern = self.character_set_manager.get_regex_pattern_for_sector(source_agent.sector)
        target_sector_pattern = self.character_set_manager.get_regex_pattern_for_sector(target_agent.sector)

        source_measures = [
            TransactionMeasure(
                measure_id=f"{transaction_id}_source",
                account_id=source_agent_id,
                primary_regex_pattern=source_sector_pattern,  # Pattern sectoriel (ex: ".*[ABC].*")
                primary_regex_weight=source_agent.get_sector_info().weight,
                acceptable_value=amount,  # Montant transféré
                required_value=Decimal('0')
            )
        ]

        target_measures = [
            TransactionMeasure(
                measure_id=f"{transaction_id}_target",
                account_id=target_agent_id,
                primary_regex_pattern=target_sector_pattern,  # Pattern sectoriel (ex: ".*[IJKL].*")
                primary_regex_weight=target_agent.get_sector_info().weight,
                acceptable_value=amount * 2,  # Capacité réception
                required_value=amount  # Montant requis
            )
        ]

        # Créer Transaction icgs_core
        transaction = Transaction(
            transaction_id=transaction_id,
            source_account_id=source_agent_id,
            target_account_id=target_agent_id,
            amount=amount,
            source_measures=source_measures,
            target_measures=target_measures,
            metadata={
                'simulation_id': self.simulation_id,
                'source_sector': source_agent.sector,
                'target_sector': target_agent.sector,
                **(metadata or {})
            }
        )

        self.transactions.append(transaction)

        self.logger.info(f"Transaction créée: {transaction_id} ({source_agent_id} → {target_agent_id}, {amount})")
        return transaction_id

    def validate_transaction(self, transaction_id: str,
                           mode: SimulationMode = SimulationMode.FEASIBILITY) -> SimulationResult:
        """
        Valide une transaction avec mode spécifié

        Args:
            transaction_id: ID transaction à valider
            mode: Mode de validation (FEASIBILITY ou OPTIMIZATION)

        Returns:
            SimulationResult avec résultats validation
        """
        # Trouver transaction
        transaction = None
        for tx in self.transactions:
            if tx.transaction_id == transaction_id:
                transaction = tx
                break

        if not transaction:
            return SimulationResult(
                success=False,
                mode=mode,
                transaction_id=transaction_id,
                error_message=f"Transaction '{transaction_id}' non trouvée"
            )

        try:
            import time
            start_time = time.time()

            # Configurer taxonomie une seule fois avec tous les agents
            if not self.taxonomy_configured:
                # Toujours configurer avec EnhancedDAG (plus simple et robuste)
                self._configure_taxonomy_batch()
                self.taxonomy_configured = True

            if mode == SimulationMode.FEASIBILITY:
                # Mode FEASIBILITY avec EnhancedDAG
                success = self.dag.add_transaction_auto(transaction)
                validation_time = (time.time() - start_time) * 1000

                # Hook API Simplex 3D : capturer état après validation FEASIBILITY
                if self.simplex_3d_collector and success:
                    try:
                        self._capture_3d_state_feasibility(transaction, validation_time)
                    except Exception as e3d:
                        self.logger.warning(f"API 3D capture échouée: {e3d}")

                return SimulationResult(
                    success=success,
                    mode=mode,
                    transaction_id=transaction_id,
                    status=SolutionStatus.FEASIBLE if success else SolutionStatus.INFEASIBLE,
                    validation_time_ms=validation_time,
                    dag_stats=dict(self.dag.stats)
                )

            elif mode == SimulationMode.OPTIMIZATION:
                # Mode OPTIMIZATION avec Price Discovery
                return self._run_price_discovery(transaction, start_time)

        except Exception as e:
            return SimulationResult(
                success=False,
                mode=mode,
                transaction_id=transaction_id,
                error_message=f"Erreur validation: {str(e)}"
            )

    def _run_price_discovery(self, transaction: Transaction, start_time: float) -> SimulationResult:
        """
        Exécute Price Discovery pour une transaction

        Utilise le nouveau solve_optimization_problem d'icgs_core
        pour découvrir prix optimal.
        """
        try:
            # Construction problème LP depuis transaction
            from icgs_core import LinearProgram, LinearConstraint, ConstraintType

            # Créer problème LP simple pour cette transaction
            problem = LinearProgram(f"price_discovery_{transaction.transaction_id}")

            # Variables: flux source et target
            problem.add_variable("source_flux", lower_bound=Decimal('0'))
            problem.add_variable("target_flux", lower_bound=Decimal('0'))

            # Contrainte: conservation flux
            constraint = LinearConstraint(
                coefficients={
                    "source_flux": Decimal('1'),
                    "target_flux": Decimal('-1')
                },
                bound=Decimal('0'),
                constraint_type=ConstraintType.EQ,
                name="flux_conservation"
            )
            problem.add_constraint(constraint)

            # Contrainte capacité
            capacity_constraint = LinearConstraint(
                coefficients={"source_flux": Decimal('1')},
                bound=transaction.amount,
                constraint_type=ConstraintType.LEQ,
                name="source_capacity"
            )
            problem.add_constraint(capacity_constraint)

            # Coefficients objectif (prix unitaires par secteur)
            source_agent = self.agents[transaction.source_account_id]
            target_agent = self.agents[transaction.target_account_id]

            objective_coeffs = {
                "source_flux": source_agent.get_sector_info().weight,
                "target_flux": target_agent.get_sector_info().weight
            }

            # Cache LinearProgram pour API 3D
            self._current_linear_program = problem

            # Optimisation avec Price Discovery
            solution = self.simplex_solver.solve_optimization_problem(
                problem, objective_coeffs
            )

            validation_time = (time.time() - start_time) * 1000

            # Hook API Simplex 3D : capturer état après validation OPTIMIZATION
            if self.simplex_3d_collector and solution.status == SolutionStatus.OPTIMAL:
                try:
                    self._capture_3d_state_optimization(problem, solution, ValidationMode.OPTIMIZATION)
                except Exception as e3d:
                    self.logger.warning(f"API 3D capture OPTIMIZATION échouée: {e3d}")

            return SimulationResult(
                success=solution.status == SolutionStatus.OPTIMAL,
                mode=SimulationMode.OPTIMIZATION,
                transaction_id=transaction.transaction_id,
                status=solution.status,
                optimal_price=solution.optimal_price,
                validation_time_ms=validation_time,
                dag_stats={'price_discovery': True, 'iterations': solution.phase2_iterations}
            )

        except Exception as e:
            self.logger.error(f"Price Discovery échoué: {e}")
            return SimulationResult(
                success=False,
                mode=SimulationMode.OPTIMIZATION,
                transaction_id=transaction.transaction_id,
                error_message=f"Price Discovery erreur: {str(e)}"
            )

    def get_agent(self, agent_id: str) -> Optional[SimulationAgent]:
        """Récupère un agent par son ID"""
        return self.agents.get(agent_id)

    def list_agents(self) -> List[str]:
        """Liste tous les agents de la simulation"""
        return list(self.agents.keys())

    def get_simulation_stats(self) -> Dict[str, Any]:
        """Statistiques de la simulation"""
        return {
            'simulation_id': self.simulation_id,
            'agents_count': len(self.agents),
            'transactions_count': len(self.transactions),
            'dag_stats': dict(self.dag.stats),
            'sectors_represented': list(set(agent.sector for agent in self.agents.values()))
        }

    def _capture_3d_state_feasibility(self, transaction: Transaction, validation_time: float):
        """Capture état 3D après validation FEASIBILITY"""
        if not self.simplex_3d_collector:
            return

        # Créer SimplexSolution simulée pour FEASIBILITY
        from icgs_core.simplex_solver import SimplexSolution, SolutionStatus
        from icgs_core.linear_programming import LinearProgram

        # Solution simulée basée sur DAG stats
        solution = SimplexSolution(status=SolutionStatus.FEASIBLE)
        solution.variables = {"feasibility_check": Decimal('1.0')}  # Simulé
        solution.solving_time = validation_time / 1000.0
        solution.iterations_used = 1

        # LinearProgram minimal pour compatibilité
        problem = LinearProgram(f"feasibility_{transaction.transaction_id}")
        problem.variables = {"feasibility_check": type('FluxVar', (), {
            'variable_id': 'feasibility_check',
            'is_basic': True
        })()}

        # Capturer état
        self.simplex_3d_collector.capture_simplex_state(
            problem, solution, ValidationMode.FEASIBILITY
        )

    def _capture_3d_state_optimization(self, problem, solution, mode):
        """Capture état 3D après validation OPTIMIZATION avec vraies données Simplex"""
        if not self.simplex_3d_collector:
            return

        # Capturer état avec vraies variables f_i du Simplex
        state = self.simplex_3d_collector.capture_simplex_state(problem, solution, mode)

        # Si il y a un état précédent, créer transition
        if len(self.simplex_3d_collector.states_history) > 1:
            from icgs_simplex_3d_api import SimplexTransitionType
            previous_state = self.simplex_3d_collector.states_history[-2]
            self.simplex_3d_collector.capture_transition(
                previous_state, state, SimplexTransitionType.OPTIMIZATION_STEP
            )

    def get_3d_collector(self):
        """Accès externe au collecteur 3D pour analyseurs"""
        return self.simplex_3d_collector

    def get_current_linear_program(self):
        """Accès au LinearProgram courant pour API 3D"""
        return self._current_linear_program