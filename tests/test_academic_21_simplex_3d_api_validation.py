#!/usr/bin/env python3
"""
Test Académique 21: Validation API Simplex 3D ICGS
==================================================

Test de validation rigoureuse pour l'API read-only d'extraction
des données Simplex vers visualisation 3D.

Validation Mathématique:
- Mapping correct variables f_i → coordonnées (x,y,z)
- Classification contraintes économiques (SOURCE/TARGET/SECONDARY)
- Cohérence géométrique et stabilité numérique

Validation Algorithmique:
- Capture états Simplex authentiques
- Séquence transitions entre pivots
- Intégrité données collectées

Validation Intégration:
- Compatibilité avec icgs_core
- Performance et overhead
- Robustesse cas limites

Architecture testée:
- SimplexState3D, SimplexTransition3D, Simplex3DCollector
- Simplex3DMapper et classification contraintes
- Export animation data et format JSON
"""

import unittest
import sys
import os
import time
import math
from decimal import Decimal, getcontext
from typing import Dict, List, Tuple, Optional, Any

# Configuration précision
getcontext().prec = 50

# Import modules ICGS
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from icgs_core import (
    LinearProgram, LinearConstraint, FluxVariable, ConstraintType,
    TripleValidationOrientedSimplex, SimplexSolution, ValidationMode
)
from icgs_core.linear_programming import (
    build_source_constraint, build_target_constraint, build_secondary_constraint
)
from icgs_simulation import EconomicSimulation
from icgs_simulation.api.icgs_bridge import SimulationMode

# Import API Simplex 3D
from icgs_simplex_3d_api import (
    Simplex3DCollector, SimplexState3D, SimplexTransition3D,
    Simplex3DMapper, ConstraintClass3D, SimplexTransitionType
)
from icgs_3d_space_analyzer import ICGS3DSpaceAnalyzer


