#!/usr/bin/env python3
"""
ICGS SVG API - Endpoints Flask pour Animations SVG
====================================================

API Flask pour exposer les fonctionnalités d'animation SVG via HTTP.
Intègre avec le système ICGS existant et fournit des endpoints paramétrables
pour générer des animations SVG à partir des données de simulation.

Endpoints disponibles:
- GET /api/svg/economy_animation - Animation économie complète
- GET /api/svg/transaction/<tx_id> - Animation transaction spécifique
- GET /api/svg/simplex_steps - Animation étapes Simplex
- GET /api/svg/performance_dashboard - Dashboard performance temps réel
- POST /api/svg/custom_animation - Animation personnalisée

Usage:
    python3 icgs_svg_api.py  # Serveur standalone
    ou intégration dans icgs_web_visualizer.py
"""

import os
import sys
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from flask import Flask, request, jsonify, Response, send_file
from urllib.parse import unquote

# Import modules SVG locaux
from icgs_svg_animator import ICGSSVGAnimator, create_quick_economy_animation
from svg_templates import SVGConfig, ICGSSVGTemplates

# Import système ICGS
sys.path.insert(0, os.path.dirname(__file__))
try:
    from icgs_web_native import WebNativeICGS
    from icgs_simulation.api.icgs_bridge import EconomicSimulation, SimulationMode
    ICGS_AVAILABLE = True
except ImportError:
    ICGS_AVAILABLE = False
    print("⚠️  ICGS modules not available, using mock data")


