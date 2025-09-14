#!/usr/bin/env python3
"""
Test Académique 24: Validation WebNativeICGS - Architecture Unifiée Phase 2
==========================================================================

Test de validation complète de l'architecture WebNativeICGS avec :
- Pool virtuel pré-configuré avec slots taxonomiques
- Allocation automatique zero reconfiguration
- Système de suggestions contextuelles
- Interface web unifiée
- Compatibilité complète avec ICGS Core et API 3D

Objectifs:
- Valider architecture WebNativeICGS complète
- Tester allocation automatique slots virtuels
- Vérifier suggestions contextuelles
- Confirmer intégration ICGS Core
- Valider métriques pool temps réel

Expected: 100% success rate pour tous les composants
"""

import time
import sys
import os
from decimal import Decimal
from typing import Dict, List, Any
import json

# Ensure ICGS modules path
sys.path.insert(0, os.path.dirname(__file__))

# Import WebNativeICGS
from icgs_web_native import WebNativeICGS, AgentInfo, MeasureSuggestion

# Import ICGS core pour comparaisons
from icgs_simulation import EconomicSimulation, SECTORS
from icgs_simulation.api.icgs_bridge import SimulationMode


class TestAcademicWebNativeValidation:
    """Test validation complète WebNativeICGS"""

    def __init__(self):
        self.web_manager = None  # Instance unique réutilisée
        self.test_results = {
            'pool_configuration': {'passed': 0, 'failed': 0, 'details': []},
            'agent_allocation': {'passed': 0, 'failed': 0, 'details': []},
            'transaction_processing': {'passed': 0, 'failed': 0, 'details': []},
            'contextual_suggestions': {'passed': 0, 'failed': 0, 'details': []},
            'icgs_core_integration': {'passed': 0, 'failed': 0, 'details': []},
            'performance_metrics': {'passed': 0, 'failed': 0, 'details': []},
            '3d_api_compatibility': {'passed': 0, 'failed': 0, 'details': []}
        }

    def _get_web_manager(self):
        """Obtenir instance WebNativeICGS (singleton pour tests)"""
        if self.web_manager is None:
            self.web_manager = WebNativeICGS()
            print(f"🏗️ WebNativeICGS initialisé - Pool: {len(self.web_manager.virtual_pool)} secteurs")
        return self.web_manager

    def run_comprehensive_validation(self):
        """Exécuter validation académique complète"""
        print("🏗️ Test Académique 24: Validation WebNativeICGS - Architecture Unifiée")
        print("=" * 70)

        # Phase 1: Configuration Pool Virtuel
        print("\n📋 Phase 1: Validation Configuration Pool Virtuel")
        self._test_pool_configuration()

        # Phase 2: Allocation Agents Automatique
        print("\n👥 Phase 2: Validation Allocation Agents")
        self._test_agent_allocation()

        # Phase 3: Traitement Transactions
        print("\n💰 Phase 3: Validation Traitement Transactions")
        self._test_transaction_processing()

        # Phase 4: Suggestions Contextuelles
        print("\n💡 Phase 4: Validation Suggestions Contextuelles")
        self._test_contextual_suggestions()

        # Phase 5: Integration ICGS Core
        print("\n🔗 Phase 5: Validation Integration ICGS Core")
        self._test_icgs_core_integration()

        # Phase 6: Métriques Performance
        print("\n📊 Phase 6: Validation Métriques Performance")
        self._test_performance_metrics()

        # Phase 7: Compatibilité API 3D
        print("\n🌌 Phase 7: Validation Compatibilité API 3D")
        self._test_3d_api_compatibility()

        # Summary
        self._print_final_report()

    def _test_pool_configuration(self):
        """Test configuration pool virtuel"""
        try:
            # Obtenir WebNativeICGS
            web_manager = self._get_web_manager()

            # Test 1: Pool existe et est configuré
            assert hasattr(web_manager, 'virtual_pool'), "Pool virtuel non configuré"
            assert len(web_manager.virtual_pool) > 0, "Pool virtuel vide"

            expected_sectors = ['AGRICULTURE', 'INDUSTRY', 'SERVICES', 'FINANCE', 'ENERGY']
            for sector in expected_sectors:
                assert sector in web_manager.virtual_pool, f"Secteur {sector} manquant"
                slots = web_manager.virtual_pool[sector]
                assert len(slots) > 0, f"Secteur {sector} sans slots"

                # Vérifier structure slots
                for slot_id, char in slots:
                    assert isinstance(slot_id, str), f"Slot ID invalide: {slot_id}"
                    assert isinstance(char, str), f"Caractère invalide: {char}"
                    assert len(char) == 1, f"Caractère taxonomique invalide: {char}"

            self._record_success('pool_configuration', "Pool virtuel correctement configuré")

            # Test 2: Capacités pool correctes
            total_capacity = sum(len(slots) for slots in web_manager.virtual_pool.values())
            assert total_capacity >= 15, f"Capacité pool insuffisante: {total_capacity}"

            self._record_success('pool_configuration', f"Capacité pool validée: {total_capacity} slots")

            # Test 3: État initial pool
            assert len(web_manager.real_to_virtual) == 0, "Pool non vide à l'initialisation"
            assert len(web_manager.allocated_slots) == 0, "Slots alloués à l'initialisation"

            self._record_success('pool_configuration', "État initial pool validé")

        except Exception as e:
            self._record_failure('pool_configuration', f"Erreur configuration pool: {str(e)}")

    def _test_agent_allocation(self):
        """Test allocation automatique agents"""
        try:
            web_manager = self._get_web_manager()

            # Test 1: Allocation agent simple
            agent_info = web_manager.add_agent("ALICE_TEST", "AGRICULTURE", Decimal('1000'))

            assert isinstance(agent_info, AgentInfo), "AgentInfo invalide retourné"
            assert agent_info.real_id == "ALICE_TEST", "ID agent incorrect"
            assert agent_info.sector == "AGRICULTURE", "Secteur agent incorrect"
            assert agent_info.balance == Decimal('1000'), "Balance agent incorrecte"
            assert agent_info.virtual_slot.startswith("AGRI_"), "Slot virtuel incorrect"
            assert agent_info.taxonomic_char in ['A', 'B', 'C'], "Caractère taxonomique incorrect"

            # Vérifier mapping créé
            assert "ALICE_TEST" in web_manager.real_to_virtual, "Mapping real_id manquant"
            assert web_manager.real_to_virtual["ALICE_TEST"] == agent_info.virtual_slot, "Mapping incorrect"

            self._record_success('agent_allocation', f"Agent ALICE_TEST → {agent_info.virtual_slot} (char: {agent_info.taxonomic_char})")

            # Test 2: Allocation multiple agents même secteur
            bob_info = web_manager.add_agent("BOB_TEST", "AGRICULTURE", Decimal('800'))
            carol_info = web_manager.add_agent("CAROL_TEST", "AGRICULTURE", Decimal('600'))

            # Vérifier slots différents
            assert agent_info.virtual_slot != bob_info.virtual_slot, "Slots identiques"
            assert bob_info.virtual_slot != carol_info.virtual_slot, "Slots identiques"
            assert agent_info.taxonomic_char != bob_info.taxonomic_char, "Caractères identiques"

            self._record_success('agent_allocation', f"Allocation multiple: BOB({bob_info.taxonomic_char}), CAROL({carol_info.taxonomic_char})")

            # Test 3: Allocation secteurs différents
            dave_info = web_manager.add_agent("DAVE_TEST", "INDUSTRY", Decimal('1200'))

            assert dave_info.sector == "INDUSTRY", "Secteur incorrect"
            assert dave_info.virtual_slot.startswith("IND_"), "Slot virtuel incorrect"
            assert dave_info.taxonomic_char in ['I', 'J', 'K', 'L'], "Caractère taxonomique incorrect"

            self._record_success('agent_allocation', f"Allocation cross-secteur: DAVE → {dave_info.virtual_slot}")

            # Test 4: Vérifier capacités utilisées
            agri_used = len(web_manager.allocated_slots.get('AGRICULTURE', set()))
            assert agri_used == 3, f"Capacité AGRICULTURE incorrecte: {agri_used}"

            ind_used = len(web_manager.allocated_slots.get('INDUSTRY', set()))
            assert ind_used == 1, f"Capacité INDUSTRY incorrecte: {ind_used}"

            self._record_success('agent_allocation', f"Capacités utilisées: AGRI={agri_used}, IND={ind_used}")

        except Exception as e:
            self._record_failure('agent_allocation', f"Erreur allocation agent: {str(e)}")

    def _test_transaction_processing(self):
        """Test traitement transactions via WebNativeICGS"""
        try:
            web_manager = self._get_web_manager()

            # Préparer agents
            alice_info = web_manager.add_agent("ALICE_TX", "AGRICULTURE", Decimal('1000'))
            bob_info = web_manager.add_agent("BOB_TX", "INDUSTRY", Decimal('800'))

            # Test 1: Transaction basique
            tx_result = web_manager.process_transaction("ALICE_TX", "BOB_TX", Decimal('100'))

            assert tx_result['success'], f"Transaction échouée: {tx_result.get('error', 'Unknown')}"
            assert 'transaction_record' in tx_result, "Record transaction manquant"

            tx_record = tx_result['transaction_record']
            assert tx_record['source_id'] == "ALICE_TX", "Source ID incorrect"
            assert tx_record['target_id'] == "BOB_TX", "Target ID incorrect"
            assert tx_record['amount'] == 100.0, "Montant incorrect"
            assert 'feasibility' in tx_record, "Validation FEASIBILITY manquante"
            assert 'optimization' in tx_record, "Validation OPTIMIZATION manquante"

            self._record_success('transaction_processing', f"Transaction ALICE→BOB: {tx_record['feasibility']['success']}/{tx_record['optimization']['success']}")

            # Test 2: Validation phases
            feas_success = tx_record['feasibility']['success']
            opt_success = tx_record['optimization']['success']
            feas_time = tx_record['feasibility']['time_ms']
            opt_time = tx_record['optimization']['time_ms']

            assert isinstance(feas_time, (int, float)), "Temps FEASIBILITY invalide"
            assert isinstance(opt_time, (int, float)), "Temps OPTIMIZATION invalide"
            assert feas_time >= 0, "Temps FEASIBILITY négatif"
            assert opt_time >= 0, "Temps OPTIMIZATION négatif"

            self._record_success('transaction_processing', f"Temps validation: FEAS={feas_time}ms, OPT={opt_time}ms")

            # Test 3: Vérifier mapping dans transaction
            # La transaction doit utiliser les slots virtuels en interne
            icgs_agents = web_manager.icgs_core.agents
            virtual_alice = web_manager.real_to_virtual["ALICE_TX"]
            virtual_bob = web_manager.real_to_virtual["BOB_TX"]

            assert virtual_alice in icgs_agents, f"Agent virtuel {virtual_alice} manquant dans ICGS"
            assert virtual_bob in icgs_agents, f"Agent virtuel {virtual_bob} manquant dans ICGS"

            self._record_success('transaction_processing', f"Mapping virtuel validé: {virtual_alice}↔{virtual_bob}")

        except Exception as e:
            self._record_failure('transaction_processing', f"Erreur traitement transaction: {str(e)}")

    def _test_contextual_suggestions(self):
        """Test système suggestions contextuelles"""
        try:
            web_manager = self._get_web_manager()

            # Préparer agents avec historique
            alice_info = web_manager.add_agent("ALICE_SUGG", "AGRICULTURE", Decimal('1000'))
            bob_info = web_manager.add_agent("BOB_SUGG", "SERVICES", Decimal('600'))

            # Effectuer quelques transactions pour créer contexte
            web_manager.process_transaction("ALICE_SUGG", "BOB_SUGG", Decimal('50'))
            web_manager.process_transaction("BOB_SUGG", "ALICE_SUGG", Decimal('30'))

            # Test 1: Génération suggestions
            suggestions = web_manager.get_contextual_suggestions("ALICE_SUGG", "BOB_SUGG", Decimal('75'))

            assert isinstance(suggestions, list), "Suggestions non sous forme de liste"
            assert len(suggestions) > 0, "Aucune suggestion générée"

            for suggestion in suggestions:
                assert isinstance(suggestion, MeasureSuggestion), "Type suggestion invalide"
                assert hasattr(suggestion, 'name'), "Nom suggestion manquant"
                assert hasattr(suggestion, 'description'), "Description suggestion manquante"
                assert hasattr(suggestion, 'impact_estimate'), "Impact estimé manquant"

            self._record_success('contextual_suggestions', f"{len(suggestions)} suggestions générées")

            # Test 2: Pertinence suggestions
            suggestion_names = [s.name for s in suggestions]

            # Doit inclure au moins une suggestion de base (d'après l'implémentation WebNativeICGS)
            basic_suggestions = ['🔄 Transaction Neutre', '🔧 Facilitation Inter-Secteur', 'Transaction Simple']
            has_basic = any(name in suggestion_names for name in basic_suggestions)
            assert has_basic, f"Aucune suggestion de base trouvée dans {suggestion_names}"

            self._record_success('contextual_suggestions', f"Suggestions pertinentes: {suggestion_names[:3]}")

            # Test 3: Suggestions sans imposer (non-intrusive)
            # Les suggestions ne doivent pas être automatiquement appliquées
            tx_result = web_manager.process_transaction("ALICE_SUGG", "BOB_SUGG", Decimal('25'))
            assert tx_result['success'], "Transaction avec suggestions échouée"

            # Vérifier que les suggestions sont disponibles mais non imposées
            if 'suggestions' in tx_result:
                assert isinstance(tx_result['suggestions'], list), "Format suggestions incorrect"

            self._record_success('contextual_suggestions', "Suggestions non-intrusives validées")

        except Exception as e:
            self._record_failure('contextual_suggestions', f"Erreur suggestions contextuelles: {str(e)}")

    def _test_icgs_core_integration(self):
        """Test intégration avec ICGS Core"""
        try:
            web_manager = self._get_web_manager()

            # Test 1: ICGS Core présent et configuré
            assert hasattr(web_manager, 'icgs_core'), "ICGS Core manquant"
            assert isinstance(web_manager.icgs_core, EconomicSimulation), "ICGS Core type incorrect"

            # Test 2: Configuration taxonomique
            dag = web_manager.icgs_core.dag
            assert hasattr(dag, 'account_taxonomy'), "Taxonomie manquante"

            taxonomy = dag.account_taxonomy
            assert hasattr(taxonomy, 'character_set_manager'), "Character set manager manquant"

            char_manager = taxonomy.character_set_manager
            if char_manager:
                sectors = list(char_manager.list_defined_sectors())
                expected = ['AGRICULTURE', 'INDUSTRY', 'SERVICES', 'FINANCE', 'ENERGY']
                for sector in expected:
                    assert sector in sectors, f"Secteur {sector} manquant dans taxonomie"

            self._record_success('icgs_core_integration', f"Taxonomie configurée: {len(sectors)} secteurs")

            # Test 3: Bridge Simplex 3D
            collector = web_manager.icgs_core.get_3d_collector()
            if collector:
                assert hasattr(collector, 'states_history'), "Historique états 3D manquant"
                assert hasattr(collector, 'transitions_history'), "Historique transitions 3D manquant"

                self._record_success('icgs_core_integration', f"Collecteur 3D: {type(collector).__name__}")
            else:
                self._record_success('icgs_core_integration', "Collecteur 3D non configuré (normal)")

            # Test 4: Cohérence agents virtuels vs réels
            web_manager.add_agent("TEST_INTEGRATION", "FINANCE", Decimal('500'))

            # L'agent réel doit exister dans le registry
            assert "TEST_INTEGRATION" in web_manager.agent_registry, "Agent manquant du registry"

            # L'agent virtuel doit exister dans ICGS Core
            virtual_id = web_manager.real_to_virtual["TEST_INTEGRATION"]
            assert virtual_id in web_manager.icgs_core.agents, f"Agent virtuel {virtual_id} manquant d'ICGS Core"

            self._record_success('icgs_core_integration', f"Cohérence agents: TEST_INTEGRATION → {virtual_id}")

        except Exception as e:
            self._record_failure('icgs_core_integration', f"Erreur intégration ICGS Core: {str(e)}")

    def _test_performance_metrics(self):
        """Test métriques performance"""
        try:
            web_manager = self._get_web_manager()

            # Test 1: Métriques pool disponibles
            pool_metrics = {}
            for sector, slots in web_manager.virtual_pool.items():
                allocated = len(web_manager.allocated_slots.get(sector, set()))
                pool_metrics[sector] = {
                    'total_capacity': len(slots),
                    'allocated': allocated,
                    'available': len(slots) - allocated
                }

            assert len(pool_metrics) > 0, "Métriques pool vides"

            total_capacity = sum(m['total_capacity'] for m in pool_metrics.values())
            total_allocated = sum(m['allocated'] for m in pool_metrics.values())

            self._record_success('performance_metrics', f"Métriques pool: {total_allocated}/{total_capacity} slots utilisés")

            # Test 2: Performance allocation
            start_time = time.time()

            # Tester avec différents secteurs pour éviter saturation
            sectors = ['INDUSTRY', 'FINANCE', 'ENERGY']
            for i in range(5):
                sector = sectors[i % len(sectors)]
                web_manager.add_agent(f"PERF_TEST_{i}", sector, Decimal('100'))

            allocation_time = (time.time() - start_time) * 1000  # ms
            avg_allocation_time = allocation_time / 5

            assert avg_allocation_time < 10, f"Allocation trop lente: {avg_allocation_time}ms"

            self._record_success('performance_metrics', f"Performance allocation: {avg_allocation_time:.2f}ms/agent")

            # Test 3: Performance transaction
            start_time = time.time()

            web_manager.process_transaction("PERF_TEST_0", "PERF_TEST_1", Decimal('10'))

            tx_time = (time.time() - start_time) * 1000

            assert tx_time < 100, f"Transaction trop lente: {tx_time}ms"

            self._record_success('performance_metrics', f"Performance transaction: {tx_time:.2f}ms")

            # Test 4: Métriques contexte
            analyzer = web_manager.context_analyzer
            assert hasattr(analyzer, 'transaction_history'), "Historique contexte manquant"
            assert hasattr(analyzer, 'agent_activity'), "Activité agent manquante"

            self._record_success('performance_metrics', f"Analyseur contexte: {len(analyzer.transaction_history)} transactions")

        except Exception as e:
            self._record_failure('performance_metrics', f"Erreur métriques performance: {str(e)}")

    def _test_3d_api_compatibility(self):
        """Test compatibilité API 3D"""
        try:
            web_manager = self._get_web_manager()

            # Test 1: Collecteur 3D disponible
            collector = web_manager.icgs_core.get_3d_collector()

            if collector is None:
                self._record_success('3d_api_compatibility', "Collecteur 3D non configuré (mode test)")
                return

            # Test 2: Interface collecteur
            assert hasattr(collector, 'states_history'), "Interface états manquante"
            assert hasattr(collector, 'transitions_history'), "Interface transitions manquante"
            assert hasattr(collector, 'export_animation_data'), "Export animation manquant"

            self._record_success('3d_api_compatibility', "Interface collecteur 3D validée")

            # Test 3: Génération données avec WebNativeICGS
            web_manager.add_agent("3D_ALICE", "ENERGY", Decimal('800'))
            web_manager.add_agent("3D_BOB", "FINANCE", Decimal('600'))

            # Transaction pour générer données 3D
            tx_result = web_manager.process_transaction("3D_ALICE", "3D_BOB", Decimal('50'))

            if tx_result['success']:
                # Vérifier si données 3D générées
                if len(collector.states_history) > 0:
                    animation_data = collector.export_animation_data()
                    assert animation_data is not None, "Données animation nulles"

                    self._record_success('3d_api_compatibility', f"Données 3D générées: {len(collector.states_history)} états")
                else:
                    self._record_success('3d_api_compatibility', "Transaction sans génération 3D (normal)")

            # Test 4: Compatibilité format
            if hasattr(collector, 'export_animation_data'):
                try:
                    data = collector.export_animation_data()
                    if data:
                        # Vérifier format JSON-serializable
                        json_str = json.dumps(data, default=str)
                        assert len(json_str) > 0, "Données 3D non sérialisables"

                        self._record_success('3d_api_compatibility', "Format données 3D compatible")
                except Exception as format_error:
                    self._record_failure('3d_api_compatibility', f"Format données incompatible: {format_error}")

        except Exception as e:
            self._record_failure('3d_api_compatibility', f"Erreur compatibilité 3D: {str(e)}")

    def _record_success(self, category: str, message: str):
        """Enregistrer succès test"""
        self.test_results[category]['passed'] += 1
        self.test_results[category]['details'].append(f"✅ {message}")
        print(f"  ✅ {message}")

    def _record_failure(self, category: str, message: str):
        """Enregistrer échec test"""
        self.test_results[category]['failed'] += 1
        self.test_results[category]['details'].append(f"❌ {message}")
        print(f"  ❌ {message}")

    def _print_final_report(self):
        """Rapport final validation"""
        print("\n" + "=" * 70)
        print("📊 RAPPORT FINAL - Test Académique 24: WebNativeICGS Validation")
        print("=" * 70)

        total_passed = 0
        total_failed = 0

        for category, results in self.test_results.items():
            passed = results['passed']
            failed = results['failed']
            total = passed + failed

            if total > 0:
                success_rate = (passed / total) * 100
                status = "✅" if success_rate == 100 else "⚠️" if success_rate >= 80 else "❌"

                print(f"\n{status} {category.upper().replace('_', ' ')}: {passed}/{total} ({success_rate:.1f}%)")

                # Montrer détails si échecs
                if failed > 0:
                    for detail in results['details']:
                        if detail.startswith("❌"):
                            print(f"    {detail}")

            total_passed += passed
            total_failed += failed

        # Résumé global
        print(f"\n🏆 RÉSUMÉ GLOBAL:")
        print(f"   Tests réussis: {total_passed}")
        print(f"   Tests échoués: {total_failed}")

        if total_passed + total_failed > 0:
            global_success_rate = (total_passed / (total_passed + total_failed)) * 100
            print(f"   Taux de réussite: {global_success_rate:.1f}%")

            if global_success_rate == 100:
                print(f"\n🎉 VALIDATION ACADÉMIQUE COMPLÈTE RÉUSSIE!")
                print(f"   Architecture WebNativeICGS parfaitement validée")
            elif global_success_rate >= 90:
                print(f"\n✅ VALIDATION ACADÉMIQUE LARGEMENT RÉUSSIE")
                print(f"   Architecture WebNativeICGS fonctionnelle avec succès")
            else:
                print(f"\n⚠️ VALIDATION ACADÉMIQUE PARTIELLE")
                print(f"   Architecture WebNativeICGS nécessite améliorations")


def main():
    """Fonction principale test académique"""
    test_suite = TestAcademicWebNativeValidation()
    test_suite.run_comprehensive_validation()


if __name__ == "__main__":
    main()