#!/usr/bin/env python3
"""
Preview Architecture Character-Set Manager pour 65 Agents
Configuration pour Semaine 3 - Simulation Massive Finale

Démontre la configuration nécessaire pour atteindre 65 agents économiques
avec distribution réaliste selon ANALYSE_SIMULATION_ECONOMIQUE_MASSIVE.md
"""

import sys
import os
sys.path.insert(0, '/home/norkamer/ClaudeCode/CAPS')

from icgs_core.character_set_manager import NamedCharacterSetManager

def create_massive_character_set_manager_65_agents():
    """
    Character-Set Manager pour simulation massive 65 agents

    Distribution économique réaliste :
    - AGRICULTURE: 10 agents (base alimentaire)
    - INDUSTRY: 15 agents (transformation, manufacturing)
    - SERVICES: 20 agents (logistics, consulting, retail)
    - FINANCE: 8 agents (banking, insurance)
    - ENERGY: 12 agents (renewable, fossil, nuclear)

    Total: 65 agents × 3 caractères = 195 caractères requis
    """
    manager = NamedCharacterSetManager()

    # AGRICULTURE (10 agents = 30 caractères)
    agriculture_chars = ['A', 'B', 'C', 'D'] + [f'G{i:01d}' for i in range(26)]
    print(f"AGRICULTURE: {len(agriculture_chars)} caractères pour 10 agents")
    manager.define_character_set('AGRICULTURE', agriculture_chars[:30])

    # INDUSTRY (15 agents = 45 caractères)
    industry_chars = ['I', 'J', 'K', 'L', 'M', 'N'] + [f'N{i:01d}' for i in range(39)]
    print(f"INDUSTRY: {len(industry_chars[:45])} caractères pour 15 agents")
    manager.define_character_set('INDUSTRY', industry_chars[:45])

    # SERVICES (20 agents = 60 caractères)
    services_chars = ['S', 'T', 'U', 'V', 'W'] + [f'V{i:01d}' for i in range(55)]
    print(f"SERVICES: {len(services_chars[:60])} caractères pour 20 agents")
    manager.define_character_set('SERVICES', services_chars[:60])

    # FINANCE (8 agents = 24 caractères)
    finance_chars = ['F', 'G', 'H'] + [f'F{i:01d}' for i in range(21)]
    print(f"FINANCE: {len(finance_chars[:24])} caractères pour 8 agents")
    manager.define_character_set('FINANCE', finance_chars[:24])

    # ENERGY (12 agents = 36 caractères)
    energy_chars = ['E', 'Q', 'R', 'Z'] + [f'E{i:01d}' for i in range(32)]
    print(f"ENERGY: {len(energy_chars[:36])} caractères pour 12 agents")
    manager.define_character_set('ENERGY', energy_chars[:36])

    return manager

def validate_massive_configuration():
    """Validation configuration massive 65 agents"""
    print("🎯 VALIDATION CONFIGURATION MASSIVE 65 AGENTS")
    print("=" * 60)

    manager = create_massive_character_set_manager_65_agents()

    # Statistiques configuration
    stats = manager.get_allocation_statistics()
    total_capacity = sum(info['max_capacity'] for info in stats['sectors'].values())

    print(f"\n📊 CAPACITÉ TOTALE:")
    print(f"   Total caractères disponibles: {total_capacity}")
    print(f"   Agents supportés (÷3): {total_capacity // 3}")
    print(f"   Target 65 agents: {'✅ SUFFISANT' if total_capacity >= 195 else '❌ INSUFFISANT'}")

    print(f"\n📈 DISTRIBUTION PAR SECTEUR:")
    target_agents = {'AGRICULTURE': 10, 'INDUSTRY': 15, 'SERVICES': 20, 'FINANCE': 8, 'ENERGY': 12}

    for sector, info in stats['sectors'].items():
        target = target_agents[sector]
        capacity_agents = info['max_capacity'] // 3
        status = "✅ OK" if capacity_agents >= target else "❌ INSUFFISANT"
        print(f"   {sector}: {capacity_agents} capacity vs {target} target {status}")

    # Test allocation simulée
    print(f"\n🧪 TEST ALLOCATION SIMULÉE:")
    allocated_total = 0

    for sector, target in target_agents.items():
        try:
            allocated_count = 0
            for i in range(target):
                char = manager.allocate_character_for_sector(sector)
                char2 = manager.allocate_character_for_sector(sector)
                char3 = manager.allocate_character_for_sector(sector)
                allocated_count += 1
                allocated_total += 1

            print(f"   {sector}: {allocated_count}/{target} agents alloués ✅")

        except Exception as e:
            print(f"   {sector}: ÉCHEC après {allocated_count} agents - {e}")
            break

    print(f"\n🎯 RÉSULTAT FINAL:")
    print(f"   Agents alloués: {allocated_total}/65")
    print(f"   Configuration: {'✅ VALIDÉE' if allocated_total == 65 else '⚠️ AJUSTEMENTS REQUIS'}")

    if allocated_total == 65:
        print(f"   🚀 PRÊT POUR SEMAINE 3: Simulation massive 65 agents")
    else:
        print(f"   🔧 AJUSTEMENTS REQUIS: Augmenter capacités secteurs")

    # Patterns regex générés
    print(f"\n🔍 PATTERNS REGEX SECTORIELS GÉNÉRÉS:")
    for sector in stats['sectors']:
        pattern = manager.get_regex_pattern_for_sector(sector)
        print(f"   {sector}: {pattern}")

def show_economic_distribution():
    """Affiche distribution économique réaliste"""
    print(f"\n💼 DISTRIBUTION ÉCONOMIQUE RÉALISTE 65 AGENTS:")
    print(f"=" * 60)

    sectors_info = {
        'AGRICULTURE': {'agents': 10, 'balance_avg': 1250, 'weight': 1.5, 'desc': 'Base alimentaire prioritaire'},
        'INDUSTRY': {'agents': 15, 'balance_avg': 900, 'weight': 1.2, 'desc': 'Transformation, manufacturing'},
        'SERVICES': {'agents': 20, 'balance_avg': 700, 'weight': 1.0, 'desc': 'Logistics, consulting, retail'},
        'FINANCE': {'agents': 8, 'balance_avg': 3000, 'weight': 0.8, 'desc': 'Banking, insurance facilitateur'},
        'ENERGY': {'agents': 12, 'balance_avg': 1900, 'weight': 1.3, 'desc': 'Infrastructure énergétique'}
    }

    total_agents = sum(info['agents'] for info in sectors_info.values())
    total_balance = sum(info['agents'] * info['balance_avg'] for info in sectors_info.values())

    for sector, info in sectors_info.items():
        percentage = (info['agents'] / total_agents) * 100
        print(f"   {sector:12s}: {info['agents']:2d} agents ({percentage:4.1f}%) - {info['desc']}")
        print(f"                 Balance moy: {info['balance_avg']} unités, Poids: {info['weight']}x")
        print()

    print(f"📊 TOTAUX:")
    print(f"   Agents total: {total_agents}")
    print(f"   Balance totale: {total_balance:,} unités")
    print(f"   Throughput estimé: {int(total_balance * 0.6)} unités/heure")

def main():
    """Validation complète architecture 65 agents"""
    validate_massive_configuration()
    show_economic_distribution()

    print(f"\n" + "=" * 60)
    print(f"✅ PREVIEW ARCHITECTURE 65 AGENTS TERMINÉ")
    print(f"🚀 Configuration prête pour implémentation Semaine 3")

if __name__ == "__main__":
    main()