# Référence API - Phase 2 Simplex

## DAG (Classe Étendue Phase 2)

### Nouvelles Propriétés Phase 2

#### account_taxonomy
```python
account_taxonomy: AccountTaxonomy
```
Instance de taxonomie pour conversion chemin → mot

#### anchored_nfa  
```python
anchored_nfa: Optional[AnchoredWeightedNFA]
```
NFA ancré pour classification de motifs avec gel temporel

#### path_enumerator
```python
path_enumerator: DAGPathEnumerator  
```
Énumérateur de chemins pour traversée DAG (puits → sources)

#### simplex_solver
```python
simplex_solver: TripleValidationOrientedSimplex
```
Solveur Simplex Phase 1 avec triple validation

#### stored_pivot
```python
stored_pivot: Optional[Dict[str, Decimal]]
```
Pivot stocké pour démarrage à chaud entre transactions

#### transaction_counter
```python
transaction_counter: int
```
Compteur pour historisation taxonomique

### Méthode add_transaction Étendue

#### add_transaction (Phase 2)
```python
add_transaction(source_account_id: str, target_account_id: str, transaction: 'Transaction') -> bool
```

**Pipeline de validation étendu** :
1. Validation NFA (Phase 1 existante)
2. **Validation Simplex (Phase 2 NOUVELLE)**
3. Commit transaction

**Retourne** : `True` si transaction acceptée, `False` si rejetée

**Lève** : `ValueError` si paramètres invalides

### Nouvelles Méthodes Internes Phase 2

#### _validate_transaction_simplex
```python
_validate_transaction_simplex(transaction: 'Transaction', source_account_id: str, target_account_id: str) -> bool
```

Valide faisabilité économique via Simplex Phase 1.

**Processus** :
1. Mise à jour taxonomie avec comptes transaction
2. Création NFA ancré temporaire
3. Énumération chemins de l'arête transaction vers sources DAG
4. Construction problème LP avec variables flux et contraintes
5. Résolution Simplex Phase 1 avec triple validation

**Retourne** : `True` si économiquement faisable

#### _update_taxonomy_for_transaction
```python
_update_taxonomy_for_transaction(source_account_id: str, target_account_id: str) -> None
```

Met à jour taxonomie avec comptes impliqués dans transaction.

**Paramètres** :
- `source_account_id` : Identifiant compte source
- `target_account_id` : Identifiant compte cible

#### _create_transaction_nfa
```python
_create_transaction_nfa(transaction: 'Transaction') -> AnchoredWeightedNFA
```

Crée NFA ancré temporaire avec mesures de la transaction.

**Retourne** : NFA gelé avec regex transaction

#### _create_temporary_transaction_edge
```python
_create_temporary_transaction_edge(source_account_id: str, target_account_id: str, transaction: 'Transaction') -> Edge
```

Crée arête transaction temporaire pour énumération chemins.

**Retourne** : Arête temporaire connectant puits source et cible

#### _enumerate_and_classify_paths
```python
_enumerate_and_classify_paths(transaction_edge: Edge, nfa: AnchoredWeightedNFA) -> Dict[str, List]
```

Énumère chemins et les classe par état final NFA.

**Retourne** : Dictionnaire `état_final_id → liste_chemins`

#### _build_lp_from_path_classes
```python
_build_lp_from_path_classes(path_classes: Dict[str, List], transaction: 'Transaction', nfa: AnchoredWeightedNFA) -> LinearProgram
```

Construit problème LP depuis classes de chemins.

**Retourne** : Programme LP avec variables flux et contraintes économiques

## AccountTaxonomy

### Constructeur
```python
AccountTaxonomy(alphabet: Optional[str] = None)
```
- `alphabet` : Chaîne contenant tous caractères autorisés. Si None, utilise alphabet par défaut.

### Méthodes Principales

#### get_character
```python
get_character(account_id: str, transaction_number: int) -> str
```
Récupère caractère associé à un compte pour numéro transaction donné.

**Paramètres** :
- `account_id` : Identifiant unique compte
- `transaction_number` : Numéro transaction pour historisation

**Retourne** : Caractère Unicode représentant le compte

**Lève** : `TaxonomyError` si compte non trouvé

#### update_taxonomy
```python
update_taxonomy(mappings: Dict[str, str], transaction_number: int) -> None
```
Met à jour taxonomie avec nouveaux mappings compte → caractère.

**Paramètres** :
- `mappings` : Dictionnaire compte_id → caractère
- `transaction_number` : Numéro transaction à associer

**Lève** : `TaxonomyError` si conflits ou caractères invalides

#### assign_new_characters
```python
assign_new_characters(account_ids: Set[str], transaction_number: int) -> Dict[str, str]
```
Assigne automatiquement caractères aux comptes sans mappings.

