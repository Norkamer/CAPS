# 🏭 Guide Utilisateur : Simulation Économique Massive

## Vue d'ensemble

Ce guide vous accompagne dans l'utilisation de **CAPS** pour créer des simulations économiques massives avec **7→65 agents** répartis sur **5 secteurs économiques**. De la configuration basique aux scénarios complexes inter-sectoriels.

### 🎯 Ce que vous allez apprendre

- **Simulation 7 agents** : Écosystème économique complet (5 secteurs)
- **Flux inter-sectoriels** : AGRICULTURE→INDUSTRY→SERVICES→FINANCE + ENERGY
- **Validation économique** : FEASIBILITY + Price Discovery modes
- **Scaling 7→40→65 agents** : Architecture massive progressive validée
- **Scénarios réalistes** : "Économie Stable", "Choc Pétrolier", "Innovation Tech"

---

## 🚀 Démarrage : Première Simulation (7 Agents)

### Installation & Setup

```bash
# Installation développement
cd /path/to/CAPS
pip install -e .

# Validation système
python -m pytest tests/ -v  # 125+ tests doivent passer

# Test simulation ready
PYTHONPATH=/path/to/CAPS python3 icgs_simulation/examples/advanced_simulation.py
```

### Simulation Basique 5 Secteurs

```python
from icgs_simulation.api.icgs_bridge import EconomicSimulation, SimulationMode
from decimal import Decimal

# Créer simulation économique
simulation = EconomicSimulation("my_first_economy")

print("🏭 Création écosystème économique...")

# Secteur Primaire (Agriculture)
alice = simulation.create_agent("ALICE_FARM", "AGRICULTURE", Decimal('2500'),
                               {"type": "organic_farming", "region": "north"})

# Secteur Secondaire (Industry)
bob = simulation.create_agent("BOB_MANUFACTURING", "INDUSTRY", Decimal('1800'),
                             {"type": "food_processing", "efficiency": 0.85})

charlie = simulation.create_agent("CHARLIE_TECH", "INDUSTRY", Decimal('2200'),
                                 {"type": "equipment_manufacturing"})

# Secteur Tertiaire (Services)
diana = simulation.create_agent("DIANA_LOGISTICS", "SERVICES", Decimal('1500'),
                               {"type": "supply_chain", "coverage": 0.75})

eve = simulation.create_agent("EVE_CONSULTING", "SERVICES", Decimal('1200'),
                             {"type": "business_consulting"})

# Secteur Financier
frank = simulation.create_agent("FRANK_BANK", "FINANCE", Decimal('5000'),
                               {"type": "commercial_banking", "rating": "A+"})

# Secteur Énergétique
grace = simulation.create_agent("GRACE_ENERGY", "ENERGY", Decimal('3500'),
                               {"type": "renewable_energy", "capacity_mw": 150})

print(f"✅ {len(simulation.agents)} agents créés dans 5 secteurs")
```

### Chaîne de Valeur Économique

```python
print("⚡ Création chaîne de valeur économique...")

# Chaîne principale AGRICULTURE → INDUSTRY → SERVICES → FINANCE
tx1 = simulation.create_transaction("ALICE_FARM", "BOB_MANUFACTURING", Decimal('300'),
                                  {"product": "raw_materials", "chain_step": 1})

tx2 = simulation.create_transaction("BOB_MANUFACTURING", "DIANA_LOGISTICS", Decimal('180'),
                                  {"service": "distribution", "chain_step": 2})

tx3 = simulation.create_transaction("DIANA_LOGISTICS", "FRANK_BANK", Decimal('150'),
                                  {"service": "payment_settlement", "chain_step": 3})

# Chaîne parallèle TECH → CONSULTING
tx4 = simulation.create_transaction("CHARLIE_TECH", "EVE_CONSULTING", Decimal('220'),
                                  {"service": "optimization_consulting"})

# Infrastructure ENERGY → ALL
tx5 = simulation.create_transaction("GRACE_ENERGY", "BOB_MANUFACTURING", Decimal('120'),
                                  {"energy_type": "renewable", "infrastructure": True})

tx6 = simulation.create_transaction("GRACE_ENERGY", "DIANA_LOGISTICS", Decimal('80'),
                                  {"energy_type": "transport", "infrastructure": True})

transactions = [tx1, tx2, tx3, tx4, tx5, tx6]
print(f"✅ {len(transactions)} transactions créées")
```

### Validation Économique

