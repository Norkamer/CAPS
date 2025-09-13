# Architecture Thompson's NFA - ICGS Core

## 🎯 Vue d'Ensemble

Cette documentation décrit la refonte majeure de l'architecture NFA d'ICGS, remplaçant l'implémentation précédente par une **architecture Thompson's rigoureuse** respectant la règle d'or des automates finis.

## ⚡ Problème Résolu : Violation Règle d'Or

### Ancien Problème
```python
# AVANT - Violation règle d'or
ancien_nfa.evaluate_word("N")   # ✅ Fonctionnait
ancien_nfa.evaluate_word("NB")  # ❌ Échec - mots multi-caractères
```

### Solution Thompson's
```python
# APRÈS - Respect strict règle d'or
thompson_nfa.evaluate_word("N")   # ✅ Fonctionnait
thompson_nfa.evaluate_word("NB")  # ✅ Fonctione! Multi-caractères supportés
```

**Règle d'Or** : `1 caractère = 1 transition` dans un automate fini.

## 🏗️ Architecture Composants

### 1. RegexParser (`regex_parser.py`)

**Responsabilité** : Décomposition patterns regex en tokens Thompson's.

```python
from icgs_core.regex_parser import create_icgs_regex_parser

parser = create_icgs_regex_parser()
tokens = parser.parse(".*N.*")
# Tokens: [DOT(*), LITERAL(N), DOT(*)]
```

**Patterns Supportés** :
- Littéraux : `"N"`, `"ABC"`
- Dots : `"."`, `".*"`
- Quantificateurs : `"A+"`, `"B?"`, `"C*"`
- Ancres : `"^start"`, `"end$"`

### 2. ThompsonNFABuilder (`thompson_nfa.py`)

**Responsabilité** : Construction NFA selon algorithme Thompson's classique.

```python
from icgs_core.thompson_nfa import create_thompson_builder

builder = create_thompson_builder()
fragment = builder.build_pattern_fragment(".*N.*")
print(f"États: {len(fragment.all_state_ids)}")
print(f"Transitions: {len(fragment.transitions)}")
```

**Algorithme Thompson's** :
- Construction par fragments atomiques
- Concaténation via ε-transitions
- Quantificateurs par transformation standard
- Respect strict 1-caractère = 1-transition

### 3. SharedNFA (`shared_nfa.py`)

**Responsabilité** : NFA partagé avec entry points factorisés.

```python
from icgs_core.shared_nfa import create_shared_nfa

nfa = create_shared_nfa("production_nfa")

# Ajout mesures avec mutualisation automatique
nfa.add_measure("agriculture", ".*N.*", Decimal('1.2'))
nfa.add_measure("industry", ".*N.*", Decimal('0.9'))

# Pattern partagé, poids distincts
print(f"Patterns: {len(nfa.pattern_registry)}")  # 1
print(f"Entry points: {len(nfa.entry_points)}")  # 2
```

**Avantages Mutualisation** :
- États Thompson's partagés entre patterns identiques
- Mémoire optimisée pour patterns récurrents
- Performance améliorée construction incrémentale

### 4. WeightedNFA v2 (`weighted_nfa_v2.py`)

**Responsabilité** : Layer compatibility API existante.

```python
from icgs_core.weighted_nfa_v2 import create_weighted_nfa

nfa = create_weighted_nfa("compatibility")
state = nfa.add_weighted_regex_simple("measure", ".*N.*", Decimal('1.0'))

# API identique, implémentation Thompson's
result = nfa.evaluate_word("NB")  # ✅ Fonctionne maintenant!
```

### 5. AnchoredWeightedNFA v2 (`anchored_nfa_v2.py`)

**Responsabilité** : Ancrage automatique + Thompson's core.

```python
from icgs_core.anchored_nfa_v2 import create_anchored_nfa

nfa = create_anchored_nfa("production")

# Ancrage automatique
state = nfa.add_weighted_regex("measure", "N", Decimal('1.0'))
# Transformé automatiquement en ".*N.*$"

nfa.freeze()
result = nfa.evaluate_to_final_state("NB")  # ✅ Succès
```

## 📊 Comparaison Architectures

| Aspect | Ancienne Architecture | Thompson's Architecture |
|--------|----------------------|------------------------|
| **Règle d'Or** | ❌ Violée | ✅ Respectée rigoureusement |
| **Multi-caractères** | ❌ Échec 'NB' | ✅ Support complet |
| **Mutualisation** | ❌ Duplication patterns | ✅ États partagés |
| **Poids** | États individuels | ✅ Entry points factorisés |
| **Extensibilité** | ⚠️ Limitée | ✅ Algorithme classique |
| **Performance** | Baseline | ✅ Équivalente + optimisations |

## 🎯 Utilisation Production

### Pattern Économique Simple
```python
from icgs_core.anchored_nfa_v2 import AnchoredWeightedNFA

# Initialisation
nfa = AnchoredWeightedNFA("economic_validation")

# Ajout contraintes économiques
nfa.add_weighted_regex(
    "agriculture_source",
    ".*FARM.*",           # Pattern business logic
    Decimal('1.5')        # Poids économique
)

nfa.add_weighted_regex(
    "industry_target",
    ".*FACTORY.*",
    Decimal('0.8')
)

# Freeze pour utilisation
nfa.freeze()

# Validation transactions
words = ["FARM_TO_FACTORY", "FARM_TO_MARKET", "BANK_TO_FACTORY"]
for word in words:
    state = nfa.evaluate_to_final_state(word)
    if state:
        print(f"✅ {word} → {state}")
    else:
        print(f"❌ {word} → Rejeté")
```

