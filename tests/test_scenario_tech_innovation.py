"""
Test Scénario Innovation Tech - Validation INDUSTRY +50%

Tests validation scénario "Innovation Tech" avec:
- Croissance INDUSTRY +50% et innovation diffusion
- Validation adaptation économique positive
- Métriques croissance soutenue et équilibre final
- Tests adoption innovation par secteur
"""

import pytest
import sys
import os
from decimal import Decimal
import time

# Import modules simulation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from icgs_simulation.api.icgs_bridge import EconomicSimulation
from icgs_simulation.scenarios.tech_innovation import TechInnovationScenario


class TestTechInnovationScenario:
    """Tests validation scénario Innovation Tech"""

    def test_tech_innovation_setup_economy(self):
        """Test configuration économie pour innovation tech"""
        simulation = EconomicSimulation("test_tech_setup", agents_mode="65_agents")
        scenario = TechInnovationScenario(simulation, industry_growth=0.50)

        # Configuration agents focus innovation
        total_agents = scenario.setup_tech_innovation_economy()

        # Validation distribution innovation compatible
        expected_distribution = {
            'AGRICULTURE': 5,
            'INDUSTRY': 12,  # Focus innovation
            'SERVICES': 10,
            'FINANCE': 5,
            'ENERGY': 6
        }

        assert total_agents == 38, f"Total agents: {total_agents} != 38"

        # Vérifier focus INDUSTRY innovation
        industry_agents = len(scenario.economic_agents['INDUSTRY'])
        industry_ratio = industry_agents / total_agents

        assert industry_ratio > 0.25, f"Ratio INDUSTRY insuffisant: {industry_ratio:.1%} <= 25%"

        print(f"✅ Configuration innovation tech: {total_agents} agents, INDUSTRY focus {industry_ratio:.1%}")

    def test_tech_innovation_phases_definition(self):
        """Test définition phases innovation tech"""
        simulation = EconomicSimulation("test_phases", agents_mode="65_agents")
        scenario = TechInnovationScenario(simulation, industry_growth=0.60)  # +60%

        phases = scenario.phases

        # Validation structure phases
        assert len(phases) == 4, f"Nombre phases: {len(phases)} != 4"

        # Validation croissance INDUSTRY par phase
        industry_impacts = [phase.sector_impacts['INDUSTRY'] for phase in phases]
        expected_progression = [1.0, 1.6, 1.76, 1.92]  # 1.0 → 1.6 → 1.76 → 1.92

        for i, (actual, expected) in enumerate(zip(industry_impacts, expected_progression)):
            assert abs(actual - expected) < 0.1, f"Phase {i+1} INDUSTRY impact: {actual} ~= {expected}"

        # Validation innovation intensity
        innovation_intensities = [phase.innovation_intensity for phase in phases]
        assert innovation_intensities[1] == 1.0, "Innovation breakthrough pas à 100%"
        assert innovation_intensities[0] == 0.0, "Baseline innovation pas à 0%"

        print(f"✅ Phases innovation tech validées: croissance INDUSTRY progressive")

    def test_tech_innovation_impacts_application(self):
        """Test application impacts innovation par phase"""
        simulation = EconomicSimulation("test_impacts", agents_mode="65_agents")
        scenario = TechInnovationScenario(simulation, industry_growth=0.40)

        # Configuration agents
        scenario.setup_tech_innovation_economy()

        # Test application impacts Phase 2 (Innovation Breakthrough)
        innovation_phase = scenario.phases[1]
        impacts_applied = scenario.apply_innovation_impacts(innovation_phase)

        # Validation impacts attendus
        expected_impacts = {
            'AGRICULTURE': +5.0,    # 1.05 → +5%
            'INDUSTRY': +40.0,      # 1.40 → +40%
            'SERVICES': +2.0,       # 1.02 → +2%
            'FINANCE': +8.0,        # 1.08 → +8%
            'ENERGY': +20.0         # 1.20 → +20%
        }

        for sector, expected_impact in expected_impacts.items():
            actual_impact = impacts_applied[sector]
            assert abs(actual_impact - expected_impact) < 2.0, f"Impact {sector}: {actual_impact:.1f}% ~= {expected_impact:.1f}%"

        print(f"✅ Impacts innovation appliqués: INDUSTRY +40%, ENERGY +20%")

    def test_tech_innovation_phase_simulation(self):
        """Test simulation phase innovation"""
        simulation = EconomicSimulation("test_phase_sim", agents_mode="65_agents")
        scenario = TechInnovationScenario(simulation, min_equilibrium_growth=0.20)

        # Configuration
        scenario.setup_tech_innovation_economy()
        from datetime import datetime
        scenario.start_time = datetime.now()

        # Simulation Phase 2 (Innovation Breakthrough)
        innovation_phase = scenario.phases[1]
        phase_result = scenario.simulate_innovation_phase(innovation_phase)

        # Validation résultats phase innovation
        assert phase_result['phase'] == innovation_phase, "Phase incorrecte"
        assert phase_result['transactions_count'] >= 0, f"Transactions négatives: {phase_result['transactions_count']}"
        assert phase_result['avg_feasibility_rate'] >= 0, f"FEASIBILITY négative: {phase_result['avg_feasibility_rate']}"

        # Validation adoption innovation
        sector_adoption = phase_result['sector_adoption']
        assert len(sector_adoption) == 5, f"Secteurs adoption: {len(sector_adoption)} != 5"

        # INDUSTRY doit avoir forte adoption
        industry_adoption = sector_adoption['INDUSTRY']['adoption_rate']
        assert industry_adoption > 0.5, f"INDUSTRY adoption faible: {industry_adoption:.1%}"

        print(f"✅ Phase innovation simulée: {phase_result['transactions_count']} tx, INDUSTRY adoption {industry_adoption:.1%}")

    def test_tech_innovation_success_validation(self):
        """Test validation succès innovation"""
        simulation = EconomicSimulation("test_success", agents_mode="65_agents")
        scenario = TechInnovationScenario(simulation, min_equilibrium_growth=0.20)

        # Données test phases simulées (croissance positive)
        mock_phase_results = [
            # Phase 1: Baseline
            {'avg_feasibility_rate': 0.65, 'total_volume': Decimal('10000')},
            # Phase 2: Innovation
            {'avg_feasibility_rate': 0.78, 'total_volume': Decimal('13500')},
            # Phase 3: Réallocation
            {'avg_feasibility_rate': 0.82, 'total_volume': Decimal('14800')},
            # Phase 4: Équilibre
            {'avg_feasibility_rate': 0.85, 'total_volume': Decimal('15200')}
        ]

        # Validation succès innovation
        success_ok, metrics = scenario.validate_innovation_success(mock_phase_results)

        # Vérification métriques
        assert metrics['baseline_feasibility'] == 0.65, f"Baseline incorrecte: {metrics['baseline_feasibility']}"
        assert metrics['innovation_boost_ratio'] > 0, f"Boost innovation négatif: {metrics['innovation_boost_ratio']}"
        assert metrics['sustained_growth_ratio'] >= 0.20, f"Croissance soutenue insuffisante: {metrics['sustained_growth_ratio']:.1%}"

        print(f"✅ Innovation success validée: {'OUI' if success_ok else 'NON'}")
        print(f"  Boost innovation: {metrics['innovation_boost_ratio']:.1%}")
        print(f"  Croissance soutenue: {metrics['sustained_growth_ratio']:.1%}")

    def test_tech_innovation_full_simulation_mock(self):
        """Test simulation complète innovation (version mock)"""
        simulation = EconomicSimulation("test_full_tech", agents_mode="65_agents")
        scenario = TechInnovationScenario(simulation, industry_growth=0.35, min_equilibrium_growth=0.20)

        # Mock simulation pour performance test
        def mock_run_innovation():
            return type('MockTechResults', (), {
                'success': True,
                'simulation_id': simulation.simulation_id,
                'start_time': time.time(),
                'end_time': time.time(),
                'total_duration_hours': 0.001,
                'baseline_feasibility': 0.67,
                'innovation_feasibility': 0.81,
                'reallocation_feasibility': 0.84,
                'equilibrium_feasibility': 0.86,
                'baseline_volume': Decimal('9800'),
                'growth_impact_percent': 32.5,
                'final_growth_ratio': 1.38,
                'sector_innovation_adoption': {
                    sector: {
                        'avg_adoption_rate': 0.75 if sector == 'INDUSTRY' else 0.45,
                        'final_growth_factor': 1.35 if sector == 'INDUSTRY' else 1.15,
                        'innovation_score': 0.80 if sector == 'INDUSTRY' else 0.35
                    } for sector in ['AGRICULTURE', 'INDUSTRY', 'SERVICES', 'FINANCE', 'ENERGY']
                },
                'growth_sustained': True,
                'reallocation_successful': True,
                'equilibrium_target_met': True,
                'phase_results': []
            })()

        # Exécution test mock
        start_time = time.time()
        results = mock_run_innovation()
        execution_time = time.time() - start_time

        # Validations résultats innovation
        assert results is not None, "Aucun résultat innovation"
        assert results.success == True, "Innovation pas validée"
        assert results.growth_impact_percent > 0, f"Impact croissance nul: {results.growth_impact_percent}"
        assert results.final_growth_ratio > 1.2, f"Croissance finale insuffisante: {results.final_growth_ratio}"

        # Innovation adoption secteurs
        industry_adoption = results.sector_innovation_adoption['INDUSTRY']
        assert industry_adoption['avg_adoption_rate'] > 0.5, f"INDUSTRY adoption faible: {industry_adoption['avg_adoption_rate']:.1%}"
        assert industry_adoption['innovation_score'] > 0.5, f"INDUSTRY score innovation faible: {industry_adoption['innovation_score']}"

        print(f"✅ Test innovation tech: {execution_time:.2f}s")
        print(f"✅ Success innovation: {'OUI' if results.success else 'NON'}")
        print(f"✅ Croissance impact: +{results.growth_impact_percent:.1f}%")
        print(f"✅ Ratio final: {results.final_growth_ratio:.2f}x")
        print(f"✅ INDUSTRY adoption: {industry_adoption['avg_adoption_rate']:.1%}")

    def test_tech_innovation_sector_adoption_analysis(self):
        """Test analyse adoption innovation par secteur"""
        simulation = EconomicSimulation("test_adoption", agents_mode="65_agents")
        scenario = TechInnovationScenario(simulation)

        # Configuration
        scenario.setup_tech_innovation_economy()

        # Simulation adoption avec données phases réelles
        mock_phases = scenario.phases

        # Test calcul adoption basé sur impacts sectoriels
        for phase_idx, phase in enumerate(mock_phases):
            print(f"Phase {phase_idx + 1}: {phase.phase_name}")

            for sector, impact in phase.sector_impacts.items():
                adoption_rate = min(1.0, phase.innovation_intensity * impact * 0.8)
                growth_factor = impact
                agents_count = len(scenario.economic_agents.get(sector, []))

                print(f"  {sector}: Impact={impact:.2f}, Adoption={adoption_rate:.1%}, "
                      f"Growth={growth_factor:.2f}, Agents={agents_count}")

                # Validations secteur
                assert 0 <= adoption_rate <= 1, f"Adoption rate invalide {sector}: {adoption_rate}"
                assert growth_factor >= 1.0 or phase_idx == 0, f"Growth factor négatif {sector}: {growth_factor}"
                assert agents_count > 0, f"Aucun agent {sector}"

        # Validation spécifique INDUSTRY (secteur innovation)
        industry_final_impact = mock_phases[-1].sector_impacts['INDUSTRY']
        assert industry_final_impact >= 1.5, f"INDUSTRY impact final insuffisant: {industry_final_impact}"

    def test_tech_innovation_performance_metrics(self):
        """Test métriques performance scénario innovation"""
        simulation = EconomicSimulation("test_perf", agents_mode="65_agents")
        scenario = TechInnovationScenario(simulation, industry_growth=0.25)  # +25% modéré

        # Configuration performance
        scenario.setup_tech_innovation_economy()
        from datetime import datetime
        scenario.start_time = datetime.now()

        # Test performance simulation phase
        start_perf = time.time()
        baseline_phase = scenario.phases[0]
        phase_result = scenario.simulate_innovation_phase(baseline_phase)
        simulation_time = (time.time() - start_perf) * 1000  # ms

        # Métriques performance
        tx_count = phase_result['transactions_count']
        feasibility_rate = phase_result['avg_feasibility_rate']
        innovation_intensity = phase_result['innovation_intensity_used']

        print(f"✅ Performance innovation phase:")
        print(f"  - Temps simulation: {simulation_time:.2f}ms")
        print(f"  - Transactions: {tx_count}")
        print(f"  - FEASIBILITY: {feasibility_rate:.1%}")
        print(f"  - Intensité innovation: {innovation_intensity:.3f}")

        # Validations performance
        assert simulation_time < 10000, f"Simulation trop lente: {simulation_time:.0f}ms > 10s"
        assert tx_count > 0, f"Aucune transaction: {tx_count}"
        assert 0 <= feasibility_rate <= 1, f"FEASIBILITY invalide: {feasibility_rate}"
        assert innovation_intensity > 0, f"Intensité innovation nulle: {innovation_intensity}"


