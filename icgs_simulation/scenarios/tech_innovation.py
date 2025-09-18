"""
Scénario Innovation Tech - INDUSTRY +50%

Simule révolution technologique avec croissance massive du secteur INDUSTRY et
réallocation économique automatique:
- INDUSTRY: Croissance explosive +50% (innovation disruptive)
- Attraction: SERVICES → INDUSTRY (+15%), FINANCE → INDUSTRY (+20%)
- AGRICULTURE: Modernisation tech (+10%)
- ENERGY: Demande accrue (+25% pour alimenter croissance)
- Validation adaptation positive économie

Architecture:
- Phase 1: Économie baseline (jours 1-2)
- Phase 2: Innovation breakthrough (+50% INDUSTRY, jour 3)
- Phase 3: Réallocation économique (jours 4-5, flux migration)
- Phase 4: Nouveau équilibre (jours 6-7, croissance soutenue)
- Métriques: Croissance, innovation diffusion, équilibre final
"""

import time
import logging
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..api.icgs_bridge import EconomicSimulation, SimulationMode, SimulationResult


@dataclass
class TechInnovationPhase:
    """Phase du scénario innovation technologique"""
    phase_number: int
    phase_name: str
    day_start: int
    day_end: int
    sector_impacts: Dict[str, float]  # secteur → multiplicateur (+50% = 1.5)
    innovation_intensity: float
    expected_feasibility: float
    description: str


@dataclass
class TechInnovationResults:
    """Résultats scénario Innovation Tech"""
    success: bool
    simulation_id: str
    start_time: datetime
    end_time: datetime
    total_duration_hours: float

    # Métriques innovation
    baseline_feasibility: float
    innovation_feasibility: float
    reallocation_feasibility: float
    equilibrium_feasibility: float

    # Impact économique croissance
    baseline_volume: Decimal
    growth_impact_percent: float
    final_growth_ratio: float

    # Innovation diffusion
    sector_innovation_adoption: Dict[str, Dict[str, float]]  # secteur → metrics

    # Validation adaptation
    growth_sustained: bool
    reallocation_successful: bool
    equilibrium_target_met: bool

    # Détails phases
    phase_results: List[Dict[str, any]]


