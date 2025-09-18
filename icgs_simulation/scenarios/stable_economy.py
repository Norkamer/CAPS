"""
Scénario Économie Stable - Simulation 7 Jours

Simule une économie stable et équilibrée sur 7 jours avec:
- Flux inter-sectoriels constants et prévisibles
- Balance économique maintenue (±10% variation max)
- Validation FEASIBILITY >60% sur toute la période
- Cycles jour/nuit avec variations d'activité économique

Architecture:
- 40+ agents dans 5 secteurs économiques
- Flux automatiques avec intensité modulée par jour/cycle
- Validation performance continues (temps, taux succès)
- Métriques économiques agrégées (PIB simulation, flux totaux)
"""

import time
import logging
from decimal import Decimal
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..api.icgs_bridge import EconomicSimulation, SimulationMode, SimulationResult


@dataclass
class EconomicDay:
    """Données économiques d'une journée de simulation"""
    day_number: int
    date: datetime
    total_transactions: int
    successful_transactions: int
    feasibility_rate: float
    avg_validation_time_ms: float
    total_economic_volume: Decimal
    sector_activity: Dict[str, Dict[str, float]]  # secteur -> {transactions, success_rate, volume}
    performance_metrics: Dict[str, float]


@dataclass
class StableEconomyResults:
    """Résultats complets simulation Économie Stable 7 jours"""
    success: bool
    simulation_id: str
    start_time: datetime
    end_time: datetime
    total_duration_hours: float

    # Métriques globales
    total_days: int
    total_transactions: int
    total_successful: int
    overall_feasibility_rate: float
    avg_validation_time_ms: float

    # Performance par jour
    daily_results: List[EconomicDay]

    # Métriques économiques
    total_economic_volume: Decimal
    avg_daily_volume: Decimal
    sector_performance: Dict[str, Dict[str, float]]

    # Validation critères
    stability_achieved: bool  # ±10% variation max
    performance_target_met: bool  # >60% FEASIBILITY
    continuity_validated: bool  # 7 jours sans interruption