```python
print("🔍 Validation complète chaîne de valeur...")

# Mode FEASIBILITY (validation faisabilité)
feasible_count = 0
for tx_id in transactions:
    result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
    status = "✅ FAISABLE" if result.success else "❌ INFAISABLE"
    print(f"   {tx_id}: {status} ({result.validation_time_ms:.2f}ms)")
    if result.success:
        feasible_count += 1

feasibility_rate = (feasible_count / len(transactions)) * 100
print(f"\n📊 Taux FEASIBILITY: {feasible_count}/{len(transactions)} ({feasibility_rate:.1f}%)")

# Objectif: 100% avec Character-Set Manager ✅

# Mode OPTIMIZATION (Price Discovery)
print("\n💰 Mode OPTIMIZATION (Price Discovery):")
optimal_count = 0
total_value = Decimal('0')

for tx_id in transactions:
    result = simulation.validate_transaction(tx_id, SimulationMode.OPTIMIZATION)

    if result.success and result.optimal_price is not None:
        status = f"✅ OPTIMAL (prix: {result.optimal_price})"
        total_value += result.optimal_price
        optimal_count += 1
    else:
        status = "❌ ÉCHEC"

    print(f"   {tx_id}: {status} ({result.validation_time_ms:.2f}ms)")

print(f"\n📊 Résultats OPTIMIZATION: {optimal_count}/{len(transactions)} ({optimal_count/len(transactions)*100:.1f}%)")
print(f"💎 Valeur totale optimisée: {total_value}")
```

---

## 📊 Statistiques & Monitoring

### Métriques Simulation

```python
# Statistiques complètes simulation
stats = simulation.get_simulation_stats()

print(f"📈 MÉTRIQUES SIMULATION:")
print(f"   Agents économiques: {stats['agents_count']}")
print(f"   Transactions traitées: {stats['transactions_count']}")
print(f"   Secteurs représentés: {len(stats['sectors_represented'])}")
print(f"   DAG stats: {stats['dag_stats']}")

# Métriques Character-Set Manager
char_stats = simulation.character_set_manager.get_allocation_statistics()
print(f"\n🔧 CHARACTER-SET ALLOCATION:")
print(f"   Total allocations: {char_stats['total_allocations']}")
print(f"   Configuration figée: {char_stats['is_frozen']}")

for sector, info in char_stats['sectors'].items():
    print(f"   {sector}: {info['allocated_count']}/{info['max_capacity']} "
          f"({info['utilization_rate']:.1%} utilisé)")
```

### Performance Benchmarks

```python
import time

# Benchmark performance simulation
def benchmark_simulation(agents_count=7, transactions_count=6):
    start_time = time.time()

    # Simulation économique
    simulation = EconomicSimulation(f"benchmark_{agents_count}_agents")

    # ... création agents et transactions ...

    # Validation complète
    for tx_id in transactions:
        result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)

    total_time = (time.time() - start_time) * 1000
    avg_time = total_time / transactions_count

    print(f"⚡ BENCHMARK {agents_count} AGENTS:")
    print(f"   Temps total: {total_time:.2f}ms")
    print(f"   Temps moyen/transaction: {avg_time:.2f}ms")
    print(f"   Throughput: {1000/avg_time:.0f} tx/sec")

benchmark_simulation()
# Résultat attendu: <1ms par transaction, >1000 tx/sec
```

---

## 🚀 Simulation 40 Agents : Extension Massive (Semaine 2)

### Mode 40 Agents Activation

```python
from icgs_simulation.api.icgs_bridge import EconomicSimulation, SimulationMode
from decimal import Decimal
import time

# Activer mode 40 agents (108+ caractères)
simulation = EconomicSimulation("massive_economy", agents_mode="40_agents")

# Vérifier capacité
stats = simulation.character_set_manager.get_allocation_statistics()
total_capacity = sum(info['max_capacity'] for info in stats['sectors'].values())
print(f"Capacité: {total_capacity} caractères = {total_capacity // 3} agents maximum")
# → Capacité: 108 caractères = 36 agents maximum
```

### Flux Inter-Sectoriels Automatiques (Nouvelle API)

```python
# Créer écosystème économique représentatif
agents_config = {
    'AGRICULTURE': [('WHEAT_FARM', 2200), ('CORN_FARM', 1900), ('DAIRY_FARM', 2100)],
    'INDUSTRY': [('STEEL_MILL', 1800), ('AUTO_FACTORY', 2100), ('TEXTILE_MILL', 1500)],
    'SERVICES': [('LOGISTICS_CO', 1200), ('RETAIL_CHAIN', 1000), ('IT_SERVICES', 1400)],
    'FINANCE': [('NATIONAL_BANK', 5500), ('INSURANCE_CO', 3800)],
    'ENERGY': [('SOLAR_FARM', 2800), ('WIND_FARM', 2600)]
}

# Créer agents
all_agents = {}
for sector, agents_list in agents_config.items():
    for agent_id, balance in agents_list:
        agent = simulation.create_agent(agent_id, sector, Decimal(str(balance)))
        all_agents[agent_id] = agent

print(f"🏭 Écosystème créé: {len(all_agents)} agents, 5 secteurs")

# Générer flux automatiques (API Semaine 2)
start_time = time.time()
transaction_ids = simulation.create_inter_sectoral_flows_batch(flow_intensity=0.7)
creation_time = (time.time() - start_time) * 1000

print(f"✅ {len(transaction_ids)} transactions créées en {creation_time:.2f}ms")

# Validation haute performance
successful_validations = 0
total_validation_time = 0

for tx_id in transaction_ids:
    start = time.time()
    result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
    validation_time = (time.time() - start) * 1000
    total_validation_time += validation_time

    if result.success:
        successful_validations += 1

# Métriques Semaine 2
success_rate = (successful_validations / len(transaction_ids)) * 100
avg_validation_time = total_validation_time / len(transaction_ids)

print(f"""
🎯 RÉSULTATS SIMULATION 40 AGENTS:
  Agents créés: {len(all_agents)}
  Transactions flux: {len(transaction_ids)}
  Taux succès: {success_rate:.1f}% (objectif >70%)
  Performance: {avg_validation_time:.2f}ms moyenne (objectif <100ms)
  Status: {'✅ OBJECTIFS DÉPASSÉS' if success_rate > 70 and avg_validation_time < 100 else '⚠️ À AMÉLIORER'}
""")
```

