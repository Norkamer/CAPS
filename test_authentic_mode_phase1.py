#!/usr/bin/env python3
"""
Test Phase 1 - Mode Authentique ICGS 3D API
===========================================

Teste l'extraction des vraies variables f_i du Simplex
via l'API 3D intégrée au bridge ICGS.

Validation:
1. Bridge expose correctement le collecteur 3D
2. Collecteur capture états Simplex pendant validation
3. Variables f_i authentiques extraites
4. Coordonnées 3D calculées correctement
"""

import os
import sys
from decimal import Decimal

# Import ICGS modules
sys.path.insert(0, os.path.dirname(__file__))
from icgs_simulation import EconomicSimulation
from icgs_3d_space_analyzer import ICGS3DSpaceAnalyzer

def test_phase_1_authentic_mode():
    """Test complet Phase 1 - Mode Authentique"""

    print("🌌 Test Phase 1 - Mode Authentique ICGS 3D API")
    print("=" * 60)

    # 1. Initialiser simulation ICGS
    print("\n📊 1. Initialisation simulation ICGS...")
    simulation = EconomicSimulation()

    # 2. Créer analyzeur 3D
    print("🔍 2. Création analyseur 3D...")
    analyzer = ICGS3DSpaceAnalyzer(simulation)

    # 3. Vérifier disponibilité bridge collector
    print("🔗 3. Vérification bridge collector...")
    bridge = simulation  # EconomicSimulation IS the bridge

    if hasattr(bridge, 'get_3d_collector'):
        collector = bridge.get_3d_collector()
        if collector:
            print(f"   ✅ Bridge collector disponible: {type(collector).__name__}")
        else:
            print("   ❌ Bridge collector non initialisé")
            return False
    else:
        print("   ❌ Bridge ne supporte pas l'API 3D")
        return False

    # 4. Activer mode authentique
    print("⚡ 4. Activation mode authentique...")
    success = analyzer.enable_authentic_simplex_data(bridge)

    if not success:
        print("   ❌ Échec activation mode authentique")
        return False

    # 5. Créer agents test
    print("👥 5. Création agents test...")
    simulation.create_agent("ALICE_FARM", "AGRICULTURE", Decimal('1000'))
    simulation.create_agent("BOB_INDUSTRY", "INDUSTRY", Decimal('1000'))

    # 6. Test validation avec extraction f_i
    print("💰 6. Test transaction avec extraction variables f_i...")

    try:
        # Analyser transaction avec mode authentique
        point_3d = analyzer.analyze_transaction_3d_space(
            "ALICE_FARM",
            "BOB_INDUSTRY",
            Decimal('100')
        )

        print(f"   ✅ Point 3D calculé: ({point_3d.x:.4f}, {point_3d.y:.4f}, {point_3d.z:.4f})")
        print(f"   📊 Type pivot: {point_3d.pivot_type}")
        print(f"   ✅ Faisable: {point_3d.feasible}")
        print(f"   🎯 Optimal: {point_3d.optimal}")

        # Vérifier métadonnées authentiques
        metadata = point_3d.metadata
        if metadata.get('authentic_simplex_data'):
            print("   ✅ Données Simplex authentiques confirmées")

            variables_fi = metadata.get('variables_fi', {})
            print(f"   🔢 Variables f_i extraites: {len(variables_fi)} variables")

            if len(variables_fi) > 0:
                print("   📋 Échantillon variables f_i:")
                for i, (var_id, value) in enumerate(list(variables_fi.items())[:3]):
                    print(f"      {var_id}: {value:.6f}")
                if len(variables_fi) > 3:
                    print(f"      ... et {len(variables_fi) - 3} autres variables")

                print("   ✅ PHASE 1 SUCCÈS - Variables f_i authentiques extraites!")
                return True
            else:
                print("   ❌ Aucune variable f_i extraite")
                return False
        else:
            print("   ❌ Données non marquées comme authentiques")
            return False

    except Exception as e:
        print(f"   ❌ Erreur lors test authentique: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance_overhead():
    """Test overhead performance mode authentique"""

    print("\n⚡ Test Performance - Overhead Mode Authentique")
    print("-" * 50)

    simulation = EconomicSimulation()
    analyzer = ICGS3DSpaceAnalyzer(simulation)

    # Créer agents
    simulation.create_agent("ALICE_TEST", "AGRICULTURE", Decimal('1000'))
    simulation.create_agent("BOB_TEST", "INDUSTRY", Decimal('1000'))

    import time

    # Test mode approximation
    start = time.time()
    point_approx = analyzer.analyze_transaction_3d_space("ALICE_TEST", "BOB_TEST", Decimal('50'))
    time_approx = (time.time() - start) * 1000

    # Test mode authentique
    analyzer.enable_authentic_simplex_data(simulation)
    start = time.time()
    point_authentic = analyzer.analyze_transaction_3d_space("ALICE_TEST", "BOB_TEST", Decimal('75'))
    time_authentic = (time.time() - start) * 1000

    print(f"   Mode Approximation: {time_approx:.2f}ms")
    print(f"   Mode Authentique:   {time_authentic:.2f}ms")
    print(f"   Overhead:           {time_authentic - time_approx:.2f}ms ({((time_authentic - time_approx) / time_approx * 100):.1f}%)")

    return time_authentic - time_approx < 50  # Overhead < 50ms acceptable

if __name__ == '__main__':
    print("🚀 Démarrage tests Phase 1 - Mode Authentique")

    # Test principal
    phase1_success = test_phase_1_authentic_mode()

    # Test performance
    perf_success = test_performance_overhead()

    print("\n" + "=" * 60)
    print("📋 RÉSULTATS TESTS PHASE 1")
    print("=" * 60)
    print(f"Mode Authentique:     {'✅ SUCCÈS' if phase1_success else '❌ ÉCHEC'}")
    print(f"Performance:          {'✅ ACCEPTABLE' if perf_success else '❌ OVERHEAD ÉLEVÉ'}")

    if phase1_success and perf_success:
        print("🎉 PHASE 1 COMPLÈTE - Prêt pour Phase 2 (Animation Temps Réel)")
    else:
        print("⚠️  PHASE 1 INCOMPLÈTE - Résoudre problèmes avant Phase 2")

    print("\n🔗 Prochaines étapes Phase 2:")
    print("- Animation temps réel des pivots Simplex")
    print("- Interface 3D interactive Three.js")
    print("- Visualisation transitions algorithmiques")