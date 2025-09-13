#!/usr/bin/env python3
"""
Mini-Simulation ICGS - Demo Fonctionnelle

Démonstration complète du framework icgs_simulation avec:
- Création agents économiques multi-secteurs
- Transactions inter-sectorielles
- Validation FEASIBILITY vs OPTIMIZATION
- Price Discovery avec comparaisons

Basé sur blueprint ICGS Phase 5 - Architecture découplée.
"""

import sys
import os
from decimal import Decimal

# Ajouter icgs_simulation au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_simulation import EconomicSimulation, SECTORS


def run_mini_simulation():
    """Exécute mini-simulation complète avec Price Discovery"""

    print("=" * 60)
    print("🚀 MINI-SIMULATION ICGS - DEMO PRICE DISCOVERY")
    print("=" * 60)
    print()

    # 1. Initialiser simulation
    print("1️⃣ Initialisation simulation...")
    sim = EconomicSimulation("mini_demo_001")
    print(f"   ✅ Simulation '{sim.simulation_id}' créée")
    print()

    # 2. Créer agents économiques
    print("2️⃣ Création agents économiques...")

    alice = sim.create_agent("ALICE", "AGRICULTURE", Decimal('1500'),
                           {"name": "Alice Farm", "region": "Nord"})
    print(f"   ✅ Alice (Agriculture): balance {alice.get_balance()}")

    bob = sim.create_agent("BOB", "INDUSTRY", Decimal('800'),
                         {"name": "Bob Industries", "sector_type": "manufacturing"})
    print(f"   ✅ Bob (Industry): balance {bob.get_balance()}")

    carol = sim.create_agent("CAROL", "SERVICES", Decimal('600'),
                           {"name": "Carol Services", "service_type": "logistics"})
    print(f"   ✅ Carol (Services): balance {carol.get_balance()}")
    print()

    # 3. Afficher secteurs disponibles
    print("3️⃣ Secteurs économiques configurés:")
    for sector_name, sector_info in SECTORS.items():
        print(f"   {sector_name}: {sector_info.pattern} (poids {sector_info.weight})")
    print()

    # 4. Créer transactions économiques
    print("4️⃣ Création transactions économiques...")

    # Transaction 1: Alice → Bob (Agriculture → Industry)
    tx1 = sim.create_transaction("ALICE", "BOB", Decimal('120'),
                               {"type": "matières_premières", "urgence": "normale"})
    print(f"   ✅ {tx1}: ALICE → BOB (120 unités)")

    # Transaction 2: Bob → Carol (Industry → Services)
    tx2 = sim.create_transaction("BOB", "CAROL", Decimal('85'),
                               {"type": "produits_finis", "urgence": "élevée"})
    print(f"   ✅ {tx2}: BOB → CAROL (85 unités)")
    print()

    # 5. Tests validation FEASIBILITY
    print("5️⃣ Validation mode FEASIBILITY...")
    from icgs_simulation.api.icgs_bridge import SimulationMode

    result1_feas = sim.validate_transaction(tx1, SimulationMode.FEASIBILITY)
    print(f"   {tx1}: {'✅ FAISABLE' if result1_feas.success else '❌ INFAISABLE'} "
          f"({result1_feas.validation_time_ms:.2f}ms)")

    result2_feas = sim.validate_transaction(tx2, SimulationMode.FEASIBILITY)
    print(f"   {tx2}: {'✅ FAISABLE' if result2_feas.success else '❌ INFAISABLE'} "
          f"({result2_feas.validation_time_ms:.2f}ms)")
    print()

    # 6. Tests Price Discovery OPTIMIZATION
    print("6️⃣ Price Discovery mode OPTIMIZATION...")

    result1_opt = sim.validate_transaction(tx1, SimulationMode.OPTIMIZATION)
    if result1_opt.success:
        print(f"   {tx1}: ✅ OPTIMAL - Prix découvert: {result1_opt.optimal_price}")
        print(f"        Status: {result1_opt.status}, Temps: {result1_opt.validation_time_ms:.2f}ms")
    else:
        print(f"   {tx1}: ❌ ÉCHEC - {result1_opt.error_message}")

    result2_opt = sim.validate_transaction(tx2, SimulationMode.OPTIMIZATION)
    if result2_opt.success:
        print(f"   {tx2}: ✅ OPTIMAL - Prix découvert: {result2_opt.optimal_price}")
        print(f"        Status: {result2_opt.status}, Temps: {result2_opt.validation_time_ms:.2f}ms")
    else:
        print(f"   {tx2}: ❌ ÉCHEC - {result2_opt.error_message}")
    print()

    # 7. Comparaison FEASIBILITY vs OPTIMIZATION
    print("7️⃣ Comparaison modes validation...")
    print("   ┌─────────────┬─────────────┬─────────────┬─────────────┐")
    print("   │ Transaction │ FEASIBILITY │ OPTIMIZATION│ Prix Optimal│")
    print("   ├─────────────┼─────────────┼─────────────┼─────────────┤")

    for tx, res_feas, res_opt in [(tx1, result1_feas, result1_opt),
                                  (tx2, result2_feas, result2_opt)]:
        feas_status = "✅ OK" if res_feas.success else "❌ KO"
        opt_status = "✅ OK" if res_opt.success else "❌ KO"
        price = f"{res_opt.optimal_price}" if res_opt.optimal_price else "N/A"

        print(f"   │ {tx[-7:]:>11} │ {feas_status:>11} │ {opt_status:>11} │ {price:>11} │")

    print("   └─────────────┴─────────────┴─────────────┴─────────────┘")
    print()

    # 8. Statistiques simulation
    print("8️⃣ Statistiques simulation...")
    stats = sim.get_simulation_stats()
    print(f"   Agents: {stats['agents_count']}")
    print(f"   Transactions: {stats['transactions_count']}")
    print(f"   Secteurs représentés: {', '.join(stats['sectors_represented'])}")
    print(f"   Stats DAG: {stats['dag_stats']}")
    print()

    # 9. Conclusion
    print("9️⃣ Résultats simulation...")

    if result1_feas.success and result2_feas.success:
        print("   ✅ Validation FEASIBILITY: Toutes transactions faisables")
    else:
        print("   ❌ Validation FEASIBILITY: Problèmes détectés")

    if result1_opt.success and result2_opt.success:
        print("   ✅ Price Discovery: Optimisation réussie")
        print(f"   💰 Prix découverts: TX1={result1_opt.optimal_price}, TX2={result2_opt.optimal_price}")
    else:
        print("   ⚠️ Price Discovery: Certaines optimisations échouées")

    print()
    print("✅ MINI-SIMULATION COMPLÉTÉE")
    print("🎯 Framework icgs_simulation fonctionnel")
    print("🚀 Prêt pour simulations économiques complexes")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_mini_simulation()
    except Exception as e:
        print(f"❌ ERREUR SIMULATION: {e}")
        import traceback
        traceback.print_exc()