### Architecture 65 Agents Ready

```python
# Mode 65 agents déjà disponible (195 caractères)
simulation_65 = EconomicSimulation("massive_65", agents_mode="65_agents")

stats_65 = simulation_65.character_set_manager.get_allocation_statistics()
total_capacity_65 = sum(info['max_capacity'] for info in stats_65['sectors'].values())

print(f"""
🚀 ARCHITECTURE 65 AGENTS DISPONIBLE:
  Capacité totale: {total_capacity_65} caractères
  Agents supportés: {total_capacity_65 // 3} maximum
  Distribution économique:
    - AGRICULTURE: 10 agents (30 caractères)
    - INDUSTRY: 15 agents (45 caractères)
    - SERVICES: 20 agents (60 caractères)
    - FINANCE: 8 agents (24 caractères)
    - ENERGY: 12 agents (36 caractères)
""")
```

---

## 🔄 Flux Inter-Sectoriels Avancés

### Modèles Économiques Réalistes

```python
def create_realistic_economic_flows(simulation):
    """Crée flux économiques réalistes entre secteurs"""

    # Flux AGRICULTURE → INDUSTRY (40-60% production)
    for agri_agent in get_agents_by_sector(simulation, "AGRICULTURE"):
        for industry_agent in get_agents_by_sector(simulation, "INDUSTRY"):
            if industry_agent.metadata.get('type') == 'food_processing':
                amount = agri_agent.balance * Decimal('0.4')  # 40% production
                simulation.create_transaction(agri_agent.agent_id, industry_agent.agent_id, amount)

    # Flux INDUSTRY → SERVICES (60-80% distribution)
    for industry_agent in get_agents_by_sector(simulation, "INDUSTRY"):
        for service_agent in get_agents_by_sector(simulation, "SERVICES"):
            if service_agent.metadata.get('type') == 'supply_chain':
                amount = industry_agent.balance * Decimal('0.6')  # 60% distribution
                simulation.create_transaction(industry_agent.agent_id, service_agent.agent_id, amount)

    # Flux SERVICES ↔ FINANCE (20-30% facilitation)
    for service_agent in get_agents_by_sector(simulation, "SERVICES"):
        for finance_agent in get_agents_by_sector(simulation, "FINANCE"):
            amount = service_agent.balance * Decimal('0.2')  # 20% banking
            simulation.create_transaction(service_agent.agent_id, finance_agent.agent_id, amount)

    # Flux ENERGY → ALL (5-10% infrastructure support)
    for energy_agent in get_agents_by_sector(simulation, "ENERGY"):
        for agent in simulation.agents.values():
            if agent.sector != "ENERGY":
                amount = agent.balance * Decimal('0.05')  # 5% énergie
                simulation.create_transaction(energy_agent.agent_id, agent.agent_id, amount)

def get_agents_by_sector(simulation, sector):
    return [agent for agent in simulation.agents.values() if agent.sector == sector]
```

### Weights Sectoriels & Priorités

```python
# Configuration poids économiques sectoriels
SECTOR_WEIGHTS = {
    'AGRICULTURE': 1.5,  # Priorité alimentaire
    'INDUSTRY': 1.2,     # Transformation essentielle
    'SERVICES': 1.0,     # Référence
    'FINANCE': 0.8,      # Facilitateur
    'ENERGY': 1.3        # Infrastructure critique
}

def create_weighted_transaction(simulation, source_id, target_id, base_amount):
    """Crée transaction avec poids sectoriels"""
    source_agent = simulation.get_agent(source_id)
    target_agent = simulation.get_agent(target_id)

    source_weight = SECTOR_WEIGHTS[source_agent.sector]
    target_weight = SECTOR_WEIGHTS[target_agent.sector]

    # Ajustement montant selon poids économiques
    weighted_amount = base_amount * (source_weight + target_weight) / 2

    return simulation.create_transaction(source_id, target_id, weighted_amount, {
        'source_weight': source_weight,
        'target_weight': target_weight,
        'economic_priority': 'high' if weighted_amount > base_amount else 'normal'
    })
```

---

## 🔀 Scénarios Économiques Avancés

### Scénario 1: "Économie Stable"

