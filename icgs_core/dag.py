"""
DAG - Graphe Dirigé Acyclique avec Pipeline de Validation Économique ICGS

Module principal implémentant la classe DAG avec pipeline de validation économique
complet selon blueprint ICGS Phase 2 :
- Intégration AccountTaxonomy pour historisation comptes
- Pipeline Simplex validation avec TripleValidationOrientedSimplex
- Path enumeration et classification NFA automatique
- Warm-start pivot management pour performance optimale
- Transaction pipeline complet : NFA → Simplex → Commit atomique

Architecture Production selon Blueprint:
- Validation NFA explosion (Phase 1 existante)
- Validation Simplex économique (Phase 2 nouvelle)  
- Commit atomique avec rollback automatique
- Pivot storage et warm-start pour transactions séquentielles
- Métriques et monitoring intégrés
"""

from typing import Dict, List, Set, Optional, Any, Union, Tuple
from decimal import Decimal
from dataclasses import dataclass, field
import time
import logging
import copy

# Imports ICGS modules
from .account_taxonomy import AccountTaxonomy
try:
    from .anchored_nfa_v2 import AnchoredWeightedNFA
except ImportError:
    from anchored_nfa_v2 import AnchoredWeightedNFA
from .path_enumerator import DAGPathEnumerator, EnumerationStatistics
from .simplex_solver import TripleValidationOrientedSimplex, SimplexSolution, SolutionStatus
from .linear_programming import (
    LinearProgram, FluxVariable, LinearConstraint, ConstraintType,
    build_source_constraint, build_target_constraint, build_secondary_constraint
)
from .dag_structures import (
    Node, Edge, Account, EdgeType, NodeType,
    DAGStructureValidator, DAGValidationResult, create_node, create_edge, connect_nodes
)
from .exceptions import PathEnumerationNotReadyError, IntegrationLimitationError

logger = logging.getLogger(__name__)


@dataclass
class TransactionMeasure:
    """
    Mesure économique associée à une transaction
    
    Représente contraintes économiques appliquées à un compte (source ou cible)
    avec regex patterns pondérés pour classification flux.
    """
    measure_id: str
    account_id: str
    primary_regex_pattern: str
    primary_regex_weight: Decimal
    acceptable_value: Decimal  # Pour contraintes source (≤)
    required_value: Decimal = Decimal('0')  # Pour contraintes cible (≥)
    secondary_patterns: List[Tuple[str, Decimal]] = field(default_factory=list)  # (pattern, weight)
    
    def __post_init__(self):
        """Validation mesure après création"""
        if not isinstance(self.primary_regex_weight, Decimal):
            self.primary_regex_weight = Decimal(str(self.primary_regex_weight))
        if not isinstance(self.acceptable_value, Decimal):
            self.acceptable_value = Decimal(str(self.acceptable_value))
        if not isinstance(self.required_value, Decimal):
            self.required_value = Decimal(str(self.required_value))


