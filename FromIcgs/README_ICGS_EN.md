# ICGS - Intelligent Computation Graph System

## Overview

ICGS is an intelligent computation graph system for validation and execution of complex economic transactions. The system uses a hybrid approach combining directed acyclic graphs (DAG), weighted non-deterministic finite automata (NFA), and linear programming to ensure transaction consistency and feasibility.

## Architecture

### Main Components
- **DAG**: Primary data structure representing accounts, transactions and flows
- **WeightedNFA**: Weighted regex pattern evaluation for path classification
- **Simplex Phase 1**: Economic feasibility validation before transaction integration
- **Weight Calculators**: Extensible weight computation system (imperative, functional, hybrid)

### Transaction Pipeline
1. **Construction**: Creation of nodes and edges in the DAG
2. **Evaluation**: Path classification via weighted NFA  
3. **Validation**: Economic feasibility testing via Simplex
4. **Integration**: Definitive addition if validation succeeds

## Simplex Phase 1 - Feasibility Validation

### Problem Solved
Determine if a proposed transaction can be executed without violating economic constraints defined by weighted regex patterns of associated measures.

### Mathematical Approach
- **Flux variables** `f_i ≥ 0`: number of DAG paths ending at NFA final state i
- **Constraints** generated from transaction associations:
  - Primary source: `Σ(f_i × weight_i) ≤ V_source_acceptable`
  - Primary target: `Σ(f_i × weight_i) ≥ V_target_required`  
  - Secondary patterns: `Σ(f_i × weight_i) ≤ 0` (forbidden)
- **Resolution**: Simplex Phase 1 with triple validation

### Implemented Components

#### AccountTaxonomy
Historized taxonomic function `f(account_id, transaction_number) → character` for DAG path → NFA-evaluable word conversion.

#### AnchoredWeightedNFA  
WeightedNFA extension with automatic anchoring to eliminate partial matches and "frozen" mode for temporal consistency.

#### DAGPathEnumerator
Optimized enumeration of paths from transaction edge to DAG sources with deduplication and cycle detection.

#### TripleValidationOrientedSimplex
Simplex Phase 1 solver with absolute mathematical guarantees:
- Rigorous pivot validation (geometric compatibility)
- Intelligent warm-start with cold-start fallback
- Cross-validation for unstable cases

### Mathematical Guarantees
- **Proven correctness**: Equivalence with classical Simplex
- **Proof by induction**: Validity preserved on transaction sequences  
- **Temporal consistency**: Frozen NFA and historized taxonomy
- **Numerical stability**: High-precision Decimal arithmetic

## Installation and Usage

### Project Structure
```
ICGS/
├── icgs-core/                    # Main components
│   ├── account_taxonomy.py       # Taxonomic function
│   ├── anchored_nfa.py          # NFA with anchoring
│   ├── path_enumerator.py       # Path enumeration  
│   ├── linear_programming.py    # LP structures
│   ├── simplex_solver.py        # Triple validation solver
│   └── ...                     # Existing components
├── docs/phase1/                 # Detailed documentation
│   ├── en/                     # English version
│   │   ├── README.md           # Complete overview
│   │   ├── architecture.md     # Technical architecture
│   │   ├── mathematical_foundations.md  # Mathematical foundations
│   │   └── api_reference.md    # API reference
│   └── ...                     # French version
└── test_icgs_integration.py    # Integration tests
```

### Testing and Validation
```bash
cd ICGS
python3 test_icgs_integration.py
```
**Expected result**: 5/5 tests passed (100%) - mathematical consistency validation.

### Usage Example
```python
from icgs_core import (
    AccountTaxonomy, AnchoredWeightedNFA, 
    LinearProgram, TripleValidationOrientedSimplex,
    build_source_constraint, build_target_constraint
)
from decimal import Decimal

# 1. Taxonomy configuration
taxonomy = AccountTaxonomy()
taxonomy.update_taxonomy({'alice': 'A', 'bob': 'B'}, 0)

# 2. NFA setup with transaction patterns
nfa = AnchoredWeightedNFA()
nfa.add_weighted_regex("source_measure", "A.*", Decimal('1.0'))
nfa.add_weighted_regex("target_measure", ".*B", Decimal('0.9'))
nfa.freeze()

# 3. LP problem construction (simulated flux variables)
program = LinearProgram("alice_to_bob")
program.add_variable("alice_state")
program.add_variable("bob_state")

program.add_constraint(build_source_constraint(
    {'alice_state': Decimal('5')}, Decimal('1.0'), Decimal('150')
))
program.add_constraint(build_target_constraint(
    {'bob_state': Decimal('3')}, Decimal('0.9'), Decimal('100')
))

# 4. Validation with mathematical guarantees
solver = TripleValidationOrientedSimplex()
solution = solver.solve_with_absolute_guarantees(program)

# 5. Decision
if solution.status == SolutionStatus.FEASIBLE:
    print("Transaction validated ✓")
else:
    print("Transaction rejected ✗")
```

## Implementation Status

### ✅ Phase 1 Complete (Simplex validation)
- Base infrastructure: taxonomy, anchored NFA, path enumeration
- Complete LP structures with automatic builders  
- Simplex solver with triple validation and mathematical guarantees
- Complete tests validated (5/5 passed)

### 🚧 Phase 2 Planned
- Complete integration with `DAG.add_transaction()`
- User interface for diagnostics  
- Performance optimizations and parallelization
- Large-scale real data testing

## Detailed Documentation

For complete documentation, see:
- **[docs/phase1/en/README.md](docs/phase1/en/README.md)** - Complete overview and pipeline
- **[docs/phase1/en/architecture.md](docs/phase1/en/architecture.md)** - Detailed technical architecture
- **[docs/phase1/en/mathematical_foundations.md](docs/phase1/en/mathematical_foundations.md)** - Mathematical foundations and proofs  
- **[docs/phase1/en/api_reference.md](docs/phase1/en/api_reference.md)** - Complete API reference

## License and Contribution

This system implements a mathematically rigorous architecture for economic transaction validation with formally proven correctness guarantees.