"""
DAG Structures - Classes fondamentales pour DAG avec validation topologique

Module implémentant les structures de données core pour graphes dirigés acycliques
selon blueprint ICGS avec garanties mathématiques:
- Node: Nœuds source/sink avec connectivité trackée
- Edge: Arêtes pondérées avec métadonnées temporelles  
- Anti-cycle validation: Détection robuste via DFS
- Connectivité: Préservation invariants topologiques

Propriétés mathématiques garanties:
- Détection cycles: Algorithme DFS O(V+E) complet
- Connectivité: Invariants preservation sous modifications
- Précision: Weights Decimal pour stabilité numérique
- Temporalité: Ordering metadata pour cohérence séquentielle
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Set, Optional, Any, Union
import time
import uuid
from collections import defaultdict, deque


class NodeType(Enum):
    """Types de nœuds DAG pour classification sémantique"""
    SOURCE = "SOURCE"       # Nœud source (pas d'incoming edges)
    SINK = "SINK"          # Nœud sink (pas d'outgoing edges)  
    INTERMEDIATE = "INTERMEDIATE"  # Nœud intermédiaire (both directions)
    ISOLATED = "ISOLATED"   # Nœud isolé (ni incoming ni outgoing)


class EdgeType(Enum):
    """Types d'arêtes pour classification sémantique"""
    TRANSACTION = "TRANSACTION"    # Arête représentant transaction économique
    STRUCTURAL = "STRUCTURAL"      # Arête structurelle DAG
    TEMPORARY = "TEMPORARY"        # Arête temporaire (validation/enumeration)


