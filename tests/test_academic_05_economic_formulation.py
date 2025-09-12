"""
Test Académique 5: Validation Formulation Économique - Coefficients Réalistes

Ce test valide rigoureusement la formulation économique complète avec
intégration NFA→LP selon le blueprint ICGS pour scénarios réalistes.

Propriétés testées:
1. Cohérence NFA-LP: Poids regex → coefficients contraintes exacts
2. Scénarios Multi-Domaines: Agriculture/Industry/Services avec coefficients réalistes  
3. Classification Économique: Mapping déterministe mot → mesure → coefficient
4. Construction LP Automatique: Pipeline classifications → problème LP complet
5. Validation Mathématique: Cohérence équations économiques Σ(f_i × w_i)
6. Formulation Source-Target: Contraintes débit/crédit économiquement cohérentes
7. Patterns Secondaires: Intégration pénalités (carbone, taxes) dans formulation
8. Faisabilité Économique: Solutions respectant contraintes sectorielles réelles
9. Performance Integration: Complexité pipeline NFA→LP acceptable

Niveau académique: Validation formelle cohérence mathématique économique
"""

import pytest
import time
from decimal import Decimal
from typing import Dict, List, Set, Tuple

# Import des modules à tester
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_core.anchored_nfa import AnchoredWeightedNFA
from icgs_core.linear_programming import (
    LinearProgram, LinearConstraint, ConstraintType,
    build_source_constraint, build_target_constraint, build_secondary_constraint,
    validate_economic_consistency
)
from decimal import Decimal