### Construction LP Intégrée
```python
# Récupération poids pour construction problème LP
agriculture_weights = nfa.get_state_weights_for_measure("agriculture_source")
industry_weights = nfa.get_state_weights_for_measure("industry_target")

print(f"Agriculture: {agriculture_weights}")
# {'final_state_id': Decimal('1.5')}

print(f"Industry: {industry_weights}")
# {'final_state_id': Decimal('0.8')}

# Utilisation directe dans contraintes LP
for state_id, weight in agriculture_weights.items():
    # Création variable flux f_i avec coefficient weight
    program.add_variable(state_id, coefficient=weight)
```

## 🔧 Extension Incrémentale

### Ajout Patterns Dynamique
```python
# Démarrage avec NFA vide
nfa = create_shared_nfa("dynamic")

# Ajout pattern #1
nfa.add_measure("pattern1", ".*A.*", Decimal('1.0'))
print(f"États: {len(nfa.states)}")  # 10 états Thompson's

# Ajout pattern #2 - mutualisation automatique si identique
nfa.add_measure("pattern2", ".*A.*", Decimal('2.0'))
print(f"États: {len(nfa.states)}")  # Toujours 10 - réutilisation!

# Ajout pattern #3 - nouveau pattern
nfa.add_measure("pattern3", ".*B.*", Decimal('3.0'))
print(f"États: {len(nfa.states)}")  # ~20 états - extension
```

### Cycle Freeze/Unfreeze
```python
# Modification dynamique
nfa.add_measure("measure1", "pattern1", weight1)
nfa.add_measure("measure2", "pattern2", weight2)

# Freeze pour évaluation cohérente
nfa.freeze()

# Traitement batch
for transaction_data in transaction_batch:
    word = convert_transaction_to_word(transaction_data)
    result = nfa.evaluate_word_to_final(word)
    # Process result...

# Unfreeze pour nouvelles modifications
nfa.unfreeze()
nfa.add_measure("measure3", "pattern3", weight3)
```

## 📈 Performance & Optimisations

### Mutualisation États
```python
# Pattern identiques → Mutualisation automatique
nfa.add_measure("agri1", ".*FARM.*", Decimal('1.0'))
nfa.add_measure("agri2", ".*FARM.*", Decimal('2.0'))  # Réutilise états
nfa.add_measure("agri3", ".*FARM.*", Decimal('3.0'))  # Réutilise états

# 1 seul pattern Thompson's construit
# 3 entry points avec poids distincts
assert len(nfa.pattern_registry) == 1
assert len(nfa.entry_points) == 3
```

### Extension Incrémentale
```python
# Construction initiale: O(|pattern|)
nfa.add_measure("base", ".*N.*", Decimal('1.0'))

# Extensions: O(|nouveau_pattern|) seulement
nfa.add_measure("ext1", ".*M.*", Decimal('2.0'))  # Construction additionnelle
nfa.add_measure("ext2", ".*N.*", Decimal('3.0'))  # Réutilisation O(1)
```

## 🧪 Tests & Validation

### Tests Unitaires
```bash
# Tests architecture Thompson's
python -m pytest tests/test_thompson_nfa_validation.py -v

# Tests non-régression
python -m pytest tests/test_academic_02_nfa_determinism.py -v
python -m pytest tests/test_academic_03_anchoring_frozen.py -v
```

### Tests Intégration
```python
# Test règle d'or critique
def test_multi_character_support():
    nfa = create_anchored_nfa("test")
    nfa.add_weighted_regex("test", ".*N.*", Decimal('1.0'))
    nfa.freeze()

    # Test critique : mots multi-caractères
    assert nfa.evaluate_to_final_state("N") is not None    # ✅
    assert nfa.evaluate_to_final_state("NB") is not None   # ✅ RÉSOLU!
    assert nfa.evaluate_to_final_state("BN") is not None   # ✅ RÉSOLU!
    assert nfa.evaluate_to_final_state("NBA") is not None  # ✅ RÉSOLU!
```

## 🔮 Extensions Futures

### Optimisations Avancées
- **DFA Conversion** : Déterminisation pour patterns critiques
- **Minimisation** : Réduction états équivalents
- **Cache Intelligent** : Mémorisation résultats fréquents

### Patterns Avancés
- **Classes Caractères** : `[A-Z]+`, `[0-9]*`
- **Groupes** : `(pattern1|pattern2)`
- **Lookahead** : `(?=pattern)`, `(?!pattern)`

### Parallélisation
- **Multi-Threading** : Évaluation batch parallèle
- **SIMD** : Vectorisation transitions caractères
- **GPU** : Évaluation massive patterns

## 📝 Notes Techniques

### Algorithme Thompson's
L'algorithme Thompson's (1968) construit un NFA depuis une expression régulière :
1. **Construction par fragments** atomiques
2. **Concaténation** via ε-transitions
3. **Union** avec nouvel état initial
4. **Fermeture de Kleene** avec boucles ε

### Invariants Architecture
- Tous les NFAs respectent la règle d'or
- États finaux portent les RegexWeights
- Entry points factorisent les poids mesures
- Freeze garantit cohérence évaluations

### Compatibilité API
L'architecture v2 préserve 100% compatibility API existante tout en utilisant l'implémentation Thompson's rigoureuse sous-jacente.

---

**Auteur** : Architecture conçue et implémentée dans le contexte ICGS Core
**Date** : Décembre 2024
**Version** : Thompson's NFA v2.0
**License** : Projet ICGS