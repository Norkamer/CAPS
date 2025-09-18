"""
Test Production Datasets - Phase 3 Refactoring

Ce module teste la robustesse d'EnhancedDAG avec des datasets de production
réalistes pour valider le comportement sur des données complexes représentatives.

OBJECTIFS PRODUCTION TESTING:
1. DATASETS RÉALISTES : Validation comportement sur données production
2. SCÉNARIOS COMPLEXES : Tests workflows multi-étapes réels
3. DONNÉES VOLUMINEUSES : Validation scalabilité sur grands datasets
4. ROBUSTESSE PRODUCTION : Tests conditions réelles d'utilisation
5. BENCHMARKS RÉFÉRENCE : Établir métriques performance production

Niveau : Tests validation production et benchmarks référence
"""

import pytest
import time
import json
import tempfile
import os
import statistics
from typing import Dict, List, Tuple, Any, Optional
from decimal import Decimal

# Import du système à tester
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_core.enhanced_dag import EnhancedDAG
from icgs_core.dag import DAG, DAGConfiguration, Transaction, TransactionMeasure
from icgs_core.dag_structures import Node
from icgs_core.transaction_manager import TransactionManager


class TestProductionScenarios:
    """Tests scénarios production réalistes"""

    def test_financial_transaction_scenario(self):
        """Test scénario transactions financières réalistes"""

        # ===================================================
        # SCÉNARIO 1: Système financier multi-entités
        # ===================================================

        # Configuration système financier réaliste
        config = DAGConfiguration(
            max_path_enumeration=5000,
            simplex_max_iterations=3000
        )

        enhanced_dag = EnhancedDAG(config)

        # Entités financières typiques
        financial_accounts = {
            # Banques
            "central_bank_source": "C", "central_bank_sink": "D",
            "commercial_bank_a_source": "E", "commercial_bank_a_sink": "F",
            "commercial_bank_b_source": "G", "commercial_bank_b_sink": "H",

            # Entreprises
            "corp_alpha_source": "I", "corp_alpha_sink": "J",
            "corp_beta_source": "K", "corp_beta_sink": "L",

            # Particuliers
            "customer_alice_source": "M", "customer_alice_sink": "N",
            "customer_bob_source": "O", "customer_bob_sink": "P",

            # Services
            "payment_processor_source": "Q", "payment_processor_sink": "R",
            "clearing_house_source": "S", "clearing_house_sink": "T"
        }

        # Configuration système en une opération (API simplifiée)
        start_time = time.perf_counter()
        result = enhanced_dag.configure_accounts_simple(financial_accounts)
        config_time = time.perf_counter() - start_time

        # VALIDATION CONFIGURATION
        assert len(result) == len(financial_accounts), f"Toutes entités configurées: {len(result)}"
        assert config_time < 0.1, f"Configuration rapide: {config_time:.4f}s"

        # Simulation accès production typiques
        start_time = time.perf_counter()

        # Test accès mappings entités critiques
        critical_entities = [
            "central_bank_source", "payment_processor_source",
            "clearing_house_source", "commercial_bank_a_source"
        ]

        for _ in range(100):  # Simulation 100 requêtes
            for entity in critical_entities:
                mapping = enhanced_dag.get_current_account_mapping(entity)
                assert mapping is not None, f"Mapping disponible pour {entity}"

        access_time = time.perf_counter() - start_time

        # Test conversions paths financiers complexes
        financial_paths = [
            # Virement classique: Client → Banque → Clearing → Banque → Client
            [
                Node("customer_alice_source"), Node("commercial_bank_a_sink"),
                Node("commercial_bank_a_source"), Node("clearing_house_sink"),
                Node("clearing_house_source"), Node("commercial_bank_b_sink"),
                Node("commercial_bank_b_source"), Node("customer_bob_sink")
            ],
            # Paiement entreprise: Corp → Processeur → Client
            [
                Node("corp_alpha_source"), Node("payment_processor_sink"),
                Node("payment_processor_source"), Node("customer_alice_sink")
            ]
        ]

        start_time = time.perf_counter()
        conversion_results = []

        for path in financial_paths:
            word = enhanced_dag.convert_path_simple(path)
            conversion_results.append(word)

        conversion_time = time.perf_counter() - start_time

        # VALIDATIONS PRODUCTION
        assert len(conversion_results) == len(financial_paths), "Toutes conversions réussies"
        assert access_time < 0.1, f"Accès production rapides: {access_time:.4f}s"
        assert conversion_time < 0.01, f"Conversions rapides: {conversion_time:.4f}s"

        print(f"✅ Financial Scenario: {len(financial_accounts)} entities, access={access_time:.4f}s, convert={conversion_time:.4f}s")

    def test_supply_chain_scenario(self):
        """Test scénario chaîne logistique complexe"""

        # ===================================================
        # SCÉNARIO 2: Chaîne logistique multi-niveaux
        # ===================================================

        enhanced_dag = EnhancedDAG()

        # Chaîne logistique complète
        supply_chain_accounts = {
            # Fournisseurs matières premières
            "raw_supplier_steel": "α", "raw_supplier_plastic": "β",
            "raw_supplier_electronic": "γ",

            # Manufacturiers composants
            "manuf_components_a": "δ", "manuf_components_b": "ε",
            "manuf_pcb": "ζ", "manuf_assembly": "η",

            # Assembleurs finaux
            "assembler_main": "θ", "assembler_backup": "ι",

            # Distribution
            "warehouse_central": "κ", "warehouse_regional_east": "λ",
            "warehouse_regional_west": "μ", "distribution_center": "ν",

            # Retail
            "retail_chain_a": "ξ", "retail_chain_b": "ο",
            "retail_online": "π", "retail_specialty": "ρ"
        }

        # Configuration supply chain
        result = enhanced_dag.configure_accounts_simple(supply_chain_accounts)
        assert len(result) == len(supply_chain_accounts), "Supply chain complète configurée"

        # Simulation workflows supply chain complexes
        supply_workflows = [
            # Workflow 1: Matière première → Produit fini
            [
                Node("raw_supplier_steel"), Node("manuf_components_a"),
                Node("manuf_assembly"), Node("assembler_main"),
                Node("warehouse_central"), Node("retail_chain_a")
            ],
            # Workflow 2: Composants électroniques → Distribution
            [
                Node("raw_supplier_electronic"), Node("manuf_pcb"),
                Node("assembler_main"), Node("distribution_center"),
                Node("retail_online")
            ],
            # Workflow 3: Supply chain backup
            [
                Node("raw_supplier_plastic"), Node("manuf_components_b"),
                Node("assembler_backup"), Node("warehouse_regional_west"),
                Node("retail_specialty")
            ]
        ]

        # Test workflows avec performance
        start_time = time.perf_counter()
        workflow_results = []

        for i, workflow in enumerate(supply_workflows):
            # Validation chaque étape accessible
            for node in workflow:
                mapping = enhanced_dag.get_current_account_mapping(node.node_id)
                assert mapping is not None, f"Node {node.node_id} accessible in workflow {i}"

            # Conversion workflow complet
            workflow_word = enhanced_dag.convert_path_simple(workflow)
            workflow_results.append(workflow_word)

        workflow_time = time.perf_counter() - start_time

        # VALIDATIONS SUPPLY CHAIN
        assert len(workflow_results) == len(supply_workflows), "Tous workflows traités"
        assert workflow_time < 0.05, f"Workflows rapides: {workflow_time:.4f}s"

        # Test résistance surcharge (simulation pic activité)
        stress_operations = 200
        start_time = time.perf_counter()

        for i in range(stress_operations):
            entity = list(supply_chain_accounts.keys())[i % len(supply_chain_accounts)]
            enhanced_dag.get_current_account_mapping(entity)

        stress_time = time.perf_counter() - start_time
        avg_operation_time = (stress_time / stress_operations) * 1000  # ms

        assert avg_operation_time < 1.0, f"Opérations sous stress rapides: {avg_operation_time:.4f}ms"

        print(f"✅ Supply Chain: {len(supply_workflows)} workflows, {stress_operations} stress ops, avg={avg_operation_time:.4f}ms")

    def test_research_collaboration_scenario(self):
        """Test scénario collaboration recherche académique"""

        # ===================================================
        # SCÉNARIO 3: Collaboration recherche multi-sites
        # ===================================================

        enhanced_dag = EnhancedDAG()

        # Réseau recherche académique
        research_accounts = {
            # Institutions principales
            "university_stanford": "Ѕ", "university_mit": "М",
            "university_cambridge": "Ć", "university_tokyo": "Т",

            # Laboratoires spécialisés
            "lab_ai_research": "Ѵ", "lab_quantum_computing": "Ω",
            "lab_biotech": "Β", "lab_materials": "Π",

            # Chercheurs principaux
            "researcher_alice": "А", "researcher_bob": "Ꞵ",
            "researcher_charlie": "Ꞓ", "researcher_diana": "Ð",

            # Infrastructure
            "computing_cluster_1": "Ξ", "computing_cluster_2": "Ψ",
            "data_repository": "Δ", "publication_system": "Φ"
        }

        # Configuration recherche
        result = enhanced_dag.configure_accounts_simple(research_accounts)
        assert len(result) == len(research_accounts), "Réseau recherche configuré"

        # Simulation patterns collaboration typiques
        collaboration_patterns = [
            # Pattern 1: Recherche collaborative inter-institutions
            [
                Node("researcher_alice"), Node("university_stanford"),
                Node("lab_ai_research"), Node("computing_cluster_1"),
                Node("data_repository"), Node("researcher_bob"),
                Node("university_mit")
            ],
            # Pattern 2: Publication multi-auteurs
            [
                Node("researcher_charlie"), Node("lab_quantum_computing"),
                Node("university_cambridge"), Node("researcher_diana"),
                Node("university_tokyo"), Node("publication_system")
            ]
        ]

        # Validation patterns avec métriques détaillées
        pattern_metrics = []

        for i, pattern in enumerate(collaboration_patterns):
            start_time = time.perf_counter()

            # Validation accessibilité tous nodes
            accessible_nodes = 0
            for node in pattern:
                mapping = enhanced_dag.get_current_account_mapping(node.node_id)
                if mapping is not None:
                    accessible_nodes += 1

            # Conversion pattern
            pattern_word = enhanced_dag.convert_path_simple(pattern)
            pattern_time = time.perf_counter() - start_time

            pattern_metrics.append({
                'pattern_id': i,
                'nodes_count': len(pattern),
                'accessible_nodes': accessible_nodes,
                'conversion_time': pattern_time,
                'word_length': len(pattern_word),
                'success': accessible_nodes == len(pattern)
            })

        # VALIDATIONS RECHERCHE
        successful_patterns = [m for m in pattern_metrics if m['success']]
        assert len(successful_patterns) == len(collaboration_patterns), "Tous patterns collaboration réussis"

        avg_conversion_time = statistics.mean([m['conversion_time'] for m in pattern_metrics])
        assert avg_conversion_time < 0.01, f"Conversions collaboration rapides: {avg_conversion_time:.6f}s"

        # Test accès concurrent simulation (chercheurs multiples)
        concurrent_access_count = 50
        start_time = time.perf_counter()

        for i in range(concurrent_access_count):
            researcher = f"researcher_{['alice', 'bob', 'charlie', 'diana'][i % 4]}"
            mapping = enhanced_dag.get_current_account_mapping(researcher)
            assert mapping is not None, f"Chercheur {researcher} accessible"

        concurrent_time = time.perf_counter() - start_time

        print(f"✅ Research Collaboration: {len(collaboration_patterns)} patterns, concurrent={concurrent_time:.4f}s")


