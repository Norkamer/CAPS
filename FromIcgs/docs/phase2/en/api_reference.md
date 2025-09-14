# API Reference - Phase 2 Simplex

## DAG (Extended Phase 2 Class)

### New Phase 2 Properties

#### account_taxonomy
```python
account_taxonomy: AccountTaxonomy
```
Taxonomy instance for path → word conversion

#### anchored_nfa  
```python
anchored_nfa: Optional[AnchoredWeightedNFA]
```
Anchored NFA for pattern classification with temporal freezing

#### path_enumerator
```python
path_enumerator: DAGPathEnumerator  
```
Path enumerator for DAG traversal (sinks → sources)

#### simplex_solver
```python
simplex_solver: TripleValidationOrientedSimplex
```
Simplex Phase 1 solver with triple validation

#### stored_pivot
```python
stored_pivot: Optional[Dict[str, Decimal]]
```
Stored pivot for warm-start between transactions

#### transaction_counter
```python
transaction_counter: int
```
Counter for taxonomic historization

### Extended add_transaction Method

#### add_transaction (Phase 2)
```python
add_transaction(source_account_id: str, target_account_id: str, transaction: 'Transaction') -> bool
```

**Extended validation pipeline**:
1. NFA validation (existing Phase 1)
2. **Simplex validation (Phase 2 NEW)**
3. Transaction commit

**Returns**: `True` if transaction accepted, `False` if rejected

**Raises**: `ValueError` if invalid parameters

### New Phase 2 Internal Methods

#### _validate_transaction_simplex
```python
_validate_transaction_simplex(transaction: 'Transaction', source_account_id: str, target_account_id: str) -> bool
```

Validates economic feasibility via Simplex Phase 1.

**Process**:
1. Update taxonomy with transaction accounts
2. Create temporary anchored NFA
3. Enumerate paths from transaction edge to DAG sources
4. Build LP problem with flux variables and constraints
5. Solve with Simplex Phase 1 triple validation

**Returns**: `True` if economically feasible

#### _update_taxonomy_for_transaction
```python
_update_taxonomy_for_transaction(source_account_id: str, target_account_id: str) -> None
```

Updates taxonomy with accounts involved in transaction.

**Parameters**:
- `source_account_id`: Source account identifier
- `target_account_id`: Target account identifier

#### _create_transaction_nfa
```python
_create_transaction_nfa(transaction: 'Transaction') -> AnchoredWeightedNFA
```

Creates temporary anchored NFA with transaction measures.

**Returns**: Frozen NFA with transaction regexes

#### _create_temporary_transaction_edge
```python
_create_temporary_transaction_edge(source_account_id: str, target_account_id: str, transaction: 'Transaction') -> Edge
```

Creates temporary transaction edge for path enumeration.

**Returns**: Temporary edge connecting source and target sinks

#### _enumerate_and_classify_paths
```python
_enumerate_and_classify_paths(transaction_edge: Edge, nfa: AnchoredWeightedNFA) -> Dict[str, List]
```

Enumerates paths and classifies them by NFA final state.

**Returns**: Dictionary `final_state_id → path_list`

#### _build_lp_from_path_classes
```python
_build_lp_from_path_classes(path_classes: Dict[str, List], transaction: 'Transaction', nfa: AnchoredWeightedNFA) -> LinearProgram
```

Builds LP problem from path classes.

**Returns**: LP program with flux variables and economic constraints

## AccountTaxonomy

### Constructor
```python
AccountTaxonomy(alphabet: Optional[str] = None)
```
- `alphabet`: String containing all allowed characters. If None, uses default alphabet.

### Main Methods

#### get_character
```python
get_character(account_id: str, transaction_number: int) -> str
```
Retrieves character associated with account for given transaction number.

**Parameters**:
- `account_id`: Unique account identifier
- `transaction_number`: Transaction number for historization

**Returns**: Unicode character representing the account

**Raises**: `TaxonomyError` if account not found

#### update_taxonomy
```python
update_taxonomy(mappings: Dict[str, str], transaction_number: int) -> None
```
Updates taxonomy with new account → character mappings.

**Parameters**:
- `mappings`: Dictionary account_id → character
- `transaction_number`: Transaction number to associate

**Raises**: `TaxonomyError` if conflicts or invalid characters

#### assign_new_characters
```python
assign_new_characters(account_ids: Set[str], transaction_number: int) -> Dict[str, str]
```
Automatically assigns characters to accounts without mappings.

**Returns**: Dictionary of new mappings created

### Utility Methods

#### get_alphabet
```python
get_alphabet() -> Set[str]
```
Returns the alphabet used by this taxonomy.

#### get_statistics
```python
get_statistics() -> Dict[str, any]
```
Returns statistics on taxonomy usage.

