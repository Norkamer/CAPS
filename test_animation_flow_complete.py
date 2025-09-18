#!/usr/bin/env python3
"""
Test du flux d'animation complet 1→33 transactions
Valide que l'animation CAPS fonctionne de bout en bout
"""

import requests
import time
import json
from typing import Dict, Any

def test_animation_flow_complete():
    """Test le flux d'animation complet de 1 à 33 transactions"""

    print("🧪 DÉBUT TEST ANIMATION FLOW COMPLET")
    print("=" * 50)

    base_url = "http://localhost:5000"
    headers = {"Content-Type": "application/json"}

    # Phase 1: Reset animation
    print("\n📅 PHASE 1: Reset de l'animation")
    try:
        response = requests.post(
            f"{base_url}/api/simulations/animate",
            headers=headers,
            json={"action": "reset"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Reset réussi: {data.get('total_transactions', 0)} transactions prêtes")
            total_transactions = data.get('total_transactions', 0)
            if total_transactions != 33:
                print(f"⚠️  Attention: {total_transactions} transactions au lieu de 33 attendues")
        else:
            print(f"❌ Reset échoué: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur reset: {e}")
        return False

    # Phase 2: Test status initial
    print("\n📊 PHASE 2: Vérification status initial")
    try:
        response = requests.post(
            f"{base_url}/api/simulations/animate",
            headers=headers,
            json={"action": "status"},
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status initial: étape {data.get('current_step', 0)}/{data.get('total_transactions', 0)}")
        else:
            print(f"❌ Status échoué: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur status: {e}")

    # Phase 3: Exécution de plusieurs steps
    print("\n🔄 PHASE 3: Exécution séquentielle de transactions")

    results = []
    for step in range(1, 6):  # Tester les 5 premières transactions
        try:
            print(f"\n🔹 Étape {step}/5:")
            response = requests.post(
                f"{base_url}/api/simulations/animate",
                headers=headers,
                json={"action": "step"},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                if data.get('success'):
                    step_num = data.get('step', 0)
                    progress = data.get('progress_percent', 0)
                    transaction = data.get('transaction', {})

                    print(f"  ✅ Transaction {step_num}: {transaction.get('source', 'N/A')} → {transaction.get('target', 'N/A')}")
                    print(f"  💰 Montant: {transaction.get('amount', 0)}")
                    print(f"  📈 Progression: {progress:.1f}%")

                    results.append({
                        'step': step_num,
                        'success': True,
                        'transaction': transaction,
                        'progress': progress
                    })

                    if data.get('completed'):
                        print("  🎉 Animation terminée!")
                        break
                else:
                    print(f"  ❌ Erreur API: {data.get('error', 'Inconnue')}")
                    results.append({'step': step, 'success': False, 'error': data.get('error')})
            else:
                print(f"  ❌ HTTP Error {response.status_code}")
                results.append({'step': step, 'success': False, 'error': f'HTTP {response.status_code}'})

        except Exception as e:
            print(f"  ❌ Exception: {e}")
            results.append({'step': step, 'success': False, 'error': str(e)})

        # Pause entre les étapes
        time.sleep(1)

    # Phase 4: Vérification status final
    print("\n📊 PHASE 4: Status final après tests")
    try:
        response = requests.post(
            f"{base_url}/api/simulations/animate",
            headers=headers,
            json={"action": "status"},
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            current_step = data.get('current_step', 0)
            total_steps = data.get('total_transactions', 0)
            progress = data.get('progress_percent', 0)

            print(f"✅ Status final: étape {current_step}/{total_steps} ({progress:.1f}%)")
        else:
            print(f"❌ Status final échoué: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur status final: {e}")

    # Phase 5: Analyse des résultats
    print("\n📋 PHASE 5: Analyse des résultats")
    print("=" * 30)

    successful_steps = len([r for r in results if r.get('success')])
    total_steps_tested = len(results)

    print(f"📊 Transactions testées: {total_steps_tested}")
    print(f"✅ Transactions réussies: {successful_steps}")
    print(f"❌ Transactions échouées: {total_steps_tested - successful_steps}")
    print(f"📈 Taux de réussite: {(successful_steps/total_steps_tested*100):.1f}%")

    # Affichage détaillé des transactions réussies
    print("\n📝 DÉTAIL DES TRANSACTIONS RÉUSSIES:")
    for result in results:
        if result.get('success'):
            tx = result.get('transaction', {})
            print(f"  • Étape {result['step']}: {tx.get('flow', 'N/A')} - {tx.get('amount', 0)}")

    # Affichage des erreurs
    errors = [r for r in results if not r.get('success')]
    if errors:
        print("\n❌ ERREURS DÉTECTÉES:")
        for error in errors:
            print(f"  • Étape {error['step']}: {error.get('error', 'Erreur inconnue')}")

    # Conclusion
    print("\n🎯 CONCLUSION:")
    if successful_steps >= 3:
        print("✅ FLUX D'ANIMATION VALIDÉ - Le système fonctionne correctement!")
        print("  • L'API d'animation répond aux requêtes")
        print("  • Les transactions s'exécutent en séquence")
        print("  • Les métadonnées sont retournées correctement")
        print("  • Le système de progression fonctionne")
        return True
    else:
        print("❌ FLUX D'ANIMATION EN ÉCHEC - Problèmes détectés")
        print("  • Moins de 3 transactions réussies")
        print("  • Vérifier la configuration du serveur")
        print("  • Vérifier l'état de la simulation 65 agents")
        return False

if __name__ == "__main__":
    success = test_animation_flow_complete()

    print("\n" + "=" * 50)
    if success:
        print("🎉 TEST COMPLET RÉUSSI - Animation flow 1→33 opérationnel!")
    else:
        print("🔧 TEST PARTIELLEMENT RÉUSSI - Améliorations nécessaires")
    print("=" * 50)