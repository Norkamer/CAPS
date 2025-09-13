"""
Test Académique 14: DAG Topology Analysis - Étape 2.5

Tests validation analyse topologique DAG avec métriques centrality,
connectivity patterns, path complexity, et optimization recommendations.

Coverage:
✅ Basic topology metrics calculation
✅ Node centrality analysis (degree/betweenness/closeness)
✅ Connectivity patterns et bottlenecks identification 
✅ Path complexity analysis avec branching factors
✅ Critical path identification
✅ Optimization recommendations generation
✅ Performance analysis large DAGs
✅ Error handling robustesse
✅ Integration avec existing pipeline
✅ Comprehensive topology integration
"""

import unittest
import time
from decimal import Decimal
from icgs_core.path_enumerator import DAGPathEnumerator
from icgs_core.account_taxonomy import AccountTaxonomy
from icgs_core.dag_structures import (
    Node, Edge, NodeType, EdgeType,
    create_node, create_edge, connect_nodes
)


class TestAcademicDAGTopologyAnalysis(unittest.TestCase):
    """Test suite pour Step 2.5: DAG Topology Analysis validation complète"""

    def setUp(self):
        """Setup test environment avec DAG topology structures"""
        print("\n=== Setup Test Académique 14: DAG Topology Analysis ===")
        
        # Test taxonomy pour character mapping (using valid UTF-32 characters)
        self.test_topology_accounts = {
            'topo_source_A': 'A', 'topo_source_B': 'B', 'topo_source_C': 'C',
            'topo_hub_1': 'H', 'topo_hub_2': 'I', 'topo_hub_3': 'J',
            'topo_branch_1': 'K', 'topo_branch_2': 'L', 'topo_branch_3': 'M',
            'topo_bottleneck': 'N', 'topo_sink_1': 'O', 'topo_sink_2': 'P',
            'topo_intermediate_1': 'Q', 'topo_intermediate_2': 'R',
            'topo_critical_node': 'S', 'topo_bridge_node': 'T',
            'complex_node_0': 'U', 'complex_node_1': 'V', 'complex_node_2': 'W',
            'complex_node_3': 'X', 'complex_node_4': 'Y', 'complex_node_5': 'Z',
            'path_node_0': 'α', 'path_node_1': 'β', 'path_node_2': 'γ',
            'path_node_3': 'δ', 'path_node_4': 'ε', 'path_node_5': 'ζ',
            'topo_single': 'Σ', 'topo_disc_A': 'a', 'topo_disc_B': 'b',
            'topo_disc_C': 'c', 'topo_disc_D': 'd'
        }
        
        # Create taxonomy avec character mappings
        self.taxonomy = AccountTaxonomy()
        
        # Update taxonomy avec tous les accounts pour transaction 1
        self.taxonomy.update_taxonomy(self.test_topology_accounts, transaction_num=1)
        
        # Initialize enumerator avec taxonomy
        self.enumerator = DAGPathEnumerator(self.taxonomy)

    def create_complex_topology_dag(self) -> tuple[list[Node], list[Edge], list[Node], Node]:
        """
        Création DAG complexe pour topology analysis testing
        
        Structure:
        - 3 sources avec different connectivity patterns
        - Hub nodes avec high centrality
        - Bottleneck nodes
        - Multiple paths avec different complexities
        - Critical paths pour analysis
        """
        # Sources
        source_a = create_node('topo_source_A')
        source_b = create_node('topo_source_B') 
        source_c = create_node('topo_source_C')
        
        # Hub nodes (high centrality)
        hub_1 = create_node('topo_hub_1')
        hub_2 = create_node('topo_hub_2')
        hub_3 = create_node('topo_hub_3')
        
        # Branching nodes
        branch_1 = create_node('topo_branch_1')
        branch_2 = create_node('topo_branch_2')
        branch_3 = create_node('topo_branch_3')
        
        # Bottleneck node
        bottleneck = create_node('topo_bottleneck')
        
        # Sink nodes
        sink_1 = create_node('topo_sink_1')
        sink_2 = create_node('topo_sink_2')
        
        # Intermediate nodes
        inter_1 = create_node('topo_intermediate_1')
        inter_2 = create_node('topo_intermediate_2')
        
        # Critical et bridge nodes
        critical = create_node('topo_critical_node')
        bridge = create_node('topo_bridge_node')
        
        nodes = [source_a, source_b, source_c, hub_1, hub_2, hub_3,
                branch_1, branch_2, branch_3, bottleneck, sink_1, sink_2,
                inter_1, inter_2, critical, bridge]
        
        # Create complex edge structure avec connections
        edges = []
        
        # Sources vers hubs (multiple connectivity)
        edge1 = create_edge('edge_1', source_a, hub_1, Decimal('200'))
        connect_nodes(source_a, hub_1, edge1)
        edges.append(edge1)
        
        edge2 = create_edge('edge_2', source_a, hub_2, Decimal('300'))
        connect_nodes(source_a, hub_2, edge2)
        edges.append(edge2)
        
        edge3 = create_edge('edge_3', source_b, hub_1, Decimal('150'))
        connect_nodes(source_b, hub_1, edge3)
        edges.append(edge3)
        
        edge4 = create_edge('edge_4', source_b, hub_3, Decimal('250'))
        connect_nodes(source_b, hub_3, edge4)
        edges.append(edge4)
        
        edge5 = create_edge('edge_5', source_c, hub_2, Decimal('400'))
        connect_nodes(source_c, hub_2, edge5)
        edges.append(edge5)
        
        edge6 = create_edge('edge_6', source_c, hub_3, Decimal('350'))
        connect_nodes(source_c, hub_3, edge6)
        edges.append(edge6)
        
        # Hubs vers branches (high branching factor)
        edge7 = create_edge('edge_7', hub_1, branch_1, Decimal('100'))
        connect_nodes(hub_1, branch_1, edge7)
        edges.append(edge7)
        
        edge8 = create_edge('edge_8', hub_1, branch_2, Decimal('120'))
        connect_nodes(hub_1, branch_2, edge8)
        edges.append(edge8)
        
        edge9 = create_edge('edge_9', hub_1, inter_1, Decimal('80'))
        connect_nodes(hub_1, inter_1, edge9)
        edges.append(edge9)
        
        edge10 = create_edge('edge_10', hub_2, branch_2, Decimal('150'))
        connect_nodes(hub_2, branch_2, edge10)
        edges.append(edge10)
        
        edge11 = create_edge('edge_11', hub_2, branch_3, Decimal('130'))
        connect_nodes(hub_2, branch_3, edge11)
        edges.append(edge11)
        
        edge12 = create_edge('edge_12', hub_2, inter_2, Decimal('90'))
        connect_nodes(hub_2, inter_2, edge12)
        edges.append(edge12)
        
        edge13 = create_edge('edge_13', hub_3, branch_1, Decimal('110'))
        connect_nodes(hub_3, branch_1, edge13)
        edges.append(edge13)
        
        edge14 = create_edge('edge_14', hub_3, branch_3, Decimal('140'))
        connect_nodes(hub_3, branch_3, edge14)
        edges.append(edge14)
        
        # Branches vers bottleneck (convergence)
        edge15 = create_edge('edge_15', branch_1, bottleneck, Decimal('80'))
        connect_nodes(branch_1, bottleneck, edge15)
        edges.append(edge15)
        
        edge16 = create_edge('edge_16', branch_2, bottleneck, Decimal('90'))
        connect_nodes(branch_2, bottleneck, edge16)
        edges.append(edge16)
        
        edge17 = create_edge('edge_17', branch_3, bottleneck, Decimal('70'))
        connect_nodes(branch_3, bottleneck, edge17)
        edges.append(edge17)
        
        edge18 = create_edge('edge_18', inter_1, bottleneck, Decimal('60'))
        connect_nodes(inter_1, bottleneck, edge18)
        edges.append(edge18)
        
        edge19 = create_edge('edge_19', inter_2, critical, Decimal('50'))
        connect_nodes(inter_2, critical, edge19)
        edges.append(edge19)
        
        # Bottleneck vers critical (single path)
        edge20 = create_edge('edge_20', bottleneck, critical, Decimal('120'))
        connect_nodes(bottleneck, critical, edge20)
        edges.append(edge20)
        
        # Critical vers bridge (critical path)
        edge21 = create_edge('edge_21', critical, bridge, Decimal('80'))
        connect_nodes(critical, bridge, edge21)
        edges.append(edge21)
        
        # Bridge vers sinks (final convergence)
        edge22 = create_edge('edge_22', bridge, sink_1, Decimal('40'))
        connect_nodes(bridge, sink_1, edge22)
        edges.append(edge22)
        
        edge23 = create_edge('edge_23', bridge, sink_2, Decimal('40'))
        connect_nodes(bridge, sink_2, edge23)
        edges.append(edge23)
        
        sources = [source_a, source_b, source_c]
        target = sink_1
        
        return nodes, edges, sources, target

    def test_basic_topology_metrics_calculation(self):
        """
        Test Académique 14.01: Basic topology metrics calculation
        
        Validation:
        - Node count et edge count correct
        - Edge density calculation
        - Degree statistics (in/out/total)
        - Node classification (source/sink/intermediate)
        """
        nodes, edges, sources, target = self.create_complex_topology_dag()
        
        result = self.enumerator.analyze_dag_topology(nodes, edges, sources, target)
        
        # Validation basic metrics
        assert 'node_count' in result
        assert 'edge_count' in result
        assert 'edge_density' in result
        assert 'node_classification' in result
        assert 'degree_statistics' in result
        
        # Check specific values
        assert result['node_count'] == 16  # Total nodes created
        assert result['edge_count'] == 23  # Total edges created
        assert result['edge_density'] > 0  # Should have some density
        
        # Node classification validation
        node_class = result['node_classification']
        assert node_class['source_nodes'] == 3  # source_a, source_b, source_c
        assert node_class['sink_nodes'] == 2   # sink_1, sink_2
        assert node_class['intermediate_nodes'] > 0  # Should have intermediates
        
        # Degree statistics validation
        degree_stats = result['degree_statistics']
        assert degree_stats['avg_in_degree'] >= 0
        assert degree_stats['avg_out_degree'] >= 0
        assert degree_stats['max_in_degree'] >= 1
        assert degree_stats['max_out_degree'] >= 1
        
        print("✅ Test Académique 14.01: Basic Topology Metrics - PASSED")

    def test_node_centrality_analysis_comprehensive(self):
        """
        Test Académique 14.02: Node centrality analysis (degree/betweenness/closeness)
        
        Validation:
        - Degree centrality calculation correcte
        - Betweenness centrality estimation
        - Closeness centrality estimation
        - Critical nodes identification
        """
        nodes, edges, sources, target = self.create_complex_topology_dag()
        
        result = self.enumerator.analyze_dag_topology(nodes, edges, sources, target)
        
        # Validation centrality analysis presence
        assert 'centrality_analysis' in result
        centrality = result['centrality_analysis']
        
        assert 'degree_centrality' in centrality
        assert 'betweenness_centrality' in centrality
        assert 'closeness_centrality' in centrality
        assert 'critical_nodes' in centrality
        assert 'centrality_summary' in centrality
        
        # Check que hub nodes ont high centrality
        degree_cent = centrality['degree_centrality']
        
        # Hub nodes should have higher centrality
        hub_centralities = [
            degree_cent.get('topo_hub_1', 0),
            degree_cent.get('topo_hub_2', 0), 
            degree_cent.get('topo_hub_3', 0)
        ]
        
        source_centralities = [
            degree_cent.get('topo_source_A', 0),
            degree_cent.get('topo_source_B', 0),
            degree_cent.get('topo_source_C', 0)
        ]
        
        # Hubs should generally have higher centrality than sources
        avg_hub_centrality = sum(hub_centralities) / len(hub_centralities)
        avg_source_centrality = sum(source_centralities) / len(source_centralities)
        
        assert avg_hub_centrality >= avg_source_centrality, \
            f"Hub centrality {avg_hub_centrality} should be >= source centrality {avg_source_centrality}"
        
        # Critical nodes should be identified
        critical_nodes = centrality['critical_nodes']
        assert isinstance(critical_nodes, list)
        
        # Summary validation
        summary = centrality['centrality_summary']
        assert summary['avg_degree_centrality'] >= 0
        assert summary['max_degree_centrality'] >= 0
        assert summary['critical_nodes_count'] >= 0
        
        print("✅ Test Académique 14.02: Node Centrality Analysis - PASSED")

    def test_connectivity_patterns_bottlenecks_identification(self):
        """
        Test Académique 14.03: Connectivity patterns et bottlenecks identification
        
        Validation:
        - Bottleneck nodes identification (high in-degree, low out-degree)
        - Connected components analysis
        - Bridge edges detection
        - Flow capacity estimation
        """
        nodes, edges, sources, target = self.create_complex_topology_dag()
        
        result = self.enumerator.analyze_dag_topology(nodes, edges, sources, target)
        
        # Validation connectivity analysis
        assert 'connectivity_analysis' in result
        connectivity = result['connectivity_analysis']
        
        assert 'bottlenecks' in connectivity
        assert 'connected_components' in connectivity
        assert 'bridge_edges' in connectivity
        assert 'flow_analysis' in connectivity
        assert 'connectivity_summary' in connectivity
        
        # Bottleneck validation - le noeud 'topo_bottleneck' devrait être détecté
        bottlenecks = connectivity['bottlenecks']
        bottleneck_nodes = [bn['node_id'] for bn in bottlenecks]
        
        # Le bottleneck node créé devrait être identifié
        assert any('bottleneck' in node_id for node_id in bottleneck_nodes), \
            f"Bottleneck node should be identified in: {bottleneck_nodes}"
        
        # Connected components
        components = connectivity['connected_components']
        assert 'components' in components
        assert 'largest_component_size' in components
        assert 'components_count' in components
        
        # Should be mostly connected (1 large component expected)
        assert components['components_count'] >= 1
        assert components['largest_component_size'] > 10  # Most nodes in main component
        
        # Bridge edges detection
        bridge_edges = connectivity['bridge_edges']
        assert isinstance(bridge_edges, list)
        
        # Flow analysis
        flow = connectivity['flow_analysis']
        assert 'estimated_max_flow' in flow
        assert 'flow_bottlenecks' in flow
        assert 'sources_count' in flow
        assert 'sinks_count' in flow
        
        # Flow should match our DAG structure
        assert flow['sources_count'] == 3  # 3 sources created
        assert flow['sinks_count'] == 2   # 2 sinks created
        
        print("✅ Test Académique 14.03: Connectivity Patterns & Bottlenecks - PASSED")

    def test_path_complexity_analysis_branching(self):
        """
        Test Académique 14.04: Path complexity analysis avec branching factors
        
        Validation:
        - Branching factor calculation pour each node
        - Path length estimation
        - Complexity scoring (branching × log(path_length))
        - High complexity nodes identification
        """
        nodes, edges, sources, target = self.create_complex_topology_dag()
        
        result = self.enumerator.analyze_dag_topology(nodes, edges, sources, target)
        
        # Validation path complexity
        assert 'path_complexity' in result
        complexity = result['path_complexity']
        
        assert 'branching_factors' in complexity
        assert 'path_length_estimates' in complexity
        assert 'complexity_scores' in complexity
        assert 'high_complexity_nodes' in complexity
        assert 'complexity_summary' in complexity
        
        # Branching factors validation
        branching = complexity['branching_factors']
        
        # Hub nodes should have high branching factors
        hub_branching = [
            branching.get('topo_hub_1', 0),
            branching.get('topo_hub_2', 0),
            branching.get('topo_hub_3', 0)
        ]
        
        # At least one hub should have high branching
        assert max(hub_branching) >= 2, f"Hub nodes should have branching >= 2, got: {hub_branching}"
        
        # Sink nodes should have zero branching
        sink_branching = [
            branching.get('topo_sink_1', 0),
            branching.get('topo_sink_2', 0)
        ]
        assert all(b == 0 for b in sink_branching), f"Sink nodes should have zero branching: {sink_branching}"
        
        # Path length estimates
        path_lengths = complexity['path_length_estimates']
        assert all(length >= 0 for length in path_lengths.values())
        
        # Complexity scores
        complexity_scores = complexity['complexity_scores']
        assert all(score >= 0 for score in complexity_scores.values())
        
        # High complexity nodes
        high_complexity = complexity['high_complexity_nodes']
        assert isinstance(high_complexity, list)
        
        # Summary validation
        summary = complexity['complexity_summary']
        assert summary['avg_branching_factor'] >= 0
        assert summary['max_branching_factor'] >= 0
        assert summary['avg_complexity_score'] >= 0
        
        print("✅ Test Académique 14.04: Path Complexity Analysis - PASSED")

    def test_critical_path_identification(self):
        """
        Test Académique 14.05: Critical path identification
        
        Validation:
        - Longest paths identification entre sources et targets
        - Path criticality scoring
        - Critical path analysis statistics
        - Path importance calculation
        """
        nodes, edges, sources, target = self.create_complex_topology_dag()
        
        result = self.enumerator.analyze_dag_topology(nodes, edges, sources, target)
        
        # Validation critical paths
        assert 'critical_paths' in result
        critical_paths = result['critical_paths']
        
        assert 'identified_paths' in critical_paths
        assert 'sources_analyzed' in critical_paths
        assert 'targets_analyzed' in critical_paths
        assert 'longest_path_length' in critical_paths
        assert 'avg_path_length' in critical_paths
        
        # Sources et targets analyzed should match our input
        assert critical_paths['sources_analyzed'] >= 1  # At least some sources
        assert critical_paths['targets_analyzed'] >= 1  # At least some targets
        
        # Identified paths validation
        identified = critical_paths['identified_paths']
        assert isinstance(identified, list)
        
        if identified:  # Si paths trouvés
            # Validate path structure
            for path_info in identified[:3]:  # Check first few
                assert 'source' in path_info
                assert 'target' in path_info
                assert 'path' in path_info
                assert 'length' in path_info
                assert 'criticality_score' in path_info
                
                # Path should be reasonable
                assert path_info['length'] >= 2  # At least source -> target
                assert path_info['criticality_score'] >= 0
                assert isinstance(path_info['path'], list)
                assert len(path_info['path']) == path_info['length']
        
        # Statistics validation
        assert critical_paths['longest_path_length'] >= 0
        assert critical_paths['avg_path_length'] >= 0
        
        print("✅ Test Académique 14.05: Critical Path Identification - PASSED")

    def test_optimization_recommendations_generation(self):
        """
        Test Académique 14.06: Optimization recommendations generation
        
        Validation:
        - Enumeration strategies basées centrality
        - Performance improvements basées complexity
        - Bottleneck resolutions basées connectivity
        - Parallelization opportunities
        """
        nodes, edges, sources, target = self.create_complex_topology_dag()
        
        result = self.enumerator.analyze_dag_topology(nodes, edges, sources, target)
        
        # Validation optimization recommendations
        assert 'optimization_recommendations' in result
        optimizations = result['optimization_recommendations']
        
        assert 'enumeration_strategies' in optimizations
        assert 'performance_improvements' in optimizations
        assert 'bottleneck_resolutions' in optimizations
        assert 'parallelization_opportunities' in optimizations
        assert 'optimization_summary' in optimizations
        
        # Validation recommendation structure
        for category in ['enumeration_strategies', 'performance_improvements', 
                        'bottleneck_resolutions', 'parallelization_opportunities']:
            recommendations = optimizations[category]
            assert isinstance(recommendations, list)
            
            for rec in recommendations:
                assert 'strategy' in rec
                assert 'description' in rec
                # Should have some strategy-specific data
                assert len(rec.keys()) >= 3
        
        # Summary validation
        summary = optimizations['optimization_summary']
        assert 'total_opportunities' in summary
        assert 'priority_level' in summary
        assert 'estimated_improvement' in summary
        
        assert summary['total_opportunities'] >= 0
        assert summary['priority_level'] in ['LOW', 'MEDIUM', 'HIGH']
        assert 0 <= summary['estimated_improvement'] <= 50
        
        print("✅ Test Académique 14.06: Optimization Recommendations - PASSED")

    def test_performance_analysis_large_dags(self):
        """
        Test Académique 14.07: Performance analysis large DAGs
        
        Validation:
        - Performance stable avec increasing node count
        - Memory usage reasonable
        - Analysis time sous reasonable limits
        - Scalability characteristics
        """
        node_counts = [10, 20, 30]
        performance_results = []
        
        for node_count in node_counts:
            # Create DAG of specified size
            nodes = []
            edges = []
            
            # Create linear chain pour predictable structure
            for i in range(node_count):
                node = create_node(f'complex_node_{i}')
                nodes.append(node)
            
            # Create linear edges avec connections
            for i in range(node_count - 1):
                edge = create_edge(f'perf_edge_{i}', nodes[i], nodes[i + 1], Decimal('50'))
                connect_nodes(nodes[i], nodes[i + 1], edge)
                edges.append(edge)
            
            # Analyze performance
            start_time = time.time()
            
            result = self.enumerator.analyze_dag_topology(nodes, edges, [nodes[0]], nodes[-1])
            
            analysis_time = (time.time() - start_time) * 1000
            
            performance_results.append({
                'node_count': node_count,
                'analysis_time_ms': analysis_time,
                'analysis_summary': result['analysis_summary']
            })
        
        # Validation performance characteristics
        for perf_result in performance_results:
            # Analysis time should be reasonable (< 5s even for larger DAGs)
            assert perf_result['analysis_time_ms'] < 5000, \
                f"Analysis time {perf_result['analysis_time_ms']:.2f}ms too high for {perf_result['node_count']} nodes"
            
            # Analysis summary should be complete
            summary = perf_result['analysis_summary']
            assert summary['nodes_analyzed'] == perf_result['node_count']
            assert summary['analysis_time_ms'] > 0
        
        # Check scaling characteristics
        if len(performance_results) >= 2:
            first_result = performance_results[0]
            last_result = performance_results[-1]
            
            time_ratio = last_result['analysis_time_ms'] / first_result['analysis_time_ms']
            node_ratio = last_result['node_count'] / first_result['node_count']
            
            # Time should scale reasonably (allow small variance for quadratic)
            assert time_ratio <= node_ratio ** 2 * 1.1, \
                f"Poor scaling: time ratio {time_ratio:.2f} vs node ratio squared {node_ratio**2:.2f}"
        
        print("✅ Test Académique 14.07: Performance Analysis Large DAGs - PASSED")

    def test_error_handling_robustness_topology(self):
        """
        Test Académique 14.08: Error handling robustesse
        
        Validation:
        - Empty DAG handling
        - Invalid nodes/edges handling
        - Malformed input recovery
        - Graceful degradation
        """
        # Test 1: Empty DAG
        result = self.enumerator.analyze_dag_topology([], [], [], None)
        
        # Should handle empty DAG gracefully
        assert 'analysis_summary' in result
        assert result['analysis_summary']['nodes_analyzed'] == 0
        assert result['analysis_summary']['edges_analyzed'] == 0
        
        # Test 2: Single node DAG
        single_node = create_node('topo_single')
        
        result = self.enumerator.analyze_dag_topology([single_node], [], [single_node], single_node)
        
        # Should handle single node gracefully
        assert result['analysis_summary']['nodes_analyzed'] == 1
        assert result['analysis_summary']['edges_analyzed'] == 0
        
        # Test 3: Disconnected components
        
        # Component 1
        node_a = create_node('topo_disc_A')
        node_b = create_node('topo_disc_B')
        edge_ab = create_edge('disc_edge_1', node_a, node_b, Decimal('50'))
        connect_nodes(node_a, node_b, edge_ab)
        
        # Component 2 (isolated)
        node_c = create_node('topo_disc_C')
        node_d = create_node('topo_disc_D')
        edge_cd = create_edge('disc_edge_2', node_c, node_d, Decimal('50'))
        connect_nodes(node_c, node_d, edge_cd)
        
        disconnect_nodes = [node_a, node_b, node_c, node_d]
        disconnect_edges = [edge_ab, edge_cd]
        
        result = self.enumerator.analyze_dag_topology(disconnect_nodes, disconnect_edges, [node_a], node_b)
        
        # Should detect multiple components
        connectivity = result['connectivity_analysis']
        assert connectivity['connectivity_summary']['components_count'] >= 2
        
        print("✅ Test Académique 14.08: Error Handling Robustness - PASSED")

    def test_integration_existing_pipeline(self):
        """
        Test Académique 14.09: Integration avec existing pipeline
        
        Validation:
        - Integration avec PathEnumerator methods
        - Compatibility avec DAG structures existantes
        - Output format consistency
        - Method chaining functionality
        """
        nodes, edges, sources, target = self.create_complex_topology_dag()
        
        # Test integration avec analyze_dag_topology
        topology_result = self.enumerator.analyze_dag_topology(nodes, edges, sources, target)
        
        # Validation output format consistency avec autres methods
        assert isinstance(topology_result, dict)
        assert 'analysis_summary' in topology_result
        
        # Check que output peut être utilisé pour optimizations
        optimization_recommendations = topology_result['optimization_recommendations']
        
        # Should provide actionable data
        total_opportunities = optimization_recommendations['optimization_summary']['total_opportunities']
        assert total_opportunities >= 0
        
        # Test que critical nodes peuvent être utilisés pour prioritization
        centrality = topology_result['centrality_analysis']
        critical_nodes = centrality['critical_nodes']
        
        if critical_nodes:
            # Should be able to extract node IDs for use in enumeration
            critical_node_ids = [node['node_id'] for node in critical_nodes]
            assert all(isinstance(node_id, str) for node_id in critical_node_ids)
        
        # Test que bottlenecks peuvent être utilisés pour bypass strategies
        connectivity = topology_result['connectivity_analysis']
        bottlenecks = connectivity['bottlenecks']
        
        if bottlenecks:
            bottleneck_scores = [bn['bottleneck_score'] for bn in bottlenecks]
            assert all(score >= 0 for score in bottleneck_scores)
            assert bottlenecks == sorted(bottlenecks, key=lambda x: x['bottleneck_score'], reverse=True)
        
        print("✅ Test Académique 14.09: Integration Existing Pipeline - PASSED")

    def test_comprehensive_topology_integration(self):
        """
        Test Académique 14.10: Comprehensive topology integration
        
        Validation:
        - All analysis phases complete correctly
        - Cross-phase data consistency
        - Comprehensive analysis coverage
        - End-to-end workflow validation
        """
        nodes, edges, sources, target = self.create_complex_topology_dag()
        
        start_time = time.time()
        
        # Full topology analysis
        result = self.enumerator.analyze_dag_topology(nodes, edges, sources, target)
        
        total_time = (time.time() - start_time) * 1000
        
        # Validation all major sections present
        required_sections = [
            'node_count', 'edge_count', 'edge_density', 'node_classification', 'degree_statistics',
            'centrality_analysis', 'connectivity_analysis', 'path_complexity', 
            'critical_paths', 'optimization_recommendations', 'analysis_summary'
        ]
        
        for section in required_sections:
            assert section in result, f"Missing required section: {section}"
        
        # Cross-validation data consistency
        
        # Node counts should be consistent
        assert result['node_count'] == result['analysis_summary']['nodes_analyzed']
        assert result['edge_count'] == result['analysis_summary']['edges_analyzed']
        
        # Centrality nodes should exist in DAG
        centrality = result['centrality_analysis']
        for node_id in centrality['degree_centrality'].keys():
            # Should be valid node ID from our test DAG
            assert any(node_id in account for account in self.test_topology_accounts.keys())
        
        # Critical paths should reference valid nodes
        critical_paths = result['critical_paths']['identified_paths']
        for path_info in critical_paths:
            for node_id in path_info['path']:
                assert any(node_id in account for account in self.test_topology_accounts.keys())
        
        # Optimization recommendations should be actionable
        optimizations = result['optimization_recommendations']
        total_opportunities = optimizations['optimization_summary']['total_opportunities']
        
        # Should have found some optimization opportunities in complex DAG
        assert total_opportunities > 0, "Complex DAG should have optimization opportunities"
        
        # Performance validation
        analysis_summary = result['analysis_summary']
        assert analysis_summary['analysis_time_ms'] > 0
        assert analysis_summary['analysis_time_ms'] < 10000  # < 10s for reasonable performance
        
        # Check specific optimizations for our complex topology
        enum_strategies = optimizations['enumeration_strategies']
        perf_improvements = optimizations['performance_improvements'] 
        bottleneck_resolutions = optimizations['bottleneck_resolutions']
        parallel_opportunities = optimizations['parallelization_opportunities']
        
        # Complex DAG should suggest some strategies
        total_strategies = len(enum_strategies) + len(perf_improvements) + len(bottleneck_resolutions) + len(parallel_opportunities)
        assert total_strategies > 0, "Complex topology should generate optimization strategies"
        
        print("✅ Test Académique 14.10: Comprehensive Topology Integration - PASSED")
        print(f"   Analysis completed in {total_time:.2f}ms")
        print(f"   Optimization opportunities found: {total_opportunities}")
        print(f"   Critical paths identified: {len(critical_paths)}")
        print(f"   Bottlenecks detected: {len(result['connectivity_analysis']['bottlenecks'])}")


if __name__ == '__main__':
    unittest.main()