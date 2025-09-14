#!/usr/bin/env python3
"""
CAPS Phase 0 Semaines 3-4: Multi-Objective Optimization
Economic optimization with multiple conflicting objectives
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal, getcontext
import math

# Configuration précision économique
getcontext().prec = 50


class ObjectiveType(Enum):
    """Types d'objectifs d'optimisation"""
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


@dataclass
class Objective:
    """Objectif d'optimisation individuel"""
    name: str
    function: Callable[[Dict], Decimal]
    objective_type: ObjectiveType
    weight: Decimal = Decimal('1.0')
    constraint_bounds: Optional[Tuple[Decimal, Decimal]] = None


@dataclass
class Solution:
    """Solution candidate multi-objectifs"""
    variables: Dict[str, Decimal]
    objective_values: Dict[str, Decimal]
    fitness_score: Decimal
    pareto_rank: int = 0
    crowding_distance: Decimal = Decimal('0')
    is_feasible: bool = True
    constraint_violations: List[str] = None

    def __post_init__(self):
        if self.constraint_violations is None:
            self.constraint_violations = []


class ParetoFrontier:
    """Gestion frontière de Pareto pour solutions non-dominées"""

    def __init__(self):
        self.solutions: List[Solution] = []
        self.dominated_solutions: List[Solution] = []

    def add_solution(self, solution: Solution) -> bool:
        """Ajoute solution et met à jour frontière de Pareto"""
        is_pareto_optimal = True
        solutions_to_remove = []

        for existing in self.solutions:
            dominance = self._check_dominance(solution, existing)

            if dominance == 1:  # solution dominée par existing
                is_pareto_optimal = False
                self.dominated_solutions.append(solution)
                return False

            elif dominance == -1:  # solution domine existing
                solutions_to_remove.append(existing)

        # Retirer solutions dominées
        for dominated in solutions_to_remove:
            self.solutions.remove(dominated)
            self.dominated_solutions.append(dominated)

        if is_pareto_optimal:
            solution.pareto_rank = 1
            self.solutions.append(solution)

        return is_pareto_optimal

    def _check_dominance(self, sol1: Solution, sol2: Solution) -> int:
        """
        Compare deux solutions selon relation de dominance
        Returns: -1 si sol1 domine sol2, 1 si sol2 domine sol1, 0 si non-comparables
        """
        sol1_better = 0
        sol2_better = 0

        for obj_name, val1 in sol1.objective_values.items():
            val2 = sol2.objective_values.get(obj_name)
            if val2 is None:
                continue

            if val1 > val2:
                sol1_better += 1
            elif val1 < val2:
                sol2_better += 1

        if sol1_better > 0 and sol2_better == 0:
            return -1  # sol1 domine
        elif sol2_better > 0 and sol1_better == 0:
            return 1   # sol2 domine
        else:
            return 0   # non-comparable

    def calculate_crowding_distance(self):
        """Calcule distance de crowding pour diversité"""
        if len(self.solutions) <= 2:
            for sol in self.solutions:
                sol.crowding_distance = Decimal('inf')
            return

        # Reset distances
        for sol in self.solutions:
            sol.crowding_distance = Decimal('0')

        # Pour chaque objectif
        objective_names = list(self.solutions[0].objective_values.keys())

        for obj_name in objective_names:
            # Trier par cet objectif
            sorted_solutions = sorted(
                self.solutions,
                key=lambda s: float(s.objective_values[obj_name])
            )

            # Bornes infinies pour extrêmes
            sorted_solutions[0].crowding_distance = Decimal('inf')
            sorted_solutions[-1].crowding_distance = Decimal('inf')

            # Calculer distance pour solutions intermédiaires
            obj_range = (
                float(sorted_solutions[-1].objective_values[obj_name]) -
                float(sorted_solutions[0].objective_values[obj_name])
            )

            if obj_range > 0:
                for i in range(1, len(sorted_solutions) - 1):
                    distance = (
                        float(sorted_solutions[i+1].objective_values[obj_name]) -
                        float(sorted_solutions[i-1].objective_values[obj_name])
                    ) / obj_range

                    sorted_solutions[i].crowding_distance += Decimal(str(distance))

    def get_best_solutions(self, count: int = 10) -> List[Solution]:
        """Retourne les meilleures solutions selon Pareto et crowding"""
        self.calculate_crowding_distance()

        # Trier par rang Pareto puis distance crowding
        sorted_solutions = sorted(
            self.solutions,
            key=lambda s: (s.pareto_rank, -float(s.crowding_distance))
        )

        return sorted_solutions[:count]