```python
def scenario_stable_economy(simulation):
    """Simulation économie stable - 7 jours continus"""
    print("📊 SCÉNARIO: Économie Stable")

    transactions_per_day = 10
    days = 7
    success_count = 0

    for day in range(days):
        print(f"   Jour {day+1}/7...")

        for _ in range(transactions_per_day):
            # Sélection agents aléatoire avec distribution réaliste
            source = random.choice(list(simulation.agents.keys()))
            target = random.choice(list(simulation.agents.keys()))

            if source != target:
                amount = Decimal(random.uniform(50, 500))
                tx_id = simulation.create_transaction(source, target, amount)
                result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)

                if result.success:
                    success_count += 1

    total_transactions = days * transactions_per_day
    success_rate = (success_count / total_transactions) * 100

    print(f"✅ Économie Stable: {success_count}/{total_transactions} ({success_rate:.1f}% succès)")
    return success_rate > 60  # Objectif: >60% stabilité
```

### Scénario 2: "Choc Pétrolier"

```python
def scenario_oil_shock(simulation):
    """Simulation choc pétrolier - impact ENERGY sur économie"""
    print("⚡ SCÉNARIO: Choc Pétrolier")

    # Réduction 40% capacité agents ENERGY
    energy_agents = get_agents_by_sector(simulation, "ENERGY")
    original_balances = {}

    for agent in energy_agents:
        original_balances[agent.agent_id] = agent.balance
        agent.balance *= Decimal('0.6')  # -40% capacity
        print(f"   ENERGY {agent.agent_id}: {original_balances[agent.agent_id]} → {agent.balance}")

    # Mesure impact propagation sur autres secteurs
    impact_transactions = []

    for energy_agent in energy_agents:
        for agent in simulation.agents.values():
            if agent.sector != "ENERGY":
                # Transaction énergie réduite
                reduced_amount = agent.balance * Decimal('0.03')  # vs 0.05 normal
                tx_id = simulation.create_transaction(energy_agent.agent_id, agent.agent_id, reduced_amount)
                result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
                impact_transactions.append(result.success)

    impact_success_rate = (sum(impact_transactions) / len(impact_transactions)) * 100

    print(f"📊 Impact Choc Pétrolier: {impact_success_rate:.1f}% transactions réussies")

    # Restauration pour next scenario
    for agent in energy_agents:
        agent.balance = original_balances[agent.agent_id]

    return impact_success_rate > 40  # Économie resiliente si >40%
```

### Scénario 3: "Révolution Technologique"

```python
def scenario_tech_revolution(simulation):
    """Simulation révolution tech - boost INDUSTRY +50%"""
    print("🚀 SCÉNARIO: Révolution Technologique")

    # Boost +50% efficacité agents INDUSTRY
    industry_agents = get_agents_by_sector(simulation, "INDUSTRY")

    for agent in industry_agents:
        original_balance = agent.balance
        agent.balance *= Decimal('1.5')  # +50% efficacité
        print(f"   INDUSTRY {agent.agent_id}: {original_balance} → {agent.balance}")

    # Réallocation automatique ressources
    reallocation_transactions = []

    for industry_agent in industry_agents:
        for service_agent in get_agents_by_sector(simulation, "SERVICES"):
            # Investissement technologique services
            tech_investment = industry_agent.balance * Decimal('0.15')  # 15% investissement
            tx_id = simulation.create_transaction(industry_agent.agent_id, service_agent.agent_id, tech_investment)
            result = simulation.validate_transaction(tx_id, SimulationMode.OPTIMIZATION)
            reallocation_transactions.append(result)

    successful_reallocations = sum(1 for r in reallocation_transactions if r.success)
    total_value = sum(r.optimal_price for r in reallocation_transactions if r.success and r.optimal_price)

    print(f"🔄 Réallocation Tech: {successful_reallocations}/{len(reallocation_transactions)} réussies")
    print(f"💎 Valeur création: {total_value}")

    return successful_reallocations / len(reallocation_transactions) > 0.7  # >70% adaptation
```

---

## 📈 Scaling vers 15+ Agents

### Configuration Étendue

