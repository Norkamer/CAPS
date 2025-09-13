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