class MultiObjectiveOptimizer:
    """Optimiseur multi-objectifs avec algorithme NSGA-II adapté"""

    def __init__(self, objectives: List[Objective], constraints: Optional[List[Callable]] = None):
        self.objectives = objectives
        self.constraints = constraints or []
        self.pareto_frontier = ParetoFrontier()
        self.population: List[Solution] = []
        self.generation_history: List[Dict[str, Any]] = []

    def create_economic_objectives(self) -> List[Objective]:
        """Crée objectifs économiques typiques pour CAPS"""

        def profit_objective(variables: Dict[str, Decimal]) -> Decimal:
            """Maximiser profit total"""
            revenue = variables.get('revenue', Decimal('0'))
            costs = variables.get('costs', Decimal('0'))
            return revenue - costs

        def risk_objective(variables: Dict[str, Decimal]) -> Decimal:
            """Minimiser risque (volatilité)"""
            volatility = variables.get('volatility', Decimal('0'))
            exposure = variables.get('exposure', Decimal('1'))
            return volatility * exposure

        def liquidity_objective(variables: Dict[str, Decimal]) -> Decimal:
            """Maximiser liquidité"""
            cash_flow = variables.get('cash_flow', Decimal('0'))
            working_capital = variables.get('working_capital', Decimal('0'))
            return cash_flow + working_capital * Decimal('0.1')

        def sustainability_objective(variables: Dict[str, Decimal]) -> Decimal:
            """Maximiser score durabilité"""
            esg_score = variables.get('esg_score', Decimal('0'))
            carbon_efficiency = variables.get('carbon_efficiency', Decimal('1'))
            return esg_score * carbon_efficiency

        def efficiency_objective(variables: Dict[str, Decimal]) -> Decimal:
            """Maximiser efficacité opérationnelle"""
            output = variables.get('output', Decimal('1'))
            input_resources = variables.get('input_resources', Decimal('1'))
            return output / max(input_resources, Decimal('0.001'))

        return [
            Objective("profit", profit_objective, ObjectiveType.MAXIMIZE, Decimal('1.0')),
            Objective("risk", risk_objective, ObjectiveType.MINIMIZE, Decimal('1.2')),
            Objective("liquidity", liquidity_objective, ObjectiveType.MAXIMIZE, Decimal('0.8')),
            Objective("sustainability", sustainability_objective, ObjectiveType.MAXIMIZE, Decimal('0.6')),
            Objective("efficiency", efficiency_objective, ObjectiveType.MAXIMIZE, Decimal('1.1'))
        ]

    def evaluate_solution(self, variables: Dict[str, Decimal]) -> Solution:
        """Évalue une solution selon tous les objectifs"""
        objective_values = {}
        total_fitness = Decimal('0')

        # Calculer valeur pour chaque objectif
        for objective in self.objectives:
            try:
                value = objective.function(variables)
                objective_values[objective.name] = value

                # Contribution au fitness (normalisée par type et poids)
                if objective.objective_type == ObjectiveType.MAXIMIZE:
                    weighted_value = value * objective.weight
                else:
                    weighted_value = -value * objective.weight

                total_fitness += weighted_value

            except Exception as e:
                # Objectif non calculable - solution infaisable
                return Solution(
                    variables=variables,
                    objective_values={},
                    fitness_score=Decimal('-inf'),
                    is_feasible=False,
                    constraint_violations=[f"Objective {objective.name}: {str(e)}"]
                )

        # Vérifier contraintes
        constraint_violations = []
        for i, constraint in enumerate(self.constraints):
            try:
                if not constraint(variables):
                    constraint_violations.append(f"Constraint {i+1}")
            except Exception as e:
                constraint_violations.append(f"Constraint {i+1}: {str(e)}")

        is_feasible = len(constraint_violations) == 0

        return Solution(
            variables=variables,
            objective_values=objective_values,
            fitness_score=total_fitness if is_feasible else Decimal('-inf'),
            is_feasible=is_feasible,
            constraint_violations=constraint_violations
        )

    def generate_random_solution(self, bounds: Dict[str, Tuple[Decimal, Decimal]]) -> Dict[str, Decimal]:
        """Génère solution aléatoire dans les bornes"""
        solution = {}

        for var_name, (min_val, max_val) in bounds.items():
            # Génération aléatoire uniforme
            random_val = min_val + (max_val - min_val) * Decimal(str(np.random.random()))
            solution[var_name] = random_val

        return solution

    def optimize(self,
                 bounds: Dict[str, Tuple[Decimal, Decimal]],
                 population_size: int = 100,
                 generations: int = 50) -> Dict[str, Any]:
        """
        Optimisation multi-objectifs avec algorithme évolutionnaire
        """
        print(f"🎯 MULTI-OBJECTIVE OPTIMIZATION")
        print(f"Population: {population_size}, Generations: {generations}")
        print(f"Objectives: {[obj.name for obj in self.objectives]}")
        print("-" * 50)

        # Génération population initiale
        self.population = []
        for _ in range(population_size):
            variables = self.generate_random_solution(bounds)
            solution = self.evaluate_solution(variables)
            self.population.append(solution)

            # Ajouter à frontière Pareto
            if solution.is_feasible:
                self.pareto_frontier.add_solution(solution)

        # Évolution générations
        for gen in range(generations):
            self._evolve_generation(bounds)

            # Statistiques génération
            feasible_count = sum(1 for sol in self.population if sol.is_feasible)
            avg_fitness = sum(float(sol.fitness_score) for sol in self.population if sol.is_feasible)
            avg_fitness = avg_fitness / max(feasible_count, 1)

            self.generation_history.append({
                'generation': gen,
                'feasible_solutions': feasible_count,
                'pareto_size': len(self.pareto_frontier.solutions),
                'avg_fitness': avg_fitness
            })

            if gen % 10 == 0:
                print(f"Gen {gen}: {feasible_count} feasible, Pareto size: {len(self.pareto_frontier.solutions)}")

        # Résultats finaux
        best_solutions = self.pareto_frontier.get_best_solutions(10)

        return {
            'pareto_solutions': best_solutions,
            'pareto_size': len(self.pareto_frontier.solutions),
            'total_evaluated': len(self.population) * generations,
            'generation_history': self.generation_history,
            'objectives_summary': self._analyze_objectives(best_solutions)
        }

    def _evolve_generation(self, bounds: Dict[str, Tuple[Decimal, Decimal]]):
        """Évolution d'une génération avec sélection et mutation"""
        # Sélection des parents (tournament)
        parents = self._tournament_selection(int(len(self.population) * 0.5))

        # Reproduction (crossover + mutation)
        offspring = []
        for i in range(0, len(parents) - 1, 2):
            child1, child2 = self._crossover(parents[i], parents[i+1], bounds)
            child1 = self._mutate(child1, bounds)
            child2 = self._mutate(child2, bounds)

            offspring.extend([
                self.evaluate_solution(child1),
                self.evaluate_solution(child2)
            ])

        # Sélection survivants (élitisme + diversité)
        combined_population = self.population + offspring
        self.population = self._environmental_selection(combined_population, len(self.population))

        # Mise à jour frontière Pareto
        for solution in offspring:
            if solution.is_feasible:
                self.pareto_frontier.add_solution(solution)

    def _tournament_selection(self, count: int) -> List[Solution]:
        """Sélection par tournoi"""
        selected = []
        tournament_size = 3

        for _ in range(count):
            # Tournoi aléatoire
            candidates = np.random.choice(self.population, tournament_size, replace=False)
            # Sélectionner meilleur candidat
            winner = max(candidates, key=lambda s: float(s.fitness_score) if s.is_feasible else float('-inf'))
            selected.append(winner)

        return selected

    def _crossover(self, parent1: Solution, parent2: Solution, bounds: Dict[str, Tuple[Decimal, Decimal]]) -> Tuple[Dict[str, Decimal], Dict[str, Decimal]]:
        """Crossover arithmétique"""
        alpha = Decimal(str(np.random.random()))

        child1_vars = {}
        child2_vars = {}

        for var_name in parent1.variables:
            val1 = parent1.variables[var_name]
            val2 = parent2.variables[var_name]

            # Crossover arithmétique
            child1_val = alpha * val1 + (Decimal('1') - alpha) * val2
            child2_val = alpha * val2 + (Decimal('1') - alpha) * val1

            # Respecter bornes
            min_val, max_val = bounds[var_name]
            child1_vars[var_name] = max(min_val, min(max_val, child1_val))
            child2_vars[var_name] = max(min_val, min(max_val, child2_val))

        return child1_vars, child2_vars

    def _mutate(self, variables: Dict[str, Decimal], bounds: Dict[str, Tuple[Decimal, Decimal]], mutation_rate: Decimal = Decimal('0.1')) -> Dict[str, Decimal]:
        """Mutation gaussienne"""
        mutated = variables.copy()

        for var_name, value in variables.items():
            if Decimal(str(np.random.random())) < mutation_rate:
                min_val, max_val = bounds[var_name]
                range_val = max_val - min_val
                noise = Decimal(str(np.random.normal(0, 0.1))) * range_val

                mutated_value = value + noise
                mutated[var_name] = max(min_val, min(max_val, mutated_value))

        return mutated

    def _environmental_selection(self, population: List[Solution], target_size: int) -> List[Solution]:
        """Sélection environnementale avec élitisme et diversité"""
        # Trier par fitness et faisabilité
        feasible = [sol for sol in population if sol.is_feasible]
        infeasible = [sol for sol in population if not sol.is_feasible]

        # Prioriser solutions faisables
        if len(feasible) >= target_size:
            return sorted(feasible, key=lambda s: float(s.fitness_score), reverse=True)[:target_size]
        else:
            # Compléter avec meilleures solutions infaisables
            remaining = target_size - len(feasible)
            best_infeasible = sorted(infeasible, key=lambda s: float(s.fitness_score), reverse=True)[:remaining]
            return feasible + best_infeasible

    def _analyze_objectives(self, solutions: List[Solution]) -> Dict[str, Dict[str, float]]:
        """Analyse des valeurs d'objectifs pour les meilleures solutions"""
        if not solutions:
            return {}

        analysis = {}
        for obj in self.objectives:
            values = [float(sol.objective_values.get(obj.name, 0)) for sol in solutions]
            analysis[obj.name] = {
                'min': min(values),
                'max': max(values),
                'mean': sum(values) / len(values),
                'std': np.std(values) if len(values) > 1 else 0.0
            }

        return analysis