@dataclass
class EdgeMetadata:
    """Métadonnées arête avec timestamp et context"""
    created_at: float = field(default_factory=time.time)
    transaction_id: Optional[str] = None
    weight: Decimal = Decimal('1.0')
    edge_type: EdgeType = EdgeType.STRUCTURAL
    context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validation metadata après création"""
        if not isinstance(self.weight, Decimal):
            self.weight = Decimal(str(self.weight))
        if self.weight < 0:
            raise ValueError(f"Edge weight must be non-negative: {self.weight}")


class Node:
    """
    Nœud DAG avec connectivité bidirectionnelle trackée
    
    Fonctionnalités:
    - Incoming/outgoing edges management
    - Node type classification automatique
    - Connectivité invariants preservation
    - UUID unique identification  
    - Metadata extensible
    """
    
    def __init__(self, node_id: str, metadata: Optional[Dict[str, Any]] = None):
        self.node_id = node_id
        self.uuid = str(uuid.uuid4())
        self.metadata = metadata or {}
        self.created_at = time.time()
        
        # Connectivité trackée
        self.incoming_edges: Dict[str, 'Edge'] = {}  # edge_id -> Edge
        self.outgoing_edges: Dict[str, 'Edge'] = {}  # edge_id -> Edge
        
        # Cache type classification
        self._node_type_cache: Optional[NodeType] = None
        self._cache_invalidated = True
    
    def add_incoming_edge(self, edge: 'Edge') -> None:
        """Ajoute arête incoming avec validation"""
        if edge.edge_id in self.incoming_edges:
            raise ValueError(f"Incoming edge {edge.edge_id} already exists")
        if edge.target_node != self:
            raise ValueError(f"Edge target mismatch: expected {self.node_id}")
        
        self.incoming_edges[edge.edge_id] = edge
        self._invalidate_cache()
    
    def add_outgoing_edge(self, edge: 'Edge') -> None:
        """Ajoute arête outgoing avec validation"""
        if edge.edge_id in self.outgoing_edges:
            raise ValueError(f"Outgoing edge {edge.edge_id} already exists")
        if edge.source_node != self:
            raise ValueError(f"Edge source mismatch: expected {self.node_id}")
            
        self.outgoing_edges[edge.edge_id] = edge
        self._invalidate_cache()
    
    def remove_incoming_edge(self, edge_id: str) -> Optional['Edge']:
        """Retire arête incoming si existe"""
        edge = self.incoming_edges.pop(edge_id, None)
        if edge:
            self._invalidate_cache()
        return edge
    
    def remove_outgoing_edge(self, edge_id: str) -> Optional['Edge']:
        """Retire arête outgoing si existe"""
        edge = self.outgoing_edges.pop(edge_id, None)
        if edge:
            self._invalidate_cache()
        return edge
    
    def get_node_type(self) -> NodeType:
        """Classification type nœud avec cache"""
        if self._cache_invalidated or self._node_type_cache is None:
            self._node_type_cache = self._compute_node_type()
            self._cache_invalidated = False
        return self._node_type_cache
    
    def _compute_node_type(self) -> NodeType:
        """Calcul classification type nœud"""
        has_incoming = len(self.incoming_edges) > 0
        has_outgoing = len(self.outgoing_edges) > 0
        
        if not has_incoming and not has_outgoing:
            return NodeType.ISOLATED
        elif not has_incoming and has_outgoing:
            return NodeType.SOURCE  
        elif has_incoming and not has_outgoing:
            return NodeType.SINK
        else:
            return NodeType.INTERMEDIATE
    
    def _invalidate_cache(self) -> None:
        """Invalidation cache après modification"""
        self._cache_invalidated = True
    
    def get_connectivity_stats(self) -> Dict[str, int]:
        """Statistiques connectivité nœud"""
        return {
            'incoming_count': len(self.incoming_edges),
            'outgoing_count': len(self.outgoing_edges),
            'total_degree': len(self.incoming_edges) + len(self.outgoing_edges),
            'node_type': self.get_node_type().value
        }
    
    def __str__(self) -> str:
        return f"Node({self.node_id}, type={self.get_node_type().value}, in={len(self.incoming_edges)}, out={len(self.outgoing_edges)})"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Node):
            return False
        return self.node_id == other.node_id
    
    def __hash__(self) -> int:
        return hash(self.node_id)


class Edge:
    """
    Arête DAG pondérée avec métadonnées temporelles
    
    Fonctionnalités:
    - Source/target node references bidirectionnelles
    - Poids Decimal pour stabilité numérique
    - Métadonnées extensibles avec timestamp  
    - Edge type classification
    - Validation coherence automatique
    """
    
    def __init__(self, 
                 edge_id: str,
                 source_node: Node, 
                 target_node: Node,
                 weight: Union[Decimal, float, int, str] = Decimal('1.0'),
                 edge_type: EdgeType = EdgeType.STRUCTURAL,
                 metadata: Optional[Dict[str, Any]] = None):
        
        self.edge_id = edge_id
        self.source_node = source_node
        self.target_node = target_node
        self.uuid = str(uuid.uuid4())
        
        # Validation et conversion weight
        if not isinstance(weight, Decimal):
            weight = Decimal(str(weight))
        if weight < 0:
            raise ValueError(f"Edge weight must be non-negative: {weight}")
        self.weight = weight
        
        # Métadonnées avec type
        self.edge_metadata = EdgeMetadata(
            weight=weight,
            edge_type=edge_type,
            context=metadata or {}
        )
        
        self.created_at = time.time()
        
        # Validation nœuds différents (pas de self-loops)
        if source_node == target_node:
            raise ValueError(f"Self-loops not allowed: {source_node.node_id}")
    
    def get_reverse_direction(self) -> tuple[Node, Node]:
        """Retourne direction reverse (pour sink→source enumeration)"""
        return (self.target_node, self.source_node)
    
    def get_weight(self) -> Decimal:
        """Poids arête avec garantie Decimal"""
        return self.weight
    
    def update_weight(self, new_weight: Union[Decimal, float, int, str]) -> None:
        """Mise à jour poids avec validation"""
        if not isinstance(new_weight, Decimal):
            new_weight = Decimal(str(new_weight))
        if new_weight < 0:
            raise ValueError(f"Edge weight must be non-negative: {new_weight}")
        
        self.weight = new_weight
        self.edge_metadata.weight = new_weight
    
    def is_transaction_edge(self) -> bool:
        """Test si arête représente transaction économique"""
        return self.edge_metadata.edge_type == EdgeType.TRANSACTION
    
    def is_temporary_edge(self) -> bool:
        """Test si arête temporaire (validation/enumeration)"""
        return self.edge_metadata.edge_type == EdgeType.TEMPORARY
    
    def get_edge_info(self) -> Dict[str, Any]:
        """Informations complètes arête"""
        return {
            'edge_id': self.edge_id,
            'uuid': self.uuid,
            'source_id': self.source_node.node_id,
            'target_id': self.target_node.node_id,
            'weight': str(self.weight),
            'edge_type': self.edge_metadata.edge_type.value,
            'created_at': self.created_at,
            'transaction_id': self.edge_metadata.transaction_id,
            'context': self.edge_metadata.context
        }
    
    def __str__(self) -> str:
        return f"Edge({self.edge_id}: {self.source_node.node_id} -> {self.target_node.node_id}, w={self.weight})"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Edge):
            return False
        return self.edge_id == other.edge_id
    
    def __hash__(self) -> int:
        return hash(self.edge_id)


@dataclass  
class AccountBalance:
    """Balance comptable avec validation invariants conservation"""
    initial_balance: Decimal = Decimal('0.0')
    current_balance: Decimal = Decimal('0.0')
    total_credits: Decimal = Decimal('0.0')
    total_debits: Decimal = Decimal('0.0')
    transaction_count: int = 0
    last_updated: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """Validation cohérence après création"""
        if not isinstance(self.initial_balance, Decimal):
            self.initial_balance = Decimal(str(self.initial_balance))
        if not isinstance(self.current_balance, Decimal):
            self.current_balance = Decimal(str(self.current_balance))
        if not isinstance(self.total_credits, Decimal):
            self.total_credits = Decimal(str(self.total_credits))
        if not isinstance(self.total_debits, Decimal):
            self.total_debits = Decimal(str(self.total_debits))
    
    def update_balance(self, amount: Decimal, is_credit: bool = True) -> None:
        """Mise à jour balance avec validation conservation"""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        
        if amount < 0:
            raise ValueError(f"Balance update amount must be non-negative: {amount}")
        
        if is_credit:
            self.current_balance += amount
            self.total_credits += amount
        else:
            self.current_balance -= amount  
            self.total_debits += amount
        
        self.transaction_count += 1
        self.last_updated = time.time()
    
    def validate_balance_equation(self) -> bool:
        """Validation équation comptable: current = initial + credits - debits"""
        computed_balance = self.initial_balance + self.total_credits - self.total_debits
        return abs(computed_balance - self.current_balance) < Decimal('1e-10')
    
    def get_balance_info(self) -> Dict[str, Any]:
        """Informations balance complètes"""
        return {
            'current_balance': str(self.current_balance),
            'initial_balance': str(self.initial_balance),
            'total_credits': str(self.total_credits),
            'total_debits': str(self.total_debits),
            'transaction_count': self.transaction_count,
            'balance_equation_valid': self.validate_balance_equation(),
            'last_updated': self.last_updated
        }


class Account:
    """
    Account comptable avec intégration DAG bidirectionnelle
    
    Fonctionnalités:
    - Source/sink nodes pour flux entrants/sortants
    - Balance tracking avec invariants conservation
    - Bijection Account ↔ Node pairs  
    - Metadata extensible pour domaines économiques
    - Validation automatique cohérence comptable
    """
    
    def __init__(self, account_id: str, initial_balance: Decimal = Decimal('0.0'), 
                 metadata: Optional[Dict[str, Any]] = None):
        self.account_id = account_id
        self.uuid = str(uuid.uuid4())
        self.metadata = metadata or {}
        self.created_at = time.time()
        
        # Nœuds DAG associés
        self.source_node = Node(f"{account_id}_source", {"account_id": account_id, "role": "source"})
        self.sink_node = Node(f"{account_id}_sink", {"account_id": account_id, "role": "sink"})
        
        # Balance comptable
        self.balance = AccountBalance(
            initial_balance=initial_balance,
            current_balance=initial_balance
        )
        
        # Mapping bidirectionnel nodes ↔ account
        self.source_node.metadata['account_reference'] = self
        self.sink_node.metadata['account_reference'] = self
        
        # Statistiques tracking
        self.stats = {
            'incoming_transactions': 0,
            'outgoing_transactions': 0,
            'balance_updates': 0,
            'validation_errors': 0
        }
    
    def add_incoming_transaction(self, edge: Edge, amount: Decimal) -> None:
        """
        Ajoute transaction entrante avec mise à jour balance
        
        Flow: external_source → account.sink_node
        Effect: Credit balance (+amount)
        """
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        
        if amount <= 0:
            raise ValueError(f"Transaction amount must be positive: {amount}")
        
        # Validation edge cible correcte
        if edge.target_node != self.sink_node:
            raise ValueError(f"Edge target mismatch: expected {self.sink_node.node_id}")
        
        # Ajout edge au sink node
        self.sink_node.add_incoming_edge(edge)
        
        # Mise à jour balance (crédit)
        self.balance.update_balance(amount, is_credit=True)
        
        # Update metadata edge avec amount
        edge.edge_metadata.context['transaction_amount'] = str(amount)
        edge.edge_metadata.context['account_id'] = self.account_id
        edge.edge_metadata.edge_type = EdgeType.TRANSACTION
        
        # Statistiques
        self.stats['incoming_transactions'] += 1
        self.stats['balance_updates'] += 1
    
    def add_outgoing_transaction(self, edge: Edge, amount: Decimal) -> None:
        """
        Ajoute transaction sortante avec mise à jour balance
        
        Flow: account.source_node → external_target  
        Effect: Debit balance (-amount)
        """
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        
        if amount <= 0:
            raise ValueError(f"Transaction amount must be positive: {amount}")
        
        # Validation edge source correcte
        if edge.source_node != self.source_node:
            raise ValueError(f"Edge source mismatch: expected {self.source_node.node_id}")
        
        # Validation balance suffisant (optionnel - peut être négatif selon règles)
        if self.balance.current_balance < amount:
            # Warning mais pas erreur (découvert autorisé selon contexte)
            self.metadata['balance_warning'] = f"Insufficient balance: {self.balance.current_balance} < {amount}"
        
        # Ajout edge au source node
        self.source_node.add_outgoing_edge(edge)
        
        # Mise à jour balance (débit)  
        self.balance.update_balance(amount, is_credit=False)
        
        # Update metadata edge
        edge.edge_metadata.context['transaction_amount'] = str(amount)
        edge.edge_metadata.context['account_id'] = self.account_id
        edge.edge_metadata.edge_type = EdgeType.TRANSACTION
        
        # Statistiques
        self.stats['outgoing_transactions'] += 1
        self.stats['balance_updates'] += 1
    
    def validate_account_integrity(self) -> List[str]:
        """
        Validation intégrité compte complète
        
        Invariants validés:
        - Balance equation correcte
        - Bijection nodes ↔ account coherente  
        - Metadata consistency
        - Edge amounts cohérentes avec balance
        """
        errors = []
        
        # Invariant 1: Balance equation
        if not self.balance.validate_balance_equation():
            errors.append(f"Balance equation violation: {self.balance.get_balance_info()}")
        
        # Invariant 2: Bijection nodes ↔ account
        source_ref = self.source_node.metadata.get('account_reference')
        sink_ref = self.sink_node.metadata.get('account_reference')
        
        if source_ref != self:
            errors.append(f"Source node reference mismatch: {source_ref} != {self}")
        if sink_ref != self:
            errors.append(f"Sink node reference mismatch: {sink_ref} != {self}")
        
        # Invariant 3: Node IDs coherence
        expected_source_id = f"{self.account_id}_source"
        expected_sink_id = f"{self.account_id}_sink"
        
        if self.source_node.node_id != expected_source_id:
            errors.append(f"Source node ID mismatch: {self.source_node.node_id} != {expected_source_id}")
        if self.sink_node.node_id != expected_sink_id:
            errors.append(f"Sink node ID mismatch: {self.sink_node.node_id} != {expected_sink_id}")
        
        # Invariant 4: Edge amounts consistency (approximative - basé sur metadata)
        total_incoming_metadata = Decimal('0')
        total_outgoing_metadata = Decimal('0')
        
        for edge in self.sink_node.incoming_edges.values():
            amount_str = edge.edge_metadata.context.get('transaction_amount', '0')
            total_incoming_metadata += Decimal(amount_str)
        
        for edge in self.source_node.outgoing_edges.values():
            amount_str = edge.edge_metadata.context.get('transaction_amount', '0')
            total_outgoing_metadata += Decimal(amount_str)
        
        # Tolérance pour comparaison
        credit_diff = abs(total_incoming_metadata - self.balance.total_credits)
        debit_diff = abs(total_outgoing_metadata - self.balance.total_debits)
        tolerance = Decimal('1e-8')
        
        if credit_diff > tolerance:
            errors.append(f"Credits metadata mismatch: {total_incoming_metadata} vs {self.balance.total_credits}")
        if debit_diff > tolerance:
            errors.append(f"Debits metadata mismatch: {total_outgoing_metadata} vs {self.balance.total_debits}")
        
        # Update error count
        if errors:
            self.stats['validation_errors'] += len(errors)
        
        return errors
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Résumé compte complet avec statistiques"""
        return {
            'account_id': self.account_id,
            'uuid': self.uuid,
            'balance_info': self.balance.get_balance_info(),
            'connectivity': {
                'source_node_id': self.source_node.node_id,
                'sink_node_id': self.sink_node.node_id,
                'incoming_edges_count': len(self.sink_node.incoming_edges),
                'outgoing_edges_count': len(self.source_node.outgoing_edges)
            },
            'stats': self.stats.copy(),
            'metadata': self.metadata.copy(),
            'created_at': self.created_at,
            'integrity_valid': len(self.validate_account_integrity()) == 0
        }
    
    def __str__(self) -> str:
        return f"Account({self.account_id}, balance={self.balance.current_balance}, in={len(self.sink_node.incoming_edges)}, out={len(self.source_node.outgoing_edges)})"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Account):
            return False
        return self.account_id == other.account_id
    
    def __hash__(self) -> int:
        return hash(self.account_id)