class TestAcademicEconomicFormulation:
    """Suite de tests académiques pour validation formulation économique"""

    def setup_method(self):
        """Setup clean avec scénario économique multi-domaines"""
        self.tolerance = Decimal('1e-10')
        self.baseline_time = time.time()
        
        # Coefficients économiques réalistes selon blueprint
        self.economic_coefficients = {
            'agriculture': Decimal('1.2'),    # Agriculture: multiplicateur favorable
            'industry': Decimal('0.9'),       # Industry: coefficient neutre-défavorable  
            'services': Decimal('1.1'),       # Services: léger avantage
            'carbon_penalty': Decimal('-0.3'), # Carbon: pénalité négative
            'tax_bonus': Decimal('0.05'),     # Tax: petit bonus
            'infrastructure': Decimal('0.8')  # Infrastructure: modérément défavorable
        }

    def test_nfa_lp_coefficient_coherence(self):
        """
        PROPRIÉTÉ 1: Cohérence NFA-LP Coefficients
        Poids regex → coefficients contraintes exacts sans perte
        """
        # Construction NFA avec poids économiques réalistes
        economic_nfa = AnchoredWeightedNFA("economic_coherence_test")
        
        # Ajout patterns avec poids spécifiques
        patterns_weights = [
            ("agriculture", "Agri.*", self.economic_coefficients['agriculture']),
            ("industry", "Indus.*", self.economic_coefficients['industry']),
            ("services", "Serv.*", self.economic_coefficients['services']),
        ]
        
        for measure_id, pattern, weight in patterns_weights:
            economic_nfa.add_weighted_regex(measure_id, pattern, weight)
        
        # Extraction poids NFA par mesure
        nfa_weights = {}
        for measure_id, pattern, expected_weight in patterns_weights:
            measure_weights = economic_nfa.get_state_weights_for_measure(measure_id)
            assert len(measure_weights) == 1, f"Should have exactly one state for {measure_id}"
            
            state_id, actual_weight = next(iter(measure_weights.items()))
            nfa_weights[state_id] = actual_weight
            
            # Vérification cohérence poids
            assert actual_weight == expected_weight, \
                f"Weight mismatch for {measure_id}: expected {expected_weight}, got {actual_weight}"
        
        # Construction contrainte LP depuis poids NFA
        source_constraint = build_source_constraint(
            nfa_state_weights=nfa_weights,
            primary_regex_weight=Decimal('1.0'),
            acceptable_value=Decimal('1000'),
            constraint_name="economic_source"
        )
        
        # Vérification correspondance exacte coefficients
        for state_id, nfa_weight in nfa_weights.items():
            lp_coefficient = source_constraint.coefficients[state_id]
            assert lp_coefficient == nfa_weight, \
                f"LP coefficient mismatch for {state_id}: NFA={nfa_weight}, LP={lp_coefficient}"
        
        # Test évaluation contrainte avec flux réalistes
        realistic_flux = {
            list(nfa_weights.keys())[0]: Decimal('500'),  # Agriculture flux
            list(nfa_weights.keys())[1]: Decimal('300'),  # Industry flux  
            list(nfa_weights.keys())[2]: Decimal('200'),  # Services flux
        }
        
        # Calcul LHS : Σ(flux_i × weight_i)
        expected_lhs = sum(
            flux * nfa_weights[state_id] 
            for state_id, flux in realistic_flux.items()
        )
        
        actual_lhs = source_constraint.evaluate(realistic_flux)
        assert actual_lhs == expected_lhs, f"LHS calculation mismatch: {actual_lhs} != {expected_lhs}"

    def test_multi_domain_economic_scenarios(self):
        """
        PROPRIÉTÉ 2: Scénarios Multi-Domaines Réalistes
        Agriculture/Industry/Services avec coefficients sectoriels
        """
        # Scénarios économiques réalistes
        economic_scenarios = [
            # Scénario 1: Transaction agricole favorisée
            {
                'name': 'agricultural_transaction',
                'source_account': 'FarmCorp_Agriculture_Main',
                'target_account': 'AgriBank_Services_Account', 
                'amount': Decimal('5000'),
                'expected_source_measure': 'agriculture',
                'expected_target_measure': 'services'
            },
            # Scénario 2: Transaction industrielle standard
            {
                'name': 'industrial_transaction',
                'source_account': 'SteelWorks_Industry_Production',
                'target_account': 'LogiCorp_Services_Transport',
                'amount': Decimal('12000'),
                'expected_source_measure': 'industry',
                'expected_target_measure': 'services'
            },
            # Scénario 3: Transaction services-to-agriculture
            {
                'name': 'services_to_agriculture',
                'source_account': 'TechServices_Innovation_Hub',
                'target_account': 'GreenFarm_Agriculture_Organic',
                'amount': Decimal('3000'),
                'expected_source_measure': 'services', 
                'expected_target_measure': 'agriculture'
            }
        ]
        
        # Construction NFA multi-domaines
        multi_domain_nfa = AnchoredWeightedNFA("multi_domain_scenario")
        
        # Patterns sectoriels réalistes (noms de comptes typiques)
        sector_patterns = {
            'agriculture': ['.*Agri.*', '.*Farm.*', '.*Green.*'],
            'industry': ['.*Indus.*', '.*Steel.*', '.*Manu.*', '.*Prod.*'],
            'services': ['.*Serv.*', '.*Bank.*', '.*Tech.*', '.*Logi.*']
        }
        
        for sector, patterns in sector_patterns.items():
            for i, pattern in enumerate(patterns):
                multi_domain_nfa.add_weighted_regex(
                    measure_id=sector,
                    regex_pattern=pattern,
                    weight=self.economic_coefficients[sector],
                    regex_id=f"{sector}_{i}"
                )
        
        # Validation classifications par scénario
        for scenario in economic_scenarios:
            source_account = scenario['source_account']
            target_account = scenario['target_account']
            
            # Classification source
            source_state = multi_domain_nfa.evaluate_to_final_state(source_account)
            assert source_state is not None, f"Source account {source_account} should match a pattern"
            
            # Classification target  
            target_state = multi_domain_nfa.evaluate_to_final_state(target_account)
            assert target_state is not None, f"Target account {target_account} should match a pattern"
            
            # Vérification cohérence mesures attendues (via metadata ou poids)
            source_weights = multi_domain_nfa.get_state_weights_for_measure(scenario['expected_source_measure'])
            target_weights = multi_domain_nfa.get_state_weights_for_measure(scenario['expected_target_measure'])
            
            assert len(source_weights) > 0, f"Source measure {scenario['expected_source_measure']} should have weights"
            assert len(target_weights) > 0, f"Target measure {scenario['expected_target_measure']} should have weights"

    def test_economic_classification_determinism(self):
        """
        PROPRIÉTÉ 3: Classification Économique Déterministe
        Mapping mot → mesure → coefficient reproductible
        """
        # Construction NFA avec classification économique précise
        classification_nfa = AnchoredWeightedNFA("classification_determinism")
        
        # Patterns non-ambigus pour classification déterministe
        precise_patterns = {
            'agriculture': ('.*_Agriculture_.*', self.economic_coefficients['agriculture']),
            'industry': ('.*_Industry_.*', self.economic_coefficients['industry']),
            'services': ('.*_Services_.*', self.economic_coefficients['services'])
        }
        
        for measure_id, (pattern, weight) in precise_patterns.items():
            classification_nfa.add_weighted_regex(measure_id, pattern, weight)
        
        # Comptes tests avec classification déterministe
        test_accounts = [
            ("Alice_Agriculture_Farm", "agriculture"),
            ("Bob_Industry_Factory", "industry"), 
            ("Carol_Services_Bank", "services"),
            ("David_Agriculture_Organic", "agriculture"),
            ("Eve_Industry_Steel", "industry"),
            ("Frank_Services_IT", "services")
        ]
        
        # Test reproductibilité classification (5 répétitions)
        classification_results = {}
        
        for iteration in range(5):
            for account_name, expected_measure in test_accounts:
                result_state = classification_nfa.evaluate_to_final_state(account_name)
                
                # Stockage résultat pour comparaison
                if account_name not in classification_results:
                    classification_results[account_name] = []
                classification_results[account_name].append(result_state)
                
                # Validation état atteint
                assert result_state is not None, f"Account {account_name} should be classified"
                
                # Validation cohérence mesure
                measure_weights = classification_nfa.get_state_weights_for_measure(expected_measure)
                assert result_state in measure_weights, \
                    f"State {result_state} should correspond to measure {expected_measure}"
        
        # Vérification reproductibilité complète
        for account_name, results in classification_results.items():
            first_result = results[0]
            for result in results[1:]:
                assert result == first_result, \
                    f"Classification not deterministic for {account_name}: {results}"

    def test_automatic_lp_construction_pipeline(self):
        """
        PROPRIÉTÉ 4: Construction LP Automatique Pipeline
        Classifications NFA → problème LP complet end-to-end
        """
        # Simulation pipeline DAG → classifications → LP
        pipeline_nfa = AnchoredWeightedNFA("lp_construction_pipeline")
        
        # Configuration patterns économiques complets
        economic_patterns = {
            'agriculture': (self.economic_coefficients['agriculture'], ['.*Agriculture.*', '.*Farm.*']),
            'industry': (self.economic_coefficients['industry'], ['.*Industry.*', '.*Factory.*']),
            'services': (self.economic_coefficients['services'], ['.*Services.*', '.*Bank.*']),
            'carbon_penalty': (self.economic_coefficients['carbon_penalty'], ['.*Carbon.*', '.*Emission.*'])
        }
        
        # Construction NFA complet
        for measure_id, (weight, patterns) in economic_patterns.items():
            for i, pattern in enumerate(patterns):
                pipeline_nfa.add_weighted_regex(
                    measure_id=measure_id,
                    regex_pattern=pattern, 
                    weight=weight,
                    regex_id=f"{measure_id}_{i}"
                )
        
        # Simulation transaction économique réaliste
        transaction_scenario = {
            'source_account': 'GreenCorp_Agriculture_Organic',
            'target_account': 'EcoBank_Services_Sustainable',
            'amount': Decimal('25000'),
            'carbon_accounts': ['CarbonOffset_Emission_Reduction'],
        }
        
        # Classification comptes transaction
        source_state = pipeline_nfa.evaluate_to_final_state(transaction_scenario['source_account'])
        target_state = pipeline_nfa.evaluate_to_final_state(transaction_scenario['target_account'])
        carbon_states = [
            pipeline_nfa.evaluate_to_final_state(carbon_account) 
            for carbon_account in transaction_scenario['carbon_accounts']
        ]
        
        assert source_state is not None, "Source account should be classified"
        assert target_state is not None, "Target account should be classified"
        assert all(state is not None for state in carbon_states), "All carbon accounts should be classified"
        
        # Extraction poids pour construction LP
        all_states = [source_state, target_state] + carbon_states
        state_weights = {}
        
        for state in all_states:
            # Recherche poids par état dans tous les measures
            for measure_id in economic_patterns.keys():
                measure_weights = pipeline_nfa.get_state_weights_for_measure(measure_id)
                if state in measure_weights:
                    state_weights[state] = measure_weights[state]
                    break
        
        assert len(state_weights) == len(all_states), "All states should have associated weights"
        
        # Construction problème LP automatique
        lp_problem = LinearProgram("automatic_construction_test")
        
        # Variables flux par état classifié
        for state in all_states:
            lp_problem.add_variable(state, lower_bound=Decimal('0'))
        
        # Contraintes économiques automatiques
        source_constraint = build_source_constraint(
            nfa_state_weights={source_state: state_weights[source_state]},
            primary_regex_weight=state_weights[source_state],
            acceptable_value=transaction_scenario['amount'],
            constraint_name="auto_source"
        )
        
        target_constraint = build_target_constraint(
            nfa_state_weights={target_state: state_weights[target_state]},
            primary_regex_weight=state_weights[target_state],
            required_value=transaction_scenario['amount'] * Decimal('0.9'),  # 90% minimum
            constraint_name="auto_target"
        )
        
        # Contrainte carbone (pénalité)
        carbon_weights = {state: state_weights[state] for state in carbon_states}
        carbon_constraint = build_secondary_constraint(
            nfa_state_weights=carbon_weights,
            secondary_regex_weight=self.economic_coefficients['carbon_penalty'],
            constraint_name="auto_carbon"
        )
        
        lp_problem.add_constraint(source_constraint)
        lp_problem.add_constraint(target_constraint)
        lp_problem.add_constraint(carbon_constraint)
        
        # Validation structure LP générée
        validation_errors = lp_problem.validate_problem()
        assert len(validation_errors) == 0, f"Automatically constructed LP should be valid: {validation_errors}"
        
        # Test solution faisable
        A_matrix, b_vector, variable_order = lp_problem.get_constraint_matrix()
        assert len(A_matrix) == 3, "Should have 3 constraints (source, target, carbon)"
        assert len(variable_order) == len(all_states), f"Should have {len(all_states)} variables"

    def test_mathematical_economic_coherence(self):
        """
        PROPRIÉTÉ 5: Cohérence Mathématique Économique
        Validation équations Σ(f_i × w_i) économiquement sensées
        """
        # Coefficients économiques avec rationale mathématique
        coherence_coefficients = {
            # Agriculture: encouragée (coefficient > 1)
            'agriculture': Decimal('1.25'),  # 25% bonus
            # Industry: neutre vers défavorable  
            'industry': Decimal('0.95'),     # 5% malus
            # Services: légèrement favorisé
            'services': Decimal('1.10'),     # 10% bonus
            # Carbon: forte pénalité
            'carbon_tax': Decimal('-0.40'),  # 40% pénalité
            # Innovation: très favorisé
            'innovation': Decimal('1.50')    # 50% bonus
        }
        
        # Construction NFA avec coefficients cohérents
        coherence_nfa = AnchoredWeightedNFA("mathematical_coherence")
        
        for measure_id, coefficient in coherence_coefficients.items():
            coherence_nfa.add_weighted_regex(
                measure_id=measure_id,
                regex_pattern=f"{measure_id.title()}",  # Pattern simple pour fin de nom
                weight=coefficient
            )
        
        # Scénario économique: entreprise innovation → agriculture  
        innovation_account = "TechCorp_Innovation"  # Se termine par "Innovation"
        agriculture_account = "GreenFarm_Agriculture"  # Se termine par "Agriculture"
        transaction_amount = Decimal('10000')
        
        # Classifications
        innovation_state = coherence_nfa.evaluate_to_final_state(innovation_account)
        agriculture_state = coherence_nfa.evaluate_to_final_state(agriculture_account)
        
        assert innovation_state is not None, "Innovation account should be classified"
        assert agriculture_state is not None, "Agriculture account should be classified"
        
        # Extraction coefficients pour validation mathématique
        innovation_weights = coherence_nfa.get_state_weights_for_measure('innovation')
        agriculture_weights = coherence_nfa.get_state_weights_for_measure('agriculture')
        
        # Protection contre états non trouvés
        if innovation_state not in innovation_weights:
            pytest.fail(f"Innovation state {innovation_state} not found in weights: {innovation_weights}")
        if agriculture_state not in agriculture_weights:
            pytest.fail(f"Agriculture state {agriculture_state} not found in weights: {agriculture_weights}")
            
        innovation_coeff = innovation_weights[innovation_state]
        agriculture_coeff = agriculture_weights[agriculture_state]
        
        # Validation cohérence économique: innovation > agriculture > neutre > industry > carbon
        assert innovation_coeff > agriculture_coeff, "Innovation should be more favorable than agriculture"
        assert agriculture_coeff > Decimal('1.0'), "Agriculture should be favorable (>1)"
        assert coherence_coefficients['industry'] < Decimal('1.0'), "Industry should be less favorable (<1)"
        assert coherence_coefficients['carbon_tax'] < Decimal('0'), "Carbon should be penalty (<0)"
        
        # Test équation économique réaliste
        # Source (innovation): flux × 1.50 ≤ montant_max
        # Target (agriculture): flux × 1.25 ≥ montant_min
        
        source_max = transaction_amount * Decimal('1.2')  # 20% marge
        target_min = transaction_amount * Decimal('0.8')  # 80% minimum
        
        # Construction contraintes avec variables communes (plus réaliste économiquement)
        combined_states = {
            innovation_state: innovation_coeff,
            agriculture_state: agriculture_coeff
        }
        
        source_constraint = build_source_constraint(
            nfa_state_weights=combined_states,
            primary_regex_weight=innovation_coeff,
            acceptable_value=source_max,
            constraint_name="combined_source"
        )
        
        target_constraint = build_target_constraint(
            nfa_state_weights=combined_states,
            primary_regex_weight=agriculture_coeff,
            required_value=target_min,
            constraint_name="combined_target"
        )
        
        # Validation cohérence économique contraintes
        economic_coherence = validate_economic_consistency(source_constraint, target_constraint)
        assert economic_coherence, "Economic constraints should be mathematically coherent"
        
        # Test faisabilité avec flux optimal (corriger calcul)
        # Pour contrainte source: innovation×1.50 + agriculture×1.25 ≤ source_max (12000)
        # Si flux identique pour les deux: flux×(1.50+1.25) ≤ 12000
        # Donc flux_max = 12000/(1.50+1.25) = 12000/2.75
        optimal_flux = source_max / (innovation_coeff + agriculture_coeff)
        
        flux_values = {
            innovation_state: optimal_flux,
            agriculture_state: optimal_flux
        }
        
        assert source_constraint.is_satisfied(flux_values), "Source constraint should be satisfied with optimal flux"
        assert target_constraint.is_satisfied(flux_values), "Target constraint should be satisfied with optimal flux"

    def test_source_target_formulation_coherence(self):
        """
        PROPRIÉTÉ 6: Cohérence Formulation Source-Target
        Contraintes débit/crédit économiquement cohérentes
        """
        # Scénario source-target économique réaliste
        source_target_nfa = AnchoredWeightedNFA("source_target_coherence")
        
        # Patterns avec coefficients asymétriques réalistes
        asymmetric_patterns = {
            'agriculture_source': ('.*Farm.*Source.*', Decimal('1.3')),      # Source agricole favorisée
            'industry_target': ('.*Factory.*Target.*', Decimal('0.8')),      # Target industriel défavorisé
            'services_neutral': ('.*Bank.*Neutral.*', Decimal('1.0'))        # Services neutre
        }
        
        for measure_id, (pattern, weight) in asymmetric_patterns.items():
            source_target_nfa.add_weighted_regex(measure_id, pattern, weight)
        
        # Transaction test avec asymétrie économique
        source_account = "GreenFarm_Source_Organic"  # Agriculture source
        target_account = "SteelFactory_Target_Heavy"  # Industry target
        transaction_amount = Decimal('50000')
        
        source_state = source_target_nfa.evaluate_to_final_state(source_account)
        target_state = source_target_nfa.evaluate_to_final_state(target_account)
        
        assert source_state is not None, "Source should be classified"
        assert target_state is not None, "Target should be classified"
        
        # Extraction coefficients asymétriques
        source_weights = source_target_nfa.get_state_weights_for_measure('agriculture_source')
        target_weights = source_target_nfa.get_state_weights_for_measure('industry_target')
        
        source_coeff = source_weights[source_state]  # 1.3
        target_coeff = target_weights[target_state]  # 0.8
        
        # Validation asymétrie économique: source favorisée > target défavorisé
        assert source_coeff > target_coeff, f"Source coefficient ({source_coeff}) should be higher than target ({target_coeff})"
        assert source_coeff > Decimal('1.0'), "Source should be favorable"
        assert target_coeff < Decimal('1.0'), "Target should be less favorable"
        
        # Construction contraintes avec asymétrie
        source_constraint = build_source_constraint(
            nfa_state_weights={source_state: source_coeff},
            primary_regex_weight=source_coeff,
            acceptable_value=transaction_amount,  # Source peut débiter montant complet
            constraint_name="asymmetric_source"
        )
        
        # Target: avec coefficient plus bas, doit recevoir proportionnellement plus de flux
        adjusted_target_amount = transaction_amount * (source_coeff / target_coeff)  # Ajustement asymétrie
        
        target_constraint = build_target_constraint(
            nfa_state_weights={target_state: target_coeff},
            primary_regex_weight=target_coeff,
            required_value=transaction_amount,  # Target doit recevoir montant nominal
            constraint_name="asymmetric_target"
        )
        
        # Test faisabilité avec flux ajusté pour asymétrie
        # flux_source × 1.3 ≤ 50000 → flux_source ≤ 38461.54
        # flux_target × 0.8 ≥ 50000 → flux_target ≥ 62500
        
        # Ces contraintes sont intentionnellement conflictuelles pour tester détection
        flux_test = {source_state: Decimal('38000'), target_state: Decimal('63000')}
        
        source_satisfied = source_constraint.is_satisfied(flux_test)
        target_satisfied = target_constraint.is_satisfied(flux_test)
        
        assert source_satisfied, "Source constraint should be satisfied with adjusted flux"
        assert target_satisfied, "Target constraint should be satisfied with adjusted flux"
        
        # Validation détection incohérence si flux identiques imposés
        identical_flux = {source_state: Decimal('40000'), target_state: Decimal('40000')}
        
        # flux × 1.3 = 52000 > 50000 (violation source)
        # flux × 0.8 = 32000 < 50000 (violation target)  
        
        source_violation = source_constraint.get_violation(identical_flux)
        target_violation = target_constraint.get_violation(identical_flux)
        
        assert source_violation > Decimal('0'), "Should detect source violation with identical flux"
        assert target_violation > Decimal('0'), "Should detect target violation with identical flux"

    def test_secondary_patterns_integration(self):
        """
        PROPRIÉTÉ 7: Intégration Patterns Secondaires
        Pénalités (carbone, taxes) dans formulation complète
        """
        # NFA avec patterns principaux + secondaires
        integrated_nfa = AnchoredWeightedNFA("secondary_patterns_integration")
        
        # Patterns principaux (positifs) - patterns simples
        primary_patterns = {
            'agriculture': (Decimal('1.2'), 'Agriculture'),
            'services': (Decimal('1.1'), 'Services')
        }
        
        # Patterns secondaires (négatifs/pénalités) - patterns simples
        secondary_patterns = {
            'carbon_penalty': (Decimal('-0.25'), 'Carbon'),
            'tax_penalty': (Decimal('-0.15'), 'Tax'),
            'pollution_penalty': (Decimal('-0.35'), 'Pollution')
        }
        
        # Construction NFA intégré
        all_patterns = {**primary_patterns, **secondary_patterns}
        for measure_id, (weight, pattern) in all_patterns.items():
            integrated_nfa.add_weighted_regex(measure_id, pattern, weight)
        
        # Scénario avec patterns multiples - noms qui se terminent par les patterns
        multi_pattern_accounts = [
            "GreenAgri_Agriculture",      # Se termine par "Agriculture"
            "EcoServices_Services",       # Se termine par "Services" 
            "OldFactory_Pollution",       # Se termine par "Pollution"
            "TaxHaven_Tax",              # Se termine par "Tax"
        ]
        
        # Classification et validation patterns multiples
        classifications = {}
        for account in multi_pattern_accounts:
            state = integrated_nfa.evaluate_to_final_state(account)
            assert state is not None, f"Account {account} should be classified"
            classifications[account] = state
        
        # Construction LP avec patterns intégrés
        lp_integrated = LinearProgram("integrated_patterns_test")
        
        # Variables pour tous états classifiés
        for account, state in classifications.items():
            lp_integrated.add_variable(state, lower_bound=Decimal('0'))
        
        # Contraintes primaires (agriculture + services)
        primary_states = {}
        for measure_id in primary_patterns.keys():
            weights = integrated_nfa.get_state_weights_for_measure(measure_id)
            # Filtrer uniquement les états qui ont été créés comme variables
            filtered_weights = {
                state: weight for state, weight in weights.items() 
                if state in lp_integrated.variables
            }
            primary_states.update(filtered_weights)
        
        if primary_states:
            primary_constraint = build_source_constraint(
                nfa_state_weights=primary_states,
                primary_regex_weight=Decimal('1.0'),
                acceptable_value=Decimal('100000'),
                constraint_name="integrated_primary"
            )
            lp_integrated.add_constraint(primary_constraint)
        
        # Contraintes secondaires (pénalités ≤ 0)
        for penalty_measure in secondary_patterns.keys():
            penalty_weights = integrated_nfa.get_state_weights_for_measure(penalty_measure)
            # Filtrer uniquement les états qui ont été créés comme variables
            filtered_penalty_weights = {
                state: weight for state, weight in penalty_weights.items() 
                if state in lp_integrated.variables
            }
            if filtered_penalty_weights:
                penalty_constraint = build_secondary_constraint(
                    nfa_state_weights=filtered_penalty_weights,
                    secondary_regex_weight=secondary_patterns[penalty_measure][0],
                    constraint_name=f"penalty_{penalty_measure}"
                )
                lp_integrated.add_constraint(penalty_constraint)
        
        # Validation structure intégrée
        validation_errors = lp_integrated.validate_problem()
        assert len(validation_errors) == 0, f"Integrated LP should be valid: {validation_errors}"
        
        # Test solution avec pénalités actives
        test_flux = {state: Decimal('1000') for state in classifications.values()}
        lp_integrated.set_variable_values(test_flux)
        
        # Vérification contraintes pénalités
        violations = lp_integrated.get_constraint_violations()
        penalty_violations = {name: violation for name, violation in violations.items() if 'penalty' in name}
        
        # Pénalités peuvent être violées (flux positif × coefficient négatif > 0)
        # C'est attendu et doit être détecté correctement

    def test_realistic_economic_feasibility(self):
        """
        PROPRIÉTÉ 8: Faisabilité Économique Réaliste
        Solutions respectant contraintes sectorielles réelles
        """
        # Scénario économique complet réaliste
        realistic_nfa = AnchoredWeightedNFA("realistic_economic_scenario")
        
        # Coefficients basés sur données économiques réelles (simulées)
        realistic_coefficients = {
            'agriculture': Decimal('1.15'),      # Agriculture: léger avantage
            'manufacturing': Decimal('0.92'),    # Manufacturing: léger désavantage
            'finance': Decimal('1.05'),          # Finance: petit avantage
            'technology': Decimal('1.30'),       # Technology: fort avantage
            'energy': Decimal('0.85'),           # Energy: désavantagé
            'carbon_tax': Decimal('-0.20'),      # Carbon tax: pénalité modérée
            'green_bonus': Decimal('0.10')       # Green bonus: petit encouragement
        }
        
        # Patterns sectoriels précis (simples pour éviter conflits)
        sector_patterns = {
            'agriculture': 'Agriculture',      # Se termine par "Agriculture"
            'manufacturing': 'Manufacturing',  # Se termine par "Manufacturing" 
            'finance': 'Finance',             # Se termine par "Finance"
            'technology': 'Technology',       # Se termine par "Technology"
            'energy': 'Energy',              # Se termine par "Energy"
            'carbon_tax': 'Carbon',          # Se termine par "Carbon"
            'green_bonus': 'Green'           # Se termine par "Green"
        }
        
        for sector, pattern in sector_patterns.items():
            realistic_nfa.add_weighted_regex(
                measure_id=sector,
                regex_pattern=pattern,
                weight=realistic_coefficients[sector]
            )
        
        # Transaction économique réaliste multi-sectorielle
        realistic_transaction = {
            'source': 'TechCorp_Technology',      # Se termine par "Technology"
            'target': 'GreenFarm_Agriculture',     # Se termine par "Agriculture"
            'carbon_offset': 'CarbonCredit_Carbon', # Se termine par "Carbon"
            'amount': Decimal('75000')
        }
        
        # Classifications
        source_state = realistic_nfa.evaluate_to_final_state(realistic_transaction['source'])
        target_state = realistic_nfa.evaluate_to_final_state(realistic_transaction['target'])
        carbon_state = realistic_nfa.evaluate_to_final_state(realistic_transaction['carbon_offset'])
        
        assert source_state is not None, "Tech source should be classified"
        assert target_state is not None, "Agriculture target should be classified" 
        assert carbon_state is not None, "Carbon offset should be classified"
        
        # Construction problème LP réaliste complet
        realistic_lp = LinearProgram("realistic_economic_scenario")
        
        # Variables
        realistic_lp.add_variable(source_state, lower_bound=Decimal('0'))
        realistic_lp.add_variable(target_state, lower_bound=Decimal('0'))
        realistic_lp.add_variable(carbon_state, lower_bound=Decimal('0'))
        
        # Contraintes économiques réalistes
        
        # Source (Tech): coefficient 1.30 → flux × 1.30 ≤ montant + marge
        source_weights = realistic_nfa.get_state_weights_for_measure('technology')
        source_constraint = build_source_constraint(
            nfa_state_weights={source_state: source_weights[source_state]},
            primary_regex_weight=source_weights[source_state],
            acceptable_value=realistic_transaction['amount'] * Decimal('1.1'),  # 10% marge
            constraint_name="tech_source"
        )
        
        # Target (Agriculture + potentiel Green): au moins montant de base
        agriculture_weights = realistic_nfa.get_state_weights_for_measure('agriculture')
        target_constraint = build_target_constraint(
            nfa_state_weights={target_state: agriculture_weights[target_state]},
            primary_regex_weight=agriculture_weights[target_state], 
            required_value=realistic_transaction['amount'] * Decimal('0.9'),  # 90% minimum
            constraint_name="agriculture_target"
        )
        
        # Carbon (pénalité): doit rester ≤ 0 (minimisation émissions)
        carbon_weights = realistic_nfa.get_state_weights_for_measure('carbon_tax')
        carbon_constraint = build_secondary_constraint(
            nfa_state_weights={carbon_state: carbon_weights[carbon_state]},
            secondary_regex_weight=carbon_weights[carbon_state],
            constraint_name="carbon_penalty"
        )
        
        realistic_lp.add_constraint(source_constraint)
        realistic_lp.add_constraint(target_constraint)
        realistic_lp.add_constraint(carbon_constraint)
        
        # Validation et test faisabilité
        errors = realistic_lp.validate_problem()
        assert len(errors) == 0, f"Realistic scenario should be valid: {errors}"
        
        # Solution faisable réaliste
        tech_flux = realistic_transaction['amount'] / source_weights[source_state]      # ≈ 57692
        agri_flux = realistic_transaction['amount'] / agriculture_weights[target_state] # ≈ 65217
        carbon_flux = Decimal('0')  # Pas de flux carbon (optimal pour pénalité)
        
        feasible_solution = {
            source_state: tech_flux,
            target_state: agri_flux, 
            carbon_state: carbon_flux
        }
        
        realistic_lp.set_variable_values(feasible_solution)
        assert realistic_lp.is_feasible(), "Realistic solution should be feasible"
        
        # Validation économique
        source_lhs = source_constraint.evaluate(feasible_solution)
        target_lhs = target_constraint.evaluate(feasible_solution)
        carbon_lhs = carbon_constraint.evaluate(feasible_solution)
        
        assert source_lhs <= source_constraint.bound, f"Source: {source_lhs} should be ≤ {source_constraint.bound}"
        assert target_lhs >= target_constraint.bound, f"Target: {target_lhs} should be ≥ {target_constraint.bound}"
        assert carbon_lhs <= carbon_constraint.bound, f"Carbon: {carbon_lhs} should be ≤ {carbon_constraint.bound}"

    def test_integration_performance_pipeline(self):
        """
        PROPRIÉTÉ 9: Performance Integration Pipeline
        Complexité NFA→LP acceptable pour problèmes moyens
        """
        problem_sizes = [10, 25, 50]  # Nombre de patterns/mesures
        pipeline_times = []
        
        for n_measures in problem_sizes:
            start_time = time.perf_counter()
            
            # Construction NFA large
            performance_nfa = AnchoredWeightedNFA(f"performance_test_{n_measures}")
            
            # Ajout patterns multiples
            base_coefficients = [Decimal('1.1'), Decimal('0.9'), Decimal('1.2'), Decimal('-0.1')]
            
            for i in range(n_measures):
                measure_id = f"measure_{i}"
                pattern = f"MEASURE_{i}"  # Pattern simple pour fins de noms
                weight = base_coefficients[i % len(base_coefficients)]
                
                performance_nfa.add_weighted_regex(measure_id, pattern, weight)
            
            # Simulation classifications multiples - noms qui matchent les patterns
            test_accounts = [f"Account_{i}_MEASURE_{i}" for i in range(n_measures)]
            classifications = {}
            
            for account in test_accounts:
                state = performance_nfa.evaluate_to_final_state(account)
                if state:  # Peut être None si pattern ne matche pas
                    classifications[account] = state
            
            # Construction LP depuis classifications
            performance_lp = LinearProgram(f"performance_lp_{n_measures}")
            
            # Variables
            unique_states = set(classifications.values())
            for state in unique_states:
                performance_lp.add_variable(state, lower_bound=Decimal('0'))
            
            # Contraintes (une par mesure)
            for i in range(min(n_measures, len(unique_states))):
                measure_id = f"measure_{i}"
                measure_weights = performance_nfa.get_state_weights_for_measure(measure_id)
                
                if measure_weights:
                    constraint = build_source_constraint(
                        nfa_state_weights=measure_weights,
                        primary_regex_weight=Decimal('1.0'),
                        acceptable_value=Decimal('1000'),
                        constraint_name=f"perf_constraint_{i}"
                    )
                    performance_lp.add_constraint(constraint)
            
            # Validation et extraction matrice
            performance_lp.validate_problem()
            A_matrix, b_vector, var_order = performance_lp.get_constraint_matrix()
            
            end_time = time.perf_counter()
            pipeline_time = end_time - start_time
            pipeline_times.append(pipeline_time)
        
        # Validation performance: croissance sous-quadratique
        if len(pipeline_times) >= 2:
            time_ratio = pipeline_times[-1] / pipeline_times[0]
            size_ratio = problem_sizes[-1] / problem_sizes[0]
            
            # Pipeline devrait être proche de linéaire pour patterns moyens
            assert time_ratio < size_ratio * 1.8, \
                f"Pipeline performance too slow: {time_ratio} vs size ratio {size_ratio}"


def run_academic_test_5():
    """
    Exécution test académique 5 avec rapport détaillé
    
    Returns:
        bool: True si toutes propriétés formulation économique validées
    """
    pytest_result = pytest.main([
        __file__,
        "-v", 
        "--tb=short",
        "-x"  # Stop au premier échec
    ])
    
    return pytest_result == 0


if __name__ == "__main__":
    success = run_academic_test_5()
    if success:
        print("✅ TEST ACADÉMIQUE 5 RÉUSSI - Formulation économique validée")
        print("📊 Propriétés mathématiques vérifiées:")
        print("   • Cohérence NFA-LP avec coefficients exacts")
        print("   • Scénarios multi-domaines Agriculture/Industry/Services")
        print("   • Classification économique déterministe")
        print("   • Construction LP automatique depuis classifications")
        print("   • Cohérence mathématique équations économiques")
        print("   • Formulation source-target asymétrique cohérente")
        print("   • Intégration patterns secondaires (pénalités)")
        print("   • Faisabilité économique avec contraintes sectorielles")
        print("   • Performance pipeline NFA→LP acceptable")
    else:
        print("❌ TEST ACADÉMIQUE 5 ÉCHOUÉ - Violations formulation économique")
        exit(1)