# Detailed Architecture - Phase 2 Simplex

## Technical Overview

### Phase 2 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Transaction Validation Phase 2              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌──────────────────┐                   │
│  │ AccountTaxonomy │────│ DAGPathEnumerator │                   │
│  │                 │    │                  │                   │
│  │ f(account, tx)  │    │ Path → Word      │                   │
│  │ → character     │    │ Enumeration      │                   │
│  │ (Historized)    │    │ (Sinks→Sources)  │                   │
│  └─────────────────┘    └──────────────────┘                   │
│           │                       │                            │
│           └───────┐       ┌───────┘                            │
│                   │       │                                    │
│                   ▼       ▼                                    │
│           ┌─────────────────────────┐                          │
│           │  AnchoredWeightedNFA    │                          │
│           │                         │                          │
│           │  Word → Final State     │                          │
│           │  (Frozen during enum)   │                          │
│           │  Equivalence Classes    │                          │
│           └─────────────────────────┘                          │
│                         │                                      │
│                         ▼                                      │
│           ┌─────────────────────────┐                          │
│           │    LinearProgram        │                          │
│           │                         │                          │
│           │  f_i variables          │                          │
│           │  Source/Target/         │                          │
│           │  Secondary constraints  │                          │
│           └─────────────────────────┘                          │
│                         │                                      │
│                         ▼                                      │
│    ┌──────────────────────────────────────────┐               │
│    │  TripleValidationOrientedSimplex         │               │
│    │                                          │               │
│    │  1. Geometric Pivot Validation           │               │
│    │  2. Warm/Cold Start                      │               │
│    │  3. Cross-validation                     │               │
│    │                                          │               │
│    │  Result: FEASIBLE | INFEASIBLE          │               │
│    └──────────────────────────────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 2 Data Flow

```
Transaction Edge ──┐
                   │
DAG Structure ─────┼──► Path Enumeration ──► Word Generation
                   │         │                      │
Account Taxonomy ──┘         │                      │
                            │                      │
                            ▼                      │
                     Path Batches                  │
                            │                      │
                            └──► NFA Evaluation ◄──┘
                                     │
                                     ▼
                             Final State Classes
                                     │
                                     ▼
                             LP Problem Building
                                     │
                                     ▼
                             Simplex Resolution
                                     │
                                     ▼
                             Transaction Decision
```

## Implementation Details

### 1. Main Data Classes

#### FluxVariable (Phase 2)
```python
@dataclass
class FluxVariable:
    variable_id: str        # NFA final state ID (f_i)
    value: Decimal         # Number of paths in this class
    lower_bound: Decimal   # Always 0 (non-negativity)
    upper_bound: Optional[Decimal]  # Usually None
    is_basic: bool         # State in Simplex tableau
```

#### LinearConstraint (Phase 2)
```python
@dataclass
class LinearConstraint:
    coefficients: Dict[str, Decimal]  # var_id → coefficient
    bound: Decimal                    # RHS
    constraint_type: ConstraintType   # LEQ, GEQ, EQ
    name: Optional[str]               # Debug/logging
```

#### SimplexSolution (Phase 2)
```python
@dataclass
class SimplexSolution:
    status: SolutionStatus           # FEASIBLE, INFEASIBLE, etc.
    variables: Dict[str, Decimal]    # Optimal solution
    pivot_operations: int            # Number of pivots
    used_warm_start: bool           # Warm-start used
    solver_statistics: Dict         # Detailed metrics
```

### 2. Key Algorithms

#### Path Enumeration (Reverse BFS)
```python
def enumerate_paths_to_sources(start_edge):
    queue = deque([(start_node, [start_node], {start_node.id})])
    seen_hashes = set()
    paths_count = 0
    
    while queue and paths_count < max_paths:
        current_node, path, visited = queue.popleft()
        
        if is_source_node(current_node):
            path_hash = compute_hash(path)
            if path_hash not in seen_hashes:
                yield path
                seen_hashes.add(path_hash)
                paths_count += 1
        else:
            for incoming_edge in current_node.incoming_edges:
                predecessor = incoming_edge.source
                if predecessor.id not in visited:  # Cycle prevention
                    queue.append((predecessor, path + [predecessor], 
                                visited | {predecessor.id}))
```

#### Geometric Pivot Validation
```python
def validate_pivot_compatibility(pivot, constraints):
    # Test 1: Strict feasibility
    for constraint in constraints:
        violation = constraint.get_violation(pivot)
        if violation > tolerance:
            return MATHEMATICALLY_INFEASIBLE
    
    # Test 2: Geometric stability  
    stability = compute_geometric_stability(pivot, constraints)
    
    if stability > 0.9:
        return HIGHLY_STABLE
    elif stability > 0.5:
        return MODERATELY_STABLE
    else:
        return GEOMETRICALLY_UNSTABLE
```