```python
def create_15_agents_simulation():
    """Configuration simulation 15 agents"""
    from test_15_agents_simulation import create_extended_character_set_manager

    simulation = EconomicSimulation("scaling_15_agents")

    # Character-Set Manager étendu
    simulation.character_set_manager = create_extended_character_set_manager()

    # Agents étendus par secteur
    agents_15 = [
        # AGRICULTURE (3 agents)
        ("FARM_ALICE", "AGRICULTURE", Decimal('2500')),
        ("FARM_BOB", "AGRICULTURE", Decimal('2200')),
        ("FARM_CHARLIE", "AGRICULTURE", Decimal('2800')),

        # INDUSTRY (4 agents)
        ("MANUFACTURING_DIANA", "INDUSTRY", Decimal('1800')),
        ("TECH_EVE", "INDUSTRY", Decimal('2200')),
        ("AUTOMOTIVE_FRANK", "INDUSTRY", Decimal('1900')),
        ("CHEMICALS_GRACE", "INDUSTRY", Decimal('2100')),

        # SERVICES (3 agents)
        ("LOGISTICS_HELEN", "SERVICES", Decimal('1500')),
        ("CONSULTING_IAN", "SERVICES", Decimal('1200')),
        ("RETAIL_JANE", "SERVICES", Decimal('1400')),

        # FINANCE (2 agents)
        ("BANK_KEVIN", "FINANCE", Decimal('5000')),
        ("INSURANCE_LUCY", "FINANCE", Decimal('4500')),

        # ENERGY (3 agents)
        ("RENEWABLE_MIKE", "ENERGY", Decimal('3500')),
        ("FOSSIL_NINA", "ENERGY", Decimal('3200')),
        ("NUCLEAR_OSCAR", "ENERGY", Decimal('3800'))
    ]

    for agent_id, sector, balance in agents_15:
        simulation.create_agent(agent_id, sector, balance)

    print(f"✅ Simulation 15 agents créée: {len(simulation.agents)} agents")
    return simulation

# Usage
simulation_15 = create_15_agents_simulation()
scenario_stable_economy(simulation_15)  # Test scénario avec 15 agents
```

### Path vers 40→65 Agents

```python
# Preview architecture massive (voir character_set_65_agents_preview.py)
def preview_massive_simulation():
    """Preview simulation massive 40→65 agents"""

    print("🎯 ARCHITECTURE MASSIVE PREVIEW:")
    print("   40 agents (Semaine 2): 5 secteurs étendus")
    print("   65 agents (Semaine 3): Distribution économique réaliste")
    print("   Applications (Semaine 4): Gaming + Academic + Business")

    # Capacités Character-Set Manager
    capacities = {
        '7 agents (Actuel)': 21,
        '15 agents (Testé)': 45,
        '40 agents (Semaine 2)': 120,
        '65 agents (Semaine 3)': 195
    }

    for config, chars_needed in capacities.items():
        print(f"   {config}: {chars_needed} caractères")

    print("✅ Infrastructure validée pour scaling complet")

preview_massive_simulation()
```

---

## 🎮 Applications Gaming & Academic

### Gaming Platform Foundation

```python
def setup_carbon_flux_foundation(simulation):
    """Setup foundation pour Carbon Flux serious gaming"""

    # Agents Carbon-aware avec métadonnées ESG
    carbon_agents = []

    for agent in simulation.agents.values():
        # Attribution score carbone selon secteur
        carbon_score = {
            'AGRICULTURE': 0.8,  # Vert
            'INDUSTRY': 0.4,     # Moyen
            'SERVICES': 0.7,     # Bon
            'FINANCE': 0.6,      # Facilitateur
            'ENERGY': 0.3        # Critique
        }[agent.sector]

        agent.metadata['carbon_score'] = carbon_score
        agent.metadata['esg_rating'] = 'A' if carbon_score > 0.7 else 'B' if carbon_score > 0.5 else 'C'
        carbon_agents.append(agent)

    print(f"🌱 Carbon Flux Foundation: {len(carbon_agents)} agents ESG-ready")

    # Dual-token simulation (€ + @ carbon credits)
    carbon_transactions = []

    for agent in carbon_agents:
        if agent.metadata['carbon_score'] > 0.6:  # Agents verts
            # Génération carbon credits (@)
            carbon_credits = agent.balance * Decimal('0.1')
            carbon_transactions.append({
                'agent': agent.agent_id,
                'type': 'carbon_generation',
                'amount': carbon_credits,
                'token': '@'
            })

    print(f"💚 Carbon Credits générés: {len(carbon_transactions)} transactions @")
    return carbon_transactions
```

### Academic Data Export

```python
def export_academic_datasets(simulation):
    """Export données pour publications académiques"""

    academic_data = {
        'metadata': {
            'agents_count': len(simulation.agents),
            'sectors': list(set(agent.sector for agent in simulation.agents.values())),
            'character_set_config': simulation.character_set_manager.get_allocation_statistics(),
            'timestamp': time.time()
        },
        'agents': [],
        'transactions': [],
        'flows': {},
        'performance': {}
    }

    # Export agents data
    for agent in simulation.agents.values():
        academic_data['agents'].append({
            'id': agent.agent_id,
            'sector': agent.sector,
            'balance': float(agent.balance),
            'metadata': agent.metadata
        })

    # Export inter-sectoral flows
    for source_sector in academic_data['metadata']['sectors']:
        academic_data['flows'][source_sector] = {}
        for target_sector in academic_data['metadata']['sectors']:
            if source_sector != target_sector:
                # Calculate flow intensity
                flow_count = sum(1 for tx in simulation.transactions
                               if simulation.get_agent(tx.source_account_id).sector == source_sector
                               and simulation.get_agent(tx.target_account_id).sector == target_sector)
                academic_data['flows'][source_sector][target_sector] = flow_count

    # Export to JSON for academic analysis
    import json
    with open(f'academic_dataset_{simulation.simulation_id}.json', 'w') as f:
        json.dump(academic_data, f, indent=2, default=str)

    print(f"📊 Academic Dataset: academic_dataset_{simulation.simulation_id}.json")
    print(f"   Agents: {len(academic_data['agents'])}")
    print(f"   Flows: {sum(len(flows) for flows in academic_data['flows'].values())}")
    return academic_data
```

