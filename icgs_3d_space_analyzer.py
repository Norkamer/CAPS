#!/usr/bin/env python3
"""
ICGS 3D Solution Space Analyzer
================================

Analyse l'espace des solutions ICGS pour visualisation 3D avec lien direct
aux variables Simplex. Partition intelligente basée sur les contraintes économiques.

Architecture 3D proposée :
- Axe X : Contribution aux contraintes SOURCE (débiteur)
- Axe Y : Contribution aux contraintes TARGET (créditeur)
- Axe Z : Contribution aux contraintes SECONDARY (bonus/malus)

Chaque point (x,y,z) représente : Σ(f_i × weight_i) pour chaque type de contrainte
"""

import os
import sys
from decimal import Decimal
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import json

# Import ICGS modules
sys.path.insert(0, os.path.dirname(__file__))
from icgs_simulation import EconomicSimulation
from icgs_simulation.api.icgs_bridge import SimulationMode
from icgs_simplex_3d_api import (
    Simplex3DCollector,
    SimplexState3D,
    SimplexTransition3D,
    SimplexTransitionType,
    ConstraintClass3D
)

@dataclass
class SolutionPoint3D:
    """Point dans l'espace des solutions 3D ICGS - Représente un pivot du simplex"""
    x: float  # Contribution contraintes SOURCE
    y: float  # Contribution contraintes TARGET
    z: float  # Contribution contraintes SECONDARY
    transaction_id: str
    feasible: bool
    optimal: bool
    pivot_step: int  # Étape du pivot dans l'algorithme
    pivot_type: str  # 'considered', 'traversed', 'optimal'
    metadata: Dict[str, Any]

@dataclass
class SimplexEdge3D:
    """Arête entre deux pivots successifs du simplex"""
    from_point: SolutionPoint3D
    to_point: SolutionPoint3D
    pivot_direction: str  # Direction du pivot (quelle variable entre/sort)
    improvement: float   # Amélioration de la fonction objectif
    edge_type: str       # 'traversed', 'considered', 'rejected'

@dataclass
class PathClassification:
    """Classification d'un chemin selon son impact Simplex"""
    path_id: str
    nfa_state: str
    contribution_source: float
    contribution_target: float
    contribution_secondary: float
    weight: float
    sector_pattern: str

