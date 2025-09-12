"""
AnchoredWeightedNFA - Extension WeightedNFA avec ancrage automatique et gestion état frozen

Module implémentant automate fini pondéré avec fonctionnalités avancées selon blueprint ICGS:
- Ancrage automatique: ajout ".*$" si nécessaire pour regex complète  
- État frozen: NFA figé pendant énumération pour cohérence
- RegexWeight: extraction coefficients pour construction LP
- Élimination matches partiels avec ancrage complet

Objectif: Élimination matches partiels + cohérence temporelle évaluation
Propriétés:
- Ancrage automatique: ajout ".*$" si nécessaire pour regex complète
- État frozen: NFA figé pendant énumération pour cohérence  
- RegexWeight: extraction coefficients pour construction LP
"""

from typing import Dict, List, Set, Optional, Any
from decimal import Decimal
import copy
import re
from .weighted_nfa import WeightedNFA, NFAState, NFATransition, RegexWeight, TransitionType


class AnchoredWeightedNFA(WeightedNFA):
    """
    Extension WeightedNFA avec ancrage automatique et gestion état frozen
    
    Fonctionnalités avancées:
    - Ancrage automatique des regex pour élimination matches partiels
    - État frozen avec snapshot immuable pendant énumération
    - Classification déterministe mot → état_final → coefficients LP
    - Extraction mapping état_final → RegexWeights pour construction contraintes
    
    Architecture:
    - Hérite WeightedNFA pour fonctionnalités de base
    - Ajoute logique ancrage et gestion cohérence temporelle
    - Support freeze/unfreeze pour énumération sûre
    """
    
    def __init__(self, name: str = "AnchoredWeightedNFA"):
        super().__init__(name)
        
        # État frozen pour cohérence
        self.is_frozen: bool = False
        self.frozen_final_states: List[NFAState] = []
        self.frozen_transitions: List[NFATransition] = []
        self._frozen_snapshot_timestamp: Optional[float] = None
        
        # Statistiques ancrage et frozen
        self.stats.update({
            'patterns_anchored': 0,
            'freeze_operations': 0,
            'frozen_evaluations': 0,
            'anchor_transformations': 0
        })
    
    def add_weighted_regex(self, measure_id: str, regex_pattern: str, 
                          weight: Decimal, regex_id: Optional[str] = None) -> NFAState:
        """
        Ajoute regex pondéré avec ancrage automatique
        
        ANCRAGE AUTOMATIQUE: Si pattern ne termine pas par $, 
        transformation automatique en ".*pattern$" pour match complet
        
        Args:
            measure_id: Identifiant mesure économique
            regex_pattern: Pattern regex (sera ancré automatiquement)
            weight: Poids associé pour contraintes LP
            regex_id: Identifiant unique regex
            
        Returns:
            État final avec RegexWeight associé
            
        Raises:
            RuntimeError: Si NFA est frozen (modification interdite)
            ValueError: Si pattern regex invalide
        """
        if self.is_frozen:
            raise RuntimeError("Cannot modify frozen AnchoredWeightedNFA")
        
        # ANCRAGE AUTOMATIQUE selon blueprint
        anchored_pattern = self._apply_automatic_anchoring(regex_pattern)
        
        if anchored_pattern != regex_pattern:
            self.stats['anchor_transformations'] += 1
            self.stats['patterns_anchored'] += 1
        
        # Utilisation méthode parent avec pattern ancré
        final_state = super().add_weighted_regex_simple(
            measure_id, anchored_pattern, weight, regex_id
        )
        
        # Métadonnées ancrage pour debugging
        final_state.metadata.update({
            'original_pattern': regex_pattern,
            'anchored_pattern': anchored_pattern,
            'was_anchored': anchored_pattern != regex_pattern
        })
        
        return final_state
    
    def freeze(self):
        """
        Fige NFA pour énumération cohérente
        
        Capture snapshot états finaux et transitions actuels.
        Bloque modifications ultérieures.
        Garantit déterminisme évaluation pendant énumération.
        
        Fonctionnement:
        1. Capture snapshot immuable états finaux
        2. Capture snapshot transitions pour cohérence
        3. Marque NFA comme frozen avec timestamp
        4. Bloque toute modification jusqu'à unfreeze()
        """
        if self.is_frozen:
            return  # Déjà frozen
        
        import time
        
        # Capture snapshot états finaux (deep copy pour immutabilité)
        self.frozen_final_states = []
        for state in self.get_final_states():
            frozen_state = copy.deepcopy(state)
            self.frozen_final_states.append(frozen_state)
        
        # Capture snapshot transitions pour cohérence complète
        self.frozen_transitions = copy.deepcopy(self.transitions)
        
        # Marquage frozen avec timestamp
        self.is_frozen = True
        self._frozen_snapshot_timestamp = time.time()
        
        self.stats['freeze_operations'] += 1
    
    def unfreeze(self):
        """
        Dégèle NFA pour permettre modifications
        
        Restaure capacité de modification après énumération.
        Invalide snapshots frozen précédents.
        """
        self.is_frozen = False
        self.frozen_final_states = []
        self.frozen_transitions = []
        self._frozen_snapshot_timestamp = None
        
        # Invalidation cache pour cohérence
        self._final_states_cache = None
    
    def evaluate_to_final_state(self, word: str) -> Optional[str]:
        """
        Évalue mot et retourne ID état final ou None
        
        Utilise snapshot frozen_final_states si NFA figé.
        Match complet requis (grâce à ancrage automatique).
        Retourne state_id pour classification déterministe.
        
        Args:
            word: Mot à évaluer avec ancrage complet
            
        Returns:
            state_id du premier état final atteint, None si aucun match
        """
        if self.is_frozen:
            self.stats['frozen_evaluations'] += 1
            
            # Utilise snapshot frozen pour cohérence
            final_state_ids = self._evaluate_with_frozen_snapshot(word)
        else:
            # Évaluation normale
            final_state_ids = self.evaluate_word(word)
        
        # Retourne premier état final (déterminisme)
        if final_state_ids:
            return next(iter(final_state_ids))
        return None
    
    def get_final_state_classifications(self) -> Dict[str, List[RegexWeight]]:
        """
        Extraction mapping état_final → RegexWeights pour LP
        
        Retourne coefficients par état final pour construction contraintes.
        Utilise snapshot frozen si NFA figé pour cohérence.
        
        Returns:
            Dict: state_id → [RegexWeight] pour construction contraintes LP
        """
        classifications = {}
        
        # Utilise snapshot frozen si disponible
        final_states = (self.frozen_final_states if self.is_frozen 
                       else self.get_final_states())
        
        for state in final_states:
            if state.regex_weights:
                classifications[state.state_id] = state.regex_weights.copy()
        
        return classifications
    
    def get_state_weights_for_measure(self, measure_id: str) -> Dict[str, Decimal]:
        """
        Récupère poids par état pour mesure donnée
        
        Utilisé pour construction contraintes LP spécifiques à une mesure.
        
        Args:
            measure_id: Identifiant mesure économique
            
        Returns:
            Dict: state_id → weight pour mesure donnée
        """
        state_weights = {}
        
        # Utilise snapshot frozen si disponible
        final_states = (self.frozen_final_states if self.is_frozen 
                       else self.get_final_states())
        
        for state in final_states:
            for regex_weight in state.regex_weights:
                if regex_weight.measure_id == measure_id:
                    state_weights[state.state_id] = regex_weight.weight
                    break  # Une seule mesure par état dans cette implémentation
        
        return state_weights
    
    def validate_anchored_nfa_properties(self) -> List[str]:
        """
        Validation propriétés spécifiques AnchoredWeightedNFA
        
        Vérifie:
        - Ancrage correct des patterns (tous finissent par $)
        - Cohérence état frozen si applicable
        - Correspondance snapshots frozen avec état actuel
        - Métadonnées ancrage correctes
        
        Returns:
            Liste erreurs détectées (vide si propriétés valides)
        """
        errors = super().validate_nfa_structure()
        
        # Vérification ancrage patterns
        for transition in self.transitions:
            if (transition.transition_type == TransitionType.REGEX_MATCH 
                and transition.condition):
                
                if not self._is_properly_anchored(transition.condition):
                    errors.append(f"Pattern not properly anchored: {transition.condition}")
        
        # Vérification cohérence frozen state
        if self.is_frozen:
            if not self.frozen_final_states:
                errors.append("Frozen NFA has no frozen final states")
            
            if not self.frozen_transitions:
                errors.append("Frozen NFA has no frozen transitions")
            
            # Vérification cohérence métadonnées ancrage
            for state in self.frozen_final_states:
                if 'anchored_pattern' not in state.metadata:
                    errors.append(f"Frozen state {state.state_id} missing anchored_pattern metadata")
        
        return errors
    
    def get_frozen_state_info(self) -> Dict[str, Any]:
        """
        Information sur état frozen pour debugging et tests
        
        Returns:
            Dict avec informations détaillées sur état frozen
        """
        return {
            'is_frozen': self.is_frozen,
            'frozen_final_states_count': len(self.frozen_final_states),
            'frozen_transitions_count': len(self.frozen_transitions),
            'frozen_timestamp': self._frozen_snapshot_timestamp,
            'freeze_operations_total': self.stats.get('freeze_operations', 0),
            'frozen_evaluations_performed': self.stats.get('frozen_evaluations', 0)
        }
    
    # Méthodes privées implémentation
    
    def _apply_automatic_anchoring(self, regex_pattern: str) -> str:
        """
        Applique ancrage automatique selon blueprint ICGS
        
        Algorithme: Si pattern ne termine pas par $, 
        transformation en ".*pattern$" pour match complet
        
        Args:
            regex_pattern: Pattern original
            
        Returns:
            Pattern ancré automatiquement
            
        Raises:
            ValueError: Si pattern invalide après ancrage
        """
        if not regex_pattern:
            return regex_pattern
        
        # Ancrage automatique si pattern ne termine pas par $
        if not regex_pattern.endswith('$'):
            anchored_pattern = f".*{regex_pattern}$"
        else:
            anchored_pattern = regex_pattern
        
        # Validation pattern ancré
        try:
            re.compile(anchored_pattern)
        except re.error as e:
            raise ValueError(f"Invalid anchored pattern '{anchored_pattern}': {e}")
        
        return anchored_pattern
    
    def _is_properly_anchored(self, pattern: str) -> bool:
        """Vérifie si pattern correctement ancré (se termine par $)"""
        return pattern.endswith('$')
    
    def _evaluate_with_frozen_snapshot(self, word: str) -> Set[str]:
        """
        Évaluation avec snapshot frozen pour cohérence
        
        Utilise frozen_transitions et frozen_final_states
        pour évaluation cohérente pendant énumération.
        
        Args:
            word: Mot à évaluer
            
        Returns:
            Set des états finaux atteints avec snapshot frozen
        """
        if not self.is_frozen or self.initial_state_id is None:
            return set()
        
        # Configuration courante avec états frozen
        current_states = self._epsilon_closure_frozen({self.initial_state_id})
        
        # Traitement de chaque symbole avec transitions frozen
        for symbol in word:
            next_states = set()
            
            for state_id in current_states:
                frozen_transitions = [
                    t for t in self.frozen_transitions 
                    if t.from_state == state_id
                ]
                
                for transition in frozen_transitions:
                    if transition.matches(symbol):
                        next_states.add(transition.to_state)
            
            current_states = self._epsilon_closure_frozen(next_states)
        
        # États finaux frozen dans configuration finale
        frozen_final_ids = {state.state_id for state in self.frozen_final_states}
        final_state_ids = current_states & frozen_final_ids
        
        return final_state_ids
    
    def _epsilon_closure_frozen(self, states: Set[str]) -> Set[str]:
        """
        Epsilon-closure utilisant transitions frozen pour cohérence
        
        Similaire à méthode parent mais utilise snapshot frozen.
        
        Args:
            states: États de départ
            
        Returns:
            Epsilon-closure avec transitions frozen
        """
        closure = set(states)
        stack = list(states)
        
        while stack:
            current = stack.pop()
            
            # Transitions epsilon depuis frozen_transitions
            epsilon_transitions = [
                t for t in self.frozen_transitions
                if (t.from_state == current and 
                    t.transition_type == TransitionType.EPSILON)
            ]
            
            for transition in epsilon_transitions:
                if transition.to_state not in closure:
                    closure.add(transition.to_state)
                    stack.append(transition.to_state)
        
        return closure
    
    def __repr__(self) -> str:
        """Représentation string avec info frozen state"""
        frozen_info = " [FROZEN]" if self.is_frozen else ""
        return (f"AnchoredWeightedNFA(name='{self.name}', states={len(self.states)}, "
                f"transitions={len(self.transitions)}, "
                f"final_states={len(self.get_final_states())}, "
                f"anchored_patterns={self.stats.get('patterns_anchored', 0)}{frozen_info})")


# Utilitaires pour tests et debugging

def create_anchored_test_nfa() -> AnchoredWeightedNFA:
    """
    Crée AnchoredWeightedNFA simple pour tests unitaires
    
    Structure: pattern "abc" automatiquement ancré en ".*abc$"
    """
    nfa = AnchoredWeightedNFA("test_anchored_nfa")
    
    # Pattern qui sera automatiquement ancré
    nfa.add_weighted_regex(
        measure_id="test_measure",
        regex_pattern="abc",  # Sera transformé en ".*abc$" 
        weight=Decimal('1.0'),
        regex_id="test_pattern"
    )
    
    return nfa