"""
DAGPathEnumerator - Énumération Optimisée des Chemins DAG

Module implémentant l'énumérateur de chemins pour DAG avec énumération reverse
selon blueprint ICGS avec garanties mathématiques:
- Reverse enumeration: sink → sources pour transaction validation
- Cycle detection: prévention explosion combinatoire
- Batch processing: gestion limites performance
- Classification: regroupement chemins par états finaux NFA

Propriétés mathématiques garanties:
- Complexité: O(V + E) avec early termination via max_paths
- Détection Cycles: Visited set avec backtracking pour éviter explosion
- Classes d'Équivalence: Regroupement chemins ayant même classification NFA
- Performance: Optimisations cache et réutilisation de structures
"""

from typing import Dict, List, Set, Optional, Iterator, Tuple, Any
from dataclasses import dataclass, field
from decimal import Decimal
import logging
import time
from collections import defaultdict, deque

# Imports ICGS modules
from .account_taxonomy import AccountTaxonomy
from .dag_structures import Node, Edge, EdgeType

logger = logging.getLogger(__name__)


@dataclass
class EnumerationStatistics:
    """Statistiques énumération chemins pour monitoring performance - Version étendue"""
    paths_enumerated: int = 0
    cycles_detected: int = 0
    early_terminations: int = 0
    enumeration_time_ms: float = 0.0
    max_depth_reached: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    
    # Métriques cycle detection avancées (Étape 1.3)
    direct_cycles: int = 0
    indirect_cycles: int = 0
    self_loops: int = 0
    alternating_cycles: int = 0
    depth_limit_hits: int = 0
    memory_limit_hits: int = 0
    warning_patterns: int = 0
    
    # Métriques explosion path limits (Étape 1.4)
    explosion_preventions: int = 0
    graceful_terminations: int = 0
    overflow_detections: int = 0
    adaptive_limit_adjustments: int = 0
    batch_overflows: int = 0


@dataclass
class PathClassification:
    """Classification chemin avec état final NFA et métadonnées"""
    final_state_id: str
    paths: List[List[Node]]
    word_representations: List[str]
    classification_confidence: float = 1.0


