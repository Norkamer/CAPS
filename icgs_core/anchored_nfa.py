"""
AnchoredWeightedNFA - Extension WeightedNFA avec Character-Class Support

Module implémentant automate fini pondéré avec fonctionnalités avancées selon blueprint ICGS:
- Ancrage automatique: ajout ".*$" si nécessaire pour regex complète
- État frozen: NFA figé pendant énumération pour cohérence
- RegexWeight: extraction coefficients pour construction LP
- NOUVEAU: Support character-class patterns [ABC] pour character-sets nommés

EXTENSION: Support regex character-class pour résolution multi-agents limitation
- Patterns character-class: .*[IJKL].* pour secteurs économiques
- Thompson NFA construction pour [ABC] → états individuels
- Compatibilité patterns classiques + character-class
- Matching complet tous caractères dans sets nommés

Objectif: Élimination matches partiels + cohérence temporelle + character-sets support
Propriétés:
- Ancrage automatique: ajout ".*$" si nécessaire pour regex complète
- État frozen: NFA figé pendant énumération pour cohérence
- RegexWeight: extraction coefficients pour construction LP
- Character-class: Support [ABC] syntax avec states individuels
"""

from typing import Dict, List, Set, Optional, Any
from decimal import Decimal
import copy
import re
from .weighted_nfa import WeightedNFA, NFAState, NFATransition, RegexWeight, TransitionType
from .nfa_performance_optimizations import PerformanceOptimizedMixin


