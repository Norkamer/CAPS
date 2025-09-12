# 🏗️ ICGS - Intelligent Computation Graph System

## Vue d'Ensemble

**ICGS (Intelligent Computation Graph System)** est un système révolutionnaire de validation de transactions économiques utilisant une approche mathématiquement rigoureuse combinant :

- **DAG (Graphes Dirigés Acycliques)** : Structure de données représentant comptes et transactions
- **WeightedNFA (Automates Finis Pondérés)** : Évaluation de patterns regex pour classification des flux  
- **Simplex Phase 1** : Validation de faisabilité économique avec garanties mathématiques absolues

## Philosophie Architecture

- **Rigueur Mathématique** : Preuves formelles de correction pour tous les algorithmes
- **Cohérence Transactionnelle** : États protégés avec validation atomique
- **Extensibilité** : Architecture modulaire permettant évolution et optimisations
- **Performance** : Optimisations warm-start, cache, et réutilisation de pivots

## Structure du Projet

```
ICGS/
├── icgs-core/                     # Composants principaux
│   ├── account_taxonomy.py       # Fonction taxonomique historisée
│   ├── anchored_nfa.py          # NFA avec ancrage automatique  
│   ├── linear_programming.py     # Structures LP et constructeurs
│   ├── simplex_solver.py         # Triple validation Simplex
│   └── dag.py                    # Extension pipeline validation
├── tests/                        # Suite tests complète avec tests académiques
├── examples/                     # Exemples d'utilisation validés
└── docs/                         # Documentation technique complète
```

## Installation

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Utilisation Rapide

```python
from icgs_core import DAG, AccountTaxonomy
from icgs_core.linear_programming import LinearProgram

# Créer DAG avec validation ICGS
dag = DAG()
result = dag.add_transaction(source_account, target_account, transaction)
# True si validation économique réussie, False sinon
```

## Documentation Complète

Voir `ICGS_MASTER_RECONSTRUCTION_BLUEPRINT.md` pour la spécification technique complète.

## Statut

✅ **Phase 1-2**: Foundation mathématique et intégration production  
🚧 **Phase 3**: Architecture hybride et optimisations avancées  
🔮 **Phase 4+**: Price discovery mathématique et scalabilité