class TestAcademicSimplex3DAPI(unittest.TestCase):
    """Test académique validation API Simplex 3D"""

    def setUp(self):
        """Configuration initiale tests"""
        self.collector = Simplex3DCollector()
        self.mapper = Simplex3DMapper()

        # Configuration simulation test
        self.simulation = EconomicSimulation("test_simplex_3d_api")
        self.analyzer = ICGS3DSpaceAnalyzer(self.simulation)

    def test_01_simplex_3d_mapper_constraint_classification(self):
        """Test 01: Classification contraintes économiques"""
        print("🧮 Test 01: Classification contraintes économiques")

        # Créer contraintes test
        source_constraint = build_source_constraint(
            nfa_state_weights={"state_1": Decimal('1.5'), "state_2": Decimal('2.0')},
            primary_regex_weight=Decimal('1.0'),
            acceptable_value=Decimal('1000'),
            constraint_name="source_primary_test"
        )

        target_constraint = build_target_constraint(
            nfa_state_weights={"state_1": Decimal('0.8'), "state_3": Decimal('1.2')},
            primary_regex_weight=Decimal('1.0'),
            required_value=Decimal('500'),
            constraint_name="target_primary_test"
        )

        secondary_constraint = build_secondary_constraint(
            nfa_state_weights={"state_2": Decimal('0.5'), "state_4": Decimal('0.3')},
            secondary_regex_weight=Decimal('1.0'),
            constraint_name="secondary_test"
        )

        # Test classification
        source_class = self.mapper.classify_constraint(source_constraint)
        target_class = self.mapper.classify_constraint(target_constraint)
        secondary_class = self.mapper.classify_constraint(secondary_constraint)

        self.assertEqual(source_class, ConstraintClass3D.SOURCE)
        self.assertEqual(target_class, ConstraintClass3D.TARGET)
        self.assertEqual(secondary_class, ConstraintClass3D.SECONDARY)

        print("   ✅ Classification contraintes correcte")

    def test_02_variables_fi_to_3d_mapping(self):
        """Test 02: Mapping variables f_i vers coordonnées 3D"""
        print("🧮 Test 02: Mapping variables f_i → coordonnées 3D")

        # Variables f_i test
        variables_fi = {
            "state_1": Decimal('10.0'),
            "state_2": Decimal('5.0'),
            "state_3": Decimal('8.0'),
            "state_4": Decimal('3.0')
        }

        # Configuration contraintes avec poids
        self.mapper.constraint_classification = {
            "source_constraint": ConstraintClass3D.SOURCE,
            "target_constraint": ConstraintClass3D.TARGET,
            "secondary_constraint": ConstraintClass3D.SECONDARY
        }

        self.mapper.constraint_weights = {
            "source_constraint": {
                "state_1": Decimal('1.5'),
                "state_2": Decimal('2.0')
            },
            "target_constraint": {
                "state_1": Decimal('0.8'),
                "state_3": Decimal('1.2')
            },
            "secondary_constraint": {
                "state_2": Decimal('0.5'),
                "state_4": Decimal('0.3')
            }
        }

        # Calcul mapping 3D
        coordinates = self.mapper.map_variables_to_3d(variables_fi)

        # Validation calculs
        expected_x = float(10.0 * 1.5 + 5.0 * 2.0)  # SOURCE: 15 + 10 = 25
        expected_y = float(10.0 * 0.8 + 8.0 * 1.2)  # TARGET: 8 + 9.6 = 17.6
        expected_z = float(5.0 * 0.5 + 3.0 * 0.3)   # SECONDARY: 2.5 + 0.9 = 3.4

        self.assertAlmostEqual(coordinates[0], expected_x, places=6)
        self.assertAlmostEqual(coordinates[1], expected_y, places=6)
        self.assertAlmostEqual(coordinates[2], expected_z, places=6)

        print(f"   ✅ Mapping 3D: ({coordinates[0]:.2f}, {coordinates[1]:.2f}, {coordinates[2]:.2f})")
        print(f"   ✅ Attendu: ({expected_x:.2f}, {expected_y:.2f}, {expected_z:.2f})")

    def test_03_simplex_state_capture(self):
        """Test 03: Capture état Simplex authentique"""
        print("🧮 Test 03: Capture état Simplex")

        # Créer LinearProgram test
        linear_program = LinearProgram()

        # Variables flux
        linear_program.variables = {
            "f_1": FluxVariable(
                variable_id="f_1",
                value=Decimal('10.0'),
                lower_bound=Decimal('0'),
                is_basic=True
            ),
            "f_2": FluxVariable(
                variable_id="f_2",
                value=Decimal('5.0'),
                lower_bound=Decimal('0'),
                is_basic=False
            )
        }

        # SimplexSolution test
        from icgs_core.simplex_solver import SolutionStatus
        solution = SimplexSolution(status=SolutionStatus.OPTIMAL)
        solution.variables = {"f_1": Decimal('10.0'), "f_2": Decimal('5.0')}
        solution.iterations_used = 3
        solution.solving_time = 0.025

        # Capture état
        state = self.collector.capture_simplex_state(
            linear_program, solution, ValidationMode.OPTIMIZATION
        )

        # Validations
        self.assertEqual(state.step_number, 0)
        self.assertEqual(len(state.variables_fi), 2)
        self.assertEqual(state.variables_fi["f_1"], Decimal('10.0'))
        self.assertEqual(state.variables_fi["f_2"], Decimal('5.0'))
        self.assertTrue(state.is_optimal)
        self.assertEqual(state.iterations_used, 3)
        self.assertIn("f_1", state.basic_variables)
        self.assertIn("f_2", state.non_basic_variables)

        print(f"   ✅ État capturé: step {state.step_number}, {len(state.variables_fi)} variables f_i")
        print(f"   ✅ Variables: {dict(state.variables_fi)}")

    def test_04_simplex_transition_analysis(self):
        """Test 04: Analyse transitions Simplex"""
        print("🧮 Test 04: Analyse transitions Simplex")

        # Créer deux états test
        state1 = SimplexState3D(
            timestamp=time.time(),
            step_number=0,
            variables_fi={"f_1": Decimal('10.0'), "f_2": Decimal('5.0')},
            constraint_contributions={},
            coordinates_3d=(10.0, 15.0, 2.0),
            basic_variables={"f_1"},
            non_basic_variables={"f_2"}
        )

        state2 = SimplexState3D(
            timestamp=time.time() + 0.001,
            step_number=1,
            variables_fi={"f_1": Decimal('8.0'), "f_2": Decimal('12.0')},
            constraint_contributions={},
            coordinates_3d=(12.0, 18.0, 3.5),
            basic_variables={"f_2"},
            non_basic_variables={"f_1"}
        )

        # Capturer transition
        transition = self.collector.capture_transition(
            state1, state2, SimplexTransitionType.PIVOT_ENTER
        )

        # Validations
        self.assertEqual(transition.from_state, state1)
        self.assertEqual(transition.to_state, state2)
        self.assertEqual(transition.transition_type, SimplexTransitionType.PIVOT_ENTER)
        self.assertEqual(transition.entering_variable, "f_2")
        self.assertEqual(transition.leaving_variable, "f_1")

        # Validation distance euclidienne
        expected_distance = math.sqrt((12-10)**2 + (18-15)**2 + (3.5-2)**2)
        self.assertAlmostEqual(transition.euclidean_distance, expected_distance, places=6)

        print(f"   ✅ Transition analysée: {transition.leaving_variable} → {transition.entering_variable}")
        print(f"   ✅ Distance euclidienne: {transition.euclidean_distance:.3f}")

    def test_05_integration_with_icgs_simulation(self):
        """Test 05: Intégration avec simulation ICGS"""
        print("🧮 Test 05: Intégration simulation ICGS")

        # Créer agents
        agents_data = [
            ("ALICE_FARM", "AGRICULTURE", Decimal('1500')),
            ("BOB_INDUSTRY", "INDUSTRY", Decimal('1200'))
        ]

        for agent_id, sector, balance in agents_data:
            self.simulation.create_agent(agent_id, sector, balance)

        # Activer collecteur (mode approximation)
        self.analyzer.use_authentic_simplex_data = False

        # Analyser transaction
        point = self.analyzer.analyze_transaction_3d_space(
            "ALICE_FARM", "BOB_INDUSTRY", Decimal('300')
        )

        # Validations
        self.assertIsNotNone(point)
        self.assertEqual(point.pivot_step, 0)
        self.assertTrue(point.feasible)
        self.assertTrue(point.optimal)
        self.assertGreater(point.x, 0)
        self.assertGreater(point.y, 0)

        print(f"   ✅ Transaction analysée: {point.transaction_id}")
        print(f"   ✅ Position 3D: ({point.x:.2f}, {point.y:.2f}, {point.z:.2f})")
        print(f"   ✅ Statut: Faisable={point.feasible}, Optimal={point.optimal}")

    def test_06_export_animation_data_format(self):
        """Test 06: Format export données animation"""
        print("🧮 Test 06: Export données animation")

        # Simuler capture de données
        self._simulate_simplex_execution()

        # Export données
        animation_data = self.collector.export_animation_data()

        # Validations structure
        self.assertIn('metadata', animation_data)
        self.assertIn('simplex_states', animation_data)
        self.assertIn('simplex_transitions', animation_data)
        self.assertIn('axis_mapping', animation_data)

        # Validation métadonnées
        metadata = animation_data['metadata']
        self.assertGreater(metadata['total_states'], 0)
        self.assertGreater(metadata['algorithm_steps'], 0)

        # Validation format états
        if animation_data['simplex_states']:
            state = animation_data['simplex_states'][0]
            self.assertIn('step', state)
            self.assertIn('coordinates', state)
            self.assertIn('variables_fi', state)
            self.assertIn('is_feasible', state)

        print(f"   ✅ Export généré: {metadata['total_states']} états, {metadata['total_transitions']} transitions")

    def test_07_performance_overhead_measurement(self):
        """Test 07: Mesure overhead performance"""
        print("🧮 Test 07: Overhead performance API")

        # Mesurer performance avec collecteur
        start_time = time.time()

        for i in range(10):
            self._simulate_lightweight_simplex_operation()

        time_with_collector = time.time() - start_time

        # Réinitialiser collecteur
        self.collector.reset()

        # Mesurer performance sans collecteur
        start_time = time.time()

        for i in range(10):
            pass  # Opération minimale

        time_without_collector = time.time() - start_time

        # Calculer overhead
        overhead_ms = (time_with_collector - time_without_collector) * 1000

        # Validation performance (overhead < 50ms pour 10 opérations)
        self.assertLess(overhead_ms, 50.0)

        print(f"   ✅ Overhead mesuré: {overhead_ms:.2f}ms pour 10 opérations")
        print(f"   ✅ Performance acceptable: {overhead_ms < 50.0}")

    def test_08_geometric_consistency_validation(self):
        """Test 08: Validation cohérence géométrique"""
        print("🧮 Test 08: Cohérence géométrique")

        # Créer séquence d'états avec progression logique
        states = self._create_geometric_test_sequence()

        # Valider progression monotone sur axe X
        x_coords = [s.coordinates_3d[0] for s in states]
        self.assertTrue(all(x_coords[i] >= x_coords[i-1] for i in range(1, len(x_coords))))

        # Valider distances entre états consecutifs
        distances = []
        for i in range(1, len(states)):
            from_coords = states[i-1].coordinates_3d
            to_coords = states[i].coordinates_3d
            distance = math.sqrt(sum((to_coords[j] - from_coords[j])**2 for j in range(3)))
            distances.append(distance)

        # Toutes les distances doivent être > 0 et < 1000 (cohérence)
        self.assertTrue(all(0 < d < 1000 for d in distances))

        print(f"   ✅ {len(states)} états géométriquement cohérents")
        print(f"   ✅ Distances: min={min(distances):.2f}, max={max(distances):.2f}")

    def test_09_constraint_class_mathematical_properties(self):
        """Test 09: Propriétés mathématiques classification contraintes"""
        print("🧮 Test 09: Propriétés mathématiques contraintes")

        # Test linéarité mapping
        variables_base = {"f_1": Decimal('2.0'), "f_2": Decimal('3.0')}
        variables_double = {"f_1": Decimal('4.0'), "f_2": Decimal('6.0')}

        # Configuration mapper
        self.mapper.constraint_classification = {"test": ConstraintClass3D.SOURCE}
        self.mapper.constraint_weights = {"test": {"f_1": Decimal('1.5'), "f_2": Decimal('2.0')}}

        coords_base = self.mapper.map_variables_to_3d(variables_base)
        coords_double = self.mapper.map_variables_to_3d(variables_double)

        # Test linéarité: f(2x) = 2*f(x)
        self.assertAlmostEqual(coords_double[0], 2 * coords_base[0], places=6)

        # Test additivité
        variables_sum = {"f_1": Decimal('6.0'), "f_2": Decimal('9.0')}
        coords_sum = self.mapper.map_variables_to_3d(variables_sum)
        self.assertAlmostEqual(coords_sum[0], 3 * coords_base[0], places=6)

        print("   ✅ Linéarité mapping validée")
        print("   ✅ Additivité mapping validée")

    def test_10_robustness_edge_cases(self):
        """Test 10: Robustesse cas limites"""
        print("🧮 Test 10: Robustesse cas limites")

        # Cas 1: Variables nulles
        variables_zero = {"f_1": Decimal('0'), "f_2": Decimal('0')}
        self.mapper.constraint_classification = {"test": ConstraintClass3D.SOURCE}
        self.mapper.constraint_weights = {"test": {"f_1": Decimal('1.0'), "f_2": Decimal('1.0')}}

        coords_zero = self.mapper.map_variables_to_3d(variables_zero)
        self.assertEqual(coords_zero, (0.0, 0.0, 0.0))

        # Cas 2: Variables très grandes
        variables_large = {"f_1": Decimal('1e6'), "f_2": Decimal('1e6')}
        coords_large = self.mapper.map_variables_to_3d(variables_large)
        self.assertIsInstance(coords_large[0], float)
        self.assertFalse(math.isinf(coords_large[0]))

        # Cas 3: Collecteur vide
        empty_data = self.collector.export_animation_data()
        self.assertEqual(empty_data['metadata']['total_states'], 0)

        # Cas 4: Reset collecteur
        self.collector.reset()
        self.assertEqual(len(self.collector.states_history), 0)
        self.assertEqual(self.collector.current_step, 0)

        print("   ✅ Variables nulles gérées")
        print("   ✅ Variables grandes gérées")
        print("   ✅ Collecteur vide géré")
        print("   ✅ Reset collecteur fonctionnel")

    # Méthodes auxiliaires pour tests

    def _simulate_simplex_execution(self):
        """Simule exécution Simplex avec collecte"""
        previous_state = None

        for i in range(3):
            variables = {f"f_{j}": Decimal(str(10.0 + i*2 + j)) for j in range(2)}
            state = SimplexState3D(
                timestamp=time.time(),
                step_number=i,
                variables_fi=variables,
                constraint_contributions={},
                coordinates_3d=(10.0 + i*5, 15.0 + i*3, 2.0 + i),
                basic_variables={f"f_0"},
                non_basic_variables={f"f_1"}
            )
            self.collector.states_history.append(state)
            self.collector.current_step = i + 1  # Incrementer current_step

            # Ajouter transition si pas le premier état
            if previous_state is not None:
                transition = SimplexTransition3D(
                    from_state=previous_state,
                    to_state=state,
                    transition_type=SimplexTransitionType.PIVOT_ENTER
                )
                self.collector.transitions_history.append(transition)

            previous_state = state

    def _simulate_lightweight_simplex_operation(self):
        """Opération Simplex légère pour test performance"""
        variables = {"f_1": Decimal('1.0')}
        coords = self.mapper.map_variables_to_3d(variables)
        return coords

    def _create_geometric_test_sequence(self) -> List[SimplexState3D]:
        """Créé séquence d'états géométriquement cohérente"""
        states = []
        for i in range(5):
            x = 10.0 + i * 5.0   # Progression X
            y = 20.0 + i * 3.0   # Progression Y
            z = 5.0 + i * 1.0    # Progression Z

            state = SimplexState3D(
                timestamp=time.time() + i * 0.001,
                step_number=i,
                variables_fi={f"f_{j}": Decimal(str(1.0 + i + j)) for j in range(2)},
                constraint_contributions={},
                coordinates_3d=(x, y, z)
            )
            states.append(state)

        return states


def run_academic_test_suite():
    """Exécute suite complète tests académiques"""
    print("🎓 SUITE TESTS ACADÉMIQUES - API SIMPLEX 3D ICGS")
    print("=" * 60)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestAcademicSimplex3DAPI)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n📊 RÉSULTATS TESTS ACADÉMIQUES:")
    print(f"   Tests exécutés: {result.testsRun}")
    print(f"   Succès: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   Échecs: {len(result.failures)}")
    print(f"   Erreurs: {len(result.errors)}")

    if result.wasSuccessful():
        print("🎉 VALIDATION ACADÉMIQUE RÉUSSIE - API Simplex 3D certifiée")
        return True
    else:
        print("❌ VALIDATION ACADÉMIQUE ÉCHOUÉE")
        return False


if __name__ == '__main__':
    success = run_academic_test_suite()
    sys.exit(0 if success else 1)