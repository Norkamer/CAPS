#!/usr/bin/env python3
"""
ICGS SVG Animator - Moteur d'Animation SVG Paramétrable
========================================================

Moteur principal pour génération d'animations SVG à partir des données ICGS.
Intègre avec le système de simulation 65 agents et fournit des animations
paramétrables pour visualisation des flux économiques et algorithmes Simplex.

Usage:
    from icgs_svg_animator import ICGSSVGAnimator
    from svg_templates import SVGConfig

    config = SVGConfig(width=1200, height=800, animation_duration=3.0)
    animator = ICGSSVGAnimator(config)

    # Animation économie complète
    svg_content = animator.create_economy_animation(economy_data)

    # Animation transaction spécifique
    svg_content = animator.create_transaction_animation(transaction_data)

    # Animation Simplex
    svg_content = animator.create_simplex_animation(simplex_data)
"""

import sys
import os
import json
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from decimal import Decimal

# Import templates locaux
from svg_templates import ICGSSVGTemplates, SVGConfig

# Import simulation ICGS
sys.path.insert(0, os.path.dirname(__file__))
try:
    from icgs_simulation.api.icgs_bridge import EconomicSimulation, SimulationMode
    ICGS_AVAILABLE = True
except ImportError:
    ICGS_AVAILABLE = False
    print("⚠️  ICGS simulation not available, using mock data")


@dataclass
class AnimationParams:
    """Paramètres spécifiques pour types d'animation"""
    # Paramètres économie
    show_sector_boundaries: bool = True
    show_transaction_flows: bool = True
    show_performance_metrics: bool = True
    max_transactions_displayed: int = 20

    # Paramètres Simplex
    show_constraints: bool = True
    show_optimization_path: bool = True
    show_vertices: bool = True
    animate_convergence: bool = True

    # Paramètres temporels
    timeline_mode: bool = False
    time_window_seconds: Optional[float] = None