**Retourne** : Dictionnaire nouveaux mappings créés

### Méthodes Utilitaires

#### get_alphabet
```python
get_alphabet() -> Set[str]
```
Retourne alphabet utilisé par cette taxonomie.

#### get_statistics
```python
get_statistics() -> Dict[str, any]
```
Retourne statistiques utilisation taxonomie.

**Structure retour** :
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

### Constructeur
```python
AnchoredWeightedNFA(nfa_id: Optional[str] = None, 
                   weight_calculator: Optional['WeightCalculator'] = None)
```

### Méthodes Principales

#### add_weighted_regex
```python
add_weighted_regex(measure_id: str, pattern: str, weight: Decimal) -> None
```
Ajoute regex pondéré avec ancrage automatique.

**Lève** : `AnchoringError` si NFA gelé

#### freeze/unfreeze
```python
freeze() -> None
unfreeze() -> None
is_nfa_frozen() -> bool
```
Contrôle état gelé NFA pour cohérence pendant énumération.

#### get_final_states
```python
get_final_states() -> List[NFAState]
```
Retourne tous états finaux du NFA.

#### get_regex_weights_for_final_state
```python
get_regex_weights_for_final_state(state: NFAState) -> Set[RegexWeight]
```
Retourne RegexWeights associés à état final spécifique.

#### evaluate_to_final_state
```python
evaluate_to_final_state(text: str) -> Optional[str]
```
Évalue texte et retourne ID état final atteint, le cas échéant.

#### clone_for_transaction
```python
clone_for_transaction(transaction_regexes: List[Tuple[str, str, Decimal]]) -> 'AnchoredWeightedNFA'
```
Crée clone gelé avec regex additionnels pour transaction.

## DAGPathEnumerator

### Constructeur
```python
DAGPathEnumerator(taxonomy: AccountTaxonomy, 
                 max_paths: int = 10000, 
                 batch_size: int = 100)
```

### Méthodes Principales

#### enumerate_paths_to_sources
```python
enumerate_paths_to_sources(start_edge: Edge) -> Iterator[List[Node]]
```
Énumère tous chemins depuis start_edge vers sources DAG.

**Génère** : Listes nœuds représentant chemins

**Lève** : `PathEnumerationError` si explosion ou échec

#### path_to_word
```python
path_to_word(path: List[Node], transaction_number: int) -> str
```
Convertit chemin en mot via fonction taxonomique.

#### estimate_total_paths
```python
estimate_total_paths(start_edge: Edge, max_depth: int = 5) -> int
```
Estime nombre total chemins sans énumération complète.

### Méthodes Utilitaires

#### get_path_statistics
```python
get_path_statistics() -> Dict[str, int]
```
Retourne statistiques énumération.

## TripleValidationOrientedSimplex

### Constructeur
```python
TripleValidationOrientedSimplex(max_iterations: int = 10000,
                               tolerance: Decimal = Decimal('1e-10'))
```

### Méthodes Principales

#### solve_with_absolute_guarantees
```python
solve_with_absolute_guarantees(problem: LinearProgram,
                              old_pivot: Optional[Dict[str, Decimal]] = None) -> SimplexSolution
```
Résout avec garanties mathématiques absolues via triple validation.

**Retourne** : `SimplexSolution` avec statut et variables

**Processus** :
1. Validation pivot (si fourni)
2. Démarrage à chaud si pivot compatible
3. Fallback démarrage à froid si nécessaire  
4. Validation croisée si instabilité détectée

#### Méthodes Internes (test/debug)

#### _solve_warm_start
```python
_solve_warm_start(problem: LinearProgram, 
                 pivot: Dict[str, Decimal]) -> SimplexSolution
```

#### _solve_cold_start
```python
_solve_cold_start(problem: LinearProgram) -> SimplexSolution
```

### Méthodes Utilitaires

#### get_solver_statistics
```python
get_solver_statistics() -> Dict[str, int]
```
Retourne statistiques utilisation solveur.

## MathematicallyRigorousPivotManager

### Constructeur
```python
MathematicallyRigorousPivotManager(tolerance: Decimal = Decimal('1e-12'))
```

### Méthodes Principales

#### validate_pivot_compatibility
```python
validate_pivot_compatibility(old_pivot: Dict[str, Decimal],
                            new_constraints: List[LinearConstraint]) -> PivotStatus
```
Teste compatibilité rigoureuse pivot avec nouvelles contraintes.

**Retourne** : `PivotStatus` indiquant niveau compatibilité

**Niveaux** :
- `HIGHLY_STABLE` : Pivot très stable géométriquement
- `MODERATELY_STABLE` : Pivot modérément stable
- `GEOMETRICALLY_UNSTABLE` : Pivot instable géométriquement
- `MATHEMATICALLY_INFEASIBLE` : Pivot viole contraintes