class CycleDetectionResult:
    """Résultat détection cycle avec path et diagnostique"""
    
    def __init__(self, has_cycle: bool, cycle_path: Optional[List[Node]] = None, 
                 cycle_edges: Optional[List[Edge]] = None):
        self.has_cycle = has_cycle
        self.cycle_path = cycle_path or []
        self.cycle_edges = cycle_edges or []
        self.detected_at = time.time()
    
    def get_cycle_description(self) -> str:
        """Description textuelle cycle détecté"""
        if not self.has_cycle:
            return "No cycle detected"
        
        path_str = " -> ".join([node.node_id for node in self.cycle_path])
        return f"Cycle detected: {path_str}"
    
    def get_cycle_length(self) -> int:
        """Longueur cycle détecté"""
        return len(self.cycle_path) if self.has_cycle else 0


class AntiCycleValidator:
    """
    Validateur cycles avec algorithme DFS robuste
    
    Algorithme DFS complet avec coloration:
    - WHITE: nœud non visité
    - GRAY: nœud en cours de visite (sur stack)
    - BLACK: nœud complètement visité
    
    Détection cycle: arête vers nœud GRAY = cycle back-edge
    """
    
    def __init__(self):
        self.stats = {
            'validations_performed': 0,
            'cycles_detected': 0,
            'max_dfs_depth': 0,
            'total_nodes_visited': 0,
            'validation_time_total_ms': 0
        }
    
    def validate_no_cycles(self, nodes: List[Node]) -> CycleDetectionResult:
        """
        Validation absence cycles via DFS avec coloration
        
        Complexité: O(V + E) où V = nodes, E = edges
        Mémoire: O(V) pour coloration et stack
        """
        start_time = time.time()
        self.stats['validations_performed'] += 1
        
        if not nodes:
            return CycleDetectionResult(has_cycle=False)
        
        # États coloration DFS  
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {node: WHITE for node in nodes}
        parent = {node: None for node in nodes}
        
        # Statistiques tracking
        max_depth = 0
        nodes_visited = 0
        
        def dfs_visit(node: Node, depth: int = 0) -> Optional[CycleDetectionResult]:
            nonlocal max_depth, nodes_visited
            max_depth = max(max_depth, depth)
            nodes_visited += 1
            
            color[node] = GRAY
            
            # Visite successeurs
            for edge in node.outgoing_edges.values():
                successor = edge.target_node
                
                if color[successor] == WHITE:
                    parent[successor] = node
                    cycle_result = dfs_visit(successor, depth + 1)
                    if cycle_result and cycle_result.has_cycle:
                        return cycle_result
                        
                elif color[successor] == GRAY:
                    # Back-edge détectée = cycle
                    cycle_path = self._reconstruct_cycle_path(node, successor, parent)
                    cycle_edges = self._get_cycle_edges(cycle_path)
                    self.stats['cycles_detected'] += 1
                    return CycleDetectionResult(True, cycle_path, cycle_edges)
            
            color[node] = BLACK
            return None
        
        # DFS depuis tous nœuds non visités
        for node in nodes:
            if color[node] == WHITE:
                cycle_result = dfs_visit(node)
                if cycle_result and cycle_result.has_cycle:
                    # Mise à jour stats
                    validation_time = (time.time() - start_time) * 1000
                    self.stats['max_dfs_depth'] = max(self.stats['max_dfs_depth'], max_depth)
                    self.stats['total_nodes_visited'] += nodes_visited
                    self.stats['validation_time_total_ms'] += validation_time
                    return cycle_result
        
        # Pas de cycle détecté
        validation_time = (time.time() - start_time) * 1000
        self.stats['max_dfs_depth'] = max(self.stats['max_dfs_depth'], max_depth)
        self.stats['total_nodes_visited'] += nodes_visited
        self.stats['validation_time_total_ms'] += validation_time
        
        return CycleDetectionResult(has_cycle=False)
    
    def _reconstruct_cycle_path(self, back_edge_source: Node, back_edge_target: Node, 
                              parent: Dict[Node, Optional[Node]]) -> List[Node]:
        """Reconstruction path cycle depuis back-edge"""
        cycle_path = [back_edge_target]
        current = back_edge_source
        
        # Remontée parents jusqu'à back_edge_target
        while current != back_edge_target and current is not None:
            cycle_path.append(current)
            current = parent[current]
        
        # Fermeture cycle
        cycle_path.append(back_edge_target)
        return cycle_path
    
    def _get_cycle_edges(self, cycle_path: List[Node]) -> List[Edge]:
        """Extraction edges du cycle path"""
        if len(cycle_path) < 2:
            return []
        
        cycle_edges = []
        for i in range(len(cycle_path) - 1):
            source_node = cycle_path[i]
            target_node = cycle_path[i + 1]
            
            # Recherche edge entre source et target
            for edge in source_node.outgoing_edges.values():
                if edge.target_node == target_node:
                    cycle_edges.append(edge)
                    break
        
        return cycle_edges
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Statistiques validation performance"""
        avg_time = 0
        if self.stats['validations_performed'] > 0:
            avg_time = self.stats['validation_time_total_ms'] / self.stats['validations_performed']
        
        return {
            'validations_performed': self.stats['validations_performed'],
            'cycles_detected': self.stats['cycles_detected'],
            'cycle_detection_rate': self.stats['cycles_detected'] / max(1, self.stats['validations_performed']),
            'max_dfs_depth': self.stats['max_dfs_depth'],
            'avg_validation_time_ms': round(avg_time, 3),
            'total_nodes_visited': self.stats['total_nodes_visited']
        }


# Utilitaires construction DAG

def create_node(node_id: str, metadata: Optional[Dict[str, Any]] = None) -> Node:
    """Factory function création nœud avec validation"""
    if not node_id or not node_id.strip():
        raise ValueError("Node ID cannot be empty")
    return Node(node_id.strip(), metadata)


def create_edge(edge_id: str, source_node: Node, target_node: Node, 
               weight: Union[Decimal, float, int, str] = Decimal('1.0'),
               edge_type: EdgeType = EdgeType.STRUCTURAL,
               metadata: Optional[Dict[str, Any]] = None) -> Edge:
    """Factory function création arête avec validation"""
    if not edge_id or not edge_id.strip():
        raise ValueError("Edge ID cannot be empty")
    return Edge(edge_id.strip(), source_node, target_node, weight, edge_type, metadata)


def connect_nodes(source_node: Node, target_node: Node, edge: Edge) -> None:
    """Connection bidirectionnelle nœuds avec arête"""
    source_node.add_outgoing_edge(edge)
    target_node.add_incoming_edge(edge)


def disconnect_nodes(source_node: Node, target_node: Node, edge_id: str) -> Optional[Edge]:
    """Déconnection bidirectionnelle nœuds"""
    edge = source_node.remove_outgoing_edge(edge_id)
    if edge:
        target_node.remove_incoming_edge(edge_id)
    return edge


def validate_dag_topology(nodes: List[Node]) -> CycleDetectionResult:
    """Validation topologie DAG complète"""
    validator = AntiCycleValidator()
    return validator.validate_no_cycles(nodes)


@dataclass
class DAGValidationResult:
    """Résultat validation complète structure DAG"""
    is_valid: bool
    cycle_detection: CycleDetectionResult
    connectivity_issues: List[str]
    integrity_violations: List[str]
    orphaned_nodes: List[Node]
    statistics: Dict[str, Any]
    validation_time_ms: float
    
    def get_summary(self) -> str:
        """Résumé validation lisible"""
        if self.is_valid:
            return f"✅ DAG Valid - {self.statistics.get('total_nodes', 0)} nodes, {self.statistics.get('total_edges', 0)} edges"
        else:
            issues = len(self.cycle_detection.cycle_path) + len(self.connectivity_issues) + len(self.integrity_violations)
            return f"❌ DAG Invalid - {issues} issues detected"


class DAGStructureValidator:
    """
    Validateur structure DAG production - Étape 2.1
    
    Validation complète:
    - Topologie anti-cycle (DFS)
    - Connectivité et intégrité nodes/edges
    - Orphaned nodes detection
    - Edge weight consistency
    - Account balance coherence
    - Performance monitoring
    """
    
    def __init__(self):
        self.cycle_validator = AntiCycleValidator()
        self.validation_stats = {
            'validations_performed': 0,
            'total_validation_time_ms': 0,
            'issues_detected_total': 0,
            'cycle_detections': 0,
            'connectivity_violations': 0,
            'integrity_violations': 0
        }
    
    def validate_complete_dag_structure(self, nodes: List[Node], 
                                       edges: List[Edge],
                                       accounts: Optional[List[Account]] = None) -> DAGValidationResult:
        """
        Validation structure DAG complète - Production ready
        
        Phases validation:
        1. Topologie anti-cycle via DFS
        2. Connectivité bidirectionnelle coherence
        3. Edge-Node consistency validation
        4. Orphaned nodes detection
        5. Account balance coherence (si fourni)
        6. Performance statistics collection
        
        Args:
            nodes: Liste tous nœuds DAG
            edges: Liste toutes arêtes DAG  
            accounts: Liste comptes pour validation balance (optionnel)
            
        Returns:
            DAGValidationResult: Résultats validation complets
        """
        start_time = time.time()
        self.validation_stats['validations_performed'] += 1
        
        # Phase 1: Cycle Detection
        cycle_result = self.cycle_validator.validate_no_cycles(nodes)
        if cycle_result.has_cycle:
            self.validation_stats['cycle_detections'] += 1
        
        # Phase 2: Connectivity Validation  
        connectivity_issues = self._validate_connectivity_coherence(nodes, edges)
        if connectivity_issues:
            self.validation_stats['connectivity_violations'] += len(connectivity_issues)
        
        # Phase 3: Integrity Validation
        integrity_violations = self._validate_nodes_edges_integrity(nodes, edges)
        if integrity_violations:
            self.validation_stats['integrity_violations'] += len(integrity_violations)
        
        # Phase 4: Orphaned Nodes Detection
        orphaned_nodes = self._detect_orphaned_nodes(nodes)
        
        # Phase 5: Account Balance Validation (si applicable)
        account_issues = []
        if accounts:
            account_issues = self._validate_accounts_coherence(accounts, nodes)
            integrity_violations.extend(account_issues)
        
        # Phase 6: Statistics Collection
        statistics = self._collect_dag_statistics(nodes, edges, accounts)
        
        # Calcul temps validation
        validation_time = (time.time() - start_time) * 1000
        self.validation_stats['total_validation_time_ms'] += validation_time
        
        # Détermination validité globale
        total_issues = (len(connectivity_issues) + len(integrity_violations) + 
                       len(orphaned_nodes))
        if cycle_result.has_cycle:
            total_issues += 1
            
        is_valid = (not cycle_result.has_cycle and total_issues == 0)
        
        if not is_valid:
            self.validation_stats['issues_detected_total'] += total_issues
        
        return DAGValidationResult(
            is_valid=is_valid,
            cycle_detection=cycle_result,
            connectivity_issues=connectivity_issues,
            integrity_violations=integrity_violations,
            orphaned_nodes=orphaned_nodes,
            statistics=statistics,
            validation_time_ms=validation_time
        )
    
    def _validate_connectivity_coherence(self, nodes: List[Node], 
                                        edges: List[Edge]) -> List[str]:
        """
        Validation cohérence connectivité bidirectionnelle
        """
        issues = []
        
        # Mapping edges par ID pour lookups efficaces
        edge_map = {edge.edge_id: edge for edge in edges}
        
        # Validation 1: Chaque edge dans nodes doit exister dans edges list
        for node in nodes:
            for edge_id, edge in node.incoming_edges.items():
                if edge_id not in edge_map:
                    issues.append(f"Node {node.node_id} references non-existent incoming edge {edge_id}")
                elif edge.target_node != node:
                    issues.append(f"Incoming edge {edge_id} target mismatch: {edge.target_node.node_id} != {node.node_id}")
            
            for edge_id, edge in node.outgoing_edges.items():
                if edge_id not in edge_map:
                    issues.append(f"Node {node.node_id} references non-existent outgoing edge {edge_id}")
                elif edge.source_node != node:
                    issues.append(f"Outgoing edge {edge_id} source mismatch: {edge.source_node.node_id} != {node.node_id}")
        
        # Validation 2: Chaque edge doit être référencé par ses source/target nodes
        for edge in edges:
            source_node = edge.source_node
            target_node = edge.target_node
            
            if edge.edge_id not in source_node.outgoing_edges:
                issues.append(f"Edge {edge.edge_id} not found in source node {source_node.node_id} outgoing edges")
            
            if edge.edge_id not in target_node.incoming_edges:
                issues.append(f"Edge {edge.edge_id} not found in target node {target_node.node_id} incoming edges")
        
        return issues
    
    def _validate_nodes_edges_integrity(self, nodes: List[Node], 
                                       edges: List[Edge]) -> List[str]:
        """
        Validation intégrité interne nodes et edges
        """
        violations = []
        
        # Node integrity checks
        node_ids_seen = set()
        for node in nodes:
            # Node ID uniqueness
            if node.node_id in node_ids_seen:
                violations.append(f"Duplicate node ID detected: {node.node_id}")
            node_ids_seen.add(node.node_id)
            
            # Node type cache coherence
            try:
                computed_type = node._compute_node_type()
                if node.get_node_type() != computed_type:
                    violations.append(f"Node {node.node_id} type cache inconsistency")
            except Exception as e:
                violations.append(f"Node {node.node_id} type computation error: {e}")
        
        # Edge integrity checks
        edge_ids_seen = set()
        for edge in edges:
            # Edge ID uniqueness
            if edge.edge_id in edge_ids_seen:
                violations.append(f"Duplicate edge ID detected: {edge.edge_id}")
            edge_ids_seen.add(edge.edge_id)
            
            # Edge weight validation
            if edge.weight < 0:
                violations.append(f"Edge {edge.edge_id} has negative weight: {edge.weight}")
            
            # Edge metadata coherence
            if edge.edge_metadata.weight != edge.weight:
                violations.append(f"Edge {edge.edge_id} metadata weight mismatch: {edge.edge_metadata.weight} != {edge.weight}")
        
        return violations
    
    def _detect_orphaned_nodes(self, nodes: List[Node]) -> List[Node]:
        """
        Détection nœuds orphelins (isolated nodes)
        """
        orphaned = []
        for node in nodes:
            if node.get_node_type() == NodeType.ISOLATED:
                orphaned.append(node)
        return orphaned
    
    def _validate_accounts_coherence(self, accounts: List[Account], 
                                   nodes: List[Node]) -> List[str]:
        """
        Validation cohérence comptes avec structure DAG
        """
        issues = []
        
        # Mapping nodes par ID
        node_map = {node.node_id: node for node in nodes}
        
        for account in accounts:
            # Validation account integrity interne
            account_errors = account.validate_account_integrity()
            for error in account_errors:
                issues.append(f"Account {account.account_id}: {error}")
            
            # Validation nodes existence dans DAG
            source_id = account.source_node.node_id
            sink_id = account.sink_node.node_id
            
            if source_id not in node_map:
                issues.append(f"Account {account.account_id} source node {source_id} not found in DAG")
            if sink_id not in node_map:
                issues.append(f"Account {account.account_id} sink node {sink_id} not found in DAG")
        
        return issues
    
    def _collect_dag_statistics(self, nodes: List[Node], edges: List[Edge],
                               accounts: Optional[List[Account]]) -> Dict[str, Any]:
        """
        Collection statistiques structure DAG
        """
        # Nodes statistics
        node_types = defaultdict(int)
        total_incoming = 0
        total_outgoing = 0
        
        for node in nodes:
            node_types[node.get_node_type().value] += 1
            total_incoming += len(node.incoming_edges)
            total_outgoing += len(node.outgoing_edges)
        
        # Edges statistics  
        edge_types = defaultdict(int)
        total_weight = Decimal('0')
        
        for edge in edges:
            edge_types[edge.edge_metadata.edge_type.value] += 1
            total_weight += edge.weight
        
        # Account statistics (si applicable)
        account_stats = {}
        if accounts:
            total_balance = sum(acc.balance.current_balance for acc in accounts)
            account_stats = {
                'total_accounts': len(accounts),
                'total_balance': str(total_balance),
                'accounts_with_errors': sum(1 for acc in accounts if len(acc.validate_account_integrity()) > 0)
            }
        
        return {
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'node_types': dict(node_types),
            'edge_types': dict(edge_types),
            'connectivity': {
                'total_incoming_connections': total_incoming,
                'total_outgoing_connections': total_outgoing,
                'avg_node_degree': (total_incoming + total_outgoing) / len(nodes) if nodes else 0
            },
            'weights': {
                'total_weight': str(total_weight),
                'avg_edge_weight': str(total_weight / len(edges)) if edges else '0'
            },
            **account_stats
        }
    
    def get_validation_performance_stats(self) -> Dict[str, Any]:
        """
        Statistiques performance validations
        """
        avg_time = 0
        if self.validation_stats['validations_performed'] > 0:
            avg_time = (self.validation_stats['total_validation_time_ms'] / 
                       self.validation_stats['validations_performed'])
        
        return {
            'validations_performed': self.validation_stats['validations_performed'],
            'avg_validation_time_ms': round(avg_time, 3),
            'total_issues_detected': self.validation_stats['issues_detected_total'],
            'cycle_detection_stats': self.cycle_validator.get_validation_stats(),
            'issue_breakdown': {
                'cycle_detections': self.validation_stats['cycle_detections'],
                'connectivity_violations': self.validation_stats['connectivity_violations'],
                'integrity_violations': self.validation_stats['integrity_violations']
            }
        }


# Export classes principales
__all__ = [
    'Node', 'Edge', 'NodeType', 'EdgeType', 'EdgeMetadata', 'Account',
    'CycleDetectionResult', 'AntiCycleValidator', 'DAGStructureValidator', 
    'DAGValidationResult', 'create_node', 'create_edge', 'connect_nodes', 
    'disconnect_nodes', 'validate_dag_topology'
]