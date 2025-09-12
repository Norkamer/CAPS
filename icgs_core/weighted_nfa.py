"""
WeightedNFA - Automate Fini Non-déterministe Pondéré

Implémentation d'un NFA avec support des poids regex selon blueprint ICGS.
Base pour AnchoredWeightedNFA avec fonctionnalités avancées.

Fonctionnalités:
- États et transitions avec support regex
- Poids associés aux regex (RegexWeight)
- Évaluation de mots avec classification états finaux
- Construction dynamique d'automate depuis patterns
- Support expressions régulières complètes (via module regex)

Complexité:
- Construction: O(R × S) où R=regex, S=états moyens par regex
- Évaluation: O(M × T) où M=longueur mot, T=transitions actives moyennes
"""

import re
from typing import Dict, List, Set, Optional, Any, Iterator, Tuple
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class RegexWeight:
    """
    Poids associé à un pattern regex pour construction contraintes LP
    
    Propriétés:
    - measure_id: Identifiant mesure économique (ex: "debit_agri")
    - regex_id: Identifiant unique regex dans mesure
    - weight: Coefficient numérique pour contraintes LP (Decimal pour précision)
    """
    measure_id: str
    regex_id: str
    weight: Decimal
    
    def __post_init__(self):
        """Validation des paramètres"""
        if not self.measure_id:
            raise ValueError("measure_id cannot be empty")
        if not self.regex_id:
            raise ValueError("regex_id cannot be empty")
        if self.weight is None:
            raise ValueError("weight cannot be None")


class TransitionType(Enum):
    """Types de transitions NFA pour debugging et optimisation"""
    EPSILON = "epsilon"          # Transition epsilon (ε)
    CHARACTER = "character"      # Transition sur caractère spécifique
    REGEX_MATCH = "regex_match"  # Transition via match regex


@dataclass
class NFATransition:
    """
    Transition dans automate NFA
    
    Représente une transition from_state → to_state sur condition donnée
    """
    from_state: str
    to_state: str
    condition: Optional[str]  # None pour epsilon, caractère ou regex pattern
    transition_type: TransitionType
    regex_weight: Optional[RegexWeight] = None  # Associé si transition regex
    
    def matches(self, symbol: str) -> bool:
        """Teste si transition applicable pour symbole donné"""
        if self.transition_type == TransitionType.EPSILON:
            return False  # Epsilon transitions gérées séparément
        elif self.transition_type == TransitionType.CHARACTER:
            return symbol == self.condition
        elif self.transition_type == TransitionType.REGEX_MATCH:
            if self.condition:
                try:
                    return bool(re.match(self.condition, symbol))
                except re.error:
                    return False
        return False


@dataclass
class NFAState:
    """
    État dans automate NFA avec métadonnées
    
    Propriétés:
    - state_id: Identifiant unique état
    - is_final: Indique si état d'acceptation
    - regex_weights: Poids regex associés (pour états finaux)
    - metadata: Données additionnelles pour debugging
    """
    state_id: str
    is_final: bool = False
    regex_weights: List[RegexWeight] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.regex_weights is None:
            self.regex_weights = []
        if self.metadata is None:
            self.metadata = {}


