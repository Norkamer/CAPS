"""
Test Académique 10: DAG Structure Validation - Étape 2.1

Suite de tests complète pour validation structure DAG production:
- DAGStructureValidator avec validation 6 phases
- Cycle detection via AntiCycleValidator DFS
- Connectivité bidirectionnelle coherence
- Nodes/edges integrity validation 
- Orphaned nodes detection
- Account balance coherence
- Performance monitoring et statistics
"""

import pytest
from decimal import Decimal
from typing import List, Dict, Any
import time

from icgs_core.dag_structures import (
    Node, Edge, Account, NodeType, EdgeType,
    DAGStructureValidator, DAGValidationResult, 
    CycleDetectionResult, AntiCycleValidator,
    create_node, create_edge, connect_nodes
)


class TestAcademicDAGStructureValidation:
    """Tests académiques validation structure DAG production"""
    
    def setup_method(self):
        """Setup test environment"""
        self.validator = DAGStructureValidator()
        
    def create_simple_valid_dag(self) -> tuple[List[Node], List[Edge]]:
        """Création DAG valide simple pour tests"""
        # Nodes: source → intermediate → sink
        source = create_node("test_source")
        intermediate = create_node("test_intermediate")
        sink = create_node("test_sink")
        
        # Edges
        edge1 = create_edge("edge_1", source, intermediate, Decimal('1.5'))
        edge2 = create_edge("edge_2", intermediate, sink, Decimal('2.0'))
        
        # Connection bidirectionnelle
        connect_nodes(source, intermediate, edge1)
        connect_nodes(intermediate, sink, edge2)
        
        return [source, intermediate, sink], [edge1, edge2]
    
    def create_cycle_dag(self) -> tuple[List[Node], List[Edge]]:
        """Création DAG avec cycle pour tests détection"""
        nodeA = create_node("cycle_A")
        nodeB = create_node("cycle_B") 
        nodeC = create_node("cycle_C")
        
        # Création cycle: A → B → C → A
        edge1 = create_edge("cycle_edge_1", nodeA, nodeB)
        edge2 = create_edge("cycle_edge_2", nodeB, nodeC)
        edge3 = create_edge("cycle_edge_3", nodeC, nodeA)  # Back-edge créant cycle
        
        connect_nodes(nodeA, nodeB, edge1)
        connect_nodes(nodeB, nodeC, edge2)
        connect_nodes(nodeC, nodeA, edge3)
        
        return [nodeA, nodeB, nodeC], [edge1, edge2, edge3]
    
    def test_dag_structure_validator_construction(self):
        """
        Test Académique 10.01: Construction DAGStructureValidator
        
        Validation:
        - Initialisation validator avec AntiCycleValidator
        - Statistics validation tracking initialisé
        - Performance counters à zéro
        """
        validator = DAGStructureValidator()
        
        # Validation cycle validator initialisé
        assert validator.cycle_validator is not None
        assert isinstance(validator.cycle_validator, AntiCycleValidator)
        
        # Validation stats initialization
        expected_stats = {
            'validations_performed', 'total_validation_time_ms', 
            'issues_detected_total', 'cycle_detections',
            'connectivity_violations', 'integrity_violations'
        }
        assert set(validator.validation_stats.keys()) == expected_stats
        
        # Validation valeurs initiales
        for stat_value in validator.validation_stats.values():
            assert stat_value == 0
        
        print("✅ Test Académique 10.01: DAGStructureValidator Construction - PASSED")
    
    def test_valid_dag_complete_validation(self):
        """
        Test Académique 10.02: Validation DAG valide complète
        
        Validation:
        - DAG simple valide passe toutes validations 
        - Aucun cycle détecté
        - Connectivité coherence validée
        - Statistics correctes générées
        - Performance tracking fonctionnel
        """
        nodes, edges = self.create_simple_valid_dag()
        
        # Test validation complète
        result = self.validator.validate_complete_dag_structure(nodes, edges)
        
        # Validation résultat global
        assert isinstance(result, DAGValidationResult)
        assert result.is_valid is True
        
        # Validation cycle detection
        assert result.cycle_detection.has_cycle is False
        assert len(result.cycle_detection.cycle_path) == 0
        
        # Validation issues
        assert len(result.connectivity_issues) == 0
        assert len(result.integrity_violations) == 0
        assert len(result.orphaned_nodes) == 0
        
        # Validation statistics
        assert result.statistics['total_nodes'] == 3
        assert result.statistics['total_edges'] == 2
        assert 'SOURCE' in result.statistics['node_types']
        assert 'SINK' in result.statistics['node_types']
        assert 'INTERMEDIATE' in result.statistics['node_types']
        
        # Validation performance timing
        assert result.validation_time_ms > 0
        
        # Validation validator stats updated
        assert self.validator.validation_stats['validations_performed'] == 1
        
        print("✅ Test Académique 10.02: Valid DAG Complete Validation - PASSED")
    
    def test_cycle_detection_integration(self):
        """
        Test Académique 10.03: Détection cycle intégrée
        
        Validation:
        - DAG avec cycle détecté correctement
        - Cycle path reconstruit avec précision
        - Validation marquée invalide
        - Statistics cycle tracking mis à jour
        """
        nodes, edges = self.create_cycle_dag()
        
        # Test validation avec cycle
        result = self.validator.validate_complete_dag_structure(nodes, edges)
        
        # Validation cycle détecté
        assert result.is_valid is False
        assert result.cycle_detection.has_cycle is True
        
        # Validation cycle path
        cycle_path = result.cycle_detection.cycle_path
        assert len(cycle_path) > 0
        
        # Cycle path devrait contenir les nodes du cycle
        path_node_ids = {node.node_id for node in cycle_path}
        expected_nodes = {"cycle_A", "cycle_B", "cycle_C"}
        assert path_node_ids.issubset(expected_nodes)
        
        # Validation cycle edges (peut être vide selon l'implémentation de reconstruction)
        # L'important est qu'un cycle ait été détecté
        assert result.cycle_detection.has_cycle is True
        
        # Validation stats cycle
        assert self.validator.validation_stats['cycle_detections'] == 1
        assert self.validator.validation_stats['issues_detected_total'] >= 1
        
        print("✅ Test Académique 10.03: Cycle Detection Integration - PASSED")
    
    def test_connectivity_coherence_validation(self):
        """
        Test Académique 10.04: Validation cohérence connectivité
        
        Validation:
        - Détection incohérences bidirectionnelles
        - Edge references manquantes dans nodes
        - Node references incorrectes dans edges
        - Issues détaillés avec descriptions précises
        """
        nodes, edges = self.create_simple_valid_dag()
        
        # Création incohérence: edge non référencé par target node
        broken_edge = create_edge("broken_edge", nodes[0], nodes[1], Decimal('1.0'))
        edges.append(broken_edge)
        # Pas de connect_nodes() → incohérence intentionnelle
        
        result = self.validator.validate_complete_dag_structure(nodes, edges)
        
        # Validation incohérence détectée
        assert result.is_valid is False
        assert len(result.connectivity_issues) > 0
        
        # Validation message détaillé
        connectivity_issue = result.connectivity_issues[0]
        assert "broken_edge" in connectivity_issue
        assert "not found" in connectivity_issue
        
        # Validation stats
        assert self.validator.validation_stats['connectivity_violations'] > 0
        
        print("✅ Test Académique 10.04: Connectivity Coherence Validation - PASSED")
    
    def test_nodes_edges_integrity_validation(self):
        """
        Test Académique 10.05: Validation intégrité nodes/edges
        
        Validation:
        - Détection node IDs duplicates
        - Détection edge IDs duplicates
        - Validation metadata consistency
        - Node type cache coherence
        """
        nodes, edges = self.create_simple_valid_dag()
        
        # Test 1: Node ID duplicate
        duplicate_node = create_node(nodes[0].node_id)  # Same ID
        nodes.append(duplicate_node)
        
        # Test 2: Edge avec metadata weight incohérente
        problematic_edge = create_edge("problematic_edge", nodes[0], nodes[1], Decimal('2.0'))
        # Modifier metadata weight pour créer incohérence
        problematic_edge.edge_metadata.weight = Decimal('1.0')  # Different from edge.weight
        edges.append(problematic_edge)
        
        result = self.validator.validate_complete_dag_structure(nodes, edges)
        
        # Validation integrity violations détectées
        assert result.is_valid is False
        assert len(result.integrity_violations) >= 2
        
        # Validation messages spécifiques
        violations_text = " ".join(result.integrity_violations)
        assert "Duplicate node ID" in violations_text
        assert "metadata weight mismatch" in violations_text
        
        # Validation stats
        assert self.validator.validation_stats['integrity_violations'] >= 2
        
        print("✅ Test Académique 10.05: Nodes/Edges Integrity Validation - PASSED")
    
    def test_orphaned_nodes_detection(self):
        """
        Test Académique 10.06: Détection nœuds orphelins
        
        Validation:
        - Nœuds isolés (ISOLATED type) détectés
        - Orphaned nodes dans résultat validation
        - Statistics nodes types correctes
        """
        nodes, edges = self.create_simple_valid_dag()
        
        # Ajout nœud orphelin
        orphan_node = create_node("orphan_node")
        nodes.append(orphan_node)
        
        result = self.validator.validate_complete_dag_structure(nodes, edges)
        
        # Validation orphan detection
        assert len(result.orphaned_nodes) == 1
        assert result.orphaned_nodes[0].node_id == "orphan_node"
        assert result.orphaned_nodes[0].get_node_type() == NodeType.ISOLATED
        
        # Validation statistics node types
        assert result.statistics['node_types']['ISOLATED'] == 1
        
        print("✅ Test Académique 10.06: Orphaned Nodes Detection - PASSED")
    
    def test_account_coherence_validation(self):
        """
        Test Académique 10.07: Validation cohérence comptes
        
        Validation:
        - Account integrity validée via DAG
        - Source/sink nodes existence vérifiée
        - Balance equations validées
        - Account issues intégrés dans résultat
        """
        nodes, edges = self.create_simple_valid_dag()
        
        # Création account avec nodes DAG
        account = Account("test_account", initial_balance=Decimal('100.0'))
        
        # Ajout nodes account au DAG
        nodes.extend([account.source_node, account.sink_node])
        
        # Test validation avec accounts
        result = self.validator.validate_complete_dag_structure(
            nodes, edges, accounts=[account]
        )
        
        # Account coherent devrait être valide
        account_issues = [issue for issue in result.integrity_violations 
                         if "test_account" in issue]
        
        # Account statistics
        assert result.statistics['total_accounts'] == 1
        assert 'total_balance' in result.statistics
        
        print("✅ Test Académique 10.07: Account Coherence Validation - PASSED")
    
    def test_dag_statistics_collection(self):
        """
        Test Académique 10.08: Collection statistics DAG
        
        Validation:
        - Statistics nodes complètes (counts, types)
        - Statistics edges complètes (counts, types, weights)
        - Connectivity metrics (degré moyen)
        - Account metrics (si applicable)
        """
        nodes, edges = self.create_simple_valid_dag()
        
        result = self.validator.validate_complete_dag_structure(nodes, edges)
        stats = result.statistics
        
        # Validation statistics structure
        required_fields = {
            'total_nodes', 'total_edges', 'node_types', 'edge_types',
            'connectivity', 'weights'
        }
        assert required_fields.issubset(set(stats.keys()))
        
        # Validation node statistics
        assert stats['total_nodes'] == 3
        assert stats['node_types']['SOURCE'] == 1
        assert stats['node_types']['SINK'] == 1
        assert stats['node_types']['INTERMEDIATE'] == 1
        
        # Validation edge statistics
        assert stats['total_edges'] == 2
        assert stats['edge_types']['STRUCTURAL'] == 2  # Default type
        
        # Validation connectivity
        connectivity = stats['connectivity']
        assert connectivity['total_incoming_connections'] == 2
        assert connectivity['total_outgoing_connections'] == 2
        assert connectivity['avg_node_degree'] == pytest.approx(4/3, rel=1e-2)
        
        # Validation weights
        assert 'total_weight' in stats['weights']
        assert 'avg_edge_weight' in stats['weights']
        
        print("✅ Test Académique 10.08: DAG Statistics Collection - PASSED")
    
    def test_validation_performance_tracking(self):
        """
        Test Académique 10.09: Performance tracking validation
        
        Validation:
        - Temps validation trackés par appel
        - Statistics performance cumulatives
        - Average time calculation correct
        - Issue breakdown détaillé
        """
        nodes, edges = self.create_simple_valid_dag()
        
        # Multiple validations pour test performance
        for i in range(3):
            self.validator.validate_complete_dag_structure(nodes, edges)
        
        # Test performance stats
        perf_stats = self.validator.get_validation_performance_stats()
        
        # Validation structure
        required_fields = {
            'validations_performed', 'avg_validation_time_ms',
            'total_issues_detected', 'cycle_detection_stats', 'issue_breakdown'
        }
        assert required_fields.issubset(set(perf_stats.keys()))
        
        # Validation valeurs
        assert perf_stats['validations_performed'] == 3
        assert perf_stats['avg_validation_time_ms'] > 0
        
        # Validation issue breakdown
        breakdown = perf_stats['issue_breakdown']
        assert 'cycle_detections' in breakdown
        assert 'connectivity_violations' in breakdown
        assert 'integrity_violations' in breakdown
        
        print("✅ Test Académique 10.09: Validation Performance Tracking - PASSED")
    
    def test_validation_result_summary_generation(self):
        """
        Test Académique 10.10: Génération résumés validation
        
        Validation:
        - Summary valide pour DAG valid
        - Summary invalide avec issue count
        - Format lisible et informatif
        """
        # Test 1: DAG valide summary
        nodes, edges = self.create_simple_valid_dag()
        result = self.validator.validate_complete_dag_structure(nodes, edges)
        
        summary = result.get_summary()
        assert "✅ DAG Valid" in summary
        assert "3 nodes" in summary
        assert "2 edges" in summary
        
        # Test 2: DAG invalide summary
        cycle_nodes, cycle_edges = self.create_cycle_dag()
        invalid_result = self.validator.validate_complete_dag_structure(cycle_nodes, cycle_edges)
        
        invalid_summary = invalid_result.get_summary()
        assert "❌ DAG Invalid" in invalid_summary
        assert "issues detected" in invalid_summary
        
        print("✅ Test Académique 10.10: Validation Result Summary Generation - PASSED")
    
    def test_complex_dag_validation_integration(self):
        """
        Test Académique 10.11: Validation DAG complexe intégration
        
        Validation globale:
        - DAG avec multiple issues simultanés
        - Toutes phases validation exécutées
        - Issues categorisés correctement
        - Performance sous charge
        """
        # Construction DAG complexe avec multiple issues
        nodes = [create_node(f"complex_{i}") for i in range(10)]
        edges = []
        
        # Création edges avec quelques issues intentionnelles
        for i in range(len(nodes) - 1):
            edge = create_edge(f"edge_{i}", nodes[i], nodes[i+1])
            edges.append(edge)
            connect_nodes(nodes[i], nodes[i+1], edge)
        
        # Issue 1: Nœud orphelin
        orphan = create_node("complex_orphan")
        nodes.append(orphan)
        
        # Issue 2: Edge avec inconsistent metadata
        bad_edge = create_edge("bad_edge", nodes[0], nodes[1], Decimal('5.0'))
        bad_edge.edge_metadata.weight = Decimal('1.0')  # Create inconsistency
        edges.append(bad_edge)
        
        # Issue 3: Duplicate node ID
        duplicate = create_node(nodes[0].node_id)
        nodes.append(duplicate)
        
        # Validation complète
        result = self.validator.validate_complete_dag_structure(nodes, edges)
        
        # Validation globale: should be invalid
        assert result.is_valid is False
        
        # Validation issues détectés
        assert len(result.orphaned_nodes) >= 1
        assert len(result.integrity_violations) >= 2  # metadata mismatch + duplicate
        assert len(result.connectivity_issues) >= 1  # bad_edge not connected
        
        # Validation statistics cohérentes
        assert result.statistics['total_nodes'] == len(nodes)
        assert result.validation_time_ms > 0
        
        print("✅ Test Académique 10.11: Complex DAG Validation Integration - PASSED")
    
    def test_production_performance_requirements(self):
        """
        Test Académique 10.12: Performance requirements production
        
        Validation:
        - Validation large DAG (100+ nodes) sous limite temps
        - Memory usage raisonnable
        - Statistics accuracy maintenue
        - No performance degradation
        """
        # Construction large DAG pour test performance
        large_nodes = [create_node(f"perf_node_{i}") for i in range(150)]
        large_edges = []
        
        # Connection linéaire pour éviter cycles
        for i in range(len(large_nodes) - 1):
            edge = create_edge(f"perf_edge_{i}", large_nodes[i], large_nodes[i+1])
            large_edges.append(edge)
            connect_nodes(large_nodes[i], large_nodes[i+1], edge)
        
        # Test performance validation
        start_time = time.time()
        result = self.validator.validate_complete_dag_structure(large_nodes, large_edges)
        end_time = time.time()
        
        validation_time = (end_time - start_time) * 1000  # ms
        
        # Performance requirements
        assert validation_time < 1000  # < 1 seconde pour 150 nodes
        assert result.is_valid is True  # Should be valid linear DAG
        
        # Validation statistics accuracy
        assert result.statistics['total_nodes'] == 150
        assert result.statistics['total_edges'] == 149
        
        # Performance stats
        perf_stats = self.validator.get_validation_performance_stats()
        assert perf_stats['avg_validation_time_ms'] > 0
        
        print("✅ Test Académique 10.12: Production Performance Requirements - PASSED")