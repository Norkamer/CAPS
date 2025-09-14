# Mathematical Foundations - Phase 2 Simplex

## LP Problem Formulation

### Decision Variables

**Definition**: Flux variables by NFA equivalence class
```
f_i ∈ ℝ₊ ∪ {0}  for each non-empty class C_i
where C_i = {paths | NFA(word(path)) = final_state_i}
```

**Economic Interpretation**:
- `f_i` = number of DAG paths ending at NFA final state `i`
- Represents **flux capacity** available for patterns matching state `i`
- Semantic grouping: equivalent paths from regex perspective

### Objective Function

**Standard Phase 1**: Feasibility testing only
```
Objective: Find f⃗ such that A·f⃗ satisfies all constraints
```

**Phase 1 Tableau**: Artificial variable minimization
```
min Σ(s_i)  where s_i are artificial slack variables
```

### Constraints per Transaction

For a transaction T with source S and target T associations:

#### Source Constraints (debiting account)
```
Primary:   Σ(f_i × coeff_i,R_s0) ≤ V_source_acceptable
Secondary: ∀k∈[1,n] : Σ(f_i × coeff_i,R_sk) ≤ 0
```

where:
- `R_s0` = primary regex of source measure
- `R_sk` = secondary regexes (forbidden patterns, bonuses)
- `coeff_i,R` = weight of regex R if state `i` matches R, else 0

#### Target Constraints (crediting account)
```
Primary:   Σ(f_i × coeff_i,R_t0) ≥ V_target_required
Secondary: ∀k∈[1,m] : Σ(f_i × coeff_i,R_tk) ≤ 0
```

### Coefficient Matrix

**Construction**: From RegexWeights of NFA final states
```python
def build_coefficient_matrix():
    coefficients = {}
    for state_id in nfa_final_states:
        for regex_weight in state.regex_weights:
            if regex_weight.measure_id == constraint.measure_id:
                coefficients[state_id] = regex_weight.weight_factor.to_decimal()
    return coefficients
```

**Concrete Example**:
```
NFA States: [state_A, state_B, state_C]
Regex "debit_pattern" weight 1.2 matches state_A and state_C
Regex "credit_pattern" weight 0.9 matches state_B

Source constraint: 1.2×f_A + 0×f_B + 1.2×f_C ≤ 150
Target constraint: 0×f_A + 0.9×f_B + 0×f_C ≥ 100
```

## Correctness Proofs

### Theorem 1: Equivalence with Classical Simplex

**Statement**:
```
∀ well-posed LP problem P :
TripleValidationSimplex(P, pivot) ≡ ClassicalSimplex(P)
```

**Proof**:
1. **Pivot validation**: If pivot compatible → warm-start = resolution from feasible point
2. **Guaranteed fallback**: If pivot incompatible → cold-start = standard resolution  
3. **Cross-validation**: If instability detected → verification by independent resolution
4. **Complete union**: Warm ∪ Cold ∪ Cross covers all possible cases

**Detailed Proof**:

*Case 1: Compatible Pivot*
- Hypothesis: `validate_pivot_compatibility(pivot, constraints) ∈ {HIGHLY_STABLE, MODERATELY_STABLE}`
- The pivot satisfies all constraints within geometric tolerance
- Warm-start from this pivot is equivalent to continuing a classical Simplex resolution
- Correctness: Since pivot is feasible, algorithm will converge to optimal solution

*Case 2: Incompatible Pivot*
- Hypothesis: `validate_pivot_compatibility(pivot, constraints) = MATHEMATICALLY_INFEASIBLE`
- Algorithm performs cold-start
- Equivalence: Cold-start ≡ ClassicalSimplex from origin
- Correctness: Standard algorithm guaranteed correct

*Case 3: Geometric Instability*
- Hypothesis: `validate_pivot_compatibility(pivot, constraints) = GEOMETRICALLY_UNSTABLE`
- Cross-validation by independent resolution
- If results agree: solution validated
- If results diverge: use most conservative resolution

### Theorem 2: Recursive Correctness with Pivot

**Statement**: For transaction sequence T₁, T₂, ..., Tₙ
```
∀n : OrientedSimplex(LPₙ, pivotₙ₋₁) = ClassicalSimplex(LPₙ)
```

**Proof by induction**:

**Base case P(1)**:
- LP₁ with pivot₀ = ∅ (no initial pivot)
- Cold-start resolution ≡ ClassicalSimplex ✓

**Inductive step P(n) ⟹ P(n+1)**:
- Hypothesis: pivotₙ correct after solving LPₙ
- LPₙ₊₁ = LPₙ ∪ {new constraints Tₙ₊₁}
- If pivotₙ compatible with LPₙ₊₁: valid warm-start
- If pivotₙ incompatible: fallback cold-start ≡ ClassicalSimplex
- In all cases: correct result ✓

**Maintained Invariant**: At each transaction, the stored pivot (if it exists) represents a feasible solution of the current LP problem.

