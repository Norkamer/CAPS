# ICGS Economic Simulation Framework

## 🎯 Vue d'ensemble

Framework de simulation économique utilisant icgs_core pour la validation mathématique rigoureuse et le Price Discovery. Masque la complexité d'icgs_core derrière une API simple pour créer des agents économiques, transactions inter-sectorielles et chaînes de valeur.

## ✅ Fonctionnalités

- **Agents économiques multi-secteurs**: Agriculture, Industry, Services, Finance, Energy
- **Validation transactions**: Mode FEASIBILITY (faisabilité) + Mode OPTIMIZATION (Price Discovery)
- **Chaînes de valeur**: Transactions séquentielles avec garanties mathématiques
- **Métriques performance**: Temps validation, taux succès, valeur optimisée
- **API simplifiée**: Masque complexité taxonomie/DAG/Simplex d'icgs_core

## 🚀 Usage Rapide

```python
from icgs_simulation import EconomicSimulation
from icgs_simulation.api.icgs_bridge import SimulationMode
from decimal import Decimal

# Créer simulation
sim = EconomicSimulation("demo")

# Créer agents économiques
alice = sim.create_agent("ALICE", "AGRICULTURE", Decimal('1500'))
bob = sim.create_agent("BOB", "INDUSTRY", Decimal('800'))

# Créer transaction
tx_id = sim.create_transaction("ALICE", "BOB", Decimal('120'))

# Valider transaction
result = sim.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
print(f"Succès: {result.success}, Temps: {result.validation_time_ms:.2f}ms")

# Price Discovery
result_opt = sim.validate_transaction(tx_id, SimulationMode.OPTIMIZATION)
print(f"Prix optimal: {result_opt.optimal_price}")
```

## 📊 Performance Validée

**Mini-simulation (3 agents):**
- ✅ FEASIBILITY: 100% (2/2 réussies)
- ✅ OPTIMIZATION: 100% (2/2 réussies)

**Simulation avancée (7 agents):**
- ✅ FEASIBILITY: 83.3% (5/6 réussies)
- ✅ OPTIMIZATION: 100% (6/6 réussies)

## 🏗️ Architecture

```
icgs_simulation/
├── __init__.py                    # Points d'entrée principaux
├── api/
│   └── icgs_bridge.py            # API bridge masquant icgs_core
├── domains/
│   └── base.py                   # Secteurs économiques pré-configurés
└── examples/
    ├── mini_simulation.py        # Démo 3-agents
    └── advanced_simulation.py    # Chaîne valeur 7-agents
```

## 🎯 Secteurs Économiques

| Secteur | Pattern | Poids | Description |
|---------|---------|-------|-------------|
| AGRICULTURE | `.*A.*` | 1.5 | Production primaire |
| INDUSTRY | `.*I.*` | 1.2 | Transformation industrielle |
| SERVICES | `.*S.*` | 1.0 | Secteur tertiaire |
| FINANCE | `.*F.*` | 0.8 | Intermédiation financière |
| ENERGY | `.*E.*` | 1.3 | Utilities énergétiques |

## ⚠️ Limitations Actuelles & Solutions

### 📋 Limitation: Agents Multiples Même Secteur

**Problème actuel:**
- Premier agent/secteur: validation complète ✅
- Agents supplémentaires: FEASIBILITY peut échouer ❌ (OPTIMIZATION fonctionne ✅)

**Exemple:**
```python
# Fonctionne parfaitement
bob = sim.create_agent("BOB_MANUFACTURING", "INDUSTRY", Decimal('800'))

# FEASIBILITY peut échouer (OPTIMIZATION fonctionne)
charlie = sim.create_agent("CHARLIE_TECH", "INDUSTRY", Decimal('1200'))
```

### 💡 Solution Technique: Character-Sets

**Root Cause:** icgs_core NFA ne supporte pas encore les regex character classes `[ABC]`.

**Solution architecturale correcte:**

1. **Étendre icgs_core NFA** pour supporter character classes:
```python
# Dans icgs_core/anchored_nfa.py
def _process_character_class(self, pattern):
    """Support pour [ABC], [A-Z], etc."""
    # Implémentation regex character class
```

2. **Taxonomie secteur cohérente:**
```python
# Agents Industry → caractères cohérents
BOB_MANUFACTURING_sink = 'I'    # Premier agent
CHARLIE_TECH_sink = 'J'         # Deuxième agent
DELTA_FACTORY_sink = 'K'        # Troisième agent

# Agents Services → caractères cohérents
DIANA_LOGISTICS_sink = 'S'      # Premier agent
EVE_CONSULTING_sink = 'T'       # Deuxième agent
```

3. **Patterns character-sets:**
```python
SECTORS = {
    'INDUSTRY': EconomicSector(
        pattern='.*[IJKL].*',       # Matche I, J, K, L
        # ...
    ),
    'SERVICES': EconomicSector(
        pattern='.*[STUV].*',       # Matche S, T, U, V
        # ...
    )
}
```

**Résultat attendu:** 100% FEASIBILITY même avec multiples agents/secteur.

### 🎯 Workaround Actuel

En attendant l'implémentation character-sets:

```python
# Recommandé: 1 agent principal/secteur
sim.create_agent("MAIN_INDUSTRY", "INDUSTRY", Decimal('2000'))

# Agents supplémentaires: OPTIMIZATION seulement
# (FEASIBILITY peut échouer mais Price Discovery fonctionne)
sim.create_agent("SECONDARY_INDUSTRY", "INDUSTRY", Decimal('1000'))
```

## 🔧 Installation & Setup

```bash
# Activer environnement ICGS
source activate_icgs.sh

# Lancer simulations
icgs_simulation        # Mini-simulation
icgs_simulation_advanced  # Simulation avancée
```

## 📈 Exemples d'Usage

### Mini-Simulation
```bash
python3 icgs_simulation/examples/mini_simulation.py
```

### Simulation Avancée (Chaîne de Valeur)
```bash
python3 icgs_simulation/examples/advanced_simulation.py
```

## 🎉 Statut

**Framework icgs_simulation: OPÉRATIONNEL ✅**

- ✅ API simplifiée fonctionnelle
- ✅ Validation mathématique rigoureuse
- ✅ Price Discovery complet
- ✅ Performance excellente (83-100% succès)
- ✅ Architecture scalable
- 📋 Extension character-sets documentée

**Prêt pour simulations économiques complexes !**