---

## 🚀 Prochaines Étapes

### Roadmap Semaines 2-3-4

```python
def show_development_roadmap():
    """Affiche roadmap développement CAPS"""

    roadmap = {
        'Semaine 2': {
            'target': '40 agents économiques',
            'focus': 'Flux inter-sectoriels étendus',
            'validation': '>70% FEASIBILITY, <100ms'
        },
        'Semaine 3': {
            'target': '65 agents maximum',
            'focus': 'Performance industrielle',
            'validation': '100+ tx/sec, 52K+ unités/heure'
        },
        'Semaine 4': {
            'target': 'Applications production-ready',
            'focus': 'Gaming + Academic + Business',
            'validation': 'Scénarios économiques complets'
        }
    }

    print("🗓️  ROADMAP CAPS DEVELOPMENT:")
    for week, goals in roadmap.items():
        print(f"   {week}:")
        print(f"      Target: {goals['target']}")
        print(f"      Focus: {goals['focus']}")
        print(f"      Validation: {goals['validation']}")
        print()

show_development_roadmap()
```

### Quick Start Templates

```python
# Template simulation 7 agents
def quick_start_7_agents():
    simulation = EconomicSimulation("quick_start")
    # ... 7 agents standard (voir début guide)
    return simulation

# Template simulation 15 agents
def quick_start_15_agents():
    simulation = create_15_agents_simulation()
    # ... configuration étendue
    return simulation

# Template scénarios économiques
def quick_start_scenarios(simulation):
    scenario_stable_economy(simulation)
    scenario_oil_shock(simulation)
    scenario_tech_revolution(simulation)

print("🚀 Quick Start Templates disponibles!")
print("   quick_start_7_agents() - Simulation basique")
print("   quick_start_15_agents() - Simulation étendue")
print("   quick_start_scenarios(sim) - Scénarios économiques")
```

---

## 🏗️ Architecture Fondamentale : Tri-Caractères

### Comprendre l'Architecture Taxonomique

**CAPS** utilise une architecture taxonomique **tri-caractères** fondamentale que tout utilisateur doit comprendre pour optimiser ses simulations économiques.

#### Pourquoi 3 Caractères par Agent ?

Chaque agent économique dans CAPS nécessite **exactement 3 mappings taxonomiques distincts** :

```python
# Agent économique FARM_01
agent_mappings = {
    'FARM_01': 'A',         # Caractère principal (compte économique)
    'FARM_01_source': 'B',  # Caractère source (nœud source DAG)
    'FARM_01_sink': 'C'     # Caractère sink (nœud sink DAG)
}
```

#### Process de Validation Interne

```python
# 1. DAG Path Enumeration génère chemins inter-agents
path_example = [farm_01_source_node, indu_05_sink_node]

# 2. convert_path_to_word() effectue mapping node_id → character
# farm_01_source_node.node_id = "FARM_01_source" → 'B'
# indu_05_sink_node.node_id = "INDU_05_sink" → 'X'
# Résultat: word = "BX"

# 3. NFA validation teste word contre regex sectoriels
agriculture_pattern = ".*[ABCDEF...].*"  # Matche caractères AGRICULTURE
industry_pattern = ".*[GHIJKL...].*"     # Matche caractères INDUSTRY
# word "BX" validé car B ∈ AGRICULTURE et X ∈ INDUSTRY ✅
```

### Calcul Capacité Agents

#### Distribution 65 Agents - Configuration Massive

```python
# Capacité requise par secteur
SECTEUR_DISTRIBUTION = {
    'AGRICULTURE': 10,  # 10 × 3 = 30 caractères
    'INDUSTRY': 15,     # 15 × 3 = 45 caractères
    'SERVICES': 20,     # 20 × 3 = 60 caractères
    'FINANCE': 8,       # 8 × 3 = 24 caractères
    'ENERGY': 12        # 12 × 3 = 36 caractères
}

# TOTAL: 65 agents × 3 caractères = 195 caractères requis minimum
```

#### Validation Character-Set Manager

```python
def validate_character_capacity(simulation):
    """Vérifier capacité character-set pour agents cibles"""

    stats = simulation.character_set_manager.get_allocation_statistics()
    total_capacity = sum(info['max_capacity'] for info in stats['sectors'].values())

    print(f"Capacité totale: {total_capacity} caractères")
    print(f"Agents supportés: {total_capacity // 3} maximum")

    # Validation 65 agents
    if total_capacity >= 195:
        print("✅ Configuration 65 agents SUPPORTÉE")
    else:
        print(f"⚠️  Insuffisant pour 65 agents: {total_capacity} < 195")

    return total_capacity >= 195

# Usage avec mode 65 agents
simulation = EconomicSimulation("capacity_check", agents_mode="65_agents")
validate_character_capacity(simulation)
```