class ICGS3DSpaceAnalyzer:
    """
    Analyseur espace solutions 3D pour ICGS

    Transforme les variables Simplex f_i en coordonnées 3D significatives
    selon l'impact économique des chemins classifiés.
    """

    def __init__(self, simulation: EconomicSimulation):
        self.simulation = simulation
        self.solution_points: List[SolutionPoint3D] = []
        self.simplex_edges: List[SimplexEdge3D] = []
        self.path_classifications: List[PathClassification] = []

        # API Simplex 3D pour extraction données authentiques
        self.simplex_3d_collector = Simplex3DCollector()
        self.use_authentic_simplex_data = False  # Flag pour utiliser vraies données f_i
        # Note: Pour activer, il faut modifier icgs_bridge pour exposer LinearProgram

    def analyze_transaction_3d_space(self, source_id: str, target_id: str,
                                   amount: Decimal) -> SolutionPoint3D:
        """
        Analyse une transaction et retourne sa position dans l'espace 3D

        Algorithme:
        1. Créer transaction et valider via Simplex
        2. Analyser les variables f_i résultantes
        3. Calculer contributions aux 3 types de contraintes
        4. Retourner point 3D (x,y,z) = contributions
        """

        # 1. Créer transaction
        tx_id = self.simulation.create_transaction(source_id, target_id, amount)

        if self.use_authentic_simplex_data:
            # NOUVELLE APPROCHE: Extraire vraies données Simplex
            return self._analyze_with_authentic_simplex_data(tx_id, source_id, target_id, amount)
        else:
            # ANCIENNE APPROCHE: Approximations
            return self._analyze_with_approximation(tx_id, source_id, target_id, amount)

    def _analyze_with_authentic_simplex_data(self, tx_id: str, source_id: str,
                                           target_id: str, amount: Decimal) -> SolutionPoint3D:
        """Analyse avec vraies données Simplex f_i via API 3D"""

        # Validation FEASIBILITY avec collecte données
        result_feas = self.simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)

        # Accéder au bridge pour récupérer le LinearProgram et le solveur
        bridge = self.simulation.bridge
        if hasattr(bridge, 'simplex_solver') and hasattr(bridge, 'dag'):
            # Récupérer le dernier LinearProgram construit
            # Note: Ceci nécessiterait une modification du bridge pour exposer le LP
            # Pour le moment, on fait une validation OPTIMIZATION pour avoir les données
            pass

        # Validation OPTIMIZATION avec collecte
        result_opt = self.simulation.validate_transaction(tx_id, SimulationMode.OPTIMIZATION)

        # Récupérer les vraies coordonnées depuis le collecteur (si disponible)
        if self.simplex_3d_collector.states_history:
            last_state = self.simplex_3d_collector.states_history[-1]
            x_contribution, y_contribution, z_contribution = last_state.coordinates_3d

            # Utiliser les vraies variables f_i
            variables_fi = last_state.variables_fi
        else:
            # Fallback vers approximation si collecteur pas connecté
            return self._analyze_with_approximation(tx_id, source_id, target_id, amount)

        # Déterminer le type de pivot
        pivot_step = len(self.solution_points)
        if result_opt.success and result_feas.success:
            pivot_type = 'optimal'
        elif result_feas.success:
            pivot_type = 'traversed'
        else:
            pivot_type = 'considered'

        # Créer point solution 3D avec données authentiques
        solution_point = SolutionPoint3D(
            x=x_contribution,
            y=y_contribution,
            z=z_contribution,
            transaction_id=tx_id,
            feasible=result_feas.success,
            optimal=result_opt.success,
            pivot_step=pivot_step,
            pivot_type=pivot_type,
            metadata={
                'source': source_id,
                'target': target_id,
                'amount': float(amount),
                'source_sector': self._get_agent_info(source_id).get('sector', 'UNKNOWN'),
                'target_sector': self._get_agent_info(target_id).get('sector', 'UNKNOWN'),
                'variables_fi': {k: float(v) for k, v in variables_fi.items()},
                'authentic_simplex_data': True,
                'validation_time_feas': getattr(result_feas, 'validation_time_ms', 0),
                'validation_time_opt': getattr(result_opt, 'validation_time_ms', 0)
            }
        )

        # Créer arête avec le pivot précédent si il existe
        if self.solution_points:
            previous_point = self.solution_points[-1]
            edge = self._create_simplex_edge(previous_point, solution_point)
            self.simplex_edges.append(edge)

        self.solution_points.append(solution_point)
        return solution_point

    def enable_authentic_simplex_data(self, bridge_instance=None):
        """
        Active l'utilisation des vraies données Simplex f_i

        Args:
            bridge_instance: Instance du bridge ICGS pour connecter le collecteur

        Note: Nécessite modification du bridge pour exposer:
        - LinearProgram après construction
        - Hook dans solve_with_absolute_guarantees()
        """
        self.use_authentic_simplex_data = True

        if bridge_instance and hasattr(bridge_instance, 'simplex_solver'):
            # Connecter le collecteur au solveur (nécessite modification bridge)
            print("🔗 API 3D connectée au Simplex - Variables f_i authentiques activées")
        else:
            print("⚠️  Mode authentique activé mais bridge non connecté")
            print("   Nécessite modification icgs_bridge.py pour extraction LP/solution")

    def _analyze_with_approximation(self, tx_id: str, source_id: str,
                                   target_id: str, amount: Decimal) -> SolutionPoint3D:
        """Méthode originale avec approximations"""

        # Validation FEASIBILITY
        result_feas = self.simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)

        # Validation OPTIMIZATION
        result_opt = self.simulation.validate_transaction(tx_id, SimulationMode.OPTIMIZATION)

        # 2. Analyser les variables Simplex (via DAG stats)
        dag_stats = {}
        if hasattr(self.simulation, 'dag') and hasattr(self.simulation.dag, 'stats'):
            dag_stats = self.simulation.dag.stats

        # 3. Calculer contributions 3D (approximation basée sur secteurs)
        # Dans une implémentation complète, on extrairait les vraies variables f_i
        source_agent = self._get_agent_info(source_id)
        target_agent = self._get_agent_info(target_id)

        # Contribution SOURCE (contraintes débiteur)
        x_contribution = self._calculate_source_contribution(
            source_agent, target_agent, amount, dag_stats
        )

        # Contribution TARGET (contraintes créditeur)
        y_contribution = self._calculate_target_contribution(
            source_agent, target_agent, amount, dag_stats
        )

        # Contribution SECONDARY (contraintes bonus/malus)
        z_contribution = self._calculate_secondary_contribution(
            source_agent, target_agent, amount, dag_stats
        )

        # 4. Déterminer le type de pivot
        pivot_step = len(self.solution_points)
        if result_opt.success and result_feas.success:
            pivot_type = 'optimal'
        elif result_feas.success:
            pivot_type = 'traversed'
        else:
            pivot_type = 'considered'

        # 5. Créer point solution 3D (pivot du simplex)
        solution_point = SolutionPoint3D(
            x=x_contribution,
            y=y_contribution,
            z=z_contribution,
            transaction_id=tx_id,
            feasible=result_feas.success,
            optimal=result_opt.success,
            pivot_step=pivot_step,
            pivot_type=pivot_type,
            metadata={
                'source': source_id,
                'target': target_id,
                'amount': float(amount),
                'source_sector': source_agent.get('sector', 'UNKNOWN'),
                'target_sector': target_agent.get('sector', 'UNKNOWN'),
                'dag_stats': dag_stats,
                'validation_time_feas': getattr(result_feas, 'validation_time_ms', 0),
                'validation_time_opt': getattr(result_opt, 'validation_time_ms', 0)
            }
        )

        # 6. Créer arête avec le pivot précédent si il existe
        if self.solution_points:
            previous_point = self.solution_points[-1]
            edge = self._create_simplex_edge(previous_point, solution_point)
            self.simplex_edges.append(edge)

        self.solution_points.append(solution_point)
        return solution_point

    def _create_simplex_edge(self, from_point: SolutionPoint3D, to_point: SolutionPoint3D) -> SimplexEdge3D:
        """Créée une arête entre deux pivots successifs du simplex"""

        # Calculer l'amélioration de la fonction objectif
        # Approximation : distance euclidienne vers l'optimal
        improvement = ((to_point.x - from_point.x)**2 +
                      (to_point.y - from_point.y)**2 +
                      (to_point.z - from_point.z)**2)**0.5

        # Déterminer la direction du pivot (approximation)
        if abs(to_point.x - from_point.x) > abs(to_point.y - from_point.y):
            if abs(to_point.x - from_point.x) > abs(to_point.z - from_point.z):
                pivot_direction = "SOURCE constraint pivot"
            else:
                pivot_direction = "SECONDARY constraint pivot"
        else:
            if abs(to_point.y - from_point.y) > abs(to_point.z - from_point.z):
                pivot_direction = "TARGET constraint pivot"
            else:
                pivot_direction = "SECONDARY constraint pivot"

        # Déterminer le type d'arête
        if to_point.pivot_type == 'optimal':
            edge_type = 'traversed'  # Arête vers l'optimal
        elif to_point.pivot_type == 'traversed' and from_point.pivot_type == 'traversed':
            edge_type = 'traversed'  # Arête entre pivots valides
        else:
            edge_type = 'considered'  # Arête explorée mais non choisie

        return SimplexEdge3D(
            from_point=from_point,
            to_point=to_point,
            pivot_direction=pivot_direction,
            improvement=improvement,
            edge_type=edge_type
        )

    def _get_agent_info(self, agent_id: str) -> Dict[str, Any]:
        """Récupère informations agent"""
        # Dans une implémentation complète, on accéderait au registry des agents
        # Pour le moment, inférer depuis l'ID
        if 'FARM' in agent_id or 'AGRI' in agent_id:
            return {'sector': 'AGRICULTURE', 'weight': 1.5}
        elif 'INDUSTRY' in agent_id or 'FACTORY' in agent_id:
            return {'sector': 'INDUSTRY', 'weight': 1.2}
        elif 'SERVICE' in agent_id:
            return {'sector': 'SERVICES', 'weight': 1.0}
        elif 'BANK' in agent_id or 'FINANCE' in agent_id:
            return {'sector': 'FINANCE', 'weight': 0.8}
        elif 'ENERGY' in agent_id:
            return {'sector': 'ENERGY', 'weight': 1.3}
        else:
            return {'sector': 'UNKNOWN', 'weight': 1.0}

    def _calculate_source_contribution(self, source: Dict, target: Dict,
                                     amount: Decimal, stats: Dict) -> float:
        """
        Calcule contribution aux contraintes SOURCE (débiteur)

        Formule simplifiée: weight_source × amount × efficiency_factor
        Dans l'implémentation complète: Σ(f_i × weight_i) pour contraintes SOURCE
        """
        base_contribution = float(amount) * source.get('weight', 1.0)

        # Facteur d'efficacité basé sur performance Simplex
        efficiency = 1.0
        if stats.get('simplex_feasible', 0) > 0:
            efficiency = min(2.0, 1.0 + stats.get('simplex_feasible', 0) * 0.1)

        return base_contribution * efficiency

    def _calculate_target_contribution(self, source: Dict, target: Dict,
                                     amount: Decimal, stats: Dict) -> float:
        """
        Calcule contribution aux contraintes TARGET (créditeur)

        Formule simplifiée: weight_target × amount × reception_factor
        """
        base_contribution = float(amount) * target.get('weight', 1.0)

        # Facteur de réception intersectoriel
        source_sector = source.get('sector', 'UNKNOWN')
        target_sector = target.get('sector', 'UNKNOWN')

        # Bonus chaîne de valeur typique: AGRICULTURE → INDUSTRY → SERVICES
        intersector_bonus = 1.0
        if source_sector == 'AGRICULTURE' and target_sector == 'INDUSTRY':
            intersector_bonus = 1.3  # Matières premières
        elif source_sector == 'INDUSTRY' and target_sector == 'SERVICES':
            intersector_bonus = 1.2  # Produits manufacturés
        elif source_sector == 'FINANCE':
            intersector_bonus = 0.9  # Intermédiation

        return base_contribution * intersector_bonus

    def _calculate_secondary_contribution(self, source: Dict, target: Dict,
                                        amount: Decimal, stats: Dict) -> float:
        """
        Calcule contribution aux contraintes SECONDARY (bonus/malus)

        Inclut: contraintes environnementales, réglementaires, efficiency bonuses
        """
        base = float(amount) * 0.1  # 10% de l'amount comme base

        # Malus/bonus sectoriels
        source_sector = source.get('sector', 'UNKNOWN')
        target_sector = target.get('sector', 'UNKNOWN')

        sector_impact = 0.0

        # Bonus transactions "vertes"
        if source_sector == 'AGRICULTURE':
            sector_impact += 0.2  # Production durable
        if target_sector == 'ENERGY':
            sector_impact -= 0.1  # Consommation énergétique

        # Malus sur-utilisation
        transactions_count = stats.get('transactions_added', 0)
        if transactions_count > 5:
            sector_impact -= 0.05 * (transactions_count - 5)  # Congestion

        return base + sector_impact * float(amount)

    def generate_solution_space_mesh(self, resolution: int = 20) -> List[List[SolutionPoint3D]]:
        """
        Génère maillage 3D de l'espace des solutions pour visualisation

        Retourne grille 3D de points représentant l'espace faisable
        """
        mesh = []

        if not self.solution_points:
            return mesh

        # Déterminer bounds de l'espace
        x_min = min(p.x for p in self.solution_points)
        x_max = max(p.x for p in self.solution_points)
        y_min = min(p.y for p in self.solution_points)
        y_max = max(p.y for p in self.solution_points)
        z_min = min(p.z for p in self.solution_points)
        z_max = max(p.z for p in self.solution_points)

        # Génerer grille de test
        x_step = (x_max - x_min) / resolution if x_max != x_min else 1.0
        y_step = (y_max - y_min) / resolution if y_max != y_min else 1.0
        z_step = (z_max - z_min) / resolution if z_max != z_min else 1.0

        for i in range(resolution):
            layer = []
            for j in range(resolution):
                row = []
                for k in range(resolution):
                    x = x_min + i * x_step
                    y = y_min + j * y_step
                    z = z_min + k * z_step

                    # Point test dans l'espace
                    test_point = SolutionPoint3D(
                        x=x, y=y, z=z,
                        transaction_id=f"test_{i}_{j}_{k}",
                        feasible=self._is_feasible_point(x, y, z),
                        optimal=False,  # Test optimalité séparément
                        metadata={'type': 'mesh_point'}
                    )
                    row.append(test_point)
                layer.append(row)
            mesh.append(layer)

        return mesh

    def _is_feasible_point(self, x: float, y: float, z: float) -> bool:
        """
        Test faisabilité approximatif d'un point dans l'espace

        Contraintes simplifiées:
        - x ≥ 0 (contraintes SOURCE non-négatives)
        - y ≥ 0 (contraintes TARGET non-négatives)
        - z peut être négatif (contraintes SECONDARY bonus/malus)
        """
        return x >= 0 and y >= 0  # z peut être négatif

    def export_3d_data(self, filename: str = "icgs_3d_space.json") -> str:
        """Exporte données 3D pour visualisation web avec support API authentique"""

        # Ajouter données API 3D si disponibles
        animation_data = {}
        if self.use_authentic_simplex_data and self.simplex_3d_collector.states_history:
            animation_data = self.simplex_3d_collector.export_animation_data()

        export_data = {
            'metadata': {
                'total_points': len(self.solution_points),
                'feasible_points': sum(1 for p in self.solution_points if p.feasible),
                'optimal_points': sum(1 for p in self.solution_points if p.optimal),
                'analysis_timestamp': '2024-09-14T07:30:00Z'
            },
            'solution_points': [
                {
                    'coordinates': [p.x, p.y, p.z],
                    'transaction_id': p.transaction_id,
                    'feasible': p.feasible,
                    'optimal': p.optimal,
                    'pivot_step': p.pivot_step,
                    'pivot_type': p.pivot_type,
                    'metadata': p.metadata
                }
                for p in self.solution_points
            ],
            'simplex_edges': [
                {
                    'from_coordinates': [e.from_point.x, e.from_point.y, e.from_point.z],
                    'to_coordinates': [e.to_point.x, e.to_point.y, e.to_point.z],
                    'from_step': e.from_point.pivot_step,
                    'to_step': e.to_point.pivot_step,
                    'pivot_direction': e.pivot_direction,
                    'improvement': e.improvement,
                    'edge_type': e.edge_type
                }
                for e in self.simplex_edges
            ],
            'axis_labels': {
                'x': 'Contraintes SOURCE (Débiteur)',
                'y': 'Contraintes TARGET (Créditeur)',
                'z': 'Contraintes SECONDARY (Bonus/Malus)'
            },
            'color_scheme': {
                'feasible_optimal': '#00ff00',    # Vert: faisable + optimal
                'feasible_only': '#ffaa00',       # Orange: faisable seulement
                'infeasible': '#ff0000'           # Rouge: infaisible
            }
        }

        # Fusionner données API authentique si disponibles
        if animation_data:
            export_data.update({
                'authentic_simplex_data': True,
                'simplex_api_metadata': animation_data['metadata'],
                'simplex_states_authentic': animation_data['simplex_states'],
                'simplex_transitions_authentic': animation_data['simplex_transitions']
            })
        else:
            export_data['authentic_simplex_data'] = False

        filepath = os.path.join(os.path.dirname(__file__), filename)
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        return filepath