## Fonctions Utilitaires

### Constructeurs de Contraintes

#### build_source_constraint
```python
build_source_constraint(nfa_state_weights: Dict[str, Decimal],
                       primary_regex_weight: Decimal,
                       acceptable_value: Decimal,
                       constraint_name: str = "source_primary") -> LinearConstraint
```
Construit contrainte source primaire : `Σ(f_i × weight_i) ≤ V_source_acceptable`

#### build_target_constraint
```python
build_target_constraint(nfa_state_weights: Dict[str, Decimal],
                       primary_regex_weight: Decimal,
                       required_value: Decimal,
                       constraint_name: str = "target_primary") -> LinearConstraint
```
Construit contrainte cible primaire : `Σ(f_i × weight_i) ≥ V_target_required`

#### build_secondary_constraint
```python
build_secondary_constraint(nfa_state_weights: Dict[str, Decimal],
                          secondary_regex_weight: Decimal,
                          constraint_name: str = "secondary") -> LinearConstraint
```
Construit contrainte secondaire : `Σ(f_i × weight_i) ≤ 0`

## Énumérations et Types

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
Levée pour erreurs taxonomie (conflits, alphabet invalide).

### AnchoringError
Levée pour erreurs ancrage NFA (NFA gelé, motifs invalides).

### PathEnumerationError
Levée durant énumération chemins (explosion, cycles).

### SimplexError
Levée durant opérations Simplex (pivot invalide, tableau corrompu).

## Exemple Utilisation Complète

### Validation Transaction avec Phase 2

```python
# 1. Configuration
from icgs_core import DAG, Account, Transaction, Association, Measure, WeightedRegex
from decimal import Decimal

# Créer DAG avec composants Phase 2 (automatique)
dag = DAG()

# 2. Ajouter comptes
alice = Account("alice")  
bob = Account("bob")
dag.add_account(alice)
dag.add_account(bob)

# 3. Configurer mesures économiques
source_measure = Measure("capacite_debit", [
    WeightedRegex("A.*", Decimal('1.0')),      # Alice peut débiter
    WeightedRegex("FRAUD.*", Decimal('-10.0'))  # Motif fraude pénalisé
])

target_measure = Measure("exigence_credit", [
    WeightedRegex(".*B", Decimal('0.9')),      # Bob reçoit avec facteur 0.9
    WeightedRegex("BONUS.*", Decimal('1.2'))   # Motif bonus amélioré
])

# 4. Créer transaction
source_assoc = Association(source_measure, Decimal('200'))  # Alice peut fournir 200
target_assoc = Association(target_measure, Decimal('150'))  # Bob a besoin 150

transaction = Transaction("alice_vers_bob", source_assoc, target_assoc)

# 5. Validation automatique Phase 2
success = dag.add_transaction("alice", "bob", transaction)

if success:
    print("✓ Transaction validée - faisabilité économique confirmée")
    
    # Accéder statistiques Phase 2
    if dag.stats:
        print(f"Validations Simplex: {dag.stats['simplex_validations']}")
        print(f"Rejets Simplex: {dag.stats['simplex_rejections']}")
        print(f"Démarrages chauds: {dag.stats['warm_starts_used']}")
        print(f"Démarrages froids: {dag.stats['cold_starts_used']}")
    
    # Accéder état taxonomie
    taxonomy_stats = dag.account_taxonomy.get_statistics()
    print(f"Comptes mappés: {taxonomy_stats['total_accounts']}")
    print(f"Transactions historisées: {taxonomy_stats['total_transactions']}")
    
    # Accéder métriques solveur
    solver_stats = dag.simplex_solver.get_solver_statistics()
    print(f"Résolutions totales: {solver_stats.get('total_solves', 0)}")
    
else:
    print("✗ Transaction rejetée - infaisabilité économique détectée")
```

### Configuration Avancée

```python
# Configuration précision numérique
from decimal import getcontext
getcontext().prec = 50  # Précision ultra-haute

# Configuration solveur personnalisé
custom_solver = TripleValidationOrientedSimplex(
    max_iterations=50000,
    tolerance=Decimal('1e-15')
)

# Configuration énumérateur chemins
custom_enumerator = DAGPathEnumerator(
    dag.account_taxonomy,
    max_paths=50000,
    batch_size=500
)

# Remplacer composants par défaut
dag.simplex_solver = custom_solver
dag.path_enumerator = custom_enumerator

# Validation avec configuration avancée
result = dag.add_transaction("alice", "bob", complex_transaction)
```

Cette API Phase 2 maintient compatibilité complète avec Phase 1 tout en ajoutant validation économique rigoureuse avec garanties mathématiques absolues.