def run_multi_objective_tests():
    """Tests validation optimisation multi-objectifs"""
    print("🎯 MULTI-OBJECTIVE OPTIMIZATION VALIDATION")
    print("=" * 50)

    try:
        # Créer optimiseur avec objectifs économiques
        optimizer = MultiObjectiveOptimizer([])
        economic_objectives = optimizer.create_economic_objectives()
        optimizer.objectives = economic_objectives

        print(f"✅ Created {len(economic_objectives)} economic objectives")

        # Définir bornes des variables
        bounds = {
            'revenue': (Decimal('1000'), Decimal('100000')),
            'costs': (Decimal('500'), Decimal('80000')),
            'volatility': (Decimal('0.01'), Decimal('0.5')),
            'exposure': (Decimal('0.1'), Decimal('10.0')),
            'cash_flow': (Decimal('100'), Decimal('50000')),
            'working_capital': (Decimal('1000'), Decimal('20000')),
            'esg_score': (Decimal('0.1'), Decimal('1.0')),
            'carbon_efficiency': (Decimal('0.5'), Decimal('2.0')),
            'output': (Decimal('1'), Decimal('1000')),
            'input_resources': (Decimal('1'), Decimal('800'))
        }

        print(f"✅ Defined bounds for {len(bounds)} variables")

        # Test génération solution aléatoire
        random_solution = optimizer.generate_random_solution(bounds)
        print(f"✅ Generated random solution with {len(random_solution)} variables")

        # Test évaluation solution
        evaluated = optimizer.evaluate_solution(random_solution)
        print(f"✅ Solution evaluation: feasible={evaluated.is_feasible}, objectives={len(evaluated.objective_values)}")

        # Test optimisation rapide
        print("\n🚀 Running mini optimization...")
        results = optimizer.optimize(bounds, population_size=20, generations=5)

        print(f"✅ Optimization completed:")
        print(f"   • Pareto solutions: {results['pareto_size']}")
        print(f"   • Total evaluated: {results['total_evaluated']}")
        print(f"   • Generations: {len(results['generation_history'])}")

        # Analyse meilleure solution
        if results['pareto_solutions']:
            best = results['pareto_solutions'][0]
            print(f"\n🏆 Best solution:")
            print(f"   • Fitness: {float(best.fitness_score):.2f}")
            print(f"   • Objectives: {len(best.objective_values)}")

            for obj_name, value in best.objective_values.items():
                print(f"     - {obj_name}: {float(value):.2f}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_multi_objective_tests()
    if success:
        print("\n🎉 MULTI-OBJECTIVE OPTIMIZATION: ALL TESTS PASSED")
    else:
        print("\n⚠️  MULTI-OBJECTIVE OPTIMIZATION: TESTS FAILED")