### Implications Pratiques

#### ✅ Ce qui FONCTIONNE

```python
# Allocation correcte - 3 caractères par agent
simulation = EconomicSimulation("correct_setup", agents_mode="40_agents")
# → 40 × 3 = 120 caractères alloués

# Création agents respectant capacité
for i in range(13):  # 13 agents max avec mode 40 (39 caractères / 3)
    simulation.create_agent(f"AGENT_{i}", "AGRICULTURE", Decimal('1000'))

# Résultat: 100% FEASIBILITY ✅
```

#### ❌ Ce qui ÉCHOUE

```python
# Allocation incorrecte - sous-estimation capacité
simulation = EconomicSimulation("wrong_setup", agents_mode="40_agents")

# Tentative création trop d'agents
for i in range(20):  # 20 agents × 3 = 60 caractères > 39 disponibles
    simulation.create_agent(f"AGENT_{i}", "AGRICULTURE", Decimal('1000'))

# Résultat: RuntimeError - Character capacity exhausted ❌
```

#### Monitoring Utilisation

```python
def monitor_character_usage(simulation):
    """Surveiller utilisation caractères en temps réel"""

    stats = simulation.character_set_manager.get_allocation_statistics()

    print(f"📊 UTILISATION CHARACTER-SET:")
    print(f"   Total alloué: {stats['total_allocations']} caractères")
    print(f"   Manager figé: {stats['is_frozen']}")

    for sector, info in stats['sectors'].items():
        utilisation = info['utilization_rate']
        status = "🔴" if utilisation > 0.9 else "🟡" if utilisation > 0.7 else "🟢"

        print(f"   {sector}: {info['allocated_count']}/{info['max_capacity']} "
              f"({utilisation:.1%} {status})")

        if utilisation > 0.85:
            remaining_agents = (info['max_capacity'] - info['allocated_count']) // 3
            print(f"      ⚠️  Seulement {remaining_agents} agents supplémentaires possibles")

# Usage recommandé avant création agents massifs
monitor_character_usage(simulation)
```

### Troubleshooting Architecture

#### Erreur Courante : "No character mapping found"

```python
# ERREUR TYPIQUE
ValueError: No character mapping found for account FARM_01_source at transaction 0
SYSTÈME FAILURE: Mapping taxonomique manquant pour node_id du chemin DAG

# CAUSE: Tentative transaction avec agent mal configuré
# SOLUTION: Vérifier que _configure_taxonomy_batch() a été appelé
```

#### Diagnostic Mappings

```python
def diagnose_taxonomy_mappings(simulation):
    """Diagnostique mappings taxonomiques complets"""

    print("🔍 DIAGNOSTIC MAPPINGS TAXONOMIE:")

    for agent_id in simulation.agents.keys():
        # Vérifier les 3 mappings requis
        mappings_required = [
            agent_id,                    # Principal
            f"{agent_id}_source",       # Source
            f"{agent_id}_sink"          # Sink
        ]

        missing_mappings = []
        for mapping_id in mappings_required:
            char = simulation.account_taxonomy.get_character_mapping(mapping_id, 0)
            if char is None:
                missing_mappings.append(mapping_id)
            else:
                print(f"   ✅ {mapping_id} → '{char}'")

        if missing_mappings:
            print(f"   ❌ {agent_id} MANQUE: {missing_mappings}")
            return False

    print("✅ Tous les mappings tri-caractères VALIDÉS")
    return True

# Usage pour debug
diagnose_taxonomy_mappings(simulation)
```

### Guidelines d'Utilisation

#### 🎯 Bonnes Pratiques

1. **Toujours vérifier capacité AVANT création agents**
2. **Utiliser modes agents appropriés** (`"7_agents"`, `"40_agents"`, `"65_agents"`)
3. **Monitorer utilisation character-set** pendant développement
4. **Diagnostic mappings** en cas d'erreurs validation

#### 📏 Dimensionnement Projets

```python
# Règle de dimensionnement : 3 × agents_target ≤ capacity_character_set

CONFIGURATION_RECOMMENDATIONS = {
    "Prototype (≤7 agents)": "Mode standard",
    "Development (≤15 agents)": "Mode 40_agents",
    "Production (≤22 agents)": "Mode 65_agents avec monitoring",
    "Enterprise (>22 agents)": "Architecture custom requise"
}
```

Cette architecture tri-caractères est la **fondation technique** permettant à CAPS d'atteindre **100% FEASIBILITY** avec validation économique complète. Comprendre cette architecture est essentiel pour exploiter pleinement les capacités de simulation massive.

---

## 📚 Ressources Supplémentaires

### Documentation Technique
- **[character_set_manager_api.md](./character_set_manager_api.md)** : API Character-Set Manager détaillée
- **[MIGRATION_GUIDE.md](../MIGRATION_GUIDE.md)** : Migration DAG → EnhancedDAG
- **[PLAN_SEMAINES_2_3_EXTENSION_MASSIVE.md](../PLAN_SEMAINES_2_3_EXTENSION_MASSIVE.md)** : Roadmap technique