#### Simplex Phase 1 Tableau Construction
```python
def build_phase1_tableau(problem):
    # Build tableau with artificial variables
    # Phase 1 objective: minimize Σ(artificial_variables)
    
    tableau = []
    artificial_vars = []
    
    # For each ≥ or = constraint, add artificial variable
    for i, constraint in enumerate(problem.constraints):
        if constraint.type in (GEQ, EQ):
            artificial_vars.append(f"a_{i}")
    
    # Eliminate artificial variables from objective function
    for basic_var in basic_vars:
        if basic_var in artificial_vars:
            # Pivot operation to eliminate from objective
            eliminate_from_objective(tableau, basic_var)
    
    return tableau, artificial_vars
```

### 3. Control Structures

#### Anchored NFA State Management
```python
class AnchoredWeightedNFA(WeightedNFA):
    def __init__(self):
        self.is_frozen = False
        self.anchor_suffix = ".*$"
    
    def freeze(self):
        """Freezes NFA for consistency during enumeration"""
        self.ensure_all_anchors()
        self.is_frozen = True
    
    def clone_for_transaction(self, tx_regexes):
        """Creates frozen clone with transaction regexes"""
        clone = AnchoredWeightedNFA()
        # Copy existing regexes
        # Add transaction regexes
        clone.freeze()  # Freeze immediately
        return clone
```

#### Cache and Historization
```python
class AccountTaxonomy:
    def __init__(self):
        # {transaction_number: {account_id: character}}
        self.historical_mappings = {}
        self.current_mappings = {}
        self.version = 0
    
    def get_character(self, account_id, tx_number):
        """Find most recent mapping ≤ tx_number"""
        for tx_num in sorted(self.historical_mappings.keys(), reverse=True):
            if tx_num <= tx_number:
                if account_id in self.historical_mappings[tx_num]:
                    return self.historical_mappings[tx_num][account_id]
        
        # If not found, assign new character
        return self._assign_new_character(account_id, tx_number)
```

#### Mathematically Rigorous Pivot Manager
```python
class MathematicallyRigorousPivotManager:
    def __init__(self, tolerance=Decimal('1e-12')):
        self.tolerance = tolerance
        self.pivot_history = []
        self.stability_metrics = {}
    
    def validate_pivot_compatibility(self, old_pivot, new_constraints):
        """Tests rigorous compatibility of pivot with new constraints"""
        
        # Feasibility validation
        for constraint in new_constraints:
            violation = constraint.get_violation(old_pivot)
            if violation > self.tolerance:
                return PivotStatus.MATHEMATICALLY_INFEASIBLE
        
        # Geometric stability computation
        geometry_score = self._compute_geometric_stability(old_pivot, new_constraints)
        
        # Stability classification
        if geometry_score > 0.95:
            return PivotStatus.HIGHLY_STABLE
        elif geometry_score > 0.7:
            return PivotStatus.MODERATELY_STABLE
        else:
            return PivotStatus.GEOMETRICALLY_UNSTABLE
    
    def _compute_geometric_stability(self, pivot, constraints):
        """Computes geometric stability score of pivot"""
        distances = []
        for constraint in constraints:
            # Distance to constraint boundary
            distance = abs(constraint.evaluate(pivot) - constraint.bound)
            distances.append(distance)
        
        # Score based on minimum distance and distribution
        min_distance = min(distances)
        avg_distance = sum(distances) / len(distances)
        
        # Normalization and composite score
        stability = min(min_distance / self.tolerance, 1.0) * 0.7 + \
                   min(avg_distance / self.tolerance, 1.0) * 0.3
        
        return stability
```

## Design Patterns Used

### 1. Strategy Pattern
- Abstract `WeightCalculator` with multiple implementations
- `ConstraintType` enum for different constraint types
- Pivot validation with multiple statuses

### 2. Builder Pattern
- `LinearProgram` incremental construction
- `build_*_constraint()` functions for specialized construction
- Simplex tableau construction by phases

### 3. Template Method
- `TripleValidationSimplex` with defined steps
- `DAGPathEnumerator` with batch strategies
- Validation with automatic fallback

### 4. Observer Pattern (implicit)
- Integrated statistics and logging
- Performance metrics collection
- Continuous consistency validation

### 5. Copy-on-Write Pattern
- Temporary validation environments
- Original state preservation during tests
- Atomic commits after successful validation

## Error Handling

### Exception Hierarchy
```
Exception
├── TaxonomyError          (conflicts, invalid alphabet)
├── AnchoringError         (frozen NFA, invalid patterns)
├── PathEnumerationError   (explosion, cycles)
├── SimplexError           (invalid pivot, corrupted tableau)
└── ValidationError        (inconsistent constraints)
```

### Recovery Strategies
1. **Graceful degradation**: Cold-start if pivot invalid
2. **Cross-validation**: Cross-checking for unstable cases
3. **Early termination**: Stop if explosion detected
4. **Rollback**: Restore previous state if failure

### Explosion Protection
```python
class PathEnumerationSafety:
    def __init__(self, max_paths=10000, max_depth=50):
        self.max_paths = max_paths
        self.max_depth = max_depth
        self.explosion_threshold = max_paths * 0.8
    
    def check_explosion_risk(self, current_paths, current_depth):
        if current_paths > self.explosion_threshold:
            raise PathEnumerationError(
                f"Risk of explosion detected: {current_paths} paths at depth {current_depth}"
            )
        
        if current_depth > self.max_depth:
            raise PathEnumerationError(
                f"Maximum depth exceeded: {current_depth} > {self.max_depth}"
            )
```