### Theorem 3: Equivalence Class Consistency

**Statement**:
```
∀ frozen NFA N, ∀ path set C :
Partition P = {C₁, C₂, ..., Cₖ} is well-defined
where Cᵢ = {path ∈ C | N(word(path)) = final_state_i}
```

**Proof**:
1. **Deterministic function**: Frozen NFA ⟹ same path always gives same final state
2. **Disjunction**: ∀i≠j : Cᵢ ∩ Cⱼ = ∅ (path can reach only one final state)
3. **Coverage**: ⋃ᵢ Cᵢ ∪ C_reject = C (all paths are classified)

**Partition Properties**:
- **Temporal stability**: Frozen NFA guarantees stable classification during enumeration
- **Completeness**: All enumerated paths are classified
- **Mutual exclusivity**: No double counting between classes

## Numerical Stability

### Arithmetic Configuration

**Decimal Configuration**:
```python
from decimal import getcontext
getcontext().prec = 28  # 28 significant digits
```

**Advantages**:
- No floating-point rounding errors
- Exact representation of monetary values
- Deterministic comparisons

### Numerical Tolerances

**Constraint validation**:
```python
tolerance = Decimal('1e-10')  # 10⁻¹⁰ for comparisons
constraint_satisfied = |lhs - rhs| ≤ tolerance
```

**Pivot validation**:
```python
geometric_tolerance = Decimal('1e-12')  # Stricter for stability
pivot_feasible = violation ≤ geometric_tolerance
```

### Edge Case Handling

**Division by zero**:
```python
def safe_divide(a, b):
    if abs(b) < Decimal('1e-15'):
        raise SimplexError("Division by near-zero element")
    return a / b
```

**Overflow protection**:
```python
if new_log_magnitude > MAX_LOG_MAGNITUDE:
    raise OverflowError("Weight magnitude too large")
```

**Singularity detection**:
```python
def check_matrix_singularity(matrix):
    """Checks constraint matrix singularity"""
    determinant = compute_determinant(matrix)
    if abs(determinant) < Decimal('1e-14'):
        raise SimplexError("Constraint matrix is singular")
```

## Algorithmic Complexity

### Path Enumeration

**Worst case**: O(|E|^d) where d = maximum DAG depth
```
- |E| = number of outgoing edges per node  
- d ≤ number of accounts in the system
- Limited to max_paths to prevent explosion
```

**Average case**: O(|useful_paths|) with pruning
```
- Cycles detected and avoided: O(1) per detection
- Hash deduplication: O(log |paths|) per path
- Batch processing: constant memory
```

**Amortized analysis**:
```python
def amortized_complexity_analysis():
    """
    Amortized complexity over transaction sequence
    
    - First transaction: O(|E|^d) full enumeration
    - Subsequent transactions: O(δ|E|^d) where δ = incremental change
    - With pivot reuse: O(k×m²) where k << m
    """
    return {
        'first_transaction': 'O(|E|^d)',
        'subsequent_transactions': 'O(δ|E|^d)',
        'simplex_warm_start': 'O(k×m²)'
    }
```

### Simplex Phase 1

**Standard**: O(m³) where m = number of constraints
```
- Tableau construction: O(m×n) where n = number of variables
- Pivot operations: O(m²) per pivot  
- Number of pivots: ≤ C(m+n, m) theoretical, <<< practical
```

**With warm-start**: O(k×m²) where k = number of pivots from initial pivot
```
- k << m generally if pivot close to optimum
- Significant gain for transaction sequences
```

**Special case analysis**:
```python
def complexity_special_cases():
    return {
        'highly_constrained': 'O(m³) → O(m²) possible reduction',
        'sparse_constraints': 'O(m³) → O(m²×sparsity) with specialized algorithms',
        'high_pivot_reuse_rate': 'O(k×m²) where k ≈ log(m)',
        'low_pivot_reuse_rate': 'O(m³) degradation to standard case'
    }
```

### Frozen NFA

**Construction**: O(|regex| × |pattern_length|²) per regex
```
- Regex compilation: standard Python cost
- Final states: O(|states|) for identification
- Frozen = no additional cost during evaluation
```

**Evaluation**: O(|word| × |active_states|) per word
```
- |word| ≤ max_DAG_path_length
- |active_states| << |total_states| in practice
- Epsilon-closure: amortized over word length
```

**NFA optimizations**:
```python
class OptimizedNFAEvaluation:
    def __init__(self):
        self.state_transition_cache = {}
        self.word_evaluation_cache = {}
    
    def evaluate_with_caching(self, word):
        """NFA evaluation with caching"""
        if word in self.word_evaluation_cache:
            return self.word_evaluation_cache[word]
        
        result = self._evaluate_nfa(word)
        self.word_evaluation_cache[word] = result
        return result
```

## Invariants and Properties

### Structural Invariants