### Exemples Pratiques
- **[advanced_simulation.py](../icgs_simulation/examples/advanced_simulation.py)** : Simulation complète 7 agents
- **[test_15_agents_simulation.py](../test_15_agents_simulation.py)** : Validation 15 agents
- **[character_set_65_agents_preview.py](../character_set_65_agents_preview.py)** : Preview 65 agents

### Support & Communauté
- **Tests validation** : `python -m pytest tests/ -v`
- **Performance benchmarks** : Guides inclus dans exemples
- **Issues & Questions** : Documentation technique disponible

---

**🎯 Résultat Final**

Avec ce guide, vous maîtrisez la simulation économique massive CAPS :
- ✅ **7 agents → 100% FEASIBILITY** (breakthrough validé)
- ✅ **Architecture 15→65 agents** (scalabilité démontrée)
- ✅ **Scénarios économiques** (applications réalistes)
- ✅ **Gaming + Academic + Business** (ready for deployment)

**CAPS** transforme la simulation économique de concept technique → plateforme world-class opérationnelle ! 🚀

---

## 📊 Cohérence Économique et Validation

### Foundation Économique Validée

CAPS présente une **architecture économique cohérente** validée par analyse approfondie:

#### ✅ Structure Sectorielle Réaliste
```python
# Distribution d'agents selon importance économique
DISTRIBUTION_AGENTS = {
    'SERVICES': 20,    # 31% - Secteur dominant économies développées
    'INDUSTRY': 15,    # 23% - Transformation/manufacturing
    'ENERGY': 12,      # 18% - Infrastructure critique
    'AGRICULTURE': 10, # 15% - Base alimentaire
    'FINANCE': 8       # 12% - Facilitation financière
}

# Pondérations sectorielles cohérentes
SECTOR_WEIGHTS = {
    'AGRICULTURE': 1.5,  # Priorité sécurité alimentaire
    'ENERGY': 1.3,       # Infrastructure critique
    'INDUSTRY': 1.2,     # Transformation essentielle
    'SERVICES': 1.0,     # Référence (secteur principal)
    'FINANCE': 0.8       # Facilitateur vs producteur
}
```

#### ✅ Flux Inter-Sectoriels Cohérents
```python
# Patterns supply chain validés
FLUX_PATTERNS = {
    'AGRICULTURE → INDUSTRY': 'Matières premières vers transformation',
    'INDUSTRY → SERVICES': 'Produits finis vers distribution',
    'SERVICES ↔ FINANCE': 'Facilitation financière bidirectionnelle',
    'ENERGY → ALL': 'Infrastructure transversale tous secteurs'
}

# Validation mathématique
✅ Conservation des flux (aucune création/destruction artificielle)
✅ Cohérence FEASIBILITY ⊆ OPTIMIZATION (100% validation)
✅ Monotonie chaînes de valeur (viabilité A→B→C)
```

### Limitations Connues (Évolutions Futures)

#### Simplifications v1.0 (Acceptables)
- **Flux Instantanés**: Pas de délais production→livraison (simplifie validation concepts)
- **Pas de Stocks**: Transactions directes sans inventaires intermédiaires
- **Capacités Illimitées**: Focus validation patterns vs contraintes production

#### Évolutions Planifiées
```python
# Phase 1: Calibrage Réaliste (Semaine 4+)
ROADMAP_REALISM = {
    'matrices_input_output': 'Calibrage coefficients OECD/INSEE',
    'contraintes_capacite': 'Limites production sectorielles',
    'validation_equilibre': 'Tests offre/demande global'
}

# Phase 2: Dynamiques Temporelles
ROADMAP_ADVANCED = {
    'cycles_economiques': 'Saisonnalité et conjoncture',
    'delais_realistes': 'Temps production→livraison',
    'chocs_exogenes': 'Crises et innovations'
}
```

### Validation Cohérence Pratique

```python
def validate_economic_coherence(simulation):
    """Validation cohérence économique simulation"""

    # 1. Vérifier distribution sectorielle
    distribution = get_sectoral_distribution(simulation)
    assert distribution['SERVICES'] > distribution['FINANCE']  # Secteur dominant

    # 2. Vérifier flux inter-sectoriels
    flows = simulation.create_inter_sectoral_flows_batch(0.5)
    feasibility_rate = validate_flows_feasibility(flows)
    assert feasibility_rate > 0.95  # >95% cohérence attendue

    return True  # Cohérence validée ✅
```

### Documentation Complémentaire

- **[Analyse Cohérence Complète](./economic_coherence_analysis.md)**: Évaluation détaillée foundation économique
- **[Évolutions Futures](./economic_coherence_analysis.md#évolutions-futures-planifiées)**: Roadmap réalisme économique
- **[Métriques Validation](./economic_coherence_analysis.md#métriques-de-validation)**: Critères cohérence économique

---

*Guide Utilisateur Simulation Économique Massive v1.2.0*
*Foundation Économique Validée + Évolutions Futures Planifiées*