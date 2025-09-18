#!/usr/bin/env python3
"""
Test Simulation 15+ Agents Économiques
Validation scalabilité pour Semaine 2-3 du plan

Démonstration que l'infrastructure Character-Set Manager + EnhancedDAG
peut gérer 15+ agents avec patterns sectoriels économiques.
"""

import sys
import os
sys.path.insert(0, '/home/norkamer/ClaudeCode/CAPS')

from icgs_simulation.api.icgs_bridge import EconomicSimulation, SimulationMode
from decimal import Decimal


def main():
    print("🎯 SIMULATION 15+ AGENTS ÉCONOMIQUES")
    print("Validation scalabilité Character-Set Manager + EnhancedDAG")
    print("=" * 60)

    # Simulation avec Character-Set Manager étendu (utilisation API bridge)
    # Utilise mode "40_agents" qui a suffisamment de capacité pour 15 agents
    simulation = EconomicSimulation("scalability_test_15_agents", agents_mode="40_agents")

    # Création 15 agents répartis sur 5 secteurs
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

    print(f"🏭 CRÉATION 15 AGENTS ÉCONOMIQUES...")
    agents_created = 0

    for agent_id, sector, balance in agents_15:
        try:
            agent = simulation.create_agent(agent_id, sector, balance)
            agents_created += 1
            print(f"   ✅ {agents_created:2d}/15: {agent_id} ({sector})")
        except Exception as e:
            print(f"   ❌ ÉCHEC {agent_id}: {e}")
            break

    print(f"\n📊 AGENTS CRÉÉS: {agents_created}/15")

    # Statistiques Character-Set Manager
    stats = simulation.character_set_manager.get_allocation_statistics()
    print(f"\n📈 CHARACTER-SET ALLOCATION:")
    print(f"   Total allocations: {stats['total_allocations']}")

    for sector, info in stats['sectors'].items():
        print(f"   {sector}: {info['allocated_count']}/{info['max_capacity']} "
              f"({info['utilization_rate']:.1%})")

    # Test configuration taxonomie
    print(f"\n🔧 TEST CONFIGURATION TAXONOMIE...")
    try:
        simulation._configure_taxonomy_batch()
        print(f"   ✅ Configuration réussie")

        # Stats après configuration
        stats = simulation.character_set_manager.get_allocation_statistics()
        print(f"   Character-Set figé: {stats['is_frozen']}")
        print(f"   Total caractères utilisés: {stats['total_allocations']}")

    except Exception as e:
        print(f"   ❌ Configuration échouée: {e}")
        return

    # Création transactions test (échantillon)
    print(f"\n⚡ CRÉATION TRANSACTIONS TEST...")
    test_transactions = [
        ("FARM_ALICE", "MANUFACTURING_DIANA", Decimal('300'), "Agri→Industry"),
        ("TECH_EVE", "CONSULTING_IAN", Decimal('250'), "Industry→Services"),
        ("LOGISTICS_HELEN", "BANK_KEVIN", Decimal('180'), "Services→Finance"),
        ("RENEWABLE_MIKE", "AUTOMOTIVE_FRANK", Decimal('120'), "Energy→Industry")
    ]

    transaction_ids = []
    for source, target, amount, desc in test_transactions:
        if source in simulation.agents and target in simulation.agents:
            tx_id = simulation.create_transaction(source, target, amount)
            transaction_ids.append((tx_id, desc))
            print(f"   ✅ {desc}: {tx_id}")

    # Validation FEASIBILITY
    print(f"\n🔍 VALIDATION FEASIBILITY...")
    feasible_count = 0

    for tx_id, desc in transaction_ids:
        result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
        status = "✅ FAISABLE" if result.success else "❌ INFAISABLE"
        print(f"   {desc}: {status} ({result.validation_time_ms:.2f}ms)")
        if result.success:
            feasible_count += 1

    feasibility_rate = (feasible_count / len(transaction_ids)) * 100 if transaction_ids else 0
    print(f"\n📊 TAUX FEASIBILITY: {feasible_count}/{len(transaction_ids)} ({feasibility_rate:.1f}%)")

    # Évaluation finale
    print(f"\n🎯 ÉVALUATION SCALABILITÉ 15+ AGENTS:")
    if agents_created >= 15 and feasibility_rate >= 70:
        print(f"   🎉 EXCELLENT: {agents_created} agents, {feasibility_rate:.1f}% FEASIBILITY")
        print(f"   🚀 PRÊT POUR SEMAINE 2-3: Extension vers 40+ agents")
    elif agents_created >= 10:
        print(f"   ✅ BON: {agents_created} agents, infrastructure scalable validée")
    else:
        print(f"   ⚠️  LIMITÉ: {agents_created} agents, optimisations nécessaires")

    print(f"\n" + "=" * 60)
    print(f"✅ TEST SCALABILITÉ 15+ AGENTS TERMINÉ")

if __name__ == "__main__":
    main()