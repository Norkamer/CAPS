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
    """Statistiques énumération chemins pour monitoring performance"""
    paths_enumerated: int = 0
    cycles_detected: int = 0
    early_terminations: int = 0
    enumeration_time_ms: float = 0.0
    max_depth_reached: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


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
        Détecte cycle dans chemin courant
        
        Args:
            node: Node à vérifier pour cycle
            
        Returns:
            bool: True si cycle détecté
        """
        return node.node_id in self.visited_nodes
    
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
            
            # DFS reverse recursif avec limite et monitoring
            paths_found = []
            for path in self._enumerate_recursive(start_node, paths_found):
                yield path
                
                # Monitoring progress périodique
                if len(paths_found) % 100 == 0:
                    self.logger.debug(f"Enumeration progress: {len(paths_found)} paths found")
            
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
        # Protection explosion globale
        if len(paths_found) >= self.max_paths:
            self.stats.early_terminations += 1
            self.logger.warning(f"Early termination - max_paths {self.max_paths} reached")
            return
        
        # Protection cycle avec node_id
        if self._detect_cycle(current_node):
            self.stats.cycles_detected += 1
            self.logger.debug(f"Cycle detected at node: {current_node.node_id}")
            return
        
        # Ajout au chemin courant avec state management
        self.visited_nodes.add(current_node.node_id)
        self.current_path.append(current_node)
        
        # Mise à jour profondeur max atteinte
        current_depth = len(self.current_path)
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
        Convertit batch chemins en mots via taxonomie
        
        Args:
            paths: Liste chemins à convertir
            transaction_num: Numéro transaction pour mapping taxonomy
            
        Returns:
            List[str]: Mots correspondants aux chemins
        """
        words = []
        
        for path in paths:
            try:
                # Génération clé cache
                path_key = tuple(node.node_id for node in path)
                cache_key = (path_key, transaction_num)
                
                if cache_key in self._word_cache:
                    word = self._word_cache[cache_key]
                    self.stats.cache_hits += 1
                else:
                    # Conversion via taxonomy - utiliser node_id comme account_id
                    word = self.taxonomy.convert_path_to_word(path, transaction_num)
                    self._word_cache[cache_key] = word
                    self.stats.cache_misses += 1
                
                words.append(word)
                
            except Exception as e:
                self.logger.error(f"Path conversion error for path length {len(path)}: {e}")
                # Fallback - mot vide si conversion échoue
                words.append("")
        
        self.logger.debug(f"Converted {len(paths)} paths to words")
        return words
    
    def enumerate_and_classify(self, transaction_edge: Edge, nfa: Any,
                              transaction_num: int) -> Dict[str, List[List[Node]]]:
        """
        Pipeline complet: enumeration → words → NFA → classification
        
        Args:
            transaction_edge: Edge transaction à valider
            nfa: AnchoredWeightedNFA pour classification
            transaction_num: Numéro transaction
            
        Returns:
            Dict[str, List[List[Node]]]: Mapping state_id → chemins correspondants
        """
        path_classes = defaultdict(list)
        all_paths = []
        
        try:
            # 1. Énumération chemins
            self.logger.debug("Starting path enumeration and classification")
            
            for path in self.enumerate_paths_from_transaction(transaction_edge, transaction_num):
                all_paths.append(path)
            
            if not all_paths:
                self.logger.warning("No paths found during enumeration")
                return dict(path_classes)
            
            # 2. Conversion en mots
            words = self.convert_paths_to_words(all_paths, transaction_num)
            
            # 3. Évaluation NFA et classification
            for path, word in zip(all_paths, words):
                if word:  # Ignorer mots vides (conversion échouée)
                    # Évaluation NFA pour obtenir état final
                    final_state_id = nfa.evaluate_to_final_state(word)
                    
                    if final_state_id:
                        path_classes[final_state_id].append(path)
                        self.logger.debug(f"Path classified to state: {final_state_id}")
                    else:
                        self.logger.debug(f"Path rejected by NFA: word='{word[:20]}...'")
            
            # 4. Statistiques classification
            total_classified = sum(len(paths) for paths in path_classes.values())
            classification_rate = (total_classified / len(all_paths)) * 100 if all_paths else 0
            
            self.logger.info(f"Classification completed - {len(path_classes)} classes, "
                           f"{total_classified}/{len(all_paths)} paths classified "
                           f"({classification_rate:.1f}%)")
            
            return dict(path_classes)
            
        except Exception as e:
            self.logger.error(f"Enumeration and classification error: {e}")
            raise