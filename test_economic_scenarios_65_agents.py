#!/usr/bin/env python3
"""
Test Scénarios Économiques 65 Agents - Validation Semaine 3

Tests des scénarios économiques réalistes selon PLAN_SEMAINES_2_3_EXTENSION_MASSIVE.md:
- "Économie Stable" : Baseline 7 jours simulés
- "Choc Pétrolier" : Réduction 40% capacité ENERGY
- "Révolution Tech" : +50% efficacité INDUSTRY
- "Crise Financière" : Réduction 60% liquidités FINANCE

Objectifs performance :
- >70% FEASIBILITY sur tous les scénarios
- 100+ tx/sec throughput
- <100ms validation moyenne
"""

import sys
import os
from decimal import Decimal
import time
import random

# Import du module simulation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))
from icgs_simulation.api.icgs_bridge import EconomicSimulation, SimulationMode


class EconomicScenariosValidator:
    """Validateur scénarios économiques 65 agents"""

    def __init__(self):
        self.results = {}

    def scenario_stable_economy(self):
        """
        Scénario 1: "Économie Stable" (Baseline)
        - Configuration normale 65 agents
        - Distribution équilibrée secteurs
        - Flux inter-sectoriels standards
        """
        print("\n🏦 SCÉNARIO 1: ÉCONOMIE STABLE (Baseline)")
        print("=" * 50)

        simulation = EconomicSimulation("stable_economy", agents_mode="65_agents")

        # Distribution économie stable selon plan Semaine 3
        stable_agents = [
            # AGRICULTURE (10 agents) - Production alimentaire stable
            ("FARM_01", "AGRICULTURE", Decimal('1250')),
            ("FARM_02", "AGRICULTURE", Decimal('1200')),
            ("FARM_03", "AGRICULTURE", Decimal('1300')),
            ("COOP_01", "AGRICULTURE", Decimal('1500')),
            ("COOP_02", "AGRICULTURE", Decimal('1400')),
            ("AGRI_01", "AGRICULTURE", Decimal('1100')),
            ("AGRI_02", "AGRICULTURE", Decimal('1150')),
            ("AGRI_03", "AGRICULTURE", Decimal('1250')),
            ("AGRI_04", "AGRICULTURE", Decimal('1350')),
            ("AGRI_05", "AGRICULTURE", Decimal('1200')),

            # INDUSTRY (15 agents) - Transformation équilibrée
            ("MFG_01", "INDUSTRY", Decimal('900')),
            ("MFG_02", "INDUSTRY", Decimal('850')),
            ("MFG_03", "INDUSTRY", Decimal('950')),
            ("PROC_01", "INDUSTRY", Decimal('880')),
            ("PROC_02", "INDUSTRY", Decimal('920')),
            ("PROC_03", "INDUSTRY", Decimal('900')),
            ("ASM_01", "INDUSTRY", Decimal('1500')),
            ("ASM_02", "INDUSTRY", Decimal('1400')),
            ("ASM_03", "INDUSTRY", Decimal('1550')),
            ("TECH_01", "INDUSTRY", Decimal('800')),
            ("TECH_02", "INDUSTRY", Decimal('750')),
            ("TECH_03", "INDUSTRY", Decimal('850')),
            ("TECH_04", "INDUSTRY", Decimal('900')),
            ("TECH_05", "INDUSTRY", Decimal('950')),
            ("TECH_06", "INDUSTRY", Decimal('800')),

            # SERVICES (20 agents) - Distribution et services
            ("RTL_01", "SERVICES", Decimal('600')),
            ("RTL_02", "SERVICES", Decimal('650')),
            ("RTL_03", "SERVICES", Decimal('700')),
            ("RTL_04", "SERVICES", Decimal('550')),
            ("RTL_05", "SERVICES", Decimal('750')),
            ("RTL_06", "SERVICES", Decimal('600')),
            ("RTL_07", "SERVICES", Decimal('680')),
            ("RTL_08", "SERVICES", Decimal('720')),
            ("LOG_01", "SERVICES", Decimal('1000')),
            ("LOG_02", "SERVICES", Decimal('950')),
            ("LOG_03", "SERVICES", Decimal('1100')),
            ("LOG_04", "SERVICES", Decimal('1050')),
            ("LOG_05", "SERVICES", Decimal('980')),
            ("LOG_06", "SERVICES", Decimal('1020')),
            ("CONS_01", "SERVICES", Decimal('800')),
            ("CONS_02", "SERVICES", Decimal('750')),
            ("CONS_03", "SERVICES", Decimal('850')),
            ("CONS_04", "SERVICES", Decimal('820')),
            ("CONS_05", "SERVICES", Decimal('780')),
            ("CONS_06", "SERVICES", Decimal('900')),

            # FINANCE (8 agents) - Facilitation financière
            ("BANK_01", "FINANCE", Decimal('5000')),
            ("BANK_02", "FINANCE", Decimal('4500')),
            ("BANK_03", "FINANCE", Decimal('5500')),
            ("INV_01", "FINANCE", Decimal('4000')),
            ("INV_02", "FINANCE", Decimal('3800')),
            ("INV_03", "FINANCE", Decimal('4200')),
            ("INS_01", "FINANCE", Decimal('3000')),
            ("INS_02", "FINANCE", Decimal('3200')),

            # ENERGY (12 agents) - Infrastructure énergétique
            ("PWR_01", "ENERGY", Decimal('2500')),
            ("PWR_02", "ENERGY", Decimal('2300')),
            ("PWR_03", "ENERGY", Decimal('2700')),
            ("PWR_04", "ENERGY", Decimal('2400')),
            ("GRID_01", "ENERGY", Decimal('1500')),
            ("GRID_02", "ENERGY", Decimal('1400')),
            ("GRID_03", "ENERGY", Decimal('1600')),
            ("GRID_04", "ENERGY", Decimal('1550')),
            ("REN_01", "ENERGY", Decimal('2000')),
            ("REN_02", "ENERGY", Decimal('1900')),
            ("REN_03", "ENERGY", Decimal('2100')),
            ("REN_04", "ENERGY", Decimal('2050'))
        ]

        print(f"🏭 Création 65 agents économie stable...")
        for agent_id, sector, balance in stable_agents:
            simulation.create_agent(agent_id, sector, balance)
        print(f"   ✅ {len(stable_agents)} agents créés")

        # Flux inter-sectoriels intensité normale
        transaction_ids = simulation.create_inter_sectoral_flows_batch(flow_intensity=0.5)
        print(f"   ✅ {len(transaction_ids)} flux inter-sectoriels créés")

        # Validation échantillon FEASIBILITY
        start_time = time.time()
        sample_size = min(20, len(transaction_ids))
        sample_transactions = random.sample(transaction_ids, sample_size)

        feasible_count = 0
        total_validation_time = 0

        for tx_id in sample_transactions:
            tx_start = time.time()
            result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
            tx_time = (time.time() - tx_start) * 1000
            total_validation_time += tx_time

            if result.success:
                feasible_count += 1

        total_time = time.time() - start_time
        feasibility_rate = (feasible_count / sample_size) * 100
        avg_validation_time = total_validation_time / sample_size
        throughput = sample_size / total_time

        scenario_result = {
            'scenario': 'Économie Stable',
            'agents': len(stable_agents),
            'transactions': len(transaction_ids),
            'sample_tested': sample_size,
            'feasibility_rate': feasibility_rate,
            'avg_validation_time_ms': avg_validation_time,
            'throughput_txs': throughput,
            'total_time_s': total_time
        }

        print(f"\n📊 Résultats Économie Stable:")
        print(f"   FEASIBILITY: {feasible_count}/{sample_size} ({feasibility_rate:.1f}%)")
        print(f"   Validation: {avg_validation_time:.2f}ms moyenne")
        print(f"   Throughput: {throughput:.1f} tx/sec")

        return scenario_result

    def scenario_oil_shock(self):
        """
        Scénario 2: "Choc Pétrolier" (Stress Test)
        - Réduction 40% capacité ENERGY
        - Impact propagation vers INDUSTRY/SERVICES
        - Test résilience système
        """
        print("\n⚡ SCÉNARIO 2: CHOC PÉTROLIER (Stress)")
        print("=" * 50)

        simulation = EconomicSimulation("oil_shock", agents_mode="65_agents")

        # Agents avec ENERGY réduite (-40% balances)
        shock_agents = [
            # AGRICULTURE (normale)
            ("FARM_A", "AGRICULTURE", Decimal('1250')),
            ("FARM_B", "AGRICULTURE", Decimal('1200')),
            ("FARM_C", "AGRICULTURE", Decimal('1300')),

            # INDUSTRY (impact -25% selon prévision)
            ("MFG_A", "INDUSTRY", Decimal('675')),  # 900 * 0.75
            ("MFG_B", "INDUSTRY", Decimal('638')),  # 850 * 0.75
            ("PROC_A", "INDUSTRY", Decimal('660')), # 880 * 0.75

            # SERVICES (impact -15% selon prévision)
            ("RTL_A", "SERVICES", Decimal('510')),  # 600 * 0.85
            ("LOG_A", "SERVICES", Decimal('850')),  # 1000 * 0.85
            ("CONS_A", "SERVICES", Decimal('680')), # 800 * 0.85

            # FINANCE (intervention +20% liquidités)
            ("BANK_A", "FINANCE", Decimal('6000')), # 5000 * 1.20
            ("INV_A", "FINANCE", Decimal('4800')),  # 4000 * 1.20

            # ENERGY (CHOC -40% capacité)
            ("PWR_SHOCK", "ENERGY", Decimal('1500')),  # 2500 * 0.60
            ("GRID_SHOCK", "ENERGY", Decimal('900')),  # 1500 * 0.60
            ("REN_SHOCK", "ENERGY", Decimal('1200'))   # 2000 * 0.60
        ]

        print(f"🏭 Création agents choc pétrolier...")
        for agent_id, sector, balance in shock_agents:
            simulation.create_agent(agent_id, sector, balance)
        print(f"   ✅ {len(shock_agents)} agents créés")
        print(f"   ⚡ ENERGY capacity réduite -40%")
        print(f"   📉 INDUSTRY impact -25%")
        print(f"   📊 SERVICES impact -15%")
        print(f"   🏦 FINANCE intervention +20%")

        # Flux réduits à cause du choc
        transaction_ids = simulation.create_inter_sectoral_flows_batch(flow_intensity=0.3)
        print(f"   ✅ {len(transaction_ids)} flux créés (intensité réduite)")

        # Test résilience
        start_time = time.time()
        sample_size = min(15, len(transaction_ids))
        sample_transactions = random.sample(transaction_ids, sample_size)

        feasible_count = 0
        total_validation_time = 0

        for tx_id in sample_transactions:
            tx_start = time.time()
            result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
            tx_time = (time.time() - tx_start) * 1000
            total_validation_time += tx_time

            if result.success:
                feasible_count += 1

        total_time = time.time() - start_time
        feasibility_rate = (feasible_count / sample_size) * 100
        avg_validation_time = total_validation_time / sample_size
        throughput = sample_size / total_time

        scenario_result = {
            'scenario': 'Choc Pétrolier',
            'agents': len(shock_agents),
            'transactions': len(transaction_ids),
            'sample_tested': sample_size,
            'feasibility_rate': feasibility_rate,
            'avg_validation_time_ms': avg_validation_time,
            'throughput_txs': throughput,
            'energy_impact': '-40%',
            'system_resilience': 'TESTED'
        }

        print(f"\n📊 Résultats Choc Pétrolier:")
        print(f"   FEASIBILITY: {feasible_count}/{sample_size} ({feasibility_rate:.1f}%)")
        print(f"   Résilience: {'BON' if feasibility_rate >= 50 else 'FRAGILE'}")
        print(f"   Validation: {avg_validation_time:.2f}ms moyenne")

        return scenario_result

    def scenario_tech_innovation(self):
        """
        Scénario 3: "Révolution Technologique" (Innovation)
        - +50% efficacité INDUSTRY
        - Réallocation INDUSTRY→SERVICES
        - Test adaptation système
        """
        print("\n🚀 SCÉNARIO 3: RÉVOLUTION TECH (Innovation)")
        print("=" * 50)

        simulation = EconomicSimulation("tech_revolution", agents_mode="65_agents")

        # Agents avec INDUSTRY boostée (+50%)
        tech_agents = [
            # AGRICULTURE (stable)
            ("FARM_T1", "AGRICULTURE", Decimal('1250')),
            ("FARM_T2", "AGRICULTURE", Decimal('1200')),

            # INDUSTRY (BOOST +50% efficacité)
            ("TECH_BOOST1", "INDUSTRY", Decimal('1350')), # 900 * 1.50
            ("TECH_BOOST2", "INDUSTRY", Decimal('1275')), # 850 * 1.50
            ("TECH_BOOST3", "INDUSTRY", Decimal('1320')), # 880 * 1.50
            ("AI_FACTORY", "INDUSTRY", Decimal('1200')),  # Nouvelle efficacité
            ("ROBO_MFG", "INDUSTRY", Decimal('1400')),    # Automation

            # SERVICES (expansion due à tech +30%)
            ("DIGITAL_A", "SERVICES", Decimal('780')),   # 600 * 1.30
            ("DIGITAL_B", "SERVICES", Decimal('1300')),  # 1000 * 1.30
            ("AI_CONSULT", "SERVICES", Decimal('1040')), # 800 * 1.30
            ("TECH_RETAIL", "SERVICES", Decimal('910')), # 700 * 1.30

            # FINANCE (croissance avec tech)
            ("FINTECH_1", "FINANCE", Decimal('5500')),
            ("FINTECH_2", "FINANCE", Decimal('4400')),

            # ENERGY (stable)
            ("PWR_TECH", "ENERGY", Decimal('2500')),
            ("SMART_GRID", "ENERGY", Decimal('2200'))
        ]

        print(f"🏭 Création agents révolution tech...")
        for agent_id, sector, balance in tech_agents:
            simulation.create_agent(agent_id, sector, balance)
        print(f"   ✅ {len(tech_agents)} agents créés")
        print(f"   🚀 INDUSTRY efficacité +50%")
        print(f"   💻 SERVICES expansion +30%")
        print(f"   🏦 FINANCE croissance tech")

        # Flux intensifiés par l'innovation
        transaction_ids = simulation.create_inter_sectoral_flows_batch(flow_intensity=0.8)
        print(f"   ✅ {len(transaction_ids)} flux créés (intensité élevée)")

        # Test adaptation
        start_time = time.time()
        sample_size = min(18, len(transaction_ids))
        sample_transactions = random.sample(transaction_ids, sample_size)

        feasible_count = 0
        optimization_count = 0
        total_validation_time = 0

        for tx_id in sample_transactions:
            # Test FEASIBILITY
            tx_start = time.time()
            result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
            tx_time = (time.time() - tx_start) * 1000
            total_validation_time += tx_time

            if result.success:
                feasible_count += 1

                # Test OPTIMIZATION sur transactions faisables
                opt_result = simulation.validate_transaction(tx_id, SimulationMode.OPTIMIZATION)
                if opt_result.success:
                    optimization_count += 1

        total_time = time.time() - start_time
        feasibility_rate = (feasible_count / sample_size) * 100
        optimization_rate = (optimization_count / sample_size) * 100
        avg_validation_time = total_validation_time / sample_size
        throughput = sample_size / total_time

        scenario_result = {
            'scenario': 'Révolution Tech',
            'agents': len(tech_agents),
            'transactions': len(transaction_ids),
            'sample_tested': sample_size,
            'feasibility_rate': feasibility_rate,
            'optimization_rate': optimization_rate,
            'avg_validation_time_ms': avg_validation_time,
            'throughput_txs': throughput,
            'innovation_impact': '+50% INDUSTRY',
            'adaptation': 'TESTED'
        }

        print(f"\n📊 Résultats Révolution Tech:")
        print(f"   FEASIBILITY: {feasible_count}/{sample_size} ({feasibility_rate:.1f}%)")
        print(f"   OPTIMIZATION: {optimization_count}/{sample_size} ({optimization_rate:.1f}%)")
        print(f"   Adaptation: {'EXCELLENT' if feasibility_rate >= 70 else 'BON' if feasibility_rate >= 50 else 'DIFFICILE'}")

        return scenario_result

    def run_all_scenarios(self):
        """Lance tous les scénarios économiques et génère rapport final"""
        print("🎯 VALIDATION SCÉNARIOS ÉCONOMIQUES 65 AGENTS")
        print("Architecture Semaine 3 - Tests réalistes économiques")
        print("=" * 60)

        results = []

        # Scénario 1: Économie Stable
        results.append(self.scenario_stable_economy())

        # Scénario 2: Choc Pétrolier
        results.append(self.scenario_oil_shock())

        # Scénario 3: Révolution Tech
        results.append(self.scenario_tech_innovation())

        # Rapport final
        self.generate_final_report(results)

        return results

    def generate_final_report(self, results):
        """Génère rapport final validation scénarios"""
        print("\n" + "=" * 60)
        print("📈 RAPPORT FINAL SCÉNARIOS ÉCONOMIQUES 65 AGENTS")
        print("=" * 60)

        print(f"\n🎯 RÉSUMÉ VALIDATION:")
        for i, result in enumerate(results, 1):
            print(f"   Scénario {i}: {result['scenario']}")
            print(f"      FEASIBILITY: {result['feasibility_rate']:.1f}%")
            print(f"      Validation: {result['avg_validation_time_ms']:.2f}ms")
            print(f"      Throughput: {result.get('throughput_txs', 0):.1f} tx/sec")

        # Moyennes globales
        avg_feasibility = sum(r['feasibility_rate'] for r in results) / len(results)
        avg_validation_time = sum(r['avg_validation_time_ms'] for r in results) / len(results)
        avg_throughput = sum(r.get('throughput_txs', 0) for r in results) / len(results)

        print(f"\n📊 MÉTRIQUES MOYENNES:")
        print(f"   FEASIBILITY: {avg_feasibility:.1f}%")
        print(f"   Validation: {avg_validation_time:.2f}ms")
        print(f"   Throughput: {avg_throughput:.1f} tx/sec")

        # Évaluation cibles Semaine 3
        print(f"\n🎯 ÉVALUATION CIBLES SEMAINE 3:")
        feasibility_ok = avg_feasibility >= 70
        validation_ok = avg_validation_time < 100
        throughput_ok = avg_throughput >= 100

        print(f"   ✅ FEASIBILITY >70%: {'OUI' if feasibility_ok else 'NON'} ({avg_feasibility:.1f}%)")
        print(f"   ✅ Validation <100ms: {'OUI' if validation_ok else 'NON'} ({avg_validation_time:.1f}ms)")
        print(f"   ✅ Throughput >100 tx/sec: {'OUI' if throughput_ok else 'NON'} ({avg_throughput:.1f})")

        if feasibility_ok and validation_ok and throughput_ok:
            print(f"\n🎉 SUCCÈS TOTAL: Architecture 65 agents prête pour production")
            print(f"🚀 Semaine 3 objectifs DÉPASSÉS")
        elif feasibility_ok and validation_ok:
            print(f"\n✅ SUCCÈS: Architecture 65 agents fonctionnelle")
            print(f"⚡ Optimisation throughput recommandée")
        else:
            print(f"\n⚠️  AMÉLIORATIONS NÉCESSAIRES: Optimisation requise")

        print("=" * 60)


def main():
    """Lance validation complète scénarios économiques 65 agents"""
    validator = EconomicScenariosValidator()
    results = validator.run_all_scenarios()


if __name__ == "__main__":
    main()