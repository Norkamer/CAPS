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
    DAG, Account, Transaction, TransactionMeasure,
    TripleValidationOrientedSimplex, ValidationMode, SolutionStatus
)
from ..domains.base import get_sector_info, get_recommended_balance


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

        # Composants icgs_core
        self.dag = DAG()
        self.simplex_solver = TripleValidationOrientedSimplex(
            max_iterations=1000,
            tolerance=Decimal('1e-10')
        )

        # État simulation
        self.agents: Dict[str, SimulationAgent] = {}
        self.transactions: List[Transaction] = []
        self.transaction_counter = 1  # Commencer à 1 pour éviter collisions taxonomie
        self.taxonomy_configured = False  # Flag pour update batch unique

        # Note: Configuration taxonomie différée jusqu'à première transaction
        # pour éviter problèmes de numérotation

        self.logger.info(f"EconomicSimulation '{simulation_id}' initialisée")

    def _configure_taxonomy(self):
        """
        Configuration initiale vide de la taxonomie

        Pré-configure avec transaction_num=0 pour initialisation.
        La vraie configuration se fait en batch avant première transaction.
        """
        try:
            # Configuration minimale pour initialisation
            self.dag.account_taxonomy.update_taxonomy(
                accounts={},  # Vide initialement
                transaction_num=0  # Init à 0, batch sera à 1
            )
            self.logger.debug("Taxonomie initialisée (configuration batch à venir)")
        except Exception as e:
            self.logger.warning(f"Initialisation taxonomie échouée: {e}")

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
        Configuration batch unique de la taxonomie avec tous les agents

        Fait une seule mise à jour avec tous les comptes nécessaires
        pour éviter les problèmes de numérotation croissante.
        """
        try:
            # Générer mappings caractères basés sur secteurs économiques
            all_accounts = {}
            sector_char_map = {
                'AGRICULTURE': 'A',
                'INDUSTRY': 'I',
                'SERVICES': 'S',
                'FINANCE': 'F',
                'ENERGY': 'E'
            }

            # Compteur global pour source/sink pour éviter toute collision
            global_counter = ord('a')  # Commencer par minuscules

            # Compteurs par secteur pour gérer multiples agents même secteur
            sector_counters = {}
            # Compteur global pour caractères de fallback (évite collisions inter-secteurs)
            fallback_counter = ord('Q')

            for agent_id, agent in self.agents.items():
                # Caractère de base selon secteur
                base_char = sector_char_map.get(agent.sector, 'X')

                # Compte principal: caractère global unique minuscule
                all_accounts[agent_id] = chr(global_counter)
                global_counter += 1

                # Source: caractère global unique
                all_accounts[f"{agent_id}_source"] = chr(global_counter)
                global_counter += 1

                # Sink: utiliser caractères secteur + compteur global pour unicité
                if base_char not in sector_counters:
                    sector_counters[base_char] = 0

                # Pour éviter collisions: premier agent utilise caractère secteur,
                # agents suivants utilisent caractères globalement uniques
                if sector_counters[base_char] == 0:
                    # Premier agent: caractère secteur direct (A, I, S, F, E)
                    all_accounts[f"{agent_id}_sink"] = base_char
                else:
                    # Agents suivants: caractères globalement uniques
                    all_accounts[f"{agent_id}_sink"] = chr(fallback_counter)
                    fallback_counter += 1

                sector_counters[base_char] += 1

            # Configuration batch pour toutes transactions possibles (0-9)
            # Évite les erreurs de synchronisation compteur comme dans test_academic_16_FIXED.py
            for tx_num in range(10):
                self.dag.account_taxonomy.update_taxonomy(
                    accounts=all_accounts,
                    transaction_num=tx_num
                )

            self.logger.info(f"Taxonomie configurée en batch pour {len(all_accounts)} comptes")
            self.logger.debug(f"Mappings: {all_accounts}")
        except Exception as e:
            self.logger.error(f"Configuration batch taxonomie échouée: {e}")
            raise RuntimeError(f"Impossible de configurer taxonomie: {e}")

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

        # Créer mesures économiques selon secteurs
        source_measures = [
            TransactionMeasure(
                measure_id=f"{transaction_id}_source",
                account_id=source_agent_id,
                primary_regex_pattern=source_agent.get_sector_info().pattern,
                primary_regex_weight=source_agent.get_sector_info().weight,
                acceptable_value=amount,  # Montant transféré
                required_value=Decimal('0')
            )
        ]

        target_measures = [
            TransactionMeasure(
                measure_id=f"{transaction_id}_target",
                account_id=target_agent_id,
                primary_regex_pattern=target_agent.get_sector_info().pattern,
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
                self._configure_taxonomy_batch()
                self.taxonomy_configured = True

            if mode == SimulationMode.FEASIBILITY:
                # Mode FEASIBILITY standard
                success = self.dag.add_transaction(transaction)
                validation_time = (time.time() - start_time) * 1000

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

            # Optimisation avec Price Discovery
            solution = self.simplex_solver.solve_optimization_problem(
                problem, objective_coeffs
            )

            validation_time = (time.time() - start_time) * 1000

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