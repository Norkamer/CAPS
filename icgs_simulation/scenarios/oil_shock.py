"""
Scénario Choc Pétrolier - ENERGY -40%

Simule un choc pétrolier avec réduction drastique du secteur ENERGY et
validation de la propagation économique inter-sectorielle:
- ENERGY: Réduction capacité -40% (crise énergétique)
- Propagation: Impact sur INDUSTRY (-15%), SERVICES (-10%), AGRICULTURE (-8%)
- FINANCE: Rôle stabilisateur (+10% pour compenser liquidités)
- Validation résilience économique et adaptation

Architecture:
- Phase 1: Économie stable (baseline 2 jours)
- Phase 2: Choc énergétique (-40% ENERGY, jour 3)
- Phase 3: Propagation inter-sectorielle (jours 4-5)
- Phase 4: Adaptation économique (jours 6-7)
- Métriques: Résilience, propagation, récupération
"""

import time
import logging
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..api.icgs_bridge import EconomicSimulation, SimulationMode, SimulationResult


@dataclass
class OilShockPhase:
    """Phase du scénario choc pétrolier"""
    phase_number: int
    phase_name: str
    day_start: int
    day_end: int
    sector_impacts: Dict[str, float]  # secteur -> multiplicateur balance (-40% = 0.6)
    expected_feasibility: float
    description: str


@dataclass
class OilShockResults:
    """Résultats complets scénario Choc Pétrolier"""
    success: bool
    simulation_id: str
    start_time: datetime
    end_time: datetime
    total_duration_hours: float

    # Métriques par phase
    baseline_feasibility: float
    shock_feasibility: float
    propagation_feasibility: float
    adaptation_feasibility: float

    # Impact économique
    baseline_volume: Decimal
    shock_impact_percent: float
    recovery_percent: float

    # Résilience secteurs
    sector_resilience: Dict[str, Dict[str, float]]  # secteur -> {baseline, shock, recovery}

    # Validation propagation
    propagation_validated: bool
    adaptation_validated: bool
    resilience_target_met: bool

    # Détails phases
    phase_results: List[Dict[str, any]]


