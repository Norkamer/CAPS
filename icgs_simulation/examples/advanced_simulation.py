#!/usr/bin/env python3
"""
Simulation Économique Avancée ICGS

Démonstration des capacités étendues du framework icgs_simulation:
- Chaînes de valeur multi-sectorielles complexes
- Optimisation Price Discovery à grande échelle
- Métriques performance détaillées
- Scénarios économiques réalistes

Extension du framework selon ICGS_MASTER_RECONSTRUCTION_BLUEPRINT.md
"""

import sys
import os
from decimal import Decimal
import time

# Ajouter icgs_simulation au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_simulation import EconomicSimulation, SECTORS
from icgs_simulation.api.icgs_bridge import SimulationMode


class AdvancedEconomicSimulator:
    """
    Simulateur économique avancé avec chaînes de valeur complexes

    Features avancées:
    - Chaînes multi-sectorielles (Agriculture → Industry → Services → Finance)
    - Métriques performance détaillées
    - Comparaisons FEASIBILITY vs OPTIMIZATION
    - Monitoring temps réel
    """

    def __init__(self, simulation_id: str = "advanced_economic_simulation"):
        self.simulation = EconomicSimulation(simulation_id)
        self.performance_metrics = {
            'total_agents': 0,
            'total_transactions': 0,
            'feasibility_success_rate': 0.0,
            'optimization_success_rate': 0.0,
            'avg_price_discovery_time': 0.0,
            'total_optimal_value': Decimal('0')
        }

    def create_economic_ecosystem(self):
        """
        Crée écosystème économique complet avec chaîne de valeur

        Modèle: Agriculture → Industry → Services → Finance → Energy
        """
        print("🏭 Création écosystème économique avancé...")

        # Secteur Primaire (Agriculture)
        alice = self.simulation.create_agent("ALICE_FARM", "AGRICULTURE", Decimal('2500'),
                                           {"type": "organic_farming", "region": "nord", "capacity": 1000})

        # Secteur Secondaire (Industry)
        bob = self.simulation.create_agent("BOB_MANUFACTURING", "INDUSTRY", Decimal('1800'),
                                         {"type": "food_processing", "efficiency": 0.85})

        charlie = self.simulation.create_agent("CHARLIE_TECH", "INDUSTRY", Decimal('2200'),
                                             {"type": "equipment_manufacturing", "innovation_score": 8.5})

        # Secteur Tertiaire (Services)
        diana = self.simulation.create_agent("DIANA_LOGISTICS", "SERVICES", Decimal('1500'),
                                           {"type": "supply_chain", "network_coverage": 0.75})

        eve = self.simulation.create_agent("EVE_CONSULTING", "SERVICES", Decimal('1200'),
                                         {"type": "business_consulting", "expertise": "optimization"})

        # Secteur Financier
        frank = self.simulation.create_agent("FRANK_BANK", "FINANCE", Decimal('5000'),
                                           {"type": "commercial_banking", "risk_rating": "A+"})

        # Secteur Énergétique
        grace = self.simulation.create_agent("GRACE_ENERGY", "ENERGY", Decimal('3500'),
                                           {"type": "renewable_energy", "capacity_mw": 150})

        self.performance_metrics['total_agents'] = len(self.simulation.agents)

        agents_by_sector = {}
        for agent_id, agent in self.simulation.agents.items():
            sector = agent.sector
            if sector not in agents_by_sector:
                agents_by_sector[sector] = []
            agents_by_sector[sector].append(agent_id)

        print(f"   ✅ {self.performance_metrics['total_agents']} agents créés:")
        for sector, agents in agents_by_sector.items():
            print(f"      {sector}: {', '.join(agents)}")

        return {
            'primary': [alice],
            'secondary': [bob, charlie],
            'tertiary': [diana, eve],
            'financial': [frank],
            'energy': [grace]
        }

    def create_value_chain_transactions(self, agents):
        """
        Crée chaîne de valeur économique complexe

        Flux: Agriculture → Processing → Services → Banking → Energy
        """
        print("\n⚡ Création chaîne de valeur économique...")

        transactions = []

        # Chaîne principale Agriculture → Industry
        tx1 = self.simulation.create_transaction("ALICE_FARM", "BOB_MANUFACTURING", Decimal('300'),
                                                {"chain_step": 1, "product": "raw_materials"})
        transactions.append(("TX1_AGRI_TO_INDUSTRY", tx1))

        # Industry → Services (Logistics)
        tx2 = self.simulation.create_transaction("BOB_MANUFACTURING", "DIANA_LOGISTICS", Decimal('180'),
                                                {"chain_step": 2, "service": "distribution"})
        transactions.append(("TX2_INDUSTRY_TO_SERVICES", tx2))

        # Services → Finance (Payment processing)
        tx3 = self.simulation.create_transaction("DIANA_LOGISTICS", "FRANK_BANK", Decimal('150'),
                                                {"chain_step": 3, "service": "payment_settlement"})
        transactions.append(("TX3_SERVICES_TO_FINANCE", tx3))

        # Chaîne parallèle Tech → Consulting
        tx4 = self.simulation.create_transaction("CHARLIE_TECH", "EVE_CONSULTING", Decimal('220'),
                                                {"chain_step": "parallel", "service": "optimization_consulting"})
        transactions.append(("TX4_TECH_TO_CONSULTING", tx4))

        # Energy pour tous (Infrastructure)
        tx5 = self.simulation.create_transaction("GRACE_ENERGY", "BOB_MANUFACTURING", Decimal('120'),
                                                {"infrastructure": True, "energy_type": "renewable"})
        transactions.append(("TX5_ENERGY_TO_INDUSTRY", tx5))

        tx6 = self.simulation.create_transaction("GRACE_ENERGY", "DIANA_LOGISTICS", Decimal('80'),
                                                {"infrastructure": True, "energy_type": "transport"})
        transactions.append(("TX6_ENERGY_TO_LOGISTICS", tx6))

        self.performance_metrics['total_transactions'] = len(transactions)

        print(f"   ✅ {len(transactions)} transactions créées dans chaîne de valeur")
        for name, tx_id in transactions:
            print(f"      {name}: {tx_id}")

        return transactions

    def run_comprehensive_validation(self, transactions):
        """
        Validation complète FEASIBILITY vs OPTIMIZATION avec métriques
        """
        print("\n🔍 Validation complète chaîne de valeur...")
        print("=" * 60)

        feasibility_results = []
        optimization_results = []

        # Tests FEASIBILITY
        print("📋 Mode FEASIBILITY (validation faisabilité):")
        feasibility_start = time.time()

        for name, tx_id in transactions:
            result = self.simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
            feasibility_results.append((name, result))

            status = "✅ FAISABLE" if result.success else "❌ INFAISABLE"
            print(f"   {name}: {status} ({result.validation_time_ms:.2f}ms)")

        feasibility_time = time.time() - feasibility_start
        feasibility_success = sum(1 for _, r in feasibility_results if r.success)
        self.performance_metrics['feasibility_success_rate'] = feasibility_success / len(transactions) * 100

        print(f"\n📊 Résultats FEASIBILITY: {feasibility_success}/{len(transactions)} réussies ({self.performance_metrics['feasibility_success_rate']:.1f}%)")

        # Tests OPTIMIZATION (Price Discovery)
        print(f"\n💰 Mode OPTIMIZATION (Price Discovery):")
        optimization_start = time.time()

        total_price_discovery_time = 0.0
        total_optimal_value = Decimal('0')

        for name, tx_id in transactions:
            result = self.simulation.validate_transaction(tx_id, SimulationMode.OPTIMIZATION)
            optimization_results.append((name, result))

            if result.success and result.optimal_price is not None:
                status = f"✅ OPTIMAL (prix: {result.optimal_price})"
                total_optimal_value += result.optimal_price
            else:
                status = "❌ ÉCHEC"

            total_price_discovery_time += result.validation_time_ms
            print(f"   {name}: {status} ({result.validation_time_ms:.2f}ms)")

        optimization_time = time.time() - optimization_start
        optimization_success = sum(1 for _, r in optimization_results if r.success)
        self.performance_metrics['optimization_success_rate'] = optimization_success / len(transactions) * 100
        self.performance_metrics['avg_price_discovery_time'] = total_price_discovery_time / len(transactions)
        self.performance_metrics['total_optimal_value'] = total_optimal_value

        print(f"\n📊 Résultats OPTIMIZATION: {optimization_success}/{len(transactions)} réussies ({self.performance_metrics['optimization_success_rate']:.1f}%)")
        print(f"💎 Valeur totale optimisée: {total_optimal_value}")
        print(f"⚡ Temps moyen Price Discovery: {self.performance_metrics['avg_price_discovery_time']:.2f}ms")

        return feasibility_results, optimization_results

    def generate_performance_report(self):
        """
        Génère rapport performance détaillé
        """
        print("\n" + "=" * 60)
        print("📈 RAPPORT PERFORMANCE SIMULATION AVANCÉE")
        print("=" * 60)

        print(f"\n🏭 ÉCOSYSTÈME ÉCONOMIQUE:")
        print(f"   Agents économiques: {self.performance_metrics['total_agents']}")
        print(f"   Transactions chaîne de valeur: {self.performance_metrics['total_transactions']}")
        print(f"   Secteurs représentés: {len(set(agent.sector for agent in self.simulation.agents.values()))}")

        print(f"\n✅ TAUX DE SUCCÈS:")
        print(f"   FEASIBILITY: {self.performance_metrics['feasibility_success_rate']:.1f}%")
        print(f"   OPTIMIZATION: {self.performance_metrics['optimization_success_rate']:.1f}%")

        print(f"\n💰 OPTIMISATION PRIX:")
        print(f"   Valeur totale découverte: {self.performance_metrics['total_optimal_value']}")
        print(f"   Temps moyen Price Discovery: {self.performance_metrics['avg_price_discovery_time']:.2f}ms")

        # Stats DAG détaillées
        dag_stats = self.simulation.get_simulation_stats()
        print(f"\n📊 PIPELINE DAG DÉTAILLÉ:")
        print(f"   Transactions ajoutées: {dag_stats['dag_stats']['transactions_added']}")
        print(f"   Transactions rejetées: {dag_stats['dag_stats']['transactions_rejected']}")
        print(f"   Résolutions Simplex: {dag_stats['dag_stats']['simplex_feasible']}")
        print(f"   Temps validation moyen: {dag_stats['dag_stats']['avg_simplex_solve_time_ms']:.2f}ms")

        # Comparaison performance
        if self.performance_metrics['feasibility_success_rate'] > 80:
            print(f"\n🎯 ÉVALUATION: Excellente robustesse pipeline (>{self.performance_metrics['feasibility_success_rate']:.0f}%)")
        elif self.performance_metrics['feasibility_success_rate'] > 60:
            print(f"\n⚠️  ÉVALUATION: Pipeline fonctionnel mais optimisable ({self.performance_metrics['feasibility_success_rate']:.0f}%)")
        else:
            print(f"\n❌ ÉVALUATION: Pipeline nécessite améliorations (<{self.performance_metrics['feasibility_success_rate']:.0f}%)")

        print(f"\n✅ SIMULATION AVANCÉE COMPLÉTÉE")
        print(f"🚀 Framework icgs_simulation opérationnel pour économies complexes")
        print("=" * 60)


def main():
    """
    Lance simulation économique avancée complète
    """
    print("🎯 SIMULATION ÉCONOMIQUE AVANCÉE ICGS")
    print("Architecture: Multi-secteurs avec Price Discovery")
    print()

    # Initialisation simulateur avancé
    simulator = AdvancedEconomicSimulator("advanced_demo_v1")

    try:
        # Étape 1: Création écosystème économique
        agents = simulator.create_economic_ecosystem()

        # Étape 2: Chaîne de valeur complexe
        transactions = simulator.create_value_chain_transactions(agents)

        # Étape 3: Validation complète avec métriques
        feasibility_results, optimization_results = simulator.run_comprehensive_validation(transactions)

        # Étape 4: Rapport performance
        simulator.generate_performance_report()

    except Exception as e:
        print(f"\n❌ ERREUR SIMULATION AVANCÉE: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()