**Return structure**:
```python
{
    'total_accounts': int,
    'total_transactions': int,
    'alphabet_size': int,
    'alphabet_usage_ratio': float,
    'current_version': int,
    'characters_used': int,
    'characters_available': int
}
```

## AnchoredWeightedNFA

### Constructor
```python
AnchoredWeightedNFA(nfa_id: Optional[str] = None, 
                   weight_calculator: Optional['WeightCalculator'] = None)
```

### Main Methods

#### add_weighted_regex
```python
add_weighted_regex(measure_id: str, pattern: str, weight: Decimal) -> None
```
Adds weighted regex with automatic anchoring.

**Raises**: `AnchoringError` if NFA is frozen

#### freeze/unfreeze
```python
freeze() -> None
unfreeze() -> None
is_nfa_frozen() -> bool
```
Controls frozen state of NFA for consistency during enumeration.

#### get_final_states
```python
get_final_states() -> List[NFAState]
```
Returns all final states of the NFA.

#### get_regex_weights_for_final_state
```python
get_regex_weights_for_final_state(state: NFAState) -> Set[RegexWeight]
```
Returns RegexWeights associated with specific final state.

#### evaluate_to_final_state
```python
evaluate_to_final_state(text: str) -> Optional[str]
```
Evaluates text and returns ID of final state reached, if any.

#### clone_for_transaction
```python
clone_for_transaction(transaction_regexes: List[Tuple[str, str, Decimal]]) -> 'AnchoredWeightedNFA'
```
Creates frozen clone with additional regexes for transaction.

## DAGPathEnumerator

### Constructor
```python
DAGPathEnumerator(taxonomy: AccountTaxonomy, 
                 max_paths: int = 10000, 
                 batch_size: int = 100)
```

### Main Methods

#### enumerate_paths_to_sources
```python
enumerate_paths_to_sources(start_edge: Edge) -> Iterator[List[Node]]
```
Enumerates all paths from start_edge to DAG sources.

**Yields**: Lists of nodes representing paths

**Raises**: `PathEnumerationError` if explosion or failure

#### path_to_word
```python
path_to_word(path: List[Node], transaction_number: int) -> str
```
Converts path to word via taxonomic function.

#### estimate_total_paths
```python
estimate_total_paths(start_edge: Edge, max_depth: int = 5) -> int
```
Estimates total number of paths without full enumeration.

### Utility Methods

#### get_path_statistics
```python
get_path_statistics() -> Dict[str, int]
```
Returns enumeration statistics.

## TripleValidationOrientedSimplex

### Constructor
```python
TripleValidationOrientedSimplex(max_iterations: int = 10000,
                               tolerance: Decimal = Decimal('1e-10'))
```

### Main Methods

#### solve_with_absolute_guarantees
```python
solve_with_absolute_guarantees(problem: LinearProgram,
                              old_pivot: Optional[Dict[str, Decimal]] = None) -> SimplexSolution
```
Solves with absolute mathematical guarantees via triple validation.

**Returns**: `SimplexSolution` with status and variables

**Process**:
1. Pivot validation (if provided)
2. Warm-start if pivot compatible
3. Cold-start fallback if necessary  
4. Cross-validation if instability detected

#### Internal Methods (testing/debugging)

#### _solve_warm_start
```python
_solve_warm_start(problem: LinearProgram, 
                 pivot: Dict[str, Decimal]) -> SimplexSolution
```

#### _solve_cold_start
```python
_solve_cold_start(problem: LinearProgram) -> SimplexSolution
```

### Utility Methods

#### get_solver_statistics
```python
get_solver_statistics() -> Dict[str, int]
```
Returns solver usage statistics.

## MathematicallyRigorousPivotManager

### Constructor
```python
MathematicallyRigorousPivotManager(tolerance: Decimal = Decimal('1e-12'))
```

### Main Methods

#### validate_pivot_compatibility
```python
validate_pivot_compatibility(old_pivot: Dict[str, Decimal],
                            new_constraints: List[LinearConstraint]) -> PivotStatus
```
Tests rigorous compatibility of pivot with new constraints.

**Returns**: `PivotStatus` indicating compatibility level

**Levels**:
- `HIGHLY_STABLE`: Pivot very stable geometrically
- `MODERATELY_STABLE`: Pivot moderately stable
- `GEOMETRICALLY_UNSTABLE`: Pivot geometrically unstable
- `MATHEMATICALLY_INFEASIBLE`: Pivot violates constraints

## Utility Functions

### Constraint Builders

#### build_source_constraint
```python
build_source_constraint(nfa_state_weights: Dict[str, Decimal],
                       primary_regex_weight: Decimal,
                       acceptable_value: Decimal,
                       constraint_name: str = "source_primary") -> LinearConstraint
```
Builds primary source constraint: `Σ(f_i × weight_i) ≤ V_source_acceptable`

