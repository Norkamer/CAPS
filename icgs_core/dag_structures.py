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


# Export classes principales
__all__ = [
    'Node', 'Edge', 'NodeType', 'EdgeType', 'EdgeMetadata',
    'CycleDetectionResult', 'AntiCycleValidator',
    'create_node', 'create_edge', 'connect_nodes', 'disconnect_nodes',
    'validate_dag_topology'
]