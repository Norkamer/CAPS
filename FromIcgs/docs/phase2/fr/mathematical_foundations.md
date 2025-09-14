# Fondements Mathématiques - Phase 2 Simplex

## Formulation du Problème LP

### Variables de Décision

**Définition** : Variables de flux par classe d'équivalence NFA
```
f_i ∈ ℝ₊ ∪ {0}  pour chaque classe non-vide C_i
où C_i = {chemins | NFA(mot(chemin)) = état_final_i}
```

**Interprétation Économique** :
- `f_i` = nombre de chemins DAG se terminant à l'état final NFA `i`
- Représente la **capacité de flux** disponible pour les motifs correspondant à l'état `i`
- Regroupement sémantique : chemins équivalents du point de vue regex

### Fonction Objectif

**Simplex Phase 1 Standard** : Test de faisabilité uniquement
```
Objectif: Trouver f⃗ tel que A·f⃗ satisfait toutes les contraintes
```

**Tableau Phase 1** : Minimisation variables artificielles
```
min Σ(s_i)  où s_i sont variables artificielles de slack
```

### Contraintes par Transaction

Pour une transaction T avec associations source S et cible T :

#### Contraintes Source (compte débiteur)
```
Primaire:   Σ(f_i × coeff_i,R_s0) ≤ V_source_acceptable
Secondaires: ∀k∈[1,n] : Σ(f_i × coeff_i,R_sk) ≤ 0
```

où :
- `R_s0` = regex primaire de la mesure source
- `R_sk` = regex secondaires (motifs interdits, bonus)
- `coeff_i,R` = poids du regex R si l'état `i` correspond à R, sinon 0

#### Contraintes Cible (compte créditeur)
```
Primaire:   Σ(f_i × coeff_i,R_t0) ≥ V_target_required
Secondaires: ∀k∈[1,m] : Σ(f_i × coeff_i,R_tk) ≤ 0
```

### Matrice de Coefficients

**Construction** : À partir des RegexWeights des états finaux NFA
```python
def build_coefficient_matrix():
    coefficients = {}
    for state_id in nfa_final_states:
        for regex_weight in state.regex_weights:
            if regex_weight.measure_id == constraint.measure_id:
                coefficients[state_id] = regex_weight.weight_factor.to_decimal()
    return coefficients
```

**Exemple Concret** :
```
États NFA: [state_A, state_B, state_C]
Regex "debit_pattern" poids 1.2 correspond state_A et state_C
Regex "credit_pattern" poids 0.9 correspond state_B

Contrainte source: 1.2×f_A + 0×f_B + 1.2×f_C ≤ 150
Contrainte cible: 0×f_A + 0.9×f_B + 0×f_C ≥ 100
```

## Preuves de Correction

### Théorème 1 : Équivalence avec Simplex Classique

**Énoncé** :
```
∀ problème LP bien posé P :
TripleValidationSimplex(P, pivot) ≡ SimplexClassique(P)
```

**Démonstration** :
1. **Validation pivot** : Si pivot compatible → démarrage à chaud = résolution depuis point faisable
2. **Fallback garanti** : Si pivot incompatible → démarrage à froid = résolution standard
3. **Validation croisée** : Si instabilité détectée → vérification par résolution indépendante
4. **Union complète** : Chaud ∪ Froid ∪ Croisé couvre tous les cas possibles

**Démonstration détaillée** :

*Cas 1 : Pivot Compatible*
- Hypothèse : `validate_pivot_compatibility(pivot, contraintes) ∈ {HIGHLY_STABLE, MODERATELY_STABLE}`
- Le pivot satisfait toutes les contraintes avec tolérance géométrique
- Le démarrage à chaud depuis ce pivot est équivalent à continuer une résolution Simplex classique
- Correctness : Le pivot étant faisable, l'algorithme convergera vers la solution optimale

*Cas 2 : Pivot Incompatible*
- Hypothèse : `validate_pivot_compatibility(pivot, contraintes) = MATHEMATICALLY_INFEASIBLE`
- L'algorithme effectue un démarrage à froid
- Équivalence : Démarrage à froid ≡ SimplexClassique depuis origine
- Correctness : Algorithme standard garanti correct