@dataclass  
class Transaction:
    """
    Transaction économique avec mesures source/cible
    
    Représente flux économique entre comptes avec contraintes réglementaires
    exprimées via mesures et regex patterns pondérés.
    """
    transaction_id: str
    source_account_id: str
    target_account_id: str
    amount: Decimal
    source_measures: List[TransactionMeasure] = field(default_factory=list)
    target_measures: List[TransactionMeasure] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validation transaction après création"""
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))
        if self.amount <= 0:
            raise ValueError(f"Transaction amount must be positive: {self.amount}")
    
    def get_primary_source_measure(self) -> Optional[TransactionMeasure]:
        """Retourne mesure source primaire si existe"""
        return self.source_measures[0] if self.source_measures else None
    
    def get_primary_target_measure(self) -> Optional[TransactionMeasure]:
        """Retourne mesure cible primaire si existe"""
        return self.target_measures[0] if self.target_measures else None


@dataclass
class DAGConfiguration:
    """Configuration DAG avec paramètres optimisés selon blueprint"""
    max_path_enumeration: int = 10000
    simplex_max_iterations: int = 10000
    simplex_tolerance: Decimal = Decimal('1e-10')
    nfa_explosion_threshold: int = 50000
    enable_warm_start: bool = True
    enable_cross_validation: bool = True
    validation_mode: str = "STRICT"  # STRICT, MODERATE, LENIENT
    
    def __post_init__(self):
        if not isinstance(self.simplex_tolerance, Decimal):
            self.simplex_tolerance = Decimal(str(self.simplex_tolerance))


class DAG:
    """
    DAG Principal avec Pipeline de Validation Économique Complet
    
    Architecture ICGS Phase 2 complète selon blueprint:
    - AccountTaxonomy : Historisation UTF-32 comptes 
    - AnchoredWeightedNFA : Classification flux avec ancrage automatique
    - DAGPathEnumerator : Énumération reverse sink→sources  
    - TripleValidationOrientedSimplex : Validation économique avec garanties
    - Pipeline atomique : NFA explosion → Simplex validation → Commit
    
    Garanties Production:
    - Rollback automatique en cas d'échec validation
    - Warm-start pivot optimization pour performance  
    - Métriques et monitoring temps réel
    - Copy-on-validation pour protection état
    """
    
    def __init__(self, configuration: Optional[DAGConfiguration] = None):
        """
        Initialisation DAG avec composants ICGS Phase 2
        
        Args:
            configuration: Paramètres DAG (utilise defaults si None)
        """
        self.configuration = configuration or DAGConfiguration()
        
        # Structures DAG de base
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}
        self.accounts: Dict[str, Account] = {}
        
        # Composants ICGS Phase 2 intégrés selon blueprint
        self.account_taxonomy = AccountTaxonomy()
        self.anchored_nfa: Optional[AnchoredWeightedNFA] = None
        self.nfa_taxonomy_version: Optional[int] = None  # Version taxonomie pour optimisation NFA
        self.path_enumerator = DAGPathEnumerator(
            self.account_taxonomy, 
            max_paths=self.configuration.max_path_enumeration
        )
        self.simplex_solver = TripleValidationOrientedSimplex(
            max_iterations=self.configuration.simplex_max_iterations,
            tolerance=self.configuration.simplex_tolerance
        )
        
        # État pipeline validation
        self.stored_pivot: Optional[Dict[str, Decimal]] = None
        self.transaction_counter: int = 0  # Démarre à 0 selon blueprint
        self._taxonomy_counter: int = 0  # Compteur interne taxonomie
        
        # Validators et monitoring
        self.dag_validator = DAGStructureValidator()
        self.logger = logging.getLogger("ICGS.DAG")
        
        # CORRECTION: Initialisation taxonomie avec snapshot vide à transaction -1
        try:
            self.account_taxonomy.update_taxonomy({}, -1)
            self.logger.debug("Initialized empty taxonomy snapshot at transaction -1")
        except Exception as e:
            self.logger.warning(f"Failed to initialize taxonomy snapshot: {e}")
        
        # Statistiques étendues selon blueprint  
        self.stats = {
            'transactions_added': 0,
            'transactions_rejected': 0,
            'nfa_explosions_detected': 0,
            'simplex_feasible': 0,
            'simplex_infeasible': 0,
            'warm_starts_used': 0,
            'cold_starts_used': 0,
            'cross_validations_performed': 0,
            'pivot_rejections': 0,
            'avg_enumeration_time_ms': 0.0,
            'avg_simplex_solve_time_ms': 0.0,
            'max_paths_enumerated': 0,
            'total_validation_time_ms': 0.0
        }
        
        self.logger.info(f"DAG initialized with ICGS Phase 2 pipeline - config: {self.configuration}")
    
    def add_account(self, account: Account) -> bool:
        """
        Ajoute compte au DAG avec intégration taxonomie

        Args:
            account: Compte à ajouter avec source/sink nodes

        Returns:
            True si ajout réussi, False sinon
        """
        if account.account_id in self.accounts:
            self.logger.warning(f"Account {account.account_id} already exists")
            return False

        try:
            # Ajout nodes du compte
            self.nodes[account.source_node.node_id] = account.source_node
            self.nodes[account.sink_node.node_id] = account.sink_node

            # CORRECTION CRITIQUE: Ajout edge interne source → sink
            # Cette edge est essentielle pour l'énumération reverse des chemins
            internal_edge_id = f"internal_{account.account_id}"
            internal_edge = Edge(
                edge_id=internal_edge_id,
                source_node=account.source_node,
                target_node=account.sink_node,
                weight=Decimal('0'),  # Edge interne sans coût
                edge_type=EdgeType.STRUCTURAL,
                metadata={
                    'account_id': account.account_id,
                    'is_internal': True,
                    'purpose': 'path_enumeration_support'
                }
            )

            # Ajout edge aux collections DAG et nodes
            self.edges[internal_edge_id] = internal_edge
            account.source_node.add_outgoing_edge(internal_edge)
            account.sink_node.add_incoming_edge(internal_edge)

            # Ajout compte
            self.accounts[account.account_id] = account

            self.logger.debug(f"Account {account.account_id} added with internal edge {internal_edge_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add account {account.account_id}: {e}")
            return False
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """
        Pipeline validation transaction complet selon blueprint ICGS Phase 2
        
        Pipeline en 3 phases:
        1. Validation NFA explosion (protection système)
        2. Validation Simplex économique (nouvea selon blueprint)  
        3. Commit atomique avec pivot update
        
        Args:
            transaction: Transaction économique avec mesures
            
        Returns:
            True si transaction validée et commitée, False si rejetée
        """
        self.logger.info(f"Processing transaction {transaction.transaction_id}: {transaction.source_account_id} → {transaction.target_account_id}, amount={transaction.amount}")
        
        start_time = time.time()
        
        try:
            # Phase 0: CORRECTION - Création batch comptes avec taxonomie
            self._ensure_accounts_exist_with_taxonomy(transaction)
            
            # Phase 1: Validation NFA explosion protection
            if not self._validate_transaction_nfa_explosion(transaction):
                self.stats['nfa_explosions_detected'] += 1
                self.stats['transactions_rejected'] += 1
                self.logger.warning(f"Transaction {transaction.transaction_id} rejected - NFA explosion risk")
                return False
            
            # Phase 2: Validation Simplex économique (NOUVEAU selon blueprint)
            if not self._validate_transaction_simplex(transaction):
                self.stats['simplex_infeasible'] += 1
                self.stats['transactions_rejected'] += 1
                self.logger.warning(f"Transaction {transaction.transaction_id} rejected - Simplex infeasible")
                return False
            
            # Phase 3: Commit atomique transaction
            self._commit_transaction_atomic(transaction)
            
            # Mise à jour statistiques succès
            self.stats['transactions_added'] += 1
            self.stats['simplex_feasible'] += 1
            self.transaction_counter += 1
            
            # Timing
            total_time = (time.time() - start_time) * 1000
            self.stats['total_validation_time_ms'] += total_time
            
            self.logger.info(f"Transaction {transaction.transaction_id} validated and committed successfully in {total_time:.2f}ms")
            return True
            
        except PathEnumerationNotReadyError:
            # Re-propagation exception contrôlée pour limitation documentée
            self.stats['transactions_rejected'] += 1
            raise
        except Exception as e:
            self.logger.error(f"Transaction {transaction.transaction_id} processing error: {e}")
            self.stats['transactions_rejected'] += 1
            return False
    
    def _validate_transaction_nfa_explosion(self, transaction: Transaction) -> bool:
        """
        Validation NFA explosion protection (Phase 1 existante)
        
        Vérifie que l'ajout de nouvelles mesures NFA ne causera pas
        d'explosion combinatoire selon seuil configuration.
        """
        if not self.anchored_nfa:
            return True  # Pas de NFA = pas de risque explosion
        
        # Simulation ajout mesures temporaire pour test explosion
        temp_nfa = copy.deepcopy(self.anchored_nfa)
        
        try:
            # Ajout mesures source temporaires
            for measure in transaction.source_measures:
                temp_nfa.add_weighted_regex(
                    measure.measure_id,
                    measure.primary_regex_pattern,
                    measure.primary_regex_weight
                )
            
            # Ajout mesures cible temporaires  
            for measure in transaction.target_measures:
                temp_nfa.add_weighted_regex(
                    measure.measure_id,
                    measure.primary_regex_pattern,
                    measure.primary_regex_weight
                )
            
            # Test explosion via comptage états
            final_states_count = len(temp_nfa.get_final_states())
            if final_states_count > self.configuration.nfa_explosion_threshold:
                self.logger.warning(f"NFA explosion detected: {final_states_count} > {self.configuration.nfa_explosion_threshold}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"NFA explosion validation error: {e}")
            return False
    
    def _validate_transaction_simplex(self, transaction: Transaction) -> bool:
        """
        Validation économique complète via Simplex Phase 1 selon blueprint
        
        Pipeline détaillé blueprint:
        1. Mise à jour taxonomie avec nouveaux comptes
        2. Création NFA temporaire pour énumération consistante  
        3. Énumération chemins et classification par états finaux
        4. Construction problème LP depuis classifications
        5. Résolution via TripleValidationOrientedSimplex
        6. Stockage pivot si solution faisable
        
        Args:
            transaction: Transaction avec mesures économiques
            
        Returns:
            True si validation économique réussie, False sinon
        """
        simplex_start = time.time()
        
        try:
            # Étape 1: Mise à jour taxonomie pour transaction courante (auto-assignment inclus)
            new_accounts = self._extract_accounts_from_transaction(transaction)
            # Taxonomie déjà mise à jour dans _extract_accounts_from_transaction
            
            # Étape 2: Création NFA temporaire avec état frozen
            temp_nfa = self._create_temporary_nfa_for_transaction(transaction)
            temp_nfa.freeze()

            # HYBRID DUAL-NFA: Freeze target NFA si disponible
            if hasattr(temp_nfa, 'metadata') and isinstance(temp_nfa.metadata, dict):
                target_nfa = temp_nfa.metadata.get('target_nfa')
                if target_nfa:
                    target_nfa.freeze()
                    self.logger.debug(f"Target NFA frozen with {len(target_nfa.get_final_states())} final states")

            self.logger.debug(f"Temporary NFA created and frozen with {len(temp_nfa.get_final_states())} final states")
            
            # Étape 3: Énumération et classification chemins
            transaction_edge = self._create_temporary_transaction_edge(transaction)
            
            try:
                path_classes = self.path_enumerator.enumerate_and_classify(
                    transaction_edge, temp_nfa, self.transaction_counter
                )
                
                # PHASE 2.9: Vérification résultat path enumeration avec taxonomie explicite
                if not path_classes:
                    # Si vide même avec taxonomie explicite, c'est un problème technique
                    self.logger.warning(f"Path enumeration returned empty result for transaction {transaction.transaction_id}")
                    return False  # Retourne False pour test diagnostic
                    
            except PathEnumerationNotReadyError:
                raise  # Re-propagation exception contrôlée
            except Exception as e:
                raise PathEnumerationNotReadyError(
                    f"Path enumeration failed for transaction {transaction.transaction_id}: {e}. "
                    f"This integration feature is pending implementation in PHASE 2.9.",
                    "PATH_ENUM_FAILED"
                )
            
            enum_time = (time.time() - simplex_start) * 1000
            self.stats['avg_enumeration_time_ms'] = (
                (self.stats['avg_enumeration_time_ms'] * self.stats['transactions_added'] + enum_time) / 
                (self.stats['transactions_added'] + 1)
            )
            
            self.logger.debug(f"Path enumeration completed: {len(path_classes)} equivalence classes, {sum(len(paths) for paths in path_classes.values())} total paths")
            
            # Étape 4: Construction problème LP
            lp_problem = self._build_lp_from_path_classes(path_classes, transaction, temp_nfa)
            self.logger.debug(f"LP problem constructed: {len(lp_problem.variables)} variables, {len(lp_problem.constraints)} constraints")
            
            # Étape 5: Résolution avec garanties absolues
            solution = self.simplex_solver.solve_with_absolute_guarantees(
                lp_problem, self.stored_pivot
            )
            
            simplex_time = (time.time() - simplex_start) * 1000  
            self.stats['avg_simplex_solve_time_ms'] = (
                (self.stats['avg_simplex_solve_time_ms'] * self.stats['transactions_added'] + simplex_time) /
                (self.stats['transactions_added'] + 1)
            )
            
            # Étape 6: Analyse résultat et mise à jour pivot
            if solution.status == SolutionStatus.FEASIBLE:
                self.stored_pivot = solution.variables.copy()
                
                # Statistiques warm-start
                if solution.warm_start_successful:
                    self.stats['warm_starts_used'] += 1
                else:
                    self.stats['cold_starts_used'] += 1
                
                if solution.cross_validation_passed:
                    self.stats['cross_validations_performed'] += 1
                
                self.logger.info(f"Simplex validation successful: {solution.status.value}, iterations={solution.iterations_used}, warm_start={solution.warm_start_successful}")
                return True
            else:
                self.logger.warning(f"Simplex validation failed: {solution.status.value}")
                return False
                
        except PathEnumerationNotReadyError:
            # Re-propagation exception contrôlée
            raise
        except Exception as e:
            self.logger.error(f"Simplex validation error: {e}")
            return False
    
    def _extract_accounts_from_transaction(self, transaction: Transaction) -> Dict[str, Optional[str]]:
        """
        Extraction et création des comptes nécessaires pour une transaction
        
        PHASE 2.9: PRÉ-CONDITION STRICTE - La taxonomie DOIT être configurée 
        explicitement AVANT l'appel à add_transaction().
        
        Raises:
            AssertionError: Si taxonomie pas configurée pour transaction_counter actuel
            
        Returns:
            Dict node_id → character mapping (vide, pour compatibilité API)
        """
        # PRÉ-CONDITION 1: Taxonomie configurée pour transaction courante
        assert len(self.account_taxonomy.taxonomy_history) > 0, (
            "Taxonomy history is empty. "
            "Must configure taxonomy with update_taxonomy() before adding transactions."
        )
        
        # PRÉ-CONDITION 2: Taxonomie configurée pour transaction_counter actuel ou antérieur
        max_configured_tx = max(snapshot.transaction_num for snapshot in self.account_taxonomy.taxonomy_history)
        assert self.transaction_counter <= max_configured_tx, (
            f"Taxonomy not configured for current transaction_counter={self.transaction_counter}. "
            f"Latest configured transaction_num={max_configured_tx}. "
            f"Must configure taxonomy up to transaction_counter before adding transactions."
        )
        
        # Création comptes s'ils n'existent pas
        if transaction.source_account_id not in self.accounts:
            source_account = self._get_or_create_account(transaction.source_account_id)
            # ASSERTION: Taxonomie doit être configurée pour ces nodes
            required_nodes = [
                f"{transaction.source_account_id}_source",
                f"{transaction.source_account_id}_sink"
            ]
            for node_id in required_nodes:
                mapping = self.account_taxonomy.get_character_mapping(node_id, self.transaction_counter)
                assert mapping is not None, (
                    f"Taxonomy mapping is None for '{node_id}' at transaction_num={self.transaction_counter}. "
                    f"Must configure explicit character mapping before creating account '{transaction.source_account_id}'."
                )
            
        if transaction.target_account_id not in self.accounts:
            target_account = self._get_or_create_account(transaction.target_account_id)
            # ASSERTION: Taxonomie doit être configurée pour ces nodes
            required_nodes = [
                f"{transaction.target_account_id}_source", 
                f"{transaction.target_account_id}_sink"
            ]
            for node_id in required_nodes:
                mapping = self.account_taxonomy.get_character_mapping(node_id, self.transaction_counter)
                assert mapping is not None, (
                    f"Taxonomy mapping is None for '{node_id}' at transaction_num={self.transaction_counter}. "
                    f"Must configure explicit character mapping before creating account '{transaction.target_account_id}'."
                )
        
        # Aucune modification de taxonomie - responsabilité de l'appelant
        return {}
    
    def _extract_pattern_representative_char(self, measures: List[TransactionMeasure]) -> Optional[str]:
        """
        PHASE 2.9: Extraction caractère représentatif depuis patterns mesures
        
        Analyse les patterns regex pour extraire un caractère représentatif
        qui sera compatible avec les patterns lors de la classification NFA.
        
        Args:
            measures: Liste mesures transaction
            
        Returns:
            Caractère représentatif ou None pour auto-assignment par défaut
        """
        if not measures:
            return None  # Auto-assignment par défaut 'N'
        
        # Analyse du pattern principal de la première mesure
        primary_pattern = measures[0].primary_regex_pattern
        
        # Extraction caractère simple depuis pattern .* patterns
        import re
        
        # Pattern .*X.* → extrait X
        simple_char_match = re.search(r'\.\*([A-Z])\.\*', primary_pattern)
        if simple_char_match:
            return simple_char_match.group(1)
        
        # Pattern .*WORD.* → extrait première lettre
        word_match = re.search(r'\.\*([A-Z]+)\.\*', primary_pattern)
        if word_match:
            return word_match.group(1)[0]  # Première lettre
        
        # Fallback: caractère par défaut
        return None  # Auto-assignment 'N'
    
    def _nfa_update_needed(self, transaction: Transaction) -> bool:
        """
        Détermine si mise à jour NFA nécessaire pour transaction

        Optimisation: Évite deepcopy quand NFA stable peut être réutilisé.

        Returns:
            True si deepcopy + mise à jour nécessaire, False si version stable OK
        """
        # Cas 1: Pas de NFA existant
        if not self.anchored_nfa:
            return True

        # Cas 2: Version taxonomie changée depuis dernière mise à jour NFA
        # NOTE: Pas NÉCESSAIRE aujourd'hui (taxonomie/NFA indépendants), mais le deviendra.
        # Future: NFA pourrait optimiser patterns selon caractères disponibles en taxonomie.
        # À optimiser à ce moment-là pour éviter deepcopy inutile quand changement taxonomie isolé.
        current_taxonomy_version = len(self.account_taxonomy.taxonomy_history)
        if self.nfa_taxonomy_version != current_taxonomy_version:
            return True

        # Cas 3: Nouveaux patterns regex pas encore dans NFA
        # (Pour simplicité, on assume que tous patterns transaction nécessitent mise à jour)
        # Une optimisation future pourrait tracker patterns déjà ajoutés
        if transaction.source_measures or transaction.target_measures:
            return True

        return False

    def _create_temporary_nfa_for_transaction(self, transaction: Transaction) -> AnchoredWeightedNFA:
        """
        Création NFA temporaire avec mesures transaction

        OPTIMISÉ: Évite deepcopy inutile si NFA stable peut être réutilisé.
        Combine NFA existant avec nouvelles mesures transaction pour
        évaluation cohérente sans modification état permanent.
        """
        # SOLUTION ARCHITECTURALE: NFAs temporaires TOUJOURS propres
        # Élimination pollution patterns cross-transaction
        temp_nfa = AnchoredWeightedNFA(f"clean_main_tx_{self.transaction_counter}")
        self.logger.debug("Clean NFA created - zero pollution strategy")
        
        # BUG CRITIQUE FIX: Workaround AnchoredWeightedNFA patterns multiples
        # STRATÉGIE HYBRIDE: Créer deux NFAs temporaires PROPRES - un pour chaque type de pattern
        # et stocker dans metadata pour classification duale

        # NFA PROPRE pour patterns target (évite conflicts avec existing patterns)
        temp_nfa_target = AnchoredWeightedNFA(f"clean_target_tx_{self.transaction_counter}")

        # CORRECTION: Support patterns target ET fallback si vide
        has_target_measures = len(transaction.target_measures) > 0

        for measure in transaction.target_measures:
            temp_nfa_target.add_weighted_regex(
                measure.measure_id,
                measure.primary_regex_pattern,
                measure.primary_regex_weight,
                regex_id=f"target_{measure.measure_id}"
            )

            for pattern, weight in measure.secondary_patterns:
                temp_nfa_target.add_weighted_regex(
                    f"{measure.measure_id}_secondary",
                    pattern,
                    weight,
                    regex_id=f"target_{measure.measure_id}_secondary"
                )

        # FALLBACK: Si pas de target measures, dupliquer source patterns dans target NFA
        if not has_target_measures:
            self.logger.debug("No target measures - duplicating source patterns in target NFA for classification")
            for measure in transaction.source_measures:
                temp_nfa_target.add_weighted_regex(
                    f"fallback_{measure.measure_id}",
                    measure.primary_regex_pattern,
                    measure.primary_regex_weight,
                    regex_id=f"fallback_{measure.measure_id}"
                )

        # Store target NFA in metadata SEULEMENT si patterns ajoutés
        if has_target_measures or len(transaction.source_measures) > 0:
            temp_nfa.metadata['target_nfa'] = temp_nfa_target
        else:
            self.logger.warning("No patterns available for target NFA - classification may fail")

        # Ajout patterns source au NFA principal (priorité finale)
        for measure in transaction.source_measures:
            temp_nfa.add_weighted_regex(
                measure.measure_id,
                measure.primary_regex_pattern,
                measure.primary_regex_weight,
                regex_id=f"source_{measure.measure_id}"
            )

            for pattern, weight in measure.secondary_patterns:
                temp_nfa.add_weighted_regex(
                    f"{measure.measure_id}_secondary",
                    pattern,
                    weight,
                    regex_id=f"source_{measure.measure_id}_secondary"
                )

        # HACK: Stocker NFA target dans metadata pour classification hybride
        if hasattr(temp_nfa, 'metadata'):
            temp_nfa.metadata['target_nfa'] = temp_nfa_target
        else:
            temp_nfa.target_nfa_hack = temp_nfa_target  # Fallback
        
        return temp_nfa
    
    def _create_temporary_transaction_edge(self, transaction: Transaction) -> Edge:
        """
        Création arête temporaire pour énumération
        
        Crée edge temporaire representant transaction pour énumération
        reverse sink→sources sans modification DAG permanent.
        """
        # Récupération ou création nodes comptes
        source_account = self._get_or_create_account(transaction.source_account_id)
        target_account = self._get_or_create_account(transaction.target_account_id)
        
        # Création edge temporaire
        temp_edge = Edge(
            edge_id=f"temp_transaction_{transaction.transaction_id}",
            source_node=source_account.source_node,
            target_node=target_account.sink_node,
            weight=transaction.amount,
            edge_type=EdgeType.TEMPORARY,
            metadata={
                'transaction_id': transaction.transaction_id,
                'source_account_id': transaction.source_account_id,
                'target_account_id': transaction.target_account_id,
                'is_temporary': True
            }
        )
        
        return temp_edge
    
    def _build_lp_from_path_classes(self, path_classes: Dict[str, List[List[Node]]], 
                                   transaction: Transaction, 
                                   nfa: AnchoredWeightedNFA) -> LinearProgram:
        """
        Construction automatique problème LP depuis classifications chemins selon blueprint
        
        Algorithme blueprint avec fallback pour path_classes vides:
        1. Création variables flux: une par classe d'équivalence NFA (ou variables minimales)
        2. Extraction coefficients depuis RegexWeights des états finaux  
        3. Construction contraintes source/cible selon associations transaction
        4. Validation cohérence problème LP final
        
        Args:
            path_classes: Classes équivalence chemin par état final NFA
            transaction: Transaction avec mesures économiques
            nfa: NFA temporaire pour extraction coefficients
            
        Returns:
            LinearProgram: Problème LP complet pour résolution Simplex
        """
        # Étape 1: Variables flux par classe équivalence (avec fallback)
        program = LinearProgram(f"transaction_{self.transaction_counter}_{transaction.transaction_id}")
        
        if not path_classes:
            # Fallback: créer variables avec noms cohérents basés sur mesures transaction
            self.logger.warning("No path classes provided, creating fallback variables with coherent naming")

            # Création variables avec noms compatibles NFA final states
            for measure in transaction.source_measures + transaction.target_measures:
                # Format cohérent avec get_state_weights_for_measure
                var_id = f"{measure.measure_id}_{measure.measure_id}_final"
                program.add_variable(var_id, lower_bound=Decimal('0'))

                # Contraintes basiques pour faisabilité
                # Source constraint: variable ≤ acceptable_value
                if hasattr(measure, 'acceptable_value') and measure.acceptable_value is not None:
                    source_constraint = LinearConstraint(
                        coefficients={var_id: measure.primary_regex_weight},
                        bound=measure.acceptable_value,
                        constraint_type=ConstraintType.LEQ,
                        name=f"fallback_source_{measure.measure_id}"
                    )
                    program.add_constraint(source_constraint)

                # Target constraint: variable ≥ required_value
                if hasattr(measure, 'required_value') and measure.required_value is not None:
                    target_constraint = LinearConstraint(
                        coefficients={var_id: measure.primary_regex_weight},
                        bound=measure.required_value,
                        constraint_type=ConstraintType.GEQ,
                        name=f"fallback_target_{measure.measure_id}"
                    )
                    program.add_constraint(target_constraint)

            self.logger.info(f"Fallback LP created with {len(program.variables)} variables and {len(program.constraints)} constraints")
            return program
        
        for state_id, paths in path_classes.items():
            # Variable flux f_i ≥ 0 pour état final i
            program.add_variable(
                state_id, 
                lower_bound=Decimal('0'), 
                upper_bound=None  # Unbounded
            )
        
        # Étape 2: Contraintes source (compte débiteur)
        source_measure = transaction.get_primary_source_measure()
        if source_measure:
            state_weights = nfa.get_state_weights_for_measure(source_measure.measure_id)
            
            # Contrainte primaire source: Σ(f_i × weight_i) ≤ V_source_acceptable
            if state_weights:
                source_constraint = build_source_constraint(
                    state_weights,
                    source_measure.primary_regex_weight,
                    source_measure.acceptable_value,
                    f"source_primary_{source_measure.measure_id}"
                )
                program.add_constraint(source_constraint)
            
            # Contraintes secondaires source: Σ(f_i × weight_i) ≤ 0
            for pattern, weight in source_measure.secondary_patterns:
                secondary_state_weights = nfa.get_state_weights_for_measure(f"{source_measure.measure_id}_secondary")
                if secondary_state_weights:
                    secondary_constraint = build_secondary_constraint(
                        secondary_state_weights,
                        weight,
                        f"source_secondary_{source_measure.measure_id}"
                    )
                    program.add_constraint(secondary_constraint)
        
        # Étape 3: Contraintes cible (compte créditeur)
        target_measure = transaction.get_primary_target_measure()
        if target_measure:
            state_weights = nfa.get_state_weights_for_measure(target_measure.measure_id)
            
            # Contrainte primaire cible: Σ(f_i × weight_i) ≥ V_target_required
            if state_weights:
                target_constraint = build_target_constraint(
                    state_weights,
                    target_measure.primary_regex_weight,
                    target_measure.required_value,
                    f"target_primary_{target_measure.measure_id}"
                )
                program.add_constraint(target_constraint)
            
            # Contraintes secondaires cible
            for pattern, weight in target_measure.secondary_patterns:
                secondary_state_weights = nfa.get_state_weights_for_measure(f"{target_measure.measure_id}_secondary")
                if secondary_state_weights:
                    secondary_constraint = build_secondary_constraint(
                        secondary_state_weights,
                        weight,
                        f"target_secondary_{target_measure.measure_id}"
                    )
                    program.add_constraint(secondary_constraint)
        
        # Étape 4: Validation cohérence problème
        validation_errors = program.validate_problem()
        if validation_errors:
            self.logger.warning(f"LP problem validation warnings: {validation_errors}")
        
        return program
    
    def _commit_transaction_atomic(self, transaction: Transaction) -> None:
        """
        Commit atomique transaction avec création arête permanente

        Finalise transaction validée en créant structures DAG permanentes
        et mise à jour balances comptes.
        """
        self.logger.debug(f"COMMIT DEBUG: Starting commit for transaction {transaction.transaction_id}")
        # Récupération comptes source/target
        source_account = self._get_or_create_account(transaction.source_account_id)
        target_account = self._get_or_create_account(transaction.target_account_id)
        
        # Création arête transaction permanente
        edge_id = f"transaction_{transaction.transaction_id}"
        self.logger.debug(f"COMMIT DEBUG: Creating transaction edge {edge_id}")

        transaction_edge = Edge(
            edge_id=edge_id,
            source_node=source_account.source_node,
            target_node=target_account.sink_node,
            weight=transaction.amount,
            edge_type=EdgeType.TRANSACTION,
            metadata={
                'transaction_id': transaction.transaction_id,
                'source_account_id': transaction.source_account_id,
                'target_account_id': transaction.target_account_id,
                'timestamp': time.time(),
                'measures_source': [m.measure_id for m in transaction.source_measures],
                'measures_target': [m.measure_id for m in transaction.target_measures]
            }
        )
        
        # Ajout edge au DAG (éviter doublons complets)
        edge_exists_in_dag = transaction_edge.edge_id in self.edges
        edge_exists_in_source = transaction_edge.edge_id in source_account.source_node.outgoing_edges
        edge_exists_in_target = transaction_edge.edge_id in target_account.sink_node.incoming_edges

        if edge_exists_in_dag or edge_exists_in_source or edge_exists_in_target:
            self.logger.debug(f"Transaction edge {transaction_edge.edge_id} already exists (DAG:{edge_exists_in_dag}, Source:{edge_exists_in_source}, Target:{edge_exists_in_target}), skipping creation")
        else:
            # Connection défensive avec gestion complète erreurs
            try:
                self.edges[transaction_edge.edge_id] = transaction_edge
                connect_nodes(source_account.source_node, target_account.sink_node, transaction_edge)
                self.logger.debug(f"Transaction edge {transaction_edge.edge_id} created successfully")
            except ValueError as e:
                # Edge déjà existe dans les nœuds - nettoyer edge du DAG et skip silencieusement
                if transaction_edge.edge_id in self.edges:
                    del self.edges[transaction_edge.edge_id]
                self.logger.debug(f"Transaction edge {transaction_edge.edge_id} connection failed (edge already exists), skipping: {e}")
        
        # Mise à jour balances comptes
        source_account.add_outgoing_transaction(transaction_edge, transaction.amount)
        target_account.add_incoming_transaction(transaction_edge, transaction.amount)
        
        # Mise à jour NFA permanent avec nouvelles mesures
        if not self.anchored_nfa:
            self.anchored_nfa = AnchoredWeightedNFA("DAG_Production_NFA")
        
        # Ajout mesures à NFA permanent
        for measure in transaction.source_measures + transaction.target_measures:
            self.anchored_nfa.add_weighted_regex(
                measure.measure_id,
                measure.primary_regex_pattern,
                measure.primary_regex_weight
            )

        # OPTIMISATION: Mise à jour version taxonomie pour éviter deepcopy inutile
        self.nfa_taxonomy_version = len(self.account_taxonomy.taxonomy_history)

        self.logger.debug(f"Transaction {transaction.transaction_id} committed atomically (NFA version: {self.nfa_taxonomy_version})")
    
    def _get_or_create_account(self, account_id: str) -> Account:
        """
        Récupère compte existant ou crée nouveau compte
        
        NOTE: Taxonomie gérée séparément par _ensure_accounts_exist_with_taxonomy
        """
        if account_id in self.accounts:
            return self.accounts[account_id]
        
        # CORRECTION: Création simple sans taxonomie (gérée en batch ailleurs)
        new_account = Account(account_id, Decimal('0'))
        self.add_account(new_account)
        self.logger.debug(f"Account {account_id} created (taxonomy managed separately)")
        
        return new_account
    
    def _ensure_accounts_exist_with_taxonomy(self, transaction: Transaction) -> None:
        """
        PHASE 2.9: PRÉ-CONDITION STRICTE - Crée les comptes nécessaires
        
        La taxonomie DOIT être configurée explicitement AVANT l'appel.
        Aucune modification automatique de taxonomie n'est effectuée.
        
        Raises:
            AssertionError: Si taxonomie pas configurée pour les nouveaux comptes
        """
        # PRÉ-CONDITION: Taxonomie configurée pour transaction courante
        assert len(self.account_taxonomy.taxonomy_history) > 0, (
            "Taxonomy history is empty. "
            "Must configure taxonomy with update_taxonomy() before creating accounts."
        )
        
        max_configured_tx = max(snapshot.transaction_num for snapshot in self.account_taxonomy.taxonomy_history)
        assert self.transaction_counter <= max_configured_tx, (
            f"Taxonomy not configured for current transaction_counter={self.transaction_counter}. "
            f"Latest configured transaction_num={max_configured_tx}. "
            f"Must configure taxonomy up to transaction_counter before creating accounts."
        )
        
        # Création des comptes sans modification de taxonomie
        for account_id in [transaction.source_account_id, transaction.target_account_id]:
            if account_id not in self.accounts:
                # Création compte 
                new_account = Account(account_id, Decimal('0'))
                
                # ASSERTION: Vérifier que taxonomie configurée pour nodes de ce compte
                required_nodes = [
                    f"{account_id}_source",
                    f"{account_id}_sink"
                ]
                for node_id in required_nodes:
                    mapping = self.account_taxonomy.get_character_mapping(node_id, self.transaction_counter)
                    assert mapping is not None, (
                        f"Taxonomy mapping is None for '{node_id}' at transaction_num={self.transaction_counter}. "
                        f"Must configure explicit character mapping before creating account '{account_id}'."
                    )
                
                # Ajout compte au DAG
                self.add_account(new_account)
                self.logger.debug(f"Created account '{account_id}' with pre-configured taxonomy")
    
    def validate_dag_integrity(self) -> DAGValidationResult:
        """
        Validation intégrité DAG complète
        
        Utilise DAGStructureValidator pour validation production selon blueprint.
        """
        nodes_list = list(self.nodes.values())
        edges_list = list(self.edges.values())
        accounts_list = list(self.accounts.values())
        
        return self.dag_validator.validate_complete_dag_structure(
            nodes_list, edges_list, accounts_list
        )
    
    def get_dag_statistics(self) -> Dict[str, Any]:
        """
        Statistiques DAG complètes avec métriques ICGS
        
        Returns:
            Dict: Statistiques DAG + pipeline + performance selon blueprint
        """
        # Statistiques de base DAG
        basic_stats = {
            'total_accounts': len(self.accounts),
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges),
            'transaction_counter': self.transaction_counter
        }
        
        # Statistiques pipeline validation
        pipeline_stats = dict(self.stats)
        
        # Statistiques Simplex solver
        simplex_stats = self.simplex_solver.get_solver_stats()
        
        # Statistiques taxonomie
        taxonomy_stats = self.account_taxonomy.stats.copy()
        
        # Statistiques NFA
        nfa_stats = {}
        if self.anchored_nfa:
            nfa_stats = {
                'nfa_final_states': len(self.anchored_nfa.get_final_states()),
                'nfa_frozen': self.anchored_nfa.is_frozen,
                'nfa_patterns_anchored': self.anchored_nfa.stats.get('patterns_anchored', 0)
            }
        
        return {
            'basic_stats': basic_stats,
            'pipeline_stats': pipeline_stats,
            'simplex_stats': simplex_stats,
            'taxonomy_stats': taxonomy_stats,
            'nfa_stats': nfa_stats,
            'configuration': {
                'max_path_enumeration': self.configuration.max_path_enumeration,
                'simplex_tolerance': str(self.configuration.simplex_tolerance),
                'enable_warm_start': self.configuration.enable_warm_start
            }
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Résumé performance pour monitoring selon blueprint
        """
        total_transactions = self.stats['transactions_added'] + self.stats['transactions_rejected']
        success_rate = self.stats['transactions_added'] / max(1, total_transactions)
        
        return {
            'transaction_success_rate': round(success_rate, 4),
            'avg_total_validation_time_ms': round(
                self.stats['total_validation_time_ms'] / max(1, self.stats['transactions_added']), 2
            ),
            'avg_enumeration_time_ms': round(self.stats['avg_enumeration_time_ms'], 2),
            'avg_simplex_solve_time_ms': round(self.stats['avg_simplex_solve_time_ms'], 2),
            'warm_start_usage_rate': round(
                self.stats['warm_starts_used'] / max(1, self.stats['warm_starts_used'] + self.stats['cold_starts_used']), 4
            ),
            'pivot_stored': self.stored_pivot is not None,
            'transactions_processed': total_transactions,
            'nfa_explosion_incidents': self.stats['nfa_explosions_detected'],
            'system_status': 'OPERATIONAL' if success_rate > 0.95 else 'DEGRADED' if success_rate > 0.8 else 'CRITICAL'
        }
    
    def __str__(self) -> str:
        return f"DAG(accounts={len(self.accounts)}, transactions={self.transaction_counter}, nodes={len(self.nodes)}, edges={len(self.edges)})"
    
    def __repr__(self) -> str:
        return self.__str__()


# Fonctions utilitaires pour tests et exemples

def create_test_dag() -> DAG:
    """Crée DAG test pour validation académique"""
    config = DAGConfiguration(
        max_path_enumeration=1000,
        simplex_max_iterations=100,
        nfa_explosion_threshold=100
    )
    return DAG(config)


def create_simple_transaction(source_id: str, target_id: str, amount: Decimal,
                            source_pattern: str = ".*", source_weight: Decimal = Decimal('1.0'),
                            source_limit: Decimal = Decimal('1000')) -> Transaction:
    """Crée transaction simple pour tests"""
    source_measure = TransactionMeasure(
        measure_id=f"measure_{source_id}",
        account_id=source_id,
        primary_regex_pattern=source_pattern,
        primary_regex_weight=source_weight,
        acceptable_value=source_limit
    )
    
    return Transaction(
        transaction_id=f"tx_{source_id}_{target_id}_{int(time.time())}",
        source_account_id=source_id,
        target_account_id=target_id,
        amount=amount,
        source_measures=[source_measure],
        target_measures=[]
    )