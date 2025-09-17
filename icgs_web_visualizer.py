#!/usr/bin/env python3
"""
ICGS Web Visualizer - Mini Serveur de Visualisation
=====================================================

Interface web pour démontrer ICGS en action avec :
- Création d'agents économiques
- Lancement de transactions
- Visualisation temps réel du pipeline de validation
- Métriques de performance
- Dashboard des simulations

Usage: python3 icgs_web_visualizer.py
"""

import os
import sys
import json
import time
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Any

# Configuration Flask
from flask import Flask, render_template, request, jsonify, send_from_directory

# Import ICGS modules
sys.path.insert(0, os.path.dirname(__file__))
from icgs_simulation import EconomicSimulation, SECTORS
from icgs_simulation.api.icgs_bridge import SimulationMode, SimulationResult

# Import Web-Native Manager
from icgs_web_native import WebNativeICGS

# Import 3D analyzer
try:
    from icgs_3d_space_analyzer import ICGS3DSpaceAnalyzer
    ANALYZER_3D_AVAILABLE = True
except ImportError:
    ANALYZER_3D_AVAILABLE = False
    print("⚠️  3D Analyzer not available")

# Import extensions avancées
try:
    from icgs_web_extensions import register_all_extensions
    EXTENSIONS_AVAILABLE = True
except ImportError:
    EXTENSIONS_AVAILABLE = False
    print("⚠️  Extensions avancées not available")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'icgs_demo_2024'

# Global Web-Native ICGS Manager
web_manager = None
global_3d_analyzer = None  # PHASE 2A: Analyseur 3D global
simulation_history = []
performance_metrics = {
    'total_transactions': 0,
    'successful_feasibility': 0,
    'successful_optimization': 0,
    'avg_validation_time_ms': 0.0,
    'agents_count': 0,
    'sectors_used': set()
}

def init_web_manager():
    """Initialize global Web-Native ICGS Manager with pre-configured pool"""
    global web_manager, global_3d_analyzer
    if web_manager is None:
        # Créer Web-Native ICGS Manager avec pool pré-configuré
        web_manager = WebNativeICGS()
        print("🚀 WebNative ICGS Manager initialized")
        print(f"🏗️ Pool virtuel configuré avec {len(web_manager.virtual_pool)} slots")
        print(f"   Secteurs disponibles: {list(web_manager.virtual_pool.keys())}")

        # Afficher capacités des pools
        for sector, slots in web_manager.virtual_pool.items():
            print(f"   {sector}: {len(slots)} agents max - chars: {','.join([slot[1] for slot in slots])}")

        # PHASE 2A: Initialiser analyseur 3D avec mode authentique
        if ANALYZER_3D_AVAILABLE:
            global_3d_analyzer = ICGS3DSpaceAnalyzer(web_manager.icgs_core)
            success = global_3d_analyzer.enable_authentic_simplex_data(web_manager.icgs_core)
            if success:
                print("🌌 Analyseur 3D Mode Authentique activé avec WebNativeICGS")
            else:
                print("⚠️  Analyseur 3D Mode Authentique échoué")
    return web_manager

@app.route('/')
def index():
    """Page d'accueil du visualiseur ICGS"""
    return render_template('index.html')

@app.route('/api/sectors')
def api_sectors():
    """API: Liste des secteurs économiques disponibles"""
    sectors_data = {}
    for name, sector in SECTORS.items():
        sectors_data[name] = {
            'name': sector.name,
            'pattern': sector.pattern,
            'weight': float(sector.weight),
            'description': sector.description,
            'balance_range': [float(sector.typical_balance_range[0]),
                            float(sector.typical_balance_range[1])]
        }
    return jsonify(sectors_data)