class WeightedNFA:
    """
    Automate Fini Non-déterministe avec support poids regex
    
    Architecture:
    - États stockés avec métadonnées complètes
    - Transitions avec types différenciés pour optimisation
    - Evaluation avec gestion non-déterminisme
    - Support construction dynamique depuis regex patterns
    
    Note: Classe de base - AnchoredWeightedNFA hérite pour fonctionnalités avancées
    """
    
    def __init__(self, name: str = "WeightedNFA"):
        self.name = name
        self.states: Dict[str, NFAState] = {}
        self.transitions: List[NFATransition] = []
        self.initial_state_id: Optional[str] = None
        self.alphabet: Set[str] = set()
        
        # Indexation pour performance
        self._transitions_from: Dict[str, List[NFATransition]] = {}
        self._transitions_to: Dict[str, List[NFATransition]] = {}
        self._final_states_cache: Optional[List[NFAState]] = None
        
        # Métriques construction et performance
        self.stats = {
            'states_count': 0,
            'transitions_count': 0,
            'regex_patterns_added': 0,
            'evaluations_performed': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def add_state(self, state_id: str, is_final: bool = False, 
                  regex_weights: Optional[List[RegexWeight]] = None,
                  metadata: Optional[Dict[str, Any]] = None) -> NFAState:
        """
        Ajoute état au NFA avec validation unicité
        
        Args:
            state_id: Identifiant unique état
            is_final: Si état d'acceptation
            regex_weights: Poids regex associés (états finaux)
            metadata: Données additionnelles
            
        Returns:
            NFAState créé
            
        Raises:
            ValueError: Si state_id déjà existe
        """
        if state_id in self.states:
            raise ValueError(f"State {state_id} already exists in NFA {self.name}")
        
        state = NFAState(
            state_id=state_id,
            is_final=is_final,
            regex_weights=regex_weights or [],
            metadata=metadata or {}
        )
        
        self.states[state_id] = state
        self.stats['states_count'] += 1
        
        # Invalidation cache
        self._final_states_cache = None
        
        return state
    
    def add_transition(self, from_state_id: str, to_state_id: str, 
                      condition: Optional[str] = None,
                      transition_type: TransitionType = TransitionType.CHARACTER,
                      regex_weight: Optional[RegexWeight] = None) -> NFATransition:
        """
        Ajoute transition entre états avec validation existence
        
        Args:
            from_state_id: État source
            to_state_id: État destination  
            condition: Condition transition (None pour epsilon)
            transition_type: Type de transition
            regex_weight: Poids si transition regex
            
        Returns:
            NFATransition créée
            
        Raises:
            ValueError: Si états source/destination n'existent pas
        """
        # Validation existence états
        if from_state_id not in self.states:
            raise ValueError(f"Source state {from_state_id} not found in NFA {self.name}")
        if to_state_id not in self.states:
            raise ValueError(f"Target state {to_state_id} not found in NFA {self.name}")
        
        # Création transition
        transition = NFATransition(
            from_state=from_state_id,
            to_state=to_state_id,
            condition=condition,
            transition_type=transition_type,
            regex_weight=regex_weight
        )
        
        self.transitions.append(transition)
        self.stats['transitions_count'] += 1
        
        # Mise à jour index pour performance
        self._transitions_from.setdefault(from_state_id, []).append(transition)
        self._transitions_to.setdefault(to_state_id, []).append(transition)
        
        # Mise à jour alphabet si caractère spécifique
        if condition and transition_type == TransitionType.CHARACTER:
            self.alphabet.add(condition)
        
        return transition
    
    def set_initial_state(self, state_id: str):
        """
        Définit état initial avec validation existence
        
        Args:
            state_id: Identifiant état initial
            
        Raises:
            ValueError: Si état n'existe pas
        """
        if state_id not in self.states:
            raise ValueError(f"Initial state {state_id} not found in NFA {self.name}")
        
        self.initial_state_id = state_id
    
    def get_final_states(self) -> List[NFAState]:
        """Retourne tous états finaux avec cache pour performance"""
        if self._final_states_cache is None:
            self._final_states_cache = [
                state for state in self.states.values() if state.is_final
            ]
        return self._final_states_cache
    
    def evaluate_word(self, word: str) -> Set[str]:
        """
        Évalue mot et retourne ensemble états finaux atteints
        
        CORRECTION: Algorithme adapté pour regex patterns complets
        1. Démarrage depuis état initial avec epsilon-closure  
        2. Test direct transitions regex sur mot complet
        3. Fallback vers évaluation caractère par caractère pour transitions simples
        
        Args:
            word: Mot à évaluer
            
        Returns:
            Set d'identifiants états finaux atteints
        """
        self.stats['evaluations_performed'] += 1
        
        if self.initial_state_id is None:
            return set()
        
        # Configuration courante: ensemble états actifs
        current_states = self._epsilon_closure({self.initial_state_id})
        
        # CORRECTION: Traitement spécial pour transitions regex
        final_states_found = set()
        
        # Test direct regex patterns sur mot complet depuis états initiaux
        for state_id in current_states:
            transitions = self._transitions_from.get(state_id, [])
            
            for transition in transitions:
                if transition.transition_type == TransitionType.REGEX_MATCH:
                    if transition.condition and self._matches_regex_pattern(word, transition.condition):
                        final_states_found.add(transition.to_state)
                        
                        # Si état destination est final, l'ajouter
                        if self.states[transition.to_state].is_final:
                            final_states_found.add(transition.to_state)
        
        # Traitement caractère par caractère pour transitions CHARACTER/EPSILON
        for symbol in word:
            next_states = set()
            
            for state_id in current_states:
                transitions = self._transitions_from.get(state_id, [])
                
                for transition in transitions:
                    if (transition.transition_type == TransitionType.CHARACTER and 
                        transition.matches(symbol)):
                        next_states.add(transition.to_state)
            
            current_states = self._epsilon_closure(next_states)
        
        # Combinaison états finaux des deux méthodes
        final_state_ids = final_states_found | {
            state_id for state_id in current_states 
            if self.states[state_id].is_final
        }
        
        return final_state_ids
    
    def _matches_regex_pattern(self, word: str, pattern: str) -> bool:
        """
        Teste si mot matche pattern regex complet
        
        Args:
            word: Mot à tester
            pattern: Pattern regex complet
            
        Returns:
            True si match, False sinon
        """
        try:
            return bool(re.match(pattern, word))
        except re.error:
            return False
    
    def add_weighted_regex_simple(self, measure_id: str, regex_pattern: str, 
                                 weight: Decimal, regex_id: Optional[str] = None) -> NFAState:
        """
        Ajoute pattern regex avec poids associé - version simplifiée
        
        Crée automate simple: initial → regex_match → final
        Version basique - AnchoredWeightedNFA fournira version avancée
        
        Args:
            measure_id: Identifiant mesure économique
            regex_pattern: Pattern regex
            weight: Poids associé
            regex_id: Identifiant regex (généré si None)
            
        Returns:
            État final créé avec RegexWeight associé
        """
        if regex_id is None:
            regex_id = f"regex_{len(self.transitions)}"
        
        # Validation pattern regex
        try:
            re.compile(regex_pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{regex_pattern}': {e}")
        
        # Création RegexWeight
        regex_weight = RegexWeight(
            measure_id=measure_id,
            regex_id=regex_id,
            weight=weight
        )
        
        # États pour ce pattern
        initial_id = f"{measure_id}_{regex_id}_initial"
        final_id = f"{measure_id}_{regex_id}_final"
        
        # Ajout états si pas d'état initial défini
        if self.initial_state_id is None:
            self.add_state(initial_id, is_final=False)
            self.set_initial_state(initial_id)
        else:
            initial_id = self.initial_state_id
        
        # État final avec poids
        final_state = self.add_state(
            final_id, 
            is_final=True,
            regex_weights=[regex_weight],
            metadata={'pattern': regex_pattern, 'measure': measure_id}
        )
        
        # Transition regex
        self.add_transition(
            initial_id,
            final_id,
            regex_pattern,
            TransitionType.REGEX_MATCH,
            regex_weight
        )
        
        self.stats['regex_patterns_added'] += 1
        
        return final_state
    
    def get_regex_weights_for_state(self, state_id: str) -> List[RegexWeight]:
        """Récupère poids regex associés à un état donné"""
        if state_id in self.states:
            return self.states[state_id].regex_weights.copy()
        return []
    
    def validate_nfa_structure(self) -> List[str]:
        """
        Validation structure NFA pour tests académiques
        
        Vérifie:
        - États initial et finaux définis
        - Transitions cohérentes (états source/dest existent)
        - Pas de doublons transitions
        - Regex patterns valides
        
        Returns:
            Liste erreurs détectées (vide si structure valide)
        """
        errors = []
        
        # Vérification état initial
        if self.initial_state_id is None:
            errors.append("No initial state defined")
        elif self.initial_state_id not in self.states:
            errors.append(f"Initial state {self.initial_state_id} not found in states")
        
        # Vérification états finaux
        final_states = self.get_final_states()
        if len(final_states) == 0:
            errors.append("No final states defined")
        
        # Vérification transitions
        transition_signatures = set()
        for transition in self.transitions:
            # États existent
            if transition.from_state not in self.states:
                errors.append(f"Transition from unknown state: {transition.from_state}")
            if transition.to_state not in self.states:
                errors.append(f"Transition to unknown state: {transition.to_state}")
            
            # Pas de doublons
            signature = (transition.from_state, transition.to_state, 
                        transition.condition, transition.transition_type)
            if signature in transition_signatures:
                errors.append(f"Duplicate transition: {signature}")
            transition_signatures.add(signature)
            
            # Regex valides
            if (transition.transition_type == TransitionType.REGEX_MATCH 
                and transition.condition):
                try:
                    re.compile(transition.condition)
                except re.error as e:
                    errors.append(f"Invalid regex in transition: {transition.condition} - {e}")
        
        return errors
    
    # Méthodes privées utilitaires
    
    def _epsilon_closure(self, states: Set[str]) -> Set[str]:
        """
        Calcule epsilon-closure d'ensemble d'états
        
        Algorithme standard: DFS depuis états donnés via transitions epsilon
        
        Args:
            states: États de départ
            
        Returns:
            Ensemble états atteignables via epsilon-transitions
        """
        closure = set(states)
        stack = list(states)
        
        while stack:
            current = stack.pop()
            
            # Transitions epsilon depuis état courant
            epsilon_transitions = [
                t for t in self._transitions_from.get(current, [])
                if t.transition_type == TransitionType.EPSILON
            ]
            
            for transition in epsilon_transitions:
                if transition.to_state not in closure:
                    closure.add(transition.to_state)
                    stack.append(transition.to_state)
        
        return closure
    
    def __repr__(self) -> str:
        """Représentation string pour debugging"""
        return (f"WeightedNFA(name='{self.name}', states={len(self.states)}, "
                f"transitions={len(self.transitions)}, "
                f"final_states={len(self.get_final_states())})")


# Classes utilitaires pour debugging et tests

def create_simple_test_nfa() -> WeightedNFA:
    """
    Crée NFA simple pour tests unitaires
    
    Structure: q0 -'a'-> q1 -'b'-> q2(final)
    """
    nfa = WeightedNFA("test_nfa")
    
    nfa.add_state("q0")
    nfa.add_state("q1") 
    nfa.add_state("q2", is_final=True)
    
    nfa.set_initial_state("q0")
    
    nfa.add_transition("q0", "q1", "a", TransitionType.CHARACTER)
    nfa.add_transition("q1", "q2", "b", TransitionType.CHARACTER)
    
    return nfa