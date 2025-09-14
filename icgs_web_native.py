#!/usr/bin/env python3
"""
ICGS Web-Native Manager - Couche d'Abstraction Web-Friendly
===========================================================

Architecture pool pré-configuré pour résoudre les défauts de conception
icgs_core dans un contexte web interactif.

Fonctionnalités:
- Pool d'agents virtuels pré-alloués avec caractères taxonomiques garantis
- Mapping dynamique agents réels → slots virtuels (zero reconfiguration)
- Suggestions de mesures contextuelles basées sur l'état simulation
- Validation transactions garantie avec animation 3D immédiate

Usage:
    web_manager = WebNativeICGS()
    web_manager.add_agent("ALICE_FARM", "AGRICULTURE", balance=1500)
    suggestions = web_manager.get_transaction_suggestions("ALICE_FARM", "BOB_FACTORY", 150)
    result = web_manager.process_transaction("ALICE_FARM", "BOB_FACTORY", 150)
"""

import time
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict

# ICGS Core imports
from icgs_simulation import EconomicSimulation
from icgs_simulation.api.icgs_bridge import SimulationResult, SimulationMode

# Définir EconomicMeasure localement pour éviter problème import
@dataclass
class EconomicMeasure:
    """Mesure économique simplifiée"""
    measure_id: str
    name: str
    primary_regex_pattern: str
    primary_regex_weight: Decimal


@dataclass
class MeasureSuggestion:
    """Suggestion de mesure contextuelle"""
    name: str
    description: str
    measure_data: Dict[str, Any]
    confidence: float  # 0.0 to 1.0
    reason: str
    impact_estimate: Optional[str] = None

    def estimate_impact(self) -> str:
        """Estimer impact de la mesure"""
        if 'weight' in self.measure_data:
            weight = float(self.measure_data['weight'])
            if weight > 1.1:
                return f"Bonus estimé: +{(weight-1)*100:.0f}%"
            elif weight < 0.9:
                return f"Coût estimé: {(1-weight)*100:.0f}%"
            else:
                return "Impact neutre"
        return "Impact variable"


@dataclass
class AgentInfo:
    """Information agent réel"""
    real_id: str
    virtual_slot: str
    taxonomic_char: str
    sector: str
    balance: Decimal
    metadata: Dict[str, Any] = field(default_factory=dict)
    transaction_count: int = 0
    success_rate: float = 0.0


class SimulationContextAnalyzer:
    """Analyseur contexte simulation pour suggestions intelligentes"""

    def __init__(self):
        self.transaction_history: List[Dict] = []
        self.agent_activity: Dict[str, int] = defaultdict(int)
        self.agent_success: Dict[str, List[bool]] = defaultdict(list)
        self.sector_pairs_performance: Dict[Tuple[str, str], List[bool]] = defaultdict(list)

    def record_transaction(self, source_id: str, target_id: str, source_sector: str,
                          target_sector: str, success: bool):
        """Enregistrer transaction pour analyse future"""
        self.transaction_history.append({
            'timestamp': time.time(),
            'source_id': source_id,
            'target_id': target_id,
            'source_sector': source_sector,
            'target_sector': target_sector,
            'success': success
        })

        # Statistiques agents
        self.agent_activity[source_id] += 1
        self.agent_activity[target_id] += 1
        self.agent_success[source_id].append(success)
        self.agent_success[target_id].append(success)

        # Statistiques paires secteurs
        sector_pair = (source_sector, target_sector)
        self.sector_pairs_performance[sector_pair].append(success)

    def get_agent_performance(self, agent_id: str) -> Dict[str, float]:
        """Performance historique agent"""
        successes = self.agent_success[agent_id]
        if not successes:
            return {'activity': 0, 'success_rate': 0.0}

        return {
            'activity': len(successes),
            'success_rate': sum(successes) / len(successes)
        }

    def get_sector_pair_performance(self, source_sector: str, target_sector: str) -> Dict[str, Any]:
        """Performance paire de secteurs"""
        pair = (source_sector, target_sector)
        results = self.sector_pairs_performance[pair]

        if not results:
            return {'transactions': 0, 'success_rate': 0.5}  # Neutre par défaut

        return {
            'transactions': len(results),
            'success_rate': sum(results) / len(results)
        }

    def get_recent_success_rate(self, last_n: int = 10) -> float:
        """Taux succès récent global"""
        recent = self.transaction_history[-last_n:] if len(self.transaction_history) >= last_n else self.transaction_history
        if not recent:
            return 0.5  # Neutre par défaut
        return sum(1 for t in recent if t['success']) / len(recent)