class ICGSSVGAnimator:
    """Moteur d'animation SVG pour visualisations ICGS"""

    def __init__(self, config: Optional[SVGConfig] = None,
                 animation_params: Optional[AnimationParams] = None):
        self.config = config or SVGConfig()
        self.params = animation_params or AnimationParams()
        self.templates = ICGSSVGTemplates(self.config)

        # Cache pour optimisation
        self._sector_positions_cache = {}
        self._agent_positions_cache = {}

        # Statistiques génération
        self.generation_stats = {
            'animations_created': 0,
            'total_generation_time': 0.0,
            'last_generation_time': 0.0,
            'cache_hits': 0
        }

    def create_economy_animation(self, economy_data: Dict[str, Any],
                                animation_type: str = "complete") -> str:
        """
        Crée animation SVG de l'économie 65 agents

        Args:
            economy_data: Données économie du système ICGS
            animation_type: "complete", "sectors_only", "flows_only", "metrics_only"

        Returns:
            Contenu SVG complet de l'animation
        """
        start_time = time.time()

        try:
            if animation_type == "complete":
                svg_content = self._create_complete_economy_animation(economy_data)
            elif animation_type == "sectors_only":
                svg_content = self._create_sectors_only_animation(economy_data)
            elif animation_type == "flows_only":
                svg_content = self._create_flows_only_animation(economy_data)
            elif animation_type == "metrics_only":
                svg_content = self._create_metrics_only_animation(economy_data)
            else:
                raise ValueError(f"Unknown animation type: {animation_type}")

            self._update_generation_stats(start_time)
            return svg_content

        except Exception as e:
            print(f"❌ Erreur génération animation économie: {e}")
            return self._create_error_animation(str(e))

    def create_transaction_animation(self, transaction_data: Dict[str, Any],
                                   context_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Crée animation SVG pour une transaction spécifique

        Args:
            transaction_data: Données transaction (tx_id, source, target, amount, etc.)
            context_data: Données contextuelles (agents, secteurs)

        Returns:
            Animation SVG focalisée sur la transaction
        """
        start_time = time.time()

        try:
            # Données transaction
            tx_id = transaction_data.get('tx_id', 'unknown')
            source_id = transaction_data.get('source_id', '')
            target_id = transaction_data.get('target_id', '')
            amount = transaction_data.get('amount', 0)

            # Validation pipeline
            feasibility = transaction_data.get('feasibility', {})
            optimization = transaction_data.get('optimization', {})

            # Position des agents source/target
            source_pos, target_pos = self._get_transaction_agent_positions(
                source_id, target_id, context_data
            )

            # Génération contenu animation
            content = self._generate_transaction_animation_content(
                tx_id, source_pos, target_pos, amount,
                feasibility, optimization, context_data
            )

            svg_content = self.templates.get_base_svg_structure(
                f"Transaction Animation - {tx_id}", content
            )

            self._update_generation_stats(start_time)
            return svg_content

        except Exception as e:
            print(f"❌ Erreur génération animation transaction: {e}")
            return self._create_error_animation(str(e))

    def create_simplex_animation(self, simplex_data: Dict[str, Any],
                               animation_style: str = "standard") -> str:
        """
        Crée animation SVG des étapes algorithme Simplex

        Args:
            simplex_data: Données Simplex (steps, constraints, optimal_solution)
            animation_style: "standard", "educational", "technical"

        Returns:
            Animation SVG du processus Simplex
        """
        start_time = time.time()

        try:
            # Extraction données Simplex
            steps = simplex_data.get('simplex_steps', [])
            constraints = simplex_data.get('constraints', [])
            optimal_solution = simplex_data.get('optimal_solution', {})

            # Conversion coordonnées 3D → 2D pour SVG
            vertices_2d = self._convert_simplex_to_2d(
                simplex_data.get('vertices', [])
            )

            optimal_point_2d = None
            if optimal_solution:
                optimal_point_2d = self._convert_point_to_2d(
                    optimal_solution.get('coordinates', [0, 0, 0])
                )

            # Génération contenu selon style
            if animation_style == "educational":
                content = self._generate_educational_simplex_content(
                    vertices_2d, steps, optimal_point_2d
                )
            elif animation_style == "technical":
                content = self._generate_technical_simplex_content(
                    vertices_2d, constraints, steps, optimal_point_2d
                )
            else:  # standard
                content = self._generate_standard_simplex_content(
                    vertices_2d, optimal_point_2d
                )

            # Construire titre dynamique avec transaction courante
            metadata = simplex_data.get('transaction_metadata', {})
            current_step = metadata.get('current_step')
            total_steps = metadata.get('total_steps', 33)

            if current_step and current_step.isdigit():
                title = f"Simplex Animation - Transaction {current_step}/{total_steps}"
            else:
                title = f"Simplex Animation - {animation_style.title()}"  # fallback

            svg_content = self.templates.get_base_svg_structure(title, content)

            self._update_generation_stats(start_time)
            return svg_content

        except Exception as e:
            print(f"❌ Erreur génération animation Simplex: {e}")
            return self._create_error_animation(str(e))

    def create_performance_dashboard(self, metrics_data: Dict[str, Any],
                                   timeline_data: Optional[List[Dict]] = None) -> str:
        """
        Crée dashboard SVG de performance avec métriques temps réel

        Args:
            metrics_data: Métriques actuelles du système
            timeline_data: Historique temporel optionnel

        Returns:
            Dashboard SVG interactif
        """
        start_time = time.time()

        try:
            # Métriques principales
            performance_section = self.templates.render_performance_metrics(
                metrics_data, x=50, y=100
            )

            # Timeline si fournie
            timeline_section = ""
            if timeline_data and self.params.timeline_mode:
                timeline_section = self._generate_timeline_visualization(timeline_data)

            # Gauges en temps réel
            gauges_section = self._generate_performance_gauges(metrics_data)

            # Indicateurs de santé système
            health_indicators = self._generate_system_health_indicators(metrics_data)

            content = f'''
    {performance_section}

    {timeline_section}

    {gauges_section}

    {health_indicators}

    <!-- Horodatage -->
    <text x="{self.config.width - 20}" y="{self.config.height - 20}"
          class="metric-label"
          text-anchor="end"
          style="font-size: 10px; opacity: 0.7;">
      Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
    </text>'''

            svg_content = self.templates.get_base_svg_structure(
                "ICGS Performance Dashboard", content
            )

            self._update_generation_stats(start_time)
            return svg_content

        except Exception as e:
            print(f"❌ Erreur génération dashboard: {e}")
            return self._create_error_animation(str(e))

    def export_animation_config(self) -> Dict[str, Any]:
        """Exporte configuration actuelle pour modification externe"""
        return {
            'svg_config': asdict(self.config),
            'animation_params': asdict(self.params),
            'generation_stats': self.generation_stats.copy()
        }

    def update_animation_config(self, new_config: Dict[str, Any]) -> bool:
        """Met à jour configuration à partir d'un dictionnaire externe"""
        try:
            if 'svg_config' in new_config:
                for key, value in new_config['svg_config'].items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)

            if 'animation_params' in new_config:
                for key, value in new_config['animation_params'].items():
                    if hasattr(self.params, key):
                        setattr(self.params, key, value)

            # Recréer templates avec nouvelle config
            self.templates = ICGSSVGTemplates(self.config)
            return True

        except Exception as e:
            print(f"❌ Erreur mise à jour configuration: {e}")
            return False

    # Méthodes privées d'implémentation

    def _create_complete_economy_animation(self, economy_data: Dict[str, Any]) -> str:
        """Génère animation économie complète"""
        return self.templates.render_complete_economy_animation(economy_data)

    def _create_sectors_only_animation(self, economy_data: Dict[str, Any]) -> str:
        """Génère animation secteurs uniquement"""
        content_width = self.config.width - 2 * self.config.margin
        content_height = self.config.height - 2 * self.config.margin

        # Positions secteurs
        sector_positions = self._calculate_sector_positions(content_width, content_height)

        # Génération clusters
        sector_clusters = []
        agents_distribution = economy_data.get('agents_distribution', {})

        for sector, position in sector_positions.items():
            sector_data = agents_distribution.get(sector, {})
            agents = sector_data.get('agents', [])
            if agents:
                x, y = position
                cluster = self.templates.render_sector_cluster(sector, agents, x, y)
                sector_clusters.append(cluster)

        return '\n'.join(sector_clusters)

    def _create_flows_only_animation(self, economy_data: Dict[str, Any]) -> str:
        """Génère animation flux uniquement"""
        transactions = economy_data.get('sample_results', [])[:self.params.max_transactions_displayed]
        sector_positions = self._calculate_sector_positions(
            self.config.width - 2 * self.config.margin,
            self.config.height - 2 * self.config.margin
        )

        flows = []
        for i, tx in enumerate(transactions):
            # Approximation positions pour demo
            source_sector = list(sector_positions.keys())[i % len(sector_positions)]
            target_sector = list(sector_positions.keys())[(i + 1) % len(sector_positions)]

            flow = self.templates.render_transaction_flow(
                sector_positions[source_sector],
                sector_positions[target_sector],
                tx.get('amount', 0),
                tx.get('feasibility', {}).get('success', True),
                tx.get('tx_id', f'tx_{i}')
            )
            flows.append(flow)

        return '\n'.join(flows)

    def _create_metrics_only_animation(self, economy_data: Dict[str, Any]) -> str:
        """Génère animation métriques uniquement"""
        return self.templates.render_performance_metrics(
            economy_data.get('performance_metrics', {})
        )

    def _get_transaction_agent_positions(self, source_id: str, target_id: str,
                                       context_data: Optional[Dict]) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Calcule positions des agents pour transaction"""
        # Position par défaut
        default_source = (200, 300)
        default_target = (600, 300)

        if not context_data:
            return default_source, default_target

        # Recherche dans données contextuelles
        agents = context_data.get('agents', [])
        source_pos = default_source
        target_pos = default_target

        for agent in agents:
            if agent.get('agent_id') == source_id:
                source_pos = (agent.get('x', 200), agent.get('y', 300))
            elif agent.get('agent_id') == target_id:
                target_pos = (agent.get('x', 600), agent.get('y', 300))

        return source_pos, target_pos

    def _generate_transaction_animation_content(self, tx_id: str,
                                              source_pos: Tuple[float, float],
                                              target_pos: Tuple[float, float],
                                              amount: float,
                                              feasibility: Dict, optimization: Dict,
                                              context_data: Optional[Dict]) -> str:
        """Génère contenu animation transaction"""
        # Agents source et target
        source_x, source_y = source_pos
        target_x, target_y = target_pos

        agents_elements = f'''
    <!-- Agent Source -->
    <circle cx="{source_x}" cy="{source_y}" r="15"
            fill="#3498DB" stroke="white" stroke-width="3"
            filter="url(#glow-effect)">
      <title>Source Agent</title>
    </circle>

    <!-- Agent Target -->
    <circle cx="{target_x}" cy="{target_y}" r="15"
            fill="#E74C3C" stroke="white" stroke-width="3"
            filter="url(#glow-effect)">
      <title>Target Agent</title>
    </circle>'''

        # Flux transaction
        flow_element = self.templates.render_transaction_flow(
            source_pos, target_pos, amount,
            feasibility.get('success', False), tx_id
        )

        # Panneau informations transaction
        info_panel = f'''
    <g id="transaction-info" transform="translate(50, 50)">
      <rect width="300" height="150" rx="15"
            fill="rgba(255,255,255,0.95)"
            stroke="rgba(0,0,0,0.1)" stroke-width="1"/>

      <text x="15" y="25" class="metric-label"
            style="font-weight: bold; font-size: 16px;">
        Transaction {tx_id}
      </text>

      <text x="15" y="50" class="metric-label">
        Amount: {amount:.2f}
      </text>

      <text x="15" y="75" class="metric-label"
            style="fill: {'#27AE60' if feasibility.get('success') else '#E74C3C'};">
        Feasibility: {'✓ SUCCESS' if feasibility.get('success') else '✗ FAILED'}
        ({feasibility.get('time_ms', 0):.1f}ms)
      </text>

      <text x="15" y="100" class="metric-label"
            style="fill: {'#27AE60' if optimization.get('success') else '#E74C3C'};">
        Optimization: {'✓ SUCCESS' if optimization.get('success') else '✗ FAILED'}
        ({optimization.get('time_ms', 0):.1f}ms)
      </text>

      <text x="15" y="125" class="metric-label" style="font-size: 10px;">
        Optimal Price: {optimization.get('optimal_price', 0):.4f}
      </text>
    </g>'''

        return f'''
    {agents_elements}
    {flow_element}
    {info_panel}

    <!-- Animation timeline -->
    <g id="animation-timeline" transform="translate(400, 450)">
      <rect width="350" height="20" fill="rgba(200,200,200,0.3)" rx="10"/>
      <rect width="0" height="20" fill="#3498DB" rx="10">
        <animate attributeName="width" from="0" to="350" dur="3s" fill="freeze"/>
      </rect>
      <text x="175" y="35" class="metric-label" text-anchor="middle">
        Transaction Validation Timeline
      </text>
    </g>'''

    def _convert_simplex_to_2d(self, vertices_3d: List[List[float]]) -> List[Tuple[float, float]]:
        """Convertit vertices 3D Simplex en coordonnées 2D pour SVG"""
        if not vertices_3d:
            # Vertices par défaut pour demo
            return [(100, 300), (300, 100), (500, 300), (300, 400)]

        vertices_2d = []
        content_width = self.config.width - 2 * self.config.margin
        content_height = self.config.height - 2 * self.config.margin

        for vertex in vertices_3d:
            if len(vertex) >= 2:
                # Projection simple 3D → 2D et mise à l'échelle
                x = self.config.margin + (vertex[0] + 1) * content_width / 4
                y = self.config.margin + (vertex[1] + 1) * content_height / 4
                vertices_2d.append((x, y))

        return vertices_2d

    def _convert_point_to_2d(self, point_3d: List[float]) -> Optional[Tuple[float, float]]:
        """Convertit point 3D en coordonnées 2D"""
        if len(point_3d) < 2:
            return None

        content_width = self.config.width - 2 * self.config.margin
        content_height = self.config.height - 2 * self.config.margin

        x = self.config.margin + (point_3d[0] + 1) * content_width / 4
        y = self.config.margin + (point_3d[1] + 1) * content_height / 4

        return (x, y)

    def _generate_standard_simplex_content(self, vertices_2d: List[Tuple[float, float]],
                                         optimal_point: Optional[Tuple[float, float]]) -> str:
        """Génère contenu Simplex standard"""
        return self.templates.render_simplex_polytope(vertices_2d, [], optimal_point)

    def _generate_educational_simplex_content(self, vertices_2d: List[Tuple[float, float]],
                                            steps: List[Dict],
                                            optimal_point: Optional[Tuple[float, float]]) -> str:
        """Génère contenu Simplex éducatif avec étapes"""
        base_content = self.templates.render_simplex_polytope(vertices_2d, [], optimal_point)

        # Ajout annotations éducatives
        educational_annotations = '''
    <g id="educational-annotations">
      <text x="50" y="500" class="metric-label" style="font-weight: bold;">
        Algorithme Simplex - Étapes:
      </text>

      <text x="50" y="525" class="metric-label" style="font-size: 11px;">
        1. Identification région faisable (polytope)
      </text>

      <text x="50" y="545" class="metric-label" style="font-size: 11px;">
        2. Recherche sommets optimaux
      </text>

      <text x="50" y="565" class="metric-label" style="font-size: 11px;">
        3. Convergence vers solution optimale
      </text>
    </g>'''

        return base_content + educational_annotations

    def _generate_technical_simplex_content(self, vertices_2d: List[Tuple[float, float]],
                                          constraints: List[Dict],
                                          steps: List[Dict],
                                          optimal_point: Optional[Tuple[float, float]]) -> str:
        """Génère contenu Simplex technique détaillé avec métriques réelles"""
        base_content = self.templates.render_simplex_polytope(vertices_2d, constraints, optimal_point)

        # Extraction métriques avancées depuis steps si disponibles
        real_data_indicators = self._extract_real_data_indicators(steps)

        # Panneau technique étendu avec nouvelles métriques
        technical_panel = f'''
    <g id="technical-panel" transform="translate(500, 50)">
      <rect width="280" height="280" rx="10"
            fill="rgba(0,0,0,0.8)" stroke="rgba(255,255,255,0.3)"/>

      <text x="15" y="25" class="metric-label"
            style="fill: white; font-weight: bold;">
        Technical Data {real_data_indicators['source_indicator']}
      </text>

      <!-- Métriques principales -->
      <text x="15" y="50" class="metric-label" style="fill: white; font-size: 11px;">
        Vertices: {len(vertices_2d)}
      </text>

      <text x="15" y="70" class="metric-label" style="fill: white; font-size: 11px;">
        Constraints: {len(constraints)}
      </text>

      <text x="15" y="90" class="metric-label" style="fill: white; font-size: 11px;">
        Algorithm Steps: {len(steps)}
      </text>

      <!-- Métriques performance NOUVELLES -->
      {self._generate_performance_metrics_section(real_data_indicators)}

      <!-- Section solution optimale -->
      <text x="15" y="160" class="metric-label" style="fill: white; font-size: 11px;">
        Optimal Solution:
      </text>

      <text x="15" y="180" class="metric-label" style="fill: #FFD700; font-size: 10px;">
        X: {f"{optimal_point[0]:.3f}" if optimal_point else "N/A"}
      </text>

      <text x="15" y="195" class="metric-label" style="fill: #FFD700; font-size: 10px;">
        Y: {f"{optimal_point[1]:.3f}" if optimal_point else "N/A"}
      </text>

      <!-- Métriques validation NOUVELLES -->
      {self._generate_validation_metrics_section(real_data_indicators)}
    </g>'''

        return base_content + technical_panel

    def _extract_real_data_indicators(self, steps: List[Dict]) -> Dict[str, Any]:
        """Extrait indicateurs données réelles depuis steps"""
        # Vérifier si données réelles disponibles
        has_real_data = any(step.get('real_iteration', False) for step in steps)

        real_indicators = {
            'source_indicator': '📊' if has_real_data else '🔧',  # Indicateur visuel
            'has_real_data': has_real_data,
            'enumeration_time': None,
            'solve_time': None,
            'warm_start_used': False,
            'cross_validation_passed': False
        }

        # Extraction métriques depuis steps si disponibles
        for step in steps:
            if step.get('enumeration_time_ms'):
                real_indicators['enumeration_time'] = step['enumeration_time_ms']
            if step.get('solve_time_ms'):
                real_indicators['solve_time'] = step['solve_time_ms']
            if 'warm_start' in step.get('description', ''):
                real_indicators['warm_start_used'] = 'True' in step.get('description', '')
            if 'Cross-validation' in step.get('description', ''):
                real_indicators['cross_validation_passed'] = 'passed: True' in step.get('description', '')

        return real_indicators

    def _generate_performance_metrics_section(self, indicators: Dict[str, Any]) -> str:
        """Génère section métriques performance"""
        if not indicators['has_real_data']:
            return '''
      <text x="15" y="110" class="metric-label" style="fill: #888; font-size: 10px;">
        Performance: Mock data
      </text>'''

        section = '''
      <text x="15" y="110" class="metric-label" style="fill: #88FF88; font-size: 10px;">
        Performance (Real Data):
      </text>'''

        if indicators['enumeration_time']:
            section += f'''
      <text x="15" y="125" class="metric-label" style="fill: #AAFFAA; font-size: 9px;">
        Enumeration: {indicators['enumeration_time']:.1f}ms
      </text>'''

        if indicators['solve_time']:
            section += f'''
      <text x="15" y="140" class="metric-label" style="fill: #AAFFAA; font-size: 9px;">
        Solve: {indicators['solve_time']:.1f}ms
      </text>'''

        return section

    def _generate_validation_metrics_section(self, indicators: Dict[str, Any]) -> str:
        """Génère section métriques validation"""
        if not indicators['has_real_data']:
            return ''

        section = '''
      <text x="15" y="220" class="metric-label" style="fill: #FFD700; font-size: 10px;">
        Validation:
      </text>'''

        warm_start_color = '#88FF88' if indicators['warm_start_used'] else '#FF8888'
        section += f'''
      <text x="15" y="235" class="metric-label" style="fill: {warm_start_color}; font-size: 9px;">
        Warm-start: {'Yes' if indicators['warm_start_used'] else 'No'}
      </text>'''

        validation_color = '#88FF88' if indicators['cross_validation_passed'] else '#FF8888'
        section += f'''
      <text x="15" y="250" class="metric-label" style="fill: {validation_color}; font-size: 9px;">
        Cross-validation: {'Passed' if indicators['cross_validation_passed'] else 'Failed'}
      </text>'''

        return section

    def _calculate_sector_positions(self, content_width: float, content_height: float) -> Dict[str, Tuple[float, float]]:
        """Calcule positions optimales des secteurs"""
        cache_key = f"{content_width}x{content_height}"
        if cache_key in self._sector_positions_cache:
            self.generation_stats['cache_hits'] += 1
            return self._sector_positions_cache[cache_key]

        sectors = ['AGRICULTURE', 'INDUSTRY', 'SERVICES', 'FINANCE', 'ENERGY']
        positions = {}

        center_x, center_y = content_width // 2, content_height // 2
        radius = min(content_width, content_height) * 0.3

        for i, sector in enumerate(sectors):
            angle = (2 * 3.14159 * i) / len(sectors) - 3.14159/2
            x = center_x + radius * 1.2 * (0.8 + 0.4 * (i % 2)) * (1 if i < 3 else -0.5)
            y = center_y + radius * 0.8 * (0.6 + 0.6 * ((i + 1) % 3) / 2) * (1 if i % 2 == 0 else -1)
            positions[sector] = (x, y)

        self._sector_positions_cache[cache_key] = positions
        return positions

    def _generate_timeline_visualization(self, timeline_data: List[Dict]) -> str:
        """Génère visualisation timeline des métriques"""
        timeline_width = self.config.width - 100
        timeline_height = 60
        y_position = self.config.height - 150

        if not timeline_data:
            return f'''
    <g id="timeline-placeholder" transform="translate(50, {y_position})">
      <rect width="{timeline_width}" height="{timeline_height}"
            fill="rgba(200,200,200,0.1)" stroke="rgba(0,0,0,0.1)" rx="5"/>
      <text x="{timeline_width//2}" y="{timeline_height//2}"
            class="metric-label" text-anchor="middle">
        No timeline data available
      </text>
    </g>'''

        # Points de données sur la timeline
        points = []
        for i, data_point in enumerate(timeline_data[-50:]):  # 50 derniers points
            x = 50 + (i / 49) * timeline_width if len(timeline_data) > 1 else 50 + timeline_width // 2
            value = data_point.get('success_rate', 0.5)
            y = y_position + timeline_height - (value * timeline_height)
            points.append(f"{x:.1f},{y:.1f}")

        path_data = "M " + " L ".join(points)

        return f'''
    <g id="timeline-visualization" transform="translate(0, 0)">
      <rect x="50" y="{y_position}" width="{timeline_width}" height="{timeline_height}"
            fill="rgba(255,255,255,0.1)" stroke="rgba(0,0,0,0.1)" rx="5"/>

      <path d="{path_data}" fill="none" stroke="#3498DB" stroke-width="2"
            opacity="0" stroke-linecap="round">
        <animate attributeName="opacity" from="0" to="1" dur="2s" fill="freeze"/>
      </path>

      <text x="50" y="{y_position - 10}" class="metric-label"
            style="font-size: 12px; font-weight: bold;">
        Performance Timeline
      </text>
    </g>'''

    def _generate_performance_gauges(self, metrics_data: Dict[str, Any]) -> str:
        """Génère jauges circulaires de performance"""
        gauges_x = self.config.width - 300
        gauges_y = 100

        gauges = [
            ('CPU', metrics_data.get('cpu_usage', 0), 100, '#E74C3C'),
            ('Memory', metrics_data.get('memory_usage', 0), 100, '#F39C12'),
            ('Throughput', metrics_data.get('throughput_pct', 0), 100, '#27AE60')
        ]

        gauge_elements = []
        for i, (label, value, max_val, color) in enumerate(gauges):
            cx = gauges_x + i * 80
            cy = gauges_y
            percentage = (value / max_val) * 100 if max_val > 0 else 0
            circumference = 2 * 3.14159 * 25
            stroke_offset = circumference - (percentage / 100) * circumference

            gauge_elements.append(f'''
        <g class="performance-gauge" transform="translate({cx}, {cy})">
          <!-- Background circle -->
          <circle r="25" fill="none" stroke="rgba(200,200,200,0.3)" stroke-width="5"/>

          <!-- Progress circle -->
          <circle r="25" fill="none" stroke="{color}" stroke-width="5"
                  stroke-linecap="round"
                  stroke-dasharray="{circumference:.1f}"
                  stroke-dashoffset="{circumference:.1f}"
                  transform="rotate(-90)">
            <animate attributeName="stroke-dashoffset"
                     from="{circumference:.1f}"
                     to="{stroke_offset:.1f}"
                     dur="2s"
                     begin="{i * 0.3}s"
                     fill="freeze"/>
          </circle>

          <!-- Label -->
          <text y="-35" class="metric-label" text-anchor="middle" style="font-size: 10px;">
            {label}
          </text>

          <!-- Value -->
          <text y="5" class="metric-value" text-anchor="middle" style="font-size: 12px;">
            {value:.0f}%
          </text>
        </g>''')

        return f'''
    <g id="performance-gauges">
      {''.join(gauge_elements)}
    </g>'''

    def _generate_system_health_indicators(self, metrics_data: Dict[str, Any]) -> str:
        """Génère indicateurs de santé système"""
        health_x = self.config.width - 250
        health_y = 250

        # Calcul santé globale
        feasibility_rate = metrics_data.get('feasibility_rate', 0)
        optimization_rate = metrics_data.get('optimization_rate', 0)
        avg_time = metrics_data.get('avg_validation_time_ms', 0)

        health_score = (feasibility_rate + optimization_rate) / 2
        health_color = "#27AE60" if health_score >= 70 else "#F39C12" if health_score >= 50 else "#E74C3C"
        health_status = "EXCELLENT" if health_score >= 80 else "GOOD" if health_score >= 60 else "WARNING" if health_score >= 40 else "CRITICAL"

        return f'''
    <g id="system-health" transform="translate({health_x}, {health_y})">
      <rect width="200" height="100" rx="15"
            fill="rgba(255,255,255,0.95)"
            stroke="{health_color}" stroke-width="2"/>

      <text x="100" y="25" class="metric-label"
            text-anchor="middle" style="font-weight: bold;">
        System Health
      </text>

      <circle cx="50" cy="55" r="15"
              fill="{health_color}" opacity="0.8">
        <animate attributeName="r" values="15;18;15" dur="2s" repeatCount="indefinite"/>
      </circle>

      <text x="75" y="50" class="metric-label" style="font-size: 11px;">
        Status: {health_status}
      </text>

      <text x="75" y="65" class="metric-label" style="font-size: 11px;">
        Score: {health_score:.1f}%
      </text>

      <text x="100" y="85" class="metric-label"
            text-anchor="middle" style="font-size: 9px; opacity: 0.7;">
        Avg Response: {avg_time:.1f}ms
      </text>
    </g>'''

    def _create_error_animation(self, error_message: str) -> str:
        """Crée animation d'erreur"""
        content = f'''
    <rect x="50" y="50" width="{self.config.width-100}" height="{self.config.height-100}"
          fill="rgba(231, 76, 60, 0.1)" stroke="#E74C3C" stroke-width="2" rx="15"/>

    <text x="{self.config.width//2}" y="{self.config.height//2 - 20}"
          class="metric-label" text-anchor="middle"
          style="font-size: 18px; font-weight: bold; fill: #E74C3C;">
      Animation Generation Error
    </text>

    <text x="{self.config.width//2}" y="{self.config.height//2 + 10}"
          class="metric-label" text-anchor="middle"
          style="font-size: 12px; fill: #2C3E50;">
      {error_message}
    </text>

    <text x="{self.config.width//2}" y="{self.config.height//2 + 40}"
          class="metric-label" text-anchor="middle"
          style="font-size: 10px; opacity: 0.7;">
      Please check the input data and try again
    </text>'''

        return self.templates.get_base_svg_structure("Error Animation", content)

    def _update_generation_stats(self, start_time: float):
        """Met à jour statistiques de génération"""
        generation_time = time.time() - start_time
        self.generation_stats['animations_created'] += 1
        self.generation_stats['total_generation_time'] += generation_time
        self.generation_stats['last_generation_time'] = generation_time

    def get_generation_stats(self) -> Dict[str, Any]:
        """Retourne statistiques de génération"""
        stats = self.generation_stats.copy()
        if stats['animations_created'] > 0:
            stats['avg_generation_time'] = stats['total_generation_time'] / stats['animations_created']
        else:
            stats['avg_generation_time'] = 0.0
        return stats


