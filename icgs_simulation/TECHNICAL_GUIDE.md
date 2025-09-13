# ICGS Simulation - Guide Technique

## 🏗️ Architecture Interne

### Composants Clés

#### 1. EconomicSimulation (icgs_bridge.py)
```python
class EconomicSimulation:
    """API principale masquant icgs_core"""

    def __init__(self, simulation_id: str):
        self.dag = DAG()                    # Core ICGS
        self.simplex_solver = TripleValidationOrientedSimplex()
        self.agents: Dict[str, SimulationAgent] = {}
        self.transactions: List[Transaction] = []
```

**Responsabilités:**
- Masquer complexité icgs_core (DAG, AccountTaxonomy, Simplex)
- Gérer lifecycle agents économiques
- Configuration automatique taxonomie
- Validation transactions avec métriques

#### 2. Taxonomie Character Mapping

**Design actuel (robuste avec limitation):**
```python
def _configure_taxonomy_batch(self):
    sector_char_map = {
        'AGRICULTURE': 'A', 'INDUSTRY': 'I', 'SERVICES': 'S',
        'FINANCE': 'F', 'ENERGY': 'E'
    }

    for agent_id, agent in self.agents.items():
        base_char = sector_char_map.get(agent.sector, 'X')

        # Premier agent/secteur: caractère secteur direct
        if sector_counters[base_char] == 0:
            all_accounts[f"{agent_id}_sink"] = base_char  # A, I, S, F, E
        else:
            # Agents supplémentaires: fallback global unique
            all_accounts[f"{agent_id}_sink"] = chr(fallback_counter)  # Q, R, S...
            fallback_counter += 1
```

## 🎯 Pattern Matching Strategy

### Approche Actuelle
```python
SECTORS = {
    'AGRICULTURE': EconomicSector(pattern='.*A.*', ...),
    'INDUSTRY': EconomicSector(pattern='.*I.*', ...),
    # ...
}
```

### ⚡ Problème: Agents Multiples
```python
# Agent 1 Industry: sink='I' → pattern='.*I.*' ✅ MATCH
# Agent 2 Industry: sink='Q' → pattern='.*I.*' ❌ NO MATCH
```

### 💡 Solution: Character-Sets (À Implémenter)

#### 1. Extension NFA Character Classes

**Fichier cible:** `icgs_core/anchored_nfa_v2.py`

```python
class AnchoredWeightedNFA(WeightedNFA):
    def add_weighted_regex(self, measure_id: str, regex_pattern: str, ...):
        # EXTENSION: Détecter character classes
        if '[' in regex_pattern and ']' in regex_pattern:
            return self._add_character_class_regex(measure_id, regex_pattern, ...)
        else:
            return super().add_weighted_regex_simple(measure_id, regex_pattern, ...)

    def _add_character_class_regex(self, measure_id: str, pattern: str, ...):
        """
        Nouveau: Support [ABC], [A-Z], etc.

        Pattern '.*[IJKL].*' devient:
        - État initial → '.*' → [I|J|K|L] → '.*' → état final
        """
        # Parsing character class [IJKL]
        char_class = self._extract_character_class(pattern)  # ['I', 'J', 'K', 'L']

        # Créer branches NFA pour chaque caractère
        for char in char_class:
            individual_pattern = pattern.replace('['+char_class+']', char)
            self._add_branch(measure_id, individual_pattern, weight)

        return final_state
```

#### 2. Taxonomie Character-Sets Cohérente

```python
def _configure_taxonomy_batch_v2(self):
    """Version character-sets avec allocation cohérente"""

    sector_ranges = {
        'AGRICULTURE': ['A', 'B', 'C', 'D'],    # A-D pour Agriculture
        'INDUSTRY': ['I', 'J', 'K', 'L'],       # I-L pour Industry
        'SERVICES': ['S', 'T', 'U', 'V'],       # S-V pour Services
        'FINANCE': ['F', 'G', 'H', 'M'],        # F,G,H,M pour Finance
        'ENERGY': ['E', 'N', 'O', 'P']          # E,N,O,P pour Energy
    }

    for agent_id, agent in self.agents.items():
        sector_chars = sector_ranges.get(agent.sector, ['X'])
        agent_index = sector_counters[agent.sector]

        # Allocation cohérente dans range secteur
        if agent_index < len(sector_chars):
            all_accounts[f"{agent_id}_sink"] = sector_chars[agent_index]
        else:
            # Fallback pour >4 agents/secteur
            all_accounts[f"{agent_id}_sink"] = chr(ord('Z') - agent_index)
```

#### 3. Patterns Character-Sets

```python
SECTORS_V2 = {
    'AGRICULTURE': EconomicSector(
        name='AGRICULTURE',
        pattern='.*[ABCD].*',          # Matche A, B, C, D
        weight=Decimal('1.5'),
        # ...
    ),
    'INDUSTRY': EconomicSector(
        name='INDUSTRY',
        pattern='.*[IJKL].*',          # Matche I, J, K, L
        weight=Decimal('1.2'),
        # ...
    ),
    # ...
}
```

## 📊 Impact Attendu

### Performance Simulation
```python
# AVANT (limitation actuelle)
mini_simulation:     100% FEASIBILITY, 100% OPTIMIZATION  ✅
advanced_simulation: 83.3% FEASIBILITY, 100% OPTIMIZATION ⚠️

# APRÈS (avec character-sets)
mini_simulation:     100% FEASIBILITY, 100% OPTIMIZATION  ✅
advanced_simulation: 100% FEASIBILITY, 100% OPTIMIZATION  ✅
```

### Capacités Étendues
- ✅ Multiples agents/secteur avec validation complète
- ✅ Chaînes de valeur complexes sans limitation
- ✅ Scalabilité économies réalistes (5-10 agents/secteur)

## 🔧 Plan d'Implémentation

### Phase 1: Extension icgs_core NFA
1. **Analyser** parsing regex existant dans `weighted_nfa_v2.py`
2. **Implémenter** `_extract_character_class()` pour patterns `[ABC]`
3. **Étendre** `add_weighted_regex()` avec détection character classes
4. **Tester** avec patterns simples `.*[AB].*`

### Phase 2: Taxonomie Character-Sets
1. **Modifier** `_configure_taxonomy_batch()` avec ranges secteurs
2. **Mettre à jour** `domains/base.py` avec patterns `.*[ABCD].*`
3. **Valider** avec agents multiples même secteur

### Phase 3: Tests & Validation
1. **Étendre** tests académiques avec character-sets
2. **Valider** simulation avancée 100% FEASIBILITY
3. **Benchmark** performance vs approche actuelle

## 🎯 État Actuel vs Cible

### Actuellement ✅
- Framework simulation opérationnel
- API économique simplifiée
- Price Discovery complet
- Performance excellente (83-100%)

### Extension Character-Sets 🚀
- **Objectif:** Passage 83.3% → 100% FEASIBILITY
- **Impact:** Agents multiples/secteur sans limitation
- **Effort:** ~2-3 jours développement icgs_core + simulation

**Framework prêt pour extension character-sets !**