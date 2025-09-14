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

# Import 3D analyzer
try:
    from icgs_3d_space_analyzer import ICGS3DSpaceAnalyzer
    ANALYZER_3D_AVAILABLE = True
except ImportError:
    ANALYZER_3D_AVAILABLE = False
    print("⚠️  3D Analyzer not available")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'icgs_demo_2024'

# Global simulation instance
global_simulation = None
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

def init_simulation():
    """Initialize global ICGS simulation"""
    global global_simulation, global_3d_analyzer
    if global_simulation is None:
        global_simulation = EconomicSimulation("web_demo")
        print("🚀 ICGS Web Simulation initialized")

        # PHASE 2A: Initialiser analyseur 3D avec mode authentique
        if ANALYZER_3D_AVAILABLE:
            global_3d_analyzer = ICGS3DSpaceAnalyzer(global_simulation)
            success = global_3d_analyzer.enable_authentic_simplex_data(global_simulation)
            if success:
                print("🌌 Analyseur 3D Mode Authentique activé")
            else:
                print("⚠️  Analyseur 3D Mode Authentique échoué")
    return global_simulation

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
    """API: Gestion des agents économiques"""
    sim = init_simulation()

    if request.method == 'GET':
        # Retourner liste des agents actuels
        agents_data = []
        if hasattr(sim, 'agents'):
            for agent_id, agent in sim.agents.items():
                agents_data.append({
                    'agent_id': agent_id,
                    'sector': agent.sector,
                    'balance': float(agent.balance),
                    'metadata': agent.metadata
                })
        return jsonify(agents_data)

    elif request.method == 'POST':
        # Créer nouvel agent
        data = request.json
        try:
            agent_id = data['agent_id']
            sector = data['sector']
            balance = Decimal(str(data['balance']))
            metadata = data.get('metadata', {})

            agent = sim.create_agent(agent_id, sector, balance, metadata)

            # Mise à jour métriques
            performance_metrics['agents_count'] += 1
            performance_metrics['sectors_used'].add(sector)

            return jsonify({
                'success': True,
                'message': f'Agent {agent_id} créé avec succès',
                'agent': {
                    'agent_id': agent_id,
                    'sector': sector,
                    'balance': float(balance),
                    'metadata': metadata
                }
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400

@app.route('/api/transaction', methods=['POST'])
def api_transaction():
    """API: Créer et valider une transaction"""
    sim = init_simulation()

    try:
        data = request.json
        source_id = data['source_id']
        target_id = data['target_id']
        amount = Decimal(str(data['amount']))

        # Créer transaction
        tx_id = sim.create_transaction(source_id, target_id, amount)

        # Valider en mode FEASIBILITY
        start_time = time.time()
        result_feas = sim.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
        feas_time = (time.time() - start_time) * 1000

        # Valider en mode OPTIMIZATION
        start_time = time.time()
        result_opt = sim.validate_transaction(tx_id, SimulationMode.OPTIMIZATION)
        opt_time = (time.time() - start_time) * 1000

        # Mise à jour métriques
        performance_metrics['total_transactions'] += 1
        if result_feas.success:
            performance_metrics['successful_feasibility'] += 1
        if result_opt.success:
            performance_metrics['successful_optimization'] += 1

        avg_time = (feas_time + opt_time) / 2
        current_avg = performance_metrics['avg_validation_time_ms']
        total_tx = performance_metrics['total_transactions']
        performance_metrics['avg_validation_time_ms'] = (current_avg * (total_tx - 1) + avg_time) / total_tx

        # PHASE 2A: Collecter données animation 3D pour cette transaction
        animation_data = None
        if global_simulation and hasattr(global_simulation, 'get_3d_collector'):
            collector = global_simulation.get_3d_collector()
            if collector and len(collector.states_history) > 0:
                animation_data = collector.export_animation_data()

        # Enregistrer dans l'historique avec données 3D intégrées
        transaction_record = {
            'timestamp': datetime.now().isoformat(),
            'tx_id': tx_id,
            'source_id': source_id,
            'target_id': target_id,
            'amount': float(amount),
            'feasibility': {
                'success': result_feas.success,
                'time_ms': round(feas_time, 2)
            },
            'optimization': {
                'success': result_opt.success,
                'time_ms': round(opt_time, 2),
                'optimal_price': float(getattr(result_opt, 'optimal_price', 0))
            },
            'animation': animation_data  # NOUVEAU: Données animation 3D intégrées
        }
        simulation_history.append(transaction_record)

        return jsonify({
            'success': True,
            'transaction': transaction_record
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/metrics')
def api_metrics():
    """API: Métriques de performance actuelles + données 3D intégrées"""
    # Obtenir stats DAG si disponibles
    dag_stats = {}
    if global_simulation and hasattr(global_simulation, 'dag'):
        dag_stats = getattr(global_simulation.dag, 'stats', {})

    # PHASE 2A: Intégrer données 3D dans métriques existantes
    simplex_3d_data = {}
    if global_simulation and hasattr(global_simulation, 'get_3d_collector'):
        collector = global_simulation.get_3d_collector()
        if collector:
            simplex_3d_data = {
                'states_captured': len(collector.states_history),
                'transitions_captured': len(collector.transitions_history),
                'last_animation_ready': len(collector.states_history) > 0,
                'last_animation_data': collector.export_animation_data() if len(collector.states_history) > 0 else None
            }

    return jsonify({
        'performance': {
            **performance_metrics,
            'sectors_used': list(performance_metrics['sectors_used'])
        },
        'dag_stats': dag_stats,
        'history_count': len(simulation_history),
        'simplex_3d': simplex_3d_data  # NOUVEAU: Données 3D intégrées
    })

@app.route('/api/history')
def api_history():
    """API: Historique des transactions"""
    limit = request.args.get('limit', 20, type=int)
    return jsonify(simulation_history[-limit:])

@app.route('/api/simulation/run_demo')
def api_run_demo():
    """API: Lancer simulation de démonstration"""
    sim = init_simulation()

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

        # Créer agents de démonstration
        demo_agents = [
            ('ALICE_FARM', 'AGRICULTURE', Decimal('1500'), {'name': 'Alice Farm', 'region': 'Nord'}),
            ('BOB_INDUSTRY', 'INDUSTRY', Decimal('800'), {'name': 'Bob Manufacturing', 'type': 'primary'}),
            ('CAROL_SERVICES', 'SERVICES', Decimal('600'), {'name': 'Carol Logistics', 'type': 'transport'})
        ]

        for agent_id, sector, balance, metadata in demo_agents:
            sim.create_agent(agent_id, sector, balance, metadata)
            performance_metrics['agents_count'] += 1
            performance_metrics['sectors_used'].add(sector)

        # Créer transactions de démonstration
        demo_transactions = [
            ('ALICE_FARM', 'BOB_INDUSTRY', Decimal('120')),
            ('BOB_INDUSTRY', 'CAROL_SERVICES', Decimal('85'))
        ]

        results = []
        for source, target, amount in demo_transactions:
            tx_id = sim.create_transaction(source, target, amount)

            # Validation
            result_feas = sim.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
            result_opt = sim.validate_transaction(tx_id, SimulationMode.OPTIMIZATION)

            performance_metrics['total_transactions'] += 1
            if result_feas.success:
                performance_metrics['successful_feasibility'] += 1
            if result_opt.success:
                performance_metrics['successful_optimization'] += 1

            results.append({
                'tx_id': tx_id,
                'source': source,
                'target': target,
                'amount': float(amount),
                'feasibility_success': result_feas.success,
                'optimization_success': result_opt.success
            })

        return jsonify({
            'success': True,
            'message': 'Simulation de démonstration terminée',
            'results': results,
            'agents_created': len(demo_agents),
            'transactions_processed': len(demo_transactions)
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

# Template HTML intégré
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
    print("📊 Interface disponible sur: http://localhost:5000")
    print("✨ Fonctionnalités:")
    print("   - Création d'agents économiques")
    print("   - Validation de transactions (FEASIBILITY + OPTIMIZATION)")
    print("   - Métriques temps réel")
    print("   - Simulation de démonstration")
    print("   - Historique des transactions")
    print()

    app.run(debug=True, host='0.0.0.0', port=5000)