## Metrics and Monitoring

### Collected Metrics
- `paths_enumerated`, `paths_deduplicated`, `cycles_detected`
- `warm_starts_used`, `cold_starts_used`, `pivot_rejections`
- `iterations`, `pivot_operations` per resolution
- `alphabet_usage_ratio`, `characters_available`
- `simplex_validations`, `simplex_rejections`

### Diagnostic Points
```python
class Phase2Diagnostics:
    def get_comprehensive_stats(self):
        return {
            # NFA state
            'nfa_state': {
                'is_frozen': self.anchored_nfa.is_frozen if self.anchored_nfa else None,
                'states_count': len(self.anchored_nfa.get_final_states()) if self.anchored_nfa else 0,
                'patterns_count': len(self.anchored_nfa.regex_patterns) if self.anchored_nfa else 0
            },
            
            # Taxonomy statistics
            'taxonomy_state': self.account_taxonomy.get_statistics(),
            
            # Solver performance
            'solver_performance': self.simplex_solver.get_solver_statistics(),
            
            # Problem validation
            'problem_validation': {
                'variables_count': len(self.current_problem.variables) if hasattr(self, 'current_problem') else 0,
                'constraints_count': len(self.current_problem.constraints) if hasattr(self, 'current_problem') else 0
            },
            
            # Pivot state
            'pivot_state': {
                'has_stored_pivot': self.stored_pivot is not None,
                'pivot_size': len(self.stored_pivot) if self.stored_pivot else 0
            }
        }
```

## Performance Architecture

### Implemented Optimizations

#### 1. Pivot Reuse
```python
def solve_with_pivot_reuse(self, problem, old_pivot=None):
    if old_pivot:
        # Validate geometric compatibility
        pivot_status = self.pivot_manager.validate_pivot_compatibility(
            old_pivot, problem.constraints
        )
        
        if pivot_status in [PivotStatus.HIGHLY_STABLE, PivotStatus.MODERATELY_STABLE]:
            # Attempt warm-start
            return self._solve_warm_start(problem, old_pivot)
    
    # Fallback cold-start
    return self._solve_cold_start(problem)
```

#### 2. Batch Path Processing
```python
class BatchPathProcessor:
    def __init__(self, batch_size=100):
        self.batch_size = batch_size
        self.processed_count = 0
    
    def process_paths_batched(self, path_generator):
        batch = []
        for path in path_generator:
            batch.append(path)
            
            if len(batch) >= self.batch_size:
                yield self._process_batch(batch)
                batch = []
                self.processed_count += self.batch_size
        
        # Process final batch
        if batch:
            yield self._process_batch(batch)
```

#### 3. Efficient Deduplication
```python
class PathDeduplicator:
    def __init__(self):
        self.seen_hashes = set()
        self.hash_collisions = 0
    
    def compute_path_hash(self, path):
        """Fast hash based on node IDs and length"""
        path_str = "->".join([node.id for node in path])
        return hash(path_str + str(len(path)))
    
    def is_duplicate(self, path):
        path_hash = self.compute_path_hash(path)
        if path_hash in self.seen_hashes:
            return True
        
        self.seen_hashes.add(path_hash)
        return False
```

## Security and Robustness

### Input Validation
```python
def validate_transaction_inputs(self, transaction, source_account_id, target_account_id):
    """Rigorous validation of inputs before processing"""
    
    # Transaction validation
    if not isinstance(transaction, Transaction):
        raise ValidationError("Transaction must be Transaction instance")
    
    # Account validation
    if source_account_id not in self.accounts:
        raise ValidationError(f"Source account '{source_account_id}' not found")
    
    if target_account_id not in self.accounts:
        raise ValidationError(f"Target account '{target_account_id}' not found")
    
    # Measure validation
    if not transaction.source_association or not transaction.target_association:
        raise ValidationError("Transaction must have both source and target associations")
    
    # Value validation
    if transaction.source_association.value <= 0:
        raise ValidationError("Source association value must be positive")
    
    if transaction.target_association.value <= 0:
        raise ValidationError("Target association value must be positive")
```

### Operation Atomicity
```python
class AtomicTransactionProcessor:
    def __init__(self, dag):
        self.dag = dag
        self.rollback_stack = []
    
    def execute_with_rollback(self, operations):
        """Executes operations with rollback capability"""
        try:
            for operation in operations:
                # Save state for rollback
                backup = self._create_operation_backup(operation)
                self.rollback_stack.append(backup)
                
                # Execute operation
                operation.execute()
            
            # Success: clear rollback stack
            self.rollback_stack.clear()
            return True
            
        except Exception as e:
            # Failure: perform rollback
            self._perform_rollback()
            raise e
    
    def _perform_rollback(self):
        """Rollback all operations in stack"""
        while self.rollback_stack:
            backup = self.rollback_stack.pop()
            backup.restore()
```

This Phase 2 architecture provides a solid and extensible foundation for economic transaction validation with absolute mathematical guarantees and production robustness.