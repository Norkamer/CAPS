# Architecture Détaillée - Phase 2 Simplex

## Vue d'ensemble Technique

### Diagramme de Composants Phase 2

```
┌─────────────────────────────────────────────────────────────────┐
│                    Validation Transaction Phase 2               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌──────────────────┐                   │
│  │ AccountTaxonomy │────│ DAGPathEnumerator │                   │
│  │                 │    │                  │                   │
│  │ f(compte, tx)   │    │ Chemin → Mot     │                   │
│  │ → caractère     │    │ Énumération      │                   │
│  │ (Historisé)     │    │ (Puits→Sources)  │                   │
│  └─────────────────┘    └──────────────────┘                   │
│           │                       │                            │
│           └───────┐       ┌───────┘                            │
│                   │       │                                    │
│                   ▼       ▼                                    │
│           ┌─────────────────────────┐                          │
│           │  AnchoredWeightedNFA    │                          │
│           │                         │                          │
│           │  Mot → État Final       │                          │
│           │  (Gelé pendant enum)    │                          │
│           │  Classes Équivalence    │                          │
│           └─────────────────────────┘                          │
│                         │                                      │
│                         ▼                                      │
│           ┌─────────────────────────┐                          │
│           │    LinearProgram        │                          │
│           │                         │                          │
│           │  Variables f_i          │                          │
│           │  Contraintes Source/    │                          │
│           │  Cible/Secondaires      │                          │
│           └─────────────────────────┘                          │
│                         │                                      │
│                         ▼                                      │
│    ┌──────────────────────────────────────────┐               │
│    │  TripleValidationOrientedSimplex         │               │
│    │                                          │               │
│    │  1. Validation Pivot Géométrique        │               │
│    │  2. Démarrage Chaud/Froid                │               │
│    │  3. Validation Croisée                   │               │
│    │                                          │               │
│    │  Résultat: FAISABLE | INFAISABLE        │               │
│    └──────────────────────────────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Flux de Données Phase 2

```
Arête Transaction ──┐
                    │
Structure DAG ──────┼──► Énumération Chemins ──► Génération Mots
                    │         │                      │
Taxonomie Comptes ──┘         │                      │
                             │                      │
                             ▼                      │
                      Lots de Chemins              │
                             │                      │
                             └──► Évaluation NFA ◄──┘
                                      │
                                      ▼
                              Classes États Finaux
                                      │
                                      ▼
                              Construction Problème LP
                                      │
                                      ▼
                              Résolution Simplex
                                      │
                                      ▼
                              Décision Transaction
```

## Détails d'Implémentation

### 1. Classes de Données Principales

#### FluxVariable (Phase 2)
```python
@dataclass
class FluxVariable:
    variable_id: str        # ID état final NFA (f_i)
    value: Decimal         # Nombre de chemins dans cette classe
    lower_bound: Decimal   # Toujours 0 (non-négativité)
    upper_bound: Optional[Decimal]  # Généralement None
    is_basic: bool         # État dans tableau Simplex
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
    variables: Dict[str, Decimal]    # Solution optimale
    pivot_operations: int            # Nombre de pivots
    used_warm_start: bool           # Démarrage à chaud utilisé
    solver_statistics: Dict         # Métriques détaillées
```

### 2. Algorithmes Clés

#### Énumération de Chemins (BFS Inverse)
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
                if predecessor.id not in visited:  # Prévention cycles
                    queue.append((predecessor, path + [predecessor], 
                                visited | {predecessor.id}))
```

#### Validation Pivot Géométrique
```python
def validate_pivot_compatibility(pivot, constraints):
    # Test 1 : Faisabilité stricte
    for constraint in constraints:
        violation = constraint.get_violation(pivot)
        if violation > tolerance:
            return MATHEMATICALLY_INFEASIBLE
    
    # Test 2 : Stabilité géométrique  
    stability = compute_geometric_stability(pivot, constraints)
    
    if stability > 0.9:
        return HIGHLY_STABLE
    elif stability > 0.5:
        return MODERATELY_STABLE
    else:
        return GEOMETRICALLY_UNSTABLE
```

#### Construction Tableau Simplex Phase 1
```python
def build_phase1_tableau(problem):
    # Construction tableau avec variables artificielles
    # Objectif Phase 1 : minimiser Σ(variables_artificielles)
    
    tableau = []
    artificial_vars = []
    
    # Pour chaque contrainte ≥ ou =, ajouter variable artificielle
    for i, constraint in enumerate(problem.constraints):
        if constraint.type in (GEQ, EQ):
            artificial_vars.append(f"a_{i}")
    
    # Éliminer variables artificielles de la fonction objectif
    for basic_var in basic_vars:
        if basic_var in artificial_vars:
            # Opération pivot pour éliminer de l'objectif
            eliminate_from_objective(tableau, basic_var)
    
    return tableau, artificial_vars
```