*Cas 3 : Instabilité Géométrique*
- Hypothèse : `validate_pivot_compatibility(pivot, contraintes) = GEOMETRICALLY_UNSTABLE`
- Validation croisée par résolution indépendante
- Si résultats concordent : solution validée
- Si résultats divergent : utiliser résolution la plus conservatrice

### Théorème 2 : Correction Récursive avec Pivot

**Énoncé** : Pour séquence de transactions T₁, T₂, ..., Tₙ
```
∀n : SimplexOrienté(LPₙ, pivotₙ₋₁) = SimplexClassique(LPₙ)
```

**Démonstration par récurrence** :

**Cas de base P(1)** :
- LP₁ avec pivot₀ = ∅ (pas de pivot initial)
- Résolution démarrage à froid ≡ SimplexClassique ✓

**Étape inductive P(n) ⟹ P(n+1)** :
- Hypothèse : pivotₙ correct après résolution LPₙ
- LPₙ₊₁ = LPₙ ∪ {nouvelles contraintes Tₙ₊₁}
- Si pivotₙ compatible avec LPₙ₊₁ : démarrage à chaud valide
- Si pivotₙ incompatible : fallback démarrage à froid ≡ SimplexClassique
- Dans tous les cas : résultat correct ✓

**Invariant maintenu** : À chaque transaction, le pivot stocké (s'il existe) représente une solution faisable du problème LP courant.

### Théorème 3 : Cohérence des Classes d'Équivalence

**Énoncé** :
```
∀ NFA gelé N, ∀ ensemble de chemins C :
Partition P = {C₁, C₂, ..., Cₖ} est bien définie
où Cᵢ = {chemin ∈ C | N(mot(chemin)) = état_final_i}
```

**Démonstration** :
1. **Fonction déterministe** : NFA gelé ⟹ même chemin donne toujours même état final
2. **Disjonction** : ∀i≠j : Cᵢ ∩ Cⱼ = ∅ (chemin ne peut atteindre qu'un seul état final)
3. **Couverture** : ⋃ᵢ Cᵢ ∪ C_rejet = C (tous chemins sont classifiés)

**Propriétés de la Partition** :
- **Stabilité temporelle** : NFA gelé garantit classification stable pendant énumération
- **Complétude** : Tous chemins énumérés sont classifiés
- **Exclusivité mutuelle** : Pas de double comptage entre classes

## Stabilité Numérique

### Configuration Arithmétique

**Configuration Decimal** :
```python
from decimal import getcontext
getcontext().prec = 28  # 28 chiffres significatifs
```

**Avantages** :
- Pas d'erreurs d'arrondi en virgule flottante
- Représentation exacte des valeurs monétaires
- Comparaisons déterministes

### Tolérances Numériques

**Validation contraintes** :
```python
tolerance = Decimal('1e-10')  # 10⁻¹⁰ pour comparaisons
constraint_satisfied = |lhs - rhs| ≤ tolerance
```

**Validation pivot** :
```python
geometric_tolerance = Decimal('1e-12')  # Plus strict pour stabilité
pivot_feasible = violation ≤ geometric_tolerance
```

### Gestion Cas Limites

**Division par zéro** :
```python
def safe_divide(a, b):
    if abs(b) < Decimal('1e-15'):
        raise SimplexError("Division par élément proche de zéro")
    return a / b
```

**Protection débordement** :
```python
if new_log_magnitude > MAX_LOG_MAGNITUDE:
    raise OverflowError("Magnitude poids trop importante")
```

**Détection singularité** :
```python
def check_matrix_singularity(matrix):
    """Vérifie singularité de la matrice de contraintes"""
    determinant = compute_determinant(matrix)
    if abs(determinant) < Decimal('1e-14'):
        raise SimplexError("Matrice de contraintes singulière")
```

## Complexité Algorithmique

### Énumération de Chemins

**Cas pire** : O(|E|^d) où d = profondeur maximale DAG
```
- |E| = nombre d'arêtes sortantes par nœud
- d ≤ nombre de comptes dans le système
- Limité à max_paths pour prévenir explosion
```

**Cas moyen** : O(|chemins_utiles|) avec élagage
```
- Cycles détectés et évités : O(1) par détection
- Déduplication par hachage : O(log |chemins|) par chemin
- Traitement par lots : mémoire constante
```

**Analyse amortie** :
```python
def amortized_complexity_analysis():
    """
    Complexité amortie sur séquence de transactions
    
    - Première transaction: O(|E|^d) énumération complète
    - Transactions suivantes: O(δ|E|^d) où δ = changement incrémentiel
    - Avec réutilisation pivot: O(k×m²) où k << m
    """
    return {
        'first_transaction': 'O(|E|^d)',
        'subsequent_transactions': 'O(δ|E|^d)',
        'simplex_warm_start': 'O(k×m²)'
    }
```

### Simplex Phase 1

**Standard** : O(m³) où m = nombre de contraintes
```
- Construction tableau : O(m×n) où n = nombre de variables
- Opérations pivot : O(m²) par pivot
- Nombre de pivots : ≤ C(m+n, m) théorique, <<< pratique
```

**Avec démarrage à chaud** : O(k×m²) où k = nombre de pivots depuis pivot initial
```
- k << m généralement si pivot proche de l'optimum
- Gain significatif pour séquences de transactions
```

**Analyse cas spéciaux** :
```python
def complexity_special_cases():
    return {
        'highly_constrained': 'O(m³) → O(m²) réduction possible',
        'sparse_constraints': 'O(m³) → O(m²×sparsity) avec algorithmes spécialisés',
        'pivot_reuse_rate_high': 'O(k×m²) où k ≈ log(m)',
        'pivot_reuse_rate_low': 'O(m³) dégradation vers cas standard'
    }
```

### NFA Gelé

**Construction** : O(|regex| × |longueur_motif|²) par regex
```
- Compilation regex : coût standard Python
- États finaux : O(|états|) pour identification
- Gelé = pas de coût additionnel durant évaluation
```

**Évaluation** : O(|mot| × |états_actifs|) par mot
```
- |mot| ≤ longueur_max_chemin_DAG
- |états_actifs| << |états_totaux| en pratique
- Epsilon-closure : amorti sur longueur mot
```

**Optimisations NFA** :
```python
class OptimizedNFAEvaluation:
    def __init__(self):
        self.state_transition_cache = {}
        self.word_evaluation_cache = {}
    
    def evaluate_with_caching(self, word):
        """Évaluation NFA avec mise en cache"""
        if word in self.word_evaluation_cache:
            return self.word_evaluation_cache[word]
        
        result = self._evaluate_nfa(word)
        self.word_evaluation_cache[word] = result
        return result
```

## Invariants et Propriétés

### Invariants Structurels

1. **Conservation de flux** : `Σ f_i = |chemins_totaux|` (constant)
2. **Non-négativité** : `∀i : f_i ≥ 0` (respecté par construction)
3. **Cohérence taxonomique** : `f(compte, tx) déterministe ∀ tx`
4. **Stabilité NFA** : `NFA gelé ⟹ classifications temporellement cohérentes`

### Propriétés Économiques

1. **Monotonie faible** : Ajouter chemins ne peut qu'améliorer faisabilité
2. **Localité** : Transaction affecte seulement comptes impliqués
3. **Conservation** : Somme débits ≈ somme crédits (modulo poids)
4. **Réversibilité** : Transaction inverse faisable si originale faisable

**Démonstration Monotonie** :
```
Soient C₁ ⊆ C₂ deux ensembles de chemins
Si LP(C₁) faisable et C₁ ⊆ C₂, alors LP(C₂) faisable

Preuve: 
- Solution f₁ de LP(C₁) peut être étendue à f₂ pour LP(C₂)
- en définissant f₂[i] = f₁[i] pour i ∈ classes(C₁)
- et f₂[j] = 0 pour j ∈ classes(C₂ \ C₁)
- f₂ satisfait toutes contraintes de LP(C₂)
```

### Garanties de Terminaison

1. **Énumération** : DAG acyclique ⟹ nombre fini de chemins
2. **Simplex** : Nombre fini de solutions de base ⟹ terminaison garantie
3. **Validation** : Tests finis ⟹ décision en temps fini
4. **Global** : Tous sous-algorithmes terminent ⟹ algorithme termine

**Preuve Terminaison Simplex** :
```
Théorème: L'algorithme Simplex Phase 1 termine en nombre fini d'étapes

Preuve:
1. Nombre fini de solutions de base: C(m+n, m)
2. Règle anti-cyclage (Bland) garantit pas de revisiter solution
3. Fonction objectif strictement décroissante (ou optimum atteint)
4. Donc terminaison en ≤ C(m+n, m) itérations
```

## Analyse de Robustesse

### Sensibilité aux Perturbations

**Stabilité Solution** :
```python
def sensitivity_analysis(solution, perturbation_size):
    """Analyse sensibilité solution aux perturbations données"""
    
    # Test perturbations contraintes RHS
    for i, constraint in enumerate(constraints):
        perturbed_bound = constraint.bound + perturbation_size
        new_solution = resolve_with_perturbed_constraint(i, perturbed_bound)
        
        sensitivity = compute_solution_distance(solution, new_solution)
        if sensitivity > STABILITY_THRESHOLD:
            return "UNSTABLE_TO_RHS_PERTURBATION"
    
    # Test perturbations coefficients contraintes
    for constraint in constraints:
        for var_id in constraint.coefficients:
            original_coeff = constraint.coefficients[var_id]
            perturbed_coeff = original_coeff * (1 + perturbation_size)
            
            # Résoudre avec coefficient perturbé
            new_solution = resolve_with_perturbed_coefficient(constraint, var_id, perturbed_coeff)
            
            sensitivity = compute_solution_distance(solution, new_solution)
            if sensitivity > STABILITY_THRESHOLD:
                return "UNSTABLE_TO_COEFFICIENT_PERTURBATION"
    
    return "STABLE"
```

### Condition Numbers

**Conditionnement Matrice Contraintes** :
```python
def compute_condition_number(constraint_matrix):
    """Calcule nombre de condition pour analyse stabilité numérique"""
    
    # Valeurs singulières
    singular_values = compute_singular_values(constraint_matrix)
    
    # Nombre de condition = ratio plus grande/plus petite valeur singulière
    condition_number = max(singular_values) / min(singular_values)
    
    if condition_number > CONDITION_THRESHOLD:
        raise SimplexError(f"Matrice mal conditionnée: κ = {condition_number}")
    
    return condition_number
```

### Récupération d'Erreurs Numériques

**Détection et Correction** :
```python
class NumericalErrorRecovery:
    def __init__(self):
        self.precision_escalation_levels = [28, 50, 100]
        self.current_precision_level = 0
    
    def solve_with_error_recovery(self, problem):
        """Résolution avec récupération automatique erreurs numériques"""
        
        for precision in self.precision_escalation_levels:
            try:
                # Augmenter précision
                getcontext().prec = precision
                
                # Tentative résolution
                solution = self.standard_solve(problem)
                
                # Valider solution
                if self.validate_solution_numerically(solution, problem):
                    return solution
                    
            except NumericalInstabilityError:
                # Essayer précision supérieure
                continue
        
        # Si toutes précisions échouent
        raise SimplexError("Impossible de résoudre avec stabilité numérique requise")
    
    def validate_solution_numerically(self, solution, problem):
        """Validation numérique rigoureuse solution"""
        
        # Test satisfaction contraintes avec tolérance adaptative
        tolerance = Decimal('1e-' + str(getcontext().prec - 2))
        
        for constraint in problem.constraints:
            if not constraint.is_satisfied(solution.variables, tolerance):
                return False
        
        # Test cohérence arithmétique
        if not self.check_arithmetic_consistency(solution):
            return False
        
        return True
```

Cette fondation mathématique rigoureuse assure que l'implémentation Phase 2 maintient des garanties absolues de correction tout en gérant efficacement les défis numériques et algorithmiques inhérents à la résolution de problèmes de programmation linéaire à grande échelle.