class TestLargeScaleDatasets:
    """Tests datasets volumineux réalistes"""

    def test_enterprise_system_dataset(self):
        """Test dataset système enterprise volumineux"""

        # ===================================================
        # DATASET 1: Système enterprise 100+ entités
        # ===================================================

        enhanced_dag = EnhancedDAG()

        # Génération dataset enterprise réaliste
        enterprise_entities = {}

        # Départements (10)
        departments = ["hr", "finance", "it", "sales", "marketing", "ops", "legal", "r_d", "support", "admin"]
        for i, dept in enumerate(departments):
            enterprise_entities[f"dept_{dept}_source"] = chr(65 + i)  # A-J
            enterprise_entities[f"dept_{dept}_sink"] = chr(75 + i)    # K-T

        # Services (15)
        services = ["auth", "database", "api", "web", "mobile", "analytics", "backup", "monitoring",
                   "logging", "cache", "queue", "storage", "cdn", "security", "reporting"]
        for i, service in enumerate(services):
            enterprise_entities[f"service_{service}"] = chr(945 + i)  # α-ο (Greek letters)

        # Applications (10)
        applications = ["crm", "erp", "hrms", "cms", "billing", "inventory", "support", "analytics", "reporting", "audit"]
        for i, app in enumerate(applications):
            enterprise_entities[f"app_{app}"] = chr(1040 + i)  # Cyrillic А-К

        print(f"Generated enterprise dataset: {len(enterprise_entities)} entities")

        # Configuration dataset avec mesure performance
        start_time = time.perf_counter()
        result = enhanced_dag.configure_accounts_simple(enterprise_entities)
        config_time = time.perf_counter() - start_time

        # VALIDATION DATASET VOLUMINEUX
        assert len(result) == len(enterprise_entities), f"Tous entities configurées: {len(result)}"
        assert config_time < 0.5, f"Configuration dataset volumineux: {config_time:.4f}s"

        # Test accès aléatoire sur dataset complet
        import random
        entity_keys = list(enterprise_entities.keys())
        random.seed(42)  # Reproductibilité

        access_iterations = 500
        start_time = time.perf_counter()

        for i in range(access_iterations):
            random_entity = random.choice(entity_keys)
            mapping = enhanced_dag.get_current_account_mapping(random_entity)
            assert mapping is not None, f"Entity {random_entity} accessible"

        random_access_time = time.perf_counter() - start_time
        avg_access = (random_access_time / access_iterations) * 1000

        # VALIDATION PERFORMANCE DATASET
        assert avg_access < 1.0, f"Accès aléatoire rapide: {avg_access:.4f}ms par opération"

        # Test patterns accès séquentiels (simulation batch processing)
        batch_size = 20
        batches_count = len(entity_keys) // batch_size

        start_time = time.perf_counter()

        for batch_num in range(min(batches_count, 10)):  # Limiter à 10 batches
            batch_start = batch_num * batch_size
            batch_entities = entity_keys[batch_start:batch_start + batch_size]

            for entity in batch_entities:
                enhanced_dag.get_current_account_mapping(entity)

        batch_time = time.perf_counter() - start_time

        print(f"✅ Enterprise Dataset: {len(enterprise_entities)} entities, random_avg={avg_access:.4f}ms, batch_time={batch_time:.4f}s")

    def test_iot_network_dataset(self):
        """Test dataset réseau IoT massif"""

        # ===================================================
        # DATASET 2: Réseau IoT avec capteurs multiples
        # ===================================================

        enhanced_dag = EnhancedDAG()

        # Génération réseau IoT réaliste mais gérable
        iot_devices = {}

        # Gateways IoT (5)
        for i in range(5):
            iot_devices[f"gateway_{i:02d}"] = chr(65 + i)  # A-E

        # Capteurs par catégorie (limités pour éviter collisions)
        sensor_types = ["temp", "humidity", "pressure", "motion", "light"]
        for i, sensor_type in enumerate(sensor_types):
            for j in range(8):  # 8 capteurs par type
                device_id = f"sensor_{sensor_type}_{j:02d}"
                # Utiliser caractères Unicode pour plus de variété
                char_code = 945 + (i * 8) + j  # α + offset
                iot_devices[device_id] = chr(char_code)

        # Actuators (10)
        actuator_types = ["valve", "motor", "relay", "led", "speaker"]
        for i, actuator_type in enumerate(actuator_types):
            for j in range(2):  # 2 actuators par type
                device_id = f"actuator_{actuator_type}_{j:02d}"
                char_code = 1040 + (i * 2) + j  # Cyrillic А + offset
                iot_devices[device_id] = chr(char_code)

        print(f"Generated IoT dataset: {len(iot_devices)} devices")

        # Configuration IoT network
        start_time = time.perf_counter()
        result = enhanced_dag.configure_accounts_simple(iot_devices)
        iot_config_time = time.perf_counter() - start_time

        assert len(result) == len(iot_devices), "Tous devices IoT configurés"
        assert iot_config_time < 0.3, f"Config IoT rapide: {iot_config_time:.4f}s"

        # Simulation patterns IoT typiques
        # Pattern 1: Capteur → Gateway → Cloud
        sensor_to_cloud_paths = []
        sensor_keys = [k for k in iot_devices.keys() if k.startswith("sensor_")]
        gateway_keys = [k for k in iot_devices.keys() if k.startswith("gateway_")]

        for i in range(min(10, len(sensor_keys))):  # 10 paths test
            sensor = sensor_keys[i]
            gateway = gateway_keys[i % len(gateway_keys)]
            path = [Node(sensor), Node(gateway)]
            sensor_to_cloud_paths.append(path)

        # Test conversions IoT paths
        start_time = time.perf_counter()
        iot_conversions = []

        for path in sensor_to_cloud_paths:
            word = enhanced_dag.convert_path_simple(path)
            iot_conversions.append(word)

        iot_conversion_time = time.perf_counter() - start_time

        # VALIDATION IoT
        assert len(iot_conversions) == len(sensor_to_cloud_paths), "Toutes conversions IoT réussies"
        avg_iot_conversion = (iot_conversion_time / len(sensor_to_cloud_paths)) * 1000

        # Simulation trafic IoT haute fréquence
        high_freq_operations = 1000
        start_time = time.perf_counter()

        device_keys = list(iot_devices.keys())
        for i in range(high_freq_operations):
            device = device_keys[i % len(device_keys)]
            enhanced_dag.get_current_account_mapping(device)

        high_freq_time = time.perf_counter() - start_time
        avg_freq = (high_freq_time / high_freq_operations) * 1000

        assert avg_freq < 0.5, f"Trafic IoT haute fréquence: {avg_freq:.4f}ms par opération"

        print(f"✅ IoT Network: {len(iot_devices)} devices, conversion_avg={avg_iot_conversion:.4f}ms, freq={avg_freq:.4f}ms")