#### build_target_constraint
```python
build_target_constraint(nfa_state_weights: Dict[str, Decimal],
                       primary_regex_weight: Decimal,
                       required_value: Decimal,
                       constraint_name: str = "target_primary") -> LinearConstraint
```
Builds primary target constraint: `Σ(f_i × weight_i) ≥ V_target_required`

#### build_secondary_constraint
```python
build_secondary_constraint(nfa_state_weights: Dict[str, Decimal],
                          secondary_regex_weight: Decimal,
                          constraint_name: str = "secondary") -> LinearConstraint
```
Builds secondary constraint: `Σ(f_i × weight_i) ≤ 0`

## Enums and Types

### SolutionStatus
```python
class SolutionStatus(Enum):
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    UNBOUNDED = "unbounded"
    OPTIMAL = "optimal"
    ERROR = "error"
    UNKNOWN = "unknown"
```

### PivotStatus
```python
class PivotStatus(Enum):
    HIGHLY_STABLE = "highly_stable"
    MODERATELY_STABLE = "moderately_stable"
    GEOMETRICALLY_UNSTABLE = "geometrically_unstable"
    MATHEMATICALLY_INFEASIBLE = "mathematically_infeasible"
```

## Exceptions

### TaxonomyError
Raised for taxonomy errors (conflicts, invalid alphabet).

### AnchoringError
Raised for NFA anchoring errors (frozen NFA, invalid patterns).

### PathEnumerationError
Raised during path enumeration (explosion, cycles).

### SimplexError
Raised during Simplex operations (invalid pivot, corrupted tableau).

## Complete Usage Example

### Transaction Validation with Phase 2

```python
# 1. Setup
from icgs_core import DAG, Account, Transaction, Association, Measure, WeightedRegex
from decimal import Decimal

# Create DAG with Phase 2 components (automatic)
dag = DAG()

# 2. Add accounts
alice = Account("alice")  
bob = Account("bob")
dag.add_account(alice)
dag.add_account(bob)

# 3. Configure economic measures
source_measure = Measure("debit_capacity", [
    WeightedRegex("A.*", Decimal('1.0')),      # Alice can debit
    WeightedRegex("FRAUD.*", Decimal('-10.0'))  # Fraud pattern penalized
])

target_measure = Measure("credit_requirement", [
    WeightedRegex(".*B", Decimal('0.9')),      # Bob receives with factor 0.9
    WeightedRegex("BONUS.*", Decimal('1.2'))   # Bonus pattern enhanced
])

# 4. Create transaction
source_assoc = Association(source_measure, Decimal('200'))  # Alice can provide 200
target_assoc = Association(target_measure, Decimal('150'))  # Bob needs 150

transaction = Transaction("alice_to_bob", source_assoc, target_assoc)

# 5. Automatic Phase 2 validation
success = dag.add_transaction("alice", "bob", transaction)

if success:
    print("✓ Transaction validated - economic feasibility confirmed")
    
    # Access Phase 2 statistics
    if dag.stats:
        print(f"Simplex validations: {dag.stats['simplex_validations']}")
        print(f"Simplex rejections: {dag.stats['simplex_rejections']}")
        print(f"Warm starts: {dag.stats['warm_starts_used']}")
        print(f"Cold starts: {dag.stats['cold_starts_used']}")
    
    # Access taxonomy state
    taxonomy_stats = dag.account_taxonomy.get_statistics()
    print(f"Mapped accounts: {taxonomy_stats['total_accounts']}")
    print(f"Historized transactions: {taxonomy_stats['total_transactions']}")
    
    # Access solver metrics
    solver_stats = dag.simplex_solver.get_solver_statistics()
    print(f"Total solves: {solver_stats.get('total_solves', 0)}")
    
else:
    print("✗ Transaction rejected - economic infeasibility detected")
```

### Advanced Configuration

```python
# Configure numerical precision
from decimal import getcontext
getcontext().prec = 50  # Ultra-high precision

# Configure custom solver
custom_solver = TripleValidationOrientedSimplex(
    max_iterations=50000,
    tolerance=Decimal('1e-15')
)

# Configure path enumerator
custom_enumerator = DAGPathEnumerator(
    dag.account_taxonomy,
    max_paths=50000,
    batch_size=500
)

# Replace default components
dag.simplex_solver = custom_solver
dag.path_enumerator = custom_enumerator

# Validation with advanced configuration
result = dag.add_transaction("alice", "bob", complex_transaction)
```

This Phase 2 API maintains complete compatibility with Phase 1 while adding rigorous economic validation with absolute mathematical guarantees.