### 3. Structures de Contrôle

#### Gestion État NFA Ancré
```python
class AnchoredWeightedNFA(WeightedNFA):
    def __init__(self):
        self.is_frozen = False
        self.anchor_suffix = ".*$"
    
    def freeze(self):
        """Gèle le NFA pour cohérence pendant énumération"""
        self.ensure_all_anchors()
        self.is_frozen = True
    
    def clone_for_transaction(self, tx_regexes):
        """Crée clone gelé avec regex transaction"""
        clone = AnchoredWeightedNFA()
        # Copier regex existants
        # Ajouter regex transaction
        clone.freeze()  # Geler immédiatement
        return clone
```

#### Cache et Historisation
```python
class AccountTaxonomy:
    def __init__(self):
        # {numéro_transaction: {compte_id: caractère}}
        self.historical_mappings = {}
        self.current_mappings = {}
        self.version = 0
    
    def get_character(self, account_id, tx_number):
        """Trouve mapping le plus récent ≤ tx_number"""
        for tx_num in sorted(self.historical_mappings.keys(), reverse=True):
            if tx_num <= tx_number:
                if account_id in self.historical_mappings[tx_num]:
                    return self.historical_mappings[tx_num][account_id]
        
        # Si pas trouvé, assigner nouveau caractère
        return self._assign_new_character(account_id, tx_number)
```

#### Gestionnaire Pivot Mathématiquement Rigoureux
```python
class MathematicallyRigorousPivotManager:
    def __init__(self, tolerance=Decimal('1e-12')):
        self.tolerance = tolerance
        self.pivot_history = []
        self.stability_metrics = {}
    
    def validate_pivot_compatibility(self, old_pivot, new_constraints):
        """Teste compatibilité rigoureuse du pivot avec nouvelles contraintes"""
        
        # Validation faisabilité
        for constraint in new_constraints:
            violation = constraint.get_violation(old_pivot)
            if violation > self.tolerance:
                return PivotStatus.MATHEMATICALLY_INFEASIBLE
        
        # Calcul stabilité géométrique
        geometry_score = self._compute_geometric_stability(old_pivot, new_constraints)
        
        # Classification stabilité
        if geometry_score > 0.95:
            return PivotStatus.HIGHLY_STABLE
        elif geometry_score > 0.7:
            return PivotStatus.MODERATELY_STABLE
        else:
            return PivotStatus.GEOMETRICALLY_UNSTABLE
    
    def _compute_geometric_stability(self, pivot, constraints):
        """Calcule score de stabilité géométrique du pivot"""
        distances = []
        for constraint in constraints:
            # Distance à la frontière de contrainte
            distance = abs(constraint.evaluate(pivot) - constraint.bound)
            distances.append(distance)
        
        # Score basé sur distance minimale et distribution
        min_distance = min(distances)
        avg_distance = sum(distances) / len(distances)
        
        # Normalisation et score composite
        stability = min(min_distance / self.tolerance, 1.0) * 0.7 + \
                   min(avg_distance / self.tolerance, 1.0) * 0.3
        
        return stability
```

## Patterns de Conception Utilisés

### 1. Patron Stratégie
- `WeightCalculator` abstrait avec multiples implémentations
- `ConstraintType` enum pour différents types de contraintes
- Validation pivot avec multiples statuts

### 2. Patron Builder
- `LinearProgram` construction incrémentale
- Fonctions `build_*_constraint()` pour construction spécialisée
- Construction tableau Simplex par phases

### 3. Patron Méthode Template
- `TripleValidationSimplex` avec étapes définies
- `DAGPathEnumerator` avec stratégies par lots
- Validation avec fallback automatique

### 4. Patron Observateur (implicite)
- Statistiques intégrées et logging
- Collection métriques de performance
- Validation cohérence continue

### 5. Patron Copy-on-Write
- Environnements validation temporaires
- Préservation état original pendant tests
- Commits atomiques après validation réussie

## Gestion d'Erreurs

### Hiérarchie Exceptions
```
Exception
├── TaxonomyError          (conflits, alphabet invalide)
├── AnchoringError         (NFA gelé, motifs invalides)
├── PathEnumerationError   (explosion, cycles)
├── SimplexError           (pivot invalide, tableau corrompu)
└── ValidationError        (contraintes incohérentes)
```

### Stratégies de Récupération
1. **Dégradation gracieuse** : Démarrage à froid si pivot invalide
2. **Validation croisée** : Vérification croisée pour cas instables
3. **Terminaison précoce** : Arrêt si explosion détectée
4. **Rollback** : Restauration état précédent si échec

### Protection contre Explosion
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

## Métriques et Monitoring