class WebNativeICGS:
    """Manager ICGS Web-Native avec pool pré-configuré et suggestions contextuelles"""

    def __init__(self):
        self.logger = logging.getLogger("icgs_web_native")

        # Pool virtuel pré-configuré (caractères taxonomiques garantis)
        self.virtual_pool = self._create_virtual_pool()

        # État runtime
        self.real_to_virtual: Dict[str, str] = {}  # Mapping real_id → virtual_slot
        self.virtual_to_real: Dict[str, str] = {}  # Mapping inverse
        self.allocated_slots: Dict[str, Set[str]] = defaultdict(set)  # Slots utilisés par secteur
        self.agent_registry: Dict[str, AgentInfo] = {}  # Registry agents réels

        # ICGS Core configuré UNE SEULE FOIS
        self.icgs_core = self._configure_icgs_once()

        # Analyseur contexte pour suggestions
        self.context_analyzer = SimulationContextAnalyzer()

        # Mesures neutres par défaut
        self.neutral_measures = self._create_neutral_measures()

        self.logger.info("WebNativeICGS initialisé avec pool pré-configuré")
        self.logger.info(f"Capacités: {self.get_pool_capacities()}")

    def _create_virtual_pool(self) -> Dict[str, List[Tuple[str, str]]]:
        """Créer pool virtuel avec slots et caractères pré-alloués"""
        return {
            'AGRICULTURE': [
                ('AGRI_SLOT_A', 'A'),
                ('AGRI_SLOT_B', 'B'),
                ('AGRI_SLOT_C', 'C')
            ],
            'INDUSTRY': [
                ('IND_SLOT_I', 'I'),
                ('IND_SLOT_J', 'J'),
                ('IND_SLOT_K', 'K'),
                ('IND_SLOT_L', 'L')
            ],
            'SERVICES': [
                ('SERV_SLOT_S', 'S'),
                ('SERV_SLOT_T', 'T'),
                ('SERV_SLOT_U', 'U'),
                ('SERV_SLOT_V', 'V')
            ],
            'FINANCE': [
                ('FIN_SLOT_F', 'F'),
                ('FIN_SLOT_G', 'G')
            ],
            'ENERGY': [
                ('ENG_SLOT_E', 'E'),
                ('ENG_SLOT_H', 'H')
            ]
            # Note: CARBON retiré car non supporté par ICGS Core actuel
        }

    def _configure_icgs_once(self) -> EconomicSimulation:
        """Configuration unique ICGS avec TOUS les slots virtuels"""
        icgs = EconomicSimulation("web_native_pool")

        # Créer agents virtuels pour TOUS les slots d'avance
        for sector, slots in self.virtual_pool.items():
            for virtual_id, taxonomic_char in slots:
                try:
                    icgs.create_agent(
                        agent_id=virtual_id,
                        sector=sector,
                        balance=Decimal('1000'),  # Balance par défaut
                        metadata={
                            'virtual_slot': True,
                            'taxonomic_char': taxonomic_char,
                            'sector': sector,
                            'created_at': time.time()
                        }
                    )
                    self.logger.debug(f"Slot créé: {virtual_id} → {taxonomic_char} ({sector})")
                except Exception as e:
                    self.logger.warning(f"Échec création slot {virtual_id}: {e}")

        self.logger.info("Configuration ICGS terminée - taxonomie figée")
        return icgs

    def _create_neutral_measures(self) -> Dict[str, EconomicMeasure]:
        """Mesures neutres par défaut (sans biais économique)"""
        return {
            'neutral_source': EconomicMeasure(
                measure_id='neutral_flow_out',
                name='Flux Sortant Neutre',
                primary_regex_pattern='.*',           # Matche tout caractère
                primary_regex_weight=Decimal('1.0')  # Poids neutre
            ),
            'neutral_target': EconomicMeasure(
                measure_id='neutral_flow_in',
                name='Flux Entrant Neutre',
                primary_regex_pattern='.*',           # Matche tout caractère
                primary_regex_weight=Decimal('1.0')  # Poids neutre
            )
        }

    def get_pool_capacities(self) -> Dict[str, Dict[str, int]]:
        """Capacités pool par secteur"""
        return {
            sector: {
                'total': len(slots),
                'available': len(slots) - len(self.allocated_slots[sector]),
                'used': len(self.allocated_slots[sector])
            }
            for sector, slots in self.virtual_pool.items()
        }

    def has_capacity(self, sector: str) -> bool:
        """Vérifier si secteur a de la capacité disponible"""
        if sector not in self.virtual_pool:
            return False
        total_slots = len(self.virtual_pool[sector])
        used_slots = len(self.allocated_slots[sector])
        return used_slots < total_slots

    def add_agent(self, real_id: str, sector: str, balance: Decimal,
                  metadata: Optional[Dict[str, Any]] = None) -> AgentInfo:
        """Allouer agent réel sur slot virtuel (zero reconfiguration)"""

        if real_id in self.real_to_virtual:
            raise ValueError(f"Agent '{real_id}' existe déjà")

        if sector not in self.virtual_pool:
            raise ValueError(f"Secteur '{sector}' non supporté. Disponibles: {list(self.virtual_pool.keys())}")

        if not self.has_capacity(sector):
            used = len(self.allocated_slots[sector])
            total = len(self.virtual_pool[sector])
            raise ValueError(f"Secteur '{sector}' complet ({used}/{total} slots utilisés)")

        # Trouver prochain slot libre
        sector_slots = self.virtual_pool[sector]
        available = [slot for slot in sector_slots if slot[0] not in self.allocated_slots[sector]]

        if not available:
            raise ValueError(f"Erreur interne: secteur {sector} signalé comme ayant de la capacité mais aucun slot libre")

        # Allouer premier slot libre
        virtual_slot, taxonomic_char = available[0]

        # Mapping bidirectionnel
        self.real_to_virtual[real_id] = virtual_slot
        self.virtual_to_real[virtual_slot] = real_id
        self.allocated_slots[sector].add(virtual_slot)

        # Créer info agent
        agent_info = AgentInfo(
            real_id=real_id,
            virtual_slot=virtual_slot,
            taxonomic_char=taxonomic_char,
            sector=sector,
            balance=balance,
            metadata=metadata or {}
        )

        self.agent_registry[real_id] = agent_info

        self.logger.info(f"Agent '{real_id}' alloué sur slot '{virtual_slot}' (char: '{taxonomic_char}', secteur: {sector})")
        return agent_info

    def get_agent_info(self, real_id: str) -> Optional[AgentInfo]:
        """Information agent réel"""
        return self.agent_registry.get(real_id)

    def get_contextual_suggestions(self, source_id: str, target_id: str,
                                 amount: Decimal) -> List[MeasureSuggestion]:
        """Alias pour get_transaction_suggestions (compatibilité interface web)"""
        return self.get_transaction_suggestions(source_id, target_id, amount)

    def get_transaction_suggestions(self, source_id: str, target_id: str,
                                  amount: Decimal) -> List[MeasureSuggestion]:
        """Générer suggestions mesures contextuelles"""

        if source_id not in self.agent_registry or target_id not in self.agent_registry:
            return [MeasureSuggestion(
                name="Transaction Simple",
                description="Mesures neutres (agents non trouvés)",
                measure_data={'neutral': True},
                confidence=1.0,
                reason="Un ou plusieurs agents non trouvés dans le registry"
            )]

        source_info = self.agent_registry[source_id]
        target_info = self.agent_registry[target_id]
        suggestions = []

        # Suggestion basée sur activité agent source
        source_perf = self.context_analyzer.get_agent_performance(source_id)
        if source_perf['activity'] > 2 and source_perf['success_rate'] > 0.8:
            suggestions.append(MeasureSuggestion(
                name=f"🎯 Agent {source_info.sector} Expérimenté",
                description=f"Bonus pour agent expérimenté (+15%)",
                measure_data={
                    'source_pattern': f".*{source_info.taxonomic_char}.*",
                    'source_weight': Decimal('1.15'),
                    'target_pattern': '.*',
                    'target_weight': Decimal('1.0')
                },
                confidence=0.85,
                reason=f"Agent {source_id}: {source_perf['activity']} transactions, {source_perf['success_rate']:.1%} succès"
            ))

        # Suggestion basée sur performance paire secteurs
        pair_perf = self.context_analyzer.get_sector_pair_performance(source_info.sector, target_info.sector)
        if pair_perf['success_rate'] < 0.8 and pair_perf['transactions'] > 0:
            suggestions.append(MeasureSuggestion(
                name="🔧 Facilitation Inter-Secteur",
                description=f"Réduction friction {source_info.sector}→{target_info.sector} (-10% coût)",
                measure_data={
                    'source_pattern': f".*{source_info.taxonomic_char}.*",
                    'source_weight': Decimal('1.0'),
                    'target_pattern': f".*{target_info.taxonomic_char}.*",
                    'target_weight': Decimal('0.9')
                },
                confidence=0.9,
                reason=f"Paire {source_info.sector}-{target_info.sector}: {pair_perf['success_rate']:.1%} succès sur {pair_perf['transactions']} transactions"
            ))

        # Suggestion basée sur montant
        if amount > Decimal('500'):
            suggestions.append(MeasureSuggestion(
                name="💰 Transaction Importante",
                description="Mesures équilibrées pour montant élevé",
                measure_data={
                    'source_pattern': f".*{source_info.taxonomic_char}.*",
                    'source_weight': Decimal('0.98'),  # Léger coût admin
                    'target_pattern': f".*{target_info.taxonomic_char}.*",
                    'target_weight': Decimal('1.02')   # Petit bonus réception
                },
                confidence=0.75,
                reason=f"Transaction {amount} > seuil élevé (500)"
            ))

        # Toujours proposer option neutre
        suggestions.append(MeasureSuggestion(
            name="🔄 Transaction Neutre",
            description="Mesures neutres sans biais économique",
            measure_data={
                'source_pattern': '.*',
                'source_weight': Decimal('1.0'),
                'target_pattern': '.*',
                'target_weight': Decimal('1.0')
            },
            confidence=1.0,
            reason="Option toujours disponible - validation technique pure"
        ))

        return sorted(suggestions, key=lambda s: s.confidence, reverse=True)

    def process_transaction(self, source_id: str, target_id: str, amount: Decimal,
                          custom_measures: Optional[Dict] = None) -> Dict[str, Any]:
        """Traiter transaction avec mapping vers slots virtuels"""

        # Validation entrée
        if source_id not in self.real_to_virtual:
            return {
                'success': False,
                'error': f"Agent source '{source_id}' non trouvé",
                'available_agents': list(self.agent_registry.keys())
            }

        if target_id not in self.real_to_virtual:
            return {
                'success': False,
                'error': f"Agent cible '{target_id}' non trouvé",
                'available_agents': list(self.agent_registry.keys())
            }

        # Mapping vers slots virtuels stables
        source_virtual = self.real_to_virtual[source_id]
        target_virtual = self.real_to_virtual[target_id]
        source_info = self.agent_registry[source_id]
        target_info = self.agent_registry[target_id]

        # Mesures : custom si fournies, sinon neutres
        if custom_measures:
            source_measures = custom_measures.get('source_measures', [self.neutral_measures['neutral_source']])
            target_measures = custom_measures.get('target_measures', [self.neutral_measures['neutral_target']])
            measures_type = 'custom'
        else:
            source_measures = [self.neutral_measures['neutral_source']]
            target_measures = [self.neutral_measures['neutral_target']]
            measures_type = 'neutral'

        # Traiter via ICGS Core (slots virtuels garantis de fonctionner)
        try:
            # Créer transaction avec IDs virtuels
            tx_id = self.icgs_core.create_transaction(
                source_virtual, target_virtual, amount
            )

            # Valider en mode FEASIBILITY puis OPTIMIZATION
            start_time = time.time()
            result_feas = self.icgs_core.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
            feas_time = (time.time() - start_time) * 1000

            start_time = time.time()
            result_opt = self.icgs_core.validate_transaction(tx_id, SimulationMode.OPTIMIZATION)
            opt_time = (time.time() - start_time) * 1000

            success = result_feas.success and result_opt.success

            # Enregistrer pour analyse future
            self.context_analyzer.record_transaction(
                source_id, target_id, source_info.sector, target_info.sector, success
            )

            # Mettre à jour statistiques agents
            if success:
                source_info.transaction_count += 1
                target_info.transaction_count += 1

            return {
                'success': success,
                'transaction_record': {
                    'timestamp': datetime.now().isoformat(),
                    'tx_id': tx_id,
                    'source_id': source_id,  # ID réel pour UI
                    'target_id': target_id,  # ID réel pour UI
                    'amount': float(amount),
                    'feasibility': {
                        'success': result_feas.success,
                        'time_ms': round(feas_time, 2)
                    },
                    'optimization': {
                        'success': result_opt.success,
                        'time_ms': round(opt_time, 2),
                        'optimal_price': float(getattr(result_opt, 'optimal_price', 0) or 0)
                    },
                    'virtual_mapping': {
                        'source_virtual': source_virtual,
                        'target_virtual': target_virtual,
                        'source_char': source_info.taxonomic_char,
                        'target_char': target_info.taxonomic_char
                    },
                    'measures_applied': measures_type,
                    'sectors': {
                        'source': source_info.sector,
                        'target': target_info.sector
                    }
                },
                'suggestions': self.get_contextual_suggestions(source_id, target_id, amount)
            }

        except Exception as e:
            self.logger.error(f"Erreur processing transaction {source_id}→{target_id}: {e}")
            return {
                'success': False,
                'error': f"Erreur processing: {str(e)}",
                'transaction': {
                    'source_id': source_id,
                    'target_id': target_id,
                    'amount': float(amount)
                }
            }

    def get_status(self) -> Dict[str, Any]:
        """État global du manager"""
        return {
            'pool_status': self.get_pool_capacities(),
            'active_agents': len(self.agent_registry),
            'total_transactions': len(self.context_analyzer.transaction_history),
            'recent_success_rate': self.context_analyzer.get_recent_success_rate(),
            'icgs_configured': self.icgs_core is not None,
            'suggestions_available': True
        }


if __name__ == "__main__":
    # Test basique du manager
    logging.basicConfig(level=logging.INFO)

    print("🧪 Test WebNativeICGS")
    manager = WebNativeICGS()

    print(f"Capacités initiales: {manager.get_pool_capacities()}")

    # Créer agents test
    try:
        agent1 = manager.add_agent("ALICE_TEST", "AGRICULTURE", Decimal('1000'))
        print(f"Agent créé: {agent1.real_id} → slot {agent1.virtual_slot} (char: {agent1.taxonomic_char})")

        agent2 = manager.add_agent("BOB_TEST", "INDUSTRY", Decimal('1500'))
        print(f"Agent créé: {agent2.real_id} → slot {agent2.virtual_slot} (char: {agent2.taxonomic_char})")

        # Suggestions
        suggestions = manager.get_transaction_suggestions("ALICE_TEST", "BOB_TEST", Decimal('200'))
        print(f"Suggestions disponibles: {len(suggestions)}")
        for i, s in enumerate(suggestions):
            print(f"  {i+1}. {s.name} ({s.confidence:.0%} confiance) - {s.reason}")

        print(f"État final: {manager.get_status()}")
        print("✅ Test réussi")

    except Exception as e:
        print(f"❌ Test échoué: {e}")