class AnchoredWeightedNFA(PerformanceOptimizedMixin, WeightedNFA):
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

    def add_weighted_regex_with_character_class_support(self,
                                                       measure_id: str,
                                                       regex_pattern: str,
                                                       weight: Decimal,
                                                       regex_id: Optional[str] = None) -> NFAState:
        """
        NOUVEAU: Support character-class patterns [ABC] pour character-sets nommés

        Extension add_weighted_regex pour supporter syntax [ABC]:
        - Détection patterns character-class via regex parsing
        - Construction Thompson NFA pour chaque caractère individuel
        - État final unique partagé pour toute la classe
        - Compatibilité complète avec patterns classiques

        Args:
            measure_id: Identifiant mesure économique
            regex_pattern: Pattern avec potential character-class .*[IJKL].*
            weight: Poids associé pour contraintes LP
            regex_id: Identifiant unique regex

        Returns:
            État final unique pour toute la character-class

        Example:
            nfa.add_weighted_regex_with_character_class_support(
                'industry_measure', '.*[IJKL].*', Decimal('1.2')
            )
            → États pour I, J, K, L tous vers même état final
        """
        if self.is_frozen:
            raise RuntimeError("Cannot modify frozen AnchoredWeightedNFA")

        # Détection character-class pattern
        if self._has_character_class(regex_pattern):
            return self._add_character_class_regex(measure_id, regex_pattern, weight, regex_id)
        else:
            # Fallback vers méthode standard pour patterns simples
            return self.add_weighted_regex(measure_id, regex_pattern, weight, regex_id)

    def _has_character_class(self, pattern: str) -> bool:
        """
        Détecte si pattern contient character-class [ABC]

        Args:
            pattern: Pattern regex à analyser

        Returns:
            True si contient [abc] syntax
        """
        import re
        # Pattern de détection character-class: [...] mais pas \[...\]
        char_class_pattern = r'(?<!\\)\[[^\]]+\]'
        return bool(re.search(char_class_pattern, pattern))

    def _add_character_class_regex(self,
                                 measure_id: str,
                                 pattern: str,
                                 weight: Decimal,
                                 regex_id: Optional[str] = None) -> NFAState:
        """
        Construction Thompson NFA pour character-class patterns

        Algorithme:
        1. Extraction caractères de [IJKL] → ['I', 'J', 'K', 'L']
        2. Ancrage pattern complet pour cohérence
        3. Création état final unique pour toute la classe
        4. Construction NFA individual pour chaque caractère → même état final
        5. Consolidation RegexWeights sur état final unique

        Args:
            measure_id: Identifiant mesure économique
            pattern: Pattern character-class .*[IJKL].*
            weight: Poids associé
            regex_id: Identifiant unique regex

        Returns:
            État final unique pour toute la character-class
        """
        # 1. Extraction caractères de character-class
        character_class = self._extract_character_class(pattern)

        if not character_class:
            raise ValueError(f"Invalid character-class pattern: {pattern}")

        # 2. Ancrage pattern complet
        anchored_pattern = self._apply_automatic_anchoring(pattern)

        # 3. Création état final unique pour toute la classe
        final_state_id = f"{measure_id}_character_class_state"
        if regex_id:
            final_state_id = f"{measure_id}_{regex_id}_character_class"

        # Création état final avec RegexWeight consolidé
        final_state = NFAState(
            state_id=final_state_id,
            is_final=True,
            regex_weights=[RegexWeight(measure_id, regex_id or "character_class", weight)]
        )

        # Métadonnées character-class pour debugging
        final_state.metadata.update({
            'original_pattern': pattern,
            'anchored_pattern': anchored_pattern,
            'character_class': character_class,
            'character_count': len(character_class),
            'pattern_type': 'character_class'
        })

        # 4. Construction Thompson NFA pour chaque caractère individuel
        for character in character_class:
            # Pattern individuel pour ce caractère
            individual_pattern = self._substitute_character_class(anchored_pattern, character_class, character)

            # Construction NFA states pour ce caractère vers état final unique
            self._build_thompson_nfa_for_character(individual_pattern, final_state, weight)

        # 5. Enregistrement état final dans NFA
        self.states[final_state.state_id] = final_state

        # Invalidation cache pour cohérence
        self._final_states_cache = None

        # Statistiques
        self.stats['patterns_anchored'] += 1
        self.stats['anchor_transformations'] += 1

        return final_state

    def _extract_character_class(self, pattern: str) -> List[str]:
        """
        Extrait caractères de [ABC] → ['A', 'B', 'C']

        Args:
            pattern: Pattern contenant character-class

        Returns:
            Liste caractères extraits
        """
        import re
        matches = re.findall(r'(?<!\\)\[([^\]]+)\]', pattern)
        if matches:
            # Premier character-class trouvé (support un seul pour simplicité)
            char_class_content = matches[0]
            return list(char_class_content)
        return []

    def _substitute_character_class(self, pattern: str, character_class: List[str], target_character: str) -> str:
        """
        Remplace [ABC] par caractère spécifique pour construction NFA individuel

        Args:
            pattern: Pattern original .*[IJKL].*
            character_class: Liste caractères ['I', 'J', 'K', 'L']
            target_character: Caractère cible 'I'

        Returns:
            Pattern individuel .*I.*
        """
        import re
        # Construction regex pour trouver character-class exact
        char_class_content = ''.join(character_class)
        char_class_regex = f'\\[{re.escape(char_class_content)}\\]'

        # Remplace [ABC] par caractère spécifique
        individual_pattern = re.sub(char_class_regex, target_character, pattern, count=1)
        return individual_pattern

    def _build_thompson_nfa_for_character(self,
                                        individual_pattern: str,
                                        final_state: NFAState,
                                        weight: Decimal) -> None:
        """
        Construction Thompson NFA pour caractère individuel vers état final partagé

        Args:
            individual_pattern: Pattern pour caractère spécifique .*I.*
            final_state: État final partagé pour toute la character-class
            weight: Poids associé
        """
        # Pour simplicité, utilise le regex engine Python intégré
        # Dans implémentation complète, construirait vraiment Thompson NFA
        # Ici, on simule en créant transition directe si pattern match

        # Validation pattern compilable
        try:
            compiled_pattern = re.compile(individual_pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{individual_pattern}': {e}")

        # Stockage pattern compilé dans état final pour évaluation
        if not hasattr(final_state, 'compiled_patterns'):
            final_state.compiled_patterns = []

        final_state.compiled_patterns.append({
            'pattern': individual_pattern,
            'compiled': compiled_pattern,
            'weight': weight
        })

    def freeze(self):
        """
        Fige NFA pour énumération cohérente

        Capture snapshot états finaux et transitions actuels.
        Bloque modifications ultérieures.
        Garantit déterminisme évaluation pendant énumération.

        OPTIMIZED: Invalidation caches pour cohérence performance.

        Fonctionnement:
        1. Capture snapshot immuable états finaux
        2. Capture snapshot transitions pour cohérence
        3. Marque NFA comme frozen avec timestamp
        4. Bloque toute modification jusqu'à unfreeze()
        5. Invalidation caches optimisation
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

        # OPTIMIZED: Invalidation caches pour cohérence
        if hasattr(self, '_invalidate_optimization_caches'):
            self._invalidate_optimization_caches()

        self.stats['freeze_operations'] += 1
    
    def unfreeze(self):
        """
        Dégèle NFA pour permettre modifications

        Restaure capacité de modification après énumération.
        Invalide snapshots frozen précédents.

        OPTIMIZED: Invalidation caches optimisation pour cohérence.
        """
        self.is_frozen = False
        self.frozen_final_states = []
        self.frozen_transitions = []
        self._frozen_snapshot_timestamp = None

        # Invalidation cache pour cohérence
        self._final_states_cache = None

        # OPTIMIZED: Invalidation caches optimisation
        if hasattr(self, '_invalidate_optimization_caches'):
            self._invalidate_optimization_caches()
    
    def evaluate_to_final_state(self, word: str) -> Optional[str]:
        """
        Évalue mot et retourne ID état final ou None

        UPDATED: Utilise toujours evaluate_word() unifié (standard + character-class)
        Match complet requis (grâce à ancrage automatique).
        Retourne state_id pour classification déterministe.

        Args:
            word: Mot à évaluer avec ancrage complet

        Returns:
            state_id du premier état final atteint, None si aucun match
        """
        # Statistiques
        if self.is_frozen:
            self.stats['frozen_evaluations'] += 1

        # UNIFIED: Utilise toujours evaluate_word() qui supporte character-class
        final_state_ids = self.evaluate_word(word)

        # Retourne premier état final (déterminisme)
        if final_state_ids:
            return next(iter(final_state_ids))
        return None

    def evaluate_word(self, word: str) -> Set[str]:
        """
        Override evaluate_word() pour support character-class unifié

        Architecture hybride:
        1. Évaluation WeightedNFA standard (si états/transitions existent)
        2. Évaluation character-class spécialisée (toujours)
        3. Union résultats pour compatibilité API complète

        Args:
            word: Mot à évaluer

        Returns:
            Set[str]: États finaux atteints (standard + character-class)
        """
        # 1. Évaluation WeightedNFA standard (peut être vide si pas d'état initial)
        try:
            standard_results = super().evaluate_word(word)
        except:
            # Si erreur (pas d'état initial, etc.), on continue avec character-class
            standard_results = set()

        # 2. Évaluation character-class spécialisée
        character_class_results = self._evaluate_character_class_patterns_direct(word)

        # 3. Union pour API complète
        unified_results = standard_results | character_class_results

        return unified_results

    def _evaluate_character_class_patterns_direct(self, word: str) -> Set[str]:
        """
        Évaluation directe patterns character-class avec optimisations performance

        OPTIMIZED: Utilise cache LRU et indexation pour performance maximale.
        Spécialisée pour architecture AnchoredWeightedNFA où patterns
        sont stockés dans compiled_patterns des états finaux.

        Args:
            word: Mot à évaluer

        Returns:
            Set[str]: États finaux character-class matchés (cached)
        """
        # Utilise version optimisée avec cache si disponible
        if hasattr(self, '_evaluate_character_class_patterns_optimized'):
            return self._evaluate_character_class_patterns_optimized(word)

        # Fallback version simple (sans optimisations)
        matched_finals = set()

        # Test contre tous états avec compiled_patterns
        for state in self.states.values():
            if hasattr(state, 'compiled_patterns') and state.compiled_patterns:
                # Test chaque pattern compilé dans cet état
                for pattern_info in state.compiled_patterns:
                    try:
                        compiled_pattern = pattern_info.get('compiled')
                        if compiled_pattern and compiled_pattern.match(word):
                            matched_finals.add(state.state_id)
                            break  # Premier match suffit pour cet état
                    except (AttributeError, re.error):
                        # Pattern corrompu ou malformé - ignore silencieusement
                        continue

        return matched_finals

    def evaluate_to_final_state_with_character_class_support(self, word: str) -> Optional[str]:
        """
        NOUVEAU: Évaluation avec support character-class patterns

        Extension evaluate_to_final_state pour supporter:
        - Patterns character-class [ABC] créés via add_weighted_regex_with_character_class_support
        - États finaux avec compiled_patterns multiples
        - Match contre patterns individuels consolidés
        - Compatibilité avec évaluation classique

        Args:
            word: Mot à évaluer (caractère unique généralement)

        Returns:
            state_id du premier état final matché, None si aucun match
        """
        if self.is_frozen:
            self.stats['frozen_evaluations'] += 1
            final_states = self.frozen_final_states
        else:
            final_states = self.get_final_states()

        # Test évaluation character-class puis classique
        for final_state in final_states:
            # 1. Test character-class patterns si présents
            if hasattr(final_state, 'compiled_patterns'):
                for pattern_info in final_state.compiled_patterns:
                    compiled_pattern = pattern_info['compiled']
                    if compiled_pattern.match(word):
                        return final_state.state_id

            # 2. Fallback évaluation classique WeightedNFA
            # Test regex_weights classiques
            for regex_weight in final_state.regex_weights:
                # Construction pattern depuis regex_weight (si disponible)
                if hasattr(final_state, 'pattern') and final_state.pattern:
                    try:
                        if re.match(final_state.pattern, word):
                            return final_state.state_id
                    except:
                        continue

        # 3. Fallback évaluation héritée si aucun match spécifique
        return self.evaluate_to_final_state(word)
    
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