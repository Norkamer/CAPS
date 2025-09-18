#!/usr/bin/env python3
"""
SVG Templates pour Animation ICGS - Templates Réutilisables
=============================================================

Templates SVG paramétrables pour visualisation des données économiques ICGS :
- Secteurs économiques avec clusters d'agents
- Flux de transactions inter-sectorielles
- Métriques de performance et indicateurs
- Animations Simplex avec polytopes et chemins d'optimisation

Usage:
    from svg_templates import ICGSSVGTemplates
    templates = ICGSSVGTemplates()
    svg_content = templates.render_sector_cluster('AGRICULTURE', agents_data, config)
"""

from typing import Dict, List, Any, Optional, Tuple
import json
from dataclasses import dataclass


@dataclass
class SVGConfig:
    """Configuration paramétrable pour génération SVG"""
    width: int = 800
    height: int = 600
    margin: int = 50

    # Couleurs secteurs économiques
    colors: Dict[str, str] = None

    # Paramètres animation
    animation_duration: float = 2.0
    animation_delay: float = 0.1
    transition_type: str = "ease-in-out"

    # Styles visuels
    agent_radius: int = 8
    connection_width: int = 2
    font_family: str = "Segoe UI, Arial, sans-serif"
    font_size: int = 12

    def __post_init__(self):
        if self.colors is None:
            self.colors = {
                'AGRICULTURE': '#2ECC71',
                'INDUSTRY': '#E74C3C',
                'SERVICES': '#3498DB',
                'FINANCE': '#F39C12',
                'ENERGY': '#9B59B6'
            }


class ICGSSVGTemplates:
    """Générateur de templates SVG pour visualisations ICGS"""

    def __init__(self, config: Optional[SVGConfig] = None):
        self.config = config or SVGConfig()

    def get_base_svg_structure(self, title: str = "ICGS Animation", content: str = "") -> str:
        """Structure SVG de base avec définitions réutilisables"""
        # Construction du SVG par parties pour éviter les conflits de formatage
        svg_header = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     viewBox="0 0 {self.config.width} {self.config.height}"
     preserveAspectRatio="xMidYMid meet">

  <title>{title}</title>

  <!-- Définitions réutilisables -->
  <defs>'''

        svg_middle = f'''  </defs>

  <!-- Styles CSS paramétrables -->
  <style>'''

        svg_content_start = f'''  </style>

  <!-- Zone de contenu principal -->
  <g id="main-content" transform="translate({self.config.margin}, {self.config.margin})">
'''

        svg_content_end = '''
  </g>

  <!-- Interface overlay -->
  <g id="interface-overlay">'''

        svg_footer = '''  </g>
</svg>'''

        # Assemblage final avec contenu inséré
        full_svg = (svg_header +
                   self._get_svg_definitions() +
                   svg_middle +
                   self._get_css_styles() +
                   svg_content_start +
                   content +
                   svg_content_end +
                   self._get_interface_elements() +
                   svg_footer)

        return full_svg

    def _get_svg_definitions(self) -> str:
        """Définitions SVG réutilisables (gradients, filtres, marqueurs)"""
        return '''
    <!-- Gradients pour secteurs -->
    <linearGradient id="agriculture-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#27AE60;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#2ECC71;stop-opacity:0.8" />
    </linearGradient>

    <linearGradient id="industry-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#C0392B;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#E74C3C;stop-opacity:0.8" />
    </linearGradient>

    <linearGradient id="services-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#2980B9;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#3498DB;stop-opacity:0.8" />
    </linearGradient>

    <linearGradient id="finance-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#D68910;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#F39C12;stop-opacity:0.8" />
    </linearGradient>

    <linearGradient id="energy-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#7D3C98;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#9B59B6;stop-opacity:0.8" />
    </linearGradient>

    <!-- Filtres d'effets -->
    <filter id="glow-effect" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>

    <filter id="drop-shadow" x="-50%" y="-50%" width="200%" height="200%">
      <feDropShadow dx="2" dy="2" stdDeviation="3" flood-opacity="0.3"/>
    </filter>

    <!-- Marqueurs pour flèches -->
    <marker id="arrow-marker" markerWidth="10" markerHeight="10"
            refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,6 L9,3 z" fill="currentColor" />
    </marker>

    <!-- Patterns pour zones -->
    <pattern id="sector-pattern" patternUnits="userSpaceOnUse" width="20" height="20">
      <rect width="20" height="20" fill="rgba(255,255,255,0.02)"/>
      <circle cx="10" cy="10" r="1" fill="rgba(255,255,255,0.1)"/>
    </pattern>
