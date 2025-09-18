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

# Import Transaction Simplex Analyzer
try:
    from icgs_transaction_simplex_analyzer import (
        TransactionSimplexAnalyzer, TransactionSimplexData,
        SimulationSequenceData, create_transaction_simplex_analyzer
    )
    TRANSACTION_SIMPLEX_AVAILABLE = True
except ImportError:
    TRANSACTION_SIMPLEX_AVAILABLE = False
    print("⚠️  Transaction Simplex Analyzer not available")

# Import SVG Animation API
try:
    from icgs_svg_api import register_svg_api_routes, ICGSSVGAPIServer
    from icgs_svg_animator import ICGSSVGAnimator
    from svg_templates import SVGConfig
    SVG_API_AVAILABLE = True
except ImportError:
    SVG_API_AVAILABLE = False
    print("⚠️  SVG Animation API not available")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'icgs_demo_2024'

# Global Web-Native ICGS Manager
web_manager = None
global_3d_analyzer = None  # PHASE 2A: Analyseur 3D global
global_transaction_simplex_analyzer = None  # PHASE 2B: Analyseur Simplex Transaction
global_svg_api_server = None  # API SVG Animation Server
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
    global web_manager, global_3d_analyzer, global_transaction_simplex_analyzer, global_svg_api_server
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

        # PHASE 2B: Initialiser analyseur Simplex Transaction
        if TRANSACTION_SIMPLEX_AVAILABLE:
            try:
                global_transaction_simplex_analyzer = create_transaction_simplex_analyzer(web_manager.icgs_core)
                print("🎯 Transaction Simplex Analyzer initialisé avec WebNativeICGS")
            except Exception as e:
                print(f"❌ Erreur initialisation Transaction Simplex Analyzer: {e}")
                global_transaction_simplex_analyzer = None
        else:
            print("⚠️  Transaction Simplex Analyzer non disponible")
            global_transaction_simplex_analyzer = None

        # PHASE 2C: Initialiser API SVG Animation
        if SVG_API_AVAILABLE:
            try:
                global_svg_api_server = register_svg_api_routes(app, web_manager)
                print("🎨 SVG Animation API initialisée avec WebNativeICGS")
                print("   Endpoints disponibles:")
                print("   - /api/svg/economy_animation")
                print("   - /api/svg/transaction/<tx_id>")
                print("   - /api/svg/simplex_steps")
                print("   - /api/svg/performance_dashboard")
                print("   - /api/svg/preview")
            except Exception as e:
                print(f"❌ Erreur initialisation SVG API: {e}")
                global_svg_api_server = None
        else:
            print("⚠️  SVG Animation API non disponible")
            global_svg_api_server = None

    return web_manager

