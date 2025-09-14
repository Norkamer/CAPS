# ICGS - Intelligent Computation Graph System

## Vue d'ensemble

ICGS est un système de graphe de calcul intelligent pour la validation et l'exécution de transactions économiques complexes. Le système utilise une approche hybride combinant des graphes dirigés acycliques (DAG), des automates finis non-déterministes pondérés (NFA), et la programmation linéaire pour garantir la cohérence et la faisabilité des transactions.

## Architecture

### Composants principaux
- **DAG** : Structure de données principale représentant comptes, transactions et flux
- **WeightedNFA** : Évaluation de patterns regex pondérés pour classification des chemins
- **Simplex Phase 1** : Validation de faisabilité économique avant intégration transaction
- **Weight Calculators** : Système extensible de calcul de poids (impératif, fonctionnel, hybride)

### Pipeline de transaction
1. **Construction** : Création des nœuds et arêtes dans le DAG
2. **Évaluation** : Classification des chemins via NFA pondéré  
3. **Validation** : Test de faisabilité économique via Simplex
4. **Intégration** : Ajout définitif si validation réussie

## Simplex Phase 1 - Validation de faisabilité

### Problème résolu
Déterminer si une transaction proposée peut être exécutée sans violer les contraintes économiques définies par les regex pondérés des mesures associées.

### Approche mathématique
- **Variables flux** `f_i ≥ 0` : nombre de chemins DAG aboutissant à l'état final NFA i
- **Contraintes** générées depuis les associations transaction :
  - Primary source : `Σ(f_i × weight_i) ≤ V_source_acceptable`
  - Primary target : `Σ(f_i × weight_i) ≥ V_target_required`  
  - Secondary patterns : `Σ(f_i × weight_i) ≤ 0` (interdits)
- **Résolution** : Simplex Phase 1 avec triple validation

### Composants implémentés

#### AccountTaxonomy
Fonction taxonomique historisée `f(compte_id, transaction_number) → caractère` pour conversion chemins DAG → mots évaluables par NFA.

#### AnchoredWeightedNFA  
Extension du WeightedNFA avec ancrage automatique pour éliminer matches partiels et mode "frozen" pour cohérence temporelle.

#### DAGPathEnumerator
Énumération optimisée des chemins depuis arête de transaction vers sources DAG avec déduplication et détection de cycles.

#### TripleValidationOrientedSimplex
Solveur Simplex Phase 1 avec garanties mathématiques absolues :
- Validation rigoureuse de pivot (compatibilité géométrique)
- Warm-start intelligent avec fallback cold-start
- Cross-validation pour cas instables

### Garanties mathématiques
- **Correction prouvée** : Équivalence avec Simplex classique
- **Preuve par récurrence** : Validité préservée sur séquences de transactions  
- **Cohérence temporelle** : NFA figé et taxonomie historisée
- **Stabilité numérique** : Arithmétique Decimal haute précision

## Installation et utilisation

### Structure du projet
```
ICGS/
├── icgs-core/                    # Composants principaux
│   ├── account_taxonomy.py       # Fonction taxonomique
│   ├── anchored_nfa.py          # NFA avec ancrage
│   ├── path_enumerator.py       # Énumération chemins  
│   ├── linear_programming.py    # Structures LP
│   ├── simplex_solver.py        # Solveur triple validation
│   └── ...                     # Composants existants
├── docs/phase1/                 # Documentation détaillée
│   ├── README.md               # Vue d'ensemble complète
│   ├── architecture.md         # Architecture technique
│   ├── mathematical_foundations.md  # Fondements mathématiques
│   └── api_reference.md        # Référence API
└── test_icgs_integration.py    # Tests d'intégration
```

### Tests et validation
```bash
cd ICGS
python3 test_icgs_integration.py
```
**Résultat attendu** : 5/5 tests passés (100%) - validation de cohérence mathématique.

### Exemple d'utilisation
```python
from icgs_core import (
    AccountTaxonomy, AnchoredWeightedNFA, 
    LinearProgram, TripleValidationOrientedSimplex,
    build_source_constraint, build_target_constraint
)
from decimal import Decimal

# 1. Configuration taxonomie
taxonomy = AccountTaxonomy()
taxonomy.update_taxonomy({'alice': 'A', 'bob': 'B'}, 0)

# 2. Setup NFA avec patterns transaction
nfa = AnchoredWeightedNFA()
nfa.add_weighted_regex("source_measure", "A.*", Decimal('1.0'))
nfa.add_weighted_regex("target_measure", ".*B", Decimal('0.9'))
nfa.freeze()

# 3. Construction problème LP (flux variables simulées)
program = LinearProgram("alice_to_bob")
program.add_variable("alice_state")
program.add_variable("bob_state")

program.add_constraint(build_source_constraint(
    {'alice_state': Decimal('5')}, Decimal('1.0'), Decimal('150')
))
program.add_constraint(build_target_constraint(
    {'bob_state': Decimal('3')}, Decimal('0.9'), Decimal('100')
))

# 4. Validation avec garanties mathématiques
solver = TripleValidationOrientedSimplex()
solution = solver.solve_with_absolute_guarantees(program)

# 5. Décision
if solution.status == SolutionStatus.FEASIBLE:
    print("Transaction validée ✓")
else:
    print("Transaction rejetée ✗")
```

## Statut d'implémentation

### ✅ Phase 1 complète (Simplex validation)
- Infrastructure de base : taxonomie, NFA ancré, énumération chemins
- Structures LP complètes avec constructeurs automatiques  
- Solveur Simplex avec triple validation et garanties mathématiques
- Tests complets validés (5/5 passés)

### 🚧 Phase 2 prévue
- Intégration complète avec `DAG.add_transaction()`
- Interface utilisateur pour diagnostic  
- Optimisations performance et parallélisation
- Tests sur données réelles à grande échelle

## Documentation détaillée

Pour une documentation complète, consulter :
- **[docs/phase1/README.md](docs/phase1/README.md)** - Vue d'ensemble et pipeline complet
- **[docs/phase1/architecture.md](docs/phase1/architecture.md)** - Architecture technique détaillée
- **[docs/phase1/mathematical_foundations.md](docs/phase1/mathematical_foundations.md)** - Fondements et preuves mathématiques  
- **[docs/phase1/api_reference.md](docs/phase1/api_reference.md)** - Référence API complète

## Licence et contribution

Ce système implémente une architecture mathématiquement rigoureuse pour la validation de transactions économiques avec garanties de correction formellement prouvées.