'''

    def _get_css_styles(self) -> str:
        """Styles CSS avec variables CSS pour modification facile"""
        return f'''
    :root {{
      --animation-duration: {self.config.animation_duration}s;
      --animation-delay: {self.config.animation_delay}s;
      --transition-type: {self.config.transition_type};
      --agent-radius: {self.config.agent_radius}px;
      --connection-width: {self.config.connection_width}px;
      --font-family: {self.config.font_family};
      --font-size: {self.config.font_size}px;
    }}

    /* Secteurs économiques */
    .sector-cluster {{
      opacity: 0;
      animation: fadeInScale var(--animation-duration) var(--transition-type) forwards;
    }}

    .sector-cluster:nth-child(1) {{ animation-delay: calc(var(--animation-delay) * 0); }}
    .sector-cluster:nth-child(2) {{ animation-delay: calc(var(--animation-delay) * 1); }}
    .sector-cluster:nth-child(3) {{ animation-delay: calc(var(--animation-delay) * 2); }}
    .sector-cluster:nth-child(4) {{ animation-delay: calc(var(--animation-delay) * 3); }}
    .sector-cluster:nth-child(5) {{ animation-delay: calc(var(--animation-delay) * 4); }}

    .sector-boundary {{
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
      stroke-dasharray: 5,5;
      opacity: 0.6;
      animation: dashMove 3s linear infinite;
    }}

    /* Agents économiques */
    .economic-agent {{
      r: var(--agent-radius);
      fill: url(#agriculture-gradient);
      stroke: white;
      stroke-width: 2;
      filter: url(#drop-shadow);
      cursor: pointer;
      transition: all 0.3s var(--transition-type);
    }}

    .economic-agent:hover {{
      r: calc(var(--agent-radius) * 1.3);
      filter: url(#glow-effect);
    }}

    .agent-agriculture {{ fill: url(#agriculture-gradient); }}
    .agent-industry {{ fill: url(#industry-gradient); }}
    .agent-services {{ fill: url(#services-gradient); }}
    .agent-finance {{ fill: url(#finance-gradient); }}
    .agent-energy {{ fill: url(#energy-gradient); }}

    /* Flux de transactions */
    .transaction-flow {{
      fill: none;
      stroke-width: var(--connection-width);
      stroke-linecap: round;
      marker-end: url(#arrow-marker);
      opacity: 0;
      animation: flowAnimation var(--animation-duration) var(--transition-type) forwards;
    }}

    .flow-particle {{
      r: 3;
      fill: #FFD700;
      opacity: 0;
      animation: particleFlow 2s ease-in-out infinite;
    }}

    /* Métriques de performance */
    .metric-bar {{
      fill: #3498DB;
      width: 0;
      animation: barGrowth var(--animation-duration) var(--transition-type) forwards;
    }}

    .metric-label {{
      font-family: var(--font-family);
      font-size: var(--font-size);
      fill: #2C3E50;
      text-anchor: middle;
      dominant-baseline: central;
    }}

    .metric-value {{
      font-family: var(--font-family);
      font-size: calc(var(--font-size) * 1.2);
      font-weight: bold;
      fill: #E74C3C;
      text-anchor: middle;
    }}

    /* Polytope Simplex */
    .simplex-polytope {{
      fill: rgba(52, 152, 219, 0.2);
      stroke: #3498DB;
      stroke-width: 2;
      opacity: 0;
      animation: fadeIn var(--animation-duration) var(--transition-type) forwards;
    }}

    .simplex-vertex {{
      r: 6;
      fill: #E74C3C;
      stroke: white;
      stroke-width: 2;
      filter: url(#glow-effect);
    }}

    .optimization-path {{
      fill: none;
      stroke: #F39C12;
      stroke-width: 3;
      stroke-dasharray: 0, 1000;
      animation: pathDraw 3s ease-in-out forwards;
    }}

    /* Animations keyframes */
    @keyframes fadeInScale {{
      0% {{ opacity: 0; transform: scale(0.5); }}
      100% {{ opacity: 1; transform: scale(1); }}
    }}

    @keyframes fadeIn {{
      0% {{ opacity: 0; }}
      100% {{ opacity: 1; }}
    }}

    @keyframes dashMove {{
      0% {{ stroke-dashoffset: 0; }}
      100% {{ stroke-dashoffset: 20; }}
    }}

    @keyframes flowAnimation {{
      0% {{ opacity: 0; stroke-dasharray: 0, 1000; }}
      50% {{ opacity: 0.8; }}
      100% {{ opacity: 0.6; stroke-dasharray: 1000, 0; }}
    }}

    @keyframes particleFlow {{
      0% {{ opacity: 0; }}
      50% {{ opacity: 1; }}
      100% {{ opacity: 0; }}
    }}

    @keyframes barGrowth {{
      0% {{ width: 0; }}
      100% {{ width: 100%; }}
    }}

    @keyframes pathDraw {{
      0% {{ stroke-dasharray: 0, 1000; }}
      100% {{ stroke-dasharray: 1000, 0; }}
    }}
'''

    def _get_interface_elements(self) -> str:
        """Éléments d'interface (titres, légendes, contrôles)"""
        return f'''
    <!-- Titre principal -->
    <text x="{self.config.width//2}" y="30"
          class="metric-label"
          style="font-size: 20px; font-weight: bold; fill: #2C3E50;">
      ICGS - Visualisation Économie 65 Agents
    </text>

    <!-- Légende secteurs -->
    <g id="sector-legend" transform="translate(20, {self.config.height - 100})">
      <rect width="200" height="80" rx="10"
            fill="rgba(255,255,255,0.9)"
            stroke="rgba(0,0,0,0.1)"
            stroke-width="1"/>

      <text x="10" y="20" class="metric-label" style="font-weight: bold;">Secteurs:</text>

      <circle cx="20" cy="35" r="6" class="agent-agriculture"/>
      <text x="35" y="40" class="metric-label" style="font-size: 10px;">Agriculture</text>

      <circle cx="100" cy="35" r="6" class="agent-industry"/>
      <text x="115" y="40" class="metric-label" style="font-size: 10px;">Industry</text>

      <circle cx="20" cy="55" r="6" class="agent-services"/>
      <text x="35" y="60" class="metric-label" style="font-size: 10px;">Services</text>

      <circle cx="100" cy="55" r="6" class="agent-finance"/>
      <text x="115" y="60" class="metric-label" style="font-size: 10px;">Finance</text>

      <circle cx="160" cy="45" r="6" class="agent-energy"/>
      <text x="175" y="50" class="metric-label" style="font-size: 10px;">Energy</text>
    </g>
'''

    def render_sector_cluster(self, sector: str, agents_data: List[Dict],
                             center_x: float, center_y: float,
                             cluster_radius: float = 80) -> str:
        """Génère un cluster SVG pour un secteur économique"""
        sector_lower = sector.lower()
        agents_count = len(agents_data)

        # Positions des agents en cercle autour du centre
        agent_elements = []
        for i, agent in enumerate(agents_data):
            angle = (2 * 3.14159 * i) / agents_count
            agent_x = center_x + (cluster_radius * 0.6) * (0.5 + 0.5 * (i % 3) / 2) * \
                     (1 if i % 2 == 0 else -1) * abs(1 + 0.3 * (i % 5 - 2))
            agent_y = center_y + (cluster_radius * 0.6) * (0.5 + 0.5 * (i % 4) / 3) * \
                     (1 if (i // 2) % 2 == 0 else -1) * abs(1 + 0.2 * (i % 3 - 1))

            balance = agent.get('balance', 1000)
            radius_scale = max(0.7, min(1.5, balance / 1000))  # Scale par balance

            agent_elements.append(f'''
        <circle cx="{agent_x:.1f}" cy="{agent_y:.1f}"
                class="economic-agent agent-{sector_lower}"
                style="r: calc(var(--agent-radius) * {radius_scale:.2f});"
                data-agent-id="{agent.get('id', f'agent_{i}')}"
                data-balance="{balance:.2f}"
                data-sector="{sector}">
          <title>{agent.get('id', f'Agent {i}')} - Balance: {balance:.2f}</title>
        </circle>''')

        # Boundary du cluster
        boundary = f'''
        <ellipse cx="{center_x}" cy="{center_y}"
                 rx="{cluster_radius}" ry="{cluster_radius * 0.8}"
                 class="sector-boundary"
                 style="stroke: {self.config.colors[sector]};" />'''

        # Label du secteur
        label = f'''
        <text x="{center_x}" y="{center_y - cluster_radius - 15}"
              class="metric-label"
              style="font-weight: bold; font-size: 14px; fill: {self.config.colors[sector]};">
          {sector} ({agents_count} agents)
        </text>'''

        return f'''
    <g class="sector-cluster" data-sector="{sector}">
      {boundary}
      {''.join(agent_elements)}
      {label}
    </g>'''

    def render_transaction_flow(self, source_pos: Tuple[float, float],
                               target_pos: Tuple[float, float],
                               amount: float, success: bool = True,
                               transaction_id: str = "") -> str:
        """Génère un flux de transaction animé entre deux points"""
        x1, y1 = source_pos
        x2, y2 = target_pos

        # Courbe de Bézier pour trajectoire naturelle
        ctrl_x = (x1 + x2) / 2 + (y2 - y1) * 0.2
        ctrl_y = (y1 + y2) / 2 - (x2 - x1) * 0.2

        # Couleur selon succès/échec
        color = "#27AE60" if success else "#E74C3C"
        opacity = max(0.3, min(1.0, amount / 500))  # Opacité par montant

        # Particules qui suivent le chemin
        particle_elements = []
        for i in range(3):
            delay = i * 0.5
            particle_elements.append(f'''
        <circle class="flow-particle" style="animation-delay: {delay}s;">
          <animateMotion dur="2s" repeatCount="indefinite" begin="{delay}s">
            <mpath xlink:href="#flow-path-{transaction_id}" />
          </animateMotion>
        </circle>''')

        return f'''
    <g class="transaction-flow-group" data-transaction="{transaction_id}">
      <path id="flow-path-{transaction_id}"
            d="M {x1:.1f},{y1:.1f} Q {ctrl_x:.1f},{ctrl_y:.1f} {x2:.1f},{y2:.1f}"
            class="transaction-flow"
            style="stroke: {color}; opacity: {opacity:.2f};"
            data-amount="{amount:.2f}"
            data-success="{str(success).lower()}">
        <title>Transaction: {amount:.2f} - {'Success' if success else 'Failed'}</title>
      </path>
      {''.join(particle_elements)}
    </g>'''

    def render_performance_metrics(self, metrics_data: Dict[str, Any],
                                  x: float = 20, y: float = 100) -> str:
        """Génère des barres de métriques de performance"""
        metrics = [
            ('Agents', metrics_data.get('agents_count', 0), 65, '#3498DB'),
            ('Transactions', metrics_data.get('total_transactions', 0), 1000, '#27AE60'),
            ('Feasibility', metrics_data.get('feasibility_rate', 0), 100, '#F39C12'),
            ('Optimization', metrics_data.get('optimization_rate', 0), 100, '#E74C3C')
        ]

        metric_elements = []
        bar_width = 120
        bar_height = 20
        spacing = 35

        for i, (label, value, max_value, color) in enumerate(metrics):
            y_pos = y + i * spacing
            percentage = (value / max_value) * 100 if max_value > 0 else 0
            bar_fill_width = (value / max_value) * bar_width if max_value > 0 else 0

            metric_elements.append(f'''
        <g class="metric-group" transform="translate({x}, {y_pos})">
          <!-- Background bar -->
          <rect width="{bar_width}" height="{bar_height}"
                fill="rgba(200,200,200,0.3)"
                stroke="rgba(0,0,0,0.1)"
                rx="10" />

          <!-- Value bar -->
          <rect class="metric-bar" height="{bar_height}"
                fill="{color}"
                rx="10"
                style="width: {bar_fill_width:.1f}px;">
            <animate attributeName="width"
                     from="0"
                     to="{bar_fill_width:.1f}"
                     dur="1.5s"
                     begin="{i * 0.2}s"
                     fill="freeze" />
          </rect>

          <!-- Label -->
          <text x="-10" y="{bar_height//2}"
                class="metric-label"
                text-anchor="end">
            {label}:
          </text>

          <!-- Value -->
          <text x="{bar_width + 10}" y="{bar_height//2}"
                class="metric-value">
            {value:.1f}{'%' if 'rate' in label.lower() else ''}
          </text>
        </g>''')

        return f'''
    <g id="performance-metrics">
      <rect x="{x-15}" y="{y-25}"
            width="{bar_width + 80}" height="{len(metrics) * spacing + 30}"
            fill="rgba(255,255,255,0.95)"
            stroke="rgba(0,0,0,0.1)"
            rx="15" />

      <text x="{x + bar_width//2}" y="{y-5}"
            class="metric-label"
            style="font-weight: bold; font-size: 14px;">
        Performance Metrics
      </text>

      {''.join(metric_elements)}
    </g>'''

    def render_simplex_polytope(self, vertices: List[Tuple[float, float]],
                               constraints: List[Dict],
                               optimal_point: Optional[Tuple[float, float]] = None) -> str:
        """Génère la visualisation 2D d'un polytope Simplex"""
        if len(vertices) < 3:
            return "<!-- Not enough vertices for polytope -->"

        # Points du polytope
        path_data = f"M {vertices[0][0]:.1f},{vertices[0][1]:.1f}"
        for vertex in vertices[1:]:
            path_data += f" L {vertex[0]:.1f},{vertex[1]:.1f}"
        path_data += " Z"

        # Vertices
        vertex_elements = []
        for i, (x, y) in enumerate(vertices):
            vertex_elements.append(f'''
        <circle cx="{x:.1f}" cy="{y:.1f}"
                class="simplex-vertex"
                data-vertex="{i}">
          <title>Vertex {i}: ({x:.2f}, {y:.2f})</title>
        </circle>''')

        # Point optimal si fourni
        optimal_element = ""
        if optimal_point:
            opt_x, opt_y = optimal_point
            optimal_element = f'''
        <circle cx="{opt_x:.1f}" cy="{opt_y:.1f}"
                r="8"
                fill="#FFD700"
                stroke="#F39C12"
                stroke-width="3"
                filter="url(#glow-effect)">
          <title>Point Optimal: ({opt_x:.2f}, {opt_y:.2f})</title>
          <animate attributeName="r" values="8;12;8" dur="2s" repeatCount="indefinite"/>
        </circle>'''

        return f'''
    <g id="simplex-polytope-visualization">
      <!-- Zone faisable -->
      <path d="{path_data}"
            class="simplex-polytope">
        <title>Region Faisable Simplex</title>
      </path>

      <!-- Vertices -->
      {''.join(vertex_elements)}

      <!-- Point optimal -->
      {optimal_element}

      <!-- Axes de coordonnées -->
      <g class="coordinate-axes" stroke="#2C3E50" stroke-width="1" opacity="0.6">
        <line x1="50" y1="50" x2="50" y2="350" marker-end="url(#arrow-marker)"/>
        <line x1="50" y1="350" x2="400" y2="350" marker-end="url(#arrow-marker)"/>

        <text x="25" y="200" class="metric-label"
              transform="rotate(-90, 25, 200)">Contraintes Y</text>
        <text x="225" y="375" class="metric-label">Contraintes X</text>
      </g>
    </g>'''

    def render_complete_economy_animation(self, economy_data: Dict[str, Any]) -> str:
        """Génère l'animation complète de l'économie 65 agents"""
        content_width = self.config.width - 2 * self.config.margin
        content_height = self.config.height - 2 * self.config.margin

        # Positions des secteurs en pentagone
        sectors = ['AGRICULTURE', 'INDUSTRY', 'SERVICES', 'FINANCE', 'ENERGY']
        sector_positions = {}
        center_x, center_y = content_width // 2, content_height // 2

        for i, sector in enumerate(sectors):
            angle = (2 * 3.14159 * i) / len(sectors) - 3.14159/2  # Start at top
            radius = min(content_width, content_height) * 0.3
            x = center_x + radius * (0.8 + 0.4 * (i % 2)) * \
                          (1 if i < 3 else -0.5) * abs(1 + 0.2 * (i % 4 - 1.5))
            y = center_y + radius * (0.6 + 0.6 * ((i + 1) % 3) / 2) * \
                          (1 if i % 2 == 0 else -1) * abs(1 + 0.1 * (i % 5 - 2))
            sector_positions[sector] = (x, y)

        # Génération des clusters de secteurs
        sector_clusters = []
        for sector in sectors:
            agents = economy_data.get('agents_distribution', {}).get(sector, {}).get('agents', [])
            if agents:
                x, y = sector_positions[sector]
                cluster = self.render_sector_cluster(sector, agents, x, y)
                sector_clusters.append(cluster)

        # Génération des flux de transactions
        transaction_flows = []
        transactions = economy_data.get('sample_results', [])
        for i, tx in enumerate(transactions[:10]):  # Limiter à 10 pour lisibilité
            source_sector = None
            target_sector = None

            # Trouver secteurs source/target (approximation)
            for sector, pos in sector_positions.items():
                if source_sector is None:
                    source_sector = sector
                    source_pos = pos
                elif target_sector is None and sector != source_sector:
                    target_sector = sector
                    target_pos = pos
                    break

            if source_sector and target_sector:
                flow = self.render_transaction_flow(
                    source_pos, target_pos,
                    tx.get('amount', 0),
                    tx.get('feasibility', {}).get('success', True),
                    tx.get('tx_id', f'tx_{i}')
                )
                transaction_flows.append(flow)

        # Métriques de performance
        performance_metrics = self.render_performance_metrics(
            economy_data.get('performance_metrics', {})
        )

        # Assemblage final
        content = f'''
    {''.join(sector_clusters)}

    {''.join(transaction_flows)}

    {performance_metrics}

    <!-- Indicateur central -->
    <circle cx="{center_x}" cy="{center_y}" r="15"
            fill="#34495E" stroke="white" stroke-width="3"
            filter="url(#glow-effect)">
      <title>ICGS Core System</title>
      <animate attributeName="r" values="15;18;15" dur="3s" repeatCount="indefinite"/>
    </circle>

    <text x="{center_x}" y="{center_y + 35}"
          class="metric-label"
          style="font-weight: bold; text-anchor: middle;">
      ICGS Core
    </text>'''

        return self.get_base_svg_structure("ICGS Economy Animation", content)