#!/usr/bin/env python3
"""
Debug script pour reproduire le TypeError float * Decimal
dans le pipeline de transaction creation CAPS.

Bug critique identifié:
TypeError: unsupported operand type(s) for *: 'float' and 'decimal.Decimal'

Objectif: Identifier l'emplacement exact et le flow de types problématique.
"""

import sys
import os
from decimal import Decimal
import traceback

# Add CAPS to path
sys.path.insert(0, '/home/norkamer/ClaudeCode/CAPS')

try:
    from icgs_simulation.api.icgs_bridge import EconomicSimulation, SimulationMode

    def reproduce_type_error():
        """Reproduit le TypeError avec configuration minimale"""
        print("🔍 Reproduction TypeError float * Decimal")
        print("=" * 50)

        try:
            # Configuration comme test_extended_scalability.py (avec float!)
            simulation = EconomicSimulation("debug_test", agents_mode="7_agents")

            print("✅ 1. EconomicSimulation créée")

            # REPRODUIRE BUG: Utiliser float pour balance (comme test_extended_scalability.py)
            print("🚨 2. Création agents avec float balance (bug source suspectée)...")
            alice = simulation.create_agent("ALICE_FARM", "AGRICULTURE", 1000.0)  # FLOAT!
            bob = simulation.create_agent("BOB_FACTORY", "INDUSTRY", 800.0)       # FLOAT!

            print(f"✅ 2. Agents créés: {alice.agent_id}, {bob.agent_id}")
            print(f"   - Alice balance: {alice.balance} (type: {type(alice.balance)})")
            print(f"   - Bob balance: {bob.balance} (type: {type(bob.balance)})")

            # Créer transaction avec montant Decimal strict
            amount = Decimal('200')
            print(f"✅ 3. Montant transaction: {amount} (type: {type(amount)})")

            # ICI: Le bug se produit généralement dans create_transaction
            print("🚨 4. Tentative création transaction...")
            tx_id = simulation.create_transaction(
                source_agent_id="ALICE_FARM",
                target_agent_id="BOB_FACTORY",
                amount=amount
            )

            print(f"✅ 4. Transaction créée: {tx_id}")

            # Test batch flows (comme dans extended scalability)
            print("🚨 5. Tentative batch flows inter-sectoriels...")
            tx_ids = simulation.create_inter_sectoral_flows_batch(flow_intensity=0.2)
            print(f"✅ 5. Batch flows créés: {len(tx_ids)} transactions")

            # Validation des transactions
            print("🚨 6. Tentative validation transactions...")
            for tx_id in tx_ids[:3]:  # Test premiers seulement
                result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
                print(f"   - {tx_id}: {result.success}")

            print(f"✅ 6. Tests validations terminés")

        except Exception as e:
            print(f"❌ ERREUR DÉTECTÉE: {type(e).__name__}: {e}")
            print("\n📍 STACK TRACE COMPLÈTE:")
            traceback.print_exc()

            print("\n🔬 ANALYSE TYPES:")
            print("Variables disponibles au moment de l'erreur:")

            # Analyse du contexte au moment de l'erreur
            frame = traceback.extract_tb(e.__traceback__)[-1]
            print(f"   - Fichier: {frame.filename}")
            print(f"   - Ligne: {frame.lineno}")
            print(f"   - Code: {frame.line}")

            return e

    if __name__ == "__main__":
        error = reproduce_type_error()

        if error:
            print("\n🎯 DIAGNOSTIC FINAL:")
            print(f"   - Type d'erreur: {type(error).__name__}")
            print(f"   - Message: {error}")
            print("   - Source probable: Multiplication float × Decimal dans pipeline transaction")

except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("   - Vérifier que CAPS est dans le PYTHONPATH")
    print("   - Vérifier que les modules icgs_core sont présents")