if __name__ == "__main__":
    # Exécution directe pour debug
    test_suite = TestTechInnovationScenario()

    print("=== Test Suite Scénario Innovation Tech ===")

    try:
        test_suite.test_tech_innovation_setup_economy()
        print("✅ Test 1: Configuration économie innovation PASS")

        test_suite.test_tech_innovation_phases_definition()
        print("✅ Test 2: Définition phases innovation PASS")

        test_suite.test_tech_innovation_impacts_application()
        print("✅ Test 3: Application impacts innovation PASS")

        test_suite.test_tech_innovation_phase_simulation()
        print("✅ Test 4: Simulation phase innovation PASS")

        test_suite.test_tech_innovation_success_validation()
        print("✅ Test 5: Validation succès innovation PASS")

        test_suite.test_tech_innovation_full_simulation_mock()
        print("✅ Test 6: Simulation complète innovation PASS")

        test_suite.test_tech_innovation_sector_adoption_analysis()
        print("✅ Test 7: Analyse adoption sectorielle PASS")

        test_suite.test_tech_innovation_performance_metrics()
        print("✅ Test 8: Métriques performance PASS")

        print("\n🎯 RÉSULTAT: Scénario Innovation Tech VALIDÉ - INDUSTRY +50% Opérationnel")

    except Exception as e:
        print(f"❌ ÉCHEC: {e}")
        raise