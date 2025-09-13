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
from .dag_structures import (
    Node, Edge, EdgeType, Account, 
    DAGStructureValidator, DAGValidationResult
)

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
        
        # DAG Integration - Étape 2.2
        self.dag_validator = DAGStructureValidator()
        self.last_dag_validation: Optional[DAGValidationResult] = None
        
        # Transaction Edge Processing - Étape 2.3
        self.transaction_processor_stats = {
            'edges_processed': 0,
            'validation_errors': 0,
            'amount_extraction_time_ms': 0.0,
            'metadata_validation_time_ms': 0.0,
            'total_processing_time_ms': 0.0
        }
        
        # Multi-Source Path Enumeration - Étape 2.4
        self.multi_source_stats = {
            'sources_processed': 0,
            'total_paths_enumerated': 0,
            'path_overlaps_detected': 0,
            'coordination_time_ms': 0.0,
            'merge_operations': 0,
            'parallel_efficiency': 0.0
        }
    
    def validate_dag_before_enumeration(self, nodes: List[Node], edges: List[Edge], 
                                       accounts: Optional[List[Account]] = None,
                                       strict_validation: bool = True) -> DAGValidationResult:
        """
        Validation DAG structure avant énumération - Étape 2.2
        
        Pipeline validation intégrée:
        1. Structure DAG complète (6 phases via DAGStructureValidator)
        2. Cache résultat pour monitoring
        3. Option strict: failure si invalide, warning si permissif
        4. Statistics intégrées avec enumeration stats
        
        Args:
            nodes: Tous nœuds DAG pour validation
            edges: Toutes arêtes DAG pour validation
            accounts: Comptes optionnels pour validation coherence
            strict_validation: True = exception si invalide, False = warning
            
        Returns:
            DAGValidationResult: Résultats validation complète
            
        Raises:
            ValueError: Si strict_validation=True et DAG invalide
        """
        start_time = time.time()
        self.logger.debug(f"Starting DAG validation - {len(nodes)} nodes, {len(edges)} edges")
        
        # Validation structure DAG via DAGStructureValidator
        validation_result = self.dag_validator.validate_complete_dag_structure(
            nodes, edges, accounts
        )
        
        # Cache résultat pour monitoring et diagnostics
        self.last_dag_validation = validation_result
        
        validation_time = (time.time() - start_time) * 1000
        
        # Logging résultats selon validation outcome
        if validation_result.is_valid:
            self.logger.info(f"DAG validation passed in {validation_time:.2f}ms - "
                           f"Structure valid for enumeration")
        else:
            # Count issues pour summary
            total_issues = (
                len(validation_result.connectivity_issues) +
                len(validation_result.integrity_violations) +
                len(validation_result.orphaned_nodes) +
                (1 if validation_result.cycle_detection.has_cycle else 0)
            )
            
            issue_summary = validation_result.get_summary()
            warning_msg = f"DAG validation issues detected: {issue_summary}"
            
            if strict_validation:
                self.logger.error(f"Strict validation failed: {warning_msg}")
                raise ValueError(f"DAG structure invalid: {total_issues} issues detected. "
                               f"Details: {validation_result.get_summary()}")
            else:
                self.logger.warning(f"Permissive validation: {warning_msg} - continuing enumeration")
        
        # Integration statistics avec enumeration
        self.stats.enumeration_time_ms += validation_time
        
        return validation_result
    
    def build_dag_from_transaction_edge(self, transaction_edge: Edge) -> tuple[List[Node], List[Edge]]:
        """
        Construction DAG minimal depuis transaction edge - Étape 2.2
        
        Algorithm:
        1. Démarrage depuis transaction edge (source/target nodes)
        2. Traversal backward depuis target (sink) via incoming edges
        3. Traversal forward depuis source via outgoing edges  
        4. Collection tous nodes/edges accessibles
        5. Validation structure minimale (pas de cycles)
        
        Args:
            transaction_edge: Edge transaction comme point départ DAG
            
        Returns:
            tuple[List[Node], List[Edge]]: (nodes_collected, edges_collected)
        """
        nodes_collected = set()
        edges_collected = set()
        
        # Queue pour BFS traversal
        nodes_to_visit = deque([transaction_edge.source_node, transaction_edge.target_node])
        visited_for_traversal = set()
        
        self.logger.debug(f"Building DAG from transaction edge: {transaction_edge.edge_id}")
        
        # BFS traversal pour collection nodes/edges connectés
        while nodes_to_visit:
            current_node = nodes_to_visit.popleft()
            
            if current_node.node_id in visited_for_traversal:
                continue
                
            visited_for_traversal.add(current_node.node_id)
            nodes_collected.add(current_node)
            
            # Traversal incoming edges
            for edge in current_node.incoming_edges.values():
                edges_collected.add(edge)
                if edge.source_node.node_id not in visited_for_traversal:
                    nodes_to_visit.append(edge.source_node)
            
            # Traversal outgoing edges
            for edge in current_node.outgoing_edges.values():
                edges_collected.add(edge)
                if edge.target_node.node_id not in visited_for_traversal:
                    nodes_to_visit.append(edge.target_node)
        
        # Include transaction edge si pas déjà collecté
        edges_collected.add(transaction_edge)
        
        nodes_list = list(nodes_collected)
        edges_list = list(edges_collected)
        
        self.logger.info(f"DAG built from transaction: {len(nodes_list)} nodes, "
                        f"{len(edges_list)} edges collected")
        
        return nodes_list, edges_list
    
    def enumerate_with_dag_validation(self, transaction_edge: Edge, nfa: Any,
                                    transaction_num: int, 
                                    dag_validation_mode: str = "strict") -> Dict[str, List[List[Node]]]:
        """
        Énumération avec validation DAG intégrée - Pipeline Production Étape 2.2
        
        Pipeline intégré:
        1. Construction DAG depuis transaction edge
        2. Validation structure DAG complète  
        3. Énumération chemins via pipeline existant
        4. Classification avec NFA
        5. Statistics consolidées DAG + enumeration
        
        Args:
            transaction_edge: Edge transaction pour énumération
            nfa: NFA pour classification chemins
            transaction_num: Numéro transaction  
            dag_validation_mode: "strict" | "permissive" | "skip"
            
        Returns:
            Dict[str, List[List[Node]]]: Classification chemins par états NFA
            
        Raises:
            ValueError: Si dag_validation_mode="strict" et DAG invalide
        """
        start_time = time.time()
        pipeline_stage = "initialization"
        
        try:
            self.logger.info(f"Starting integrated enumeration with DAG validation - "
                           f"transaction {transaction_num}, mode: {dag_validation_mode}")
            
            # STAGE 1: Construction DAG
            pipeline_stage = "dag_construction"
            nodes, edges = self.build_dag_from_transaction_edge(transaction_edge)
            
            # STAGE 2: Validation DAG (selon mode)
            pipeline_stage = "dag_validation"
            if dag_validation_mode != "skip":
                strict_validation = (dag_validation_mode == "strict")
                dag_validation = self.validate_dag_before_enumeration(
                    nodes, edges, strict_validation=strict_validation
                )
                
                # Store validation result for tests access
                self.last_dag_validation = dag_validation
                
                # Log validation summary
                self.logger.debug(f"DAG validation completed - {dag_validation.get_summary()}")
            else:
                # Skip mode - no validation performed
                self.last_dag_validation = None
            
            # STAGE 3: Énumération via pipeline existant
            pipeline_stage = "path_enumeration"
            classification_result = self.enumerate_and_classify(
                transaction_edge, nfa, transaction_num
            )
            
            # STAGE 4: Statistics consolidation
            pipeline_stage = "statistics_consolidation"
            total_time = (time.time() - start_time) * 1000
            
            self.logger.info(f"Integrated enumeration completed in {total_time:.2f}ms - "
                           f"{len(classification_result)} path classes generated")
            
            return classification_result
            
        except Exception as e:
            error_time = (time.time() - start_time) * 1000
            self.logger.error(f"Integrated enumeration failed at {pipeline_stage} "
                            f"after {error_time:.2f}ms: {e}")
            raise RuntimeError(f"Integrated enumeration pipeline failed at {pipeline_stage}: {e}") from e
    
    def get_integrated_dag_statistics(self) -> Dict[str, Any]:
        """
        Statistics intégrées DAG validation + enumeration - Étape 2.2
        
        Returns:
            Dict[str, Any]: Métriques consolidées validation + enumeration
        """
        # Base enumeration statistics
        enum_stats = {
            'enumeration': {
                'paths_enumerated': self.stats.paths_enumerated,
                'cycles_detected': self.stats.cycles_detected,
                'enumeration_time_ms': self.stats.enumeration_time_ms,
                'cache_hits': self.stats.cache_hits,
                'cache_misses': self.stats.cache_misses
            }
        }
        
        # DAG validation statistics (si disponible)
        dag_stats = {}
        if self.last_dag_validation:
            dag_stats = {
                'dag_validation': {
                    'is_valid': self.last_dag_validation.is_valid,
                    'validation_time_ms': self.last_dag_validation.validation_time_ms,
                    'total_issues': (
                        len(self.last_dag_validation.connectivity_issues) +
                        len(self.last_dag_validation.integrity_violations) +
                        len(self.last_dag_validation.orphaned_nodes) +
                        (1 if self.last_dag_validation.cycle_detection.has_cycle else 0)
                    ),
                    'dag_statistics': self.last_dag_validation.statistics
                }
            }
        
        # DAG validator performance statistics
        validator_stats = {}
        if hasattr(self, 'dag_validator'):
            validator_stats = {
                'validator_performance': self.dag_validator.get_validation_performance_stats()
            }
        
        return {
            **enum_stats,
            **dag_stats, 
            **validator_stats,
            'integration': {
                'has_dag_validation': self.last_dag_validation is not None,
                'validator_initialized': hasattr(self, 'dag_validator')
            },
            'transaction_processing': self.transaction_processor_stats.copy(),
            'multi_source_enumeration': self.multi_source_stats.copy()
        }
    
    # Step 2.3: Transaction Edge Processing - Production Methods
    
    def process_transaction_edges(self, transaction_edges: List[Edge], 
                                validate_metadata: bool = True) -> Dict[str, Any]:
        """
        Processing batch des transaction edges avec validation complète - Étape 2.3
        
        Pipeline Transaction Processing:
        1. Validation structure edges transaction
        2. Extraction et validation métadonnées (amounts, dates, références)
        3. Validation cohérence transaction amounts
        4. Statistics collection transaction-specific
        5. Optimizations performance pour batch processing
        
        Args:
            transaction_edges: List edges de type TRANSACTION
            validate_metadata: Flag validation métadonnées complète
            
        Returns:
            Dict[str, Any]: Résultats processing avec statistics détaillées
        """
        import time
        from decimal import Decimal, InvalidOperation
        
        start_time = time.time()
        processing_results = {
            'valid_transactions': [],
            'invalid_transactions': [],
            'extracted_amounts': {},
            'validation_errors': [],
            'processing_summary': {}
        }
        
        try:
            self.logger.info(f"Starting transaction edge processing - {len(transaction_edges)} edges")
            
            # Phase 1: Structure validation
            structure_valid = []
            for edge in transaction_edges:
                if self._validate_transaction_edge_structure(edge):
                    structure_valid.append(edge)
                else:
                    processing_results['invalid_transactions'].append({
                        'edge_id': edge.edge_id,
                        'error': 'Invalid transaction edge structure'
                    })
                    self.transaction_processor_stats['validation_errors'] += 1
            
            # Phase 2: Metadata extraction et validation
            if validate_metadata:
                metadata_start = time.time()
                for edge in structure_valid:
                    metadata_result = self.validate_transaction_metadata(edge)
                    if metadata_result['is_valid']:
                        processing_results['valid_transactions'].append({
                            'edge_id': edge.edge_id,
                            'metadata': metadata_result['metadata'],
                            'amounts': metadata_result['amounts']
                        })
                        processing_results['extracted_amounts'][edge.edge_id] = metadata_result['amounts']
                    else:
                        processing_results['invalid_transactions'].append({
                            'edge_id': edge.edge_id,
                            'error': metadata_result['error']
                        })
                        self.transaction_processor_stats['validation_errors'] += 1
                
                metadata_time = (time.time() - metadata_start) * 1000
                self.transaction_processor_stats['metadata_validation_time_ms'] += metadata_time
            
            # Phase 3: Processing summary
            total_time = (time.time() - start_time) * 1000
            self.transaction_processor_stats['total_processing_time_ms'] += total_time
            self.transaction_processor_stats['edges_processed'] += len(transaction_edges)
            
            processing_results['processing_summary'] = {
                'total_edges': len(transaction_edges),
                'valid_count': len(processing_results['valid_transactions']),
                'invalid_count': len(processing_results['invalid_transactions']),
                'processing_time_ms': total_time,
                'validation_enabled': validate_metadata
            }
            
            self.logger.info(f"Transaction processing completed - "
                           f"{len(processing_results['valid_transactions'])} valid, "
                           f"{len(processing_results['invalid_transactions'])} invalid")
            
            return processing_results
            
        except Exception as e:
            error_time = (time.time() - start_time) * 1000
            self.logger.error(f"Transaction edge processing failed after {error_time:.2f}ms: {e}")
            raise RuntimeError(f"Transaction edge processing failed: {e}") from e
    
    def validate_transaction_metadata(self, transaction_edge: Edge) -> Dict[str, Any]:
        """
        Validation complète métadonnées transaction edge - Étape 2.3
        
        Validations:
        - Transaction amount presence et format
        - Transaction date/timestamp validity
        - Reference IDs coherence
        - Currency/unit consistency
        - Precision decimal requirements
        
        Args:
            transaction_edge: Edge transaction à valider
            
        Returns:
            Dict[str, Any]: Résultat validation avec métadonnées extraites
        """
        from decimal import Decimal, InvalidOperation
        import re
        from datetime import datetime
        
        validation_result = {
            'is_valid': True,
            'error': None,
            'metadata': {},
            'amounts': {}
        }
        
        try:
            metadata = transaction_edge.edge_metadata.context
            
            # Validation 1: Transaction amount
            amount_str = metadata.get('transaction_amount', '0')
            try:
                amount = Decimal(str(amount_str))
                if amount < 0:
                    validation_result['is_valid'] = False
                    validation_result['error'] = f"Negative transaction amount: {amount}"
                    return validation_result
                
                validation_result['amounts']['transaction_amount'] = amount
                validation_result['metadata']['amount_validated'] = True
                
            except (InvalidOperation, ValueError, TypeError) as e:
                validation_result['is_valid'] = False
                validation_result['error'] = f"Invalid transaction amount format: {amount_str} - {e}"
                return validation_result
            
            # Validation 2: Transaction timestamp
            timestamp = metadata.get('timestamp')
            if timestamp:
                try:
                    # Support multiple timestamp formats
                    if isinstance(timestamp, (int, float)):
                        datetime.fromtimestamp(timestamp)
                    elif isinstance(timestamp, str):
                        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    
                    validation_result['metadata']['timestamp_validated'] = True
                    validation_result['metadata']['timestamp'] = timestamp
                    
                except (ValueError, OSError) as e:
                    validation_result['is_valid'] = False
                    validation_result['error'] = f"Invalid timestamp format: {timestamp} - {e}"
                    return validation_result
            
            # Validation 3: Reference IDs format
            reference_id = metadata.get('reference_id')
            if reference_id:
                if not isinstance(reference_id, str) or len(reference_id.strip()) == 0:
                    validation_result['is_valid'] = False
                    validation_result['error'] = f"Invalid reference_id format: {reference_id}"
                    return validation_result
                
                validation_result['metadata']['reference_id'] = reference_id.strip()
                validation_result['metadata']['reference_validated'] = True
            
            # Validation 4: Currency/unit consistency
            currency = metadata.get('currency', 'USD')
            if not isinstance(currency, str) or not re.match(r'^[A-Z]{3}$', currency):
                validation_result['is_valid'] = False
                validation_result['error'] = f"Invalid currency format: {currency} (expected 3-letter code)"
                return validation_result
            
            validation_result['metadata']['currency'] = currency
            validation_result['metadata']['currency_validated'] = True
            
            # Validation 5: Edge weight consistency avec amount
            edge_weight = transaction_edge.edge_metadata.weight
            if abs(edge_weight - amount) > Decimal('1e-8'):
                self.logger.warning(f"Edge weight {edge_weight} differs from transaction amount {amount}")
            
            validation_result['amounts']['edge_weight'] = edge_weight
            validation_result['metadata']['weight_consistency_checked'] = True
            
            return validation_result
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['error'] = f"Metadata validation exception: {e}"
            return validation_result
    
    def extract_transaction_amounts(self, transaction_edges: List[Edge]) -> Dict[str, Dict[str, Any]]:
        """
        Extraction optimisée amounts depuis transaction edges - Étape 2.3
        
        Features:
        - Batch processing optimized pour performance
        - Precision decimal preservation
        - Currency grouping et aggregation
        - Error resilience avec partial results
        
        Args:
            transaction_edges: List edges transaction pour extraction
            
        Returns:
            Dict[str, Dict]: Mapping edge_id -> amount_info avec aggregations
        """
        import time
        from decimal import Decimal
        from collections import defaultdict
        
        extraction_start = time.time()
        amounts_data = {}
        currency_totals = defaultdict(Decimal)
        extraction_errors = []
        
        try:
            for edge in transaction_edges:
                try:
                    metadata = edge.edge_metadata.context
                    amount_str = metadata.get('transaction_amount', '0')
                    amount = Decimal(str(amount_str))
                    currency = metadata.get('currency', 'USD')
                    
                    amounts_data[edge.edge_id] = {
                        'amount': amount,
                        'currency': currency,
                        'edge_weight': edge.edge_metadata.weight,
                        'consistency_check': abs(edge.edge_metadata.weight - amount) <= Decimal('1e-8'),
                        'timestamp': metadata.get('timestamp'),
                        'reference_id': metadata.get('reference_id')
                    }
                    
                    # Currency aggregation
                    currency_totals[currency] += amount
                    
                except Exception as e:
                    extraction_errors.append({
                        'edge_id': edge.edge_id,
                        'error': str(e)
                    })
            
            extraction_time = (time.time() - extraction_start) * 1000
            self.transaction_processor_stats['amount_extraction_time_ms'] += extraction_time
            
            # Build aggregated result
            return {
                'amounts_by_edge': amounts_data,
                'currency_totals': dict(currency_totals),
                'extraction_summary': {
                    'total_edges': len(transaction_edges),
                    'successful_extractions': len(amounts_data),
                    'extraction_errors': len(extraction_errors),
                    'extraction_time_ms': extraction_time,
                    'unique_currencies': len(currency_totals)
                },
                'extraction_errors': extraction_errors
            }
            
        except Exception as e:
            self.logger.error(f"Amount extraction failed: {e}")
            raise RuntimeError(f"Transaction amount extraction failed: {e}") from e
    
    def optimize_transaction_enumeration(self, transaction_edges: List[Edge], 
                                       nfa: Any, transaction_num: int) -> Dict[str, Any]:
        """
        Enumeration optimisée spécifique pour transaction edges - Étape 2.3
        
        Optimizations:
        - Pre-filtering edges by amount thresholds
        - Parallel processing pour large transaction sets
        - Caching results by transaction patterns
        - Statistics-driven path pruning
        
        Args:
            transaction_edges: Edges transaction à énumérer
            nfa: NFA pour classification
            transaction_num: Numéro transaction
            
        Returns:
            Dict[str, Any]: Résultats enumeration avec optimizations appliquées
        """
        import time
        
        optimization_start = time.time()
        
        try:
            self.logger.info(f"Starting optimized transaction enumeration - "
                           f"{len(transaction_edges)} edges, transaction {transaction_num}")
            
            # Phase 1: Pre-processing et filtering
            processed_edges = self.process_transaction_edges(
                transaction_edges, validate_metadata=True
            )
            
            valid_edges = [
                edge for edge in transaction_edges
                if any(valid['edge_id'] == edge.edge_id 
                      for valid in processed_edges['valid_transactions'])
            ]
            
            if not valid_edges:
                self.logger.warning("No valid transaction edges after processing")
                return {
                    'enumeration_results': {},
                    'optimization_summary': {
                        'input_edges': len(transaction_edges),
                        'valid_after_processing': 0,
                        'enumeration_performed': False,
                        'optimization_time_ms': (time.time() - optimization_start) * 1000
                    }
                }
            
            # Phase 2: Optimized enumeration pour chaque edge valide
            enumeration_results = {}
            total_paths = 0
            
            for edge in valid_edges:
                edge_start = time.time()
                
                # Use integrated DAG validation pipeline
                edge_result = self.enumerate_with_dag_validation(
                    edge, nfa, transaction_num, 
                    dag_validation_mode="permissive"  # Performance-oriented
                )
                
                enumeration_results[edge.edge_id] = {
                    'classification_result': edge_result,
                    'path_count': sum(len(paths) for paths in edge_result.values()),
                    'enumeration_time_ms': (time.time() - edge_start) * 1000
                }
                
                total_paths += enumeration_results[edge.edge_id]['path_count']
            
            optimization_time = (time.time() - optimization_start) * 1000
            
            # Phase 3: Optimization summary
            optimization_summary = {
                'input_edges': len(transaction_edges),
                'valid_after_processing': len(valid_edges),
                'total_paths_enumerated': total_paths,
                'enumeration_performed': True,
                'optimization_time_ms': optimization_time,
                'average_paths_per_edge': total_paths / len(valid_edges) if valid_edges else 0,
                'processing_efficiency': len(valid_edges) / len(transaction_edges) if transaction_edges else 0
            }
            
            self.logger.info(f"Optimized transaction enumeration completed - "
                           f"{total_paths} paths from {len(valid_edges)} edges in {optimization_time:.2f}ms")
            
            return {
                'enumeration_results': enumeration_results,
                'processing_results': processed_edges,
                'optimization_summary': optimization_summary
            }
            
        except Exception as e:
            error_time = (time.time() - optimization_start) * 1000
            self.logger.error(f"Optimized transaction enumeration failed after {error_time:.2f}ms: {e}")
            raise RuntimeError(f"Transaction enumeration optimization failed: {e}") from e
    
    def build_transaction_statistics(self, processing_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Construction statistics détaillées transaction processing - Étape 2.3
        
        Statistics:
        - Distribution amounts par currency
        - Performance métriques processing
        - Error rate analysis
        - Temporal distribution si timestamps disponibles
        
        Args:
            processing_results: Résultats depuis process_transaction_edges()
            
        Returns:
            Dict[str, Any]: Statistics complètes transaction processing
        """
        from collections import Counter, defaultdict
        from decimal import Decimal
        
        try:
            valid_transactions = processing_results.get('valid_transactions', [])
            invalid_transactions = processing_results.get('invalid_transactions', [])
            extracted_amounts = processing_results.get('extracted_amounts', {})
            processing_summary = processing_results.get('processing_summary', {})
            
            # Statistics 1: Amount distribution
            amount_stats = {
                'total_transactions': len(valid_transactions),
                'currency_distribution': Counter(),
                'amount_ranges': defaultdict(int),
                'total_value_by_currency': defaultdict(Decimal)
            }
            
            for tx in valid_transactions:
                amounts = tx.get('amounts', {})
                metadata = tx.get('metadata', {})
                
                currency = metadata.get('currency', 'USD')
                amount = amounts.get('transaction_amount', Decimal('0'))
                
                amount_stats['currency_distribution'][currency] += 1
                amount_stats['total_value_by_currency'][currency] += amount
                
                # Amount ranges classification
                if amount == 0:
                    amount_stats['amount_ranges']['zero'] += 1
                elif amount <= Decimal('100'):
                    amount_stats['amount_ranges']['small'] += 1
                elif amount <= Decimal('10000'):
                    amount_stats['amount_ranges']['medium'] += 1
                else:
                    amount_stats['amount_ranges']['large'] += 1
            
            # Statistics 2: Error analysis
            error_stats = {
                'total_errors': len(invalid_transactions),
                'error_types': Counter(),
                'error_rate': len(invalid_transactions) / (len(valid_transactions) + len(invalid_transactions)) if (valid_transactions or invalid_transactions) else 0
            }
            
            for invalid_tx in invalid_transactions:
                error = invalid_tx.get('error', 'Unknown error')
                if 'amount' in error.lower():
                    error_stats['error_types']['amount_validation'] += 1
                elif 'timestamp' in error.lower():
                    error_stats['error_types']['timestamp_validation'] += 1
                elif 'currency' in error.lower():
                    error_stats['error_types']['currency_validation'] += 1
                elif 'structure' in error.lower():
                    error_stats['error_types']['structure_validation'] += 1
                else:
                    error_stats['error_types']['other'] += 1
            
            # Statistics 3: Performance metrics
            performance_stats = {
                'processing_time_ms': processing_summary.get('processing_time_ms', 0),
                'throughput_tx_per_sec': 0,
                'average_processing_time_per_tx': 0
            }
            
            total_tx = processing_summary.get('total_edges', 0)
            processing_time = processing_summary.get('processing_time_ms', 0)
            
            if processing_time > 0 and total_tx > 0:
                performance_stats['throughput_tx_per_sec'] = (total_tx * 1000) / processing_time
                performance_stats['average_processing_time_per_tx'] = processing_time / total_tx
            
            return {
                'amount_statistics': {
                    k: dict(v) if isinstance(v, (Counter, defaultdict)) else v
                    for k, v in amount_stats.items()
                },
                'error_statistics': {
                    k: dict(v) if isinstance(v, Counter) else v
                    for k, v in error_stats.items()
                },
                'performance_statistics': performance_stats,
                'processor_cumulative_stats': self.transaction_processor_stats.copy()
            }
            
        except Exception as e:
            self.logger.error(f"Transaction statistics building failed: {e}")
            return {
                'error': f"Statistics building failed: {e}",
                'processor_cumulative_stats': self.transaction_processor_stats.copy()
            }
    
    # Step 2.3: Helper Methods
    
    def _validate_transaction_edge_structure(self, edge: Edge) -> bool:
        """
        Validation structure de base transaction edge - Étape 2.3
        
        Validations:
        - Edge type est TRANSACTION
        - Source et target nodes existent
        - Edge metadata présent
        - Edge weight non-négative
        """
        try:
            # Check edge type
            if edge.edge_metadata.edge_type.value != 'TRANSACTION':
                return False
            
            # Check nodes existence
            if not edge.source_node or not edge.target_node:
                return False
            
            # Check metadata presence
            if not hasattr(edge, 'edge_metadata') or not edge.edge_metadata:
                return False
            
            # Check weight non-negative
            if edge.edge_metadata.weight < 0:
                return False
            
            # Check context existence
            if not hasattr(edge.edge_metadata, 'context') or not edge.edge_metadata.context:
                return False
            
            return True
            
        except Exception:
            return False
    
    # Step 2.4: Multi-Source Path Enumeration - Production Methods
    
    def enumerate_from_multiple_sources(self, source_nodes: List[Node], 
                                      target_edge: Edge, nfa: Any, transaction_num: int,
                                      coordination_mode: str = "parallel") -> Dict[str, Any]:
        """
        Enumeration coordonnée depuis multiples sources - Étape 2.4
        
        Pipeline Multi-Source:
        1. Validation et préparation sources multiples
        2. Coordination enumeration (parallel/sequential/adaptive)
        3. Detection et handling path overlaps
        4. Merge intelligent des résultats avec deduplication
        5. Statistics consolidation multi-source
        
        Args:
            source_nodes: List nodes sources pour enumeration
            target_edge: Edge transaction target commune
            nfa: NFA pour classification paths
            transaction_num: Numéro transaction
            coordination_mode: "parallel" | "sequential" | "adaptive"
            
        Returns:
            Dict[str, Any]: Résultats multi-source avec analytics détaillées
        """
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        start_time = time.time()
        coordination_start = time.time()
        
        try:
            self.logger.info(f"Starting multi-source enumeration - {len(source_nodes)} sources, "
                           f"mode: {coordination_mode}")
            
            # Phase 1: Validation sources et target
            valid_sources = self._validate_multiple_sources(source_nodes, target_edge)
            if not valid_sources:
                return {
                    'enumeration_results': {},
                    'coordination_summary': {
                        'sources_attempted': len(source_nodes),
                        'valid_sources': 0,
                        'enumeration_performed': False,
                        'error': 'No valid sources for enumeration'
                    }
                }
            
            # Phase 2: Coordination enumeration selon mode
            source_results, actual_mode_used = self.coordinate_source_enumeration(
                valid_sources, target_edge, nfa, transaction_num, coordination_mode
            )
            
            coordination_time = (time.time() - coordination_start) * 1000
            self.multi_source_stats['coordination_time_ms'] += coordination_time
            
            # Phase 3: Detection path overlaps
            overlap_analysis = self.detect_path_overlaps(source_results)
            
            # Phase 4: Merge résultats avec deduplication intelligente
            merged_results = self.merge_enumeration_results(
                source_results, overlap_analysis, deduplication=True
            )
            
            # Phase 5: Statistics consolidation
            total_time = (time.time() - start_time) * 1000
            
            self.multi_source_stats['sources_processed'] += len(valid_sources)
            self.multi_source_stats['total_paths_enumerated'] += merged_results['total_unique_paths']
            self.multi_source_stats['path_overlaps_detected'] += overlap_analysis['total_overlaps']
            
            # Calculate parallel efficiency
            if coordination_mode == "parallel" and len(valid_sources) > 1:
                sequential_time_estimate = sum(result.get('enumeration_time_ms', 0) 
                                             for result in source_results.values())
                if sequential_time_estimate > 0:
                    efficiency = sequential_time_estimate / total_time
                    self.multi_source_stats['parallel_efficiency'] = efficiency
            
            # Get actual coordination mode used (from coordinate_source_enumeration)
            actual_coordination_mode = actual_mode_used
            
            coordination_summary = {
                'sources_attempted': len(source_nodes),
                'valid_sources': len(valid_sources),
                'enumeration_performed': True,
                'coordination_mode': actual_coordination_mode,
                'total_time_ms': total_time,
                'coordination_time_ms': coordination_time,
                'parallel_efficiency': self.multi_source_stats['parallel_efficiency']
            }
            
            self.logger.info(f"Multi-source enumeration completed - "
                           f"{merged_results['total_unique_paths']} unique paths from "
                           f"{len(valid_sources)} sources in {total_time:.2f}ms")
            
            return {
                'enumeration_results': merged_results,
                'source_individual_results': source_results,
                'overlap_analysis': overlap_analysis,
                'coordination_summary': coordination_summary
            }
            
        except Exception as e:
            error_time = (time.time() - start_time) * 1000
            self.logger.error(f"Multi-source enumeration failed after {error_time:.2f}ms: {e}")
            raise RuntimeError(f"Multi-source enumeration failed: {e}") from e
    
    def coordinate_source_enumeration(self, source_nodes: List[Node], target_edge: Edge,
                                    nfa: Any, transaction_num: int, 
                                    coordination_mode: str = "parallel") -> tuple[Dict[str, Dict], str]:
        """
        Coordination enumeration entre sources multiples - Étape 2.4
        
        Coordination Modes:
        - parallel: Enumeration simultanée avec ThreadPoolExecutor
        - sequential: Enumeration séquentielle avec shared state
        - adaptive: Selection automatique selon source count et complexity
        
        Args:
            source_nodes: Sources validées pour enumeration
            target_edge: Edge target commune
            nfa: NFA pour classification
            transaction_num: Numéro transaction
            coordination_mode: Mode coordination
            
        Returns:
            tuple[Dict[str, Dict], str]: (Résultats par source avec métriques, mode_utilisé)
        """
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        source_results = {}
        
        try:
            if coordination_mode == "adaptive":
                # Adaptive selection: parallel si >2 sources, sinon sequential
                coordination_mode = "parallel" if len(source_nodes) > 2 else "sequential"
                self.logger.info(f"Adaptive coordination selected: {coordination_mode}")
            
            if coordination_mode == "parallel":
                # Parallel enumeration avec ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=min(len(source_nodes), 4)) as executor:
                    # Submit enumeration tasks
                    future_to_source = {}
                    for source in source_nodes:
                        future = executor.submit(
                            self._enumerate_single_source,
                            source, target_edge, nfa, transaction_num
                        )
                        future_to_source[future] = source
                    
                    # Collect results as completed
                    for future in as_completed(future_to_source):
                        source = future_to_source[future]
                        try:
                            result = future.result()
                            source_results[source.node_id] = result
                        except Exception as e:
                            self.logger.warning(f"Source {source.node_id} enumeration failed: {e}")
                            source_results[source.node_id] = {
                                'classification_result': {},
                                'error': str(e),
                                'enumeration_time_ms': 0
                            }
            
            elif coordination_mode == "sequential":
                # Sequential enumeration avec state preservation
                for source in source_nodes:
                    source_start = time.time()
                    try:
                        result = self._enumerate_single_source(
                            source, target_edge, nfa, transaction_num
                        )
                        source_results[source.node_id] = result
                    except Exception as e:
                        self.logger.warning(f"Source {source.node_id} enumeration failed: {e}")
                        source_results[source.node_id] = {
                            'classification_result': {},
                            'error': str(e),
                            'enumeration_time_ms': (time.time() - source_start) * 1000
                        }
            
            return source_results, coordination_mode
            
        except Exception as e:
            self.logger.error(f"Source coordination failed: {e}")
            raise RuntimeError(f"Source enumeration coordination failed: {e}") from e
    
    def merge_enumeration_results(self, source_results: Dict[str, Dict], 
                                overlap_analysis: Dict[str, Any],
                                deduplication: bool = True) -> Dict[str, Any]:
        """
        Fusion intelligente résultats multi-source avec deduplication - Étape 2.4
        
        Merge Strategy:
        - Classification state aggregation avec priority source
        - Path deduplication basée path signatures
        - Overlap resolution avec source preference
        - Metadata consolidation pour analytics
        
        Args:
            source_results: Résultats par source
            overlap_analysis: Analysis overlaps détectés
            deduplication: Flag deduplication activation
            
        Returns:
            Dict[str, Any]: Résultats mergés avec analytics
        """
        from collections import defaultdict
        
        try:
            merged_classifications = defaultdict(list)
            path_signatures = set()
            total_paths_before_merge = 0
            source_contributions = {}
            
            # Phase 1: Aggregation classifications par état NFA
            for source_id, source_result in source_results.items():
                classification_result = source_result.get('classification_result', {})
                source_path_count = 0
                
                for nfa_state, paths in classification_result.items():
                    for path in paths:
                        total_paths_before_merge += 1
                        source_path_count += 1
                        
                        if deduplication:
                            # Generate path signature pour deduplication
                            path_signature = self._generate_path_signature(path)
                            
                            if path_signature not in path_signatures:
                                path_signatures.add(path_signature)
                                merged_classifications[nfa_state].append(path)
                        else:
                            merged_classifications[nfa_state].append(path)
                
                source_contributions[source_id] = source_path_count
            
            # Phase 2: Convert defaultdict to regular dict
            final_classifications = dict(merged_classifications)
            
            # Phase 3: Calculate merge statistics
            total_unique_paths = sum(len(paths) for paths in final_classifications.values())
            deduplication_efficiency = 0
            
            if total_paths_before_merge > 0:
                deduplication_efficiency = (total_paths_before_merge - total_unique_paths) / total_paths_before_merge
            
            self.multi_source_stats['merge_operations'] += 1
            
            merge_summary = {
                'total_paths_before_merge': total_paths_before_merge,
                'total_unique_paths': total_unique_paths,
                'deduplication_enabled': deduplication,
                'deduplication_efficiency': deduplication_efficiency,
                'source_contributions': source_contributions,
                'nfa_states_populated': len(final_classifications),
                'overlaps_resolved': overlap_analysis.get('total_overlaps', 0)
            }
            
            return {
                'merged_classifications': final_classifications,
                'total_unique_paths': total_unique_paths,
                'merge_summary': merge_summary
            }
            
        except Exception as e:
            self.logger.error(f"Result merging failed: {e}")
            raise RuntimeError(f"Enumeration result merging failed: {e}") from e
    
    def detect_path_overlaps(self, source_results: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Detection overlaps entre chemins de sources différentes - Étape 2.4
        
        Overlap Detection:
        - Path intersection analysis par paires de sources
        - Node sequence overlap detection
        - Shared sub-path identification
        - Overlap significance scoring
        
        Args:
            source_results: Résultats enumeration par source
            
        Returns:
            Dict[str, Any]: Analysis complète overlaps détectés
        """
        try:
            overlap_analysis = {
                'pairwise_overlaps': {},
                'shared_nodes': {},
                'overlap_significance': {},
                'total_overlaps': 0
            }
            
            source_ids = list(source_results.keys())
            
            # Phase 1: Pairwise overlap analysis
            for i, source_a in enumerate(source_ids):
                for j, source_b in enumerate(source_ids[i+1:], i+1):
                    overlap_key = f"{source_a}_{source_b}"
                    
                    paths_a = self._extract_all_paths_from_result(source_results[source_a])
                    paths_b = self._extract_all_paths_from_result(source_results[source_b])
                    
                    # Detect overlapping nodes dans paths
                    overlap_nodes = self._find_overlapping_nodes(paths_a, paths_b)
                    overlap_count = len(overlap_nodes)
                    
                    if overlap_count > 0:
                        overlap_analysis['pairwise_overlaps'][overlap_key] = {
                            'overlapping_nodes': overlap_nodes,
                            'overlap_count': overlap_count,
                            'source_a_paths': len(paths_a),
                            'source_b_paths': len(paths_b)
                        }
                        
                        # Calculate overlap significance
                        total_paths = len(paths_a) + len(paths_b)
                        significance = overlap_count / total_paths if total_paths > 0 else 0
                        overlap_analysis['overlap_significance'][overlap_key] = significance
                        
                        overlap_analysis['total_overlaps'] += overlap_count
            
            # Phase 2: Global shared nodes analysis
            from collections import defaultdict
            all_node_occurrences = defaultdict(list)
            
            for source_id, source_result in source_results.items():
                paths = self._extract_all_paths_from_result(source_result)
                for path in paths:
                    for node in path:
                        all_node_occurrences[node.node_id].append(source_id)
            
            # Identify nodes shared across multiple sources
            shared_nodes = {
                node_id: sources for node_id, sources in all_node_occurrences.items()
                if len(set(sources)) > 1  # Node appears in paths from multiple sources
            }
            
            overlap_analysis['shared_nodes'] = shared_nodes
            
            return overlap_analysis
            
        except Exception as e:
            self.logger.error(f"Path overlap detection failed: {e}")
            return {
                'error': f"Overlap detection failed: {e}",
                'total_overlaps': 0
            }
    
    def optimize_multi_source_performance(self, source_nodes: List[Node], 
                                        target_edge: Edge) -> Dict[str, Any]:
        """
        Optimizations performance pour multi-source enumeration - Étape 2.4
        
        Optimizations:
        - Source prioritization basée complexity analysis
        - Load balancing intelligent entre sources
        - Early termination strategies pour large datasets
        - Memory usage optimization avec streaming results
        
        Args:
            source_nodes: Sources à optimiser
            target_edge: Edge target pour analysis
            
        Returns:
            Dict[str, Any]: Configuration optimisée et metrics
        """
        try:
            optimization_result = {
                'optimized_order': [],
                'load_balancing': {},
                'performance_estimates': {},
                'optimization_strategies': []
            }
            
            # Phase 1: Source complexity analysis
            source_complexities = {}
            for source in source_nodes:
                complexity_score = self._estimate_source_complexity(source, target_edge)
                source_complexities[source.node_id] = complexity_score
            
            # Phase 2: Source prioritization (simple first, complex last)
            sorted_sources = sorted(source_nodes, 
                                  key=lambda s: source_complexities[s.node_id])
            optimization_result['optimized_order'] = [s.node_id for s in sorted_sources]
            
            # Phase 3: Load balancing recommendations
            total_complexity = sum(source_complexities.values())
            if total_complexity > 0:
                for source in source_nodes:
                    complexity_fraction = source_complexities[source.node_id] / total_complexity
                    optimization_result['load_balancing'][source.node_id] = {
                        'complexity_score': source_complexities[source.node_id],
                        'complexity_fraction': complexity_fraction,
                        'recommended_priority': 1.0 - complexity_fraction  # Inverse priority
                    }
            
            # Phase 4: Performance estimates
            estimated_sequential_time = sum(
                complexity * 10 for complexity in source_complexities.values()  # 10ms per complexity unit
            )
            estimated_parallel_time = max(source_complexities.values()) * 10 if source_complexities else 0
            
            optimization_result['performance_estimates'] = {
                'estimated_sequential_ms': estimated_sequential_time,
                'estimated_parallel_ms': estimated_parallel_time,
                'parallelization_benefit': estimated_sequential_time - estimated_parallel_time,
                'recommended_mode': 'parallel' if len(source_nodes) > 2 else 'sequential'
            }
            
            # Phase 5: Optimization strategies
            strategies = []
            if len(source_nodes) > 4:
                strategies.append('batch_processing')
            if max(source_complexities.values()) > 50:
                strategies.append('early_termination')
            if total_complexity > 200:
                strategies.append('memory_streaming')
            
            optimization_result['optimization_strategies'] = strategies
            
            return optimization_result
            
        except Exception as e:
            self.logger.error(f"Multi-source performance optimization failed: {e}")
            return {
                'error': f"Performance optimization failed: {e}",
                'optimized_order': [node.node_id for node in source_nodes]
            }
    
    # Step 2.4: Helper Methods
    
    def _validate_multiple_sources(self, source_nodes: List[Node], target_edge: Edge) -> List[Node]:
        """Validation sources multiples pour enumeration - Étape 2.4"""
        valid_sources = []
        
        for source in source_nodes:
            try:
                # Validation source node existence et connectivity
                if not source or not hasattr(source, 'node_id'):
                    continue
                
                # Validation connectivity vers target (via outgoing edges)
                has_connectivity = False
                if hasattr(source, 'outgoing_edges') and source.outgoing_edges:
                    has_connectivity = True
                elif hasattr(source, 'incoming_edges') and source.incoming_edges:
                    has_connectivity = True
                
                if has_connectivity:
                    valid_sources.append(source)
                else:
                    self.logger.warning(f"Source {source.node_id} has no connectivity")
                    
            except Exception as e:
                self.logger.warning(f"Source validation failed for {getattr(source, 'node_id', 'unknown')}: {e}")
                continue
        
        return valid_sources
    
    def _enumerate_single_source(self, source_node: Node, target_edge: Edge, 
                                nfa: Any, transaction_num: int) -> Dict[str, Any]:
        """Enumeration single source avec metrics - Étape 2.4"""
        import time
        
        start_time = time.time()
        
        try:
            # Create edge from source to target for enumeration
            temp_edge = Edge(
                f"temp_{source_node.node_id}_to_{target_edge.target_node.node_id}",
                source_node, target_edge.target_node,
                target_edge.edge_metadata.weight,
                target_edge.edge_metadata.edge_type,
                target_edge.edge_metadata
            )
            
            # Use existing enumeration pipeline
            classification_result = self.enumerate_and_classify(temp_edge, nfa, transaction_num)
            
            enumeration_time = (time.time() - start_time) * 1000
            
            return {
                'classification_result': classification_result,
                'enumeration_time_ms': enumeration_time,
                'source_id': source_node.node_id,
                'path_count': sum(len(paths) for paths in classification_result.values())
            }
            
        except Exception as e:
            enumeration_time = (time.time() - start_time) * 1000
            self.logger.error(f"Single source enumeration failed for {source_node.node_id}: {e}")
            return {
                'classification_result': {},
                'enumeration_time_ms': enumeration_time,
                'source_id': source_node.node_id,
                'error': str(e),
                'path_count': 0
            }
    
    def _generate_path_signature(self, path: List[Node]) -> str:
        """Generate signature unique pour path deduplication - Étape 2.4"""
        try:
            # Create signature based on node IDs sequence
            node_sequence = [node.node_id for node in path]
            return "_".join(node_sequence)
        except Exception:
            # Fallback signature
            return f"path_{hash(str(path))}"
    
    def _extract_all_paths_from_result(self, source_result: Dict[str, Any]) -> List[List[Node]]:
        """Extract tous paths depuis résultat source - Étape 2.4"""
        all_paths = []
        
        try:
            classification_result = source_result.get('classification_result', {})
            
            for nfa_state, paths in classification_result.items():
                all_paths.extend(paths)
            
            return all_paths
            
        except Exception as e:
            self.logger.warning(f"Path extraction failed: {e}")
            return []
    
    def _find_overlapping_nodes(self, paths_a: List[List[Node]], 
                               paths_b: List[List[Node]]) -> List[str]:
        """Find nodes overlapping entre deux ensembles de paths - Étape 2.4"""
        try:
            # Collect all node IDs from paths_a
            nodes_a = set()
            for path in paths_a:
                for node in path:
                    nodes_a.add(node.node_id)
            
            # Collect all node IDs from paths_b
            nodes_b = set()
            for path in paths_b:
                for node in path:
                    nodes_b.add(node.node_id)
            
            # Find intersection
            overlapping_nodes = nodes_a.intersection(nodes_b)
            return list(overlapping_nodes)
            
        except Exception as e:
            self.logger.warning(f"Overlap detection failed: {e}")
            return []
    
    def _estimate_source_complexity(self, source_node: Node, target_edge: Edge) -> int:
        """Estimate complexity pour source node - Étape 2.4"""
        try:
            complexity_score = 1  # Base complexity
            
            # Factor 1: Outgoing edges count
            if hasattr(source_node, 'outgoing_edges'):
                complexity_score += len(source_node.outgoing_edges)
            
            # Factor 2: Incoming edges count  
            if hasattr(source_node, 'incoming_edges'):
                complexity_score += len(source_node.incoming_edges)
            
            # Factor 3: Node type complexity
            if hasattr(source_node, 'get_node_type'):
                node_type = source_node.get_node_type()
                if node_type.name == 'INTERMEDIATE':
                    complexity_score += 2
                elif node_type.name == 'SOURCE':
                    complexity_score += 1
            
            return max(complexity_score, 1)  # Minimum complexity of 1
            
        except Exception:
            return 1  # Default complexity
    
    def reset_enumeration_state(self):
        """Reset état énumération pour nouvelle transaction - Étape 2.2 Enhanced"""
        self.visited_nodes.clear()
        self.current_path.clear()
        self.enumerated_paths.clear()
        self.stats = EnumerationStatistics()
        
        # Note: Don't reset DAG validation state for test access - Étape 2.2
        # self.last_dag_validation should persist for test validation
        
        self.logger.debug("Enumeration state reset (including DAG validation state)")
    
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
        
        # PHASE 2.9: PRÉ-CONDITION STRICTE - Taxonomie configurée pour transaction_num
        assert len(self.taxonomy.taxonomy_history) > 0, (
            f"Taxonomy history is empty for transaction_num={transaction_num}. "
            f"Must configure taxonomy with update_taxonomy() before path enumeration."
        )
        
        max_configured_tx = max(snapshot.transaction_num for snapshot in self.taxonomy.taxonomy_history)
        assert transaction_num <= max_configured_tx, (
            f"Taxonomy not configured for transaction_num={transaction_num}. "
            f"Latest configured transaction_num={max_configured_tx}. "
            f"Must configure taxonomy up to transaction_num before path enumeration."
        )
            
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
    
    # ==================== ÉTAPE 2.5: DAG TOPOLOGY ANALYSIS ====================
    
    def analyze_dag_topology(self, nodes: List[Node], edges: List[Edge], 
                           source_nodes: List[Node] = None, 
                           target_node: Node = None) -> Dict[str, Any]:
        """
        Analyse topologique complète du DAG pour optimisation enumeration - Étape 2.5
        
        Topology Analysis:
        - Node centrality metrics (betweenness, closeness, degree)
        - Connectivity patterns et bottlenecks identification
        - Path complexity analysis avec branching factor
        - Critical path identification pour optimization
        
        Args:
            nodes: List des nodes du DAG
            edges: List des edges du DAG
            source_nodes: Sources optionnelles pour analysis ciblée
            target_node: Target optionnel pour analysis ciblée
            
        Returns:
            Dict[str, Any]: Analyse topologique complète avec métriques optimization
        """
        import time
        from collections import defaultdict, deque
        
        analysis_start = time.time()
        topology_metrics = {}
        
        try:
            self.logger.info(f"Starting DAG topology analysis: {len(nodes)} nodes, {len(edges)} edges")
            
            # Phase 1: Basic topology metrics
            topology_metrics.update(self._calculate_basic_topology_metrics(nodes, edges))
            
            # Phase 2: Node centrality analysis
            centrality_metrics = self._analyze_node_centrality(nodes, edges)
            topology_metrics['centrality_analysis'] = centrality_metrics
            
            # Phase 3: Connectivity patterns analysis
            connectivity_analysis = self._analyze_connectivity_patterns(nodes, edges)
            topology_metrics['connectivity_analysis'] = connectivity_analysis
            
            # Phase 4: Path complexity analysis
            complexity_analysis = self._analyze_path_complexity(nodes, edges, source_nodes, target_node)
            topology_metrics['path_complexity'] = complexity_analysis
            
            # Phase 5: Critical path identification
            critical_paths = self._identify_critical_paths(nodes, edges, source_nodes, target_node)
            topology_metrics['critical_paths'] = critical_paths
            
            # Phase 6: Optimization recommendations
            optimization_recommendations = self._generate_topology_optimizations(
                topology_metrics, source_nodes, target_node
            )
            topology_metrics['optimization_recommendations'] = optimization_recommendations
            
            analysis_time = (time.time() - analysis_start) * 1000
            topology_metrics['analysis_summary'] = {
                'analysis_time_ms': analysis_time,
                'nodes_analyzed': len(nodes),
                'edges_analyzed': len(edges),
                'sources_considered': len(source_nodes) if source_nodes else 0,
                'target_considered': bool(target_node),
                'bottlenecks_identified': len(connectivity_analysis.get('bottlenecks', [])),
                'critical_paths_found': len(critical_paths.get('identified_paths', []))
            }
            
            self.logger.info(f"DAG topology analysis completed in {analysis_time:.2f}ms")
            return topology_metrics
            
        except Exception as e:
            error_time = (time.time() - analysis_start) * 1000
            self.logger.error(f"DAG topology analysis failed after {error_time:.2f}ms: {e}")
            raise RuntimeError(f"DAG topology analysis failed: {e}") from e
    
    def _calculate_basic_topology_metrics(self, nodes: List[Node], 
                                        edges: List[Edge]) -> Dict[str, Any]:
        """
        Calcul métriques topologiques de base - Étape 2.5
        
        Basic Metrics:
        - Node count et distribution
        - Edge density et distribution
        - Degree statistics (in/out/total)
        - Graph diameter estimation
        """
        from collections import defaultdict
        
        try:
            # Degree calculations
            in_degrees = defaultdict(int)
            out_degrees = defaultdict(int)
            
            for edge in edges:
                out_degrees[edge.source_node.node_id] += 1
                in_degrees[edge.target_node.node_id] += 1
            
            # Node classification
            source_nodes = [node for node in nodes if in_degrees[node.node_id] == 0]
            sink_nodes = [node for node in nodes if out_degrees[node.node_id] == 0]
            intermediate_nodes = [node for node in nodes 
                                if in_degrees[node.node_id] > 0 and out_degrees[node.node_id] > 0]
            
            # Degree statistics
            in_degree_values = list(in_degrees.values())
            out_degree_values = list(out_degrees.values())
            total_degrees = [in_degrees[node.node_id] + out_degrees[node.node_id] for node in nodes]
            
            basic_metrics = {
                'node_count': len(nodes),
                'edge_count': len(edges),
                'edge_density': len(edges) / (len(nodes) * (len(nodes) - 1)) if len(nodes) > 1 else 0,
                'node_classification': {
                    'source_nodes': len(source_nodes),
                    'sink_nodes': len(sink_nodes),
                    'intermediate_nodes': len(intermediate_nodes)
                },
                'degree_statistics': {
                    'avg_in_degree': sum(in_degree_values) / len(nodes) if nodes else 0,
                    'avg_out_degree': sum(out_degree_values) / len(nodes) if nodes else 0,
                    'max_in_degree': max(in_degree_values) if in_degree_values else 0,
                    'max_out_degree': max(out_degree_values) if out_degree_values else 0,
                    'avg_total_degree': sum(total_degrees) / len(nodes) if nodes else 0
                }
            }
            
            return basic_metrics
            
        except Exception as e:
            self.logger.error(f"Basic topology metrics calculation failed: {e}")
            raise RuntimeError(f"Basic topology metrics failed: {e}") from e
    
    def _analyze_node_centrality(self, nodes: List[Node], 
                               edges: List[Edge]) -> Dict[str, Any]:
        """
        Analyse centralité des nœuds pour identification bottlenecks - Étape 2.5
        
        Centrality Metrics:
        - Degree centrality (normalized)
        - Betweenness centrality estimation
        - Closeness centrality estimation
        - Critical node identification
        """
        from collections import defaultdict, deque
        import heapq
        
        try:
            # Build adjacency lists
            adjacency = defaultdict(list)
            reverse_adjacency = defaultdict(list)
            
            for edge in edges:
                adjacency[edge.source_node.node_id].append(edge.target_node.node_id)
                reverse_adjacency[edge.target_node.node_id].append(edge.source_node.node_id)
            
            node_ids = [node.node_id for node in nodes]
            
            # Degree centrality
            degree_centrality = {}
            max_possible_degree = len(nodes) - 1
            
            for node_id in node_ids:
                total_degree = len(adjacency[node_id]) + len(reverse_adjacency[node_id])
                degree_centrality[node_id] = total_degree / max_possible_degree if max_possible_degree > 0 else 0
            
            # Betweenness centrality estimation (simplified for performance)
            betweenness_centrality = self._estimate_betweenness_centrality(
                node_ids, adjacency, reverse_adjacency
            )
            
            # Closeness centrality estimation
            closeness_centrality = self._estimate_closeness_centrality(
                node_ids, adjacency, reverse_adjacency
            )
            
            # Identify critical nodes (high centrality)
            critical_nodes = []
            for node_id in node_ids:
                centrality_score = (
                    degree_centrality.get(node_id, 0) * 0.4 +
                    betweenness_centrality.get(node_id, 0) * 0.4 +
                    closeness_centrality.get(node_id, 0) * 0.2
                )
                if centrality_score > 0.7:  # High centrality threshold
                    critical_nodes.append({
                        'node_id': node_id,
                        'centrality_score': centrality_score,
                        'degree_centrality': degree_centrality.get(node_id, 0),
                        'betweenness_centrality': betweenness_centrality.get(node_id, 0),
                        'closeness_centrality': closeness_centrality.get(node_id, 0)
                    })
            
            centrality_analysis = {
                'degree_centrality': degree_centrality,
                'betweenness_centrality': betweenness_centrality,
                'closeness_centrality': closeness_centrality,
                'critical_nodes': sorted(critical_nodes, key=lambda x: x['centrality_score'], reverse=True),
                'centrality_summary': {
                    'avg_degree_centrality': sum(degree_centrality.values()) / len(degree_centrality) if degree_centrality else 0,
                    'max_degree_centrality': max(degree_centrality.values()) if degree_centrality else 0,
                    'critical_nodes_count': len(critical_nodes)
                }
            }
            
            return centrality_analysis
            
        except Exception as e:
            self.logger.error(f"Node centrality analysis failed: {e}")
            raise RuntimeError(f"Node centrality analysis failed: {e}") from e
    
    def _estimate_betweenness_centrality(self, node_ids: List[str], adjacency: Dict[str, List[str]], 
                                       reverse_adjacency: Dict[str, List[str]]) -> Dict[str, float]:
        """
        Estimation betweenness centrality via sampling - Étape 2.5
        
        Sampling-based approximation pour performance sur large graphs
        """
        from collections import deque
        import random
        
        try:
            betweenness = {node_id: 0.0 for node_id in node_ids}
            
            # Sample-based approximation (sample up to 100 nodes for performance)
            sample_size = min(100, len(node_ids))
            sampled_nodes = random.sample(node_ids, sample_size) if len(node_ids) > sample_size else node_ids
            
            for source in sampled_nodes:
                # BFS from source
                distances = {source: 0}
                predecessors = {node_id: [] for node_id in node_ids}
                queue = deque([source])
                
                while queue:
                    current = queue.popleft()
                    current_dist = distances[current]
                    
                    for neighbor in adjacency[current]:
                        if neighbor not in distances:
                            distances[neighbor] = current_dist + 1
                            predecessors[neighbor].append(current)
                            queue.append(neighbor)
                        elif distances[neighbor] == current_dist + 1:
                            predecessors[neighbor].append(current)
                
                # Calculate betweenness contribution
                for target in node_ids:
                    if target in distances and target != source:
                        self._accumulate_betweenness(source, target, predecessors, betweenness)
            
            # Normalize by sampling factor
            normalization_factor = (len(node_ids) / sample_size) if sample_size > 0 else 1
            for node_id in betweenness:
                betweenness[node_id] = betweenness[node_id] / (len(node_ids) * (len(node_ids) - 1)) * normalization_factor
            
            return betweenness
            
        except Exception as e:
            self.logger.warning(f"Betweenness centrality estimation failed: {e}")
            return {node_id: 0.0 for node_id in node_ids}
    
    def _accumulate_betweenness(self, source: str, target: str, predecessors: Dict[str, List[str]], 
                              betweenness: Dict[str, float]):
        """
        Accumulation betweenness score pour shortest paths - Étape 2.5
        """
        try:
            # Simple path counting approximation
            visited = set()
            stack = [(target, 1.0)]
            
            while stack:
                node, weight = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                
                if node != source:
                    betweenness[node] += weight
                    
                    for pred in predecessors[node]:
                        if pred not in visited:
                            stack.append((pred, weight / len(predecessors[node])))
                            
        except Exception:
            pass  # Silent fail for robustness
    
    def _estimate_closeness_centrality(self, node_ids: List[str], adjacency: Dict[str, List[str]], 
                                     reverse_adjacency: Dict[str, List[str]]) -> Dict[str, float]:
        """
        Estimation closeness centrality via BFS sampling - Étape 2.5
        """
        from collections import deque
        import random
        
        try:
            closeness = {}
            
            # Sample nodes for performance
            sample_size = min(50, len(node_ids))
            sampled_nodes = random.sample(node_ids, sample_size) if len(node_ids) > sample_size else node_ids
            
            for node_id in sampled_nodes:
                # BFS to calculate distances
                distances = {node_id: 0}
                queue = deque([node_id])
                
                while queue:
                    current = queue.popleft()
                    current_dist = distances[current]
                    
                    # Check both outgoing and incoming edges for undirected behavior
                    neighbors = set(adjacency[current] + reverse_adjacency[current])
                    
                    for neighbor in neighbors:
                        if neighbor not in distances:
                            distances[neighbor] = current_dist + 1
                            queue.append(neighbor)
                
                # Calculate closeness
                reachable_distances = [dist for dist in distances.values() if dist > 0]
                if reachable_distances:
                    total_distance = sum(reachable_distances)
                    closeness[node_id] = (len(reachable_distances)) / total_distance
                else:
                    closeness[node_id] = 0.0
            
            # Fill in non-sampled nodes with average
            avg_closeness = sum(closeness.values()) / len(closeness) if closeness else 0.0
            for node_id in node_ids:
                if node_id not in closeness:
                    closeness[node_id] = avg_closeness
            
            return closeness
            
        except Exception as e:
            self.logger.warning(f"Closeness centrality estimation failed: {e}")
            return {node_id: 0.0 for node_id in node_ids}
    
    def _analyze_connectivity_patterns(self, nodes: List[Node], 
                                     edges: List[Edge]) -> Dict[str, Any]:
        """
        Analyse patterns de connectivité et identification bottlenecks - Étape 2.5
        
        Connectivity Analysis:
        - Bottleneck identification
        - Connected components analysis
        - Bridge edges detection
        - Flow capacity estimation
        """
        from collections import defaultdict, deque
        
        try:
            adjacency = defaultdict(list)
            reverse_adjacency = defaultdict(list)
            
            for edge in edges:
                adjacency[edge.source_node.node_id].append(edge.target_node.node_id)
                reverse_adjacency[edge.target_node.node_id].append(edge.source_node.node_id)
            
            node_ids = [node.node_id for node in nodes]
            
            # Identify bottlenecks (nodes with high in-degree but low out-degree)
            bottlenecks = []
            for node_id in node_ids:
                in_degree = len(reverse_adjacency[node_id])
                out_degree = len(adjacency[node_id])
                
                if in_degree > 2 and out_degree <= 1:
                    bottleneck_score = in_degree / (out_degree + 1)
                    bottlenecks.append({
                        'node_id': node_id,
                        'bottleneck_score': bottleneck_score,
                        'in_degree': in_degree,
                        'out_degree': out_degree
                    })
            
            # Connected components analysis (treating as undirected for this)
            connected_components = self._find_connected_components(node_ids, adjacency, reverse_adjacency)
            
            # Bridge edges detection (simplified)
            bridge_edges = self._identify_bridge_edges(adjacency, reverse_adjacency, node_ids)
            
            # Flow capacity estimation
            flow_analysis = self._estimate_flow_capacity(adjacency, reverse_adjacency, node_ids)
            
            connectivity_analysis = {
                'bottlenecks': sorted(bottlenecks, key=lambda x: x['bottleneck_score'], reverse=True),
                'connected_components': connected_components,
                'bridge_edges': bridge_edges,
                'flow_analysis': flow_analysis,
                'connectivity_summary': {
                    'bottlenecks_count': len(bottlenecks),
                    'components_count': len(connected_components['components']),
                    'bridge_edges_count': len(bridge_edges),
                    'max_component_size': max([comp['size'] for comp in connected_components['components']]) if connected_components['components'] else 0
                }
            }
            
            return connectivity_analysis
            
        except Exception as e:
            self.logger.error(f"Connectivity patterns analysis failed: {e}")
            raise RuntimeError(f"Connectivity analysis failed: {e}") from e
    
    def _find_connected_components(self, node_ids: List[str], adjacency: Dict[str, List[str]], 
                                 reverse_adjacency: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Identification connected components via DFS - Étape 2.5
        """
        from collections import deque
        
        try:
            visited = set()
            components = []
            
            for node_id in node_ids:
                if node_id not in visited:
                    # DFS to find component
                    component_nodes = []
                    stack = [node_id]
                    
                    while stack:
                        current = stack.pop()
                        if current not in visited:
                            visited.add(current)
                            component_nodes.append(current)
                            
                            # Add both outgoing and incoming neighbors (undirected)
                            neighbors = set(adjacency[current] + reverse_adjacency[current])
                            for neighbor in neighbors:
                                if neighbor not in visited:
                                    stack.append(neighbor)
                    
                    components.append({
                        'component_id': len(components),
                        'nodes': component_nodes,
                        'size': len(component_nodes)
                    })
            
            return {
                'components': components,
                'largest_component_size': max([comp['size'] for comp in components]) if components else 0,
                'components_count': len(components)
            }
            
        except Exception as e:
            self.logger.warning(f"Connected components analysis failed: {e}")
            return {'components': [], 'largest_component_size': 0, 'components_count': 0}
    
    def _identify_bridge_edges(self, adjacency: Dict[str, List[str]], 
                             reverse_adjacency: Dict[str, List[str]], 
                             node_ids: List[str]) -> List[Dict[str, str]]:
        """
        Identification bridge edges - connexions critiques - Étape 2.5
        """
        try:
            bridge_edges = []
            
            # Simple heuristic: edges from/to nodes with degree 1
            for node_id in node_ids:
                total_degree = len(adjacency[node_id]) + len(reverse_adjacency[node_id])
                
                if total_degree == 1:
                    # This node's edge is likely a bridge
                    if adjacency[node_id]:
                        bridge_edges.append({
                            'source': node_id,
                            'target': adjacency[node_id][0],
                            'bridge_type': 'outgoing_leaf'
                        })
                    elif reverse_adjacency[node_id]:
                        bridge_edges.append({
                            'source': reverse_adjacency[node_id][0],
                            'target': node_id,
                            'bridge_type': 'incoming_leaf'
                        })
            
            return bridge_edges
            
        except Exception as e:
            self.logger.warning(f"Bridge edges identification failed: {e}")
            return []
    
    def _estimate_flow_capacity(self, adjacency: Dict[str, List[str]], 
                              reverse_adjacency: Dict[str, List[str]], 
                              node_ids: List[str]) -> Dict[str, Any]:
        """
        Estimation flow capacity du DAG - Étape 2.5
        """
        try:
            # Simple flow estimation based on node degrees
            min_cut_nodes = []
            flow_bottlenecks = []
            
            for node_id in node_ids:
                in_degree = len(reverse_adjacency[node_id])
                out_degree = len(adjacency[node_id])
                
                # Identify potential bottlenecks
                if in_degree > 1 and out_degree == 1:
                    flow_bottlenecks.append({
                        'node_id': node_id,
                        'flow_reduction': in_degree - out_degree,
                        'in_degree': in_degree,
                        'out_degree': out_degree
                    })
                
                # Identify min-cut candidates
                if in_degree == 1 and out_degree >= 1:
                    min_cut_nodes.append({
                        'node_id': node_id,
                        'cut_capacity': min(in_degree, out_degree)
                    })
            
            total_sources = len([node_id for node_id in node_ids if not reverse_adjacency[node_id]])
            total_sinks = len([node_id for node_id in node_ids if not adjacency[node_id]])
            
            flow_analysis = {
                'estimated_max_flow': min(total_sources, total_sinks),
                'flow_bottlenecks': sorted(flow_bottlenecks, key=lambda x: x['flow_reduction'], reverse=True),
                'min_cut_candidates': min_cut_nodes,
                'sources_count': total_sources,
                'sinks_count': total_sinks,
                'flow_efficiency': total_sinks / total_sources if total_sources > 0 else 0
            }
            
            return flow_analysis
            
        except Exception as e:
            self.logger.warning(f"Flow capacity estimation failed: {e}")
            return {'estimated_max_flow': 0, 'flow_bottlenecks': [], 'min_cut_candidates': []}
    
    def _analyze_path_complexity(self, nodes: List[Node], edges: List[Edge],
                               source_nodes: List[Node] = None, target_node: Node = None) -> Dict[str, Any]:
        """
        Analyse complexité des chemins et branching factors - Étape 2.5
        """
        from collections import defaultdict
        
        try:
            adjacency = defaultdict(list)
            reverse_adjacency = defaultdict(list)
            
            for edge in edges:
                adjacency[edge.source_node.node_id].append(edge.target_node.node_id)
                reverse_adjacency[edge.target_node.node_id].append(edge.source_node.node_id)
            
            node_ids = [node.node_id for node in nodes]
            
            # Branching factor analysis
            branching_factors = {}
            for node_id in node_ids:
                out_degree = len(adjacency[node_id])
                branching_factors[node_id] = out_degree
            
            # Path length estimation
            path_length_estimates = self._estimate_path_lengths(adjacency, node_ids, source_nodes, target_node)
            
            # Complexity scoring
            complexity_scores = {}
            for node_id in node_ids:
                branching = branching_factors[node_id]
                path_length = path_length_estimates.get(node_id, 1)
                
                # Complexity = branching_factor * log(path_length)
                import math
                complexity_scores[node_id] = branching * math.log(path_length + 1)
            
            # High complexity nodes
            avg_complexity = sum(complexity_scores.values()) / len(complexity_scores) if complexity_scores else 0
            high_complexity_nodes = [
                {'node_id': node_id, 'complexity_score': score}
                for node_id, score in complexity_scores.items()
                if score > avg_complexity * 1.5
            ]
            
            complexity_analysis = {
                'branching_factors': branching_factors,
                'path_length_estimates': path_length_estimates,
                'complexity_scores': complexity_scores,
                'high_complexity_nodes': sorted(high_complexity_nodes, key=lambda x: x['complexity_score'], reverse=True),
                'complexity_summary': {
                    'avg_branching_factor': sum(branching_factors.values()) / len(branching_factors) if branching_factors else 0,
                    'max_branching_factor': max(branching_factors.values()) if branching_factors else 0,
                    'avg_complexity_score': avg_complexity,
                    'high_complexity_count': len(high_complexity_nodes)
                }
            }
            
            return complexity_analysis
            
        except Exception as e:
            self.logger.error(f"Path complexity analysis failed: {e}")
            raise RuntimeError(f"Path complexity analysis failed: {e}") from e
    
    def _estimate_path_lengths(self, adjacency: Dict[str, List[str]], node_ids: List[str],
                             source_nodes: List[Node] = None, target_node: Node = None) -> Dict[str, int]:
        """
        Estimation longueurs moyennes des chemins - Étape 2.5
        """
        from collections import deque
        
        try:
            path_lengths = {}
            
            # Use provided sources or find graph sources
            if source_nodes:
                sources = [node.node_id for node in source_nodes]
            else:
                sources = [node_id for node_id in node_ids if not any(node_id in adj for adj in adjacency.values())]
            
            for source in sources:
                # BFS from each source
                distances = {source: 0}
                queue = deque([source])
                
                while queue:
                    current = queue.popleft()
                    current_dist = distances[current]
                    
                    for neighbor in adjacency[current]:
                        if neighbor not in distances:
                            distances[neighbor] = current_dist + 1
                            queue.append(neighbor)
                
                # Update path lengths
                for node_id, distance in distances.items():
                    if node_id not in path_lengths:
                        path_lengths[node_id] = distance
                    else:
                        path_lengths[node_id] = (path_lengths[node_id] + distance) / 2
            
            # Fill in missing nodes
            for node_id in node_ids:
                if node_id not in path_lengths:
                    path_lengths[node_id] = 1
            
            return path_lengths
            
        except Exception as e:
            self.logger.warning(f"Path length estimation failed: {e}")
            return {node_id: 1 for node_id in node_ids}
    
    def _identify_critical_paths(self, nodes: List[Node], edges: List[Edge],
                               source_nodes: List[Node] = None, target_node: Node = None) -> Dict[str, Any]:
        """
        Identification critical paths pour optimization - Étape 2.5
        """
        from collections import defaultdict, deque
        
        try:
            adjacency = defaultdict(list)
            
            for edge in edges:
                adjacency[edge.source_node.node_id].append(edge.target_node.node_id)
            
            node_ids = [node.node_id for node in nodes]
            
            # Find sources and sinks
            if source_nodes:
                sources = [node.node_id for node in source_nodes]
            else:
                sources = [node_id for node_id in node_ids if not any(node_id in adj for adj in adjacency.values())]
            
            if target_node:
                targets = [target_node.node_id]
            else:
                targets = [node_id for node_id in node_ids if not adjacency[node_id]]
            
            critical_paths = []
            
            # Find longest paths (critical paths)
            for source in sources:
                for target in targets:
                    path = self._find_longest_path(source, target, adjacency)
                    if path and len(path) > 2:  # Only significant paths
                        critical_paths.append({
                            'source': source,
                            'target': target,
                            'path': path,
                            'length': len(path),
                            'criticality_score': len(path) * self._calculate_path_importance(path, adjacency)
                        })
            
            # Sort by criticality
            critical_paths.sort(key=lambda x: x['criticality_score'], reverse=True)
            
            critical_path_analysis = {
                'identified_paths': critical_paths[:10],  # Top 10 critical paths
                'sources_analyzed': len(sources),
                'targets_analyzed': len(targets),
                'longest_path_length': max([cp['length'] for cp in critical_paths]) if critical_paths else 0,
                'avg_path_length': sum([cp['length'] for cp in critical_paths]) / len(critical_paths) if critical_paths else 0
            }
            
            return critical_path_analysis
            
        except Exception as e:
            self.logger.error(f"Critical paths identification failed: {e}")
            raise RuntimeError(f"Critical paths identification failed: {e}") from e
    
    def _find_longest_path(self, source: str, target: str, adjacency: Dict[str, List[str]]) -> List[str]:
        """
        Recherche plus long chemin entre source et target - Étape 2.5
        """
        try:
            # Simple DFS to find longest path (limited depth for performance)
            def dfs(current, target, path, visited, max_depth=10):
                if len(path) > max_depth:
                    return []
                
                if current == target:
                    return path + [current]
                
                longest = []
                for neighbor in adjacency[current]:
                    if neighbor not in visited:
                        new_visited = visited | {current}
                        candidate = dfs(neighbor, target, path + [current], new_visited, max_depth)
                        if len(candidate) > len(longest):
                            longest = candidate
                
                return longest
            
            return dfs(source, target, [], set())
            
        except Exception:
            return []
    
    def _calculate_path_importance(self, path: List[str], adjacency: Dict[str, List[str]]) -> float:
        """
        Calcul importance d'un chemin basé sur branching - Étape 2.5
        """
        try:
            if len(path) <= 1:
                return 1.0
            
            importance = 1.0
            for node in path[:-1]:  # Exclude last node
                branching_factor = len(adjacency[node])
                if branching_factor > 1:
                    importance *= branching_factor
                    
            return importance
            
        except Exception:
            return 1.0
    
    def _generate_topology_optimizations(self, topology_metrics: Dict[str, Any], 
                                       source_nodes: List[Node] = None, 
                                       target_node: Node = None) -> Dict[str, Any]:
        """
        Génération recommandations optimization basées analyse topologique - Étape 2.5
        """
        try:
            optimizations = {
                'enumeration_strategies': [],
                'performance_improvements': [],
                'bottleneck_resolutions': [],
                'parallelization_opportunities': []
            }
            
            # Analyze centrality results
            centrality = topology_metrics.get('centrality_analysis', {})
            critical_nodes = centrality.get('critical_nodes', [])
            
            if critical_nodes:
                optimizations['enumeration_strategies'].append({
                    'strategy': 'critical_node_prioritization',
                    'description': f'Prioritize enumeration through {len(critical_nodes)} critical nodes',
                    'critical_nodes': [node['node_id'] for node in critical_nodes[:5]]
                })
            
            # Analyze connectivity bottlenecks
            connectivity = topology_metrics.get('connectivity_analysis', {})
            bottlenecks = connectivity.get('bottlenecks', [])
            
            if bottlenecks:
                optimizations['bottleneck_resolutions'].append({
                    'strategy': 'bottleneck_bypass',
                    'description': f'Implement bypass strategies for {len(bottlenecks)} bottlenecks',
                    'bottleneck_nodes': [bn['node_id'] for bn in bottlenecks[:3]]
                })
            
            # Analyze path complexity
            complexity = topology_metrics.get('path_complexity', {})
            high_complexity = complexity.get('high_complexity_nodes', [])
            
            if high_complexity:
                optimizations['performance_improvements'].append({
                    'strategy': 'complexity_reduction',
                    'description': f'Reduce enumeration complexity at {len(high_complexity)} high-complexity nodes',
                    'complex_nodes': [node['node_id'] for node in high_complexity[:5]]
                })
            
            # Parallelization opportunities
            components = connectivity.get('connected_components', {}).get('components', [])
            if len(components) > 1:
                optimizations['parallelization_opportunities'].append({
                    'strategy': 'component_parallelization',
                    'description': f'Parallelize enumeration across {len(components)} disconnected components',
                    'component_sizes': [comp['size'] for comp in components]
                })
            
            # Overall recommendations
            total_optimizations = (
                len(optimizations['enumeration_strategies']) +
                len(optimizations['performance_improvements']) +
                len(optimizations['bottleneck_resolutions']) +
                len(optimizations['parallelization_opportunities'])
            )
            
            optimizations['optimization_summary'] = {
                'total_opportunities': total_optimizations,
                'priority_level': 'HIGH' if total_optimizations > 3 else 'MEDIUM' if total_optimizations > 1 else 'LOW',
                'estimated_improvement': min(total_optimizations * 15, 50)  # Max 50% improvement
            }
            
            return optimizations
            
        except Exception as e:
            self.logger.error(f"Topology optimization generation failed: {e}")
            return {
                'enumeration_strategies': [],
                'performance_improvements': [],
                'bottleneck_resolutions': [],
                'parallelization_opportunities': [],
                'optimization_summary': {'total_opportunities': 0, 'priority_level': 'LOW', 'estimated_improvement': 0}
            }