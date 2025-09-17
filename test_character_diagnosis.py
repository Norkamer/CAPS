#!/usr/bin/env python3
"""
Test diagnostic Character-Set Manager
Comprendre exactement combien d'agents et caractères sont nécessaires
"""

import sys
import os
sys.path.insert(0, '/home/norkamer/ClaudeCode/CAPS')

from icgs_simulation.api.icgs_bridge import EconomicSimulation
from decimal import Decimal

def main():
    print("🔍 DIAGNOSTIC CHARACTER-SET MANAGER")
    print("=" * 50)

    # Créer simulation simple
    simulation = EconomicSimulation("diagnostic_test")

    print(f"📊 AVANT CRÉATION AGENTS:")
    stats = simulation.character_set_manager.get_allocation_statistics()
    print(f"   Secteurs disponibles: {list(stats['sectors'].keys())}")
    for sector, info in stats['sectors'].items():
        print(f"   {sector}: {info['allocated_count']}/{info['max_capacity']} (available: {info['available_characters']})")

    # Créer agents UN PAR UN avec monitoring
    agents_data = [
        ("ALICE_FARM", "AGRICULTURE"),
        ("BOB_MANUFACTURING", "INDUSTRY"),
        ("CHARLIE_TECH", "INDUSTRY"),
        ("DIANA_LOGISTICS", "SERVICES"),
        ("EVE_CONSULTING", "SERVICES"),
        ("FRANK_BANK", "FINANCE"),
        ("GRACE_ENERGY", "ENERGY")
    ]

    for i, (agent_id, sector) in enumerate(agents_data):
        print(f"\n🏭 CRÉATION AGENT {i+1}: {agent_id} ({sector})")

        try:
            agent = simulation.create_agent(agent_id, sector, Decimal('1000'))
            print(f"   ✅ Agent créé: {agent_id}")

            # Stats après création
            stats = simulation.character_set_manager.get_allocation_statistics()
            sector_info = stats['sectors'][sector]
            print(f"   {sector}: {sector_info['allocated_count']}/{sector_info['max_capacity']} utilisé")

        except Exception as e:
            print(f"   ❌ ÉCHEC: {e}")

            # Stats au moment de l'échec
            stats = simulation.character_set_manager.get_allocation_statistics()
            sector_info = stats['sectors'][sector]
            print(f"   {sector}: {sector_info['allocated_count']}/{sector_info['max_capacity']} (plein)")
            break

    print(f"\n📊 AGENTS CRÉÉS: {len(simulation.agents)}")
    for agent_id, agent in simulation.agents.items():
        print(f"   {agent_id} → {agent.sector}")

    print(f"\n🔧 TEST CONFIGURATION TAXONOMIE:")
    try:
        simulation._configure_taxonomy_batch()
        print("   ✅ Configuration réussie")
    except Exception as e:
        print(f"   ❌ Configuration échouée: {e}")

    # Stats finales
    print(f"\n📈 STATISTIQUES FINALES:")
    stats = simulation.character_set_manager.get_allocation_statistics()
    print(f"   Total allocations: {stats['total_allocations']}")
    print(f"   Frozen: {stats['is_frozen']}")

    for sector, info in stats['sectors'].items():
        print(f"   {sector}: {info['allocated_count']}/{info['max_capacity']} "
              f"({info['utilization_rate']:.1%} utilisé)")

if __name__ == "__main__":
    main()