class TechInnovationScenario:
    """
    Scénario Innovation Tech - Croissance INDUSTRY +50%

    Teste capacité économie à intégrer innovation disruptive
    avec réallocation ressources et croissance soutenue.
    """

    def __init__(self, simulation: EconomicSimulation,
                 industry_growth: float = 0.50,
                 min_equilibrium_growth: float = 0.25):
        """
        Initialise scénario innovation technologique

        Args:
            simulation: Instance EconomicSimulation configurée
            industry_growth: Croissance INDUSTRY (défaut +50%)
            min_equilibrium_growth: Croissance minimum équilibre final (défaut +25%)
        """
        self.simulation = simulation
        self.industry_growth = industry_growth
        self.min_equilibrium_growth = min_equilibrium_growth

        self.logger = logging.getLogger(f"tech_innovation.{simulation.simulation_id}")
        self.start_time: Optional[datetime] = None

        # Phases innovation
        self.phases = self._define_innovation_phases()

        # Agents économiques innovation
        self.economic_agents: Dict[str, List[str]] = {}
        self.original_balances: Dict[str, Decimal] = {}

    def _define_innovation_phases(self) -> List[TechInnovationPhase]:
        """Définit phases scénario innovation technologique"""
        growth_multiplier = 1.0 + self.industry_growth  # +50% = 1.5

        return [
            TechInnovationPhase(
                phase_number=1,
                phase_name="Baseline Économique",
                day_start=1, day_end=2,
                sector_impacts={
                    'AGRICULTURE': 1.0,
                    'INDUSTRY': 1.0,
                    'SERVICES': 1.0,
                    'FINANCE': 1.0,
                    'ENERGY': 1.0
                },
                innovation_intensity=0.0,
                expected_feasibility=0.65,
                description="État économique initial"
            ),
            TechInnovationPhase(
                phase_number=2,
                phase_name="Innovation Breakthrough",
                day_start=3, day_end=3,
                sector_impacts={
                    'AGRICULTURE': 1.05,     # Modernisation tech légère
                    'INDUSTRY': growth_multiplier,  # +50% growth disruptif
                    'SERVICES': 1.02,        # Légère croissance induite
                    'FINANCE': 1.08,         # Financement innovation
                    'ENERGY': 1.20          # Demande accrue (+20%)
                },
                innovation_intensity=1.0,
                expected_feasibility=0.70,
                description="Breakthrough tech INDUSTRY"
            ),
            TechInnovationPhase(
                phase_number=3,
                phase_name="Réallocation Économique",
                day_start=4, day_end=5,
                sector_impacts={
                    'AGRICULTURE': 1.08,     # Tech adoption progressive
                    'INDUSTRY': growth_multiplier * 1.1,  # Croissance soutenue +60%
                    'SERVICES': 1.12,        # Migration vers tech services
                    'FINANCE': 1.15,         # Capital réallocation active
                    'ENERGY': 1.25          # Infrastructure expansion
                },
                innovation_intensity=0.8,
                expected_feasibility=0.75,
                description="Migration flux vers secteurs tech"
            ),
            TechInnovationPhase(
                phase_number=4,
                phase_name="Nouvel Équilibre",
                day_start=6, day_end=7,
                sector_impacts={
                    'AGRICULTURE': 1.12,     # Tech agricole adoptée
                    'INDUSTRY': growth_multiplier * 1.2,  # Croissance mature +70%
                    'SERVICES': 1.18,        # Services tech développés
                    'FINANCE': 1.12,         # Financement normalisé
                    'ENERGY': 1.30          # Nouvelle capacité (+30%)
                },
                innovation_intensity=0.6,
                expected_feasibility=0.80,
                description="Économie tech mature équilibrée"
            )
        ]

    def setup_tech_innovation_economy(self) -> int:
        """
        Configure économie pour scénario innovation technologique
        Distribution compatible mode 65_agents: AGRICULTURE(5) + INDUSTRY(12) + SERVICES(10) + FINANCE(5) + ENERGY(6) = 38 agents
        """
        # Distribution réduite compatible capacités
        innovation_distribution = {
            'AGRICULTURE': 5,   # Base alimentaire + tech agricole
            'INDUSTRY': 12,     # Secteur innovation focus
            'SERVICES': 10,     # Support innovation + migration tech
            'FINANCE': 5,       # Capital innovation + fintech
            'ENERGY': 6         # Infrastructure énergie innovation
        }

        # Balances optimisées croissance
        sector_balances = {
            'AGRICULTURE': Decimal('1200'),  # Modernisation préparée
            'INDUSTRY': Decimal('1800'),     # Capital innovation prêt
            'SERVICES': Decimal('1100'),     # Flexibilité adaptation
            'FINANCE': Decimal('3500'),      # Capital venture important
            'ENERGY': Decimal('2500')        # Infrastructure expansion
        }

        total_agents = 0

        for sector, count in innovation_distribution.items():
            self.economic_agents[sector] = []
            base_balance = sector_balances[sector]

            for i in range(count):
                agent_id = f"TECH_{sector}_{i+1:02d}"

                # Variation balance ±25% pour diversité
                balance_factor = Decimal(str(0.75 + 0.50 * (i / count)))
                agent_balance = base_balance * balance_factor

                agent = self.simulation.create_agent(agent_id, sector, agent_balance)
                self.economic_agents[sector].append(agent_id)
                self.original_balances[agent_id] = agent_balance
                total_agents += 1

        self.logger.info(f"Économie innovation tech configurée: {total_agents} agents, focus INDUSTRY")

        # Log distribution
        for sector, agents in self.economic_agents.items():
            self.logger.info(f"  {sector}: {len(agents)} agents, balance base {sector_balances[sector]}")

        return total_agents

    def apply_innovation_impacts(self, phase: TechInnovationPhase) -> Dict[str, float]:
        """
        Applique impacts innovation selon phase

        Returns:
            Statistiques impacts par secteur
        """
        impacts_applied = {}

        self.logger.info(f"Application innovation Phase {phase.phase_number}: {phase.phase_name}")
        self.logger.info(f"Innovation intensity: {phase.innovation_intensity:.1%}")

        for sector, impact_multiplier in phase.sector_impacts.items():
            impact_percent = (impact_multiplier - 1.0) * 100
            impacts_applied[sector] = impact_percent

            if impact_percent >= 10:
                self.logger.info(f"  {sector}: +{impact_percent:.1f}% (innovation majeure)")
            elif impact_percent > 0:
                self.logger.info(f"  {sector}: +{impact_percent:.1f}% (croissance)")
            else:
                self.logger.info(f"  {sector}: {impact_percent:+.1f}%")

        return impacts_applied

    def simulate_innovation_phase(self, phase: TechInnovationPhase) -> Dict[str, any]:
        """
        Simule phase innovation technologique

        Returns:
            Résultats détaillés phase
        """
        self.logger.info(f"=== Phase {phase.phase_number}: {phase.phase_name} (Jours {phase.day_start}-{phase.day_end}) ===")

        # Application impacts innovation
        impacts_applied = self.apply_innovation_impacts(phase)

        # Intensité flux modulée par innovation et croissance
        base_intensity = 0.72
        innovation_boost = 1.0 + (phase.innovation_intensity * 0.4)  # Boost jusqu'à +40%

        # Impact INDUSTRY sur flux global
        industry_impact = phase.sector_impacts.get('INDUSTRY', 1.0)
        industry_agents_ratio = len(self.economic_agents['INDUSTRY']) / sum(len(agents) for agents in self.economic_agents.values())

        # Intensité ajustée par innovation et dominance INDUSTRY
        adjusted_intensity = base_intensity * innovation_boost * (1.0 + (industry_impact - 1.0) * industry_agents_ratio)

        phase_transactions = []
        phase_feasibility_rates = []
        phase_volumes = []

        # Simulation jours phase
        for day in range(phase.day_start, phase.day_end + 1):
            day_date = self.start_time + timedelta(days=day-1)

            # Variation quotidienne innovation
            daily_innovation_factor = 0.95 + 0.10 * phase.innovation_intensity * (day % 2)
            daily_intensity = adjusted_intensity * daily_innovation_factor

            self.logger.info(f"Jour {day} - Intensité tech: {daily_intensity:.3f} (base: {base_intensity}, innovation: {innovation_boost:.2f})")

            # Génération flux innovation
            start_time = time.time()
            transaction_ids = self.simulation.create_inter_sectoral_flows_batch(
                flow_intensity=min(daily_intensity, 1.0)  # Cap à 1.0
            )
            creation_time = (time.time() - start_time) * 1000

            # Validation échantillon
            sample_size = min(25, len(transaction_ids))
            validation_results = []

            for tx_id in transaction_ids[:sample_size]:
                result = self.simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
                validation_results.append(result.success)

            # Métriques jour
            successful_count = sum(validation_results)
            day_feasibility = successful_count / len(validation_results) if validation_results else 0
            day_volume = Decimal(str(len(transaction_ids) * 950))  # Volume accru innovation

            phase_transactions.extend(transaction_ids)
            phase_feasibility_rates.append(day_feasibility)
            phase_volumes.append(day_volume)

            self.logger.info(f"Jour {day}: {len(transaction_ids)} tx, {day_feasibility:.1%} FEASIBILITY, innovation active")

        # Métriques phase agrégées
        phase_total_tx = len(phase_transactions)
        phase_avg_feasibility = sum(phase_feasibility_rates) / len(phase_feasibility_rates) if phase_feasibility_rates else 0
        phase_total_volume = sum(phase_volumes)

        # Validation objectifs innovation
        feasibility_target_met = phase_avg_feasibility >= phase.expected_feasibility * 0.85  # 85% tolérance

        # Métriques adoption innovation par secteur (simulées)
        sector_adoption = {}
        for sector in self.economic_agents.keys():
            sector_impact = phase.sector_impacts[sector]
            adoption_rate = min(1.0, phase.innovation_intensity * sector_impact * 0.8)

            sector_adoption[sector] = {
                'adoption_rate': adoption_rate,
                'growth_factor': sector_impact,
                'innovation_readiness': adoption_rate * (1.0 + len(self.economic_agents[sector]) * 0.02)
            }

        phase_result = {
            'phase': phase,
            'impacts_applied': impacts_applied,
            'transactions_count': phase_total_tx,
            'avg_feasibility_rate': phase_avg_feasibility,
            'total_volume': phase_total_volume,
            'feasibility_target_met': feasibility_target_met,
            'sector_adoption': sector_adoption,
            'innovation_intensity_used': adjusted_intensity,
            'daily_feasibility_rates': phase_feasibility_rates
        }

        self.logger.info(f"Phase {phase.phase_number} terminée: {phase_total_tx} tx, {phase_avg_feasibility:.1%} FEASIBILITY, innovation diffusée")

        return phase_result

    def validate_innovation_success(self, phase_results: List[Dict]) -> Tuple[bool, Dict[str, float]]:
        """
        Valide succès innovation technologique

        Returns:
            (innovation_success, innovation_metrics)
        """
        if len(phase_results) < 4:
            return False, {'error': 'Phases incomplètes'}

        # Extraction métriques par phase
        baseline_feasibility = phase_results[0]['avg_feasibility_rate']
        innovation_feasibility = phase_results[1]['avg_feasibility_rate']
        reallocation_feasibility = phase_results[2]['avg_feasibility_rate']
        equilibrium_feasibility = phase_results[3]['avg_feasibility_rate']

        # Calculs innovation
        innovation_boost = (innovation_feasibility - baseline_feasibility) / baseline_feasibility if baseline_feasibility > 0 else 0
        sustained_growth = (equilibrium_feasibility - baseline_feasibility) / baseline_feasibility if baseline_feasibility > 0 else 0

        # Validation critères innovation
        growth_sustained = sustained_growth >= self.min_equilibrium_growth  # Croissance soutenue 25%+
        reallocation_successful = reallocation_feasibility > baseline_feasibility  # Adaptation positive
        equilibrium_target_met = equilibrium_feasibility >= baseline_feasibility * 1.15  # +15% final minimum

        innovation_metrics = {
            'baseline_feasibility': baseline_feasibility,
            'innovation_boost_ratio': innovation_boost,
            'sustained_growth_ratio': sustained_growth,
            'final_vs_baseline_ratio': equilibrium_feasibility / baseline_feasibility if baseline_feasibility > 0 else 0,
            'growth_trajectory_positive': equilibrium_feasibility > innovation_feasibility,
            'reallocation_adaptation_successful': reallocation_successful,
            'equilibrium_growth_target_achieved': equilibrium_target_met
        }

        overall_success = growth_sustained and reallocation_successful and equilibrium_target_met

        return overall_success, innovation_metrics

    def run_tech_innovation_simulation(self) -> TechInnovationResults:
        """
        Exécute scénario innovation tech complet

        Returns:
            Résultats complets avec validation croissance
        """
        self.start_time = datetime.now()
        self.logger.info(f"=== DÉBUT Scénario Innovation Tech (+{self.industry_growth:.0%}) ===")

        try:
            # Configuration économie innovation
            total_agents = self.setup_tech_innovation_economy()
            self.logger.info(f"Configuration: {total_agents} agents, focus innovation INDUSTRY")

            # Simulation par phases innovation
            phase_results = []

            for phase in self.phases:
                phase_result = self.simulate_innovation_phase(phase)
                phase_results.append(phase_result)

                # Pause inter-phases
                time.sleep(0.2)

            end_time = datetime.now()
            duration_hours = (end_time - self.start_time).total_seconds() / 3600

            # Validation innovation globale
            innovation_success, innovation_metrics = self.validate_innovation_success(phase_results)

            # Métriques économiques croissance
            baseline_volume = phase_results[0]['total_volume']
            innovation_volume = phase_results[1]['total_volume']
            equilibrium_volume = phase_results[3]['total_volume']

            growth_impact_percent = float((innovation_volume - baseline_volume) / baseline_volume * 100) if baseline_volume > 0 else 0
            final_growth_ratio = float(equilibrium_volume / baseline_volume) if baseline_volume > 0 else 1.0

            # Innovation adoption par secteur
            sector_innovation_adoption = {}
            for sector in self.economic_agents.keys():
                # Agrégation adoption sur toutes phases
                total_adoption = sum(phase_result['sector_adoption'][sector]['adoption_rate'] for phase_result in phase_results) / len(phase_results)
                final_growth = phase_results[-1]['sector_adoption'][sector]['growth_factor']
                readiness = phase_results[-1]['sector_adoption'][sector]['innovation_readiness']

                sector_innovation_adoption[sector] = {
                    'avg_adoption_rate': total_adoption,
                    'final_growth_factor': final_growth,
                    'innovation_readiness': readiness,
                    'innovation_score': total_adoption * final_growth * 0.5
                }

            # Construction résultats
            results = TechInnovationResults(
                success=innovation_success,
                simulation_id=self.simulation.simulation_id,
                start_time=self.start_time,
                end_time=end_time,
                total_duration_hours=duration_hours,

                baseline_feasibility=innovation_metrics['baseline_feasibility'],
                innovation_feasibility=phase_results[1]['avg_feasibility_rate'],
                reallocation_feasibility=phase_results[2]['avg_feasibility_rate'],
                equilibrium_feasibility=phase_results[3]['avg_feasibility_rate'],

                baseline_volume=baseline_volume,
                growth_impact_percent=growth_impact_percent,
                final_growth_ratio=final_growth_ratio,

                sector_innovation_adoption=sector_innovation_adoption,

                growth_sustained=innovation_metrics['equilibrium_growth_target_achieved'],
                reallocation_successful=innovation_metrics['reallocation_adaptation_successful'],
                equilibrium_target_met=innovation_metrics['equilibrium_growth_target_achieved'],

                phase_results=phase_results
            )

            # Log résultats innovation
            self.logger.info(f"=== RÉSULTATS Innovation Tech ===")
            self.logger.info(f"Innovation Success: {'✅ VALIDÉE' if results.success else '❌ INSUFFISANTE'}")
            self.logger.info(f"Croissance Impact: +{growth_impact_percent:.1f}% volume économique")
            self.logger.info(f"Croissance Finale: {final_growth_ratio:.2f}x (cible: {1 + self.min_equilibrium_growth:.2f}x)")
            self.logger.info(f"FEASIBILITY: {results.baseline_feasibility:.1%} → {results.equilibrium_feasibility:.1%}")

            return results

        except Exception as e:
            self.logger.error(f"Erreur scénario innovation tech: {e}")

            return TechInnovationResults(
                success=False,
                simulation_id=self.simulation.simulation_id,
                start_time=self.start_time,
                end_time=datetime.now(),
                total_duration_hours=0,
                baseline_feasibility=0, innovation_feasibility=0,
                reallocation_feasibility=0, equilibrium_feasibility=0,
                baseline_volume=Decimal('0'), growth_impact_percent=0, final_growth_ratio=1.0,
                sector_innovation_adoption={}, growth_sustained=False,
                reallocation_successful=False, equilibrium_target_met=False,
                phase_results=[]
            )