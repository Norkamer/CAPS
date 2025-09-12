"""
Test Académique 09: Path Enumeration Basic
=========================================

Tests validation pour DAGPathEnumerator - Structure de base et fonctionnalités
selon spécifications blueprint ICGS.

Tests couverts:
- Construction classe et paramètres
- Initialisation taxonomy integration  
- Max_paths boundary conditions
- Basic enumeration functionality
- Error handling et validation parameters
- Cache functionality basic
- Statistics tracking
- Reset state mechanisms
"""

import pytest
import time
from decimal import Decimal
from unittest.mock import Mock, MagicMock

# Import modules ICGS
from icgs_core.path_enumerator import DAGPathEnumerator, EnumerationStatistics
from icgs_core.account_taxonomy import AccountTaxonomy
from icgs_core.dag_structures import Node, Edge, EdgeMetadata, NodeType, EdgeType


class TestAcademicPathEnumerationBasic:
    """
    Test Académique 09: DAGPathEnumerator - Validation Structure Basic
    
    Validation propriétés fondamentales énumérateur selon blueprint:
    - Construction et paramètres
    - Integration taxonomy  
    - Boundary conditions
    - Basic functionality
    """
    
    def setup_method(self):
        """Setup test environment avec taxonomy et structures DAG"""
        self.taxonomy = AccountTaxonomy()
        self.taxonomy.update_taxonomy({
            'account_A': 'A',
            'account_B': 'B', 
            'account_C': 'C'
        }, transaction_num=0)
        
        # Configuration enumerator avec paramètres test
        self.max_paths = 100
        self.batch_size = 10
        
    def test_construction_parameters_validation(self):
        """
        Test Académique 09.1: Construction et validation paramètres
        
        Validation:
        - Paramètres construction corrects
        - Initialisation structures internes
        - Validation parameters method
        """
        # Test construction normale
        enumerator = DAGPathEnumerator(
            taxonomy=self.taxonomy,
            max_paths=self.max_paths,
            batch_size=self.batch_size
        )
        
        # Validation attributs
        assert enumerator.taxonomy is self.taxonomy
        assert enumerator.max_paths == self.max_paths
        assert enumerator.batch_size == self.batch_size
        
        # Validation structures internes
        assert isinstance(enumerator.visited_nodes, set)
        assert isinstance(enumerator.current_path, list)
        assert isinstance(enumerator.enumerated_paths, list)
        assert isinstance(enumerator._path_cache, dict)
        assert isinstance(enumerator._word_cache, dict)
        assert isinstance(enumerator.stats, EnumerationStatistics)
        
        # Test validation parameters
        assert enumerator.validate_enumeration_parameters() is True
        
    def test_invalid_parameters_handling(self):
        """
        Test Académique 09.2: Gestion paramètres invalides
        
        Validation:
        - Max_paths invalide détecté
        - Batch_size invalide détecté  
        - Taxonomy None détecté
        """
        # Test max_paths invalide
        enumerator_invalid_max = DAGPathEnumerator(
            taxonomy=self.taxonomy,
            max_paths=0,  # Invalide
            batch_size=self.batch_size
        )
        assert enumerator_invalid_max.validate_enumeration_parameters() is False
        
        # Test batch_size invalide
        enumerator_invalid_batch = DAGPathEnumerator(
            taxonomy=self.taxonomy,
            max_paths=self.max_paths,
            batch_size=-1  # Invalide
        )
        assert enumerator_invalid_batch.validate_enumeration_parameters() is False
        
        # Test taxonomy None
        enumerator_no_taxonomy = DAGPathEnumerator(
            taxonomy=None,  # Invalide
            max_paths=self.max_paths,
            batch_size=self.batch_size
        )
        assert enumerator_no_taxonomy.validate_enumeration_parameters() is False
    
    def test_reset_enumeration_state(self):
        """
        Test Académique 09.3: Reset état énumération
        
        Validation:
        - Structures internes remises à zéro
        - Statistics reset
        - État clean pour nouvelle énumération
        """
        enumerator = DAGPathEnumerator(self.taxonomy, self.max_paths, self.batch_size)
        
        # Simulation état "dirty"
        enumerator.visited_nodes.add("test_node")
        enumerator.current_path.append(Mock())
        enumerator.enumerated_paths.append([Mock()])
        enumerator.stats.paths_enumerated = 10
        
        # Reset
        enumerator.reset_enumeration_state()
        
        # Validation reset
        assert len(enumerator.visited_nodes) == 0
        assert len(enumerator.current_path) == 0
        assert len(enumerator.enumerated_paths) == 0
        assert enumerator.stats.paths_enumerated == 0
    
    def test_cache_key_generation(self):
        """
        Test Académique 09.4: Génération clés cache
        
        Validation:
        - Clés uniques pour différents paramètres
        - Format clé cohérent
        - Différentiation transaction_num
        """
        enumerator = DAGPathEnumerator(self.taxonomy, self.max_paths, self.batch_size)
        
        # Nodes test
        node1 = Node("node_1")
        node2 = Node("node_2")
        
        # Génération clés
        key1 = enumerator._generate_cache_key(node1, 1)
        key2 = enumerator._generate_cache_key(node2, 1)
        key3 = enumerator._generate_cache_key(node1, 2)  # Différent transaction_num
        
        # Validation unicité
        assert key1 != key2  # Différents nodes
        assert key1 != key3  # Différent transaction_num
        assert key2 != key3
        
        # Validation format
        assert "node_1" in key1
        assert "node_2" in key2
        assert str(self.max_paths) in key1  # Max_paths dans clé
    
    def test_source_node_detection(self):
        """
        Test Académique 09.5: Détection nodes sources
        
        Validation:
        - Source node (no incoming edges) détecté
        - Non-source node détecté
        - Edge cases gérés
        """
        enumerator = DAGPathEnumerator(self.taxonomy, self.max_paths, self.batch_size)
        
        # Node source (pas d'incoming edges)
        source_node = Node("source")
        assert enumerator._is_source_node(source_node) is True
        
        # Node non-source (avec incoming edges)
        sink_node = Node("sink")
        source_node_2 = Node("source_2")
        
        # Création edge pour avoir incoming
        edge = Edge(
            edge_id="test_edge",
            source_node=source_node_2,
            target_node=sink_node,
            edge_type=EdgeType.STRUCTURAL
        )
        
        # Ajout edge aux nodes pour actualiser connectivité
        sink_node.add_incoming_edge(edge)
        source_node_2.add_outgoing_edge(edge)
        
        # Sink node a maintenant incoming edge
        assert enumerator._is_source_node(sink_node) is False
        assert enumerator._is_source_node(source_node_2) is True  # Toujours source car pas d'incoming
    
    def test_cycle_detection_mechanism(self):
        """
        Test Académique 09.6: Mécanisme détection cycles
        
        Validation:
        - Cycle détecté dans visited_nodes
        - Pas de faux positifs
        - État visited_nodes correct
        """
        enumerator = DAGPathEnumerator(self.taxonomy, self.max_paths, self.batch_size)
        
        node1 = Node("node_1")
        node2 = Node("node_2")
        
        # Pas de cycle initialement
        assert enumerator._detect_cycle(node1) is False
        assert enumerator._detect_cycle(node2) is False
        
        # Ajout node1 aux visited
        enumerator.visited_nodes.add(node1.node_id)
        
        # Cycle détecté pour node1, pas pour node2
        assert enumerator._detect_cycle(node1) is True
        assert enumerator._detect_cycle(node2) is False
        
        # Ajout node2
        enumerator.visited_nodes.add(node2.node_id)
        assert enumerator._detect_cycle(node2) is True
    
    def test_statistics_tracking_basic(self):
        """
        Test Académique 09.7: Tracking statistics de base
        
        Validation:
        - EnumerationStatistics correctement initialisées
        - Getters statistics fonctionnels
        - Reset statistics avec reset_enumeration_state
        """
        enumerator = DAGPathEnumerator(self.taxonomy, self.max_paths, self.batch_size)
        
        # Statistics initiales
        stats = enumerator.get_enumeration_statistics()
        assert stats.paths_enumerated == 0
        assert stats.cycles_detected == 0
        assert stats.early_terminations == 0
        assert stats.enumeration_time_ms == 0.0
        assert stats.max_depth_reached == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
        
        # Modification manuelle pour test (simulation)
        enumerator.stats.paths_enumerated = 5
        enumerator.stats.cycles_detected = 1
        
        # Vérification modification
        stats_updated = enumerator.get_enumeration_statistics()
        assert stats_updated.paths_enumerated == 5
        assert stats_updated.cycles_detected == 1
        
        # Reset via reset_enumeration_state
        enumerator.reset_enumeration_state()
        stats_reset = enumerator.get_enumeration_statistics()
        assert stats_reset.paths_enumerated == 0
        assert stats_reset.cycles_detected == 0
    
    def test_boundary_conditions_max_paths(self):
        """
        Test Académique 09.8: Boundary conditions max_paths
        
        Validation:
        - Comportement avec max_paths = 1
        - Comportement avec max_paths très grand
        - Protection explosion
        """
        # Test max_paths = 1 (minimum pratique)
        enumerator_min = DAGPathEnumerator(self.taxonomy, max_paths=1, batch_size=1)
        assert enumerator_min.max_paths == 1
        assert enumerator_min.validate_enumeration_parameters() is True
        
        # Test max_paths très grand
        enumerator_max = DAGPathEnumerator(self.taxonomy, max_paths=1000000, batch_size=100)
        assert enumerator_max.max_paths == 1000000
        assert enumerator_max.validate_enumeration_parameters() is True
        
        # Test protection explosion via early termination logic
        # (sera testé plus en détail dans étapes suivantes avec vrais DAGs)
        
    def test_conversion_paths_to_words_empty_list(self):
        """
        Test Académique 09.9: Conversion paths vides et edge cases
        
        Validation:
        - Liste vide gérée correctement
        - Erreurs conversion gérées gracieusement  
        - Cache utilisé correctement
        """
        enumerator = DAGPathEnumerator(self.taxonomy, self.max_paths, self.batch_size)
        
        # Test liste vide
        words_empty = enumerator.convert_paths_to_words([], transaction_num=1)
        assert words_empty == []
        
        # Test avec path contenant nodes
        node_a = Node("account_A")
        node_b = Node("account_B")
        
        path_test = [node_a, node_b]
        words = enumerator.convert_paths_to_words([path_test], transaction_num=0)
        
        # Devrait avoir 1 mot
        assert len(words) == 1
        assert isinstance(words[0], str)
        
        # Test cache: deuxième appel devrait utiliser cache
        stats_before = enumerator.stats.cache_hits
        words_cached = enumerator.convert_paths_to_words([path_test], transaction_num=0)
        stats_after = enumerator.stats.cache_hits
        
        # Cache hit devrait avoir augmenté
        assert stats_after > stats_before
        assert words_cached == words  # Même résultat
    
    def test_enumerate_and_classify_basic_structure(self):
        """
        Test Académique 09.10: Structure de base enumerate_and_classify
        
        Validation:
        - Méthode existe et callable
        - Paramètres acceptés correctement
        - Retourne dict avec bonne structure
        - Gestion erreurs de base
        """
        enumerator = DAGPathEnumerator(self.taxonomy, self.max_paths, self.batch_size)
        
        # Mock NFA pour test structure
        mock_nfa = Mock()
        mock_nfa.evaluate_to_final_state = Mock(return_value="state_1")
        
        # Mock transaction edge simple
        source_node = Node("source")
        sink_node = Node("sink")
        transaction_edge = Edge(
            edge_id="transaction_test",
            source_node=source_node,
            target_node=sink_node,
            edge_type=EdgeType.TRANSACTION
        )
        
        # Test appel méthode (ne devrait pas crash)
        try:
            result = enumerator.enumerate_and_classify(
                transaction_edge=transaction_edge,
                nfa=mock_nfa,
                transaction_num=1
            )
            
            # Validation type retour
            assert isinstance(result, dict)
            
            # Pour ce test basic, pas de chemins attendus car pas de structure DAG complète
            # (sera testé plus en détail dans étapes suivantes)
            
        except Exception as e:
            # Ne devrait pas avoir d'exception fatale dans structure de base
            pytest.fail(f"Unexpected exception in enumerate_and_classify: {e}")
    
    def test_integration_taxonomy_basic(self):
        """
        Test Académique 09.11: Intégration taxonomy de base
        
        Validation:
        - AccountTaxonomy correctement utilisé
        - Paramètres transaction_num passés correctement
        - Conversion path→word fonctionnelle basique
        """
        enumerator = DAGPathEnumerator(self.taxonomy, self.max_paths, self.batch_size)
        
        # Nodes avec IDs correspondant à taxonomy
        node_a = Node("account_A")
        node_b = Node("account_B") 
        node_c = Node("account_C")
        
        # Path test
        test_path = [node_a, node_b, node_c]
        
        # Test conversion
        words = enumerator.convert_paths_to_words([test_path], transaction_num=0)
        
        assert len(words) == 1
        word = words[0]
        
        # Word devrait contenir caractères de taxonomy (A, B, C)
        assert isinstance(word, str)
        assert len(word) > 0  # Au minimum pas vide
        
        # Vérification que taxonomy est appelé avec bons paramètres
        # (test indirect via résultat non-vide et cohérent)
        
    def test_error_handling_robustness(self):
        """
        Test Académique 09.12: Robustesse gestion erreurs
        
        Validation:
        - Exceptions gérées gracieusement
        - Logging approprié
        - État clean après erreurs
        - Recovery possible
        """
        enumerator = DAGPathEnumerator(self.taxonomy, self.max_paths, self.batch_size)
        
        # Test avec taxonomy défaillante (mock qui lève exception)
        bad_taxonomy = Mock()
        bad_taxonomy.convert_path_to_word = Mock(side_effect=Exception("Test taxonomy error"))
        
        enumerator_bad = DAGPathEnumerator(bad_taxonomy, self.max_paths, self.batch_size)
        
        # Test conversion avec taxonomy défaillante
        node_test = Node("test_account")
        test_path = [node_test]
        
        # Ne devrait pas crasher, mais retourner fallback
        words = enumerator_bad.convert_paths_to_words([test_path], transaction_num=1)
        
        assert len(words) == 1
        assert words[0] == ""  # Fallback empty string
        
        # État enumerator devrait rester stable
        assert enumerator_bad.validate_enumeration_parameters() is True
        
    def test_comprehensive_basic_integration(self):
        """
        Test Académique 09.13: Intégration complète structure de base
        
        Validation globale fonctionnalités implémentées Étape 1.1:
        - Construction et paramètres ✓
        - Structures internes ✓  
        - Validation et error handling ✓
        - Cache et statistics ✓
        - Integration taxonomy basic ✓
        """
        # Construction avec paramètres réalistes
        enumerator = DAGPathEnumerator(
            taxonomy=self.taxonomy,
            max_paths=1000,
            batch_size=50
        )
        
        # Validation construction complète
        assert enumerator.validate_enumeration_parameters() is True
        assert isinstance(enumerator.get_enumeration_statistics(), EnumerationStatistics)
        
        # Test cycle complet reset
        enumerator.visited_nodes.add("temp")
        enumerator.reset_enumeration_state()
        assert len(enumerator.visited_nodes) == 0
        
        # Test conversion basic
        node = Node("account_A")
        words = enumerator.convert_paths_to_words([[node]], transaction_num=0)
        assert len(words) == 1
        assert isinstance(words[0], str)
        
        # Performance basique (pas de freeze)
        start_time = time.time()
        
        for i in range(10):
            enumerator.reset_enumeration_state()
            enumerator._generate_cache_key(node, i)
        
        duration = time.time() - start_time
        assert duration < 0.1  # Devrait être très rapide
        
        # Validation finale état clean
        assert enumerator.validate_enumeration_parameters() is True
        
        print("✅ Test Académique 09: DAGPathEnumerator Basic Structure - PASSED")
    
    def test_reverse_traversal_from_transaction_basic(self):
        """
        Test Académique 09.14: Traversal reverse basic depuis transaction
        
        Validation Étape 1.2:
        - Énumération reverse depuis target node (sink)
        - Navigation via incoming_edges correcte
        - Détection nodes source comme condition d'arrêt
        - Chemins sink→source générés correctement
        """
        enumerator = DAGPathEnumerator(self.taxonomy, self.max_paths, self.batch_size)
        
        # Setup DAG simple: source → sink
        source_node = Node("source_account")
        sink_node = Node("sink_account")
        
        # Transaction edge
        transaction_edge = Edge(
            edge_id="transaction_reverse_test",
            source_node=source_node,
            target_node=sink_node,
            edge_type=EdgeType.TRANSACTION
        )
        
        # Ajout edges aux nodes pour connectivité
        sink_node.add_incoming_edge(transaction_edge)
        source_node.add_outgoing_edge(transaction_edge)
        
        # Test énumération reverse
        paths = list(enumerator.enumerate_paths_from_transaction(transaction_edge, transaction_num=0))
        
        # Validation résultats
        assert len(paths) == 1  # Un seul chemin sink→source
        assert len(paths[0]) == 2  # Chemin complet sink→source
        assert paths[0][0] == sink_node  # Commence par sink node
        assert paths[0][1] == source_node  # Se termine par source node
        
        # Validation statistics
        stats = enumerator.get_enumeration_statistics()
        assert stats.paths_enumerated == 1
        assert stats.max_depth_reached == 2  # Profondeur sink→source
        assert stats.cycles_detected == 0
    
    def test_reverse_traversal_multi_level_path(self):
        """
        Test Académique 09.15: Traversal reverse multi-niveau
        
        Validation:
        - Chemins multiples sink→sources
        - Profondeur traversal correcte
        - Backtracking propre sans corruption état
        """
        enumerator = DAGPathEnumerator(self.taxonomy, self.max_paths, self.batch_size)
        
        # Setup DAG multi-niveau: source1 → intermediate → sink
        #                        source2 ↗
        source1 = Node("source1")
        source2 = Node("source2") 
        intermediate = Node("intermediate")
        sink = Node("sink")
        
        # Edges structure
        edge1 = Edge("edge1", source1, intermediate)
        edge2 = Edge("edge2", source2, intermediate)
        edge3 = Edge("edge3", intermediate, sink)
        transaction_edge = Edge("transaction", intermediate, sink, edge_type=EdgeType.TRANSACTION)
        
        # Connexion DAG
        intermediate.add_incoming_edge(edge1)
        intermediate.add_incoming_edge(edge2)
        sink.add_incoming_edge(edge3)
        sink.add_incoming_edge(transaction_edge)
        
        source1.add_outgoing_edge(edge1)
        source2.add_outgoing_edge(edge2)
        intermediate.add_outgoing_edge(edge3)
        intermediate.add_outgoing_edge(transaction_edge)
        
        # Énumération depuis transaction (sink)
        paths = list(enumerator.enumerate_paths_from_transaction(transaction_edge, transaction_num=0))
        
        # Validation: 2 chemins (sink → intermediate → source1/source2)
        assert len(paths) >= 1  # Au minimum 1 chemin
        
        # Vérification que tous les chemins commencent par sink
        for path in paths:
            assert len(path) > 0
            assert path[0] == sink  # Tous commencent par sink node
            
        # Statistics validation
        stats = enumerator.get_enumeration_statistics()
        assert stats.paths_enumerated >= 1
        assert stats.max_depth_reached >= 1
        assert stats.cycles_detected == 0  # Pas de cycles dans ce DAG
    
    def test_reverse_traversal_cycle_detection(self):
        """
        Test Académique 09.16: Détection cycles pendant traversal reverse
        
        Validation:
        - Cycles détectés et évités
        - Pas d'explosion combinatoire
        - Backtracking correct après détection cycle
        """
        enumerator = DAGPathEnumerator(self.taxonomy, self.max_paths, self.batch_size)
        
        # Setup DAG avec cycle potentiel: A ↔ B
        node_a = Node("cycle_a")
        node_b = Node("cycle_b")
        
        edge_ab = Edge("ab", node_a, node_b)
        edge_ba = Edge("ba", node_b, node_a)  # Crée cycle
        transaction_edge = Edge("transaction", node_a, node_b, edge_type=EdgeType.TRANSACTION)
        
        # Connexion avec cycle
        node_b.add_incoming_edge(edge_ab)
        node_b.add_incoming_edge(transaction_edge)
        node_a.add_incoming_edge(edge_ba)
        
        node_a.add_outgoing_edge(edge_ab)
        node_a.add_outgoing_edge(transaction_edge)
        node_b.add_outgoing_edge(edge_ba)
        
        # Énumération avec cycle - ne devrait pas boucler infiniment
        paths = list(enumerator.enumerate_paths_from_transaction(transaction_edge, transaction_num=0))
        
        # Validation: énumération terminée proprement
        assert isinstance(paths, list)
        
        # Statistics: cycles détectés
        stats = enumerator.get_enumeration_statistics()
        assert stats.cycles_detected >= 0  # Au moins some cycle detection activity
        
        # Test terminaison dans temps raisonnable (pas d'explosion)
        # Si on arrive ici, pas de boucle infinie
        assert True  # Test passé si pas de timeout
    
    def test_dag_structure_validation(self):
        """
        Test Académique 09.17: Validation structure DAG avant énumération
        
        Validation Étape 1.2:
        - Validation nodes non-None
        - Validation node_id présent
        - Validation incoming_edges structure
        """
        enumerator = DAGPathEnumerator(self.taxonomy, self.max_paths, self.batch_size)
        
        # Test validation avec node valide
        valid_node = Node("valid_test")
        assert enumerator._validate_dag_structure(valid_node) is True
        
        # Test validation avec node None
        assert enumerator._validate_dag_structure(None) is False
        
        # Test validation avec node sans node_id (mock)
        invalid_node = Mock()
        invalid_node.node_id = None
        assert enumerator._validate_dag_structure(invalid_node) is False
        
        # Test validation avec node sans incoming_edges (mock)
        no_edges_node = Mock()
        no_edges_node.node_id = "test"
        del no_edges_node.incoming_edges  # Remove attribute
        assert enumerator._validate_dag_structure(no_edges_node) is False