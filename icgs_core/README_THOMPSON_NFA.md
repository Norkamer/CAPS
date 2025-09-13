# Thompson's NFA - Guide Développeur ICGS

## 🚀 Quick Start

```python
from icgs_core.anchored_nfa_v2 import AnchoredWeightedNFA
from decimal import Decimal

# Création NFA production
nfa = AnchoredWeightedNFA("production_nfa")

# Ajout contraintes économiques
nfa.add_weighted_regex("agriculture", ".*FARM.*", Decimal('1.5'))
nfa.add_weighted_regex("industry", ".*FACTORY.*", Decimal('0.8'))

# Freeze pour utilisation
nfa.freeze()

# Validation
result = nfa.evaluate_to_final_state("FARM_TO_FACTORY")
print(f"Résultat: {result}")  # État final ou None
```

## 🎯 Migration v1 → v2

### Ancien Code
```python
# v1 - Problématique
from icgs_core.anchored_nfa import AnchoredWeightedNFA

nfa = AnchoredWeightedNFA("old")
nfa.add_weighted_regex("measure", ".*N.*", Decimal('1.0'))
result = nfa.evaluate_to_final_state("NB")  # ❌ None (échec)
```

### Nouveau Code
```python
# v2 - Thompson's rigoureux
from icgs_core.anchored_nfa_v2 import AnchoredWeightedNFA

nfa = AnchoredWeightedNFA("new")
nfa.add_weighted_regex("measure", ".*N.*", Decimal('1.0'))
result = nfa.evaluate_to_final_state("NB")  # ✅ État final
```

## 📊 Composants Architecture

| Module | Responsabilité |
|--------|---------------|
| `regex_parser.py` | Parsing patterns → tokens |
| `thompson_nfa.py` | Construction NFA Thompson's |
| `shared_nfa.py` | NFA partagé + entry points |
| `weighted_nfa_v2.py` | Compatibility layer |
| `anchored_nfa_v2.py` | API production + ancrage |

## ⚡ Optimisations

### Mutualisation Automatique
```python
nfa = create_shared_nfa()

# Pattern identique → États partagés
nfa.add_measure("m1", ".*N.*", Decimal('1.0'))
nfa.add_measure("m2", ".*N.*", Decimal('2.0'))  # Réutilise NFA
nfa.add_measure("m3", ".*N.*", Decimal('3.0'))  # Réutilise NFA

print(f"Patterns: {len(nfa.pattern_registry)}")  # 1
print(f"Mesures: {len(nfa.entry_points)}")      # 3
```

### Poids Factorisés
```python
# Récupération poids pour LP
weights = nfa.get_state_weights_for_measure("measure_id")
# {'state_id': Decimal('weight')} - factorisé à l'entry point
```

## 🔧 Cycle de Vie

```python
# 1. Construction
nfa = AnchoredWeightedNFA("lifecycle")

# 2. Configuration
nfa.add_weighted_regex("measure1", "pattern1", weight1)
nfa.add_weighted_regex("measure2", "pattern2", weight2)

# 3. Freeze (requis pour évaluation)
nfa.freeze()

# 4. Évaluation batch
for word in words:
    result = nfa.evaluate_to_final_state(word)

# 5. Modification (unfreeze requis)
nfa.unfreeze()
nfa.add_weighted_regex("measure3", "pattern3", weight3)
```

## 🧪 Tests & Debug

### Tests Unitaires
```bash
# Tests architecture Thompson's
pytest tests/test_thompson_nfa_validation.py

# Tests spécifiques NFA
pytest tests/test_academic_02_nfa_determinism.py
pytest tests/test_academic_03_anchoring_frozen.py
```

### Debug Patterns
```python
# Validation pattern supporté
from icgs_core.regex_parser import create_icgs_regex_parser

parser = create_icgs_regex_parser()
if parser.validate_pattern(".*complex.*"):
    tokens = parser.parse(".*complex.*")
    print(f"Tokens: {[str(t) for t in tokens]}")
```

### Performance Monitoring
```python
# Stats NFA
stats = nfa.get_shared_nfa_stats()
print(f"States: {stats['current_states']}")
print(f"Patterns: {stats['patterns_registered']}")
print(f"Evaluations: {stats['evaluations_performed']}")
```

## ⚠️ Points d'Attention

### Freeze Requis
```python
nfa.add_weighted_regex("measure", "pattern", weight)
# ❌ Évaluation sans freeze
result = nfa.evaluate_to_final_state("word")  # RuntimeError

# ✅ Freeze avant évaluation
nfa.freeze()
result = nfa.evaluate_to_final_state("word")  # OK
```

### Patterns Supportés
```python
# ✅ Supportés
patterns_ok = ["N", ".*", ".*N.*", "^start", "end$", "A+", "B?"]

# ❌ Non supportés (pour l'instant)
patterns_todo = ["[A-Z]+", "a{2,5}", "(A|B)", "(?=lookahead)"]
```

### API Compatibility
```python
# v2 préserve 100% API v1
# Migration transparente en changeant juste l'import
from icgs_core.anchored_nfa_v2 import AnchoredWeightedNFA  # v2
# au lieu de:
# from icgs_core.anchored_nfa import AnchoredWeightedNFA  # v1
```

## 🏆 Bénéfices Clés

1. **Règle d'Or Respectée** - Automates théoriquement corrects
2. **Multi-caractères Supportés** - "NB", "ABC" fonctionnent
3. **Mutualisation Optimale** - États partagés entre patterns
4. **Extensibilité Future** - Base solide pour optimisations
5. **API Compatible** - Migration transparente
6. **Performance Équivalente** - Pas de régression

---
**Note** : Cette architecture respecte rigoureusement les fondamentaux théoriques tout en optimisant pour les besoins ICGS production.