# Fonctions utilitaires pour intégration facile

def create_quick_economy_animation(economy_data: Dict[str, Any],
                                 width: int = 1000, height: int = 700) -> str:
    """Fonction utilitaire pour création rapide d'animation économie"""
    config = SVGConfig(width=width, height=height, animation_duration=2.5)
    animator = ICGSSVGAnimator(config)
    return animator.create_economy_animation(economy_data)


def create_quick_transaction_animation(transaction_data: Dict[str, Any],
                                     context_data: Optional[Dict[str, Any]] = None) -> str:
    """Fonction utilitaire pour création rapide d'animation transaction"""
    config = SVGConfig(width=800, height=500, animation_duration=3.0)
    animator = ICGSSVGAnimator(config)
    return animator.create_transaction_animation(transaction_data, context_data)


def create_quick_simplex_animation(simplex_data: Dict[str, Any],
                                 style: str = "standard") -> str:
    """Fonction utilitaire pour création rapide d'animation Simplex"""
    config = SVGConfig(width=700, height=600, animation_duration=4.0)
    animator = ICGSSVGAnimator(config)
    return animator.create_simplex_animation(simplex_data, style)


if __name__ == "__main__":
    # Test basique
    print("🎨 ICGS SVG Animator - Test de base")

    # Configuration test
    config = SVGConfig(width=800, height=600, animation_duration=2.0)
    animator = ICGSSVGAnimator(config)

    # Données test
    test_economy_data = {
        'agents_distribution': {
            'AGRICULTURE': {'agents': [{'id': 'FARM_01', 'balance': 1200}]},
            'INDUSTRY': {'agents': [{'id': 'MFG_01', 'balance': 900}]}
        },
        'performance_metrics': {
            'feasibility_rate': 85.5,
            'optimization_rate': 78.2,
            'avg_validation_time_ms': 45.3
        }
    }

    # Test génération
    try:
        svg_content = animator.create_economy_animation(test_economy_data)
        print(f"✅ Animation générée: {len(svg_content)} caractères")
        print(f"📊 Stats: {animator.get_generation_stats()}")

    except Exception as e:
        print(f"❌ Erreur test: {e}")