@app.route('/')
def index():
    """Page d'accueil ICGS 3D - Application SPA avec visualisation massive 65 agents"""
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Servir les fichiers statiques CSS/JS pour application 3D"""
    from flask import send_from_directory
    import os

    # Créer le répertoire static s'il n'existe pas
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    os.makedirs(static_dir, exist_ok=True)

    return send_from_directory(static_dir, filename)

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

@app.route('/api/simulation/launch_advanced', methods=['POST'])
def api_launch_advanced_simulation():
    """API: Lancer simulation avancée avec sélection mode d'agents et scénario économique"""
    try:
        config = request.json or {}
        agents_mode = config.get('agents_mode', '15_agents')
        scenario_type = config.get('scenario', 'simple')
        flow_intensity = config.get('flow_intensity', 0.7)
        analysis_3d = config.get('analysis_3d', True)

        print(f"🚀 Lancement simulation avancée: mode={agents_mode}, scénario={scenario_type}")

        # CORRECTION: Utiliser EconomicSimulation avec le bon mode d'agents
        # au lieu du WebNativeICGS qui ne supporte pas les modes
        from icgs_simulation.api.icgs_bridge import EconomicSimulation

        # Mapper les modes de l'interface vers les modes supportés par le bridge
        bridge_mode = agents_mode
        if agents_mode == '15_agents':
            bridge_mode = '40_agents'  # Mode 40_agents a assez de capacité pour 15 agents
        elif agents_mode == 'demo':
            bridge_mode = '7_agents'   # Mode par défaut pour démo

        simulation = EconomicSimulation(f"advanced_{agents_mode}", agents_mode=bridge_mode)
        print(f"📊 EconomicSimulation créée avec mode: {bridge_mode}")

        # Conserver aussi le manager web pour compatibilité
        manager = init_web_manager()

        # Réinitialiser les métriques
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

        # Configuration des agents selon le mode sélectionné
        agents_config = {}

        if agents_mode == 'demo':
            agents_config = {
                'AGRICULTURE': [('ALICE_FARM', Decimal('1500'))],
                'INDUSTRY': [('BOB_INDUSTRY', Decimal('800'))],
                'SERVICES': [('CAROL_SERVICES', Decimal('600'))]
            }
        elif agents_mode == '15_agents':
            agents_config = {
                'AGRICULTURE': [('FARM_A1', Decimal('1200')), ('FARM_A2', Decimal('1300')), ('FARM_A3', Decimal('1100'))],
                'INDUSTRY': [('IND_I1', Decimal('900')), ('IND_I2', Decimal('850')), ('IND_I3', Decimal('950')), ('IND_I4', Decimal('800'))],
                'SERVICES': [('SERV_S1', Decimal('600')), ('SERV_S2', Decimal('650')), ('SERV_S3', Decimal('700'))],
                'FINANCE': [('FIN_F1', Decimal('2000')), ('FIN_F2', Decimal('1800'))],
                'ENERGY': [('ENG_E1', Decimal('1500')), ('ENG_E2', Decimal('1400')), ('ENG_E3', Decimal('1600'))]
            }
        elif agents_mode == '40_agents':
            agents_config = {
                'AGRICULTURE': [('AGR_{:02d}'.format(i), Decimal(str(1200 + i * 50))) for i in range(1, 9)],
                'INDUSTRY': [('IND_{:02d}'.format(i), Decimal(str(900 + i * 40))) for i in range(1, 11)],
                'SERVICES': [('SRV_{:02d}'.format(i), Decimal(str(600 + i * 30))) for i in range(1, 13)],
                'FINANCE': [('FIN_{:02d}'.format(i), Decimal(str(2000 + i * 100))) for i in range(1, 5)],
                'ENERGY': [('ENG_{:02d}'.format(i), Decimal(str(1500 + i * 80))) for i in range(1, 6)]
            }
        elif agents_mode == '65_agents':
            agents_config = {
                'AGRICULTURE': [('FARM_{:02d}'.format(i), Decimal(str(1250 + i * 50))) for i in range(1, 11)],
                'INDUSTRY': [('MFG_{:02d}'.format(i), Decimal(str(900 + i * 60))) for i in range(1, 16)],
                'SERVICES': [('RTL_{:02d}'.format(i), Decimal(str(600 + i * 40))) for i in range(1, 21)],
                'FINANCE': [('BANK_{:02d}'.format(i), Decimal(str(5000 + i * 200))) for i in range(1, 9)],
                'ENERGY': [('PWR_{:02d}'.format(i), Decimal(str(2500 + i * 100))) for i in range(1, 13)]
            }

        # Appliquer modifications selon le scénario économique
        if scenario_type == 'oil_shock':
            # Réduction -40% secteur ENERGY
            for sector, agents in agents_config.items():
                if sector == 'ENERGY':
                    agents_config[sector] = [(agent_id, balance * Decimal('0.6')) for agent_id, balance in agents]
                elif sector == 'INDUSTRY':
                    # Impact -25% sur INDUSTRY
                    agents_config[sector] = [(agent_id, balance * Decimal('0.75')) for agent_id, balance in agents]
                elif sector == 'SERVICES':
                    # Impact -15% sur SERVICES
                    agents_config[sector] = [(agent_id, balance * Decimal('0.85')) for agent_id, balance in agents]
                elif sector == 'FINANCE':
                    # Intervention +20% liquidités
                    agents_config[sector] = [(agent_id, balance * Decimal('1.20')) for agent_id, balance in agents]
            flow_intensity *= 0.6  # Réduction flux

        elif scenario_type == 'tech_innovation':
            # Boost +50% secteur INDUSTRY
            for sector, agents in agents_config.items():
                if sector == 'INDUSTRY':
                    agents_config[sector] = [(agent_id, balance * Decimal('1.50')) for agent_id, balance in agents]
                elif sector == 'SERVICES':
                    # Expansion +30% SERVICES
                    agents_config[sector] = [(agent_id, balance * Decimal('1.30')) for agent_id, balance in agents]
                elif sector == 'ENERGY':
                    # Demande accrue +25%
                    agents_config[sector] = [(agent_id, balance * Decimal('1.25')) for agent_id, balance in agents]
            flow_intensity *= 1.3  # Augmentation flux

        # Créer tous les agents
        created_agents = []
        agents_count = 0

        for sector, agents_list in agents_config.items():
            for agent_id, balance in agents_list:
                try:
                    if agent_id in manager.real_to_virtual:
                        # Agent existe déjà
                        agent_info = manager.agent_registry[agent_id]
                        created_agents.append({
                            'agent_id': agent_id,
                            'virtual_slot': agent_info.virtual_slot,
                            'sector': agent_info.sector,
                            'balance': float(balance),
                            'status': 'exists'
                        })
                    else:
                        # Créer nouvel agent via EconomicSimulation
                        simulation_agent = simulation.create_agent(agent_id, sector, balance)
                        agents_count += 1
                        created_agents.append({
                            'agent_id': agent_id,
                            'virtual_slot': agent_id,  # Pour compatibilité
                            'sector': sector,
                            'balance': float(balance),
                            'status': 'created'
                        })

                        # Aussi l'ajouter au manager web pour compatibilité interface
                        try:
                            manager.add_agent(agent_id, sector, balance)
                        except Exception as web_error:
                            print(f"⚠️ Erreur ajout web manager (non critique): {web_error}")
                    performance_metrics['sectors_used'].add(sector)
                except Exception as e:
                    print(f"⚠️ Erreur création agent {agent_id}: {e}")

        performance_metrics['agents_count'] = agents_count

        # Générer flux inter-sectoriels selon l'intensité
        if len(created_agents) >= 3:
            try:
                # Utiliser l'EconomicSimulation pour tous les modes
                print(f"🔄 Génération flux inter-sectoriels (intensité: {flow_intensity})")

                # Import nécessaire pour modes de simulation
                from icgs_simulation.api.icgs_bridge import SimulationMode

                # Générer transactions inter-sectorielles
                if hasattr(simulation, 'create_inter_sectoral_flows_batch'):
                    transaction_ids = simulation.create_inter_sectoral_flows_batch(flow_intensity)
                    print(f"✅ {len(transaction_ids)} transactions générées")
                else:
                    # Fallback : création manuelle de quelques transactions
                    transaction_ids = []
                    agent_list = list(simulation.agents.keys())
                    for i in range(min(8, len(agent_list)-1)):
                        try:
                            source = agent_list[i]
                            target = agent_list[i+1]
                            amount = Decimal('100') * flow_intensity
                            tx_id = simulation.create_transaction(source, target, amount)
                            transaction_ids.append(tx_id)
                        except Exception as tx_error:
                            print(f"⚠️ Erreur transaction {i}: {tx_error}")

                # Validation échantillon
                sample_size = min(15, len(transaction_ids))
                for tx_id in transaction_ids[:sample_size]:
                    try:
                        feas_result = simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
                        opt_result = simulation.validate_transaction(tx_id, SimulationMode.OPTIMIZATION)

                        performance_metrics['total_transactions'] += 1
                        if feas_result.success:
                            performance_metrics['successful_feasibility'] += 1
                            if opt_result.success:
                                performance_metrics['successful_optimization'] += 1

                    except Exception as e:
                        print(f"⚠️ Erreur validation {tx_id}: {e}")
                else:
                    # Créer transactions manuelles pour autres modes
                    sample_transactions = []
                    agents_by_sector = {}
                    for agent in created_agents:
                        sector = agent['sector']
                        if sector not in agents_by_sector:
                            agents_by_sector[sector] = []
                        agents_by_sector[sector].append(agent['agent_id'])

                    # Générer flux inter-sectoriels
                    sectors = list(agents_by_sector.keys())
                    for i, source_sector in enumerate(sectors):
                        for target_sector in sectors[i+1:]:
                            if agents_by_sector[source_sector] and agents_by_sector[target_sector]:
                                source_agent = agents_by_sector[source_sector][0]
                                target_agent = agents_by_sector[target_sector][0]
                                amount = Decimal(str(100 + len(sample_transactions) * 20)) * Decimal(str(flow_intensity))
                                sample_transactions.append((source_agent, target_agent, amount))

                    # Traiter transactions
                    for source, target, amount in sample_transactions[:int(10 * flow_intensity)]:
                        try:
                            result = manager.process_transaction(source, target, amount)
                            if result['success']:
                                tx_record = result['transaction_record']
                                performance_metrics['total_transactions'] += 1
                                if tx_record['feasibility']['success']:
                                    performance_metrics['successful_feasibility'] += 1
                                if tx_record['optimization']['success']:
                                    performance_metrics['successful_optimization'] += 1
                                simulation_history.append(tx_record)
                        except Exception as e:
                            print(f"⚠️ Erreur transaction {source}→{target}: {e}")

            except Exception as e:
                print(f"⚠️ Erreur génération flux: {e}")

        # Statistiques par secteur
        agents_distribution = {}
        for agent in created_agents:
            sector = agent['sector']
            if sector not in agents_distribution:
                agents_distribution[sector] = {'count': 0, 'total_balance': 0, 'agents': []}

            agents_distribution[sector]['count'] += 1
            agents_distribution[sector]['total_balance'] += agent['balance']
            agents_distribution[sector]['agents'].append({
                'id': agent['agent_id'],
                'balance': agent['balance']
            })

        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'simulation_config': {
                'agents_mode': agents_mode,
                'scenario_type': scenario_type,
                'flow_intensity': flow_intensity,
                'analysis_3d_enabled': analysis_3d
            },
            'agents_created': len(created_agents),
            'agents_distribution': agents_distribution,
            'transactions_generated': performance_metrics['total_transactions'],
            'performance_metrics': {
                'feasible_transactions': performance_metrics['successful_feasibility'],
                'optimal_transactions': performance_metrics['successful_optimization'],
                'sectors_involved': len(performance_metrics['sectors_used']),
                'feasibility_rate': (performance_metrics['successful_feasibility'] / max(performance_metrics['total_transactions'], 1)) * 100
            },
            'scenario_effects': {
                'oil_shock': {
                    'energy_impact': '-40%',
                    'industry_impact': '-25%',
                    'services_impact': '-15%',
                    'finance_boost': '+20%'
                } if scenario_type == 'oil_shock' else None,
                'tech_innovation': {
                    'industry_boost': '+50%',
                    'services_expansion': '+30%',
                    'energy_demand': '+25%'
                } if scenario_type == 'tech_innovation' else None
            }
        })

    except Exception as e:
        print(f"❌ Erreur simulation avancée: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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

        # Utiliser l'instance partagée web_manager.icgs_core au lieu de créer une nouvelle simulation
        manager = init_web_manager()
        if not manager or not manager.icgs_core:
            return jsonify({
                'success': False,
                'error': 'Instance ICGS non initialisée. Créer des agents d\'abord.'
            }), 400
        simulation = web_manager.icgs_core

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


# ==========================================
# SIMPLEX 3D ANIMATION API ENDPOINTS
# ==========================================

@app.route('/api/simplex_3d/transactions')
def api_list_simplex_transactions():
    """API: Liste des transactions disponibles pour animation Simplex"""
    try:
        manager = init_web_manager()
        global global_transaction_simplex_analyzer

        if not manager or not hasattr(manager, 'icgs_core'):
            return jsonify({
                'success': False,
                'error': 'Simulation non disponible'
            }), 400

        if not global_transaction_simplex_analyzer:
            return jsonify({
                'success': False,
                'error': 'Analyseur Simplex Transaction non initialisé'
            }), 400

        # Obtenir toutes transactions via analyseur
        simulation = web_manager.icgs_core
        transactions_list = []

        # Extraire transactions depuis DAG enhanced
        if hasattr(simulation, 'enhanced_dag') and simulation.enhanced_dag:
            for tx in simulation.enhanced_dag.transactions:
                # Analyser rapidement pour obtenir nombre d'étapes
                step_count = global_transaction_simplex_analyzer.get_transaction_step_count(tx.transaction_id)

                transactions_list.append({
                    'id': tx.transaction_id,
                    'source': tx.source_account,
                    'target': tx.target_account,
                    'amount': float(tx.amount),
                    'status': getattr(tx, 'status', 'unknown'),
                    'step_count': step_count,
                    'estimated_duration_ms': step_count * 200,  # 200ms par étape
                    'complexity': 'LOW' if step_count < 5 else 'MEDIUM' if step_count < 15 else 'HIGH'
                })

        return jsonify({
            'success': True,
            'transactions': transactions_list,
            'total_count': len(transactions_list),
            'timestamp': time.time()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/simplex_3d/transaction/<tx_id>')
def api_get_transaction_simplex_data(tx_id):
    """API: Données Simplex détaillées pour une transaction spécifique"""
    try:
        manager = init_web_manager()
        global global_transaction_simplex_analyzer

        if not manager or not global_transaction_simplex_analyzer:
            return jsonify({
                'success': False,
                'error': 'Services non disponibles'
            }), 400

        # Analyser transaction en détail
        transaction_data = global_transaction_simplex_analyzer.analyze_single_transaction(tx_id)

        # Convertir en format JSON serializable
        response_data = {
            'success': True,
            'transaction_id': transaction_data.transaction_id,
            'step_count': transaction_data.step_count,
            'estimated_duration_ms': transaction_data.estimated_duration_ms,
            'complexity_level': transaction_data.complexity.value,
            'simplex_steps': transaction_data.simplex_steps,
            'optimal_solution': transaction_data.optimal_solution,
            'convergence_info': transaction_data.convergence_info,
            'transaction_info': {
                'source_account': transaction_data.source_account,
                'target_account': transaction_data.target_account,
                'amount': float(transaction_data.amount),
                'feasible': transaction_data.feasible
            },
            'performance_metrics': {
                'actual_solving_time_ms': transaction_data.actual_solving_time_ms,
                'iterations_used': transaction_data.iterations_used,
                'pivot_count': transaction_data.pivot_count
            },
            'timestamp': time.time()
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'transaction_id': tx_id
        }), 500


@app.route('/api/simplex_3d/simulation/run', methods=['POST'])
def api_run_complete_simplex_simulation():
    """API: Lancement simulation complète avec animation enchaînée"""
    try:
        manager = init_web_manager()
        global global_transaction_simplex_analyzer

        if not manager or not global_transaction_simplex_analyzer:
            return jsonify({
                'success': False,
                'error': 'Services non disponibles'
            }), 400

        # Préparer séquence simulation complète
        sequence_data = global_transaction_simplex_analyzer.prepare_simulation_sequence()

        # Convertir en format JSON serializable
        response_data = {
            'success': True,
            'simulation_id': sequence_data.simulation_id,
            'total_transactions': sequence_data.total_transactions,
            'total_steps': sequence_data.total_steps,
            'estimated_duration_ms': sequence_data.estimated_duration_ms,
            'transactions': [
                {
                    'transaction_id': tx.transaction_id,
                    'step_count': tx.step_count,
                    'estimated_duration_ms': tx.estimated_duration_ms,
                    'complexity': tx.complexity.value,
                    'simplex_steps': tx.simplex_steps,
                    'source_account': tx.source_account,
                    'target_account': tx.target_account,
                    'amount': float(tx.amount),
                    'feasible': tx.feasible
                }
                for tx in sequence_data.transactions
            ],
            'transition_points': sequence_data.transition_points,
            'sequence_metadata': sequence_data.sequence_metadata,
            'timestamp': time.time()
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/simplex_3d/simulation/status')
def api_get_simulation_status():
    """API: Status simulation en cours (pour progression temps réel)"""
    try:
        manager = init_web_manager()
        global global_transaction_simplex_analyzer

        if not manager:
            return jsonify({
                'success': False,
                'error': 'Simulation non disponible'
            }), 400

        # Pour l'instant, retourner status basique
        # Peut être étendu pour tracking progression temps réel
        simulation = web_manager.icgs_core

        status_info = {
            'success': True,
            'simulation_running': True,
            'total_agents': len(getattr(simulation, 'enhanced_dag', {}).accounts or []),
            'total_transactions': len(getattr(simulation, 'enhanced_dag', {}).transactions or []),
            'analyzer_available': global_transaction_simplex_analyzer is not None,
            'cache_stats': global_transaction_simplex_analyzer._transaction_cache.keys() if global_transaction_simplex_analyzer else [],
            'timestamp': time.time()
        }

        return jsonify(status_info)

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
    <title>ICGS 3D - Visualisation Économie Massive</title>
    <link rel="stylesheet" href="/static/styles.css">

    <!-- Three.js CDN -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/dat-gui/0.7.9/dat.gui.min.js"></script>

    <!-- Orbit Controls pour Three.js -->
    <script>
        // OrbitControls inline pour éviter problème CDN
        !function(e,t){"object"==typeof exports&&"undefined"!=typeof module?t(exports,require("three")):"function"==typeof define&&define.amd?define(["exports","three"],t):t((e=e||self).THREE=e.THREE||{},e.THREE)}(this,function(e,t){"use strict";var n=function(e){function n(t,o){e.call(this),this.object=t,this.domElement=void 0!==o?o:document,this.enabled=!0,this.target=new t.Vector3,this.minDistance=0,this.maxDistance=1/0,this.minZoom=0,this.maxZoom=1/0,this.minPolarAngle=0,this.maxPolarAngle=Math.PI,this.minAzimuthAngle=-1/0,this.maxAzimuthAngle=1/0,this.enableDamping=!1,this.dampingFactor=.05,this.enableZoom=!0,this.zoomSpeed=1,this.enableRotate=!0,this.rotateSpeed=1,this.enablePan=!0,this.panSpeed=1,this.screenSpacePanning=!0,this.keyPanSpeed=7,this.autoRotate=!1,this.autoRotateSpeed=2,this.keys={LEFT:37,UP:38,RIGHT:39,BOTTOM:40},this.mouseButtons={LEFT:t.MOUSE.ROTATE,MIDDLE:t.MOUSE.DOLLY,RIGHT:t.MOUSE.PAN},this.touches={ONE:t.TOUCH.ROTATE,TWO:t.TOUCH.DOLLY_PAN},this.target0=this.target.clone(),this.position0=this.object.position.clone(),this.zoom0=this.object.zoom,this._domElementKeyEvents=null,this.getPolarAngle=function(){return l.phi},this.getAzimuthalAngle=function(){return l.theta},this.getDistance=function(){return this.object.position.distanceTo(this.target)},this.listenToKeyEvents=function(e){e.addEventListener("keydown",J),this._domElementKeyEvents=e},this.stopListenToKeyEvents=function(){this._domElementKeyEvents.removeEventListener("keydown",J),this._domElementKeyEvents=null},this.saveState=function(){i.target0.copy(i.target),i.position0.copy(i.object.position),i.zoom0=i.object.zoom},this.reset=function(){i.target.copy(i.target0),i.object.position.copy(i.position0),i.object.zoom=i.zoom0,i.object.updateProjectionMatrix(),i.dispatchEvent(r),i.update(),c=a.NONE},this.update=function(){var e=new t.Vector3,n=(new t.Quaternion).setFromUnitVectors(i.object.up,new t.Vector3(0,1,0)),o=n.clone().invert(),h=new t.Vector3,u=new t.Quaternion,f=2*Math.PI;return function(){var t=i.object.position;e.copy(t).sub(i.target),e.applyQuaternion(n),l.setFromVector3(e),i.autoRotate&&c===a.NONE&&D(2*Math.PI/60/60*i.autoRotateSpeed),i.enableDamping?(l.theta+=m.theta*i.dampingFactor,l.phi+=m.phi*i.dampingFactor):(l.theta+=m.theta,l.phi+=m.phi);var r=i.minAzimuthAngle,g=i.maxAzimuthAngle;isFinite(r)&&isFinite(g)&&(r<-Math.PI?r+=f:r>Math.PI&&(r-=f),g<-Math.PI?g+=f:g>Math.PI&&(g-=f),r<=g?l.theta=Math.max(r,Math.min(g,l.theta)):l.theta=l.theta>(r+g)/2?Math.max(r,l.theta):Math.min(g,l.theta)),l.phi=Math.max(i.minPolarAngle,Math.min(i.maxPolarAngle,l.phi)),l.makeSafe(),l.radius*=d,l.radius=Math.max(i.minDistance,Math.min(i.maxDistance,l.radius)),i.enableDamping===!0?i.target.addScaledVector(p,i.dampingFactor):i.target.add(p),e.setFromSpherical(l),e.applyQuaternion(o),t.copy(i.target).add(e),i.object.lookAt(i.target),i.enableDamping===!0?(m.theta*=1-i.dampingFactor,m.phi*=1-i.dampingFactor,p.multiplyScalar(1-i.dampingFactor)):(m.set(0,0,0),p.set(0,0,0)),d=1,!!(v||h.distanceToSquared(i.object.position)>s||8*(1-u.dot(i.object.quaternion))>s)&&(i.dispatchEvent(r),h.copy(i.object.position),u.copy(i.object.quaternion),v=!1,!0)}}(),this.dispose=function(){i.domElement.removeEventListener("contextmenu",K),i.domElement.removeEventListener("pointerdown",G),i.domElement.removeEventListener("pointercancel",k),i.domElement.removeEventListener("wheel",Y),i.domElement.removeEventListener("pointermove",q),i.domElement.removeEventListener("pointerup",k),null!==i._domElementKeyEvents&&(i._domElementKeyEvents.removeEventListener("keydown",J),i._domElementKeyEvents=null)};var i=this,r={type:"change"},s=1e-6,a={NONE:-1,ROTATE:0,DOLLY:1,PAN:2,TOUCH_ROTATE:3,TOUCH_PAN:4,TOUCH_DOLLY_PAN:5,TOUCH_DOLLY_ROTATE:6},c=a.NONE,l=new t.Spherical,m=new t.Spherical,d=1,p=new t.Vector3,v=!1,g=new t.Vector2,y=new t.Vector2,b=new t.Vector2,w=new t.Vector2,M=new t.Vector2,x=new t.Vector2,E=new t.Vector2,A=new t.Vector2,P=new t.Vector2,L=[],S={};function T(){return Math.pow(.95,i.zoomSpeed)}function R(e){m.theta-=e}function D(e){m.phi-=e}function C(e){i.object.isPerspectiveCamera?d/=e:i.object.isOrthographicCamera?(i.object.zoom=Math.max(i.minZoom,Math.min(i.maxZoom,i.object.zoom*e)),i.object.updateProjectionMatrix(),v=!0):(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - dolly/zoom disabled."),i.enableZoom=!1)}function I(e){i.object.isPerspectiveCamera?d*=e:i.object.isOrthographicCamera?(i.object.zoom=Math.max(i.minZoom,Math.min(i.maxZoom,i.object.zoom/e)),i.object.updateProjectionMatrix(),v=!0):(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - dolly/zoom disabled."),i.enableZoom=!1)}function U(e){g.set(e.clientX,e.clientY)}function z(e){E.set(e.clientX,e.clientY)}function F(e){w.set(e.clientX,e.clientY)}function O(e){y.set(e.clientX,e.clientY),b.subVectors(y,g).multiplyScalar(i.rotateSpeed);var t=i.domElement;R(2*Math.PI*b.x/t.clientHeight),D(2*Math.PI*b.y/t.clientHeight),g.copy(y),i.update()}function N(e){A.set(e.clientX,e.clientY),P.subVectors(A,E),P.y>0?C(T()):P.y<0&&I(T()),E.copy(A),i.update()}function V(e){M.set(e.clientX,e.clientY),x.subVectors(M,w).multiplyScalar(i.panSpeed),B(x.x,x.y),w.copy(M),i.update()}function B(e,t){i.object.isPerspectiveCamera?function(e,t){var n=i.object.position;p.copy(n).sub(i.target);var o=p.length();o*=Math.tan(i.object.fov/2*Math.PI/180),H(2*e*o/i.domElement.clientHeight,2*t*o/i.domElement.clientHeight)}(e,t):i.object.isOrthographicCamera?function(e,t){H(e*(i.object.right-i.object.left)/i.object.zoom/i.domElement.clientWidth,t*(i.object.top-i.object.bottom)/i.object.zoom/i.domElement.clientHeight)}(e,t):(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - pan disabled."),i.enablePan=!1)}function H(e,t){var n=i.object.matrix.elements;p.set(n[0],n[1],n[2]),p.multiplyScalar(-e);var o=i.object.matrix.elements;p.add((new t.Vector3).set(o[4],o[5],o[6]).multiplyScalar(t)),i.target.add(p)}function j(){return 2*Math.PI/60*(i.autoRotateSpeed*60)}function W(e){if(1==L.length)g.set(e.pageX,e.pageY);else{var t=Q(e),n=.5*(e.pageX+t.x),o=.5*(e.pageY+t.y);g.set(n,o)}}function X(e){if(1==L.length)w.set(e.pageX,e.pageY);else{var t=Q(e),n=.5*(e.pageX+t.x),o=.5*(e.pageY+t.y);w.set(n,o)}}function _(e){var t=Q(e),n=e.pageX-t.x,o=e.pageY-t.y,i=Math.sqrt(n*n+o*o);E.set(0,i)}function Q(e){for(var t=0;t<L.length;t++)if(L[t].pointerId!==e.pointerId)return L[t];return null}function G(e){var t;switch(L.push(e),L.length){case 1:switch(i.touches.ONE){case t.TOUCH.ROTATE:if(i.enableRotate===!1)return;W(e),c=a.TOUCH_ROTATE;break;case t.TOUCH.PAN:if(i.enablePan===!1)return;X(e),c=a.TOUCH_PAN;break;default:c=a.NONE}break;case 2:switch(i.touches.TWO){case t.TOUCH.DOLLY_PAN:if(i.enableZoom===!1&&i.enablePan===!1)return;!function(e){i.enableZoom&&_(e),i.enablePan&&X(e)}(e),c=a.TOUCH_DOLLY_PAN;break;case t.TOUCH.DOLLY_ROTATE:if(i.enableZoom===!1&&i.enableRotate===!1)return;!function(e){i.enableZoom&&_(e),i.enableRotate&&W(e)}(e),c=a.TOUCH_DOLLY_ROTATE;break;default:c=a.NONE}break;default:c=a.NONE}c!==a.NONE&&i.dispatchEvent(r)}function q(e){switch(e.pointerType){case"mouse":case"pen":!function(e){switch(e.button){case 0:switch(i.mouseButtons.LEFT){case t.MOUSE.ROTATE:if(e.ctrlKey||e.metaKey||e.shiftKey){if(i.enablePan===!1)return;F(e),c=a.PAN}else{if(i.enableRotate===!1)return;U(e),c=a.ROTATE}break;case t.MOUSE.PAN:if(e.ctrlKey||e.metaKey||e.shiftKey){if(i.enableRotate===!1)return;U(e),c=a.ROTATE}else{if(i.enablePan===!1)return;F(e),c=a.PAN}break;default:c=a.NONE}break;case 1:switch(i.mouseButtons.MIDDLE){case t.MOUSE.DOLLY:if(i.enableZoom===!1)return;z(e),c=a.DOLLY;break;default:c=a.NONE}break;case 2:switch(i.mouseButtons.RIGHT){case t.MOUSE.ROTATE:if(i.enableRotate===!1)return;U(e),c=a.ROTATE;break;case t.MOUSE.PAN:if(i.enablePan===!1)return;F(e),c=a.PAN;break;default:c=a.NONE}break;default:c=a.NONE}c!==a.NONE&&i.dispatchEvent(r)}(e);break;default:!function(e){var t,n,o;switch(L.length){case 1:switch(i.touches.ONE){case t.TOUCH.ROTATE:if(i.enableRotate===!1)return;O(e);break;case t.TOUCH.PAN:if(i.enablePan===!1)return;V(e);break;default:c=a.NONE}break;case 2:switch(i.touches.TWO){case t.TOUCH.DOLLY_PAN:if(i.enableZoom===!1&&i.enablePan===!1)return;t=e,n=Q(t),o=.5*(t.pageX+n.x),r=.5*(t.pageY+n.y),M.set(o,r),x.subVectors(M,w).multiplyScalar(i.panSpeed),B(x.x,x.y),w.copy(M),function(e){var t=Q(e),n=e.pageX-t.x,o=e.pageY-t.y,i=Math.sqrt(n*n+o*o);A.set(0,i),P.subVectors(A,E),P.y>0?C(T()):P.y<0&&I(T()),E.copy(A)}(t);break;case t.TOUCH.DOLLY_ROTATE:if(i.enableZoom===!1&&i.enableRotate===!1)return;!function(e){i.enableZoom&&function(e){var t=Q(e),n=e.pageX-t.x,o=e.pageY-t.y,i=Math.sqrt(n*n+o*o);A.set(0,i),P.subVectors(A,E),P.y>0?C(T()):P.y<0&&I(T()),E.copy(A)}(e),i.enableRotate&&O(e)}(e);break;default:c=a.NONE}break;default:c=a.NONE}var r}(e)}}function k(e){$(),L.length===0?i.domElement.releasePointerCapture(e.pointerId):L.length===1&&(c=a.NONE)}function $(e){delete S[e.pointerId];for(var t=0;t<L.length;t++)if(L[t].pointerId==e.pointerId)return void L.splice(t,1)}function J(e){var t=!1;switch(e.code){case i.keys.UP:B(0,i.keyPanSpeed),t=!0;break;case i.keys.BOTTOM:B(0,-i.keyPanSpeed),t=!0;break;case i.keys.LEFT:B(i.keyPanSpeed,0),t=!0;break;case i.keys.RIGHT:B(-i.keyPanSpeed,0),t=!0}t&&(e.preventDefault(),i.update())}function Y(e){if(i.enabled===!1||i.enableZoom===!1||c!==a.NONE&&c!==a.ROTATE)return;e.preventDefault(),i.dispatchEvent(r),function(e){e.deltaY<0?I(T()):e.deltaY>0&&C(T()),i.update()}(e),i.dispatchEvent(s)}function K(e){i.enabled===!1||e.preventDefault()}i.domElement.style.touchAction="none",i.domElement.addEventListener("contextmenu",K),i.domElement.addEventListener("pointerdown",G),i.domElement.addEventListener("pointercancel",k),i.domElement.addEventListener("wheel",Y),i.update()}return n.prototype=Object.assign(Object.create(e.prototype),{constructor:n,getPolarAngle:function(){return this.spherical.phi},getAzimuthalAngle:function(){return this.spherical.theta},getDistance:function(){return this.object.position.distanceTo(this.target)},listenToKeyEvents:function(e){e.addEventListener("keydown",this.onKeyDown),this._domElementKeyEvents=e},stopListenToKeyEvents:function(){this._domElementKeyEvents.removeEventListener("keydown",this.onKeyDown),this._domElementKeyEvents=null},saveState:function(){this.target0.copy(this.target),this.position0.copy(this.object.position),this.zoom0=this.object.zoom},reset:function(){this.target.copy(this.target0),this.object.position.copy(this.position0),this.object.zoom=this.zoom0,this.object.updateProjectionMatrix(),this.dispatchEvent({type:"change"}),this.update(),this.state=this.STATE.NONE},update:function(){return this.update}(),dispose:function(){this.domElement.removeEventListener("contextmenu",this.onContextMenu),this.domElement.removeEventListener("pointerdown",this.onPointerDown),this.domElement.removeEventListener("pointercancel",this.onPointerCancel),this.domElement.removeEventListener("wheel",this.onMouseWheel),this.domElement.removeEventListener("pointermove",this.onPointerMove),this.domElement.removeEventListener("pointerup",this.onPointerUp),null!==this._domElementKeyEvents&&(this._domElementKeyEvents.removeEventListener("keydown",this.onKeyDown),this._domElementKeyEvents=null)}}),n}(t.EventDispatcher);e.OrbitControls=n,Object.defineProperty(e,"__esModule",{value:!0})});
    </script>
</head>
<body>
    <div class="app-container">
        <!-- Sidebar Navigation -->
        <div class="sidebar">
            <div class="app-header">
                <div class="app-title">ICGS 3D</div>
                <div class="app-subtitle">Économie Massive 65 Agents</div>
            </div>

            <nav class="nav-menu">
                <button class="nav-button active" data-page="dashboard">
                    <span class="nav-icon">📊</span>
                    Dashboard 3D
                </button>
                <button class="nav-button" data-page="transactions">
                    <span class="nav-icon">💰</span>
                    Transaction Navigator
                </button>
                <button class="nav-button" data-page="sectors">
                    <span class="nav-icon">🏭</span>
                    Sector Analysis
                </button>
                <button class="nav-button" data-page="simplex">
                    <span class="nav-icon">📈</span>
                    Simplex Viewer
                </button>
                <button class="nav-button" data-page="export">
                    <span class="nav-icon">📁</span>
                    Data Export
                </button>
                <button class="nav-button" data-page="svg">
                    <span class="nav-icon">🎨</span>
                    SVG Animation
                </button>
            </nav>
        </div>

        <!-- Main Content Area -->
        <div class="main-content">
            <div class="content-area">
                <!-- Three.js Container -->
                <div id="three-container"></div>

                <!-- Dashboard Page -->
                <div id="dashboard-page" class="page-content">
                    <div class="page-header">
                        <h2 class="page-title">Dashboard 3D</h2>
                        <p class="page-subtitle">Vue d'ensemble économie massive</p>
                    </div>

                    <div id="dashboard-metrics">
                        <div class="loading">
                            <div class="spinner"></div>
                            <p>Chargement métriques...</p>
                        </div>
                    </div>

                    <div class="controls-section">
                        <h4 style="margin-bottom: 10px;">Contrôles Vue 3D</h4>
                        <p style="font-size: 0.8rem; opacity: 0.7; margin-bottom: 10px;">
                            • Clic gauche + glisser : Rotation<br>
                            • Molette : Zoom<br>
                            • Clic droit + glisser : Panoramique
                        </p>
                    </div>
                </div>

                <!-- SVG Animation Page -->
                <div id="svg-page" class="page-content" style="display: none;">
                    <div class="page-header">
                        <h2 class="page-title">SVG Animation</h2>
                        <p class="page-subtitle">Animations SVG basées sur les données ICGS</p>
                    </div>

                    <div class="svg-content">
                        <!-- Configuration Panel -->
                        <div class="svg-config-panel">
                            <h3>Configuration Animation</h3>

                            <div class="config-section">
                                <h4>Type d'Animation</h4>
                                <select id="animationType">
                                    <option value="economy">Économie Générale</option>
                                    <option value="transaction">Transaction Spécifique</option>
                                    <option value="simplex">Visualisation Simplex</option>
                                    <option value="dashboard">Dashboard Complet</option>
                                </select>
                            </div>

                            <div class="config-section">
                                <h4>Dimensions</h4>
                                <div class="config-row">
                                    <label>Largeur: <input type="number" id="svgWidth" value="800" min="400" max="1600"></label>
                                    <label>Hauteur: <input type="number" id="svgHeight" value="600" min="300" max="1200"></label>
                                </div>
                            </div>

                            <div class="config-section">
                                <h4>Animation</h4>
                                <div class="config-row">
                                    <label>Durée (s): <input type="number" id="animationDuration" value="2.0" min="0.5" max="10" step="0.1"></label>
                                    <label>Délai (s): <input type="number" id="animationDelay" value="0.1" min="0" max="2" step="0.1"></label>
                                </div>
                                <div class="config-row">
                                    <label>Transition:
                                        <select id="transitionType">
                                            <option value="ease-in-out">Ease In-Out</option>
                                            <option value="linear">Linéaire</option>
                                            <option value="ease-in">Ease In</option>
                                            <option value="ease-out">Ease Out</option>
                                        </select>
                                    </label>
                                </div>
                            </div>

                            <div class="config-section" id="transactionSection" style="display: none;">
                                <h4>Transaction Spécifique</h4>
                                <input type="text" id="transactionId" placeholder="ID de transaction (ex: TX_001)">
                            </div>

                            <div class="config-actions">
                                <button id="generateSvg" class="btn btn-primary">🎨 Générer SVG</button>
                                <button id="downloadSvg" class="btn btn-secondary" disabled>💾 Télécharger</button>
                                <button id="refreshData" class="btn btn-secondary">🔄 Actualiser Données</button>
                            </div>
                        </div>

                        <!-- Preview Panel -->
                        <div class="svg-preview-panel">
                            <h3>Prévisualisation</h3>
                            <div id="svgPreview" class="svg-preview-container">
                                <div class="placeholder">
                                    <p>🎨 Sélectionnez un type d'animation et cliquez sur "Générer SVG" pour voir la prévisualisation</p>
                                </div>
                            </div>

                            <div class="preview-info">
                                <div id="svgStats" class="stats-container">
                                    <div class="stat-item">
                                        <span class="stat-label">Taille:</span>
                                        <span id="svgSize">-</span>
                                    </div>
                                    <div class="stat-item">
                                        <span class="stat-label">Éléments:</span>
                                        <span id="svgElements">-</span>
                                    </div>
                                    <div class="stat-item">
                                        <span class="stat-label">Animation:</span>
                                        <span id="svgAnimated">-</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Data Status -->
                    <div class="data-status-section">
                        <h3>État des Données ICGS</h3>
                        <div id="dataStatus" class="data-status">
                            <div class="loading">Chargement du statut...</div>
                        </div>
                    </div>
                </div>

                <!-- Transactions Page -->
                <div id="transactions-page" class="page-content" style="display: none;">
                    <div class="page-header">
                        <h2 class="page-title">Transaction Navigator</h2>
                        <p class="page-subtitle">Navigation dans les transactions ICGS</p>
                    </div>
                    <div class="placeholder">
                        <p>🔄 Page Transaction Navigator en développement</p>
                    </div>
                </div>

                <!-- Sectors Page -->
                <div id="sectors-page" class="page-content" style="display: none;">
                    <div class="page-header">
                        <h2 class="page-title">Sector Analysis</h2>
                        <p class="page-subtitle">Analyse des secteurs économiques</p>
                    </div>
                    <div class="placeholder">
                        <p>🏭 Page Sector Analysis en développement</p>
                    </div>
                </div>

                <!-- Simplex Page -->
                <div id="simplex-page" class="page-content" style="display: none;">
                    <div class="page-header">
                        <h2 class="page-title">Simplex Viewer</h2>
                        <p class="page-subtitle">Visualisation des calculs Simplex</p>
                    </div>
                    <div class="placeholder">
                        <p>📈 Page Simplex Viewer en développement</p>
                    </div>
                </div>

                <!-- Export Page -->
                <div id="export-page" class="page-content" style="display: none;">
                    <div class="page-header">
                        <h2 class="page-title">Data Export</h2>
                        <p class="page-subtitle">Export des données ICGS</p>
                    </div>
                    <div class="placeholder">
                        <p>📁 Page Data Export en développement</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Additional CSS for SVG Animation -->
    <style>
        .page-content {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            margin: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }

        .page-header {
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 15px;
            margin-bottom: 25px;
        }

        .page-title {
            color: #2d3748;
            font-size: 1.8em;
            margin-bottom: 5px;
        }

        .page-subtitle {
            color: #718096;
            font-size: 1em;
        }

        .svg-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
            margin-bottom: 25px;
        }

        .svg-config-panel, .svg-preview-panel {
            background: #f7fafc;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #e2e8f0;
        }

        .svg-config-panel h3, .svg-preview-panel h3 {
            color: #2d3748;
            margin-bottom: 20px;
            font-size: 1.2em;
        }

        .config-section {
            margin-bottom: 20px;
        }

        .config-section h4 {
            color: #4a5568;
            margin-bottom: 10px;
            font-size: 1em;
        }

        .config-row {
            display: flex;
            gap: 15px;
            margin-bottom: 10px;
        }

        .config-row label {
            flex: 1;
            font-size: 0.9em;
            color: #4a5568;
        }

        .config-row input, .config-row select, .config-section input, .config-section select {
            width: 100%;
            padding: 8px;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            font-size: 0.9em;
            margin-top: 5px;
        }

        .config-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .btn-primary {
            background: #4299e1;
            color: white;
        }

        .btn-primary:hover {
            background: #3182ce;
        }

        .btn-secondary {
            background: #a0aec0;
            color: white;
        }

        .btn-secondary:hover {
            background: #718096;
        }

        .btn:disabled {
            background: #e2e8f0;
            color: #a0aec0;
            cursor: not-allowed;
        }

        .svg-preview-container {
            min-height: 400px;
            border: 2px dashed #e2e8f0;
            border-radius: 8px;
            padding: 20px;
            background: white;
            overflow: auto;
            margin-bottom: 15px;
        }

        .placeholder {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            text-align: center;
            color: #718096;
            font-style: italic;
        }

        .preview-info {
            background: white;
            border-radius: 6px;
            padding: 15px;
        }

        .stats-container {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }

        .stat-item {
            display: flex;
            flex-direction: column;
            text-align: center;
        }

        .stat-label {
            font-size: 0.8em;
            color: #718096;
            margin-bottom: 5px;
        }

        .data-status-section {
            background: #f7fafc;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #e2e8f0;
        }

        .data-status-section h3 {
            color: #2d3748;
            margin-bottom: 15px;
        }

        .data-status {
            background: white;
            border-radius: 6px;
            padding: 15px;
            border: 1px solid #e2e8f0;
        }

        /* Navigation styles */
        .nav-button.active {
            background: #4299e1;
            color: white;
        }

        .nav-button:hover {
            background: #e2e8f0;
        }

        .nav-button.active:hover {
            background: #3182ce;
        }
    </style>

    <script>
        // Navigation Management
        document.addEventListener('DOMContentLoaded', function() {
            // Initialize navigation
            initializeNavigation();

            // Initialize SVG animation functionality
            initializeSvgAnimation();

            // Load initial data
            updateDataStatus();
        });

        function initializeNavigation() {
            const navButtons = document.querySelectorAll('.nav-button');
            const pages = document.querySelectorAll('.page-content');

            navButtons.forEach(button => {
                button.addEventListener('click', function() {
                    const targetPage = this.getAttribute('data-page');

                    // Update active nav button
                    navButtons.forEach(btn => btn.classList.remove('active'));
                    this.classList.add('active');

                    // Show target page, hide others
                    pages.forEach(page => {
                        if (page.id === targetPage + '-page') {
                            page.style.display = 'block';
                        } else {
                            page.style.display = 'none';
                        }
                    });

                    // Special handling for SVG page
                    if (targetPage === 'svg') {
                        updateDataStatus();
                    }
                });
            });
        }

        function initializeSvgAnimation() {
            const animationType = document.getElementById('animationType');
            const transactionSection = document.getElementById('transactionSection');
            const generateBtn = document.getElementById('generateSvg');
            const downloadBtn = document.getElementById('downloadSvg');
            const refreshBtn = document.getElementById('refreshData');

            // Show/hide transaction section based on type
            animationType.addEventListener('change', function() {
                if (this.value === 'transaction') {
                    transactionSection.style.display = 'block';
                } else {
                    transactionSection.style.display = 'none';
                }
            });

            // Generate SVG
            generateBtn.addEventListener('click', function() {
                generateSvgAnimation();
            });

            // Download SVG
            downloadBtn.addEventListener('click', function() {
                downloadGeneratedSvg();
            });

            // Refresh data
            refreshBtn.addEventListener('click', function() {
                updateDataStatus();
            });
        }

        async function generateSvgAnimation() {
            const generateBtn = document.getElementById('generateSvg');
            const preview = document.getElementById('svgPreview');

            generateBtn.disabled = true;
            generateBtn.textContent = '🔄 Génération...';

            try {
                const config = {
                    type: document.getElementById('animationType').value,
                    width: parseInt(document.getElementById('svgWidth').value),
                    height: parseInt(document.getElementById('svgHeight').value),
                    duration: parseFloat(document.getElementById('animationDuration').value),
                    delay: parseFloat(document.getElementById('animationDelay').value),
                    transition: document.getElementById('transitionType').value
                };

                let endpoint = '/api/svg/economy_animation';

                // Build query parameters
                const params = new URLSearchParams({
                    width: config.width,
                    height: config.height,
                    duration: config.duration,
                    delay: config.delay,
                    transition: config.transition
                });

                // Determine endpoint based on type
                switch (config.type) {
                    case 'transaction':
                        const txId = document.getElementById('transactionId').value;
                        if (!txId) {
                            alert('Veuillez saisir un ID de transaction');
                            return;
                        }
                        endpoint = `/api/svg/transaction/${txId}`;
                        break;
                    case 'simplex':
                        endpoint = '/api/svg/simplex_steps';
                        break;
                    case 'dashboard':
                        endpoint = '/api/svg/performance_dashboard';
                        break;
                }

                // Add parameters to endpoint
                const finalEndpoint = `${endpoint}?${params.toString()}`;

                const response = await fetch(finalEndpoint, {
                    method: 'GET'
                });

                if (!response.ok) {
                    throw new Error(`Erreur HTTP: ${response.status}`);
                }

                const result = await response.text();

                // Display SVG
                preview.innerHTML = result;

                // Update stats
                updateSvgStats(result);

                // Enable download
                document.getElementById('downloadSvg').disabled = false;
                window.currentSvg = result;

            } catch (error) {
                console.error('Erreur génération SVG:', error);
                preview.innerHTML = `<div class="placeholder"><p>❌ Erreur: ${error.message}</p></div>`;
            } finally {
                generateBtn.disabled = false;
                generateBtn.textContent = '🎨 Générer SVG';
            }
        }

        function updateSvgStats(svgContent) {
            const sizeKb = (new Blob([svgContent]).size / 1024).toFixed(1);
            const elementCount = (svgContent.match(/<[^\/][^>]*>/g) || []).length;
            const hasAnimation = svgContent.includes('animate') || svgContent.includes('animateTransform');

            document.getElementById('svgSize').textContent = `${sizeKb} KB`;
            document.getElementById('svgElements').textContent = elementCount;
            document.getElementById('svgAnimated').textContent = hasAnimation ? 'Oui' : 'Non';
        }

        function downloadGeneratedSvg() {
            if (!window.currentSvg) return;

            const blob = new Blob([window.currentSvg], { type: 'image/svg+xml' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');

            const type = document.getElementById('animationType').value;
            const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');

            a.href = url;
            a.download = `icgs_${type}_animation_${timestamp}.svg`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }

        async function updateDataStatus() {
            const statusDiv = document.getElementById('dataStatus');

            try {
                const response = await fetch('/api/metrics');
                const data = await response.json();

                const perf = data.performance;

                statusDiv.innerHTML = `
                    <div class="data-status-grid">
                        <div class="status-item">
                            <strong>Agents:</strong> ${perf.agents_count}
                        </div>
                        <div class="status-item">
                            <strong>Transactions:</strong> ${perf.total_transactions}
                        </div>
                        <div class="status-item">
                            <strong>Secteurs:</strong> ${perf.sectors_used.length}
                        </div>
                        <div class="status-item">
                            <strong>Performance:</strong> ${perf.avg_validation_time_ms.toFixed(1)}ms
                        </div>
                    </div>
                `;

            } catch (error) {
                statusDiv.innerHTML = `<div class="error">❌ Erreur chargement données: ${error.message}</div>`;
            }
        }
    </script>

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

            <!-- Sélecteur de Simulation -->
            <div class="card full-width">
                <h3>🎯 Lancement de Simulation</h3>

                <div class="simulation-selector" style="margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                    <div class="config-section" style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; font-weight: 600;">Mode d'Agents :</label>
                        <select id="agentsMode" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                            <option value="demo">🔹 Démo (5 agents de test)</option>
                            <option value="15_agents">🔸 Petite échelle (15 agents)</option>
                            <option value="40_agents">🔶 Moyenne échelle (40 agents)</option>
                            <option value="65_agents">🔺 Massive (65 agents)</option>
                        </select>
                    </div>

                    <div class="config-section" style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; font-weight: 600;">Scénario Économique :</label>
                        <select id="scenarioType" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                            <option value="simple">🔷 Simple (création + flux basiques)</option>
                            <option value="stable_economy">🏦 Économie Stable (équilibre 7 jours)</option>
                            <option value="oil_shock">⚡ Choc Pétrolier (-40% ENERGY)</option>
                            <option value="tech_innovation">🚀 Innovation Tech (+50% INDUSTRY)</option>
                        </select>
                    </div>

                    <div class="config-section" style="margin-bottom: 15px;">
                        <label style="display: block; margin-bottom: 5px; font-weight: 600;">Intensité des Flux :</label>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <input type="range" id="flowIntensity" min="0.1" max="1.0" step="0.1" value="0.7"
                                   style="flex: 1;" oninput="document.getElementById('flowValue').textContent = this.value">
                            <span id="flowValue" style="min-width: 30px; font-weight: 600; color: #007bff;">0.7</span>
                        </div>
                        <div style="font-size: 0.8em; color: #6c757d; margin-top: 2px;">
                            0.1 = Flux légers | 0.7 = Équilibré | 1.0 = Flux intenses
                        </div>
                    </div>

                    <div class="config-description" id="simulationDescription"
                         style="margin-bottom: 15px; padding: 10px; background: #e7f3ff; border-radius: 4px; font-size: 0.9em; color: #0066cc;">
                        🔹 Mode Démo : Simulation rapide avec 3 agents de test pour découvrir le système.
                    </div>

                    <button id="launchSimulation" class="btn btn-primary" style="width: 100%; padding: 12px; font-size: 1.1em; font-weight: 600;">
                        🚀 Lancer Simulation
                    </button>
                </div>
            </div>

            <!-- Historique -->
            <div class="card full-width">
                <h3>📋 Historique des Transactions</h3>
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

        // Gestion des descriptions dynamiques pour les simulations
        function updateSimulationDescription() {
            const agentsMode = document.getElementById('agentsMode').value;
            const scenarioType = document.getElementById('scenarioType').value;
            const descriptionEl = document.getElementById('simulationDescription');

            let description = '';
            let bgColor = '#e7f3ff';
            let textColor = '#0066cc';

            // Description selon le mode d'agents
            const agentsDescriptions = {
                'demo': '🔹 Mode Démo : Simulation rapide avec 3 agents de test pour découvrir le système.',
                '15_agents': '🔸 Petite échelle : 15 agents répartis sur 5 secteurs économiques. Idéal pour les tests.',
                '40_agents': '🔶 Moyenne échelle : 40 agents pour une simulation économique réaliste avec flux inter-sectoriels.',
                '65_agents': '🔺 Massive : 65 agents avec analyse 3D complète. Simulation industrielle complète.'
            };

            // Description selon le scénario
            const scenarioDescriptions = {
                'simple': 'Création d\'agents et génération de flux économiques basiques.',
                'stable_economy': '📊 Simulation 7 jours d\'équilibre économique avec flux constants entre secteurs.',
                'oil_shock': '⚡ Test de résilience : Choc énergétique avec réduction -40% du secteur ENERGY.',
                'tech_innovation': '🚀 Révolution technologique : Croissance +50% du secteur INDUSTRY.'
            };

            // Couleurs selon le scénario
            const scenarioColors = {
                'simple': { bg: '#e7f3ff', text: '#0066cc' },
                'stable_economy': { bg: '#e8f5e8', text: '#0f5132' },
                'oil_shock': { bg: '#fff3cd', text: '#856404' },
                'tech_innovation': { bg: '#f0e6ff', text: '#6f42c1' }
            };

            description = agentsDescriptions[agentsMode] + ' ' + scenarioDescriptions[scenarioType];
            const colors = scenarioColors[scenarioType];
            bgColor = colors.bg;
            textColor = colors.text;

            descriptionEl.innerHTML = description;
            descriptionEl.style.backgroundColor = bgColor;
            descriptionEl.style.color = textColor;
        }

        // Écouteurs pour les changements de sélection
        document.getElementById('agentsMode').addEventListener('change', updateSimulationDescription);
        document.getElementById('scenarioType').addEventListener('change', updateSimulationDescription);

        // Gestion du lancement de simulation avancée
        document.getElementById('launchSimulation').addEventListener('click', async function() {
            this.disabled = true;
            this.textContent = '⏳ Lancement en cours...';

            try {
                const agentsMode = document.getElementById('agentsMode').value;
                const scenarioType = document.getElementById('scenarioType').value;
                const flowIntensity = parseFloat(document.getElementById('flowIntensity').value);

                let endpoint;
                let config = {
                    flow_intensity: flowIntensity
                };

                // Choisir l'API selon la configuration
                if (agentsMode === 'demo' && scenarioType === 'simple') {
                    // Utiliser l'ancienne API pour le mode démo simple
                    endpoint = '/api/simulation/run_demo';
                } else {
                    // Utiliser la nouvelle API avancée
                    endpoint = '/api/simulation/launch_advanced';
                    config = {
                        agents_mode: agentsMode,
                        scenario: scenarioType,
                        flow_intensity: flowIntensity,
                        analysis_3d: agentsMode === '65_agents'
                    };
                }

                console.log(`🚀 Lancement simulation: ${endpoint}`, config);

                const response = await fetch(endpoint, {
                    method: endpoint.includes('run_demo') ? 'GET' : 'POST',
                    headers: endpoint.includes('run_demo') ? {} : {'Content-Type': 'application/json'},
                    body: endpoint.includes('run_demo') ? undefined : JSON.stringify(config)
                });

                const result = await response.json();

                if (result.success) {
                    // Message de succès détaillé
                    let successMessage = `✅ Simulation ${agentsMode} terminée!\n`;
                    successMessage += `📊 ${result.agents_created} agents créés\n`;

                    if (result.transactions_generated) {
                        successMessage += `🔄 ${result.transactions_generated} transactions générées\n`;
                    } else if (result.transactions_processed) {
                        successMessage += `🔄 ${result.transactions_processed} transactions traitées\n`;
                    }

                    if (result.performance_metrics) {
                        const perf = result.performance_metrics;
                        successMessage += `📈 Taux de faisabilité: ${perf.feasibility_rate?.toFixed(1) || 0}%\n`;
                        successMessage += `🏭 Secteurs impliqués: ${perf.sectors_involved || 0}`;
                    }

                    // Ajouter effets de scénario s'il y en a
                    if (result.scenario_effects) {
                        if (result.scenario_effects.oil_shock) {
                            successMessage += `\n⚡ Effets Choc Pétrolier appliqués`;
                        }
                        if (result.scenario_effects.tech_innovation) {
                            successMessage += `\n🚀 Effets Innovation Tech appliqués`;
                        }
                    }

                    alert(successMessage);

                    // Rafraîchir automatiquement l'historique et métriques
                    if (typeof refreshHistory === 'function') refreshHistory();
                    if (typeof refreshMetrics === 'function') refreshMetrics();
                } else {
                    alert(`❌ Erreur simulation: ${result.error}`);
                }
            } catch (error) {
                console.error('Erreur lancement simulation:', error);
                alert(`❌ Erreur: ${error.message}`);
            } finally {
                this.disabled = false;
                this.textContent = '🚀 Lancer Simulation';
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

    # Initialiser WebNative ICGS Manager et APIs
    init_web_manager()

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