1. **Flux conservation**: `Σ f_i = |total_paths|` (constant)
2. **Non-negativity**: `∀i : f_i ≥ 0` (respected by construction)
3. **Taxonomic consistency**: `f(account, tx) deterministic ∀ tx`
4. **NFA stability**: `frozen NFA ⟹ temporally consistent classifications`

### Economic Properties

1. **Weak monotonicity**: Adding paths can only improve feasibility
2. **Locality**: Transaction affects only involved accounts
3. **Conservation**: Sum of debits ≈ sum of credits (modulo weights)
4. **Reversibility**: Inverse transaction feasible if original feasible

**Monotonicity Proof**:
```
Let C₁ ⊆ C₂ be two path sets
If LP(C₁) feasible and C₁ ⊆ C₂, then LP(C₂) feasible

Proof: 
- Solution f₁ of LP(C₁) can be extended to f₂ for LP(C₂)
- by defining f₂[i] = f₁[i] for i ∈ classes(C₁)
- and f₂[j] = 0 for j ∈ classes(C₂ \ C₁)
- f₂ satisfies all constraints of LP(C₂)
```

### Termination Guarantees

1. **Enumeration**: Acyclic DAG ⟹ finite number of paths
2. **Simplex**: Finite number of basic solutions ⟹ guaranteed termination
3. **Validation**: Finite tests ⟹ decision in finite time
4. **Global**: All sub-algorithms terminate ⟹ algorithm terminates

**Simplex Termination Proof**:
```
Theorem: Simplex Phase 1 algorithm terminates in finite steps

Proof:
1. Finite number of basic solutions: C(m+n, m)
2. Anti-cycling rule (Bland) guarantees no revisiting solution
3. Objective function strictly decreasing (or optimum reached)
4. Therefore termination in ≤ C(m+n, m) iterations
```

## Robustness Analysis

### Sensitivity to Perturbations

**Solution Stability**:
```python
def sensitivity_analysis(solution, perturbation_size):
    """Analyzes solution sensitivity to given perturbations"""
    
    # Test RHS constraint perturbations
    for i, constraint in enumerate(constraints):
        perturbed_bound = constraint.bound + perturbation_size
        new_solution = resolve_with_perturbed_constraint(i, perturbed_bound)
        
        sensitivity = compute_solution_distance(solution, new_solution)
        if sensitivity > STABILITY_THRESHOLD:
            return "UNSTABLE_TO_RHS_PERTURBATION"
    
    # Test constraint coefficient perturbations
    for constraint in constraints:
        for var_id in constraint.coefficients:
            original_coeff = constraint.coefficients[var_id]
            perturbed_coeff = original_coeff * (1 + perturbation_size)
            
            # Solve with perturbed coefficient
            new_solution = resolve_with_perturbed_coefficient(constraint, var_id, perturbed_coeff)
            
            sensitivity = compute_solution_distance(solution, new_solution)
            if sensitivity > STABILITY_THRESHOLD:
                return "UNSTABLE_TO_COEFFICIENT_PERTURBATION"
    
    return "STABLE"
```

### Condition Numbers

**Constraint Matrix Conditioning**:
```python
def compute_condition_number(constraint_matrix):
    """Computes condition number for numerical stability analysis"""
    
    # Singular values
    singular_values = compute_singular_values(constraint_matrix)
    
    # Condition number = ratio largest/smallest singular value
    condition_number = max(singular_values) / min(singular_values)
    
    if condition_number > CONDITION_THRESHOLD:
        raise SimplexError(f"Matrix is ill-conditioned: κ = {condition_number}")
    
    return condition_number
```

### Numerical Error Recovery

**Detection and Correction**:
```python
class NumericalErrorRecovery:
    def __init__(self):
        self.precision_escalation_levels = [28, 50, 100]
        self.current_precision_level = 0
    
    def solve_with_error_recovery(self, problem):
        """Resolution with automatic numerical error recovery"""
        
        for precision in self.precision_escalation_levels:
            try:
                # Increase precision
                getcontext().prec = precision
                
                # Attempt resolution
                solution = self.standard_solve(problem)
                
                # Validate solution
                if self.validate_solution_numerically(solution, problem):
                    return solution
                    
            except NumericalInstabilityError:
                # Try higher precision
                continue
        
        # If all precisions fail
        raise SimplexError("Cannot solve with required numerical stability")
    
    def validate_solution_numerically(self, solution, problem):
        """Rigorous numerical validation of solution"""
        
        # Test constraint satisfaction with adaptive tolerance
        tolerance = Decimal('1e-' + str(getcontext().prec - 2))
        
        for constraint in problem.constraints:
            if not constraint.is_satisfied(solution.variables, tolerance):
                return False
        
        # Test arithmetic consistency
        if not self.check_arithmetic_consistency(solution):
            return False
        
        return True
```

This rigorous mathematical foundation ensures that the Phase 2 implementation maintains absolute correctness guarantees while efficiently handling the numerical and algorithmic challenges inherent in solving large-scale linear programming problems.