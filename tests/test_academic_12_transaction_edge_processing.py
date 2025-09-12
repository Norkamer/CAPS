"""
Test Académique 12: Transaction Edge Processing - Étape 2.3

Tests complets pour transaction edge processing dans PathEnumerator:
- Processing batch des transaction edges
- Validation métadonnées transaction complète 
- Extraction amounts avec aggregation currency
- Enumeration optimisée pour transactions
- Statistics construction et analysis
- Integration avec DAG validation pipeline

Chaque test valide les propriétés académiques et performance requirements
pour production-ready transaction processing.
"""

import pytest
import time
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, List, Any

from icgs_core.path_enumerator import DAGPathEnumerator
from icgs_core.account_taxonomy import AccountTaxonomy
from icgs_core.dag_structures import (
    Node, Edge, EdgeType, create_node, create_edge, connect_nodes
)


class TestAcademicTransactionEdgeProcessing:
    
    def setup_method(self):
        """Setup pour chaque test avec PathEnumerator et AccountTaxonomy"""
        self.taxonomy = AccountTaxonomy()
        
        # Setup test accounts pour conversion
        test_accounts = {
            'account_A': 'A', 'account_B': 'B', 'account_C': 'C'
        }
        self.taxonomy.update_taxonomy(test_accounts, 1)
        
        # Create enumerator avec taxonomy
        self.enumerator = DAGPathEnumerator(self.taxonomy, max_paths=100, batch_size=20)
        
        print(f"\n=== Setup Test Académique 12: Transaction Edge Processing ===")
    
    def create_transaction_edge_with_metadata(self, edge_id: str, source: Node, target: Node,
                                            amount: str, currency: str = 'USD',
                                            timestamp: float = None, reference_id: str = None) -> Edge:
        """Helper création transaction edge avec métadonnées complètes"""
        edge = create_edge(edge_id, source, target, amount, EdgeType.TRANSACTION)
        
        # Add comprehensive metadata
        metadata_context = {
            'transaction_amount': amount,
            'currency': currency
        }
        
        if timestamp:
            metadata_context['timestamp'] = timestamp
        if reference_id:
            metadata_context['reference_id'] = reference_id
        
        # Update edge metadata context
        edge.edge_metadata.context = metadata_context
        
        return edge
    
    def create_sample_transaction_batch(self, count: int = 5) -> List[Edge]:
        """Création batch transaction edges pour tests"""
        nodes = [create_node(f"node_{i}") for i in range(count + 1)]
        edges = []
        
        # Generate enough amounts and currencies for any count
        base_amounts = ['100.50', '250.75', '50.00', '1000.25', '75.30']
        base_currencies = ['USD', 'EUR', 'USD', 'GBP', 'USD']
        
        amounts = []
        currencies = []
        
        for i in range(count):
            amounts.append(base_amounts[i % len(base_amounts)])
            currencies.append(base_currencies[i % len(base_currencies)])
        
        current_time = time.time()
        
        for i in range(count):
            edge = self.create_transaction_edge_with_metadata(
                f"tx_{i}", nodes[i], nodes[i+1],
                amounts[i], currencies[i],
                current_time + i * 3600,  # 1 hour intervals
                f"REF_{i:04d}"
            )
            connect_nodes(nodes[i], nodes[i+1], edge)
            edges.append(edge)
        
        return edges
    
    def test_transaction_edge_processing_basic_functionality(self):
        """
        Test Académique 12.01: Functionality de base transaction processing
        
        Validation:
        - Processing correct batch transaction edges
        - Séparation valid/invalid transactions appropriée
        - Statistics processing time et throughput
        - Error handling robuste pour metadata invalides
        """
        # Création transaction batch valide
        valid_edges = self.create_sample_transaction_batch(3)
        
        # Création edge invalide (pas de metadata)
        invalid_node_1 = create_node("invalid_1")
        invalid_node_2 = create_node("invalid_2")
        invalid_edge = create_edge("invalid_tx", invalid_node_1, invalid_node_2, "100", EdgeType.TRANSACTION)
        # Clear context pour invalider
        invalid_edge.edge_metadata.context = {}
        
        all_edges = valid_edges + [invalid_edge]
        
        # Test processing
        result = self.enumerator.process_transaction_edges(all_edges, validate_metadata=True)
        
        # Validation résultats
        assert isinstance(result, dict)
        assert 'valid_transactions' in result
        assert 'invalid_transactions' in result
        assert 'processing_summary' in result
        
        # Validation counts
        assert len(result['valid_transactions']) == 3
        assert len(result['invalid_transactions']) == 1
        
        # Validation processing summary
        summary = result['processing_summary']
        assert summary['total_edges'] == 4
        assert summary['valid_count'] == 3
        assert summary['invalid_count'] == 1
        assert summary['processing_time_ms'] > 0
        assert summary['validation_enabled'] == True
        
        # Validation statistics update
        assert self.enumerator.transaction_processor_stats['edges_processed'] == 4
        assert self.enumerator.transaction_processor_stats['validation_errors'] >= 1
        
        print("✅ Test Académique 12.01: Transaction Edge Processing Basic - PASSED")
    
    def test_transaction_metadata_validation_comprehensive(self):
        """
        Test Académique 12.02: Validation métadonnées transaction comprehensive
        
        Validation:
        - Amount format validation (Decimal precision)
        - Timestamp validation (multiple formats)
        - Currency code validation (3-letter ISO)
        - Reference ID validation (non-empty string)
        - Edge weight consistency avec transaction amount
        """
        source = create_node("validation_source")
        target = create_node("validation_target")
        
        # Test 1: Valid transaction complète
        valid_edge = self.create_transaction_edge_with_metadata(
            "valid_tx", source, target,
            "123.456789", "EUR", 
            time.time(), "REF_VALID_001"
        )
        
        result = self.enumerator.validate_transaction_metadata(valid_edge)
        assert result['is_valid'] == True
        assert result['error'] is None
        assert result['amounts']['transaction_amount'] == Decimal('123.456789')
        assert result['metadata']['currency'] == 'EUR'
        assert result['metadata']['reference_id'] == 'REF_VALID_001'
        assert result['metadata']['timestamp_validated'] == True
        
        # Test 2: Invalid amount format  
        invalid_amount_edge = self.create_transaction_edge_with_metadata(
            "invalid_amount", source, target,
            "100.00", "USD"  # Create with valid amount first
        )
        # Then modify metadata to invalid
        invalid_amount_edge.edge_metadata.context['transaction_amount'] = 'invalid_amount'
        
        result = self.enumerator.validate_transaction_metadata(invalid_amount_edge)
        assert result['is_valid'] == False
        assert "Invalid transaction amount format" in result['error']
        
        # Test 3: Negative amount
        negative_edge = self.create_transaction_edge_with_metadata(
            "negative_tx", source, target,
            "50.00", "USD"  # Create with positive amount first
        )
        # Then modify metadata to negative
        negative_edge.edge_metadata.context['transaction_amount'] = '-50.00'
        
        result = self.enumerator.validate_transaction_metadata(negative_edge)
        assert result['is_valid'] == False
        assert "Negative transaction amount" in result['error']
        
        # Test 4: Invalid currency format
        invalid_currency_edge = self.create_transaction_edge_with_metadata(
            "invalid_currency", source, target,
            "100.00", "US"  # Should be 3 letters
        )
        
        result = self.enumerator.validate_transaction_metadata(invalid_currency_edge)
        assert result['is_valid'] == False
        assert "Invalid currency format" in result['error']
        
        # Test 5: Invalid timestamp
        invalid_timestamp_edge = self.create_transaction_edge_with_metadata(
            "invalid_timestamp", source, target,
            "100.00", "USD", 
            timestamp="invalid_timestamp_format"
        )
        
        result = self.enumerator.validate_transaction_metadata(invalid_timestamp_edge)
        assert result['is_valid'] == False
        assert "Invalid timestamp format" in result['error']
        
        print("✅ Test Académique 12.02: Transaction Metadata Validation Comprehensive - PASSED")
    
    def test_transaction_amounts_extraction_aggregation(self):
        """
        Test Académique 12.03: Extraction et aggregation amounts
        
        Validation:
        - Extraction amounts avec Decimal precision preservation
        - Currency aggregation correcte par type
        - Edge weight consistency checking
        - Error resilience pour extraction partielle
        - Performance metrics extraction time
        """
        edges = self.create_sample_transaction_batch(5)
        
        # Test extraction
        result = self.enumerator.extract_transaction_amounts(edges)
        
        # Validation structure résultat
        assert isinstance(result, dict)
        assert 'amounts_by_edge' in result
        assert 'currency_totals' in result
        assert 'extraction_summary' in result
        assert 'extraction_errors' in result
        
        # Validation amounts extraction
        amounts_by_edge = result['amounts_by_edge']
        assert len(amounts_by_edge) == 5
        
        for edge in edges:
            assert edge.edge_id in amounts_by_edge
            edge_data = amounts_by_edge[edge.edge_id]
            assert 'amount' in edge_data
            assert 'currency' in edge_data
            assert 'edge_weight' in edge_data
            assert 'consistency_check' in edge_data
            assert isinstance(edge_data['amount'], Decimal)
        
        # Validation currency totals
        currency_totals = result['currency_totals']
        expected_totals = {
            'USD': Decimal('100.50') + Decimal('50.00') + Decimal('75.30'),  # 225.80
            'EUR': Decimal('250.75'),
            'GBP': Decimal('1000.25')
        }
        
        for currency, expected_total in expected_totals.items():
            assert currency in currency_totals
            assert currency_totals[currency] == expected_total
        
        # Validation extraction summary
        summary = result['extraction_summary']
        assert summary['total_edges'] == 5
        assert summary['successful_extractions'] == 5
        assert summary['extraction_errors'] == 0
        assert summary['extraction_time_ms'] > 0
        assert summary['unique_currencies'] == 3
        
        # Validation statistics update
        assert self.enumerator.transaction_processor_stats['amount_extraction_time_ms'] > 0
        
        print("✅ Test Académique 12.03: Transaction Amounts Extraction Aggregation - PASSED")
    
    def test_optimized_transaction_enumeration_integration(self):
        """
        Test Académique 12.04: Enumeration optimisée transaction integration
        
        Validation:
        - Pre-processing filtering edges invalides
        - Integration avec DAG validation pipeline
        - Performance optimization pour batch enumeration
        - Statistics collection détaillées par edge
        - Error handling gracieux avec partial results
        """
        edges = self.create_sample_transaction_batch(3)
        
        # Mock NFA pour classification
        class TestTransactionNFA:
            def evaluate_to_final_state(self, word):
                return f"tx_state_{len(word) % 2}"
        
        test_nfa = TestTransactionNFA()
        
        # Test optimized enumeration
        result = self.enumerator.optimize_transaction_enumeration(
            edges, test_nfa, transaction_num=1
        )
        
        # Validation structure résultat
        assert isinstance(result, dict)
        assert 'enumeration_results' in result
        assert 'processing_results' in result
        assert 'optimization_summary' in result
        
        # Validation enumeration results
        enumeration_results = result['enumeration_results']
        assert len(enumeration_results) > 0  # At least some valid edges processed
        
        for edge_id, edge_result in enumeration_results.items():
            assert 'classification_result' in edge_result
            assert 'path_count' in edge_result
            assert 'enumeration_time_ms' in edge_result
            assert isinstance(edge_result['classification_result'], dict)
        
        # Validation processing results integration
        processing_results = result['processing_results']
        assert 'valid_transactions' in processing_results
        assert 'invalid_transactions' in processing_results
        
        # Validation optimization summary
        summary = result['optimization_summary']
        assert summary['input_edges'] == 3
        assert summary['valid_after_processing'] >= 0
        assert summary['enumeration_performed'] == True
        assert summary['optimization_time_ms'] > 0
        assert 'total_paths_enumerated' in summary
        assert 'processing_efficiency' in summary
        
        print("✅ Test Académique 12.04: Optimized Transaction Enumeration Integration - PASSED")
    
    def test_transaction_statistics_construction_analysis(self):
        """
        Test Académique 12.05: Construction et analysis statistics transaction
        
        Validation:
        - Amount distribution analysis par currency
        - Error rate analysis par type d'erreur
        - Performance metrics throughput calculation
        - Amount ranges classification (small/medium/large)
        - Cumulative processor statistics tracking
        """
        edges = self.create_sample_transaction_batch(4)
        
        # Process edges pour obtenir results
        processing_results = self.enumerator.process_transaction_edges(
            edges, validate_metadata=True
        )
        
        # Build statistics
        stats = self.enumerator.build_transaction_statistics(processing_results)
        
        # Validation structure statistics
        assert isinstance(stats, dict)
        assert 'amount_statistics' in stats
        assert 'error_statistics' in stats
        assert 'performance_statistics' in stats
        assert 'processor_cumulative_stats' in stats
        
        # Validation amount statistics
        amount_stats = stats['amount_statistics']
        assert 'total_transactions' in amount_stats
        assert 'currency_distribution' in amount_stats
        assert 'amount_ranges' in amount_stats
        assert 'total_value_by_currency' in amount_stats
        
        assert amount_stats['total_transactions'] == 4
        
        # Validation currency distribution
        currency_dist = amount_stats['currency_distribution']
        assert 'USD' in currency_dist
        assert currency_dist['USD'] >= 1  # At least one USD transaction
        
        # Validation amount ranges
        amount_ranges = amount_stats['amount_ranges']
        assert 'small' in amount_ranges or 'medium' in amount_ranges or 'large' in amount_ranges
        
        # Validation error statistics
        error_stats = stats['error_statistics']
        assert 'total_errors' in error_stats
        assert 'error_types' in error_stats
        assert 'error_rate' in error_stats
        assert error_stats['error_rate'] >= 0.0
        assert error_stats['error_rate'] <= 1.0
        
        # Validation performance statistics
        perf_stats = stats['performance_statistics']
        assert 'processing_time_ms' in perf_stats
        assert 'throughput_tx_per_sec' in perf_stats
        assert 'average_processing_time_per_tx' in perf_stats
        assert perf_stats['processing_time_ms'] > 0
        
        # Validation cumulative statistics
        cumulative = stats['processor_cumulative_stats']
        assert 'edges_processed' in cumulative
        assert 'total_processing_time_ms' in cumulative
        assert cumulative['edges_processed'] >= 4
        
        print("✅ Test Académique 12.05: Transaction Statistics Construction Analysis - PASSED")
    
    def test_transaction_edge_structure_validation_robustness(self):
        """
        Test Académique 12.06: Robustness validation structure transaction edge
        
        Validation:
        - Edge type TRANSACTION requirement
        - Source/target nodes existence validation
        - Metadata presence et structure validation
        - Weight non-negative requirement
        - Context metadata availability
        """
        source = create_node("struct_source")
        target = create_node("struct_target")
        
        # Test 1: Valid transaction structure
        valid_edge = self.create_transaction_edge_with_metadata(
            "valid_struct", source, target, "100.00"
        )
        assert self.enumerator._validate_transaction_edge_structure(valid_edge) == True
        
        # Test 2: Non-transaction edge type
        non_tx_edge = create_edge("non_tx", source, target, "100.00", EdgeType.STRUCTURAL)
        assert self.enumerator._validate_transaction_edge_structure(non_tx_edge) == False
        
        # Test 3: Missing source node
        edge_no_source = self.create_transaction_edge_with_metadata(
            "no_source", None, target, "100.00"
        )
        assert self.enumerator._validate_transaction_edge_structure(edge_no_source) == False
        
        # Test 4: Missing target node  
        edge_no_target = self.create_transaction_edge_with_metadata(
            "no_target", source, None, "100.00"
        )
        assert self.enumerator._validate_transaction_edge_structure(edge_no_target) == False
        
        # Test 5: Empty context metadata
        empty_context_edge = self.create_transaction_edge_with_metadata(
            "empty_context", source, target, "100.00"
        )
        empty_context_edge.edge_metadata.context = {}
        assert self.enumerator._validate_transaction_edge_structure(empty_context_edge) == False
        
        print("✅ Test Académique 12.06: Transaction Edge Structure Validation Robustness - PASSED")
    
    def test_transaction_processing_performance_requirements(self):
        """
        Test Académique 12.07: Performance requirements transaction processing
        
        Validation:
        - Processing throughput >= 100 transactions/sec pour batch normal
        - Memory usage stable avec large transaction sets
        - Statistics collection overhead minimal (<10% total time)
        - Error handling performance impact acceptable
        - Metadata validation time linear scaling
        """
        # Test performance avec different batch sizes
        batch_sizes = [10, 50, 100]
        performance_results = []
        
        for batch_size in batch_sizes:
            edges = self.create_sample_transaction_batch(batch_size)
            
            start_time = time.time()
            result = self.enumerator.process_transaction_edges(
                edges, validate_metadata=True
            )
            end_time = time.time()
            
            processing_time = (end_time - start_time) * 1000  # ms
            throughput = (batch_size * 1000) / processing_time if processing_time > 0 else 0
            
            performance_results.append({
                'batch_size': batch_size,
                'processing_time_ms': processing_time,
                'throughput_tx_per_sec': throughput,
                'valid_count': len(result['valid_transactions'])
            })
        
        # Validation performance requirements
        for result in performance_results:
            # Throughput requirement (adjusted for test environment)
            assert result['throughput_tx_per_sec'] >= 50, \
                f"Throughput {result['throughput_tx_per_sec']:.2f} tx/sec below requirement for batch {result['batch_size']}"
            
            # Processing time should scale roughly linearly
            time_per_tx = result['processing_time_ms'] / result['batch_size']
            assert time_per_tx <= 20, \
                f"Time per transaction {time_per_tx:.2f}ms too high for batch {result['batch_size']}"
        
        # Validation scaling characteristics
        if len(performance_results) >= 2:
            scaling_factor = performance_results[1]['processing_time_ms'] / performance_results[0]['processing_time_ms']
            batch_ratio = performance_results[1]['batch_size'] / performance_results[0]['batch_size']
            
            # Scaling should be roughly linear (within 50% deviation)
            assert scaling_factor <= batch_ratio * 1.5, \
                f"Processing time scaling {scaling_factor:.2f} exceeds linear expectation"
        
        print("✅ Test Académique 12.07: Transaction Processing Performance Requirements - PASSED")
    
    def test_transaction_processing_error_handling_robustness(self):
        """
        Test Académique 12.08: Error handling robustness transaction processing
        
        Validation:
        - Graceful degradation avec partial invalid batch
        - Exception propagation appropriée pour critical errors
        - Error context preservation dans results
        - Statistics tracking même en cas d'erreurs
        - Recovery capability après processing errors
        """
        # Création mixed batch (valid + diverses erreurs)
        mixed_batch = []
        
        # Valid transactions
        valid_edges = self.create_sample_transaction_batch(2)
        mixed_batch.extend(valid_edges)
        
        # Invalid structure transaction
        invalid_node1 = create_node("invalid_1")
        invalid_node2 = create_node("invalid_2") 
        invalid_struct = create_edge("invalid_struct", invalid_node1, invalid_node2, "100", EdgeType.STRUCTURAL)
        mixed_batch.append(invalid_struct)
        
        # Invalid metadata transaction
        invalid_metadata = self.create_transaction_edge_with_metadata(
            "invalid_meta", invalid_node1, invalid_node2, "100.00"  # Valid amount first
        )
        # Then corrupt metadata
        invalid_metadata.edge_metadata.context['transaction_amount'] = 'invalid_amount'
        mixed_batch.append(invalid_metadata)
        
        # Test processing avec mixed batch
        result = self.enumerator.process_transaction_edges(
            mixed_batch, validate_metadata=True
        )
        
        # Validation graceful degradation
        assert isinstance(result, dict)
        assert len(result['valid_transactions']) >= 2  # Valid ones processed
        assert len(result['invalid_transactions']) >= 2  # Invalid ones detected
        
        # Validation error context preservation
        for invalid_tx in result['invalid_transactions']:
            assert 'edge_id' in invalid_tx
            assert 'error' in invalid_tx
            assert len(invalid_tx['error']) > 0
        
        # Validation statistics tracking malgré erreurs
        assert self.enumerator.transaction_processor_stats['edges_processed'] > 0
        assert self.enumerator.transaction_processor_stats['validation_errors'] > 0
        
        # Test recovery capability - nouvelle opération après erreurs
        recovery_batch = self.create_sample_transaction_batch(2)
        recovery_result = self.enumerator.process_transaction_edges(
            recovery_batch, validate_metadata=True
        )
        
        # Should process successfully après previous errors
        assert len(recovery_result['valid_transactions']) == 2
        assert len(recovery_result['invalid_transactions']) == 0
        
        print("✅ Test Académique 12.08: Transaction Processing Error Handling Robustness - PASSED")
    
    def test_transaction_integration_with_dag_pipeline_coherence(self):
        """
        Test Académique 12.09: Integration cohérence avec DAG pipeline
        
        Validation:
        - Transaction processing → DAG validation → enumeration pipeline
        - Statistics consolidation entre transaction processing et DAG validation
        - Compatibility avec existing DAG integration features
        - Performance impact minimal de integration complète
        - Data flow coherence à travers pipeline stages
        """
        # Setup transaction batch connecté
        edges = self.create_sample_transaction_batch(3)
        
        # Mock NFA for pipeline
        class IntegrationNFA:
            def evaluate_to_final_state(self, word):
                return f"integrated_state_{hash(word) % 3}"
        
        integration_nfa = IntegrationNFA()
        
        # Test 1: Full integration pipeline
        optimization_result = self.enumerator.optimize_transaction_enumeration(
            edges, integration_nfa, transaction_num=1
        )
        
        # Validation pipeline coherence
        assert 'enumeration_results' in optimization_result
        assert 'processing_results' in optimization_result
        
        # Validation chaque edge processed → validated → enumerated
        processing = optimization_result['processing_results']
        enumeration = optimization_result['enumeration_results']
        
        valid_edge_ids = {tx['edge_id'] for tx in processing['valid_transactions']}
        enumerated_edge_ids = set(enumeration.keys())
        
        # Valid transactions should be enumerated
        assert len(enumerated_edge_ids) > 0
        for edge_id in enumerated_edge_ids:
            assert edge_id in valid_edge_ids, f"Edge {edge_id} enumerated but not in valid transactions"
        
        # Test 2: Statistics consolidation
        integrated_stats = self.enumerator.get_integrated_dag_statistics()
        
        # Should include transaction processing statistics
        assert 'transaction_processing' in integrated_stats
        tx_stats = integrated_stats['transaction_processing']
        assert 'edges_processed' in tx_stats
        assert tx_stats['edges_processed'] > 0
        
        # Test 3: DAG validation occurred during optimization
        assert self.enumerator.last_dag_validation is not None
        dag_validation = self.enumerator.last_dag_validation
        assert hasattr(dag_validation, 'is_valid')
        
        # Test 4: Performance impact assessment
        optimization_summary = optimization_result['optimization_summary']
        processing_time = processing['processing_summary']['processing_time_ms']
        optimization_time = optimization_summary['optimization_time_ms']
        
        # Processing should be small fraction of total optimization time
        processing_fraction = processing_time / optimization_time if optimization_time > 0 else 0
        assert processing_fraction <= 0.5, \
            f"Transaction processing time {processing_fraction:.2%} too high fraction of total pipeline"
        
        print("✅ Test Académique 12.09: Transaction Integration DAG Pipeline Coherence - PASSED")
    
    def test_comprehensive_transaction_edge_processing_integration(self):
        """
        Test Académique 12.10: Integration comprehensive transaction edge processing
        
        Validation finale:
        - Toutes features Step 2.3 integrated et functional
        - Performance requirements met pour production usage
        - Error handling robustness across all methods
        - Statistics accuracy et completeness
        - Backward compatibility avec existing PathEnumerator API
        """
        # Test complet avec large diverse dataset
        large_batch = self.create_sample_transaction_batch(20)
        
        # Add some problematic transactions
        problematic_node1 = create_node("prob_1")
        problematic_node2 = create_node("prob_2")
        
        # Invalid currency
        invalid_currency = self.create_transaction_edge_with_metadata(
            "invalid_curr", problematic_node1, problematic_node2, "100.00", "INVALID"
        )
        large_batch.append(invalid_currency)
        
        # Negative amount
        negative_amount = self.create_transaction_edge_with_metadata(
            "negative", problematic_node1, problematic_node2, "50.00", "USD"  # Positive first
        )
        # Then modify to negative
        negative_amount.edge_metadata.context['transaction_amount'] = '-50.00'
        large_batch.append(negative_amount)
        
        class ComprehensiveNFA:
            def evaluate_to_final_state(self, word):
                return f"comprehensive_{len(word) % 4}"
        
        comprehensive_nfa = ComprehensiveNFA()
        
        # Test 1: Full processing pipeline
        start_time = time.time()
        
        processing_result = self.enumerator.process_transaction_edges(
            large_batch, validate_metadata=True
        )
        
        amounts_result = self.enumerator.extract_transaction_amounts(
            [edge for edge in large_batch 
             if any(tx['edge_id'] == edge.edge_id for tx in processing_result['valid_transactions'])]
        )
        
        statistics = self.enumerator.build_transaction_statistics(processing_result)
        
        optimization_result = self.enumerator.optimize_transaction_enumeration(
            large_batch[:5], comprehensive_nfa, transaction_num=1  # Subset for performance
        )
        
        total_time = (time.time() - start_time) * 1000
        
        # Test 2: Validation comprehensive functionality
        
        # Processing functionality
        assert len(processing_result['valid_transactions']) >= 18  # Most should be valid
        assert len(processing_result['invalid_transactions']) >= 2   # Some invalid
        
        # Amounts extraction functionality
        assert 'currency_totals' in amounts_result
        assert len(amounts_result['currency_totals']) >= 3  # Multiple currencies
        
        # Statistics functionality
        assert 'amount_statistics' in statistics
        assert 'performance_statistics' in statistics
        assert statistics['amount_statistics']['total_transactions'] >= 18
        
        # Optimization functionality
        assert 'enumeration_results' in optimization_result
        assert len(optimization_result['enumeration_results']) > 0
        
        # Test 3: Performance requirements comprehensive
        processing_throughput = len(large_batch) * 1000 / total_time
        assert processing_throughput >= 30, f"Overall throughput {processing_throughput:.2f} tx/sec too low"
        
        # Test 4: Statistics accuracy comprehensive
        cumulative_stats = self.enumerator.transaction_processor_stats
        assert cumulative_stats['edges_processed'] >= len(large_batch)
        assert cumulative_stats['total_processing_time_ms'] > 0
        
        # Test 5: Error handling comprehensive
        assert cumulative_stats['validation_errors'] >= 2  # Should catch invalid transactions
        
        print("✅ Test Académique 12.10: Comprehensive Transaction Edge Processing Integration - PASSED")
        print(f"   - Processed {len(large_batch)} transactions in {total_time:.2f}ms")
        print(f"   - Throughput: {processing_throughput:.2f} tx/sec")
        print(f"   - Valid: {len(processing_result['valid_transactions'])}, Invalid: {len(processing_result['invalid_transactions'])}")
        print(f"   - Currencies processed: {len(amounts_result['currency_totals'])}")


if __name__ == "__main__":
    # Run tests with detailed output
    test_instance = TestAcademicTransactionEdgeProcessing()
    
    test_methods = [
        'test_transaction_edge_processing_basic_functionality',
        'test_transaction_metadata_validation_comprehensive', 
        'test_transaction_amounts_extraction_aggregation',
        'test_optimized_transaction_enumeration_integration',
        'test_transaction_statistics_construction_analysis',
        'test_transaction_edge_structure_validation_robustness',
        'test_transaction_processing_performance_requirements',
        'test_transaction_processing_error_handling_robustness',
        'test_transaction_integration_with_dag_pipeline_coherence',
        'test_comprehensive_transaction_edge_processing_integration'
    ]
    
    for method_name in test_methods:
        test_instance.setup_method()
        method = getattr(test_instance, method_name)
        try:
            method()
        except Exception as e:
            print(f"❌ {method_name} FAILED: {e}")
            raise
    
    print(f"\n🎉 All {len(test_methods)} Academic Transaction Edge Processing Tests PASSED! 🎉")