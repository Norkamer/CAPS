#!/usr/bin/env python3
"""
Test diagnostique simple pour reproduction collision caractères taxonomiques
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from icgs_web_native import WebNativeICGS
from decimal import Decimal


def test_character_collision():
    """Test simple pour reproduire la collision de caractères"""

    print("=== TEST DIAGNOSTIC COLLISION TAXONOMIQUE ===")

    # Initialiser WebNativeICGS
    print("\n1. Initialisation WebNativeICGS...")
    try:
        manager = WebNativeICGS()
        print("✅ WebNativeICGS initialisé")

        # Vérifier pool virtuel
        capacities = manager.get_pool_capacities()
        print(f"✅ Capacités pool: {capacities}")

    except Exception as e:
        print(f"❌ Échec initialisation: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test création agents
    print("\n2. Test création agents...")
    try:
        # Créer 3 agents sur secteurs différents
        manager.add_agent("ALICE_FARM", "AGRICULTURE", Decimal('1000'))
        print("✅ Agent ALICE_FARM créé (AGRICULTURE)")

        manager.add_agent("BOB_INDUSTRY", "INDUSTRY", Decimal('1000'))
        print("✅ Agent BOB_INDUSTRY créé (INDUSTRY)")

        manager.add_agent("CAROL_SERVICES", "SERVICES", Decimal('1000'))
        print("✅ Agent CAROL_SERVICES créé (SERVICES)")

        # Afficher mappings
        print(f"Real→Virtual mappings: {manager.real_to_virtual}")

    except Exception as e:
        print(f"❌ Échec création agents: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test transaction (là où doit se produire la collision)
    print("\n3. Test transaction (point collision attendu)...")
    try:
        result = manager.process_transaction("ALICE_FARM", "BOB_INDUSTRY", Decimal('100'))
        print(f"Résultat transaction: {result}")

        if result['success']:
            print("✅ UNEXPECTED: Transaction réussie - collision non reproduite")
            return True
        else:
            print(f"❌ EXPECTED: Transaction échoue - {result.get('error', 'pas d-erreur')}")

            error_msg = result.get('error', '')
            if 'collision' in error_msg.lower() or 'character' in error_msg.lower():
                print("🎯 COLLISION DE CARACTÈRES CONFIRMÉE")
                return True
            else:
                print("❓ Échec pour autre raison (pas collision)")
                return False

    except Exception as e:
        print(f"❌ Exception lors transaction: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_character_collision()
    if success:
        print("\n✅ Test diagnostique terminé - problème identifié")
    else:
        print("\n❌ Test diagnostique échoué")

    sys.exit(0 if success else 1)