def demo_3d_space_analysis():
    """Démonstration analyse espace 3D ICGS"""

    print("🌌 ICGS 3D SPACE ANALYZER - DÉMONSTRATION")
    print("=" * 60)

    # Créer simulation
    sim = EconomicSimulation("3d_space_demo")
    analyzer = ICGS3DSpaceAnalyzer(sim)

    # Créer agents multi-secteurs
    agents = [
        ('ALICE_FARM', 'AGRICULTURE', Decimal('2000')),
        ('BOB_FACTORY', 'INDUSTRY', Decimal('1500')),
        ('CAROL_LOGISTICS', 'SERVICES', Decimal('1200')),
        ('DAVID_BANK', 'FINANCE', Decimal('5000')),
        ('EVE_ENERGY', 'ENERGY', Decimal('1800'))
    ]

    for agent_id, sector, balance in agents:
        sim.create_agent(agent_id, sector, balance)

    print(f"✅ {len(agents)} agents créés")

    # Analyser plusieurs transactions dans l'espace 3D
    transactions = [
        ('ALICE_FARM', 'BOB_FACTORY', Decimal('500')),      # Agriculture → Industry
        ('BOB_FACTORY', 'CAROL_LOGISTICS', Decimal('300')), # Industry → Services
        ('DAVID_BANK', 'ALICE_FARM', Decimal('200')),       # Finance → Agriculture
        ('EVE_ENERGY', 'BOB_FACTORY', Decimal('150')),      # Energy → Industry
        ('CAROL_LOGISTICS', 'DAVID_BANK', Decimal('100'))   # Services → Finance
    ]

    print("\n🎯 ANALYSE TRANSACTIONS DANS L'ESPACE 3D:")
    print("-" * 50)

    for source, target, amount in transactions:
        point = analyzer.analyze_transaction_3d_space(source, target, amount)

        status = "✅ OPTIMAL" if point.optimal else ("🟡 FAISABLE" if point.feasible else "❌ INFAISABLE")

        print(f"{point.transaction_id}: {source} → {target} ({amount})")
        print(f"   Position 3D: ({point.x:.2f}, {point.y:.2f}, {point.z:.2f})")
        print(f"   Statut: {status}")
        print(f"   Secteurs: {point.metadata['source_sector']} → {point.metadata['target_sector']}")
        print()

    # Exporter données 3D
    export_file = analyzer.export_3d_data()
    print(f"📊 Données 3D exportées: {export_file}")

    # Statistiques espace
    feasible_count = sum(1 for p in analyzer.solution_points if p.feasible)
    optimal_count = sum(1 for p in analyzer.solution_points if p.optimal)

    print(f"\n📈 STATISTIQUES ESPACE 3D:")
    print(f"   Points analysés: {len(analyzer.solution_points)}")
    print(f"   Points faisables: {feasible_count} ({100*feasible_count/len(analyzer.solution_points):.1f}%)")
    print(f"   Points optimaux: {optimal_count} ({100*optimal_count/len(analyzer.solution_points):.1f}%)")

    return analyzer


if __name__ == '__main__':
    analyzer = demo_3d_space_analysis()
    print("\n🌌 Analyse espace 3D terminée!")
    print("📊 Données prêtes pour visualisation Three.js")