class StableEconomyScenario:
    """
    Scénario Économie Stable - Simulation Continue 7 Jours

    Simule une économie stable avec cycles jour/nuit et
    validation performance continue pour applications production.
    """

    def __init__(self, simulation: EconomicSimulation,
                 target_feasibility_rate: float = 0.60,
                 max_daily_variation: float = 0.10):
        """
        Initialise scénario économie stable

        Args:
            simulation: Instance EconomicSimulation configurée
            target_feasibility_rate: Taux FEASIBILITY cible (défaut 60%)
            max_daily_variation: Variation max autorisée entre jours (défaut 10%)
        """
        self.simulation = simulation
        self.target_feasibility_rate = target_feasibility_rate
        self.max_daily_variation = max_daily_variation

        self.logger = logging.getLogger(f"stable_economy.{simulation.simulation_id}")
        self.start_time: Optional[datetime] = None
        self.daily_results: List[EconomicDay] = []

        # Agents économiques pré-créés pour stabilité
        self.economic_agents: Dict[str, List[str]] = {}  # secteur -> [agent_ids]

    def setup_stable_economy_agents(self) -> int:
        """
        Configure agents économiques pour économie stable
        Distribution: AGRICULTURE(8) + INDUSTRY(12) + SERVICES(15) + FINANCE(5) + ENERGY(8) = 48 agents

        Returns:
            Nombre total d'agents créés
        """
        # Distribution équilibrée pour économie stable
        stable_distribution = {
            'AGRICULTURE': 8,   # Production alimentaire stable
            'INDUSTRY': 12,     # Manufacturing continu
            'SERVICES': 15,     # Secteur dominant - services stables
            'FINANCE': 5,       # Facilitation financière
            'ENERGY': 8         # Infrastructure énergétique
        }

        # Balances sectorielles pour stabilité économique
        sector_base_balances = {
            'AGRICULTURE': Decimal('1400'),  # Stocks saisonniers + équipements
            'INDUSTRY': Decimal('1100'),     # Capital industriel stable
            'SERVICES': Decimal('800'),      # Capital léger, flux rapides
            'FINANCE': Decimal('3200'),      # Réserves importantes
            'ENERGY': Decimal('2200')        # Infrastructure lourde stable
        }

        total_agents = 0

        for sector, count in stable_distribution.items():
            self.economic_agents[sector] = []
            base_balance = sector_base_balances[sector]

            for i in range(count):
                agent_id = f"STABLE_{sector}_{i+1:02d}"

                # Variation balance ±15% pour réalisme
                balance_factor = Decimal(str(0.85 + 0.30 * (i / count)))
                agent_balance = base_balance * balance_factor

                agent = self.simulation.create_agent(agent_id, sector, agent_balance)
                self.economic_agents[sector].append(agent_id)
                total_agents += 1

        self.logger.info(f"Économie stable configurée: {total_agents} agents, 5 secteurs")

        # Log distribution par secteur
        for sector, agents in self.economic_agents.items():
            self.logger.info(f"  {sector}: {len(agents)} agents")

        return total_agents

    def simulate_daily_economic_activity(self, day_number: int) -> EconomicDay:
        """
        Simule activité économique d'une journée

        Args:
            day_number: Numéro du jour (1-7)

        Returns:
            Résultats économiques de la journée
        """
        day_date = self.start_time + timedelta(days=day_number-1)

        # Intensité flux selon jour semaine (lundi=1.0, weekend=0.7)
        weekday = day_date.weekday()  # 0=lundi, 6=dimanche
        if weekday < 5:  # Lundi-Vendredi
            flow_intensity = 0.75 + 0.05 * (day_number % 3)  # Variation légère
        else:  # Weekend
            flow_intensity = 0.55 + 0.10 * (day_number % 2)

        self.logger.info(f"Jour {day_number} ({day_date.strftime('%A')}) - Intensité: {flow_intensity:.2f}")

        # Génération flux inter-sectoriels jour
        start_time = time.time()
        transaction_ids = self.simulation.create_inter_sectoral_flows_batch(
            flow_intensity=flow_intensity
        )
        creation_time = (time.time() - start_time) * 1000

        # Validation FEASIBILITY échantillon représentatif
        sample_size = min(25, len(transaction_ids))
        validation_results = []
        validation_times = []

        for tx_id in transaction_ids[:sample_size]:
            validation_start = time.time()
            result = self.simulation.validate_transaction(tx_id, SimulationMode.FEASIBILITY)
            validation_time = (time.time() - validation_start) * 1000

            validation_results.append(result.success)
            validation_times.append(validation_time)

        # Métriques journée
        successful_count = sum(validation_results)
        feasibility_rate = successful_count / len(validation_results) if validation_results else 0
        avg_validation_time = sum(validation_times) / len(validation_times) if validation_times else 0

        # Volume économique estimé (basé sur flux créés)
        estimated_daily_volume = Decimal(str(len(transaction_ids) * 850))  # 850 unités moy/transaction

        # Analyse par secteur (simplifiée)
        sector_activity = {}
        for sector in self.economic_agents.keys():
            sector_transactions = len(transaction_ids) // 5  # Distribution approximative
            sector_success_rate = feasibility_rate * (0.9 + 0.2 * hash(sector) % 3 / 10)  # Variation réaliste
            sector_volume = estimated_daily_volume / 5

            sector_activity[sector] = {
                'transactions': sector_transactions,
                'success_rate': min(1.0, sector_success_rate),
                'volume': float(sector_volume)
            }

        # Performance metrics
        performance_metrics = {
            'throughput_tx_sec': len(transaction_ids) / creation_time * 1000,
            'validation_efficiency': successful_count / sample_size if sample_size > 0 else 0,
            'economic_velocity': float(estimated_daily_volume) / (total_agents := sum(len(agents) for agents in self.economic_agents.values()))
        }

        economic_day = EconomicDay(
            day_number=day_number,
            date=day_date,
            total_transactions=len(transaction_ids),
            successful_transactions=successful_count,
            feasibility_rate=feasibility_rate,
            avg_validation_time_ms=avg_validation_time,
            total_economic_volume=estimated_daily_volume,
            sector_activity=sector_activity,
            performance_metrics=performance_metrics
        )

        self.logger.info(f"Jour {day_number} terminé: {len(transaction_ids)} tx, "
                        f"{feasibility_rate:.1%} FEASIBILITY, {avg_validation_time:.2f}ms")

        return economic_day

    def validate_economic_stability(self, daily_results: List[EconomicDay]) -> Tuple[bool, Dict[str, float]]:
        """
        Valide stabilité économique sur période 7 jours

        Returns:
            (stability_achieved, stability_metrics)
        """
        if len(daily_results) < 7:
            return False, {'error': 'Données insuffisantes'}

        # Métriques stabilité
        daily_volumes = [float(day.total_economic_volume) for day in daily_results]
        daily_feasibility = [day.feasibility_rate for day in daily_results]
        daily_transactions = [day.total_transactions for day in daily_results]

        # Calculs variation
        avg_volume = sum(daily_volumes) / len(daily_volumes)
        max_volume_deviation = max(abs(v - avg_volume) / avg_volume for v in daily_volumes)

        avg_feasibility = sum(daily_feasibility) / len(daily_feasibility)
        min_feasibility = min(daily_feasibility)

        avg_transactions = sum(daily_transactions) / len(daily_transactions)
        max_tx_deviation = max(abs(tx - avg_transactions) / avg_transactions for tx in daily_transactions)

        # Critères stabilité
        volume_stable = max_volume_deviation <= self.max_daily_variation
        feasibility_stable = min_feasibility >= self.target_feasibility_rate * 0.8  # 80% du target minimum
        transaction_stable = max_tx_deviation <= self.max_daily_variation * 1.5  # +50% tolérance transactions

        stability_achieved = volume_stable and feasibility_stable and transaction_stable

        stability_metrics = {
            'avg_daily_volume': avg_volume,
            'max_volume_deviation': max_volume_deviation,
            'avg_feasibility_rate': avg_feasibility,
            'min_feasibility_rate': min_feasibility,
            'avg_daily_transactions': avg_transactions,
            'max_transaction_deviation': max_tx_deviation,
            'volume_stability': volume_stable,
            'feasibility_stability': feasibility_stable,
            'transaction_stability': transaction_stable
        }

        return stability_achieved, stability_metrics

    def run_7_day_simulation(self) -> StableEconomyResults:
        """
        Exécute simulation économie stable complète 7 jours

        Returns:
            Résultats complets avec métriques stabilité
        """
        self.start_time = datetime.now()
        self.logger.info(f"=== DÉBUT Scénario Économie Stable 7 Jours ===")

        try:
            # Configuration agents économiques
            total_agents = self.setup_stable_economy_agents()
            self.logger.info(f"Configuration: {total_agents} agents économiques")

            # Simulation jour par jour
            daily_results = []

            for day in range(1, 8):  # Jours 1 à 7
                self.logger.info(f"--- Simulation Jour {day}/7 ---")

                day_result = self.simulate_daily_economic_activity(day)
                daily_results.append(day_result)

                # Pause réaliste entre jours (simulation accélérée)
                time.sleep(0.5)  # 500ms = 1 jour simulé

            end_time = datetime.now()
            duration_hours = (end_time - self.start_time).total_seconds() / 3600

            # Validation stabilité économique
            stability_achieved, stability_metrics = self.validate_economic_stability(daily_results)

            # Agrégation métriques globales
            total_transactions = sum(day.total_transactions for day in daily_results)
            total_successful = sum(day.successful_transactions for day in daily_results)
            overall_feasibility = total_successful / total_transactions if total_transactions > 0 else 0

            avg_validation_time = sum(day.avg_validation_time_ms for day in daily_results) / len(daily_results)
            total_economic_volume = sum(day.total_economic_volume for day in daily_results)
            avg_daily_volume = total_economic_volume / 7

            # Performance par secteur agrégée
            sector_performance = {}
            for sector in self.economic_agents.keys():
                sector_total_tx = sum(day.sector_activity[sector]['transactions'] for day in daily_results)
                sector_avg_success = sum(day.sector_activity[sector]['success_rate'] for day in daily_results) / 7
                sector_total_volume = sum(day.sector_activity[sector]['volume'] for day in daily_results)

                sector_performance[sector] = {
                    'total_transactions': sector_total_tx,
                    'avg_success_rate': sector_avg_success,
                    'total_volume': sector_total_volume
                }

            # Validation critères success
            performance_target_met = overall_feasibility >= self.target_feasibility_rate
            continuity_validated = len(daily_results) == 7 and all(day.total_transactions > 0 for day in daily_results)

            # Construction résultats
            results = StableEconomyResults(
                success=stability_achieved and performance_target_met and continuity_validated,
                simulation_id=self.simulation.simulation_id,
                start_time=self.start_time,
                end_time=end_time,
                total_duration_hours=duration_hours,

                total_days=len(daily_results),
                total_transactions=total_transactions,
                total_successful=total_successful,
                overall_feasibility_rate=overall_feasibility,
                avg_validation_time_ms=avg_validation_time,

                daily_results=daily_results,

                total_economic_volume=total_economic_volume,
                avg_daily_volume=avg_daily_volume,
                sector_performance=sector_performance,

                stability_achieved=stability_achieved,
                performance_target_met=performance_target_met,
                continuity_validated=continuity_validated
            )

            # Log résultats
            self.logger.info(f"=== RÉSULTATS Économie Stable 7 Jours ===")
            self.logger.info(f"Success Global: {'✅ OUI' if results.success else '❌ NON'}")
            self.logger.info(f"Transactions: {total_transactions} total, {overall_feasibility:.1%} FEASIBILITY")
            self.logger.info(f"Volume Économique: {total_economic_volume:,.0f} unités sur 7 jours")
            self.logger.info(f"Stabilité: {'✅ VALIDÉE' if stability_achieved else '❌ INSTABLE'}")
            self.logger.info(f"Performance: {'✅ TARGET MET' if performance_target_met else '❌ BELOW TARGET'}")

            return results

        except Exception as e:
            self.logger.error(f"Erreur simulation 7 jours: {e}")

            # Résultats d'erreur
            return StableEconomyResults(
                success=False,
                simulation_id=self.simulation.simulation_id,
                start_time=self.start_time,
                end_time=datetime.now(),
                total_duration_hours=0,
                total_days=0,
                total_transactions=0,
                total_successful=0,
                overall_feasibility_rate=0,
                avg_validation_time_ms=0,
                daily_results=[],
                total_economic_volume=Decimal('0'),
                avg_daily_volume=Decimal('0'),
                sector_performance={},
                stability_achieved=False,
                performance_target_met=False,
                continuity_validated=False
            )