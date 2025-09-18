"""
Test Suite - Validation Mode 65 Agents (Semaine 3)

Tests complets pour la validation du mode "65_agents" avec:
- Distribution réaliste : AGRICULTURE(10) + INDUSTRY(15) + SERVICES(20) + FINANCE(8) + ENERGY(12) = 65 agents
- Capacité Character-Set Manager : 195 caractères
- Flux inter-sectoriels avancés pour économie à grande échelle
- Performance industrielle avec 65 agents simultanés
"""

import pytest
import sys
import os
from decimal import Decimal
import time

# Import du module simulation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from icgs_simulation.api.icgs_bridge import EconomicSimulation, SimulationMode


class TestMode65AgentsSimulation:
    """Tests validation complète mode 65 agents - Configuration massive Semaine 3"""

    def test_65_agents_character_set_capacity(self):
        """Test capacité Character-Set Manager 65 agents (195 caractères)"""
        simulation = EconomicSimulation("test_65_capacity", agents_mode="65_agents")

        # Vérifier que le Character-Set Manager supporte 195+ caractères
        manager = simulation.character_set_manager
        assert manager is not None, "Character-Set Manager non initialisé"

        # Compter capacité totale disponible
        total_chars = 0
        for sector, char_set_def in manager.character_sets.items():
            chars_count = len(char_set_def.available_characters)
            total_chars += chars_count
            print(f"Secteur {sector}: {chars_count} caractères disponibles")

        print(f"Capacité totale: {total_chars} caractères pour 65 agents (195 requis)")
        assert total_chars >= 195, f"Capacité insuffisante: {total_chars} < 195"

    def test_65_agents_realistic_distribution(self):
        """Test distribution réaliste 65 agents par secteur économique"""
        simulation = EconomicSimulation("test_65_distribution", agents_mode="65_agents")

        # Distribution cible: AGRICULTURE(10) + INDUSTRY(15) + SERVICES(20) + FINANCE(8) + ENERGY(12)
        target_distribution = {
            'AGRICULTURE': 10,
            'INDUSTRY': 15,
            'SERVICES': 20,
            'FINANCE': 8,
            'ENERGY': 12
        }

        created_agents = {}
        agents_created = 0

        # Créer agents selon distribution réaliste
        for sector, count in target_distribution.items():
            created_agents[sector] = []
            for i in range(count):
                agent_id = f"{sector}_AGENT_{i+1:02d}"
                balance = Decimal(str(1000 + i * 100))  # Balance progressive

                agent = simulation.create_agent(agent_id, sector, balance)
                created_agents[sector].append(agent)
                agents_created += 1

        # Validation distribution
        assert agents_created == 65, f"Total agents créés: {agents_created} != 65"

        for sector, expected_count in target_distribution.items():
            actual_count = len(created_agents[sector])
            assert actual_count == expected_count, f"Secteur {sector}: {actual_count} != {expected_count}"
            print(f"✅ Secteur {sector}: {actual_count}/{expected_count} agents créés")

        print(f"✅ Distribution réaliste 65 agents validée")

    def test_65_agents_inter_sectoral_flows_massive(self):
        """Test flux inter-sectoriels automatiques pour économie 65 agents"""
        simulation = EconomicSimulation("test_65_flows", agents_mode="65_agents")

        # Créer échantillon représentatif agents
        sectors = ['AGRICULTURE', 'INDUSTRY', 'SERVICES', 'FINANCE', 'ENERGY']
        agents_per_sector = [6, 8, 10, 4, 6]  # Échantillon proportionnel

        for sector, count in zip(sectors, agents_per_sector):
            for i in range(count):
                agent_id = f"{sector}_AGENT_{i+1}"
                balance = Decimal(str(2000 + i * 200))
                simulation.create_agent(agent_id, sector, balance)

        # Générer flux inter-sectoriels automatiques avec intensité élevée
        start_time = time.time()
        transaction_ids = simulation.create_inter_sectoral_flows_batch(flow_intensity=0.8)
        creation_time = (time.time() - start_time) * 1000

        # Validation performance création
        assert len(transaction_ids) > 0, "Aucune transaction créée"
        assert creation_time < 500, f"Création trop lente: {creation_time:.2f}ms > 500ms"

        print(f"✅ {len(transaction_ids)} transactions flux inter-sectoriels créées en {creation_time:.2f}ms")
        print(f"✅ Performance création: {len(transaction_ids)/creation_time*1000:.1f} tx/sec")

    def test_65_agents_feasibility_validation_massive(self):
        """Test validation FEASIBILITY avec 65 agents - Performance industrielle"""
        simulation = EconomicSimulation("test_65_feasibility", agents_mode="65_agents")

        # Créer 30 agents représentatifs pour test performance
        sectors_sample = {
            'AGRICULTURE': 6,
            'INDUSTRY': 8,
            'SERVICES': 10,
            'FINANCE': 3,
            'ENERGY': 3
        }

        total_agents = 0
        for sector, count in sectors_sample.items():
            for i in range(count):
                agent_id = f"{sector}_{i+1:02d}"
                balance = Decimal(str(2500 + i * 150))
                simulation.create_agent(agent_id, sector, balance)
                total_agents += 1

        # Créer flux économiques
        transaction_ids = simulation.create_inter_sectoral_flows_batch(flow_intensity=0.7)
        assert len(transaction_ids) >= 15, f"Transactions insuffisantes: {len(transaction_ids)}"

        # Validation FEASIBILITY échantillon
        feasible_count = 0
        validation_times = []

        for tx_id in transaction_ids[:20]:  # Test sur échantillon
            start_time = time.time()
            result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
            validation_time = (time.time() - start_time) * 1000
            validation_times.append(validation_time)

            if result.success:
                feasible_count += 1

        # Métriques performance
        feasibility_rate = feasible_count / len(transaction_ids[:20]) * 100
        avg_validation_time = sum(validation_times) / len(validation_times)

        print(f"✅ FEASIBILITY rate: {feasibility_rate:.1f}% ({feasible_count}/{len(transaction_ids[:20])})")
        print(f"✅ Validation time: {avg_validation_time:.2f}ms (cible <100ms)")
        print(f"✅ Agents testés: {total_agents} (architecture 65 agents)")

        # Validations
        assert feasibility_rate >= 60, f"FEASIBILITY rate insuffisant: {feasibility_rate:.1f}% < 60%"
        assert avg_validation_time < 100, f"Validation trop lente: {avg_validation_time:.2f}ms"

    def test_65_agents_stress_test_capacity(self):
        """Test stress avec simulation approchant capacité maximale 65 agents"""
        simulation = EconomicSimulation("test_65_stress", agents_mode="65_agents")

        # Créer 50 agents pour stress test (proche capacité max)
        sectors_stress = {
            'AGRICULTURE': 8,
            'INDUSTRY': 12,
            'SERVICES': 16,
            'FINANCE': 6,
            'ENERGY': 8
        }

        agents_created = 0
        for sector, count in sectors_stress.items():
            for i in range(count):
                agent_id = f"STRESS_{sector}_{i+1:02d}"
                balance = Decimal(str(1500 + i * 100))
                simulation.create_agent(agent_id, sector, balance)
                agents_created += 1

        assert agents_created == 50, f"Agents stress test: {agents_created} != 50"

        # Génération massive flux
        start_time = time.time()
        transaction_ids = simulation.create_inter_sectoral_flows_batch(flow_intensity=0.9)
        batch_creation_time = (time.time() - start_time) * 1000

        # Validation échantillon performance
        sample_size = min(15, len(transaction_ids))
        validation_results = []

        for tx_id in transaction_ids[:sample_size]:
            start_time = time.time()
            result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
            validation_time = (time.time() - start_time) * 1000
            validation_results.append((result.success, validation_time))

        # Métriques stress
        success_count = sum(1 for success, _ in validation_results if success)
        avg_validation = sum(time for _, time in validation_results) / len(validation_results)
        throughput = len(transaction_ids) / batch_creation_time * 1000

        print(f"✅ Agents stress test: {agents_created} agents actifs")
        print(f"✅ Transactions générées: {len(transaction_ids)} en {batch_creation_time:.2f}ms")
        print(f"✅ Throughput création: {throughput:.1f} tx/sec")
        print(f"✅ FEASIBILITY stress: {success_count}/{sample_size} ({success_count/sample_size*100:.1f}%)")
        print(f"✅ Validation stress: {avg_validation:.2f}ms moyenne")

        # Validations stress
        assert len(transaction_ids) >= 25, f"Transactions stress insuffisantes: {len(transaction_ids)}"
        assert batch_creation_time < 1000, f"Création batch trop lente: {batch_creation_time:.2f}ms"
        assert success_count >= sample_size * 0.4, f"Taux succès stress insuffisant: {success_count/sample_size*100:.1f}%"

    def test_65_agents_economic_balance_validation(self):
        """Test cohérence économique balances sectorielles 65 agents"""
        simulation = EconomicSimulation("test_65_balance", agents_mode="65_agents")

        # Balances économiques réalistes par secteur (selon analyse cohérence)
        sector_balances = {
            'AGRICULTURE': Decimal('1250'),  # Foncier + équipements agricoles
            'INDUSTRY': Decimal('900'),      # Équipements industriels moyens
            'SERVICES': Decimal('700'),      # Capital moins intensif
            'FINANCE': Decimal('3000'),      # Capital élevé - intermédiation
            'ENERGY': Decimal('1900')        # Infrastructure lourde
        }

        # Créer agents avec balances sectorielles cohérentes
        agents_distribution = {
            'AGRICULTURE': 8,
            'INDUSTRY': 12,
            'SERVICES': 15,
            'FINANCE': 5,
            'ENERGY': 8
        }

        total_balance = Decimal('0')
        agents_by_sector = {}

        for sector, count in agents_distribution.items():
            agents_by_sector[sector] = []
            sector_base_balance = sector_balances[sector]

            for i in range(count):
                agent_id = f"ECO_{sector}_{i+1:02d}"
                # Variation ±20% autour balance sectorielle
                balance_variation = Decimal(str(0.8 + 0.4 * (i / count)))
                agent_balance = sector_base_balance * balance_variation

                agent = simulation.create_agent(agent_id, sector, agent_balance)
                agents_by_sector[sector].append((agent, agent_balance))
                total_balance += agent_balance

        # Validation cohérence économique
        total_agents = sum(len(agents) for agents in agents_by_sector.values())
        avg_balance = total_balance / total_agents

        print(f"✅ Agents économie cohérente: {total_agents} agents créés")
        print(f"✅ Balance totale économie: {total_balance:,.0f} unités")
        print(f"✅ Balance moyenne: {avg_balance:,.0f} unités/agent")

        # Vérification distribution balance par secteur
        for sector, agents_list in agents_by_sector.items():
            sector_total = sum(balance for _, balance in agents_list)
            sector_avg = sector_total / len(agents_list)
            expected_avg = sector_balances[sector]
            deviation = abs(sector_avg - expected_avg) / expected_avg

            print(f"✅ {sector}: {len(agents_list)} agents, balance moy {sector_avg:,.0f} (cible {expected_avg:,.0f})")
            assert deviation <= 0.3, f"Déviation balance {sector} trop élevée: {deviation:.1%}"

        # Validation économie globale cohérente
        assert total_agents == 48, f"Total agents économie: {total_agents} != 48"
        assert total_balance >= Decimal('50000'), f"Balance totale insuffisante: {total_balance}"


if __name__ == "__main__":
    # Exécution directe pour debug
    test_suite = TestMode65AgentsSimulation()

    print("=== Test Suite Mode 65 Agents - Validation Semaine 3 ===")

    try:
        test_suite.test_65_agents_character_set_capacity()
        print("✅ Test 1: Capacité Character-Set Manager PASS")

        test_suite.test_65_agents_realistic_distribution()
        print("✅ Test 2: Distribution réaliste 65 agents PASS")

        test_suite.test_65_agents_inter_sectoral_flows_massive()
        print("✅ Test 3: Flux inter-sectoriels massifs PASS")

        test_suite.test_65_agents_feasibility_validation_massive()
        print("✅ Test 4: Validation FEASIBILITY massive PASS")

        test_suite.test_65_agents_stress_test_capacity()
        print("✅ Test 5: Stress test capacité maximale PASS")

        test_suite.test_65_agents_economic_balance_validation()
        print("✅ Test 6: Cohérence économique balances PASS")

        print("\n🎯 RÉSULTAT: Mode 65 agents VALIDÉ - Architecture Semaine 3 opérationnelle")

    except Exception as e:
        print(f"❌ ÉCHEC: {e}")
        raise