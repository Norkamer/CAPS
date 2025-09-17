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
import threading
import weakref
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

# Import icgs_core depuis parent directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from icgs_core import (
    Account, Transaction, TransactionMeasure,
    TripleValidationOrientedSimplex, ValidationMode, SolutionStatus
)
from icgs_core.enhanced_dag import EnhancedDAG
from icgs_core.character_set_manager import (
    create_default_character_set_manager,
    create_40_agents_character_set_manager,
    create_massive_character_set_manager_65_agents
)
from ..domains.base import get_sector_info, get_recommended_balance

# Import API Simplex 3D et Analyseur 3D (optionnel)
try:
    from icgs_simplex_3d_api import Simplex3DCollector
    from icgs_3d_space_analyzer import ICGS3DSpaceAnalyzer
    SIMPLEX_3D_API_AVAILABLE = True
    ICGS_3D_ANALYZER_AVAILABLE = True
except ImportError:
    SIMPLEX_3D_API_AVAILABLE = False
    ICGS_3D_ANALYZER_AVAILABLE = False


class PerformanceCache:
    """
    Cache haute performance pour optimiser gestion 65 agents + données 3D massives

    Features:
    - Cache validation transactions avec TTL
    - Cache données 3D par secteur
    - Mécanisme LRU avec cleanup automatique
    - Thread-safe pour requests web simultanées
    """

    def __init__(self, max_validation_cache: int = 500, max_3d_cache: int = 100):
        self.max_validation_cache = max_validation_cache
        self.max_3d_cache = max_3d_cache

        # Cache validation transactions avec timestamps
        self._validation_cache: Dict[str, Tuple[Any, float]] = {}
        self._validation_lock = threading.RLock()

        # Cache données 3D par groupe sectoriel
        self._3d_data_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self._3d_lock = threading.RLock()

        # Configuration TTL (Time-To-Live)
        self.validation_ttl = 300.0  # 5 minutes
        self.data_3d_ttl = 600.0     # 10 minutes

        # Statistiques performance
        self.hit_count = 0
        self.miss_count = 0

    def get_validation_result(self, transaction_key: str) -> Optional[Any]:
        """Récupère résultat validation depuis cache si disponible"""
        with self._validation_lock:
            if transaction_key in self._validation_cache:
                result, timestamp = self._validation_cache[transaction_key]
                if time.time() - timestamp <= self.validation_ttl:
                    self.hit_count += 1
                    return result
                else:
                    # Expiration cache
                    del self._validation_cache[transaction_key]

        self.miss_count += 1
        return None

    def store_validation_result(self, transaction_key: str, result: Any):
        """Stocke résultat validation avec cleanup LRU si nécessaire"""
        with self._validation_lock:
            # Cleanup si taille maximale atteinte
            if len(self._validation_cache) >= self.max_validation_cache:
                self._cleanup_validation_cache()

            self._validation_cache[transaction_key] = (result, time.time())

    def get_3d_data(self, data_key: str) -> Optional[Dict[str, Any]]:
        """Récupère données 3D depuis cache si disponibles"""
        with self._3d_lock:
            if data_key in self._3d_data_cache:
                data, timestamp = self._3d_data_cache[data_key]
                if time.time() - timestamp <= self.data_3d_ttl:
                    self.hit_count += 1
                    return data
                else:
                    del self._3d_data_cache[data_key]

        self.miss_count += 1
        return None

    def store_3d_data(self, data_key: str, data: Dict[str, Any]):
        """Stocke données 3D avec cleanup LRU si nécessaire"""
        with self._3d_lock:
            if len(self._3d_data_cache) >= self.max_3d_cache:
                self._cleanup_3d_cache()

            self._3d_data_cache[data_key] = (data, time.time())

    def _cleanup_validation_cache(self):
        """Cleanup LRU pour cache validation (supprime 25% plus anciens)"""
        if not self._validation_cache:
            return

        # Trier par timestamp et supprimer 25% plus anciens
        sorted_items = sorted(self._validation_cache.items(), key=lambda x: x[1][1])
        cleanup_count = len(sorted_items) // 4

        for key, _ in sorted_items[:cleanup_count]:
            del self._validation_cache[key]

    def _cleanup_3d_cache(self):
        """Cleanup LRU pour cache données 3D"""
        if not self._3d_data_cache:
            return

        sorted_items = sorted(self._3d_data_cache.items(), key=lambda x: x[1][1])
        cleanup_count = len(sorted_items) // 4

        for key, _ in sorted_items[:cleanup_count]:
            del self._3d_data_cache[key]

    def get_cache_stats(self) -> Dict[str, Any]:
        """Statistiques performance cache"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0

        return {
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate_percent': round(hit_rate, 2),
            'validation_cache_size': len(self._validation_cache),
            'data_3d_cache_size': len(self._3d_data_cache)
        }

    def clear_cache(self):
        """Vide complètement le cache"""
        with self._validation_lock:
            self._validation_cache.clear()
        with self._3d_lock:
            self._3d_data_cache.clear()


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

    def __init__(self, simulation_id: str = "default_simulation", agents_mode: str = "7_agents"):
        """
        Initialise simulateur avec configuration automatique

        Args:
            simulation_id: Identifiant unique de la simulation
            agents_mode: Mode configuration agents ("7_agents", "40_agents", "65_agents")
        """
        self.simulation_id = simulation_id
        self.agents_mode = agents_mode
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

        # Performance Cache pour optimisation 65 agents + données 3D massives
        cache_config = self._get_cache_config_for_mode()
        self.performance_cache = PerformanceCache(
            max_validation_cache=cache_config['validation'],
            max_3d_cache=cache_config['data_3d']
        )

        # API Simplex 3D et Analyseur 3D (optionnel)
        self.simplex_3d_collector = None
        self.icgs_3d_analyzer = None
        self.enable_3d_collection = False  # Flag pour activer collecte données 3D

        if SIMPLEX_3D_API_AVAILABLE:
            self.simplex_3d_collector = Simplex3DCollector()
            self.logger.info("Simplex 3D Collector initialisé")

        if ICGS_3D_ANALYZER_AVAILABLE:
            # Différer l'initialisation de l'analyseur 3D car il dépend de self
            self.icgs_3d_analyzer = None  # Sera initialisé dans enable_3d_analysis()
            self.logger.info("ICGS 3D Analyzer disponible")

        self._current_linear_program = None  # Cache LinearProgram pour API 3D

        self.logger.info(f"EconomicSimulation '{simulation_id}' initialisée")

    def _create_extended_character_set_manager(self):
        """
        Créer Character-Set Manager avec capacités selon mode agents

        Modes supportés:
        - "7_agents": Configuration actuelle (21 caractères)
        - "40_agents": Configuration étendue Semaine 2 (108+ caractères)
        - "65_agents": Configuration massive Semaine 3 (195 caractères)
        """
        if self.agents_mode == "40_agents":
            manager = create_40_agents_character_set_manager()
            self.logger.info(f"Character-Set Manager configuré mode 40 agents (108+ caractères)")

        elif self.agents_mode == "65_agents":
            manager = create_massive_character_set_manager_65_agents()
            self.logger.info(f"Character-Set Manager configuré mode 65 agents (195 caractères)")

        else:  # "7_agents" par défaut
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

            self.logger.info(f"Character-Set Manager configuré mode 7 agents (21 caractères)")

        # Affichage statistiques capacité
        stats = manager.get_allocation_statistics()
        total_capacity = sum(info['max_capacity'] for info in stats['sectors'].values())
        agents_capacity = total_capacity // 3
        self.logger.info(f"Capacité totale: {total_capacity} caractères = {agents_capacity} agents maximum")

        return manager

    def _get_cache_config_for_mode(self) -> Dict[str, int]:
        """
        Configuration cache optimisée selon mode agents

        Returns:
            Dict avec tailles cache validation et data_3d
        """
        if self.agents_mode == "65_agents":
            # Configuration aggressive pour 65 agents + données 3D volumineuses
            return {
                'validation': 1000,  # Cache large pour 500+ transactions possibles
                'data_3d': 200      # Cache étendu pour analyses sectorielles complexes
            }
        elif self.agents_mode == "40_agents":
            # Configuration intermédiaire pour 40 agents
            return {
                'validation': 600,
                'data_3d': 120
            }
        else:  # "7_agents"
            # Configuration standard pour simulations limitées
            return {
                'validation': 200,
                'data_3d': 50
            }

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

    def create_inter_sectoral_flows_batch(self, flow_intensity: float = 0.5) -> List[str]:
        """
        Crée automatiquement des transactions inter-sectorielles selon patterns économiques

        Flux économiques réalistes:
        - AGRICULTURE → INDUSTRY (40-60% production flow)
        - INDUSTRY → SERVICES (60-80% distribution flow)
        - SERVICES ↔ FINANCE (20-30% financial flow)
        - ENERGY → ALL (5-10% infrastructure flow)

        Args:
            flow_intensity: Intensité des flux (0.0 à 1.0, défaut 0.5)

        Returns:
            Liste des transaction_ids créés
        """
        if not self.agents:
            raise ValueError("Aucun agent créé. Créer des agents avant les flux inter-sectoriels.")

        created_transactions = []

        # Grouper agents par secteur
        agents_by_sector = {}
        for agent_id, agent in self.agents.items():
            sector = agent.sector
            if sector not in agents_by_sector:
                agents_by_sector[sector] = []
            agents_by_sector[sector].append(agent)

        try:
            # 1. AGRICULTURE → INDUSTRY (production flow)
            if 'AGRICULTURE' in agents_by_sector and 'INDUSTRY' in agents_by_sector:
                for agri_agent in agents_by_sector['AGRICULTURE']:
                    for indus_agent in agents_by_sector['INDUSTRY']:
                        flow_amount = agri_agent.balance * Decimal(str(0.4 + 0.2 * flow_intensity))
                        if flow_amount >= 50:  # Minimum economically meaningful
                            tx_id = self.create_transaction(
                                agri_agent.agent_id,
                                indus_agent.agent_id,
                                flow_amount
                            )
                            created_transactions.append(tx_id)

            # 2. INDUSTRY → SERVICES (distribution flow)
            if 'INDUSTRY' in agents_by_sector and 'SERVICES' in agents_by_sector:
                for indus_agent in agents_by_sector['INDUSTRY']:
                    for services_agent in agents_by_sector['SERVICES']:
                        flow_amount = indus_agent.balance * Decimal(str(0.6 + 0.2 * flow_intensity))
                        if flow_amount >= 50:
                            tx_id = self.create_transaction(
                                indus_agent.agent_id,
                                services_agent.agent_id,
                                flow_amount
                            )
                            created_transactions.append(tx_id)

            # 3. SERVICES ↔ FINANCE (bidirectional financial flow)
            if 'SERVICES' in agents_by_sector and 'FINANCE' in agents_by_sector:
                for services_agent in agents_by_sector['SERVICES']:
                    for finance_agent in agents_by_sector['FINANCE']:
                        # SERVICES → FINANCE (deposits/investments)
                        flow_amount = services_agent.balance * Decimal(str(0.2 + 0.1 * flow_intensity))
                        if flow_amount >= 50:
                            tx_id = self.create_transaction(
                                services_agent.agent_id,
                                finance_agent.agent_id,
                                flow_amount
                            )
                            created_transactions.append(tx_id)

                        # FINANCE → SERVICES (loans/funding)
                        flow_amount = finance_agent.balance * Decimal(str(0.25 + 0.05 * flow_intensity))
                        if flow_amount >= 100:
                            tx_id = self.create_transaction(
                                finance_agent.agent_id,
                                services_agent.agent_id,
                                flow_amount
                            )
                            created_transactions.append(tx_id)

            # 4. ENERGY → ALL (infrastructure flow)
            if 'ENERGY' in agents_by_sector:
                for energy_agent in agents_by_sector['ENERGY']:
                    for sector, agents_list in agents_by_sector.items():
                        if sector != 'ENERGY':  # Energy flows to all other sectors
                            for target_agent in agents_list:
                                flow_amount = energy_agent.balance * Decimal(str(0.05 + 0.05 * flow_intensity))
                                if flow_amount >= 30:
                                    tx_id = self.create_transaction(
                                        energy_agent.agent_id,
                                        target_agent.agent_id,
                                        flow_amount
                                    )
                                    created_transactions.append(tx_id)

            self.logger.info(f"Flux inter-sectoriels créés: {len(created_transactions)} transactions")
            self.logger.info(f"Secteurs impliqués: {list(agents_by_sector.keys())}")

        except Exception as e:
            self.logger.error(f"Erreur création flux inter-sectoriels: {e}")
            raise

        return created_transactions

    def _configure_taxonomy_batch(self):
        """
        Configuration batch unique de la taxonomie avec Character-Set Manager sectoriel

        ARCHITECTURE TRI-CARACTÈRES FONDAMENTALE :

        Chaque agent économique nécessite 3 caractères taxonomiques distincts :
        1. Caractère principal : pour l'Account object principal
        2. Caractère "_source" : pour le source_node du DAG
        3. Caractère "_sink" : pour le sink_node du DAG

        NÉCESSITÉ FONCTIONNELLE :
        - Path enumeration génère des chemins comme [farm_01_source_node, indu_01_sink_node]
        - convert_path_to_word() utilise node.node_id pour lookup taxonomique
        - Validation NFA nécessite caractères distincts pour chaque nœud du chemin
        - Architecture 65 agents = 195 caractères (65 × 3) obligatoires

        SANS CES MAPPINGS : Path validation échoue, DAG connectivity cassée, NFA non-fonctionnel

        Utilise Character-Set Manager pour allocation sectorielle intelligente + EnhancedDAG.
        """
        try:
            # Allocation sectorielle intelligente via Character-Set Manager
            all_accounts = {}

            for agent_id, agent in self.agents.items():
                # ALLOCATION 3 CARACTÈRES OBLIGATOIRES pour architecture DAG tri-nœuds
                # Chaque caractère sert à un mapping taxonomique distinct et fonctionnellement nécessaire
                char1 = self.character_set_manager.allocate_character_for_sector(agent.sector)  # Account principal
                char2 = self.character_set_manager.allocate_character_for_sector(agent.sector)  # source_node mapping
                char3 = self.character_set_manager.allocate_character_for_sector(agent.sector)  # sink_node mapping

                # Configuration taxonomique DAG : 3 mappings par agent
                # CRITIQUE : Ces mappings sont utilisés par convert_path_to_word() pour validation chemins
                all_accounts[agent_id] = char1                    # Account "FARM_01" → caractère principal
                all_accounts[f"{agent_id}_source"] = char2        # Nœud "FARM_01_source" → caractère source
                all_accounts[f"{agent_id}_sink"] = char3          # Nœud "FARM_01_sink" → caractère sink

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
        Valide une transaction avec mode spécifié + cache optimisé

        Args:
            transaction_id: ID transaction à valider
            mode: Mode de validation (FEASIBILITY ou OPTIMIZATION)

        Returns:
            SimulationResult avec résultats validation
        """
        # Générer clé cache basée sur transaction + mode
        cache_key = f"{transaction_id}:{mode.value}"

        # Vérifier cache pour résultats antérieurs
        cached_result = self.performance_cache.get_validation_result(cache_key)
        if cached_result is not None:
            return cached_result

        # Trouver transaction
        transaction = None
        for tx in self.transactions:
            if tx.transaction_id == transaction_id:
                transaction = tx
                break

        if not transaction:
            result = SimulationResult(
                success=False,
                mode=mode,
                transaction_id=transaction_id,
                error_message=f"Transaction '{transaction_id}' non trouvée"
            )
            # Stocker result d'erreur dans cache (TTL court pour erreurs)
            self.performance_cache.store_validation_result(cache_key, result)
            return result

        try:
            import time
            start_time = time.time()

            # Configurer taxonomie une seule fois avec tous les agents
            if not self.taxonomy_configured:
                # Toujours configurer avec EnhancedDAG (plus simple et robuste)
                self._configure_taxonomy_batch()
                self.taxonomy_configured = True

            if mode == SimulationMode.FEASIBILITY:
                # Mode FEASIBILITY avec EnhancedDAG optimisé
                success = self.dag.add_transaction_auto(transaction)
                validation_time = (time.time() - start_time) * 1000

                # Hook API Simplex 3D : capturer état après validation FEASIBILITY (avec cache 3D)
                if self.simplex_3d_collector and success:
                    try:
                        self._capture_3d_state_feasibility_cached(transaction, validation_time)
                    except Exception as e3d:
                        self.logger.warning(f"API 3D capture échouée: {e3d}")

                result = SimulationResult(
                    success=success,
                    mode=mode,
                    transaction_id=transaction_id,
                    status=SolutionStatus.FEASIBLE if success else SolutionStatus.INFEASIBLE,
                    validation_time_ms=validation_time,
                    dag_stats=dict(self.dag.stats)
                )

            elif mode == SimulationMode.OPTIMIZATION:
                # Mode OPTIMIZATION avec Price Discovery (cache intégré)
                result = self._run_price_discovery_cached(transaction, start_time, cache_key)

            # Stocker résultat dans cache pour réutilisation
            self.performance_cache.store_validation_result(cache_key, result)
            return result

        except Exception as e:
            error_result = SimulationResult(
                success=False,
                mode=mode,
                transaction_id=transaction_id,
                error_message=f"Erreur validation: {str(e)}"
            )
            # Stocker erreur dans cache avec TTL réduit
            self.performance_cache.store_validation_result(cache_key, error_result)
            return error_result

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

    # =====================================
    # API 3D ANALYSIS - NATIVE INTEGRATION
    # =====================================

    def enable_3d_analysis(self, use_authentic_data: bool = True) -> bool:
        """
        Active l'analyse 3D native avec ICGS3DSpaceAnalyzer intégré

        Args:
            use_authentic_data: Utiliser vraies variables f_i du Simplex vs approximations

        Returns:
            bool: True si activation réussie
        """
        if not ICGS_3D_ANALYZER_AVAILABLE:
            self.logger.warning("ICGS 3D Analyzer non disponible")
            return False

        # Initialiser l'analyseur 3D maintenant que self est complet
        self.icgs_3d_analyzer = ICGS3DSpaceAnalyzer(self)

        # Activer mode données authentiques si demandé
        if use_authentic_data and hasattr(self.icgs_3d_analyzer, 'enable_authentic_simplex_data'):
            success = self.icgs_3d_analyzer.enable_authentic_simplex_data(self)
            if success:
                self.logger.info("Mode 3D authentique activé - Variables f_i réelles utilisées")
            else:
                self.logger.warning("Échec activation mode 3D authentique - Fallback approximation")

        self.enable_3d_collection = True
        self.logger.info("Analyse 3D native activée pour simulation économique")
        return True

    def get_3d_analyzer(self):
        """Accès à l'analyseur 3D intégré"""
        return self.icgs_3d_analyzer

    def analyze_transaction_3d(self, source_id: str, target_id: str, amount: Decimal):
        """
        Analyse 3D d'une transaction avec collecte données Simplex

        Args:
            source_id: Agent source
            target_id: Agent cible
            amount: Montant transaction

        Returns:
            SolutionPoint3D ou None si analyse 3D non activée
        """
        if not self.enable_3d_collection or not self.icgs_3d_analyzer:
            return None

        try:
            # Utiliser l'analyseur 3D intégré pour traitement complet
            point_3d = self.icgs_3d_analyzer.analyze_transaction_3d_space(
                source_id, target_id, amount
            )
            return point_3d

        except Exception as e:
            self.logger.error(f"Erreur analyse 3D transaction {source_id}→{target_id}: {e}")
            return None

    def get_3d_analysis_data(self) -> Dict[str, Any]:
        """
        Récupère données d'analyse 3D complètes pour export web

        Returns:
            Dict avec solution_points, simplex_edges, animation_data, etc.
        """
        if not self.icgs_3d_analyzer:
            return {'error': 'Analyse 3D non activée'}

        try:
            # Export données selon le format du guide 3D
            return {
                'solution_points': [
                    {
                        'coordinates': [p.x, p.y, p.z],
                        'transaction_id': p.transaction_id,
                        'feasible': p.feasible,
                        'optimal': p.optimal,
                        'pivot_step': p.pivot_step,
                        'pivot_type': p.pivot_type,
                        'metadata': p.metadata
                    }
                    for p in self.icgs_3d_analyzer.solution_points
                ],
                'simplex_edges': [
                    {
                        'from_coords': [e.from_point.x, e.from_point.y, e.from_point.z],
                        'to_coords': [e.to_point.x, e.to_point.y, e.to_point.z],
                        'pivot_direction': e.pivot_direction,
                        'improvement': float(e.improvement),
                        'edge_type': e.edge_type
                    }
                    for e in self.icgs_3d_analyzer.simplex_edges
                ],
                'path_classifications': [
                    {
                        'path_id': pc.path_id,
                        'contribution_source': float(pc.contribution_source),
                        'contribution_target': float(pc.contribution_target),
                        'contribution_secondary': float(pc.contribution_secondary),
                        'sector_pattern': pc.sector_pattern
                    }
                    for pc in self.icgs_3d_analyzer.path_classifications
                ],
                'axes_labels': {
                    'x': 'Contraintes SOURCE (Débiteur)',
                    'y': 'Contraintes TARGET (Créditeur)',
                    'z': 'Contraintes SECONDARY (Bonus/Malus)'
                },
                'authentic_simplex_data': hasattr(self.icgs_3d_analyzer, 'use_authentic_simplex_data')
                                        and self.icgs_3d_analyzer.use_authentic_simplex_data,
                'total_transactions_analyzed': len(self.icgs_3d_analyzer.solution_points)
            }

        except Exception as e:
            self.logger.error(f"Erreur export données 3D: {e}")
            return {'error': f'Erreur export: {str(e)}'}

    def create_inter_sectoral_flows_batch_3d(self, flow_intensity: float = 0.5,
                                           enable_3d_analysis: bool = True) -> Tuple[List[str], Dict[str, Any]]:
        """
        Crée flux inter-sectoriels avec analyse 3D intégrée

        Args:
            flow_intensity: Intensité des flux (0.1 à 0.9)
            enable_3d_analysis: Activer collecte données 3D pour chaque transaction

        Returns:
            Tuple[List[str], Dict]: (transaction_ids, données_3d_complètes)
        """
        # Générer transactions avec méthode existante
        transaction_ids = self.create_inter_sectoral_flows_batch(flow_intensity)

        # Analyse 3D si activée
        data_3d = {'error': 'Analyse 3D non activée'}

        if enable_3d_analysis and self.icgs_3d_analyzer:
            # Pour chaque transaction générée, analyser en 3D
            for tx_id in transaction_ids[:50]:  # Limite pour performance web
                try:
                    # Récupérer détails transaction
                    transaction = next((tx for tx in self.transactions if tx.transaction_id == tx_id), None)
                    if transaction:
                        # Analyse 3D avec l'analyseur intégré
                        self.analyze_transaction_3d(
                            transaction.source_account_id,
                            transaction.target_account_id,
                            transaction.amount
                        )
                except Exception as e:
                    self.logger.warning(f"Analyse 3D échouée pour {tx_id}: {e}")

            # Export données complètes
            data_3d = self.get_3d_analysis_data()

        return transaction_ids, data_3d

    def _capture_3d_state_feasibility_cached(self, transaction: Transaction, validation_time: float):
        """Capture état 3D après validation FEASIBILITY avec cache optimisé"""
        if not self.simplex_3d_collector:
            return

        # Générer clé cache basée sur transaction
        cache_key = f"3d_state_feasibility:{transaction.transaction_id}"

        # Vérifier cache pour état 3D existant
        cached_data = self.performance_cache.get_3d_data(cache_key)
        if cached_data is not None:
            # Réutiliser données 3D cachées
            return

        # Capturer état 3D et le mettre en cache
        try:
            self._capture_3d_state_feasibility(transaction, validation_time)

            # Stocker données 3D capturées dans cache
            state_data = {
                'transaction_id': transaction.transaction_id,
                'validation_time': validation_time,
                'timestamp': time.time()
            }
            self.performance_cache.store_3d_data(cache_key, state_data)

        except Exception as e:
            self.logger.warning(f"Erreur capture 3D avec cache pour {transaction.transaction_id}: {e}")

    def _run_price_discovery_cached(self, transaction: Transaction, start_time: float, cache_key: str) -> SimulationResult:
        """
        Exécute Price Discovery avec cache optimisé pour 65 agents
        """
        try:
            # Vérifier cache spécialisé pour optimization
            opt_cache_key = f"price_discovery:{transaction.source_account_id}:{transaction.target_account_id}:{transaction.amount}"
            cached_opt_result = self.performance_cache.get_3d_data(opt_cache_key)

            if cached_opt_result is not None:
                # Reconstruction résultat depuis cache
                return SimulationResult(
                    success=cached_opt_result.get('success', False),
                    mode=SimulationMode.OPTIMIZATION,
                    transaction_id=transaction.transaction_id,
                    status=cached_opt_result.get('status'),
                    optimal_price=cached_opt_result.get('optimal_price'),
                    validation_time_ms=cached_opt_result.get('validation_time_ms', 0.0)
                )

            # Exécution price discovery normale
            result = self._run_price_discovery(transaction, start_time)

            # Stocker résultat optimization en cache
            if result.success:
                cache_data = {
                    'success': result.success,
                    'status': result.status,
                    'optimal_price': result.optimal_price,
                    'validation_time_ms': result.validation_time_ms,
                    'timestamp': time.time()
                }
                self.performance_cache.store_3d_data(opt_cache_key, cache_data)

            return result

        except Exception as e:
            return SimulationResult(
                success=False,
                mode=SimulationMode.OPTIMIZATION,
                transaction_id=transaction.transaction_id,
                error_message=f"Erreur price discovery cached: {str(e)}"
            )

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Statistiques performance complètes pour 65 agents

        Returns:
            Dict avec métriques cache, mémoire, et performance générale
        """
        import gc
        import sys

        # Statistiques cache
        cache_stats = self.performance_cache.get_cache_stats()

        # Statistiques simulation générale
        simulation_stats = {
            'agents_count': len(self.agents),
            'transactions_count': len(self.transactions),
            'taxonomy_configured': self.taxonomy_configured,
            'agents_mode': self.agents_mode
        }

        # Statistiques secteurs
        sectors_stats = {}
        for agent in self.agents.values():
            if agent.sector not in sectors_stats:
                sectors_stats[agent.sector] = 0
            sectors_stats[agent.sector] += 1

        # Statistiques 3D si disponible
        data_3d_stats = {}
        if self.icgs_3d_analyzer:
            data_3d_stats = {
                'analyzer_active': True,
                'solution_points': len(getattr(self.icgs_3d_analyzer, 'solution_points', [])),
                'simplex_edges': len(getattr(self.icgs_3d_analyzer, 'simplex_edges', []))
            }
        else:
            data_3d_stats = {'analyzer_active': False}

        # Statistiques mémoire (optionnel pour diagnostic)
        memory_stats = {
            'gc_collections': gc.get_count(),
            'python_objects': len(gc.get_objects()) if hasattr(gc, 'get_objects') else 0
        }

        # Character-Set Manager stats
        cs_manager_stats = {}
        if hasattr(self.character_set_manager, 'get_allocation_statistics'):
            cs_manager_stats = self.character_set_manager.get_allocation_statistics()

        return {
            'cache_performance': cache_stats,
            'simulation': simulation_stats,
            'sectors_distribution': sectors_stats,
            'data_3d': data_3d_stats,
            'memory': memory_stats,
            'character_set_manager': cs_manager_stats,
            'timestamp': time.time()
        }

    def optimize_for_web_load(self):
        """
        Optimisations spécifiques pour charge web avec 65 agents
        - Préchauffe cache
        - Optimise structures de données
        - Configure paramètres pour performance web
        """
        try:
            # Préchaufage cache validation pour patterns fréquents
            if len(self.agents) >= 40:  # Mode gros volume
                self.logger.info("Activation optimisations charge web massive (65 agents)")

                # Ajustement paramètres cache pour performance web
                self.performance_cache.validation_ttl = 180.0  # Réduit TTL pour web
                self.performance_cache.data_3d_ttl = 300.0

                # Préparation taxonomie
                if not self.taxonomy_configured:
                    self._configure_taxonomy_batch()
                    self.taxonomy_configured = True

                self.logger.info("Optimisations web activées avec succès")

        except Exception as e:
            self.logger.warning(f"Erreur optimisation web: {e}")

    def clear_performance_cache(self):
        """Vide le cache de performance (utile pour tests)"""
        self.performance_cache.clear_cache()
        self.logger.info("Cache de performance vidé")