class OilShockScenario:
    """
    Scénario Choc Pétrolier - Simulation Crise Énergétique

    Teste résilience économique face à choc externe majeur
    avec validation propagation inter-sectorielle et adaptation.
    """

    def __init__(self, simulation: EconomicSimulation,
                 energy_impact: float = -0.40,
                 min_recovery_rate: float = 0.65):
        """
        Initialise scénario choc pétrolier

        Args:
            simulation: Instance EconomicSimulation configurée
            energy_impact: Impact sur secteur ENERGY (défaut -40%)
            min_recovery_rate: Taux récupération minimum attendu (défaut 65%)
        """
        self.simulation = simulation
        self.energy_impact = energy_impact
        self.min_recovery_rate = min_recovery_rate

        self.logger = logging.getLogger(f"oil_shock.{simulation.simulation_id}")
        self.start_time: Optional[datetime] = None

        # Phases du scénario
        self.phases = self._define_shock_phases()

        # Agents économiques pré-adaptation
        self.economic_agents: Dict[str, List[str]] = {}
        self.original_balances: Dict[str, Decimal] = {}  # Sauvegarde balances originales

    def _define_shock_phases(self) -> List[OilShockPhase]:
        """Définit les phases du scénario choc pétrolier"""
        return [
            OilShockPhase(
                phase_number=1,
                phase_name="Baseline Stable",
                day_start=1, day_end=2,
                sector_impacts={
                    'AGRICULTURE': 1.0,
                    'INDUSTRY': 1.0,
                    'SERVICES': 1.0,
                    'FINANCE': 1.0,
                    'ENERGY': 1.0
                },
                expected_feasibility=0.65,
                description="Économie stable avant choc"
            ),
            OilShockPhase(
                phase_number=2,
                phase_name="Choc Énergétique",
                day_start=3, day_end=3,
                sector_impacts={
                    'AGRICULTURE': 0.95,  # Léger impact (fuel agricole)
                    'INDUSTRY': 0.88,     # Impact modéré (énergie production)
                    'SERVICES': 0.92,     # Impact léger (transport)
                    'FINANCE': 1.05,      # Rôle stabilisateur
                    'ENERGY': 0.60       # Impact majeur (-40%)
                },
                expected_feasibility=0.45,
                description="Choc pétrolier initial"
            ),
            OilShockPhase(
                phase_number=3,
                phase_name="Propagation Inter-Sectorielle",
                day_start=4, day_end=5,
                sector_impacts={
                    'AGRICULTURE': 0.92,  # Propagation coûts énergie
                    'INDUSTRY': 0.85,     # Forte dépendance énergie
                    'SERVICES': 0.90,     # Impact logistique
                    'FINANCE': 1.10,      # Intervention stabilisation
                    'ENERGY': 0.55       # Aggravation temporaire
                },
                expected_feasibility=0.40,
                description="Propagation impacts sectoriels"
            ),
            OilShockPhase(
                phase_number=4,
                phase_name="Adaptation Économique",
                day_start=6, day_end=7,
                sector_impacts={
                    'AGRICULTURE': 0.96,  # Début adaptation
                    'INDUSTRY': 0.90,     # Optimisations énergie
                    'SERVICES': 0.94,     # Nouvelles logistiques
                    'FINANCE': 1.08,      # Support adaptation
                    'ENERGY': 0.70       # Récupération partielle
                },
                expected_feasibility=0.55,
                description="Adaptation et récupération partielle"
            )
        ]

    def setup_oil_shock_economy(self) -> int:
        """
        Configure agents économiques pour scénario choc pétrolier
        Distribution compatible mode 40_agents: AGRICULTURE(8) + INDUSTRY(10) + SERVICES(12) + FINANCE(5) + ENERGY(8) = 43 agents
        """
        # Distribution compatible capacité mode 40_agents
        shock_distribution = {
            'AGRICULTURE': 8,   # Sécurité alimentaire critique
            'INDUSTRY': 10,     # Secteur vulnérable énergie
            'SERVICES': 12,     # Secteur dominant mais adaptable
            'FINANCE': 5,       # Stabilisateur économique
            'ENERGY': 8         # Secteur test résilience choc
        }

        # Balances sectorielles renforcées pour résilience
        sector_balances = {
            'AGRICULTURE': Decimal('1600'),  # Stocks sécurité
            'INDUSTRY': Decimal('1300'),     # Capital résistant
            'SERVICES': Decimal('1000'),     # Flexibilité adaptation
            'FINANCE': Decimal('4000'),      # Réserves intervention
            'ENERGY': Decimal('2800')        # Infrastructure critique
        }

        total_agents = 0

        for sector, count in shock_distribution.items():
            self.economic_agents[sector] = []
            base_balance = sector_balances[sector]

            for i in range(count):
                agent_id = f"SHOCK_{sector}_{i+1:02d}"

                # Variation balance ±20% pour hétérogénéité
                balance_factor = Decimal(str(0.80 + 0.40 * (i / count)))
                agent_balance = base_balance * balance_factor

                agent = self.simulation.create_agent(agent_id, sector, agent_balance)
                self.economic_agents[sector].append(agent_id)
                self.original_balances[agent_id] = agent_balance
                total_agents += 1

        self.logger.info(f"Économie choc pétrolier configurée: {total_agents} agents, 5 secteurs")

        # Log distribution
        for sector, agents in self.economic_agents.items():
            self.logger.info(f"  {sector}: {len(agents)} agents, balance base {sector_balances[sector]}")

        return total_agents

    def apply_sector_shock_impacts(self, phase: OilShockPhase) -> Dict[str, int]:
        """
        Applique impacts sectoriels selon phase choc pétrolier
        Simulation via modulation intensité flux (agents balances préservées)

        Returns:
            Statistiques impacts appliqués par secteur
        """
        impacts_applied = {}

        self.logger.info(f"Application impacts Phase {phase.phase_number}: {phase.phase_name}")

        for sector, impact_multiplier in phase.sector_impacts.items():
            impact_percent = (impact_multiplier - 1.0) * 100
            impacts_applied[sector] = impact_percent

            self.logger.info(f"  {sector}: {impact_percent:+.1f}% impact")

        return impacts_applied

    def simulate_shock_phase(self, phase: OilShockPhase) -> Dict[str, any]:
        """
        Simule une phase du choc pétrolier

        Returns:
            Résultats détaillés de la phase
        """
        self.logger.info(f"=== Phase {phase.phase_number}: {phase.phase_name} (Jours {phase.day_start}-{phase.day_end}) ===")

        # Application impacts sectoriels
        impacts_applied = self.apply_sector_shock_impacts(phase)

        # Calcul intensité flux ajustée selon impacts
        # Impact moyen pondéré par nombre d'agents par secteur
        total_agents_by_sector = {sector: len(agents) for sector, agents in self.economic_agents.items()}
        total_agents = sum(total_agents_by_sector.values())

        weighted_impact = sum(
            phase.sector_impacts[sector] * (total_agents_by_sector[sector] / total_agents)
            for sector in phase.sector_impacts.keys()
        )

        # Intensité flux modulée par impact moyen
        base_flow_intensity = 0.70
        adjusted_flow_intensity = base_flow_intensity * weighted_impact

        phase_transactions = []
        phase_feasibility_rates = []
        phase_volumes = []

        # Simulation jours de la phase
        for day in range(phase.day_start, phase.day_end + 1):
            day_date = self.start_time + timedelta(days=day-1)

            # Variation quotidienne légère
            daily_intensity = adjusted_flow_intensity * (0.95 + 0.10 * (day % 2))

            self.logger.info(f"Jour {day} - Intensité ajustée: {daily_intensity:.3f} (base: {base_flow_intensity})")

            # Génération flux inter-sectoriels
            start_time = time.time()
            transaction_ids = self.simulation.create_inter_sectoral_flows_batch(
                flow_intensity=daily_intensity
            )
            creation_time = (time.time() - start_time) * 1000

            # Validation FEASIBILITY échantillon
            sample_size = min(20, len(transaction_ids))
            validation_results = []

            for tx_id in transaction_ids[:sample_size]:
                result = self.simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
                validation_results.append(result.success)

            # Métriques jour
            successful_count = sum(validation_results)
            day_feasibility = successful_count / len(validation_results) if validation_results else 0
            day_volume = Decimal(str(len(transaction_ids) * 750))

            phase_transactions.extend(transaction_ids)
            phase_feasibility_rates.append(day_feasibility)
            phase_volumes.append(day_volume)

            self.logger.info(f"Jour {day}: {len(transaction_ids)} tx, {day_feasibility:.1%} FEASIBILITY")

        # Métriques phase agrégées
        phase_total_tx = len(phase_transactions)
        phase_avg_feasibility = sum(phase_feasibility_rates) / len(phase_feasibility_rates) if phase_feasibility_rates else 0
        phase_total_volume = sum(phase_volumes)

        # Validation objectifs phase
        feasibility_target_met = phase_avg_feasibility >= phase.expected_feasibility * 0.8  # 80% tolérance

        phase_result = {
            'phase': phase,
            'impacts_applied': impacts_applied,
            'transactions_count': phase_total_tx,
            'avg_feasibility_rate': phase_avg_feasibility,
            'total_volume': phase_total_volume,
            'feasibility_target_met': feasibility_target_met,
            'daily_feasibility_rates': phase_feasibility_rates,
            'adjusted_flow_intensity': adjusted_flow_intensity
        }

        self.logger.info(f"Phase {phase.phase_number} terminée: {phase_total_tx} tx, {phase_avg_feasibility:.1%} FEASIBILITY")

        return phase_result

    def validate_shock_resilience(self, phase_results: List[Dict]) -> Tuple[bool, Dict[str, float]]:
        """
        Valide résilience économique au choc pétrolier

        Returns:
            (resilience_validated, resilience_metrics)
        """
        if len(phase_results) < 4:
            return False, {'error': 'Phases incomplètes'}

        # Extraction métriques par phase
        baseline_feasibility = phase_results[0]['avg_feasibility_rate']
        shock_feasibility = phase_results[1]['avg_feasibility_rate']
        propagation_feasibility = phase_results[2]['avg_feasibility_rate']
        adaptation_feasibility = phase_results[3]['avg_feasibility_rate']

        # Calculs résilience
        shock_impact = (baseline_feasibility - shock_feasibility) / baseline_feasibility if baseline_feasibility > 0 else 0
        recovery_rate = (adaptation_feasibility - propagation_feasibility) / (baseline_feasibility - propagation_feasibility) if (baseline_feasibility - propagation_feasibility) > 0 else 0

        # Validation critères
        propagation_validated = propagation_feasibility <= shock_feasibility * 1.1  # Propagation contrôlée
        adaptation_validated = adaptation_feasibility > propagation_feasibility    # Récupération positive
        resilience_target_met = recovery_rate >= self.min_recovery_rate           # Recovery suffisante

        resilience_metrics = {
            'baseline_feasibility': baseline_feasibility,
            'shock_impact_ratio': shock_impact,
            'recovery_rate': recovery_rate,
            'final_vs_baseline_ratio': adaptation_feasibility / baseline_feasibility if baseline_feasibility > 0 else 0,
            'propagation_controlled': propagation_validated,
            'recovery_positive': adaptation_validated,
            'resilience_target_achieved': resilience_target_met
        }

        overall_resilience = propagation_validated and adaptation_validated and resilience_target_met

        return overall_resilience, resilience_metrics

    def run_oil_shock_simulation(self) -> OilShockResults:
        """
        Exécute scénario choc pétrolier complet 7 jours

        Returns:
            Résultats complets avec validation résilience
        """
        self.start_time = datetime.now()
        self.logger.info(f"=== DÉBUT Scénario Choc Pétrolier 7 Jours ===")

        try:
            # Configuration économie choc pétrolier
            total_agents = self.setup_oil_shock_economy()
            self.logger.info(f"Configuration: {total_agents} agents, test résilience énergétique")

            # Simulation par phases
            phase_results = []

            for phase in self.phases:
                phase_result = self.simulate_shock_phase(phase)
                phase_results.append(phase_result)

                # Pause entre phases
                time.sleep(0.3)

            end_time = datetime.now()
            duration_hours = (end_time - self.start_time).total_seconds() / 3600

            # Validation résilience globale
            resilience_validated, resilience_metrics = self.validate_shock_resilience(phase_results)

            # Calcul métriques économiques
            baseline_volume = phase_results[0]['total_volume']
            shock_volume = phase_results[1]['total_volume']
            adaptation_volume = phase_results[3]['total_volume']

            shock_impact_percent = float((baseline_volume - shock_volume) / baseline_volume * 100) if baseline_volume > 0 else 0
            recovery_percent = float((adaptation_volume - shock_volume) / (baseline_volume - shock_volume) * 100) if (baseline_volume - shock_volume) > 0 else 0

            # Résilience par secteur (simulation basée sur impacts appliqués)
            sector_resilience = {}
            for sector in self.economic_agents.keys():
                baseline_impact = self.phases[0].sector_impacts[sector]
                shock_impact = self.phases[1].sector_impacts[sector]
                adaptation_impact = self.phases[3].sector_impacts[sector]

                sector_resilience[sector] = {
                    'baseline': float(baseline_impact),
                    'shock': float(shock_impact),
                    'recovery': float(adaptation_impact),
                    'resilience_score': float((adaptation_impact - shock_impact) / (baseline_impact - shock_impact)) if (baseline_impact - shock_impact) != 0 else 1.0
                }

            # Construction résultats
            results = OilShockResults(
                success=resilience_validated,
                simulation_id=self.simulation.simulation_id,
                start_time=self.start_time,
                end_time=end_time,
                total_duration_hours=duration_hours,

                baseline_feasibility=resilience_metrics['baseline_feasibility'],
                shock_feasibility=phase_results[1]['avg_feasibility_rate'],
                propagation_feasibility=phase_results[2]['avg_feasibility_rate'],
                adaptation_feasibility=phase_results[3]['avg_feasibility_rate'],

                baseline_volume=baseline_volume,
                shock_impact_percent=shock_impact_percent,
                recovery_percent=recovery_percent,

                sector_resilience=sector_resilience,

                propagation_validated=resilience_metrics['propagation_controlled'],
                adaptation_validated=resilience_metrics['recovery_positive'],
                resilience_target_met=resilience_metrics['resilience_target_achieved'],

                phase_results=phase_results
            )

            # Log résultats
            self.logger.info(f"=== RÉSULTATS Choc Pétrolier 7 Jours ===")
            self.logger.info(f"Résilience Globale: {'✅ VALIDÉE' if results.success else '❌ INSUFFISANTE'}")
            self.logger.info(f"Impact Choc: -{shock_impact_percent:.1f}% volume économique")
            self.logger.info(f"Récupération: {recovery_percent:.1f}% (cible: {self.min_recovery_rate:.1%})")
            self.logger.info(f"FEASIBILITY: {results.baseline_feasibility:.1%} → {results.shock_feasibility:.1%} → {results.adaptation_feasibility:.1%}")

            return results

        except Exception as e:
            self.logger.error(f"Erreur scénario choc pétrolier: {e}")

            return OilShockResults(
                success=False,
                simulation_id=self.simulation.simulation_id,
                start_time=self.start_time,
                end_time=datetime.now(),
                total_duration_hours=0,
                baseline_feasibility=0, shock_feasibility=0,
                propagation_feasibility=0, adaptation_feasibility=0,
                baseline_volume=Decimal('0'), shock_impact_percent=0, recovery_percent=0,
                sector_resilience={}, propagation_validated=False,
                adaptation_validated=False, resilience_target_met=False,
                phase_results=[]
            )