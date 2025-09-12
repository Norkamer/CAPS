"""
Test Académique 08 - DAG Structures Fondamentales

Tests rigoureux des structures DAG core selon blueprint ICGS:
- Invariants mathématiques validation topologique
- Robustesse cycle detection algorithme DFS  
- Précision weights Decimal pour stabilité numérique
- Connectivité preservation sous modifications

Invariants testés:
1. Cycle Detection Robustness: DFS O(V+E) exhaustif
2. Node Connectivity Preservation: Invariants sous add/remove
3. Edge Weights Decimal Precision: Stabilité numérique
4. Topological Integrity: Validation coherence structure
"""

import pytest
import time
import uuid
from decimal import Decimal, getcontext
from typing import List, Dict, Set, Optional

# Configuration précision Decimal pour tests
getcontext().prec = 50

# Import modules ICGS
from icgs_core.dag_structures import (
    Node, Edge, NodeType, EdgeType, EdgeMetadata,
    CycleDetectionResult, AntiCycleValidator,
    create_node, create_edge, connect_nodes, disconnect_nodes,
    validate_dag_topology
)


class TestAcademicDAGStructures:
    """Suite tests académiques structures DAG fondamentales"""
    
    def setup_method(self):
        """Setup avant chaque test"""
        self.validator = AntiCycleValidator()
        self.test_start_time = time.time()
    
    def teardown_method(self):
        """Teardown après chaque test"""
        test_duration = time.time() - self.test_start_time
        if test_duration > 1.0:  # Alert si test > 1 seconde
            pytest.fail(f"Test performance degradation: {test_duration:.3f}s > 1.0s limit")
    
    # ========================================
    # INVARIANT 1: Cycle Detection Robustness
    # ========================================
    
    def test_invariant_cycle_detection_dfs_correctness(self):
        """
        Test Invariant 1.1: Algorithme DFS détection cycles correctness
        
        Validation:
        - Détection cycles simples (A->B->C->A)
        - Détection cycles complexes multi-branche  
        - Absence faux positifs sur DAG valides
        - Complexité O(V+E) respectée
        """
        # Test 1: Cycle simple 3-nodes
        nodes = [create_node(f"N{i}") for i in range(3)]
        edges = [
            create_edge("E01", nodes[0], nodes[1]),
            create_edge("E12", nodes[1], nodes[2]), 
            create_edge("E20", nodes[2], nodes[0])  # Cycle
        ]
        
        # Connection DAG avec cycle
        for edge in edges:
            connect_nodes(edge.source_node, edge.target_node, edge)
        
        result = self.validator.validate_no_cycles(nodes)
        assert result.has_cycle == True
        assert len(result.cycle_path) == 4  # A->B->C->A
        assert result.cycle_path[0] == result.cycle_path[-1]  # Fermeture cycle
        
        # Test 2: DAG valide sans cycle
        valid_nodes = [create_node(f"V{i}") for i in range(4)]
        valid_edges = [
            create_edge("VE01", valid_nodes[0], valid_nodes[1]),
            create_edge("VE02", valid_nodes[0], valid_nodes[2]),
            create_edge("VE13", valid_nodes[1], valid_nodes[3]),
            create_edge("VE23", valid_nodes[2], valid_nodes[3])
        ]
        
        for edge in valid_edges:
            connect_nodes(edge.source_node, edge.target_node, edge)
            
        valid_result = self.validator.validate_no_cycles(valid_nodes)
        assert valid_result.has_cycle == False
        assert len(valid_result.cycle_path) == 0
        
        # Test 3: Cycle complexe multi-branche
        complex_nodes = [create_node(f"C{i}") for i in range(5)]
        complex_edges = [
            create_edge("CE01", complex_nodes[0], complex_nodes[1]),
            create_edge("CE12", complex_nodes[1], complex_nodes[2]),
            create_edge("CE23", complex_nodes[2], complex_nodes[3]),
            create_edge("CE34", complex_nodes[3], complex_nodes[4]),
            create_edge("CE41", complex_nodes[4], complex_nodes[1]),  # Cycle 1->2->3->4->1
            create_edge("CE02", complex_nodes[0], complex_nodes[2])   # Branch additionnelle
        ]
        
        for edge in complex_edges:
            connect_nodes(edge.source_node, edge.target_node, edge)
            
        complex_result = self.validator.validate_no_cycles(complex_nodes)
        assert complex_result.has_cycle == True
        
        # Validation performance O(V+E)
        stats = self.validator.get_validation_stats()
        assert stats['validations_performed'] == 3
        assert stats['cycles_detected'] == 2
    
    def test_invariant_cycle_detection_edge_cases_robustness(self):
        """
        Test Invariant 1.2: Robustesse edge cases cycle detection
        
        Edge cases:
        - Self-loops (interdits)
        - Nodes isolés  
        - DAG vide
        - Composants disconnectés avec/sans cycles
        """
        # Test 1: Self-loops interdits
        node = create_node("SelfLoop")
        with pytest.raises(ValueError, match="Self-loops not allowed"):
            create_edge("SelfEdge", node, node)
        
        # Test 2: DAG vide
        empty_result = self.validator.validate_no_cycles([])
        assert empty_result.has_cycle == False
        
        # Test 3: Nodes isolés
        isolated_nodes = [create_node(f"I{i}") for i in range(3)]
        isolated_result = self.validator.validate_no_cycles(isolated_nodes)
        assert isolated_result.has_cycle == False
        
        for node in isolated_nodes:
            assert node.get_node_type() == NodeType.ISOLATED
        
        # Test 4: Composants disconnectés - un avec cycle, un sans
        # Composant 1: Sans cycle
        comp1_nodes = [create_node(f"Comp1_{i}") for i in range(2)]
        comp1_edge = create_edge("Comp1_E", comp1_nodes[0], comp1_nodes[1])
        connect_nodes(comp1_edge.source_node, comp1_edge.target_node, comp1_edge)
        
        # Composant 2: Avec cycle
        comp2_nodes = [create_node(f"Comp2_{i}") for i in range(3)]
        comp2_edges = [
            create_edge("Comp2_E01", comp2_nodes[0], comp2_nodes[1]),
            create_edge("Comp2_E12", comp2_nodes[1], comp2_nodes[2]),
            create_edge("Comp2_E20", comp2_nodes[2], comp2_nodes[0])
        ]
        for edge in comp2_edges:
            connect_nodes(edge.source_node, edge.target_node, edge)
        
        all_nodes = comp1_nodes + comp2_nodes
        mixed_result = self.validator.validate_no_cycles(all_nodes)
        assert mixed_result.has_cycle == True  # Cycle détecté dans composant 2
    
    def test_invariant_cycle_detection_performance_complexity(self):
        """
        Test Invariant 1.3: Performance cycle detection O(V+E)
        
        Validation:
        - Temps exécution linéaire avec taille DAG
        - Mémoire usage O(V) pour coloration
        - Statistiques tracking accuracy
        """
        # Construction DAG taille croissante
        dag_sizes = [10, 50, 100]
        performance_results = []
        
        for size in dag_sizes:
            # DAG linéaire sans cycle (worst case pour DFS)
            nodes = [create_node(f"Perf{size}_{i}") for i in range(size)]
            edges = []
            
            # Chain linéaire: 0->1->2->...->n-1
            for i in range(size - 1):
                edge = create_edge(f"PerfE{size}_{i}", nodes[i], nodes[i + 1])
                edges.append(edge)
                connect_nodes(edge.source_node, edge.target_node, edge)
            
            # Mesure performance
            start_time = time.time()
            result = self.validator.validate_no_cycles(nodes)
            end_time = time.time()
            
            performance_results.append({
                'size': size,
                'time_ms': (end_time - start_time) * 1000,
                'has_cycle': result.has_cycle
            })
            
            assert result.has_cycle == False  # DAG linéaire valide
        
        # Validation complexité roughly linear
        # Note: Pour tests petits, overhead dominant, mais trend doit être reasonable
        max_time_ms = max(r['time_ms'] for r in performance_results)
        assert max_time_ms < 100  # Moins de 100ms pour DAG 100 nodes
        
        # Validation stats tracking
        stats = self.validator.get_validation_stats()
        assert stats['max_dfs_depth'] >= dag_sizes[-1] - 1  # Profondeur ≈ taille DAG linéaire
    
    # ===============================================
    # INVARIANT 2: Node Connectivity Preservation  
    # ===============================================
    
    def test_invariant_node_connectivity_add_remove_preservation(self):
        """
        Test Invariant 2.1: Preservation connectivité sous add/remove edges
        
        Validation:
        - Node type classification dynamique correcte
        - Incoming/outgoing counts coherence
        - Cache invalidation proper
        - Bidirectional connectivity maintenance
        """
        # Setup nodes initial
        source = create_node("Source")
        intermediate = create_node("Intermediate")
        sink = create_node("Sink")
        
        # État initial: nodes isolés
        assert source.get_node_type() == NodeType.ISOLATED
        assert intermediate.get_node_type() == NodeType.ISOLATED  
        assert sink.get_node_type() == NodeType.ISOLATED
        
        # Ajout première edge: Source -> Intermediate
        edge1 = create_edge("E_SI", source, intermediate)
        connect_nodes(edge1.source_node, edge1.target_node, edge1)
        
        # Validation types après connection
        assert source.get_node_type() == NodeType.SOURCE
        assert intermediate.get_node_type() == NodeType.SINK
        assert sink.get_node_type() == NodeType.ISOLATED
        
        # Validation counts
        assert len(source.outgoing_edges) == 1
        assert len(source.incoming_edges) == 0
        assert len(intermediate.incoming_edges) == 1
        assert len(intermediate.outgoing_edges) == 0
        
        # Ajout deuxième edge: Intermediate -> Sink
        edge2 = create_edge("E_IS", intermediate, sink)
        connect_nodes(edge2.source_node, edge2.target_node, edge2)
        
        # Validation types après deuxième connection
        assert source.get_node_type() == NodeType.SOURCE
        assert intermediate.get_node_type() == NodeType.INTERMEDIATE
        assert sink.get_node_type() == NodeType.SINK
        
        # Test disconnection
        disconnected_edge = disconnect_nodes(source, intermediate, "E_SI")
        assert disconnected_edge == edge1
        
        # Validation types après disconnection
        assert source.get_node_type() == NodeType.ISOLATED
        assert intermediate.get_node_type() == NodeType.SOURCE  # Devient source
        assert sink.get_node_type() == NodeType.SINK
        
        # Validation counts après disconnection
        assert len(source.outgoing_edges) == 0
        assert len(intermediate.incoming_edges) == 0
        assert len(intermediate.outgoing_edges) == 1
    
    def test_invariant_node_connectivity_statistics_coherence(self):
        """
        Test Invariant 2.2: Cohérence statistiques connectivité
        
        Validation:
        - Statistics accuracy avec état réel
        - Cache performance effective
        - Memory management sous modifications
        """
        # Setup DAG complexe
        nodes = [create_node(f"Stat{i}") for i in range(6)]
        edges = [
            create_edge("SE01", nodes[0], nodes[1]),
            create_edge("SE02", nodes[0], nodes[2]),
            create_edge("SE12", nodes[1], nodes[2]),
            create_edge("SE23", nodes[2], nodes[3]),
            create_edge("SE34", nodes[3], nodes[4]),
            create_edge("SE35", nodes[3], nodes[5])
        ]
        
        for edge in edges:
            connect_nodes(edge.source_node, edge.target_node, edge)
        
        # Validation statistiques détaillées
        stats = []
        for node in nodes:
            node_stats = node.get_connectivity_stats()
            stats.append(node_stats)
            
            # Validation coherence counts
            actual_incoming = len(node.incoming_edges)
            actual_outgoing = len(node.outgoing_edges)
            
            assert node_stats['incoming_count'] == actual_incoming
            assert node_stats['outgoing_count'] == actual_outgoing
            assert node_stats['total_degree'] == actual_incoming + actual_outgoing
        
        # Validation types spécifiques
        assert nodes[0].get_node_type() == NodeType.SOURCE      # Pas d'incoming
        assert nodes[4].get_node_type() == NodeType.SINK        # Pas d'outgoing
        assert nodes[5].get_node_type() == NodeType.SINK        # Pas d'outgoing
        assert nodes[1].get_node_type() == NodeType.INTERMEDIATE # Both directions
        assert nodes[2].get_node_type() == NodeType.INTERMEDIATE
        assert nodes[3].get_node_type() == NodeType.INTERMEDIATE
        
        # Test cache invalidation performance
        cache_test_iterations = 100
        start_time = time.time()
        
        for _ in range(cache_test_iterations):
            _ = nodes[2].get_node_type()  # Should hit cache
        
        cache_time = time.time() - start_time
        
        # Re-invalidation cache
        dummy_edge = create_edge("CacheTest", nodes[2], nodes[4])
        connect_nodes(dummy_edge.source_node, dummy_edge.target_node, dummy_edge)
        
        start_time = time.time()
        _ = nodes[2].get_node_type()  # Should recompute
        recompute_time = time.time() - start_time
        
        # Cache doit être plus rapide que recompute (dans général)
        # Mais pour tests simples, différence peut être négligeable
        assert cache_time < 0.1  # Cache iterations < 100ms total
        assert recompute_time < 0.1  # Single recompute < 100ms
    
    # ==========================================
    # INVARIANT 3: Edge Weights Decimal Precision
    # ==========================================
    
    def test_invariant_edge_weights_decimal_precision_stability(self):
        """
        Test Invariant 3.1: Stabilité précision Decimal weights
        
        Validation:
        - Précision Decimal preservée sous opérations
        - Conversion types robuste (float, int, str -> Decimal)
        - Arithmetic operations stabilité
        - Negative weights validation
        """
        node1 = create_node("DecimalTest1")
        node2 = create_node("DecimalTest2")
        
        # Test 1: Précision Decimal haute précision
        high_precision_weight = Decimal('1.23456789012345678901234567890')
        edge_decimal = create_edge("EdgeDecimal", node1, node2, high_precision_weight)
        
        assert edge_decimal.get_weight() == high_precision_weight
        assert isinstance(edge_decimal.get_weight(), Decimal)
        assert str(edge_decimal.get_weight()) == '1.23456789012345678901234567890'
        
        # Test 2: Conversion float -> Decimal
        float_weight = 3.14159265359
        edge_float = create_edge("EdgeFloat", node1, node2, float_weight)
        
        # Conversion doit préserver précision raisonnable
        assert isinstance(edge_float.get_weight(), Decimal)
        converted_weight = edge_float.get_weight()
        assert abs(float(converted_weight) - float_weight) < 1e-10
        
        # Test 3: Conversion str -> Decimal
        str_weight = "2.71828182845904523536"
        edge_str = create_edge("EdgeStr", node1, node2, str_weight)
        
        assert isinstance(edge_str.get_weight(), Decimal)
        assert str(edge_str.get_weight()) == str_weight
        
        # Test 4: Conversion int -> Decimal
        int_weight = 42
        edge_int = create_edge("EdgeInt", node1, node2, int_weight)
        
        assert isinstance(edge_int.get_weight(), Decimal)
        assert edge_int.get_weight() == Decimal('42')
        
        # Test 5: Weights négatifs interdits
        with pytest.raises(ValueError, match="must be non-negative"):
            create_edge("EdgeNegative", node1, node2, Decimal('-1.0'))
        
        with pytest.raises(ValueError, match="must be non-negative"):
            create_edge("EdgeNegativeFloat", node1, node2, -2.5)
    
    def test_invariant_edge_weights_arithmetic_stability(self):
        """
        Test Invariant 3.2: Stabilité arithmétique weights Decimal
        
        Validation:
        - Opérations arithmétiques précision préservée
        - Update weights robustesse
        - Overflow/underflow handling
        """
        node1 = create_node("ArithTest1")
        node2 = create_node("ArithTest2")
        
        # Test arithmetic précision
        weight1 = Decimal('0.1')
        weight2 = Decimal('0.2')
        expected_sum = Decimal('0.3')
        
        edge1 = create_edge("EdgeArith1", node1, node2, weight1)
        edge2 = create_edge("EdgeArith2", node1, node2, weight2)
        
        # Somme précise (évite problème 0.1 + 0.2 ≠ 0.3 des floats)
        actual_sum = edge1.get_weight() + edge2.get_weight()
        assert actual_sum == expected_sum
        assert str(actual_sum) == '0.3'
        
        # Test update weight
        edge1.update_weight(Decimal('1.5'))
        assert edge1.get_weight() == Decimal('1.5')
        assert edge1.edge_metadata.weight == Decimal('1.5')  # Coherence metadata
        
        # Test update avec conversion
        edge1.update_weight('2.75')
        assert edge1.get_weight() == Decimal('2.75')
        
        # Update weight négatif interdit
        with pytest.raises(ValueError, match="must be non-negative"):
            edge1.update_weight(-1.0)
        
        # Test very large numbers (dans limites Decimal précision)
        large_weight = Decimal('9' * 40)  # 40 digits
        edge_large = create_edge("EdgeLarge", node1, node2, large_weight)
        assert edge_large.get_weight() == large_weight
    
    # =========================================
    # INVARIANT 4: Topological Integrity
    # =========================================
    
    def test_invariant_topological_integrity_validation(self):
        """
        Test Invariant 4.1: Intégrité validation topologique complète
        
        Validation:
        - Bijection edges ↔ node connections
        - Coherence source/target references  
        - Metadata consistency
        - UUID uniqueness
        """
        # Setup DAG complexe pour tests intégrité
        nodes = [create_node(f"Topo{i}") for i in range(4)]
        edges = [
            create_edge("TE01", nodes[0], nodes[1], Decimal('1.1')),
            create_edge("TE12", nodes[1], nodes[2], Decimal('2.2')),
            create_edge("TE23", nodes[2], nodes[3], Decimal('3.3')),
            create_edge("TE02", nodes[0], nodes[2], Decimal('0.5'))  # Shortcut
        ]
        
        for edge in edges:
            connect_nodes(edge.source_node, edge.target_node, edge)
        
        # Validation 1: Bijection edges ↔ connections
        for edge in edges:
            source_has_edge = edge.edge_id in edge.source_node.outgoing_edges
            target_has_edge = edge.edge_id in edge.target_node.incoming_edges
            
            assert source_has_edge, f"Source node missing outgoing edge {edge.edge_id}"
            assert target_has_edge, f"Target node missing incoming edge {edge.edge_id}"
            
            # References coherence
            source_edge_ref = edge.source_node.outgoing_edges[edge.edge_id]
            target_edge_ref = edge.target_node.incoming_edges[edge.edge_id]
            
            assert source_edge_ref == edge
            assert target_edge_ref == edge
            assert source_edge_ref.target_node == edge.target_node
            assert target_edge_ref.source_node == edge.source_node
        
        # Validation 2: UUID uniqueness
        all_node_uuids = [node.uuid for node in nodes]
        all_edge_uuids = [edge.uuid for edge in edges]
        
        assert len(set(all_node_uuids)) == len(all_node_uuids)  # Tous différents
        assert len(set(all_edge_uuids)) == len(all_edge_uuids)  # Tous différents
        
        # Validation 3: Metadata consistency
        for edge in edges:
            assert edge.edge_metadata.weight == edge.weight
            assert edge.edge_metadata.edge_type == EdgeType.STRUCTURAL  # Default
            assert abs(edge.edge_metadata.created_at - edge.created_at) < 1  # ≈ Same time
        
        # Validation 4: DAG integrity complet
        topology_result = validate_dag_topology(nodes)
        assert topology_result.has_cycle == False
    
    def test_invariant_topological_integrity_factory_functions(self):
        """
        Test Invariant 4.2: Robustesse factory functions
        
        Validation:
        - create_node/create_edge validation
        - connect_nodes/disconnect_nodes coherence
        - Error handling edge cases
        """
        # Test 1: create_node validation
        valid_node = create_node("ValidNode", {"test": "metadata"})
        assert valid_node.node_id == "ValidNode"
        assert valid_node.metadata["test"] == "metadata"
        assert valid_node.get_node_type() == NodeType.ISOLATED
        
        # Node ID empty interdit
        with pytest.raises(ValueError, match="cannot be empty"):
            create_node("")
        
        with pytest.raises(ValueError, match="cannot be empty"):
            create_node("   ")  # Whitespace only
        
        # Test 2: create_edge validation
        node1 = create_node("FactoryNode1")
        node2 = create_node("FactoryNode2")
        
        valid_edge = create_edge("ValidEdge", node1, node2, "1.5", EdgeType.TRANSACTION)
        assert valid_edge.edge_id == "ValidEdge"
        assert valid_edge.source_node == node1
        assert valid_edge.target_node == node2
        assert valid_edge.get_weight() == Decimal('1.5')
        assert valid_edge.edge_metadata.edge_type == EdgeType.TRANSACTION
        
        # Edge ID empty interdit
        with pytest.raises(ValueError, match="cannot be empty"):
            create_edge("", node1, node2)
        
        # Test 3: connect_nodes robustesse
        test_edge = create_edge("TestConnect", node1, node2)
        connect_nodes(test_edge.source_node, test_edge.target_node, test_edge)
        
        # Validation bidirectional connection
        assert test_edge.edge_id in node1.outgoing_edges
        assert test_edge.edge_id in node2.incoming_edges
        assert node1.outgoing_edges[test_edge.edge_id] == test_edge
        assert node2.incoming_edges[test_edge.edge_id] == test_edge
        
        # Test 4: disconnect_nodes robustesse
        disconnected = disconnect_nodes(node1, node2, test_edge.edge_id)
        assert disconnected == test_edge
        assert test_edge.edge_id not in node1.outgoing_edges
        assert test_edge.edge_id not in node2.incoming_edges
        
        # Disconnect non-existent edge
        non_existent = disconnect_nodes(node1, node2, "NonExistentEdge")
        assert non_existent is None
    
    # =====================================
    # TESTS PERFORMANCE ET ROBUSTESSE
    # =====================================
    
    def test_performance_large_dag_handling(self):
        """
        Test Performance: Handling DAG large scale
        
        Validation:
        - Performance acceptable jusqu'à 1000+ nodes
        - Memory usage stable
        - Operations O(1) pour node lookup
        """
        # Construction DAG large scale
        large_size = 500  # Reduced for test speed
        nodes = [create_node(f"Large{i}") for i in range(large_size)]
        edges = []
        
        # Tree structure pour éviter cycles (plus efficient que full mesh)
        start_time = time.time()
        
        for i in range(1, large_size):
            parent_idx = (i - 1) // 2  # Binary tree structure
            edge = create_edge(f"LargeE{parent_idx}_{i}", nodes[parent_idx], nodes[i])
            edges.append(edge)
            connect_nodes(edge.source_node, edge.target_node, edge)
        
        construction_time = time.time() - start_time
        
        # Test validation performance
        start_time = time.time()
        result = validate_dag_topology(nodes)
        validation_time = time.time() - start_time
        
        # Performance assertions
        assert construction_time < 2.0  # Construction < 2 seconds
        assert validation_time < 1.0   # Validation < 1 second
        assert result.has_cycle == False
        
        # Memory usage validation (approximative)
        total_edges_tracked = sum(len(node.incoming_edges) + len(node.outgoing_edges) 
                                 for node in nodes)
        expected_edges = 2 * len(edges)  # Chaque edge dans 2 nodes
        assert total_edges_tracked == expected_edges
    
    def test_robustness_concurrent_modifications(self):
        """
        Test Robustesse: Modifications concurrentes simulation
        
        Validation:
        - State coherence sous modifications séquentielles
        - Error handling robuste
        - Recovery après erreurs
        """
        nodes = [create_node(f"Robust{i}") for i in range(5)]
        
        # Séquence modifications complexe
        modifications = [
            ("add", create_edge("R01", nodes[0], nodes[1])),
            ("add", create_edge("R12", nodes[1], nodes[2])),
            ("add", create_edge("R23", nodes[2], nodes[3])),
            ("remove", "R12"),  # Création gap dans chain
            ("add", create_edge("R13", nodes[1], nodes[3])),  # Bypass gap
            ("add", create_edge("R34", nodes[3], nodes[4]))
        ]
        
        edges_registry = {}
        
        for action, edge_or_id in modifications:
            if action == "add":
                edge = edge_or_id
                connect_nodes(edge.source_node, edge.target_node, edge)
                edges_registry[edge.edge_id] = edge
                
                # Validation coherence après chaque add
                result = validate_dag_topology(nodes)
                assert result.has_cycle == False
                
            elif action == "remove":
                edge_id = edge_or_id
                if edge_id in edges_registry:
                    edge = edges_registry[edge_id]
                    disconnect_nodes(edge.source_node, edge.target_node, edge_id)
                    del edges_registry[edge_id]
                    
                    # Validation coherence après chaque remove
                    result = validate_dag_topology(nodes)
                    assert result.has_cycle == False
        
        # Final state validation
        final_result = validate_dag_topology(nodes)
        assert final_result.has_cycle == False
        
        # Validation final connectivity
        assert nodes[0].get_node_type() == NodeType.SOURCE
        assert nodes[4].get_node_type() == NodeType.SINK
        
        # Path 0->1->3->4 doit exister
        assert "R01" in nodes[0].outgoing_edges
        assert "R13" in nodes[1].outgoing_edges  
        assert "R34" in nodes[3].outgoing_edges
    
    def test_comprehensive_dag_structures_integration(self):
        """
        Test Intégration: Validation complète tous composants ensemble
        
        Validation finale:
        - Tous invariants préservés simultaneously
        - Performance acceptable ensemble
        - Robustesse edge cases combinés
        """
        # Scenario complexe intégré
        scenario_nodes = [create_node(f"Integration{i}", {"role": f"role_{i}"}) for i in range(6)]
        
        # DAG structure: Multi-source, multi-sink avec branches
        scenario_edges = [
            create_edge("I01", scenario_nodes[0], scenario_nodes[2], Decimal('1.0')),
            create_edge("I12", scenario_nodes[1], scenario_nodes[2], Decimal('2.0')),  # Multi-source vers 2
            create_edge("I23", scenario_nodes[2], scenario_nodes[3], Decimal('3.0')),
            create_edge("I34", scenario_nodes[3], scenario_nodes[4], Decimal('4.0')),
            create_edge("I35", scenario_nodes[3], scenario_nodes[5], Decimal('5.0'))   # Multi-sink depuis 3
        ]
        
        # Construction avec validation step-by-step
        validator_stats_before = self.validator.get_validation_stats()
        
        for edge in scenario_edges:
            connect_nodes(edge.source_node, edge.target_node, edge)
            
            # Validation intégrité après chaque edge avec le même validator
            result = self.validator.validate_no_cycles(scenario_nodes)
            assert result.has_cycle == False
            
            # Validation weights précision
            assert isinstance(edge.get_weight(), Decimal)
            assert edge.get_weight() > 0
        
        # Validation finale types
        expected_types = {
            0: NodeType.SOURCE,      # Pas d'incoming
            1: NodeType.SOURCE,      # Pas d'incoming  
            2: NodeType.INTERMEDIATE, # Multi-incoming, 1 outgoing
            3: NodeType.INTERMEDIATE, # 1 incoming, multi-outgoing
            4: NodeType.SINK,        # Pas d'outgoing
            5: NodeType.SINK         # Pas d'outgoing
        }
        
        for i, expected_type in expected_types.items():
            assert scenario_nodes[i].get_node_type() == expected_type
        
        # Validation statistiques finales
        validator_stats_after = self.validator.get_validation_stats()
        validations_performed = validator_stats_after['validations_performed'] - validator_stats_before['validations_performed']
        assert validations_performed == len(scenario_edges)
        assert validator_stats_after['cycles_detected'] == validator_stats_before['cycles_detected']
        
        # Performance intégration complète < 100ms
        start_time = time.time()
        final_result = self.validator.validate_no_cycles(scenario_nodes)
        integration_time = time.time() - start_time
        
        assert integration_time < 0.1  # < 100ms
        assert final_result.has_cycle == False
        
        print(f"\n🎯 DAG Structures Integration Success:")
        print(f"   - Nodes: {len(scenario_nodes)}")
        print(f"   - Edges: {len(scenario_edges)}")  
        print(f"   - Validation time: {integration_time*1000:.2f}ms")
        print(f"   - Validator stats: {self.validator.get_validation_stats()}")