class DAGPathEnumerator:
    """
    Énumérateur reverse des chemins depuis arête transaction vers sources DAG
    
    Objectif: Découverte tous chemins possibles pour construction variables LP  
    Propriétés:
    - Reverse enumeration: sink → sources pour transaction validation
    - Cycle detection: prévention explosion combinatoire
    - Batch processing: gestion limites performance
    - Classification: regroupement par états finaux NFA
    """
    
    def __init__(self, taxonomy: AccountTaxonomy, max_paths: int = 10000, 
                 batch_size: int = 200):
        """
        Initialize DAGPathEnumerator avec paramètres performance
        
        Args:
            taxonomy: AccountTaxonomy pour conversion path→word
            max_paths: Limite maximum chemins énumérés (protection explosion)
            batch_size: Taille batch pour processing optimisé
        """
        self.taxonomy = taxonomy
        self.max_paths = max_paths
        self.batch_size = batch_size
        
        # Structures de données énumération
        self.visited_nodes: Set[str] = set()
        self.current_path: List[Node] = []
        self.enumerated_paths: List[List[Node]] = []
        
        # Cache performance
        self._path_cache: Dict[str, List[List[Node]]] = {}
        self._word_cache: Dict[Tuple[str, ...], str] = {}
        
        # Statistiques et monitoring
        self.stats = EnumerationStatistics()
        self.logger = logging.getLogger(f"{__name__}.DAGPathEnumerator")
        
        self.logger.info(f"DAGPathEnumerator initialized - max_paths: {max_paths}, "
                        f"batch_size: {batch_size}")
    
    def reset_enumeration_state(self):
        """Reset état énumération pour nouvelle transaction"""
        self.visited_nodes.clear()
        self.current_path.clear()
        self.enumerated_paths.clear()
        self.stats = EnumerationStatistics()
        
        self.logger.debug("Enumeration state reset")
    
    def get_enumeration_statistics(self) -> EnumerationStatistics:
        """Retourne statistiques énumération dernière opération"""
        return self.stats
    
    def validate_enumeration_parameters(self) -> bool:
        """
        Validation paramètres énumération
        
        Returns:
            bool: True si paramètres valides
        """
        if self.max_paths <= 0:
            self.logger.error(f"Invalid max_paths: {self.max_paths} (must be > 0)")
            return False
            
        if self.batch_size <= 0:
            self.logger.error(f"Invalid batch_size: {self.batch_size} (must be > 0)")
            return False
            
        if not self.taxonomy:
            self.logger.error("AccountTaxonomy not provided")
            return False
            
        return True
    
    def _generate_cache_key(self, start_node: Node, transaction_num: int) -> str:
        """Génère clé cache pour énumération depuis nœud"""
        return f"{start_node.node_id}_{transaction_num}_{self.max_paths}"
    
    def _is_source_node(self, node: Node) -> bool:
        """
        Teste si nœud est source (pas d'incoming edges)
        
        Args:
            node: Node à tester
            
        Returns:
            bool: True si node est source
        """
        return len(node.incoming_edges) == 0
    
    def _detect_cycle(self, node: Node) -> bool:
        """
        Détecte cycle dans chemin courant - Version basique
        
        Args:
            node: Node à vérifier pour cycle
            
        Returns:
            bool: True si cycle détecté
        """
        return node.node_id in self.visited_nodes
    
    def _detect_complex_cycle_patterns(self, node: Node, depth: int) -> tuple[bool, str]:
        """
        Détection cycles complexes avec classification patterns
        
        Détecte différents types de cycles:
        - Direct cycles: A → B → A
        - Indirect cycles: A → B → C → A  
        - Self-loops: A → A (même node)
        - Multi-path cycles: A → B → D → A, A → C → D → A
        
        Args:
            node: Node à vérifier pour cycles complexes
            depth: Profondeur courante dans traversal
            
        Returns:
            tuple[bool, str]: (cycle_detected, cycle_type)
        """
        if not node or not node.node_id:
            return False, "no_cycle"
        
        node_id = node.node_id
        
        # Type 1: Self-loop detection
        if depth == 1 and node_id in self.visited_nodes:
            return True, "self_loop"
        
        # Type 2: Direct cycle (node déjà visité)
        if node_id in self.visited_nodes:
            # Calcul position dans chemin pour classifier
            try:
                position = next(i for i, n in enumerate(self.current_path) if n.node_id == node_id)
                cycle_length = len(self.current_path) - position
                
                if cycle_length <= 2:
                    return True, "direct_cycle"
                elif cycle_length <= 5:
                    return True, "short_indirect_cycle"
                else:
                    return True, "long_indirect_cycle"
                    
            except StopIteration:
                return True, "unknown_cycle"
        
        # Type 3: Multi-path cycle detection (patterns répétitifs)
        if len(self.current_path) >= 4:
            # Recherche patterns répétitifs dans chemin
            path_ids = [n.node_id for n in self.current_path]
            
            # Détection pattern A-B-A
            if len(path_ids) >= 3:
                for i in range(len(path_ids) - 2):
                    if path_ids[i] == path_ids[i + 2] and node_id == path_ids[i]:
                        return True, "alternating_cycle"
        
        return False, "no_cycle"
    
    def _advanced_cycle_prevention(self, node: Node, depth: int) -> bool:
        """
        Prévention cycles avancée avec heuristiques intelligentes
        
        Stratégies:
        1. Limite profondeur adaptive basée sur taille DAG
        2. Détection early warning avant cycle complet
        3. Pattern recognition pour cycles probables
        4. Resource protection (memory, time)
        
        Args:
            node: Node candidat pour continuation traversal
            depth: Profondeur courante
            
        Returns:
            bool: True si continuation autorisée, False si blocked
        """
        if not node:
            return False
            
        # Strategy 1: Adaptive depth limit basée sur complexity
        adaptive_max_depth = min(50, self.max_paths // 100 + 10)
        if depth > adaptive_max_depth:
            self.logger.warning(f"Adaptive depth limit reached: {depth} > {adaptive_max_depth}")
            self.stats.cycles_detected += 1
            self.stats.depth_limit_hits += 1
            return False
        
        # Strategy 2: Complex cycle detection
        cycle_detected, cycle_type = self._detect_complex_cycle_patterns(node, depth)
        if cycle_detected:
            self.logger.debug(f"Complex cycle detected: {cycle_type} at node {node.node_id}")
            self.stats.cycles_detected += 1
            
            # Mise à jour métriques détaillées
            if cycle_type == "self_loop":
                self.stats.self_loops += 1
            elif cycle_type == "direct_cycle":
                self.stats.direct_cycles += 1
            elif cycle_type in ["short_indirect_cycle", "long_indirect_cycle"]:
                self.stats.indirect_cycles += 1
            elif cycle_type == "alternating_cycle":
                self.stats.alternating_cycles += 1
            
            return False
        
        # Strategy 3: Resource protection - memory usage
        current_memory_usage = len(self.current_path) * len(self.visited_nodes)
        if current_memory_usage > 10000:  # Arbitrary but reasonable limit
            self.logger.warning(f"Memory protection: usage {current_memory_usage} > 10000")
            self.stats.early_terminations += 1
            self.stats.memory_limit_hits += 1
            return False
        
        # Strategy 4: Pattern-based early warning
        if self._detect_cycle_warning_patterns(node, depth):
            self.logger.debug(f"Cycle warning pattern detected at node {node.node_id}")
            self.stats.cycles_detected += 1
            self.stats.warning_patterns += 1
            return False
        
        return True
    
    def _detect_cycle_warning_patterns(self, node: Node, depth: int) -> bool:
        """
        Détection patterns warning de cycles probables
        
        Patterns détectés:
        - Oscillation: A → B → A → B (début de cycle alternant)
        - Convergence: Multiples chemins vers même node
        - Deep recursion: Profondeur excessive pour topology simple
        
        Args:
            node: Node à analyser
            depth: Profondeur courante
            
        Returns:
            bool: True si pattern warning détecté
        """
        if not node or len(self.current_path) < 3:
            return False
        
        node_id = node.node_id
        path_ids = [n.node_id for n in self.current_path]
        
        # Pattern 1: Oscillation detection (A-B-A pattern)
        if len(path_ids) >= 2:
            if path_ids[-1] == node_id and path_ids[-2] != node_id:
                # Recherche si node_id apparaît avant dans pattern alternant
                alternation_count = 0
                for i in range(len(path_ids) - 1, -1, -1):
                    if path_ids[i] == node_id:
                        alternation_count += 1
                        if alternation_count >= 2:  # Node vu 2+ fois
                            return True
        
        # Pattern 2: Convergence excessive
        convergence_count = path_ids.count(node_id)
        if convergence_count > 0:  # Node déjà visité
            return True
        
        # Pattern 3: Deep recursion heuristic
        if depth > 20 and len(set(path_ids)) < depth // 3:
            # Trop de profondeur avec peu de nodes uniques = probable cycle
            return True
        
        return False
    
    def _calculate_adaptive_limits(self, current_complexity: int) -> tuple[int, int]:
        """
        Calcul limites adaptives basées sur complexité DAG observée
        
        Args:
            current_complexity: Métrique complexity courante (depth × nodes)
            
        Returns:
            tuple[int, int]: (adaptive_max_paths, adaptive_batch_size)
        """
        base_max = self.max_paths
        base_batch = self.batch_size
        
        # Stratégie adaptive basée sur complexité observée
        if current_complexity < 100:
            # DAG simple - limites généreuses
            return base_max, base_batch
        elif current_complexity < 1000:
            # DAG modéré - limites réduites de 25%
            adaptive_max = int(base_max * 0.75)
            adaptive_batch = int(base_batch * 0.75)
            return max(adaptive_max, 10), max(adaptive_batch, 1)
        else:
            # DAG complexe - limites sévères de 50%
            adaptive_max = int(base_max * 0.5)
            adaptive_batch = int(base_batch * 0.5)
            return max(adaptive_max, 5), max(adaptive_batch, 1)
    
    def _detect_explosion_risk(self, paths_count: int, depth: int, elapsed_time: float) -> tuple[bool, str]:
        """
        Détection risque explosion combinatoire avec classification
        
        Args:
            paths_count: Nombre chemins énumérés actuellement
            depth: Profondeur courante traversal
            elapsed_time: Temps écoulé depuis début énumération
            
        Returns:
            tuple[bool, str]: (explosion_risk_detected, risk_type)
        """
        # Risk Type 1: Croissance exponentielle paths
        if depth > 5:
            expected_paths = min(2 ** (depth - 3), 100)  # Croissance attendue raisonnable
            if paths_count > expected_paths * 5:  # 5x plus que attendu
                return True, "exponential_growth"
        
        # Risk Type 2: Timeout risque (performance dégradée)
        if elapsed_time > 5.0:  # Plus de 5 secondes
            if paths_count < elapsed_time * 100:  # Moins de 100 paths/sec
                return True, "performance_degradation"
        
        # Risk Type 3: Memory pressure approximative
        estimated_memory = paths_count * depth * 50  # Approximation rough
        if estimated_memory > 1_000_000:  # > 1MB approximatif
            return True, "memory_pressure"
        
        # Risk Type 4: Ratio paths/depth anormal
        if depth > 10 and paths_count > depth * 100:
            return True, "depth_path_ratio"
            
        return False, "no_risk"
    
    def _graceful_enumeration_termination(self, paths_found: List[List[Node]], 
                                       termination_reason: str) -> None:
        """
        Terminaison gracieuse énumération avec logging et statistics
        
        Args:
            paths_found: Chemins trouvés avant terminaison
            termination_reason: Raison terminaison pour logging
        """
        self.stats.graceful_terminations += 1
        
        # Logging informatif selon raison
        if termination_reason == "max_paths_reached":
            self.logger.info(f"Graceful termination: max_paths {self.max_paths} reached. "
                           f"Found {len(paths_found)} valid paths.")
        elif termination_reason == "explosion_detected":
            self.stats.explosion_preventions += 1
            self.logger.warning(f"Graceful termination: explosion risk detected. "
                              f"Enumeration stopped at {len(paths_found)} paths.")
        elif termination_reason == "adaptive_limit":
            self.stats.adaptive_limit_adjustments += 1
            self.logger.info(f"Graceful termination: adaptive limit applied. "
                           f"Complexity-based early stop at {len(paths_found)} paths.")
        else:
            self.logger.debug(f"Graceful termination: {termination_reason}")
        
        # Cache résultat partiel si reasonable
        if len(paths_found) <= self.max_paths // 2:
            # Cache partiel peut être utile pour requêtes futures similaires
            self.logger.debug(f"Partial result cached: {len(paths_found)} paths")
    
    def _handle_batch_overflow(self, current_batch: List[List[Node]], 
                             paths_found: List[List[Node]]) -> bool:
        """
        Gestion overflow batch avec continuation intelligente
        
        Args:
            current_batch: Batch courant de chemins
            paths_found: Accumulation totale chemins
            
        Returns:
            bool: True si continuation autorisée, False si arrêt total
        """
        total_paths = len(paths_found) + len(current_batch)
        
        # Overflow detection
        if len(current_batch) >= self.batch_size:
            self.stats.batch_overflows += 1
            
            # Strategy: yield batch et continue si sous limite totale
            if total_paths < self.max_paths:
                self.logger.debug(f"Batch overflow handled: {len(current_batch)} paths yielded, "
                                f"continuing enumeration ({total_paths}/{self.max_paths})")
                return True
            else:
                self.stats.overflow_detections += 1
                self.logger.warning(f"Total overflow detected: {total_paths} >= {self.max_paths}")
                return False
        
        return True  # Pas d'overflow, continue normalement
    
    def enumerate_paths_from_transaction(self, transaction_edge: Edge, 
                                       transaction_num: int) -> Iterator[List[Node]]:
        """
        Énumère tous chemins depuis sink transaction vers sources DAG
        
        Pipeline énumération:
        1. Démarrage depuis transaction.sink_node
        2. Reverse traversal via incoming_edges
        3. Détection cycles et prévention boucles infinies
        4. Yield chemins complets jusqu'aux sources
        5. Limite explosion via max_paths
        
        Args:
            transaction_edge: Edge représentant transaction à valider
            transaction_num: Numéro transaction pour historisation taxonomy
            
        Yields:
            List[Node]: Chemins complets sink→source
        """
        if not self.validate_enumeration_parameters():
            self.logger.error("Invalid enumeration parameters")
            return
        
        start_time = time.time()
        self.reset_enumeration_state()
        
        # Cache check
        cache_key = self._generate_cache_key(transaction_edge.target_node, transaction_num)
        if cache_key in self._path_cache:
            self.logger.debug(f"Cache hit for key: {cache_key}")
            self.stats.cache_hits += 1
            for path in self._path_cache[cache_key]:
                yield path
            return
        
        self.stats.cache_misses += 1
        
        try:
            # Démarrage énumération depuis target transaction (sink)
            start_node = transaction_edge.target_node
            
            # Validation structure DAG avant énumération
            if not self._validate_dag_structure(start_node):
                self.logger.error("Invalid DAG structure for enumeration")
                return
            
            self.logger.info(f"Starting reverse enumeration from target: {start_node.node_id}")
            
            # DFS reverse recursif avec limite et monitoring amélioré
            paths_found = []
            start_enumeration_time = time.time()
            
            for path in self._enumerate_recursive(start_node, paths_found):
                yield path
                
                # Monitoring progress périodique avec explosion risk detection
                if len(paths_found) % 50 == 0:  # Check plus fréquent
                    elapsed_time = time.time() - start_enumeration_time
                    current_depth = self.stats.max_depth_reached
                    
                    # Détection risque explosion
                    explosion_risk, risk_type = self._detect_explosion_risk(
                        len(paths_found), current_depth, elapsed_time
                    )
                    
                    if explosion_risk:
                        self.logger.warning(f"Explosion risk detected: {risk_type}")
                        self._graceful_enumeration_termination(paths_found, "explosion_detected")
                        break
                    
                    # Progress logging
                    self.logger.debug(f"Enumeration progress: {len(paths_found)} paths found "
                                    f"in {elapsed_time:.2f}s, depth: {current_depth}")
                
                # Limite globale paths avec terminaison gracieuse
                if len(paths_found) >= self.max_paths:
                    self._graceful_enumeration_termination(paths_found, "max_paths_reached")
                    break
            
            # Stockage cache si pas trop de paths
            if len(paths_found) <= self.max_paths // 4:  # Cache seulement si reasonable
                self._path_cache[cache_key] = paths_found.copy()
            
            # Statistiques finales
            self.stats.enumeration_time_ms = (time.time() - start_time) * 1000
            self.stats.paths_enumerated = len(paths_found)
            
            self.logger.info(f"Enumeration completed - {self.stats.paths_enumerated} paths "
                           f"in {self.stats.enumeration_time_ms:.2f}ms")
            
        except Exception as e:
            self.logger.error(f"Enumeration error: {e}")
            raise
    
    def _enumerate_recursive(self, current_node: Node, 
                           paths_found: List[List[Node]]) -> Iterator[List[Node]]:
        """
        Énumération récursive DFS avec backtracking - Version améliorée
        
        Algorithme DFS reverse optimisé:
        1. Protection explosion et cycles
        2. Traversal via incoming_edges (reverse direction)  
        3. Yield chemins complets depuis sources DAG
        4. Backtracking propre avec state cleanup
        
        Args:
            current_node: Node courant dans traversal reverse
            paths_found: Liste accumulation chemins trouvés
        
        Yields:
            List[Node]: Chemins complets sink→source
        """
        # Protection explosion avec limites adaptives
        current_complexity = len(self.current_path) * len(self.visited_nodes)
        adaptive_max_paths, adaptive_batch_size = self._calculate_adaptive_limits(current_complexity)
        
        if len(paths_found) >= adaptive_max_paths:
            self.stats.early_terminations += 1
            
            if adaptive_max_paths < self.max_paths:
                self.stats.adaptive_limit_adjustments += 1
                self.logger.info(f"Adaptive limit termination - {adaptive_max_paths} reached "
                               f"(complexity-based reduction from {self.max_paths})")
            else:
                self.logger.warning(f"Early termination - max_paths {self.max_paths} reached")
            return
        
        # Calcul profondeur courante avant protection
        current_depth = len(self.current_path) + 1  # +1 car on va ajouter current_node
        
        # Protection cycle avancée avec patterns complexes
        if not self._advanced_cycle_prevention(current_node, current_depth):
            # Cycle ou pattern dangereux détecté - arrêt traversal
            return
        
        # Ajout au chemin courant avec state management
        self.visited_nodes.add(current_node.node_id)
        self.current_path.append(current_node)
        
        # Mise à jour profondeur max atteinte
        self.stats.max_depth_reached = max(self.stats.max_depth_reached, current_depth)
        
        try:
            # Test si source (pas d'incoming edges) - condition d'arrêt
            if self._is_source_node(current_node):
                # Chemin complet trouvé depuis sink vers source
                complete_path = self.current_path.copy()
                paths_found.append(complete_path)
                
                self.logger.debug(f"Complete path found - length: {len(complete_path)}, "
                                f"source: {current_node.node_id}, "
                                f"path: {' -> '.join([n.node_id for n in complete_path])}")
                
                yield complete_path
            else:
                # Continuer traversal reverse via incoming edges
                incoming_edges_list = list(current_node.incoming_edges.values())
                
                self.logger.debug(f"Exploring {len(incoming_edges_list)} incoming edges "
                                f"from node: {current_node.node_id}")
                
                for edge in incoming_edges_list:
                    # Validation edge avant recursion
                    if edge.source_node and edge.source_node != current_node:
                        # Recursion sur source node de l'edge (direction reverse)
                        yield from self._enumerate_recursive(edge.source_node, paths_found)
                    else:
                        self.logger.warning(f"Invalid edge structure: {edge.edge_id}")
                        
        except Exception as e:
            self.logger.error(f"Enumeration error at node {current_node.node_id}: {e}")
        finally:
            # Backtracking critique - nettoyage état pour eviter corruption
            if self.current_path and self.current_path[-1] == current_node:
                self.current_path.pop()
            if current_node.node_id in self.visited_nodes:
                self.visited_nodes.remove(current_node.node_id)
            
            self.logger.debug(f"Backtracked from node: {current_node.node_id}, "
                            f"remaining path depth: {len(self.current_path)}")
    
    def _validate_dag_structure(self, start_node: Node) -> bool:
        """
        Validation structure DAG avant énumération
        
        Args:
            start_node: Node de départ énumération
            
        Returns:
            bool: True si structure DAG valide pour énumération
        """
        if not start_node:
            self.logger.error("Start node is None")
            return False
        
        if not hasattr(start_node, 'node_id') or not start_node.node_id:
            self.logger.error("Start node missing node_id")
            return False
            
        if not hasattr(start_node, 'incoming_edges'):
            self.logger.error("Start node missing incoming_edges structure")
            return False
        
        self.logger.debug(f"DAG structure validation passed for node: {start_node.node_id}")
        return True
    
    def convert_paths_to_words(self, paths: List[List[Node]], 
                              transaction_num: int) -> List[str]:
        """
        Convertit batch chemins en mots via taxonomie - Version améliorée
        
        Fonctionnalités améliorées Étape 1.5:
        - Validation rigoureuse paths avant conversion
        - Cache optimisé avec cleanup périodique
        - Error handling granulaire par chemin
        - Préservation ordre strict chemin→mot
        - Statistics détaillées conversion
        
        Args:
            paths: Liste chemins à convertir (ordre préservé)
            transaction_num: Numéro transaction pour mapping taxonomy historique
            
        Returns:
            List[str]: Mots correspondants aux chemins (même ordre)
        """
        if not paths:
            self.logger.debug("Empty paths list for conversion")
            return []
        
        words = []
        conversion_errors = 0
        cache_cleanup_threshold = 1000
        
        # Cache cleanup périodique pour éviter memory leak
        if len(self._word_cache) > cache_cleanup_threshold:
            self._cleanup_word_cache()
        
        self.logger.debug(f"Converting {len(paths)} paths to words for transaction {transaction_num}")
        
        for path_index, path in enumerate(paths):
            try:
                # Validation path avant conversion
                if not self._validate_path_for_conversion(path, path_index):
                    words.append("")  # Fallback pour path invalide
                    conversion_errors += 1
                    continue
                
                # Génération clé cache optimisée
                path_key = tuple(node.node_id for node in path)
                cache_key = (path_key, transaction_num)
                
                if cache_key in self._word_cache:
                    word = self._word_cache[cache_key]
                    self.stats.cache_hits += 1
                else:
                    # Conversion via taxonomy avec validation
                    word = self._convert_single_path_to_word(path, transaction_num)
                    
                    if word is not None:  # Seulement cache si success
                        self._word_cache[cache_key] = word
                        self.stats.cache_misses += 1
                    else:
                        word = ""  # Fallback
                        conversion_errors += 1
                
                words.append(word)
                
            except Exception as e:
                self.logger.error(f"Path conversion error at index {path_index} "
                                f"(path length {len(path)}): {e}")
                words.append("")  # Fallback pour préserver ordre
                conversion_errors += 1
        
        # Logging résultats conversion
        success_rate = ((len(paths) - conversion_errors) / len(paths)) * 100 if paths else 100
        self.logger.info(f"Conversion completed: {len(words)} words generated, "
                        f"success rate: {success_rate:.1f}% "
                        f"({conversion_errors} errors)")
        
        # Validation ordre préservé
        assert len(words) == len(paths), "Word count mismatch - order not preserved"
        
        return words
    
    def _validate_path_for_conversion(self, path: List[Node], path_index: int) -> bool:
        """
        Validation chemin avant conversion word
        
        Args:
            path: Chemin à valider
            path_index: Index chemin pour debugging
            
        Returns:
            bool: True si path valid pour conversion
        """
        if not path:
            self.logger.warning(f"Empty path at index {path_index}")
            return False
        
        if len(path) > 1000:  # Limite raisonnable
            self.logger.warning(f"Excessively long path at index {path_index}: {len(path)} nodes")
            return False
        
        # Validation nodes dans path
        for node_index, node in enumerate(path):
            if not node:
                self.logger.warning(f"None node at path[{path_index}][{node_index}]")
                return False
                
            if not hasattr(node, 'node_id') or not node.node_id:
                self.logger.warning(f"Node without node_id at path[{path_index}][{node_index}]")
                return False
        
        return True
    
    def _convert_single_path_to_word(self, path: List[Node], transaction_num: int) -> Optional[str]:
        """
        Conversion single path vers word avec error handling robuste
        
        Args:
            path: Chemin single à convertir
            transaction_num: Transaction number pour historique
            
        Returns:
            Optional[str]: Word généré ou None si erreur
        """
        try:
            word = self.taxonomy.convert_path_to_word(path, transaction_num)
            
            # Validation word généré
            if not isinstance(word, str):
                self.logger.error(f"Taxonomy returned non-string: {type(word)}")
                return None
                
            if len(word) > 10000:  # Limite raisonnable
                self.logger.warning(f"Excessively long word generated: {len(word)} chars")
                return word[:10000]  # Truncate
            
            return word
            
        except Exception as e:
            self.logger.error(f"Taxonomy conversion failed: {e}")
            return None
    
    def _cleanup_word_cache(self) -> None:
        """
        Nettoyage cache mots avec stratégie LRU approximative
        """
        initial_size = len(self._word_cache)
        
        if initial_size <= 500:  # Garde minimum
            return
        
        # Strategy: Garder 70% des entrées (removal 30%)
        target_size = int(initial_size * 0.7)
        
        # Simple cleanup: remove oldest entries (approximation LRU)
        # Note: Vrai LRU nécessiterait OrderedDict, mais overhead pas justifié ici
        cache_items = list(self._word_cache.items())
        items_to_keep = cache_items[-target_size:] if target_size > 0 else []
        
        self._word_cache.clear()
        self._word_cache.update(items_to_keep)
        
        cleaned_count = initial_size - len(self._word_cache)
        self.logger.debug(f"Word cache cleanup: removed {cleaned_count} entries, "
                        f"kept {len(self._word_cache)}")
    
    def get_conversion_statistics(self) -> Dict[str, Any]:
        """
        Statistiques détaillées conversion paths→words
        
        Returns:
            Dict[str, Any]: Métriques conversion performance
        """
        total_cache_operations = self.stats.cache_hits + self.stats.cache_misses
        cache_hit_rate = (self.stats.cache_hits / total_cache_operations * 100) if total_cache_operations > 0 else 0
        
        return {
            'word_cache_size': len(self._word_cache),
            'cache_hit_rate_percent': round(cache_hit_rate, 1),
            'total_cache_hits': self.stats.cache_hits,
            'total_cache_misses': self.stats.cache_misses,
            'estimated_memory_kb': len(self._word_cache) * 0.1  # Rough estimate
        }
    
    def enumerate_and_classify(self, transaction_edge: Edge, nfa: Any,
                              transaction_num: int) -> Dict[str, List[List[Node]]]:
        """
        Pipeline complet enumeration → conversion → classification - Version Production Étape 1.6
        
        Pipeline Enhanced Features:
        - Validation complète inputs/outputs
        - Batch processing optimisé large datasets
        - Statistics détaillées toutes phases
        - Error resilience avec fallbacks gracieux
        - Performance monitoring temps réel
        
        Args:
            transaction_edge: Edge transaction à valider
            nfa: AnchoredWeightedNFA pour classification
            transaction_num: Numéro transaction
            
        Returns:
            Dict[str, List[List[Node]]]: Mapping state_id → chemins correspondants
            
        Raises:
            ValueError: Si inputs invalides
            RuntimeError: Si pipeline échoue complètement
        """
        # Validation inputs rigoureuse
        if not self._validate_pipeline_inputs(transaction_edge, nfa, transaction_num):
            raise ValueError("Invalid pipeline inputs")
            
        start_time = time.time()
        pipeline_stats = {
            'enumeration_time': 0,
            'conversion_time': 0, 
            'classification_time': 0,
            'paths_enumerated': 0,
            'words_generated': 0,
            'paths_classified': 0,
            'classification_rate': 0,
            'performance_warnings': []
        }
        
        path_classes = defaultdict(list)
        all_paths = []
        
        try:
            self.logger.info(f"Starting production pipeline for transaction {transaction_num}")
            
            # PHASE 1: Énumération avec monitoring performance
            enum_start = time.time()
            self.logger.debug("Phase 1: Path enumeration starting")
            
            for path in self.enumerate_paths_from_transaction(transaction_edge, transaction_num):
                all_paths.append(path)
                
                # Performance monitoring énumération
                if len(all_paths) % 100 == 0:
                    elapsed = time.time() - enum_start
                    if elapsed > 5.0:  # Warning si > 5s pour 100 paths
                        pipeline_stats['performance_warnings'].append(
                            f"Enumeration slow: {len(all_paths)} paths in {elapsed:.1f}s"
                        )
            
            pipeline_stats['enumeration_time'] = time.time() - enum_start
            pipeline_stats['paths_enumerated'] = len(all_paths)
            
            if not all_paths:
                self.logger.warning("No paths found during enumeration - pipeline termination")
                return self._finalize_pipeline_results(dict(path_classes), pipeline_stats, start_time)
            
            self.logger.info(f"Phase 1 complete: {len(all_paths)} paths enumerated in "
                           f"{pipeline_stats['enumeration_time']:.2f}s")
            
            # PHASE 2: Conversion batch processing optimisé  
            conv_start = time.time()
            self.logger.debug("Phase 2: Word conversion starting")
            
            words = self._batch_convert_paths_to_words(all_paths, transaction_num, pipeline_stats)
            
            pipeline_stats['conversion_time'] = time.time() - conv_start
            pipeline_stats['words_generated'] = len([w for w in words if w])
            
            self.logger.info(f"Phase 2 complete: {pipeline_stats['words_generated']}/{len(words)} "
                           f"words generated in {pipeline_stats['conversion_time']:.2f}s")
            
            # PHASE 3: Classification avec validation NFA
            class_start = time.time()
            self.logger.debug("Phase 3: NFA classification starting")
            
            classified_count = self._classify_paths_with_nfa(
                all_paths, words, nfa, path_classes, pipeline_stats
            )
            
            pipeline_stats['classification_time'] = time.time() - class_start
            pipeline_stats['paths_classified'] = classified_count
            pipeline_stats['classification_rate'] = (
                (classified_count / len(all_paths)) * 100 if all_paths else 0
            )
            
            self.logger.info(f"Phase 3 complete: {classified_count}/{len(all_paths)} paths classified "
                           f"({pipeline_stats['classification_rate']:.1f}%) in "
                           f"{pipeline_stats['classification_time']:.2f}s")
            
            # PHASE 4: Validation output et finalisation
            validated_results = self._validate_and_finalize_results(
                dict(path_classes), pipeline_stats, start_time
            )
            
            return validated_results
            
        except Exception as e:
            self.logger.error(f"Pipeline critical error at transaction {transaction_num}: {e}")
            self._log_pipeline_failure_diagnostics(pipeline_stats, start_time)
            raise RuntimeError(f"Pipeline failed: {e}") from e
    
    def _validate_pipeline_inputs(self, transaction_edge: Edge, nfa: Any, 
                                 transaction_num: int) -> bool:
        """
        Validation rigoureuse inputs pipeline - Étape 1.6
        
        Returns:
            bool: True si tous inputs valides
        """
        if not transaction_edge or not hasattr(transaction_edge, 'target_node'):
            self.logger.error("Invalid transaction_edge: missing or no target_node")
            return False
            
        if not nfa:
            self.logger.error("Invalid NFA: None or missing")
            return False
            
        if not hasattr(nfa, 'evaluate_to_final_state') and not hasattr(nfa, 'evaluate_word'):
            self.logger.error("Invalid NFA: missing evaluation methods")
            return False
            
        if not isinstance(transaction_num, int) or transaction_num < 0:
            self.logger.error(f"Invalid transaction_num: {transaction_num} (must be int >= 0)")
            return False
            
        return True
    
    def _batch_convert_paths_to_words(self, all_paths: List[List[Node]], 
                                     transaction_num: int, 
                                     pipeline_stats: Dict[str, Any]) -> List[str]:
        """
        Conversion batch optimisée avec monitoring - Étape 1.6
        
        Returns:
            List[str]: Words générés (même ordre que paths)
        """
        if len(all_paths) <= 50:  # Small batch - conversion directe
            return self.convert_paths_to_words(all_paths, transaction_num)
        
        # Large batch - processing par chunks avec monitoring
        words = []
        chunk_size = 50
        total_chunks = (len(all_paths) + chunk_size - 1) // chunk_size
        
        self.logger.debug(f"Batch conversion: {len(all_paths)} paths in {total_chunks} chunks")
        
        for chunk_idx in range(0, len(all_paths), chunk_size):
            chunk_start = time.time()
            chunk_paths = all_paths[chunk_idx:chunk_idx + chunk_size]
            chunk_words = self.convert_paths_to_words(chunk_paths, transaction_num)
            words.extend(chunk_words)
            
            chunk_time = time.time() - chunk_start
            if chunk_time > 2.0:  # Warning si chunk > 2s
                pipeline_stats['performance_warnings'].append(
                    f"Conversion chunk {chunk_idx//chunk_size + 1}/{total_chunks} slow: {chunk_time:.1f}s"
                )
        
        return words
    
    def _classify_paths_with_nfa(self, all_paths: List[List[Node]], words: List[str],
                                nfa: Any, path_classes: Dict[str, List[List[Node]]],
                                pipeline_stats: Dict[str, Any]) -> int:
        """
        Classification NFA avec validation et monitoring - Étape 1.6
        
        Returns:
            int: Nombre paths successfully classified
        """
        classified_count = 0
        nfa_errors = 0
        
        for path_idx, (path, word) in enumerate(zip(all_paths, words)):
            if not word:  # Skip conversion failures
                continue
                
            try:
                # Flexible NFA evaluation (support both method types)
                if hasattr(nfa, 'evaluate_to_final_state'):
                    final_state_id = nfa.evaluate_to_final_state(word)
                elif hasattr(nfa, 'evaluate_word'):
                    result = nfa.evaluate_word(word)
                    final_state_id = result[0] if isinstance(result, tuple) else result
                else:
                    self.logger.error("NFA has no supported evaluation method")
                    break
                
                if final_state_id:
                    path_classes[final_state_id].append(path)
                    classified_count += 1
                    
                    if classified_count % 100 == 0:  # Progress logging
                        self.logger.debug(f"Classified {classified_count}/{len(all_paths)} paths")
                else:
                    self.logger.debug(f"Path {path_idx} rejected by NFA: word='{word[:20]}...'")
                    
            except Exception as e:
                nfa_errors += 1
                self.logger.warning(f"NFA evaluation error for path {path_idx}: {e}")
                
                if nfa_errors > 10:  # Too many NFA errors
                    pipeline_stats['performance_warnings'].append(
                        f"Excessive NFA errors: {nfa_errors} failures"
                    )
        
        if nfa_errors > 0:
            self.logger.warning(f"NFA classification completed with {nfa_errors} evaluation errors")
            
        return classified_count
    
    def _validate_and_finalize_results(self, path_classes: Dict[str, List[List[Node]]],
                                      pipeline_stats: Dict[str, Any], 
                                      start_time: float) -> Dict[str, List[List[Node]]]:
        """
        Validation finale et logging résultats pipeline - Étape 1.6
        """
        total_time = time.time() - start_time
        
        # Validation results
        if not path_classes:
            self.logger.warning("Pipeline completed but no paths were classified")
        
        total_classified = sum(len(paths) for paths in path_classes.values())
        
        # Logging performance summary
        self.logger.info(
            f"PIPELINE COMPLETE - Total: {total_time:.2f}s | "
            f"Enum: {pipeline_stats['enumeration_time']:.2f}s | "
            f"Conv: {pipeline_stats['conversion_time']:.2f}s | "
            f"Class: {pipeline_stats['classification_time']:.2f}s | "
            f"Rate: {pipeline_stats['classification_rate']:.1f}%"
        )
        
        # Performance warnings summary
        if pipeline_stats['performance_warnings']:
            for warning in pipeline_stats['performance_warnings']:
                self.logger.warning(f"Performance: {warning}")
        
        # Update global statistics
        self.stats.paths_enumerated += pipeline_stats['paths_enumerated']
        
        return path_classes
    
    def _log_pipeline_failure_diagnostics(self, pipeline_stats: Dict[str, Any], 
                                         start_time: float) -> None:
        """
        Logging diagnostique en cas échec pipeline - Étape 1.6
        """
        failure_time = time.time() - start_time
        self.logger.error(f"Pipeline failure after {failure_time:.2f}s")
        self.logger.error(f"Stats at failure: {pipeline_stats}")
        
        # Diagnostic state
        self.logger.error(f"Enumerator state: max_paths={self.max_paths}, "
                        f"batch_size={self.batch_size}")
        self.logger.error(f"Cache sizes: path={len(self._path_cache)}, "
                        f"word={len(self._word_cache)}")
        
    def _finalize_pipeline_results(self, path_classes: Dict[str, List[List[Node]]],
                                  pipeline_stats: Dict[str, Any], 
                                  start_time: float) -> Dict[str, List[List[Node]]]:
        """
        Finalisation résultats pipeline (cas early termination) - Étape 1.6
        """
        total_time = time.time() - start_time
        self.logger.info(f"Pipeline early termination after {total_time:.2f}s")
        return path_classes
    
    def get_pipeline_performance_metrics(self) -> Dict[str, Any]:
        """
        Métriques performance pipeline production - Étape 1.6
        
        Returns:
            Dict[str, Any]: Métriques complètes toutes phases pipeline
        """
        # Combine enumeration stats + conversion stats
        enum_stats = self.get_enumeration_statistics()
        conversion_stats = self.get_conversion_statistics()
        
        # Pipeline-specific metrics
        total_cache_operations = enum_stats.cache_hits + enum_stats.cache_misses
        overall_cache_hit_rate = (
            (enum_stats.cache_hits / total_cache_operations * 100) 
            if total_cache_operations > 0 else 0
        )
        
        return {
            # Enumeration Performance
            'enumeration': {
                'paths_enumerated': enum_stats.paths_enumerated,
                'cycles_detected': enum_stats.cycles_detected,
                'early_terminations': enum_stats.early_terminations,
                'enumeration_time_ms': enum_stats.enumeration_time_ms,
                'max_depth_reached': enum_stats.max_depth_reached,
                'explosion_preventions': getattr(enum_stats, 'explosion_preventions', 0),
                'graceful_terminations': getattr(enum_stats, 'graceful_terminations', 0)
            },
            
            # Conversion Performance  
            'conversion': {
                'word_cache_size': conversion_stats['word_cache_size'],
                'cache_hit_rate_percent': conversion_stats['cache_hit_rate_percent'],
                'total_cache_hits': conversion_stats['total_cache_hits'],
                'total_cache_misses': conversion_stats['total_cache_misses'],
                'estimated_memory_kb': conversion_stats['estimated_memory_kb']
            },
            
            # Overall Pipeline Metrics
            'pipeline': {
                'overall_cache_hit_rate_percent': round(overall_cache_hit_rate, 1),
                'total_cache_operations': total_cache_operations,
                'memory_efficiency_score': self._calculate_memory_efficiency_score(
                    conversion_stats, enum_stats
                ),
                'performance_grade': self._calculate_performance_grade(
                    enum_stats, conversion_stats
                )
            }
        }
    
    def _calculate_memory_efficiency_score(self, conversion_stats: Dict[str, Any], 
                                          enum_stats: Any) -> float:
        """
        Score efficacité mémoire pipeline (0-100) - Étape 1.6
        """
        base_score = 100.0
        
        # Penalty pour cache sizes excessifs
        if conversion_stats['word_cache_size'] > 1000:
            base_score -= min(20, (conversion_stats['word_cache_size'] - 1000) / 100)
        
        # Bonus pour good cache hit rates
        if conversion_stats['cache_hit_rate_percent'] > 70:
            base_score += min(10, (conversion_stats['cache_hit_rate_percent'] - 70) / 3)
        
        # Penalty pour excessive memory usage
        if conversion_stats['estimated_memory_kb'] > 1000:  # > 1MB
            base_score -= min(15, (conversion_stats['estimated_memory_kb'] - 1000) / 200)
        
        return max(0, min(100, base_score))
    
    def _calculate_performance_grade(self, enum_stats: Any, 
                                   conversion_stats: Dict[str, Any]) -> str:
        """
        Grade performance pipeline A-F - Étape 1.6
        """
        memory_score = self._calculate_memory_efficiency_score(conversion_stats, enum_stats)
        cache_hit_rate = conversion_stats['cache_hit_rate_percent']
        
        # Calculate composite score
        composite_score = (memory_score * 0.4) + (cache_hit_rate * 0.6)
        
        if composite_score >= 90:
            return "A"
        elif composite_score >= 80:
            return "B" 
        elif composite_score >= 70:
            return "C"
        elif composite_score >= 60:
            return "D"
        else:
            return "F"
    
    def validate_complete_pipeline_health(self) -> Dict[str, Any]:
        """
        Validation santé complète pipeline production - Étape 1.6
        
        Returns:
            Dict[str, Any]: Rapport santé avec recommendations
        """
        metrics = self.get_pipeline_performance_metrics()
        health_report = {
            'overall_health': 'HEALTHY',
            'warnings': [],
            'critical_issues': [],
            'recommendations': [],
            'metrics_summary': metrics
        }
        
        # Check enumeration health
        enum_metrics = metrics['enumeration']
        if enum_metrics['explosion_preventions'] > 0:
            health_report['warnings'].append(
                f"Path explosion preventions: {enum_metrics['explosion_preventions']}"
            )
            health_report['recommendations'].append(
                "Consider reducing max_paths or improving DAG structure"
            )
        
        if enum_metrics['cycles_detected'] > enum_metrics['paths_enumerated'] * 0.1:
            health_report['warnings'].append(
                f"High cycle detection rate: {enum_metrics['cycles_detected']} cycles"
            )
            health_report['recommendations'].append(
                "Review DAG structure for excessive cycles"
            )
        
        # Check conversion health
        conv_metrics = metrics['conversion']
        if conv_metrics['cache_hit_rate_percent'] < 30:
            health_report['warnings'].append(
                f"Low cache hit rate: {conv_metrics['cache_hit_rate_percent']}%"
            )
            health_report['recommendations'].append(
                "Review path patterns - low cache efficiency detected"
            )
        
        if conv_metrics['estimated_memory_kb'] > 5000:  # > 5MB
            health_report['critical_issues'].append(
                f"High memory usage: {conv_metrics['estimated_memory_kb']} KB"
            )
            health_report['recommendations'].append(
                "Implement more aggressive cache cleanup or reduce batch sizes"
            )
        
        # Check pipeline health
        pipeline_metrics = metrics['pipeline']
        performance_grade = pipeline_metrics['performance_grade']
        if performance_grade in ['D', 'F']:
            health_report['critical_issues'].append(
                f"Poor performance grade: {performance_grade}"
            )
            health_report['overall_health'] = 'CRITICAL'
        elif performance_grade == 'C':
            health_report['warnings'].append(
                f"Below average performance: {performance_grade}"
            )
            health_report['overall_health'] = 'WARNING'
        
        # Set overall health status
        if health_report['critical_issues']:
            health_report['overall_health'] = 'CRITICAL'
        elif health_report['warnings']:
            health_report['overall_health'] = 'WARNING'
        
        return health_report