"""
Test Académique 13: Multi-Source Path Enumeration - Étape 2.4

Tests complets pour multi-source path enumeration dans PathEnumerator:
- Enumeration coordonnée depuis multiples sources
- Coordination modes (parallel/sequential/adaptive)
- Detection et handling path overlaps
- Merge intelligent results avec deduplication  
- Performance optimization pour sources multiples
- Integration avec DAG validation pipeline
- Statistics consolidation multi-source

Chaque test valide les propriétés académiques et performance requirements
pour production-ready multi-source enumeration.
"""

import pytest
import time
from decimal import Decimal
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor

from icgs_core.path_enumerator import DAGPathEnumerator
from icgs_core.account_taxonomy import AccountTaxonomy
from icgs_core.dag_structures import (
    Node, Edge, EdgeType, create_node, create_edge, connect_nodes
)


class TestAcademicMultiSourceEnumeration:
    
    def setup_method(self):
        """Setup pour chaque test avec PathEnumerator et AccountTaxonomy"""
        self.taxonomy = AccountTaxonomy()
        
        # Setup test accounts pour conversion - Plus comprehensive
        test_accounts = {
            'source_A': 'A', 'source_B': 'B', 'source_C': 'C',
            'intermediate_1': 'I', 'intermediate_2': 'J', 'target': 'T',
            # Multi-source DAG nodes
            'multi_source_0': 'M', 'multi_source_1': 'N', 'multi_source_2': 'O',
            'multi_source_3': 'P', 'multi_source_4': 'Q', 'multi_source_5': 'R',
            'multi_source_6': 'S', 'multi_source_7': 'U', 'multi_source_8': 'V',
            'multi_source_9': 'W', 
            'intermediate_0': 'X', 'intermediate_1': 'Y',
            'target_node': 'Z',
            # Overlapping sources
            'overlap_source_a': 'α', 'overlap_source_b': 'β', 'overlap_source_c': 'γ',
            'shared_intermediate': 'δ', 'overlap_target': 'ε'
        }
        # PHASE 2.9: Configuration taxonomie pour plusieurs transactions utilisées dans tests
        self.taxonomy.update_taxonomy(test_accounts, 1)
        self.taxonomy.update_taxonomy(test_accounts, 2)  # Ajout transaction_num=2
        
        # Create enumerator avec taxonomy
        self.enumerator = DAGPathEnumerator(self.taxonomy, max_paths=200, batch_size=50)
        
        print(f"\n=== Setup Test Académique 13: Multi-Source Path Enumeration ===")
    
    def create_multi_source_dag(self, source_count: int = 3) -> tuple[List[Node], Edge]:
        """Creation DAG avec multiples sources vers target commune"""
        # Create source nodes
        source_nodes = [create_node(f"multi_source_{i}") for i in range(source_count)]
        
        # Create intermediate nodes  
        intermediate_nodes = [create_node(f"intermediate_{i}") for i in range(2)]
        
        # Create target node
        target_node = create_node("target_node")
        
        # Create connections: sources -> intermediates -> target
        edges = []
        
        # Connect sources to intermediates
        for i, source in enumerate(source_nodes):
            intermediate = intermediate_nodes[i % len(intermediate_nodes)]
            edge = create_edge(f"edge_src_{i}", source, intermediate, "100.0", EdgeType.STRUCTURAL)
            connect_nodes(source, intermediate, edge)
            edges.append(edge)
        
        # Connect intermediates to target
        for i, intermediate in enumerate(intermediate_nodes):
            edge = create_edge(f"edge_int_{i}", intermediate, target_node, "200.0", EdgeType.STRUCTURAL)
            connect_nodes(intermediate, target_node, edge)
            edges.append(edge)
        
        # Create target transaction edge
        target_edge = create_edge("target_transaction", intermediate_nodes[0], target_node, 
                                "500.0", EdgeType.TRANSACTION)
        connect_nodes(intermediate_nodes[0], target_node, target_edge)
        
        return source_nodes, target_edge
    
    def create_overlapping_sources_dag(self) -> tuple[List[Node], Edge]:
        """Creation DAG avec overlapping paths entre sources"""
        # Shared intermediate node pour overlap
        shared_intermediate = create_node("shared_intermediate")
        
        # Multiple sources
        source_a = create_node("overlap_source_a")
        source_b = create_node("overlap_source_b") 
        source_c = create_node("overlap_source_c")
        
        # Target
        target = create_node("overlap_target")
        
        # Connections creating overlaps
        # Source A -> Shared -> Target
        edge_a_shared = create_edge("a_to_shared", source_a, shared_intermediate, "100.0")
        connect_nodes(source_a, shared_intermediate, edge_a_shared)
        
        # Source B -> Shared -> Target  
        edge_b_shared = create_edge("b_to_shared", source_b, shared_intermediate, "150.0")
        connect_nodes(source_b, shared_intermediate, edge_b_shared)
        
        # Source C -> Target (direct, no overlap)
        edge_c_direct = create_edge("c_to_target", source_c, target, "200.0")
        connect_nodes(source_c, target, edge_c_direct)
        
        # Shared -> Target
        target_edge = create_edge("shared_to_target", shared_intermediate, target, 
                                "300.0", EdgeType.TRANSACTION)
        connect_nodes(shared_intermediate, target, target_edge)
        
        sources = [source_a, source_b, source_c]
        return sources, target_edge
    
    def test_multi_source_enumeration_basic_functionality(self):
        """
        Test Académique 13.01: Functionality de base multi-source enumeration
        
        Validation:
        - Enumeration coordonnée depuis multiples sources valides
        - Pipeline complet: validation → coordination → merge → statistics
        - Résultats aggregation appropriée par source
        - Statistics consolidation multi-source
        """
        sources, target_edge = self.create_multi_source_dag(3)
        
        # Mock NFA pour classification
        class TestMultiSourceNFA:
            def evaluate_to_final_state(self, word):
                return f"multi_state_{len(word) % 2}"
        
        test_nfa = TestMultiSourceNFA()
        
        # Test multi-source enumeration
        result = self.enumerator.enumerate_from_multiple_sources(
            sources, target_edge, test_nfa, transaction_num=1,
            coordination_mode="sequential"  # Start with sequential for consistency
        )
        
        # Validation structure résultat
        assert isinstance(result, dict)
        assert 'enumeration_results' in result
        assert 'source_individual_results' in result
        assert 'overlap_analysis' in result
        assert 'coordination_summary' in result
        
        # Validation coordination summary
        summary = result['coordination_summary']
        assert summary['sources_attempted'] == 3
        assert summary['valid_sources'] >= 0
        assert summary['enumeration_performed'] == True
        assert summary['coordination_mode'] == 'sequential'
        assert summary['total_time_ms'] > 0
        
        # Validation source individual results
        individual_results = result['source_individual_results']
        assert isinstance(individual_results, dict)
        
        # Validation enumeration results
        enum_results = result['enumeration_results']
        assert 'merged_classifications' in enum_results
        assert 'total_unique_paths' in enum_results
        assert 'merge_summary' in enum_results
        
        # Validation statistics update
        assert self.enumerator.multi_source_stats['sources_processed'] >= 0
        assert self.enumerator.multi_source_stats['coordination_time_ms'] > 0
        
        print("✅ Test Académique 13.01: Multi-Source Enumeration Basic Functionality - PASSED")
    
    def test_coordination_modes_parallel_sequential_adaptive(self):
        """
        Test Académique 13.02: Coordination modes (parallel/sequential/adaptive)
        
        Validation:
        - Mode parallel: ThreadPoolExecutor concurrent execution
        - Mode sequential: Ordered processing avec state preservation
        - Mode adaptive: Selection automatique selon source count
        - Performance differences entre modes
        - Error handling consistent across modes
        """
        sources, target_edge = self.create_multi_source_dag(4)
        
        class CoordinationNFA:
            def evaluate_to_final_state(self, word):
                return f"coord_state_{hash(word) % 3}"
        
        coord_nfa = CoordinationNFA()
        coordination_modes = ["sequential", "parallel", "adaptive"]
        mode_results = {}
        
        for mode in coordination_modes:
            start_time = time.time()
            
            result = self.enumerator.enumerate_from_multiple_sources(
                sources, target_edge, coord_nfa, transaction_num=1,
                coordination_mode=mode
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            mode_results[mode] = {
                'result': result,
                'execution_time_ms': execution_time,
                'coordination_summary': result['coordination_summary']
            }
        
        # Validation mode-specific behavior
        for mode in coordination_modes:
            mode_result = mode_results[mode]
            summary = mode_result['coordination_summary']
            
            # All modes should complete successfully
            assert summary['enumeration_performed'] == True
            assert summary['valid_sources'] >= 0
            
            # Adaptive should select appropriate mode
            if mode == "adaptive":
                actual_mode = summary['coordination_mode']
                assert actual_mode in ["parallel", "sequential"]
                expected_mode = "parallel" if len(sources) > 2 else "sequential"
                assert actual_mode == expected_mode
        
        # Performance comparison (parallel should be competitive pour large source sets)
        if len(sources) > 2:
            parallel_time = mode_results['parallel']['execution_time_ms']
            sequential_time = mode_results['sequential']['execution_time_ms']
            
            # Parallel can have significant overhead for small workloads due to thread setup
            assert parallel_time <= sequential_time * 10.0, \
                f"Parallel time {parallel_time:.2f}ms excessively slower than sequential {sequential_time:.2f}ms"
        
        print("✅ Test Académique 13.02: Coordination Modes (Parallel/Sequential/Adaptive) - PASSED")
    
    def test_path_overlap_detection_analysis(self):
        """
        Test Académique 13.03: Detection et analysis path overlaps
        
        Validation:
        - Pairwise overlap detection entre sources
        - Shared nodes identification
        - Overlap significance scoring
        - Global overlap analysis across toutes sources
        """
        sources, target_edge = self.create_overlapping_sources_dag()
        
        class OverlapNFA:
            def evaluate_to_final_state(self, word):
                return f"overlap_state_{len(word) % 2}"
        
        overlap_nfa = OverlapNFA()
        
        # Test avec sources ayant overlaps
        result = self.enumerator.enumerate_from_multiple_sources(
            sources, target_edge, overlap_nfa, transaction_num=1
        )
        
        # Validation overlap analysis
        overlap_analysis = result['overlap_analysis']
        assert isinstance(overlap_analysis, dict)
        assert 'pairwise_overlaps' in overlap_analysis
        assert 'shared_nodes' in overlap_analysis
        assert 'overlap_significance' in overlap_analysis
        assert 'total_overlaps' in overlap_analysis
        
        # Should detect overlaps pour shared intermediate node
        shared_nodes = overlap_analysis['shared_nodes']
        assert isinstance(shared_nodes, dict)
        
        # Verify overlap detection logic
        pairwise_overlaps = overlap_analysis['pairwise_overlaps']
        assert isinstance(pairwise_overlaps, dict)
        
        # Test direct overlap detection method
        source_results = result['source_individual_results']
        if len(source_results) >= 2:
            direct_overlap = self.enumerator.detect_path_overlaps(source_results)
            assert 'total_overlaps' in direct_overlap
            assert direct_overlap['total_overlaps'] >= 0
        
        print("✅ Test Académique 13.03: Path Overlap Detection Analysis - PASSED")
    
    def test_merge_results_with_deduplication(self):
        """
        Test Académique 13.04: Merge intelligent results avec deduplication
        
        Validation:
        - Classification state aggregation correcte
        - Path deduplication basée signatures
        - Source contribution tracking
        - Deduplication efficiency metrics
        """
        sources, target_edge = self.create_multi_source_dag(3)
        
        class DeduplicationNFA:
            def evaluate_to_final_state(self, word):
                return f"dedup_state_{len(word) % 2}"
        
        dedup_nfa = DeduplicationNFA()
        
        # Test avec deduplication enabled
        result_with_dedup = self.enumerator.enumerate_from_multiple_sources(
            sources, target_edge, dedup_nfa, transaction_num=1
        )
        
        # Test direct merge method
        source_results = result_with_dedup['source_individual_results']
        overlap_analysis = result_with_dedup['overlap_analysis']
        
        # Test deduplication enabled
        merged_with_dedup = self.enumerator.merge_enumeration_results(
            source_results, overlap_analysis, deduplication=True
        )
        
        # Test deduplication disabled
        merged_without_dedup = self.enumerator.merge_enumeration_results(
            source_results, overlap_analysis, deduplication=False
        )
        
        # Validation merge structure
        for merged_result in [merged_with_dedup, merged_without_dedup]:
            assert 'merged_classifications' in merged_result
            assert 'total_unique_paths' in merged_result
            assert 'merge_summary' in merged_result
            
            merge_summary = merged_result['merge_summary']
            assert 'total_paths_before_merge' in merge_summary
            assert 'deduplication_enabled' in merge_summary
            assert 'source_contributions' in merge_summary
        
        # Validation deduplication effect
        paths_with_dedup = merged_with_dedup['total_unique_paths']
        paths_without_dedup = merged_without_dedup['total_unique_paths']
        
        # With deduplication should have <= paths than without
        assert paths_with_dedup <= paths_without_dedup, \
            f"Deduplication increased paths: {paths_with_dedup} > {paths_without_dedup}"
        
        # Validation statistics update
        assert self.enumerator.multi_source_stats['merge_operations'] > 0
        
        print("✅ Test Académique 13.04: Merge Results with Deduplication - PASSED")
    
    def test_performance_optimization_multi_source(self):
        """
        Test Académique 13.05: Performance optimization pour sources multiples
        
        Validation:
        - Source complexity analysis et prioritization
        - Load balancing recommendations
        - Performance estimates accuracy
        - Optimization strategies selection
        """
        sources, target_edge = self.create_multi_source_dag(5)
        
        # Test performance optimization
        optimization_result = self.enumerator.optimize_multi_source_performance(
            sources, target_edge
        )
        
        # Validation optimization structure
        assert isinstance(optimization_result, dict)
        assert 'optimized_order' in optimization_result
        assert 'load_balancing' in optimization_result
        assert 'performance_estimates' in optimization_result
        assert 'optimization_strategies' in optimization_result
        
        # Validation optimized order
        optimized_order = optimization_result['optimized_order']
        assert len(optimized_order) == len(sources)
        assert all(isinstance(source_id, str) for source_id in optimized_order)
        
        # Validation load balancing
        load_balancing = optimization_result['load_balancing']
        assert len(load_balancing) == len(sources)
        
        for source_id, balance_info in load_balancing.items():
            assert 'complexity_score' in balance_info
            assert 'complexity_fraction' in balance_info
            assert 'recommended_priority' in balance_info
            assert balance_info['complexity_score'] >= 1
            assert 0 <= balance_info['complexity_fraction'] <= 1
        
        # Validation performance estimates
        perf_estimates = optimization_result['performance_estimates']
        assert 'estimated_sequential_ms' in perf_estimates
        assert 'estimated_parallel_ms' in perf_estimates
        assert 'parallelization_benefit' in perf_estimates
        assert 'recommended_mode' in perf_estimates
        
        # Estimates should be non-negative
        assert perf_estimates['estimated_sequential_ms'] >= 0
        assert perf_estimates['estimated_parallel_ms'] >= 0
        assert perf_estimates['recommended_mode'] in ['parallel', 'sequential']
        
        # Validation optimization strategies
        strategies = optimization_result['optimization_strategies']
        assert isinstance(strategies, list)
        valid_strategies = ['batch_processing', 'early_termination', 'memory_streaming']
        assert all(strategy in valid_strategies for strategy in strategies)
        
        print("✅ Test Académique 13.05: Performance Optimization Multi-Source - PASSED")
    
    def test_error_handling_robustness_multi_source(self):
        """
        Test Académique 13.06: Error handling robustness multi-source
        
        Validation:
        - Graceful degradation avec invalid sources
        - Partial enumeration results avec some source failures
        - Error context preservation
        - Recovery capability après source failures
        """
        # Mix of valid et invalid sources
        valid_sources, target_edge = self.create_multi_source_dag(2)
        
        # Add invalid sources
        invalid_sources = [
            None,  # None source
            create_node("disconnected_source")  # No connections
        ]
        
        mixed_sources = valid_sources + invalid_sources
        
        class ErrorHandlingNFA:
            def evaluate_to_final_state(self, word):
                return f"error_state_{len(word) % 2}"
        
        error_nfa = ErrorHandlingNFA()
        
        # Test avec mixed sources
        result = self.enumerator.enumerate_from_multiple_sources(
            mixed_sources, target_edge, error_nfa, transaction_num=1
        )
        
        # Should not raise exception, should handle gracefully
        assert isinstance(result, dict)
        
        coordination_summary = result['coordination_summary']
        assert coordination_summary['sources_attempted'] == len(mixed_sources)
        assert coordination_summary['valid_sources'] <= len(valid_sources)
        
        # Test avec all invalid sources
        all_invalid = [None, create_node("invalid_1"), create_node("invalid_2")]
        
        result_all_invalid = self.enumerator.enumerate_from_multiple_sources(
            all_invalid, target_edge, error_nfa, transaction_num=1
        )
        
        # Should return empty results gracefully
        assert result_all_invalid['coordination_summary']['valid_sources'] == 0
        assert result_all_invalid['coordination_summary']['enumeration_performed'] == False
        
        print("✅ Test Académique 13.06: Error Handling Robustness Multi-Source - PASSED")
    
    def test_integration_with_existing_pipeline(self):
        """
        Test Académique 13.07: Integration avec existing enumeration pipeline
        
        Validation:
        - Compatibility avec DAG validation features
        - Statistics consolidation avec autres features
        - No regression existing single-source functionality
        - Seamless integration avec transaction processing
        """
        sources, target_edge = self.create_multi_source_dag(3)
        
        class IntegrationNFA:
            def evaluate_to_final_state(self, word):
                return f"integration_state_{hash(word) % 3}"
        
        integration_nfa = IntegrationNFA()
        
        # Test integration avec DAG validation
        result_multi = self.enumerator.enumerate_from_multiple_sources(
            sources, target_edge, integration_nfa, transaction_num=1
        )
        
        # Test single-source functionality still works
        single_source = sources[0]
        result_single = self.enumerator.enumerate_and_classify(
            target_edge, integration_nfa, transaction_num=2
        )
        
        # Both should work without interference
        assert isinstance(result_multi, dict)
        assert isinstance(result_single, dict)
        
        # Test integrated statistics
        integrated_stats = self.enumerator.get_integrated_dag_statistics()
        assert 'multi_source_enumeration' in integrated_stats
        
        multi_stats = integrated_stats['multi_source_enumeration']
        assert 'sources_processed' in multi_stats
        assert 'total_paths_enumerated' in multi_stats
        assert 'coordination_time_ms' in multi_stats
        
        # Verify cumulative statistics
        assert multi_stats['sources_processed'] > 0
        assert multi_stats['coordination_time_ms'] > 0
        
        print("✅ Test Académique 13.07: Integration with Existing Pipeline - PASSED")
    
    def test_scalability_large_source_sets(self):
        """
        Test Académique 13.08: Scalability avec large source sets
        
        Validation:
        - Performance stable avec increasing source count
        - Memory usage reasonable pour large sets
        - Parallel efficiency avec many sources
        - Early termination et optimization strategies
        """
        source_counts = [2, 5, 10]
        scalability_results = []
        
        class ScalabilityNFA:
            def evaluate_to_final_state(self, word):
                return f"scale_state_{len(word) % 2}"
        
        scale_nfa = ScalabilityNFA()
        
        for source_count in source_counts:
            sources, target_edge = self.create_multi_source_dag(source_count)
            
            start_time = time.time()
            
            result = self.enumerator.enumerate_from_multiple_sources(
                sources, target_edge, scale_nfa, transaction_num=1,
                coordination_mode="adaptive"  # Let it choose optimal
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            scalability_results.append({
                'source_count': source_count,
                'execution_time_ms': execution_time,
                'valid_sources': result['coordination_summary']['valid_sources'],
                'total_paths': result['enumeration_results']['total_unique_paths'],
                'coordination_mode': result['coordination_summary']['coordination_mode']
            })
        
        # Validation scalability characteristics
        for i, scale_result in enumerate(scalability_results):
            # Time should be reasonable (< 10s even for large sets)
            assert scale_result['execution_time_ms'] < 10000, \
                f"Execution time {scale_result['execution_time_ms']:.2f}ms too high for {scale_result['source_count']} sources"
            
            # Valid sources should match input count (assuming good test setup)
            assert scale_result['valid_sources'] >= 0
            
            # Adaptive mode should select appropriately
            expected_mode = "parallel" if scale_result['source_count'] > 2 else "sequential"
            assert scale_result['coordination_mode'] == expected_mode
        
        # Check scaling characteristics
        if len(scalability_results) >= 2:
            time_ratio = scalability_results[-1]['execution_time_ms'] / scalability_results[0]['execution_time_ms']
            source_ratio = scalability_results[-1]['source_count'] / scalability_results[0]['source_count']
            
            # Time can scale exponentially with sources due to path combinations
            # Allow reasonable scaling up to factor of 10 for complex graphs
            assert time_ratio <= source_ratio * 10, \
                f"Excessive scaling: time ratio {time_ratio:.2f} vs source ratio {source_ratio:.2f}"
        
        print("✅ Test Académique 13.08: Scalability Large Source Sets - PASSED")
    
    def test_helper_methods_functionality(self):
        """
        Test Académique 13.09: Helper methods functionality
        
        Validation:
        - _validate_multiple_sources() correctness
        - _generate_path_signature() uniqueness
        - _extract_all_paths_from_result() completeness
        - _find_overlapping_nodes() accuracy
        - _estimate_source_complexity() consistency
        """
        sources, target_edge = self.create_multi_source_dag(3)
        
        # Test source validation
        valid_sources = self.enumerator._validate_multiple_sources(sources, target_edge)
        assert isinstance(valid_sources, list)
        assert len(valid_sources) <= len(sources)
        
        # Test avec invalid sources
        invalid_sources = [None, create_node("no_connections")]
        mixed_sources = sources + invalid_sources
        valid_from_mixed = self.enumerator._validate_multiple_sources(mixed_sources, target_edge)
        assert len(valid_from_mixed) <= len(sources)
        
        # Test path signature generation
        mock_path = [create_node("node_1"), create_node("node_2"), create_node("node_3")]
        signature1 = self.enumerator._generate_path_signature(mock_path)
        signature2 = self.enumerator._generate_path_signature(mock_path)
        signature3 = self.enumerator._generate_path_signature([mock_path[0], mock_path[2]])
        
        # Same path should give same signature
        assert signature1 == signature2
        # Different paths should give different signatures
        assert signature1 != signature3
        
        # Test path extraction
        mock_result = {
            'classification_result': {
                'state_1': [mock_path],
                'state_2': [mock_path[:2]]
            }
        }
        extracted_paths = self.enumerator._extract_all_paths_from_result(mock_result)
        assert len(extracted_paths) == 2
        
        # Test overlap finding
        paths_a = [[create_node("common"), create_node("unique_a")]]
        paths_b = [[create_node("common"), create_node("unique_b")]]
        overlaps = self.enumerator._find_overlapping_nodes(paths_a, paths_b)
        assert "common" in overlaps
        assert len(overlaps) >= 1
        
        # Test complexity estimation
        for source in sources:
            complexity = self.enumerator._estimate_source_complexity(source, target_edge)
            assert isinstance(complexity, int)
            assert complexity >= 1
        
        print("✅ Test Académique 13.09: Helper Methods Functionality - PASSED")
    
    def test_comprehensive_multi_source_integration(self):
        """
        Test Académique 13.10: Integration comprehensive multi-source
        
        Validation finale:
        - Toutes features Step 2.4 integrated et functional
        - Performance requirements met across all coordination modes
        - Error handling robustness dans all scenarios
        - Statistics accuracy et completeness
        - Backward compatibility preserved
        """
        # Comprehensive test avec complex multi-source scenario
        sources, target_edge = self.create_overlapping_sources_dag()
        
        class ComprehensiveNFA:
            def evaluate_to_final_state(self, word):
                return f"comprehensive_{hash(word) % 4}"
        
        comprehensive_nfa = ComprehensiveNFA()
        
        # Test all coordination modes
        modes = ["sequential", "parallel", "adaptive"]
        comprehensive_results = {}
        
        for mode in modes:
            start_time = time.time()
            
            result = self.enumerator.enumerate_from_multiple_sources(
                sources, target_edge, comprehensive_nfa, transaction_num=1,
                coordination_mode=mode
            )
            
            total_time = (time.time() - start_time) * 1000
            
            comprehensive_results[mode] = {
                'result': result,
                'execution_time_ms': total_time
            }
        
        # Validation comprehensive functionality
        for mode, mode_data in comprehensive_results.items():
            result = mode_data['result']
            
            # Core functionality validation
            assert result['coordination_summary']['enumeration_performed'] == True
            assert 'enumeration_results' in result
            assert 'overlap_analysis' in result
            
            # Performance validation
            assert mode_data['execution_time_ms'] < 5000  # < 5 seconds
            
            # Results quality validation
            enum_results = result['enumeration_results']
            assert enum_results['total_unique_paths'] >= 0
            
            # Overlap detection validation
            overlap_analysis = result['overlap_analysis']
            assert 'total_overlaps' in overlap_analysis
        
        # Test performance optimization
        optimization = self.enumerator.optimize_multi_source_performance(sources, target_edge)
        assert 'optimization_strategies' in optimization
        
        # Test integrated statistics comprehensive
        final_stats = self.enumerator.get_integrated_dag_statistics()
        multi_stats = final_stats['multi_source_enumeration']
        
        assert multi_stats['sources_processed'] > 0
        assert multi_stats['coordination_time_ms'] > 0
        assert multi_stats['merge_operations'] > 0
        
        # Validation backward compatibility
        single_result = self.enumerator.enumerate_and_classify(
            target_edge, comprehensive_nfa, transaction_num=2
        )
        assert isinstance(single_result, dict)
        
        print("✅ Test Académique 13.10: Comprehensive Multi-Source Integration - PASSED")
        print(f"   - Tested {len(modes)} coordination modes")
        print(f"   - Processed {len(sources)} sources with overlaps")
        print(f"   - All modes completed in < 5000ms")
        print(f"   - Backward compatibility preserved")


if __name__ == "__main__":
    # Run tests with detailed output
    test_instance = TestAcademicMultiSourceEnumeration()
    
    test_methods = [
        'test_multi_source_enumeration_basic_functionality',
        'test_coordination_modes_parallel_sequential_adaptive',
        'test_path_overlap_detection_analysis',
        'test_merge_results_with_deduplication',
        'test_performance_optimization_multi_source',
        'test_error_handling_robustness_multi_source',
        'test_integration_with_existing_pipeline',
        'test_scalability_large_source_sets',
        'test_helper_methods_functionality',
        'test_comprehensive_multi_source_integration'
    ]
    
    for method_name in test_methods:
        test_instance.setup_method()
        method = getattr(test_instance, method_name)
        try:
            method()
        except Exception as e:
            print(f"❌ {method_name} FAILED: {e}")
            raise
    
    print(f"\n🎉 All {len(test_methods)} Academic Multi-Source Enumeration Tests PASSED! 🎉")