class TestPerformanceBenchmarks:
    """Tests benchmarks performance référence"""

    def test_throughput_benchmark(self):
        """Test benchmark débit opérations"""

        # ===================================================
        # BENCHMARK 1: Débit maximum opérations
        # ===================================================

        enhanced_dag = EnhancedDAG()

        # Setup système benchmark
        benchmark_accounts = {f"bench_{i:03d}": chr(65 + (i % 26)) for i in range(26)}
        enhanced_dag.configure_accounts_simple(benchmark_accounts)

        # Mesures débit différentes opérations
        benchmark_results = {}

        # Test 1: Débit accès mappings
        account_keys = list(benchmark_accounts.keys())
        operations_count = 5000

        start_time = time.perf_counter()
        for i in range(operations_count):
            account = account_keys[i % len(account_keys)]
            enhanced_dag.get_current_account_mapping(account)

        mapping_throughput_time = time.perf_counter() - start_time
        mapping_ops_per_sec = operations_count / mapping_throughput_time

        benchmark_results['mapping_access'] = {
            'operations': operations_count,
            'time': mapping_throughput_time,
            'ops_per_sec': mapping_ops_per_sec
        }

        # Test 2: Débit conversions path
        test_paths = [
            [Node("bench_000"), Node("bench_001")],
            [Node("bench_002"), Node("bench_003"), Node("bench_004")],
            [Node("bench_005"), Node("bench_006")]
        ]

        path_operations = 1000
        start_time = time.perf_counter()

        for i in range(path_operations):
            path = test_paths[i % len(test_paths)]
            enhanced_dag.convert_path_simple(path)

        path_throughput_time = time.perf_counter() - start_time
        path_ops_per_sec = path_operations / path_throughput_time

        benchmark_results['path_conversion'] = {
            'operations': path_operations,
            'time': path_throughput_time,
            'ops_per_sec': path_ops_per_sec
        }

        # VALIDATION BENCHMARKS
        assert mapping_ops_per_sec > 1000, f"Débit mapping acceptable: {mapping_ops_per_sec:.0f} ops/sec"
        assert path_ops_per_sec > 500, f"Débit path acceptable: {path_ops_per_sec:.0f} ops/sec"

        print(f"✅ Throughput Benchmark:")
        print(f"   - Mapping access: {mapping_ops_per_sec:.0f} ops/sec")
        print(f"   - Path conversion: {path_ops_per_sec:.0f} ops/sec")

    def test_latency_percentiles_benchmark(self):
        """Test benchmark latence avec percentiles"""

        # ===================================================
        # BENCHMARK 2: Distribution latence détaillée
        # ===================================================

        enhanced_dag = EnhancedDAG()

        # Setup système latence
        latency_accounts = {f"lat_{i:02d}": chr(97 + i) for i in range(20)}  # a-t
        enhanced_dag.configure_accounts_simple(latency_accounts)

        # Mesures latence sur échantillon large
        latency_measurements = []
        account_keys = list(latency_accounts.keys())

        for i in range(2000):  # Large échantillon
            account = account_keys[i % len(account_keys)]

            start_time = time.perf_counter()
            enhanced_dag.get_current_account_mapping(account)
            end_time = time.perf_counter()

            latency_ms = (end_time - start_time) * 1000
            latency_measurements.append(latency_ms)

        # Calcul percentiles
        latency_measurements.sort()
        percentiles = {
            'p50': latency_measurements[len(latency_measurements) // 2],
            'p90': latency_measurements[int(len(latency_measurements) * 0.9)],
            'p95': latency_measurements[int(len(latency_measurements) * 0.95)],
            'p99': latency_measurements[int(len(latency_measurements) * 0.99)]
        }

        latency_stats = {
            'min': min(latency_measurements),
            'max': max(latency_measurements),
            'mean': statistics.mean(latency_measurements),
            'median': statistics.median(latency_measurements),
            'std': statistics.stdev(latency_measurements),
            'percentiles': percentiles
        }

        # VALIDATION LATENCE
        assert percentiles['p99'] < 1.0, f"P99 latence acceptable: {percentiles['p99']:.4f}ms"
        assert percentiles['p95'] < 0.5, f"P95 latence acceptable: {percentiles['p95']:.4f}ms"
        assert latency_stats['mean'] < 0.1, f"Latence moyenne acceptable: {latency_stats['mean']:.4f}ms"

        print(f"✅ Latency Benchmark:")
        print(f"   - Mean: {latency_stats['mean']:.4f}ms")
        print(f"   - P50: {percentiles['p50']:.4f}ms")
        print(f"   - P95: {percentiles['p95']:.4f}ms")
        print(f"   - P99: {percentiles['p99']:.4f}ms")

    def test_memory_efficiency_benchmark(self):
        """Test benchmark efficacité mémoire"""

        # ===================================================
        # BENCHMARK 3: Efficacité utilisation mémoire
        # ===================================================

        import tracemalloc

        # Mesure mémoire baseline
        tracemalloc.start()

        enhanced_dag = EnhancedDAG()
        baseline_memory = get_current_memory_usage()

        # Configuration système test mémoire
        memory_accounts = {f"mem_{i:03d}": chr(945 + (i % 50)) for i in range(50)}  # α-...
        enhanced_dag.configure_accounts_simple(memory_accounts)

        config_memory = get_current_memory_usage()

        # Opérations intensives mémoire
        intensive_operations = 1000
        for i in range(intensive_operations):
            account = f"mem_{i % len(memory_accounts):03d}"
            enhanced_dag.get_current_account_mapping(account)

        operations_memory = get_current_memory_usage()

        tracemalloc.stop()

        # Calcul métriques mémoire
        memory_metrics = {
            'baseline_kb': baseline_memory,
            'config_overhead_kb': config_memory - baseline_memory,
            'operations_overhead_kb': operations_memory - config_memory,
            'total_overhead_kb': operations_memory - baseline_memory,
            'memory_per_account_kb': (config_memory - baseline_memory) / len(memory_accounts),
            'accounts_count': len(memory_accounts),
            'operations_count': intensive_operations
        }

        # VALIDATION MÉMOIRE
        assert memory_metrics['memory_per_account_kb'] < 10, f"Mémoire par compte: {memory_metrics['memory_per_account_kb']:.2f}KB"
        assert memory_metrics['total_overhead_kb'] < 500, f"Overhead total: {memory_metrics['total_overhead_kb']:.2f}KB"

        print(f"✅ Memory Efficiency:")
        print(f"   - Per account: {memory_metrics['memory_per_account_kb']:.2f}KB")
        print(f"   - Config overhead: {memory_metrics['config_overhead_kb']:.2f}KB")
        print(f"   - Total overhead: {memory_metrics['total_overhead_kb']:.2f}KB")


class TestRealWorldWorkflows:
    """Tests workflows monde réel complets"""

    def test_complete_business_workflow(self):
        """Test workflow business complet end-to-end"""

        # ===================================================
        # WORKFLOW 1: Processus commande e-commerce complet
        # ===================================================

        enhanced_dag = EnhancedDAG()

        # Acteurs workflow e-commerce
        ecommerce_accounts = {
            # Client
            "customer_account": "C", "customer_payment_method": "P",

            # Système e-commerce
            "shopping_cart": "S", "order_system": "O",
            "payment_processor": "Π", "inventory_system": "I",

            # Logistique
            "warehouse": "W", "shipping_provider": "Φ",
            "tracking_system": "Т", "delivery_service": "D",

            # Support
            "customer_service": "Σ", "refund_system": "R"
        }

        enhanced_dag.configure_accounts_simple(ecommerce_accounts)

        # Workflow commande complète
        order_workflow = [
            Node("customer_account"), Node("shopping_cart"),
            Node("order_system"), Node("payment_processor"),
            Node("inventory_system"), Node("warehouse"),
            Node("shipping_provider"), Node("tracking_system"),
            Node("delivery_service")
        ]

        # Exécution workflow avec timing
        start_time = time.perf_counter()

        # Validation chaque étape
        for i, step in enumerate(order_workflow):
            mapping = enhanced_dag.get_current_account_mapping(step.node_id)
            assert mapping is not None, f"Étape {i} accessible: {step.node_id}"

        # Conversion workflow complet
        workflow_word = enhanced_dag.convert_path_simple(order_workflow)
        workflow_time = time.perf_counter() - start_time

        # Workflow alternatif (remboursement)
        refund_workflow = [
            Node("customer_account"), Node("customer_service"),
            Node("refund_system"), Node("payment_processor")
        ]

        refund_word = enhanced_dag.convert_path_simple(refund_workflow)

        # VALIDATION WORKFLOW BUSINESS
        assert len(workflow_word) == len(order_workflow), "Workflow complet converti"
        assert len(refund_word) == len(refund_workflow), "Workflow refund converti"
        assert workflow_time < 0.01, f"Workflow rapide: {workflow_time:.6f}s"

        print(f"✅ Business Workflow: {len(order_workflow)} steps, time={workflow_time:.6f}s")
        print(f"   - Order path: {workflow_word}")
        print(f"   - Refund path: {refund_word}")

    def test_data_pipeline_workflow(self):
        """Test workflow pipeline données analytiques"""

        # ===================================================
        # WORKFLOW 2: Pipeline données analytiques
        # ===================================================

        enhanced_dag = EnhancedDAG()

        # Pipeline données modèle ETL
        data_pipeline_accounts = {
            # Sources données
            "data_source_sales": "Ѕ", "data_source_users": "U",
            "data_source_logs": "L", "data_source_external": "Е",

            # Extraction
            "extractor_api": "А", "extractor_db": "Β",
            "extractor_files": "F",

            # Transformation
            "transformer_clean": "Т", "transformer_aggregate": "Г",
            "transformer_enrich": "Є",

            # Loading
            "loader_warehouse": "Λ", "loader_mart": "М",
            "loader_cache": "Ҫ",

            # Analytics
            "analytics_engine": "Α", "reporting_system": "Ρ",
            "dashboard": "Δ"
        }

        enhanced_dag.configure_accounts_simple(data_pipeline_accounts)

        # Workflows pipeline multiples
        pipelines = [
            # Pipeline 1: Sales analytics
            [
                Node("data_source_sales"), Node("extractor_db"),
                Node("transformer_clean"), Node("transformer_aggregate"),
                Node("loader_warehouse"), Node("analytics_engine"),
                Node("dashboard")
            ],
            # Pipeline 2: User behavior
            [
                Node("data_source_users"), Node("data_source_logs"),
                Node("extractor_api"), Node("transformer_enrich"),
                Node("loader_mart"), Node("reporting_system")
            ]
        ]

        # Exécution pipelines avec métriques
        pipeline_results = []

        for i, pipeline in enumerate(pipelines):
            start_time = time.perf_counter()

            # Test accessibilité pipeline
            accessible_steps = 0
            for step in pipeline:
                mapping = enhanced_dag.get_current_account_mapping(step.node_id)
                if mapping is not None:
                    accessible_steps += 1

            # Conversion pipeline
            pipeline_word = enhanced_dag.convert_path_simple(pipeline)
            pipeline_time = time.perf_counter() - start_time

            pipeline_results.append({
                'pipeline_id': i,
                'steps': len(pipeline),
                'accessible_steps': accessible_steps,
                'conversion_time': pipeline_time,
                'word': pipeline_word,
                'success': accessible_steps == len(pipeline)
            })

        # VALIDATION PIPELINES
        successful_pipelines = [r for r in pipeline_results if r['success']]
        assert len(successful_pipelines) == len(pipelines), "Tous pipelines réussis"

        avg_pipeline_time = statistics.mean([r['conversion_time'] for r in pipeline_results])
        assert avg_pipeline_time < 0.01, f"Pipelines rapides: {avg_pipeline_time:.6f}s"

        print(f"✅ Data Pipeline: {len(pipelines)} pipelines, avg_time={avg_pipeline_time:.6f}s")
        for result in pipeline_results:
            print(f"   - Pipeline {result['pipeline_id']}: {result['steps']} steps → {result['word']}")


# =========================================================================
# UTILITAIRES PRODUCTION TESTING
# =========================================================================

def get_current_memory_usage() -> float:
    """Obtient usage mémoire actuel en KB"""
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024  # KB
    except ImportError:
        # Fallback basique si psutil non disponible
        return 0.0


def generate_production_config() -> DAGConfiguration:
    """Génère configuration optimisée production"""
    return DAGConfiguration(
        max_path_enumeration=10000,
        simplex_max_iterations=5000
    )


if __name__ == "__main__":
    # Execution directe pour debugging
    pytest.main([__file__, "-v"])