class ICGSSVGAPIServer:
    """Serveur API Flask pour animations SVG"""

    def __init__(self, app: Optional[Flask] = None, web_manager=None):
        self.app = app or Flask(__name__)
        self.web_manager = web_manager
        self.animators_cache = {}  # Cache des animators par configuration
        self.generation_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0.0
        }

        # Configuration par défaut
        self.default_config = SVGConfig()

        # Enregistrer routes
        self._register_routes()

    def _register_routes(self):
        """Enregistre tous les endpoints API"""

        @self.app.route('/api/svg/economy_animation')
        def api_economy_animation():
            """Animation SVG économie complète 65 agents"""
            return self._handle_economy_animation_request()

        @self.app.route('/api/svg/transaction/<tx_id>')
        def api_transaction_animation(tx_id: str):
            """Animation SVG transaction spécifique"""
            return self._handle_transaction_animation_request(tx_id)

        @self.app.route('/api/svg/simplex_steps')
        def api_simplex_animation():
            """Animation SVG étapes algorithme Simplex"""
            return self._handle_simplex_animation_request()

        @self.app.route('/api/svg/performance_dashboard')
        def api_performance_dashboard():
            """Dashboard SVG performance temps réel"""
            return self._handle_performance_dashboard_request()

        @self.app.route('/api/svg/custom_animation', methods=['POST'])
        def api_custom_animation():
            """Animation SVG personnalisée via données POST"""
            return self._handle_custom_animation_request()

        @self.app.route('/api/svg/config', methods=['GET', 'POST'])
        def api_svg_config():
            """Configuration SVG (GET pour lire, POST pour modifier)"""
            if request.method == 'GET':
                return self._handle_get_config_request()
            else:
                return self._handle_update_config_request()

        @self.app.route('/api/svg/stats')
        def api_svg_stats():
            """Statistiques génération SVG"""
            return self._handle_stats_request()

        @self.app.route('/api/svg/preview')
        def api_svg_preview():
            """Prévisualisation SVG avec données de test"""
            return self._handle_preview_request()

    def _handle_economy_animation_request(self) -> Response:
        """Traite requête animation économie"""
        start_time = time.time()
        self.generation_stats['total_requests'] += 1

        try:
            # Paramètres de requête
            params = self._extract_request_params()
            animation_type = request.args.get('type', 'complete')
            include_flows = request.args.get('flows', 'true').lower() == 'true'
            include_metrics = request.args.get('metrics', 'true').lower() == 'true'

            # Récupération données économie
            economy_data = self._get_economy_data()
            if not economy_data:
                return self._error_response("Economy data not available", 503)

            # Création animator avec configuration
            animator = self._get_animator(params)

            # Paramètres animation
            animator.params.show_transaction_flows = include_flows
            animator.params.show_performance_metrics = include_metrics

            # Génération animation
            svg_content = animator.create_economy_animation(economy_data, animation_type)

            response_time = time.time() - start_time
            self._update_stats(True, response_time)

            return Response(
                svg_content,
                mimetype='image/svg+xml',
                headers={
                    'Content-Disposition': f'inline; filename="icgs_economy_{animation_type}.svg"',
                    'X-Generation-Time': f'{response_time:.3f}s',
                    'X-Animation-Type': animation_type
                }
            )

        except Exception as e:
            self._update_stats(False, time.time() - start_time)
            return self._error_response(f"Economy animation generation failed: {str(e)}", 500)

    def _handle_transaction_animation_request(self, tx_id: str) -> Response:
        """Traite requête animation transaction"""
        start_time = time.time()
        self.generation_stats['total_requests'] += 1

        try:
            # Décodage URL
            tx_id = unquote(tx_id)

            # Paramètres de requête
            params = self._extract_request_params()
            show_context = request.args.get('context', 'false').lower() == 'true'

            # Récupération données transaction
            transaction_data = self._get_transaction_data(tx_id)
            if not transaction_data:
                return self._error_response(f"Transaction {tx_id} not found", 404)

            # Données contextuelles optionnelles
            context_data = None
            if show_context:
                context_data = self._get_transaction_context_data(tx_id)

            # Création animator
            animator = self._get_animator(params)

            # Génération animation
            svg_content = animator.create_transaction_animation(transaction_data, context_data)

            response_time = time.time() - start_time
            self._update_stats(True, response_time)

            return Response(
                svg_content,
                mimetype='image/svg+xml',
                headers={
                    'Content-Disposition': f'inline; filename="icgs_transaction_{tx_id}.svg"',
                    'X-Generation-Time': f'{response_time:.3f}s',
                    'X-Transaction-ID': tx_id
                }
            )

        except Exception as e:
            self._update_stats(False, time.time() - start_time)
            return self._error_response(f"Transaction animation generation failed: {str(e)}", 500)

    def _handle_simplex_animation_request(self) -> Response:
        """Traite requête animation Simplex"""
        start_time = time.time()
        self.generation_stats['total_requests'] += 1

        try:
            # Paramètres de requête
            params = self._extract_request_params()
            animation_style = request.args.get('style', 'standard')
            transaction_id = request.args.get('transaction_id', None)

            # Récupération données Simplex
            simplex_data = self._get_simplex_data(transaction_id)
            if not simplex_data:
                return self._error_response("Simplex data not available", 503)

            # Création animator
            animator = self._get_animator(params)

            # Génération animation
            svg_content = animator.create_simplex_animation(simplex_data, animation_style)

            response_time = time.time() - start_time
            self._update_stats(True, response_time)

            return Response(
                svg_content,
                mimetype='image/svg+xml',
                headers={
                    'Content-Disposition': f'inline; filename="icgs_simplex_{animation_style}.svg"',
                    'X-Generation-Time': f'{response_time:.3f}s',
                    'X-Animation-Style': animation_style
                }
            )

        except Exception as e:
            self._update_stats(False, time.time() - start_time)
            return self._error_response(f"Simplex animation generation failed: {str(e)}", 500)

    def _handle_performance_dashboard_request(self) -> Response:
        """Traite requête dashboard performance"""
        start_time = time.time()
        self.generation_stats['total_requests'] += 1

        try:
            # Paramètres de requête
            params = self._extract_request_params()
            include_timeline = request.args.get('timeline', 'false').lower() == 'true'

            # Récupération métriques performance
            metrics_data = self._get_performance_metrics()
            if not metrics_data:
                return self._error_response("Performance metrics not available", 503)

            # Timeline optionnelle
            timeline_data = None
            if include_timeline:
                timeline_data = self._get_performance_timeline()

            # Création animator
            animator = self._get_animator(params)

            # Configuration timeline
            animator.params.timeline_mode = include_timeline

            # Génération dashboard
            svg_content = animator.create_performance_dashboard(metrics_data, timeline_data)

            response_time = time.time() - start_time
            self._update_stats(True, response_time)

            return Response(
                svg_content,
                mimetype='image/svg+xml',
                headers={
                    'Content-Disposition': 'inline; filename="icgs_performance_dashboard.svg"',
                    'X-Generation-Time': f'{response_time:.3f}s',
                    'X-Include-Timeline': str(include_timeline)
                }
            )

        except Exception as e:
            self._update_stats(False, time.time() - start_time)
            return self._error_response(f"Performance dashboard generation failed: {str(e)}", 500)

    def _handle_custom_animation_request(self) -> Response:
        """Traite requête animation personnalisée"""
        start_time = time.time()
        self.generation_stats['total_requests'] += 1

        try:
            # Données POST
            if not request.is_json:
                return self._error_response("JSON data required", 400)

            data = request.get_json()
            animation_type = data.get('type', 'economy')
            custom_config = data.get('config', {})
            animation_data = data.get('data', {})

            # Configuration personnalisée
            config = SVGConfig()
            for key, value in custom_config.items():
                if hasattr(config, key):
                    setattr(config, key, value)

            # Création animator
            animator = ICGSSVGAnimator(config)

            # Génération selon type
            if animation_type == 'economy':
                svg_content = animator.create_economy_animation(animation_data)
            elif animation_type == 'transaction':
                context = data.get('context', None)
                svg_content = animator.create_transaction_animation(animation_data, context)
            elif animation_type == 'simplex':
                style = data.get('style', 'standard')
                svg_content = animator.create_simplex_animation(animation_data, style)
            elif animation_type == 'dashboard':
                timeline = data.get('timeline', None)
                svg_content = animator.create_performance_dashboard(animation_data, timeline)
            else:
                return self._error_response(f"Unknown animation type: {animation_type}", 400)

            response_time = time.time() - start_time
            self._update_stats(True, response_time)

            return Response(
                svg_content,
                mimetype='image/svg+xml',
                headers={
                    'Content-Disposition': f'inline; filename="icgs_custom_{animation_type}.svg"',
                    'X-Generation-Time': f'{response_time:.3f}s',
                    'X-Custom-Animation': 'true'
                }
            )

        except Exception as e:
            self._update_stats(False, time.time() - start_time)
            return self._error_response(f"Custom animation generation failed: {str(e)}", 500)

    def _handle_get_config_request(self) -> Response:
        """Traite requête lecture configuration"""
        try:
            # Configuration actuelle
            config_data = {
                'default_config': {
                    'width': self.default_config.width,
                    'height': self.default_config.height,
                    'margin': self.default_config.margin,
                    'colors': self.default_config.colors,
                    'animation_duration': self.default_config.animation_duration,
                    'animation_delay': self.default_config.animation_delay,
                    'transition_type': self.default_config.transition_type,
                    'agent_radius': self.default_config.agent_radius,
                    'connection_width': self.default_config.connection_width,
                    'font_family': self.default_config.font_family,
                    'font_size': self.default_config.font_size
                },
                'available_options': {
                    'animation_types': ['complete', 'sectors_only', 'flows_only', 'metrics_only'],
                    'simplex_styles': ['standard', 'educational', 'technical'],
                    'transition_types': ['ease-in-out', 'ease-in', 'ease-out', 'linear', 'bounce'],
                    'color_schemes': ['default', 'dark', 'pastel', 'high_contrast']
                },
                'cache_info': {
                    'cached_animators': len(self.animators_cache),
                    'cache_hit_rate': self._calculate_cache_hit_rate()
                }
            }

            return jsonify({
                'success': True,
                'config': config_data,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return self._error_response(f"Config retrieval failed: {str(e)}", 500)

    def _handle_update_config_request(self) -> Response:
        """Traite requête mise à jour configuration"""
        try:
            if not request.is_json:
                return self._error_response("JSON data required", 400)

            new_config = request.get_json()

            # Mise à jour configuration par défaut
            for key, value in new_config.items():
                if hasattr(self.default_config, key):
                    setattr(self.default_config, key, value)

            # Vider cache des animators (configuration changée)
            self.animators_cache.clear()

            return jsonify({
                'success': True,
                'message': 'Configuration updated successfully',
                'cache_cleared': True,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return self._error_response(f"Config update failed: {str(e)}", 500)

    def _handle_stats_request(self) -> Response:
        """Traite requête statistiques"""
        try:
            stats = self.generation_stats.copy()

            # Ajout informations système
            stats.update({
                'icgs_available': ICGS_AVAILABLE,
                'cache_size': len(self.animators_cache),
                'uptime': time.time(),  # Placeholder
                'timestamp': datetime.now().isoformat()
            })

            return jsonify({
                'success': True,
                'stats': stats
            })

        except Exception as e:
            return self._error_response(f"Stats retrieval failed: {str(e)}", 500)

    def _handle_preview_request(self) -> Response:
        """Traite requête prévisualisation avec données test"""
        try:
            # Paramètres de requête
            params = self._extract_request_params()
            preview_type = request.args.get('type', 'economy')

            # Génération données test
            if preview_type == 'economy':
                test_data = self._generate_test_economy_data()
                animator = self._get_animator(params)
                svg_content = animator.create_economy_animation(test_data)

            elif preview_type == 'transaction':
                test_data = self._generate_test_transaction_data()
                animator = self._get_animator(params)
                svg_content = animator.create_transaction_animation(test_data)

            elif preview_type == 'simplex':
                test_data = self._generate_test_simplex_data()
                animator = self._get_animator(params)
                svg_content = animator.create_simplex_animation(test_data)

            else:
                return self._error_response(f"Unknown preview type: {preview_type}", 400)

            return Response(
                svg_content,
                mimetype='image/svg+xml',
                headers={
                    'Content-Disposition': f'inline; filename="icgs_preview_{preview_type}.svg"',
                    'X-Preview-Mode': 'true',
                    'X-Test-Data': 'true'
                }
            )

        except Exception as e:
            return self._error_response(f"Preview generation failed: {str(e)}", 500)

    # Méthodes utilitaires

    def _extract_request_params(self) -> Dict[str, Any]:
        """Extrait paramètres de requête pour configuration SVG"""
        params = {}

        # Dimensions
        if 'width' in request.args:
            params['width'] = int(request.args.get('width', self.default_config.width))
        if 'height' in request.args:
            params['height'] = int(request.args.get('height', self.default_config.height))

        # Animation
        if 'duration' in request.args:
            params['animation_duration'] = float(request.args.get('duration', self.default_config.animation_duration))
        if 'delay' in request.args:
            params['animation_delay'] = float(request.args.get('delay', self.default_config.animation_delay))

        # Style
        if 'transition' in request.args:
            params['transition_type'] = request.args.get('transition', self.default_config.transition_type)

        return params

    def _get_animator(self, params: Dict[str, Any]) -> ICGSSVGAnimator:
        """Récupère animator depuis cache ou crée nouveau"""
        # Clé de cache basée sur paramètres
        cache_key = json.dumps(params, sort_keys=True)

        if cache_key in self.animators_cache:
            return self.animators_cache[cache_key]

        # Création nouvelle configuration
        config = SVGConfig()
        for key, value in params.items():
            if hasattr(config, key):
                setattr(config, key, value)

        # Création animator
        animator = ICGSSVGAnimator(config)
        self.animators_cache[cache_key] = animator

        return animator

    def _get_economy_data(self) -> Optional[Dict[str, Any]]:
        """Récupère données économie depuis système ICGS"""
        if not ICGS_AVAILABLE or not self.web_manager:
            return self._generate_mock_economy_data()

        try:
            # Utiliser web_manager.icgs_core pour récupérer données
            simulation = self.web_manager.icgs_core

            # Distribution agents par secteur
            agents_distribution = {}
            for agent_id, agent in simulation.agents.items():
                sector = agent.sector
                if sector not in agents_distribution:
                    agents_distribution[sector] = {'agents': [], 'count': 0, 'total_balance': 0}

                agents_distribution[sector]['agents'].append({
                    'id': agent_id,
                    'balance': float(agent.balance),
                    'sector': sector
                })
                agents_distribution[sector]['count'] += 1
                agents_distribution[sector]['total_balance'] += float(agent.balance)

            # Échantillon transactions récentes
            sample_results = []
            for i, tx in enumerate(simulation.transactions[-20:]):  # 20 dernières
                try:
                    # Validation rapide pour status
                    feas_result = simulation.validate_transaction(tx.transaction_id, SimulationMode.FEASIBILITY)
                    opt_result = simulation.validate_transaction(tx.transaction_id, SimulationMode.OPTIMIZATION)

                    sample_results.append({
                        'tx_id': tx.transaction_id,
                        'source_id': tx.source_account_id,
                        'target_id': tx.target_account_id,
                        'amount': float(tx.amount),
                        'feasibility': {
                            'success': feas_result.success,
                            'time_ms': feas_result.validation_time_ms
                        },
                        'optimization': {
                            'success': opt_result.success,
                            'time_ms': opt_result.validation_time_ms,
                            'optimal_price': float(getattr(opt_result, 'optimal_price', 0) or 0)
                        }
                    })
                except Exception:
                    continue  # Skip en cas d'erreur validation

            # Métriques performance
            performance_metrics = {
                'agents_count': len(simulation.agents),
                'total_transactions': len(simulation.transactions),
                'feasibility_rate': sum(1 for r in sample_results if r['feasibility']['success']) / max(len(sample_results), 1) * 100,
                'optimization_rate': sum(1 for r in sample_results if r['optimization']['success']) / max(len(sample_results), 1) * 100,
                'avg_validation_time_ms': sum(r['feasibility']['time_ms'] + r['optimization']['time_ms'] for r in sample_results) / max(len(sample_results), 1) / 2
            }

            return {
                'agents_distribution': agents_distribution,
                'sample_results': sample_results,
                'performance_metrics': performance_metrics,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"⚠️ Erreur récupération données économie: {e}")
            return self._generate_mock_economy_data()

    def _get_transaction_data(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """Récupère données transaction spécifique"""
        if not ICGS_AVAILABLE or not self.web_manager:
            return self._generate_mock_transaction_data(tx_id)

        try:
            simulation = self.web_manager.icgs_core

            # Recherche transaction
            transaction = next((tx for tx in simulation.transactions if tx.transaction_id == tx_id), None)
            if not transaction:
                return None

            # Validation transaction
            feas_result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
            opt_result = simulation.validate_transaction(tx_id, SimulationMode.OPTIMIZATION)

            return {
                'tx_id': tx_id,
                'source_id': transaction.source_account_id,
                'target_id': transaction.target_account_id,
                'amount': float(transaction.amount),
                'feasibility': {
                    'success': feas_result.success,
                    'time_ms': feas_result.validation_time_ms,
                    'status': str(feas_result.status) if hasattr(feas_result, 'status') else 'N/A'
                },
                'optimization': {
                    'success': opt_result.success,
                    'time_ms': opt_result.validation_time_ms,
                    'optimal_price': float(getattr(opt_result, 'optimal_price', 0) or 0),
                    'status': str(opt_result.status) if hasattr(opt_result, 'status') else 'N/A'
                },
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"⚠️ Erreur récupération transaction {tx_id}: {e}")
            return self._generate_mock_transaction_data(tx_id)

    def _get_transaction_context_data(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """Récupère données contextuelles pour transaction"""
        # Pour l'instant retourne info agents basique
        if not ICGS_AVAILABLE or not self.web_manager:
            return None

        try:
            simulation = self.web_manager.icgs_core
            agents_list = []

            for agent_id, agent in simulation.agents.items():
                agents_list.append({
                    'agent_id': agent_id,
                    'sector': agent.sector,
                    'balance': float(agent.balance),
                    'x': 200 + (hash(agent_id) % 400),  # Position pseudo-aléatoire
                    'y': 200 + (hash(agent.sector) % 200)
                })

            return {'agents': agents_list}

        except Exception:
            return None

    def _get_simplex_data(self, transaction_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Récupère données Simplex pour animation"""
        # Pour l'instant génère données test - peut être étendu avec vraies données ICGS
        return self._generate_test_simplex_data()

    def _get_performance_metrics(self) -> Optional[Dict[str, Any]]:
        """Récupère métriques performance actuelles"""
        if not ICGS_AVAILABLE or not self.web_manager:
            return self._generate_mock_performance_metrics()

        try:
            # Utiliser API métriques existante
            simulation = self.web_manager.icgs_core

            # Statistiques de base
            total_agents = len(simulation.agents) if hasattr(simulation, 'agents') else 0
            total_transactions = len(simulation.transactions) if hasattr(simulation, 'transactions') else 0

            # Mock des métriques système
            metrics = {
                'agents_count': total_agents,
                'total_transactions': total_transactions,
                'feasibility_rate': 85.2,  # Mock
                'optimization_rate': 78.9,  # Mock
                'avg_validation_time_ms': 47.3,  # Mock
                'cpu_usage': 15.4,  # Mock
                'memory_usage': 32.1,  # Mock
                'throughput_pct': 89.7,  # Mock
                'timestamp': datetime.now().isoformat()
            }

            return metrics

        except Exception as e:
            print(f"⚠️ Erreur récupération métriques: {e}")
            return self._generate_mock_performance_metrics()

    def _get_performance_timeline(self) -> Optional[List[Dict]]:
        """Récupère timeline des métriques"""
        # Timeline mock pour demo
        timeline = []
        for i in range(20):
            timeline.append({
                'timestamp': time.time() - (19 - i) * 60,  # 20 dernières minutes
                'success_rate': 0.7 + 0.3 * (i / 20) + 0.1 * ((-1) ** i)  # Simulation variation
            })
        return timeline

    # Méthodes de génération de données test

    def _generate_mock_economy_data(self) -> Dict[str, Any]:
        """Génère données économie mock pour test"""
        sectors = ['AGRICULTURE', 'INDUSTRY', 'SERVICES', 'FINANCE', 'ENERGY']
        agents_distribution = {}

        for sector in sectors:
            agents = []
            agent_count = {'AGRICULTURE': 10, 'INDUSTRY': 15, 'SERVICES': 20, 'FINANCE': 8, 'ENERGY': 12}[sector]

            for i in range(agent_count):
                agents.append({
                    'id': f'{sector}_AGENT_{i+1:02d}',
                    'balance': 800 + (hash(f'{sector}_{i}') % 800),
                    'sector': sector
                })

            agents_distribution[sector] = {
                'agents': agents,
                'count': len(agents),
                'total_balance': sum(a['balance'] for a in agents)
            }

        return {
            'agents_distribution': agents_distribution,
            'sample_results': self._generate_mock_sample_results(),
            'performance_metrics': self._generate_mock_performance_metrics()
        }

    def _generate_mock_sample_results(self) -> List[Dict[str, Any]]:
        """Génère résultats transactions mock"""
        results = []
        for i in range(15):
            results.append({
                'tx_id': f'MOCK_TX_{i+1:03d}',
                'source_id': f'AGENT_A_{i%5+1}',
                'target_id': f'AGENT_B_{(i+2)%5+1}',
                'amount': 100 + (i * 23) % 400,
                'feasibility': {
                    'success': (i % 4) != 0,  # 75% success
                    'time_ms': 20 + (i * 7) % 40
                },
                'optimization': {
                    'success': (i % 5) != 0,  # 80% success
                    'time_ms': 35 + (i * 11) % 60,
                    'optimal_price': 0.8 + (i * 0.1) % 0.4
                }
            })
        return results

    def _generate_mock_performance_metrics(self) -> Dict[str, Any]:
        """Génère métriques performance mock"""
        return {
            'agents_count': 65,
            'total_transactions': 847,
            'feasibility_rate': 87.3,
            'optimization_rate': 82.1,
            'avg_validation_time_ms': 43.7,
            'cpu_usage': 18.2,
            'memory_usage': 34.6,
            'throughput_pct': 91.4
        }

    def _generate_test_economy_data(self) -> Dict[str, Any]:
        """Génère données économie test basiques"""
        return self._generate_mock_economy_data()

    def _generate_test_transaction_data(self) -> Dict[str, Any]:
        """Génère données transaction test"""
        return {
            'tx_id': 'TEST_TX_001',
            'source_id': 'TEST_AGENT_A',
            'target_id': 'TEST_AGENT_B',
            'amount': 250.75,
            'feasibility': {'success': True, 'time_ms': 32.1},
            'optimization': {'success': True, 'time_ms': 47.8, 'optimal_price': 0.9234}
        }

    def _generate_mock_transaction_data(self, tx_id: str) -> Dict[str, Any]:
        """Génère données transaction mock"""
        return {
            'tx_id': tx_id,
            'source_id': 'MOCK_SOURCE',
            'target_id': 'MOCK_TARGET',
            'amount': 150.0,
            'feasibility': {'success': True, 'time_ms': 25.3},
            'optimization': {'success': True, 'time_ms': 41.7, 'optimal_price': 0.8765}
        }

    def _generate_test_simplex_data(self) -> Dict[str, Any]:
        """Génère données Simplex test"""
        return {
            'vertices': [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [0.5, 0.5, 0.5]],
            'constraints': [
                {'type': 'linear', 'coefficients': [1, 1, 0], 'rhs': 1},
                {'type': 'linear', 'coefficients': [1, 0, 1], 'rhs': 1},
                {'type': 'linear', 'coefficients': [0, 1, 1], 'rhs': 1}
            ],
            'simplex_steps': [
                {'step': 1, 'description': 'Initial basic solution'},
                {'step': 2, 'description': 'Pivot operation'},
                {'step': 3, 'description': 'Optimality test'},
                {'step': 4, 'description': 'Optimal solution found'}
            ],
            'optimal_solution': {
                'coordinates': [0.33, 0.33, 0.33],
                'value': 1.0,
                'feasible': True
            }
        }

    def _calculate_cache_hit_rate(self) -> float:
        """Calcule taux de succès cache"""
        # Approximation basée sur taille cache
        return min(1.0, len(self.animators_cache) / 10) * 100

    def _update_stats(self, success: bool, response_time: float):
        """Met à jour statistiques génération"""
        if success:
            self.generation_stats['successful_requests'] += 1
        else:
            self.generation_stats['failed_requests'] += 1

        # Moyenne mobile temps de réponse
        current_avg = self.generation_stats['avg_response_time']
        total_requests = self.generation_stats['total_requests']
        self.generation_stats['avg_response_time'] = (current_avg * (total_requests - 1) + response_time) / total_requests

    def _error_response(self, message: str, status_code: int) -> Response:
        """Crée réponse d'erreur standardisée"""
        return jsonify({
            'success': False,
            'error': message,
            'status_code': status_code,
            'timestamp': datetime.now().isoformat()
        }), status_code


# Fonctions utilitaires pour intégration

def register_svg_api_routes(app: Flask, web_manager=None) -> ICGSSVGAPIServer:
    """Enregistre les routes SVG API dans une app Flask existante"""
    api_server = ICGSSVGAPIServer(app, web_manager)
    return api_server


def create_standalone_svg_api_server(host: str = '0.0.0.0', port: int = 5001) -> Flask:
    """Crée serveur API SVG standalone"""
    app = Flask(__name__)
    api_server = ICGSSVGAPIServer(app)

    @app.route('/')
    def index():
        return jsonify({
            'service': 'ICGS SVG Animation API',
            'version': '1.0.0',
            'endpoints': [
                '/api/svg/economy_animation',
                '/api/svg/transaction/<tx_id>',
                '/api/svg/simplex_steps',
                '/api/svg/performance_dashboard',
                '/api/svg/custom_animation',
                '/api/svg/config',
                '/api/svg/stats',
                '/api/svg/preview'
            ],
            'timestamp': datetime.now().isoformat()
        })

    return app


if __name__ == "__main__":
    # Serveur standalone pour tests
    app = create_standalone_svg_api_server()
    port = int(os.environ.get('SVG_API_PORT', 5001))

    print("🎨 ICGS SVG API Server - Starting...")
    print(f"📊 Endpoints disponibles sur: http://localhost:{port}")
    print("   - /api/svg/economy_animation")
    print("   - /api/svg/transaction/<tx_id>")
    print("   - /api/svg/simplex_steps")
    print("   - /api/svg/performance_dashboard")
    print("   - /api/svg/config")
    print("   - /api/svg/preview?type=economy")

    app.run(debug=True, host='0.0.0.0', port=port)