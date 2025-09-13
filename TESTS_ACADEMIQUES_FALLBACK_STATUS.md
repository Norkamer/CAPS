# Status Fallback APIs - Tests Académiques ICGS

## Vue d'ensemble

Documentation du status fallback des tests académiques ICGS. Indique clairement quels tests utilisent les APIs avec mécanisme fallback (`evaluate_word()` / `evaluate_to_final_state()`) et lesquels ne sont pas pertinents.

## Tests PERTINENTS (utilisent APIs avec fallback)

### ✅ test_academic_02_nfa_determinism.py
**APIs utilisées :** `evaluate_word()`, `evaluate_to_final_state()`
**Status :** PERTINENT - utilise directement les NFAs
**Fallback indications :**
- `evaluate_word("ab")` → Utilise API unifiée (standard + character-class)
- `evaluate_to_final_state("somepattern1")` → API primaire pipeline

**Code exemple :**
```python
final_states = nfa.evaluate_word(word)  # 🔄 FALLBACK API possible
result = anchored_nfa.evaluate_to_final_state(word)  # 🎯 PRIMARY API
```

### ✅ test_academic_03_anchoring_frozen.py
**APIs utilisées :** `evaluate_to_final_state()`
**Status :** PERTINENT - teste ancrage et freeze
**Fallback indications :**
- `evaluate_to_final_state(word)` → API primaire avec gestion frozen states
- Tests frozen vs unfrozen → Cohérence API primaire

**Code exemple :**
```python
result_state = self.nfa.evaluate_to_final_state(word)  # 🎯 PRIMARY API
frozen_result = self.nfa.evaluate_to_final_state(account)  # 🎯 PRIMARY API (frozen)
```

### ❌ test_academic_20_nfa_character_class_integration.py
**APIs utilisées :** `evaluate_word()` (CASSÉ)
**Status :** CASSÉ - utilise ancienne API `.total_weight`
**Problème :** Code utilise `result.total_weight` mais `evaluate_word()` retourne `Set[str]`

**Code cassé :**
```python
evaluation = self.nfa.evaluate_word(word)
assert evaluation.total_weight > 0  # ❌ ERREUR: Set n'a pas .total_weight
```

**Solution requise :** Adapter au nouveau retour `Set[str]`

## Tests NON PERTINENTS (n'utilisent pas APIs avec fallback)

### ❌ test_academic_01_taxonomy_invariants.py
**Raison :** Tests taxonomie pure - aucun appel NFA
**Architecture :** `AccountTaxonomy`, `character_set_manager`
**Indication fallback :** NON APPLICABLE

### ❌ test_academic_16_FIXED.py
**Raison :** Architecture DAG complète - NFAs encapsulés
**Architecture :** `DAG.add_transaction()` → pipeline interne
**Indication fallback :** NON APPLICABLE (NFAs non exposés)

**Explication :** Le test passe par `DAG.add_transaction()` qui utilise le pipeline `path_enumerator.enumerate_and_classify()` mais les NFAs sous-jacents ne sont pas accessibles directement aux tests.

### ❌ test_academic_05_economic_formulation.py
**Raison :** Tests formulation économique - pas d'évaluation NFA directe
**Architecture :** Simplex, contraintes économiques
**Indication fallback :** NON APPLICABLE

### ❌ test_academic_09_path_enumeration_basic.py
**Raison :** Tests énumération paths - utilise DAG PathEnumerator
**Architecture :** `DAGPathEnumerator` avec NFAs internes
**Indication fallback :** NON APPLICABLE (NFAs encapsulés)

### ❌ test_academic_11_dag_enumerator_integration.py
**Raison :** Tests intégration DAG - NFAs internes au pipeline
**Architecture :** Pipeline DAG complet
**Indication fallback :** NON APPLICABLE

### ❌ test_academic_12_transaction_edge_processing.py
**Raison :** Tests processing transactions - niveau DAG
**Architecture :** Transaction processing via DAG
**Indication fallback :** NON APPLICABLE

### ❌ test_academic_13_multi_source_enumeration.py
**Raison :** Tests énumération multi-source - DAG PathEnumerator
**Architecture :** PathEnumerator avec NFAs internes
**Indication fallback :** NON APPLICABLE

### ❌ test_academic_19_character_sets_validation.py
**Raison :** Tests character-sets nommés - pas d'évaluation NFA
**Architecture :** `NamedCharacterSetManager`, `AccountTaxonomy`
**Indication fallback :** NON APPLICABLE

## Résumé Status Fallback

| Test | API Calls | Status | Fallback Pertinent |
|------|-----------|--------|-------------------|
| 01_taxonomy_invariants | Aucun | ❌ | NON |
| 02_nfa_determinism | evaluate_word, evaluate_to_final_state | ✅ | **OUI** |
| 03_anchoring_frozen | evaluate_to_final_state | ✅ | **OUI** |
| 05_economic_formulation | Aucun direct | ❌ | NON |
| 09_path_enumeration | NFAs encapsulés | ❌ | NON |
| 11_dag_enumerator | NFAs encapsulés | ❌ | NON |
| 12_transaction_edge | NFAs encapsulés | ❌ | NON |
| 13_multi_source | NFAs encapsulés | ❌ | NON |
| 16_FIXED | DAG pipeline | ❌ | NON |
| 19_character_sets | Aucun NFA | ❌ | NON |
| 20_nfa_character_class | evaluate_word (CASSÉ) | ❌ | CASSÉ |

## Recommandations

### Tests à Monitorer (2 tests)
- **Test 02** : Ajouter logging explicite `🎯 PRIMARY API` vs `🔄 FALLBACK API`
- **Test 03** : Ajouter indication usage API primaire pour ancrage

### Tests à Corriger (1 test)
- **Test 20** : Adapter code pour nouveau retour `Set[str]` de `evaluate_word()`

### Tests Non Concernés (8 tests)
- Aucune action requise - tests fonctionnent à des niveaux d'abstraction plus élevés

## Code Diagnostic Minimal

Pour les 2 tests pertinents :

```python
# Test 02 & 03 - ajout simple
def test_nfa_evaluation(self):
    result = nfa.evaluate_word("test")
    print(f"   🔄 FALLBACK API: evaluate_word() → {len(result)} states")

    final_state = nfa.evaluate_to_final_state("test")
    print(f"   🎯 PRIMARY API: evaluate_to_final_state() → {final_state}")
```

**Conclusion :** Sur 11 tests académiques, seulement 2 sont pertinents pour l'indication fallback. C'est normal car la plupart des tests ICGS fonctionnent à des niveaux d'abstraction plus élevés (DAG, Pipeline, Taxonomie).