### Métriques Collectées
- `paths_enumerated`, `paths_deduplicated`, `cycles_detected`
- `warm_starts_used`, `cold_starts_used`, `pivot_rejections`
- `iterations`, `pivot_operations` par résolution
- `alphabet_usage_ratio`, `characters_available`
- `simplex_validations`, `simplex_rejections`

### Points Diagnostiques
```python
class Phase2Diagnostics:
    def get_comprehensive_stats(self):
        return {
            # État NFA
            'nfa_state': {
                'is_frozen': self.anchored_nfa.is_frozen if self.anchored_nfa else None,
                'states_count': len(self.anchored_nfa.get_final_states()) if self.anchored_nfa else 0,
                'patterns_count': len(self.anchored_nfa.regex_patterns) if self.anchored_nfa else 0
            },
            
            # Statistiques Taxonomie
            'taxonomy_state': self.account_taxonomy.get_statistics(),
            
            # Performance Solveur
            'solver_performance': self.simplex_solver.get_solver_statistics(),
            
            # Validation Problème
            'problem_validation': {
                'variables_count': len(self.current_problem.variables) if hasattr(self, 'current_problem') else 0,
                'constraints_count': len(self.current_problem.constraints) if hasattr(self, 'current_problem') else 0
            },
            
            # État Pivot
            'pivot_state': {
                'has_stored_pivot': self.stored_pivot is not None,
                'pivot_size': len(self.stored_pivot) if self.stored_pivot else 0
            }
        }
```

## Architecture de Performance

### Optimisations Implémentées

#### 1. Réutilisation Pivot
```python
def solve_with_pivot_reuse(self, problem, old_pivot=None):
    if old_pivot:
        # Valider compatibilité géométrique
        pivot_status = self.pivot_manager.validate_pivot_compatibility(
            old_pivot, problem.constraints
        )
        
        if pivot_status in [PivotStatus.HIGHLY_STABLE, PivotStatus.MODERATELY_STABLE]:
            # Tentative démarrage à chaud
            return self._solve_warm_start(problem, old_pivot)
    
    # Fallback démarrage à froid
    return self._solve_cold_start(problem)
```

#### 2. Traitement par Lots Chemins
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
        
        # Traiter lot final
        if batch:
            yield self._process_batch(batch)
```

#### 3. Déduplication Efficace
```python
class PathDeduplicator:
    def __init__(self):
        self.seen_hashes = set()
        self.hash_collisions = 0
    
    def compute_path_hash(self, path):
        """Hash rapide basé sur IDs nœuds et longueur"""
        path_str = "->".join([node.id for node in path])
        return hash(path_str + str(len(path)))
    
    def is_duplicate(self, path):
        path_hash = self.compute_path_hash(path)
        if path_hash in self.seen_hashes:
            return True
        
        self.seen_hashes.add(path_hash)
        return False
```

## Sécurité et Robustesse

### Validation Entrée
```python
def validate_transaction_inputs(self, transaction, source_account_id, target_account_id):
    """Validation rigoureuse des entrées avant traitement"""
    
    # Validation transaction
    if not isinstance(transaction, Transaction):
        raise ValidationError("Transaction must be Transaction instance")
    
    # Validation comptes
    if source_account_id not in self.accounts:
        raise ValidationError(f"Source account '{source_account_id}' not found")
    
    if target_account_id not in self.accounts:
        raise ValidationError(f"Target account '{target_account_id}' not found")
    
    # Validation mesures
    if not transaction.source_association or not transaction.target_association:
        raise ValidationError("Transaction must have both source and target associations")
    
    # Validation valeurs
    if transaction.source_association.value <= 0:
        raise ValidationError("Source association value must be positive")
    
    if transaction.target_association.value <= 0:
        raise ValidationError("Target association value must be positive")
```

### Atomicité des Opérations
```python
class AtomicTransactionProcessor:
    def __init__(self, dag):
        self.dag = dag
        self.rollback_stack = []
    
    def execute_with_rollback(self, operations):
        """Exécute opérations avec capacité rollback"""
        try:
            for operation in operations:
                # Sauvegarder état pour rollback
                backup = self._create_operation_backup(operation)
                self.rollback_stack.append(backup)
                
                # Exécuter opération
                operation.execute()
            
            # Succès : vider pile rollback
            self.rollback_stack.clear()
            return True
            
        except Exception as e:
            # Échec : effectuer rollback
            self._perform_rollback()
            raise e
    
    def _perform_rollback(self):
        """Rollback toutes opérations dans pile"""
        while self.rollback_stack:
            backup = self.rollback_stack.pop()
            backup.restore()
```

Cette architecture Phase 2 fournit une base solide et extensible pour la validation économique des transactions avec des garanties mathématiques absolues et une robustesse en production.