@app.route('/api/agents', methods=['GET', 'POST'])
def api_agents():
    """API: Gestion des agents économiques avec WebNativeICGS"""
    manager = init_web_manager()

    if request.method == 'GET':
        # Retourner liste des agents actuels avec info pool
        agents_data = []
        if hasattr(manager.icgs_core, 'agents'):
            for agent_id, agent in manager.icgs_core.agents.items():
                # Récupérer info allocation pool
                virtual_id = manager.real_to_virtual.get(agent_id, agent_id)
                agent_info = manager.agent_registry.get(agent_id, None)

                agents_data.append({
                    'agent_id': agent_id,
                    'virtual_slot': virtual_id,
                    'sector': agent.sector,
                    'balance': float(agent.balance),
                    'metadata': agent.metadata,
                    'pool_info': {
                        'virtual_slot': virtual_id,
                        'taxonomic_char': agent_info.taxonomic_char if agent_info else 'N/A',
                        'allocated': agent_id in manager.real_to_virtual
                    }
                })
        return jsonify(agents_data)

    elif request.method == 'POST':
        # Créer nouvel agent avec allocation automatique de slot
        data = request.json
        try:
            agent_id = data['agent_id']
            sector = data['sector']
            balance = Decimal(str(data['balance']))
            metadata = data.get('metadata', {})

            # Utiliser WebNativeICGS pour allocation automatique
            agent_info = manager.add_agent(agent_id, sector, balance, metadata)

            # Mise à jour métriques
            performance_metrics['agents_count'] += 1
            performance_metrics['sectors_used'].add(sector)

            return jsonify({
                'success': True,
                'message': f'Agent {agent_id} alloué sur slot {agent_info.virtual_slot}',
                'agent': {
                    'agent_id': agent_id,
                    'virtual_slot': agent_info.virtual_slot,
                    'sector': sector,
                    'balance': float(balance),
                    'metadata': metadata,
                    'pool_info': {
                        'virtual_slot': agent_info.virtual_slot,
                        'taxonomic_char': agent_info.taxonomic_char,
                        'allocated': True
                    }
                }
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400

@app.route('/api/transaction', methods=['POST'])
def api_transaction():
    """API: Créer et valider une transaction avec WebNativeICGS"""
    manager = init_web_manager()

    try:
        data = request.json
        source_id = data['source_id']
        target_id = data['target_id']
        amount = Decimal(str(data['amount']))

        # Utiliser WebNativeICGS pour traitement transaction
        result = manager.process_transaction(source_id, target_id, amount)

        if result['success']:
            transaction_record = result['transaction_record']

            # Mise à jour métriques
            performance_metrics['total_transactions'] += 1
            if transaction_record['feasibility']['success']:
                performance_metrics['successful_feasibility'] += 1
            if transaction_record['optimization']['success']:
                performance_metrics['successful_optimization'] += 1

            avg_time = (transaction_record['feasibility']['time_ms'] + transaction_record['optimization']['time_ms']) / 2
            current_avg = performance_metrics['avg_validation_time_ms']
            total_tx = performance_metrics['total_transactions']
            performance_metrics['avg_validation_time_ms'] = (current_avg * (total_tx - 1) + avg_time) / total_tx

            # PHASE 2A: Collecter données animation 3D pour cette transaction
            animation_data = None
            if manager.icgs_core and hasattr(manager.icgs_core, 'get_3d_collector'):
                collector = manager.icgs_core.get_3d_collector()
                if collector and len(collector.states_history) > 0:
                    animation_data = collector.export_animation_data()
                    transaction_record['animation'] = animation_data

            simulation_history.append(transaction_record)

            return jsonify({
                'success': True,
                'transaction': transaction_record,
                'suggestions': result.get('suggestions', [])  # Inclure suggestions contextuelles
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/transaction/suggestions', methods=['POST'])
def api_transaction_suggestions():
    """API: Obtenir suggestions contextuelles pour transaction"""
    manager = init_web_manager()

    try:
        data = request.json
        source_id = data.get('source_id')
        target_id = data.get('target_id')
        amount = data.get('amount')

        # Obtenir suggestions contextuelles sans imposer
        suggestions = manager.get_contextual_suggestions(source_id, target_id, amount)

        return jsonify({
            'success': True,
            'suggestions': suggestions
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/metrics')
def api_metrics():
    """API: Métriques de performance actuelles + données WebNativeICGS + pool info"""
    manager = init_web_manager()

    # Obtenir stats DAG si disponibles
    dag_stats = {}
    if manager.icgs_core and hasattr(manager.icgs_core, 'dag'):
        dag_stats = getattr(manager.icgs_core.dag, 'stats', {})

    # PHASE 2A: Intégrer données 3D dans métriques existantes
    simplex_3d_data = {}
    if manager.icgs_core and hasattr(manager.icgs_core, 'get_3d_collector'):
        collector = manager.icgs_core.get_3d_collector()
        if collector:
            simplex_3d_data = {
                'states_captured': len(collector.states_history),
                'transitions_captured': len(collector.transitions_history),
                'last_animation_ready': len(collector.states_history) > 0,
                'last_animation_data': collector.export_animation_data() if len(collector.states_history) > 0 else None
            }

    # WebNativeICGS: Informations pool
    pool_info = {}
    for sector, slots in manager.virtual_pool.items():
        # Check allocated slots based on real mappings
        allocated = len(manager.allocated_slots.get(sector, set()))
        pool_info[sector] = {
            'total_capacity': len(slots),
            'allocated': allocated,
            'available': len(slots) - allocated,
            'characters': [slot[1] for slot in slots]  # slot[1] is the character
        }

    return jsonify({
        'performance': {
            **performance_metrics,
            'sectors_used': list(performance_metrics['sectors_used'])
        },
        'dag_stats': dag_stats,
        'history_count': len(simulation_history),
        'simplex_3d': simplex_3d_data,  # PHASE 2A: Données 3D intégrées
        'pool_status': pool_info  # NOUVEAU: Status du pool WebNativeICGS
    })

@app.route('/api/history')
def api_history():
    """API: Historique des transactions"""
    limit = request.args.get('limit', 20, type=int)
    return jsonify(simulation_history[-limit:])

@app.route('/api/simulation/run_demo')
def api_run_demo():
    """API: Lancer simulation de démonstration avec WebNativeICGS"""
    manager = init_web_manager()

    try:
        # Reset simulation
        global simulation_history, performance_metrics
        simulation_history = []
        performance_metrics = {
            'total_transactions': 0,
            'successful_feasibility': 0,
            'successful_optimization': 0,
            'avg_validation_time_ms': 0.0,
            'agents_count': 0,
            'sectors_used': set()
        }

        # Créer agents de démonstration avec allocation automatique de slots
        demo_agents = [
            ('ALICE_FARM', 'AGRICULTURE', Decimal('1500'), {'name': 'Alice Farm', 'region': 'Nord'}),
            ('BOB_INDUSTRY', 'INDUSTRY', Decimal('800'), {'name': 'Bob Manufacturing', 'type': 'primary'}),
            ('CAROL_SERVICES', 'SERVICES', Decimal('600'), {'name': 'Carol Logistics', 'type': 'transport'})
        ]

        created_agents = []
        for agent_id, sector, balance, metadata in demo_agents:
            try:
                # Vérifier si l'agent existe déjà
                if agent_id in manager.real_to_virtual:
                    # Agent existe déjà, utiliser l'agent existant
                    agent_info = manager.agent_registry[agent_id]
                    created_agents.append({
                        'agent_id': agent_id,
                        'virtual_slot': agent_info.virtual_slot,
                        'sector': agent_info.sector,
                        'status': 'exists'
                    })
                    performance_metrics['sectors_used'].add(sector)
                else:
                    # Créer nouvel agent
                    agent_info = manager.add_agent(agent_id, sector, balance, metadata)
                    performance_metrics['agents_count'] += 1
                    performance_metrics['sectors_used'].add(sector)
                    created_agents.append({
                        'agent_id': agent_id,
                        'virtual_slot': agent_info.virtual_slot,
                        'sector': agent_info.sector,
                        'status': 'created'
                    })
            except Exception as e:
                print(f"⚠️ Erreur création agent {agent_id}: {e}")
                # Continuer avec les autres agents

        # Créer transactions de démonstration
        demo_transactions = [
            ('ALICE_FARM', 'BOB_INDUSTRY', Decimal('120')),
            ('BOB_INDUSTRY', 'CAROL_SERVICES', Decimal('85'))
        ]

        results = []
        for source, target, amount in demo_transactions:
            try:
                print(f"🔄 Test transaction: {source} → {target} ({amount})")
                result = manager.process_transaction(source, target, amount)
                print(f"   Result: success={result['success']}")
                if not result['success']:
                    print(f"   Error: {result.get('error', 'Unknown error')}")
                    print(f"   Full result: {result}")  # Debug complet

                if result['success']:
                    tx_record = result['transaction_record']
                    performance_metrics['total_transactions'] += 1
                    if tx_record['feasibility']['success']:
                        performance_metrics['successful_feasibility'] += 1
                    if tx_record['optimization']['success']:
                        performance_metrics['successful_optimization'] += 1

                    results.append({
                        'tx_id': tx_record['tx_id'],
                        'source': source,
                        'target': target,
                        'amount': float(amount),
                        'feasibility_success': tx_record['feasibility']['success'],
                        'optimization_success': tx_record['optimization']['success']
                    })

                    simulation_history.append(tx_record)
            except Exception as e:
                print(f"   ❌ Exception during transaction: {e}")
                # Continuer avec les autres transactions

        return jsonify({
            'success': True,
            'message': 'Simulation de démonstration WebNativeICGS terminée',
            'results': results,
            'agents_created': len(created_agents),
            'transactions_processed': len([r for r in results]),
            'pool_allocations': created_agents
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/analyze_3d')
def api_analyze_3d():
    """API: Analyser l'espace 3D des solutions Simplex"""
    if not ANALYZER_3D_AVAILABLE:
        return jsonify({
            'success': False,
            'error': '3D Analyzer not available'
        }), 501

    sim = init_simulation()

    try:
        # Créer analyseur 3D
        analyzer = ICGS3DSpaceAnalyzer(sim)

        # Générer données 3D avec transactions d'analyse
        transactions_3d = [
            ('ALICE_FARM', 'BOB_INDUSTRY', Decimal('500')),
            ('BOB_INDUSTRY', 'CAROL_SERVICES', Decimal('300')),
            ('CAROL_SERVICES', 'ALICE_FARM', Decimal('150'))
        ]

        solution_points = []
        for source, target, amount in transactions_3d:
            try:
                point = analyzer.analyze_transaction_3d_space(source, target, amount)
                solution_points.append({
                    'coordinates': [point.x, point.y, point.z],
                    'transaction_id': point.transaction_id,
                    'feasible': point.feasible,
                    'optimal': point.optimal,
                    'metadata': point.metadata
                })
            except Exception as tx_error:
                print(f"Erreur transaction 3D: {tx_error}")
                continue

        # Préparer données pour retour JSON
        analysis_3d = {
            'metadata': {
                'total_points': len(solution_points),
                'feasible_points': sum(1 for p in solution_points if p['feasible']),
                'optimal_points': sum(1 for p in solution_points if p['optimal']),
                'analysis_timestamp': datetime.now().isoformat()
            },
            'solution_points': solution_points,
            'axis_labels': {
                'x': 'Contraintes SOURCE (Débiteur)',
                'y': 'Contraintes TARGET (Créditeur)',
                'z': 'Contraintes SECONDARY (Bonus/Malus)'
            }
        }

        return jsonify({
            'success': True,
            'data_3d': analysis_3d,
            'message': f'Analyse 3D complétée: {len(solution_points)} points'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/icgs_3d_space.json')
def serve_3d_data():
    """Servir le fichier JSON des données 3D"""
    try:
        return send_from_directory('.', 'icgs_3d_space.json')
    except FileNotFoundError:
        return jsonify({'error': 'Données 3D non disponibles'}), 404

@app.route('/3d')
def view_3d():
    """Page visualisation 3D"""
    return send_from_directory('.', 'icgs_3d_visualizer.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Servir les fichiers statiques"""
    return send_from_directory('static', filename)

# =====================================
# API 3D ÉCONOMIE MASSIVE - NOUVELLE ARCHITECTURE TRANSACTION-CENTRÉE
# =====================================

@app.route('/api/economy/launch_3d', methods=['POST'])
def api_launch_massive_economy_3d():
    """Lance économie 65 agents avec analyse 3D intégrée - Élimination WebNativeICGS"""

    try:
        config = request.json
        flow_intensity = config.get('flow_intensity', 0.7)
        collect_3d_data = config.get('collect_3d', True)
        authentic_simplex = config.get('authentic_simplex', True)
        agents_mode = config.get('agents_mode', '65_agents')

        print(f"🌌 Lancement économie 3D massive: {agents_mode}, intensity={flow_intensity}")

        # DIRECT: Utilisation EconomicSimulation sans pool WebNativeICGS
        from icgs_simulation.api.icgs_bridge import EconomicSimulation
        simulation = EconomicSimulation(f"web_3d_economy_{int(time.time())}", agents_mode=agents_mode)

        # Activation analyse 3D native si demandée
        analysis_3d_enabled = False
        if collect_3d_data:
            analysis_3d_enabled = simulation.enable_3d_analysis(use_authentic_data=authentic_simplex)
            if analysis_3d_enabled:
                print(f"✅ Analyse 3D native activée avec données {'authentiques' if authentic_simplex else 'approximées'}")

        # Génération transactions inter-sectorielles avec analyse 3D
        if analysis_3d_enabled:
            transaction_ids, data_3d = simulation.create_inter_sectoral_flows_batch_3d(
                flow_intensity=flow_intensity,
                enable_3d_analysis=True
            )
        else:
            # Fallback sans analyse 3D
            transaction_ids = simulation.create_inter_sectoral_flows_batch(flow_intensity)
            data_3d = {'error': 'Analyse 3D non disponible'}

        # Validation échantillon pour métriques web
        sample_results = []
        sample_size = min(20, len(transaction_ids))

        for tx_id in transaction_ids[:sample_size]:
            try:
                feas_result = simulation.validate_transaction(tx_id, simulation.SimulationMode.FEASIBILITY)
                opt_result = simulation.validate_transaction(tx_id, simulation.SimulationMode.OPTIMIZATION)

                # Récupérer détails transaction pour affichage
                transaction = next((tx for tx in simulation.transactions if tx.transaction_id == tx_id), None)

                sample_results.append({
                    'tx_id': tx_id,
                    'source_id': transaction.source_account_id if transaction else 'N/A',
                    'target_id': transaction.target_account_id if transaction else 'N/A',
                    'amount': float(transaction.amount) if transaction else 0,
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
            except Exception as e:
                print(f"⚠️ Erreur validation échantillon {tx_id}: {e}")

        # Statistiques agents par secteur (mode 65 agents)
        agents_distribution = {}
        for agent_id, agent in simulation.agents.items():
            sector = agent.sector
            if sector not in agents_distribution:
                agents_distribution[sector] = {'count': 0, 'total_balance': 0, 'agents': []}

            agents_distribution[sector]['count'] += 1
            agents_distribution[sector]['total_balance'] += float(agent.balance)
            agents_distribution[sector]['agents'].append({
                'id': agent_id,
                'balance': float(agent.balance)
            })

        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'agents_mode': agents_mode,
            'agents_created': len(simulation.agents),
            'agents_distribution': agents_distribution,
            'transactions_generated': len(transaction_ids),
            'sample_results': sample_results,
            'performance_metrics': {
                'feasible_sample': sum(1 for r in sample_results if r['feasibility']['success']),
                'optimal_sample': sum(1 for r in sample_results if r['optimization']['success']),
                'avg_feasibility_time': sum(r['feasibility']['time_ms'] for r in sample_results) / max(len(sample_results), 1),
                'avg_optimization_time': sum(r['optimization']['time_ms'] for r in sample_results) / max(len(sample_results), 1)
            },
            'analysis_3d': {
                'enabled': analysis_3d_enabled,
                'data': data_3d if analysis_3d_enabled else None,
                'authentic_mode': authentic_simplex and analysis_3d_enabled
            },
            'flow_intensity': flow_intensity
        })

    except Exception as e:
        print(f"❌ Erreur lancement économie 3D: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/transactions/3d')
def api_get_transactions_3d():
    """Navigation paginée des transactions avec données 3D"""

    try:
        # Paramètres de pagination et filtres
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        filter_status = request.args.get('status', 'all')  # all, feasible, failed
        sector_filter = request.args.get('sector', 'all')

        # Pour cette version, utiliser simulation globale (sera étendu avec session management)
        global web_manager

        if not web_manager or not hasattr(web_manager, 'icgs_core'):
            return jsonify({
                'success': False,
                'error': 'Économie 3D non lancée - Utilisez /api/economy/launch_3d d\'abord'
            }), 400

        simulation = web_manager.icgs_core

        # Récupérer toutes les transactions
        all_transactions = []
        for i, tx in enumerate(simulation.transactions):
            # Simuler validation pour status (optimisation future: cache)
            try:
                feas_result = simulation.validate_transaction(tx.transaction_id, simulation.SimulationMode.FEASIBILITY)

                tx_data = {
                    'tx_id': tx.transaction_id,
                    'source_id': tx.source_account_id,
                    'target_id': tx.target_account_id,
                    'amount': float(tx.amount),
                    'feasible': feas_result.success,
                    'validation_time_ms': feas_result.validation_time_ms,
                    'timestamp': datetime.now().isoformat()  # Placeholder
                }

                # Filtrage
                if filter_status == 'feasible' and not tx_data['feasible']:
                    continue
                elif filter_status == 'failed' and tx_data['feasible']:
                    continue

                all_transactions.append(tx_data)

            except Exception as e:
                print(f"Erreur status transaction {tx.transaction_id}: {e}")

        # Pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_transactions = all_transactions[start_idx:end_idx]

        return jsonify({
            'success': True,
            'transactions': paginated_transactions,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_transactions': len(all_transactions),
                'total_pages': (len(all_transactions) + per_page - 1) // per_page,
                'has_next': end_idx < len(all_transactions),
                'has_prev': page > 1
            },
            'filters': {
                'status': filter_status,
                'sector': sector_filter
            },
            'stats': {
                'total': len(all_transactions),
                'feasible': sum(1 for tx in all_transactions if tx['feasible']),
                'failed': sum(1 for tx in all_transactions if not tx['feasible'])
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/transaction/<tx_id>/3d_detail')
def api_get_transaction_3d_detail(tx_id):
    """Détails 3D complets pour une transaction spécifique"""

    try:
        global web_manager

        if not web_manager or not hasattr(web_manager, 'icgs_core'):
            return jsonify({
                'success': False,
                'error': 'Économie 3D non disponible'
            }), 400

        simulation = web_manager.icgs_core

        # Trouver la transaction
        transaction = next((tx for tx in simulation.transactions if tx.transaction_id == tx_id), None)
        if not transaction:
            return jsonify({
                'success': False,
                'error': f'Transaction {tx_id} non trouvée'
            }), 404

        # Validation complète
        feas_result = simulation.validate_transaction(tx_id, simulation.SimulationMode.FEASIBILITY)
        opt_result = simulation.validate_transaction(tx_id, simulation.SimulationMode.OPTIMIZATION)

        # Analyse 3D si disponible
        analysis_3d = None
        if hasattr(simulation, 'icgs_3d_analyzer') and simulation.icgs_3d_analyzer:
            try:
                point_3d = simulation.analyze_transaction_3d(
                    transaction.source_account_id,
                    transaction.target_account_id,
                    transaction.amount
                )
                if point_3d:
                    analysis_3d = {
                        'coordinates': [point_3d.x, point_3d.y, point_3d.z],
                        'feasible': point_3d.feasible,
                        'optimal': point_3d.optimal,
                        'pivot_step': point_3d.pivot_step,
                        'pivot_type': point_3d.pivot_type,
                        'metadata': point_3d.metadata
                    }
            except Exception as e:
                print(f"Erreur analyse 3D pour {tx_id}: {e}")

        # Informations agents source/target
        source_agent = simulation.agents.get(transaction.source_account_id)
        target_agent = simulation.agents.get(transaction.target_account_id)

        return jsonify({
            'success': True,
            'tx_id': tx_id,
            'transaction_details': {
                'source_id': transaction.source_account_id,
                'target_id': transaction.target_account_id,
                'amount': float(transaction.amount),
                'timestamp': datetime.now().isoformat()  # Placeholder
            },
            'agents': {
                'source': {
                    'id': transaction.source_account_id,
                    'sector': source_agent.sector if source_agent else 'Unknown',
                    'balance': float(source_agent.balance) if source_agent else 0
                },
                'target': {
                    'id': transaction.target_account_id,
                    'sector': target_agent.sector if target_agent else 'Unknown',
                    'balance': float(target_agent.balance) if target_agent else 0
                }
            },
            'validation_pipeline': {
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
                }
            },
            'analysis_3d': analysis_3d
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sectors/3d_matrix')
def api_get_sectoral_3d_matrix():
    """Matrice 3D flux inter-sectoriels pour visualisation massive"""

    try:
        global web_manager

        if not web_manager or not hasattr(web_manager, 'icgs_core'):
            return jsonify({
                'success': False,
                'error': 'Économie 3D non disponible'
            }), 400

        simulation = web_manager.icgs_core

        # Calculer matrice flux inter-sectoriels
        sectors = ['AGRICULTURE', 'INDUSTRY', 'SERVICES', 'FINANCE', 'ENERGY']
        flux_matrix = {}

        for source_sector in sectors:
            flux_matrix[source_sector] = {}
            for target_sector in sectors:
                flux_matrix[source_sector][target_sector] = {
                    'transaction_count': 0,
                    'total_amount': 0.0,
                    'avg_feasibility_rate': 0.0,
                    'transactions': []
                }

        # Analyser toutes les transactions
        for tx in simulation.transactions:
            source_agent = simulation.agents.get(tx.source_account_id)
            target_agent = simulation.agents.get(tx.target_account_id)

            if source_agent and target_agent:
                source_sector = source_agent.sector
                target_sector = target_agent.sector

                if source_sector in flux_matrix and target_sector in flux_matrix[source_sector]:
                    flux_matrix[source_sector][target_sector]['transaction_count'] += 1
                    flux_matrix[source_sector][target_sector]['total_amount'] += float(tx.amount)
                    flux_matrix[source_sector][target_sector]['transactions'].append(tx.transaction_id)

        # Calculer centroides 3D par secteur si analyse 3D disponible
        sector_centroids = {}
        if hasattr(simulation, 'icgs_3d_analyzer') and simulation.icgs_3d_analyzer:
            # Calculer position moyenne 3D pour chaque secteur
            for sector in sectors:
                sector_points = []
                for point in simulation.icgs_3d_analyzer.solution_points:
                    # Associer point à secteur via metadata si disponible
                    if 'source_sector' in point.metadata and point.metadata['source_sector'] == sector:
                        sector_points.append([point.x, point.y, point.z])

                if sector_points:
                    # Centroide = moyenne des coordonnées
                    centroid = [
                        sum(p[0] for p in sector_points) / len(sector_points),
                        sum(p[1] for p in sector_points) / len(sector_points),
                        sum(p[2] for p in sector_points) / len(sector_points)
                    ]
                    sector_centroids[sector] = centroid
                else:
                    # Position par défaut si pas de données 3D
                    sector_centroids[sector] = [0, 0, 0]

        # Statistiques par secteur
        sector_stats = {}
        for sector in sectors:
            sector_agents = [a for a in simulation.agents.values() if a.sector == sector]
            sector_stats[sector] = {
                'agents_count': len(sector_agents),
                'total_balance': sum(float(a.balance) for a in sector_agents),
                'avg_balance': sum(float(a.balance) for a in sector_agents) / max(len(sector_agents), 1),
                'centroid_3d': sector_centroids.get(sector, [0, 0, 0])
            }

        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'flux_matrix': flux_matrix,
            'sector_centroids': sector_centroids,
            'sector_statistics': sector_stats,
            'axes_labels': {
                'x': 'Contraintes SOURCE (Débiteur)',
                'y': 'Contraintes TARGET (Créditeur)',
                'z': 'Contraintes SECONDARY (Bonus/Malus)'
            },
            'total_sectors': len(sectors),
            'total_agents': len(simulation.agents),
            'analysis_3d_available': hasattr(simulation, 'icgs_3d_analyzer') and simulation.icgs_3d_analyzer is not None
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Template HTML intégré
@app.route('/api/performance/stats')
def api_performance_stats():
    """API: Statistiques performance complètes avec cache optimisé pour 65 agents"""
    try:
        global web_manager

        if not web_manager or not hasattr(web_manager, 'icgs_core'):
            return jsonify({
                'success': False,
                'error': 'Simulation non disponible'
            }), 400

        simulation = web_manager.icgs_core

        # Statistiques performance complètes
        if hasattr(simulation, 'get_performance_stats'):
            performance_stats = simulation.get_performance_stats()
        else:
            # Fallback pour ancienne version
            performance_stats = {
                'cache_performance': {'hit_rate_percent': 0, 'note': 'Cache non disponible'},
                'simulation': {
                    'agents_count': len(getattr(simulation, 'agents', {})),
                    'transactions_count': len(getattr(simulation, 'transactions', [])),
                    'agents_mode': getattr(simulation, 'agents_mode', 'unknown')
                }
            }

        return jsonify({
            'success': True,
            'performance_stats': performance_stats,
            'timestamp': time.time()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/performance/optimize', methods=['POST'])
def api_optimize_for_web():
    """API: Optimiser performance pour charge web massive (65 agents)"""
    try:
        global web_manager

        if not web_manager or not hasattr(web_manager, 'icgs_core'):
            return jsonify({
                'success': False,
                'error': 'Simulation non disponible'
            }), 400

        simulation = web_manager.icgs_core

        # Appliquer optimisations web
        if hasattr(simulation, 'optimize_for_web_load'):
            simulation.optimize_for_web_load()
            message = "Optimisations web appliquées avec succès"
        else:
            message = "Optimisations non supportées par cette version"

        # Statistiques après optimisation
        stats_after = {}
        if hasattr(simulation, 'get_performance_stats'):
            stats_after = simulation.get_performance_stats()

        return jsonify({
            'success': True,
            'message': message,
            'optimizations_applied': [
                'Cache pré-chargé pour patterns fréquents',
                'Taxonomie configurée',
                'Paramètres TTL ajustés pour web',
                'Structures de données optimisées'
            ],
            'performance_stats': stats_after
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/performance/cache/clear', methods=['POST'])
def api_clear_performance_cache():
    """API: Vider le cache de performance (utile pour tests/développement)"""
    try:
        global web_manager

        if not web_manager or not hasattr(web_manager, 'icgs_core'):
            return jsonify({
                'success': False,
                'error': 'Simulation non disponible'
            }), 400

        simulation = web_manager.icgs_core

        # Vider cache
        if hasattr(simulation, 'clear_performance_cache'):
            simulation.clear_performance_cache()
            message = "Cache de performance vidé avec succès"
        else:
            message = "Cache non disponible sur cette version"

        return jsonify({
            'success': True,
            'message': message,
            'timestamp': time.time()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ICGS Web Visualizer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
               min-height: 100vh; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; color: white; margin-bottom: 30px; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { font-size: 1.1em; opacity: 0.9; }
        .dashboard { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
        .card { background: white; border-radius: 15px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
        .card h3 { color: #5a67d8; margin-bottom: 20px; font-size: 1.3em; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: 600; }
        .form-group input, .form-group select { width: 100%; padding: 10px; border: 2px solid #e2e8f0;
                                               border-radius: 8px; font-size: 16px; }
        .btn { background: #5a67d8; color: white; border: none; padding: 12px 24px;
               border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: 600;
               transition: background 0.3s; }
        .btn:hover { background: #4c51bf; }
        .btn-success { background: #38a169; }
        .btn-success:hover { background: #2f855a; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .metric-card { background: #f7fafc; border-left: 4px solid #5a67d8; padding: 15px; border-radius: 8px; }
        .metric-value { font-size: 2em; font-weight: bold; color: #5a67d8; }
        .metric-label { color: #718096; margin-top: 5px; }
        .history { max-height: 400px; overflow-y: auto; }
        .transaction-item { background: #f7fafc; margin: 10px 0; padding: 15px; border-radius: 8px;
                          border-left: 4px solid #38a169; }
        .transaction-item.failed { border-left-color: #e53e3e; }
        .status { display: inline-block; padding: 4px 8px; border-radius: 4px; color: white; font-size: 12px; }
        .status.success { background: #38a169; }
        .status.failed { background: #e53e3e; }
        .loading { text-align: center; padding: 20px; }
        .full-width { grid-column: 1 / -1; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 ICGS Web Visualizer</h1>
            <p>Interface de Démonstration - Intelligent Computation Graph System</p>
        </div>

        <div class="dashboard">
            <!-- Création d'agents -->
            <div class="card">
                <h3>👥 Création d'Agents Économiques</h3>
                <form id="agentForm">
                    <div class="form-group">
                        <label for="agentId">ID Agent:</label>
                        <input type="text" id="agentId" placeholder="ALICE_FARM" required>
                    </div>
                    <div class="form-group">
                        <label for="sector">Secteur:</label>
                        <select id="sector" required>
                            <option value="">Sélectionner secteur...</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="balance">Balance initiale:</label>
                        <input type="number" id="balance" placeholder="1000" step="0.01" required>
                    </div>
                    <button type="submit" class="btn">Créer Agent</button>
                </form>
            </div>

            <!-- Transaction -->
            <div class="card">
                <h3>💰 Validation de Transaction</h3>
                <form id="transactionForm">
                    <div class="form-group">
                        <label for="sourceId">Agent Source:</label>
                        <input type="text" id="sourceId" placeholder="ALICE_FARM" required>
                    </div>
                    <div class="form-group">
                        <label for="targetId">Agent Cible:</label>
                        <input type="text" id="targetId" placeholder="BOB_INDUSTRY" required>
                    </div>
                    <div class="form-group">
                        <label for="amount">Montant:</label>
                        <input type="number" id="amount" placeholder="100" step="0.01" required>
                    </div>
                    <button type="submit" class="btn">Valider Transaction</button>
                </form>
            </div>

            <!-- Métriques -->
            <div class="card full-width">
                <h3>📊 Métriques de Performance</h3>
                <div id="metricsContainer" class="metrics">
                    <div class="loading">Chargement des métriques...</div>
                </div>
            </div>

            <!-- Historique -->
            <div class="card full-width">
                <h3>📋 Historique des Transactions</h3>
                <button id="runDemo" class="btn btn-success" style="margin-bottom: 15px;">
                    🎯 Lancer Simulation Démo
                </button>
                <div id="historyContainer" class="history">
                    <div class="loading">Aucune transaction encore...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // État global
        let sectors = {};
        let updateInterval;

        // Initialisation
        document.addEventListener('DOMContentLoaded', function() {
            loadSectors();
            updateMetrics();
            updateHistory();

            // Mise à jour automatique toutes les 5 secondes
            updateInterval = setInterval(() => {
                updateMetrics();
                updateHistory();
            }, 5000);
        });

        // Charger secteurs disponibles
        async function loadSectors() {
            try {
                const response = await fetch('/api/sectors');
                sectors = await response.json();

                const sectorSelect = document.getElementById('sector');
                sectorSelect.innerHTML = '<option value="">Sélectionner secteur...</option>';

                Object.keys(sectors).forEach(name => {
                    const sector = sectors[name];
                    const option = document.createElement('option');
                    option.value = name;
                    option.textContent = `${name} - ${sector.description}`;
                    sectorSelect.appendChild(option);
                });
            } catch (error) {
                console.error('Erreur chargement secteurs:', error);
            }
        }

        // Mise à jour métriques
        async function updateMetrics() {
            try {
                const response = await fetch('/api/metrics');
                const data = await response.json();

                const container = document.getElementById('metricsContainer');
                const perf = data.performance;

                const successRateFeas = perf.total_transactions > 0 ?
                    (perf.successful_feasibility / perf.total_transactions * 100).toFixed(1) : 0;
                const successRateOpt = perf.total_transactions > 0 ?
                    (perf.successful_optimization / perf.total_transactions * 100).toFixed(1) : 0;

                container.innerHTML = `
                    <div class="metric-card">
                        <div class="metric-value">${perf.agents_count}</div>
                        <div class="metric-label">Agents Créés</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${perf.total_transactions}</div>
                        <div class="metric-label">Transactions Totales</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${successRateFeas}%</div>
                        <div class="metric-label">Succès FEASIBILITY</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${successRateOpt}%</div>
                        <div class="metric-label">Succès OPTIMIZATION</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${perf.avg_validation_time_ms.toFixed(2)}ms</div>
                        <div class="metric-label">Temps Moyen</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${perf.sectors_used.length}</div>
                        <div class="metric-label">Secteurs Utilisés</div>
                    </div>
                `;
            } catch (error) {
                console.error('Erreur métriques:', error);
            }
        }

        // Mise à jour historique
        async function updateHistory() {
            try {
                const response = await fetch('/api/history?limit=10');
                const history = await response.json();

                const container = document.getElementById('historyContainer');

                if (history.length === 0) {
                    container.innerHTML = '<div class="loading">Aucune transaction encore...</div>';
                    return;
                }

                container.innerHTML = history.reverse().map(tx => `
                    <div class="transaction-item ${tx.feasibility.success && tx.optimization.success ? '' : 'failed'}">
                        <strong>${tx.tx_id}</strong>: ${tx.source_id} → ${tx.target_id} (${tx.amount})
                        <br>
                        <span class="status ${tx.feasibility.success ? 'success' : 'failed'}">
                            FEASIBILITY: ${tx.feasibility.success ? '✓' : '✗'} (${tx.feasibility.time_ms}ms)
                        </span>
                        <span class="status ${tx.optimization.success ? 'success' : 'failed'}">
                            OPTIMIZATION: ${tx.optimization.success ? '✓' : '✗'} (${tx.optimization.time_ms}ms)
                        </span>
                        <small style="float: right; color: #718096;">
                            ${new Date(tx.timestamp).toLocaleTimeString()}
                        </small>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Erreur historique:', error);
            }
        }

        // Form handlers
        document.getElementById('agentForm').addEventListener('submit', async function(e) {
            e.preventDefault();

            const agentId = document.getElementById('agentId').value;
            const sector = document.getElementById('sector').value;
            const balance = document.getElementById('balance').value;

            try {
                const response = await fetch('/api/agents', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        agent_id: agentId,
                        sector: sector,
                        balance: parseFloat(balance),
                        metadata: {name: agentId, created_via: 'web_interface'}
                    })
                });

                const result = await response.json();
                if (result.success) {
                    alert(`✅ Agent ${agentId} créé avec succès!`);
                    this.reset();
                } else {
                    alert(`❌ Erreur: ${result.error}`);
                }
            } catch (error) {
                alert(`❌ Erreur: ${error.message}`);
            }
        });

        document.getElementById('transactionForm').addEventListener('submit', async function(e) {
            e.preventDefault();

            const sourceId = document.getElementById('sourceId').value;
            const targetId = document.getElementById('targetId').value;
            const amount = document.getElementById('amount').value;

            try {
                const response = await fetch('/api/transaction', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        source_id: sourceId,
                        target_id: targetId,
                        amount: parseFloat(amount)
                    })
                });

                const result = await response.json();
                if (result.success) {
                    const tx = result.transaction;
                    alert(`✅ Transaction validée!\nFEASIBILITY: ${tx.feasibility.success ? '✓' : '✗'}\nOPTIMIZATION: ${tx.optimization.success ? '✓' : '✗'}`);
                    this.reset();
                } else {
                    alert(`❌ Erreur: ${result.error}`);
                }
            } catch (error) {
                alert(`❌ Erreur: ${error.message}`);
            }
        });

        document.getElementById('runDemo').addEventListener('click', async function() {
            this.disabled = true;
            this.textContent = '⏳ Lancement démo...';

            try {
                const response = await fetch('/api/simulation/run_demo');
                const result = await response.json();

                if (result.success) {
                    alert(`✅ ${result.message}\n${result.agents_created} agents créés\n${result.transactions_processed} transactions traitées`);
                } else {
                    alert(`❌ Erreur: ${result.error}`);
                }
            } catch (error) {
                alert(`❌ Erreur: ${error.message}`);
            } finally {
                this.disabled = false;
                this.textContent = '🎯 Lancer Simulation Démo';
            }
        });
    </script>
</body>
</html>
"""

# Créer template directory si nécessaire
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
os.makedirs(template_dir, exist_ok=True)

# Écrire template HTML
with open(os.path.join(template_dir, 'index.html'), 'w', encoding='utf-8') as f:
    f.write(HTML_TEMPLATE)

if __name__ == '__main__':
    print("🚀 Démarrage ICGS Web Visualizer...")
    # Enregistrer extensions avancées
    if EXTENSIONS_AVAILABLE:
        register_all_extensions(app)

    print("✨ Fonctionnalités:")
    print("   - Création d'agents économiques")
    print("   - Validation de transactions (FEASIBILITY + OPTIMIZATION)")
    print("   - Métriques temps réel")
    print("   - Simulation de démonstration")
    print("   - Historique des transactions")
    if EXTENSIONS_AVAILABLE:
        print("   - Simulations académiques avancées")
        print("   - Analyse contraintes sectorielles")
        print("   - Validation théorèmes ICGS")
    print()

    port = int(os.environ.get('PORT', 5000))
    print(f"📊 Interface disponible sur: http://localhost:{port}")
    app.run(debug=True, host='0.0.0.0', port=port)