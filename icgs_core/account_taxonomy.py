"""
AccountTaxonomy - Fonction taxonomique historisée avec Character-Sets Support

Module implémentant la fonction de classification historisée selon blueprint ICGS:
f(compte_id, transaction_number) → caractère UTF-32

EXTENSION: Support character-sets nommés pour résolution limitation multi-agents
- Character-sets par secteur économique avec allocation automatique
- Configuration figée après première transaction
- Backward compatibility totale avec architecture existante

Propriétés mathématiques garanties:
- Historisation: évolution temporelle de classification des comptes
- Alphabet UTF-32: évite collisions jusqu'à 1M+ comptes
- Déterminisme: même état DAG → même mapping
- Complexité: O(log n) récupération, O(n×t) stockage
"""

from typing import Dict, List, Set, Optional, Tuple
import bisect
from decimal import Decimal
from dataclasses import dataclass

# Import character-set manager pour support secteurs économiques
from .character_set_manager import NamedCharacterSetManager


@dataclass
class TaxonomySnapshot:
    """Snapshot taxonomie à transaction donnée pour historisation"""
    transaction_num: int
    account_mappings: Dict[str, str]  # account_id -> character
    timestamp: float
    
    def __lt__(self, other):
        """Comparaison pour bisect sur transaction_num"""
        return self.transaction_num < other.transaction_num


class AccountTaxonomy:
    """
    Fonction taxonomique historisée: f(compte_id, transaction_number) → caractère

    EXTENSION: Support character-sets nommés pour résolution multi-agents limitation
    - Mode classique: allocation séquentielle UTF-32 (backward compatibility)
    - Mode character-sets: allocation automatique par secteur économique
    """

    def __init__(self, character_set_manager: Optional[NamedCharacterSetManager] = None,
                 start_character: int = 0x41):  # Commence à 'A'
        # Architecture existante préservée (backward compatibility)
        self.taxonomy_history: List[TaxonomySnapshot] = []
        self.account_registry: Set[str] = set()
        self.next_character: int = start_character

        # NOUVEAU: Support character-sets nommés
        self.character_set_manager = character_set_manager
        self.use_character_sets = character_set_manager is not None

        # Métriques performance et validation étendues
        self.stats = {
            'updates_count': 0,
            'queries_count': 0,
            'collisions_resolved': 0,
            'auto_assignments': 0,
            'max_accounts_per_transaction': 0,
            # Nouvelles métriques character-sets
            'sector_allocations': 0,
            'character_set_mode': self.use_character_sets,
            'freeze_transaction': None
        }
    
    def update_taxonomy(self, accounts: Dict[str, Optional[str]], transaction_num: int) -> Dict[str, str]:
        """
        Met à jour taxonomie pour transaction donnée avec auto-assignment
        CORRECTION: Logique simplifiée et correcte
        """
        import time
        
        # Validation numéro transaction croissant pour cohérence historique
        # Exception: Permet transaction -1 pour initialisation si liste vide
        if self.taxonomy_history:
            if transaction_num <= self.taxonomy_history[-1].transaction_num:
                raise ValueError(f"Transaction number must be strictly increasing: {transaction_num} <= {self.taxonomy_history[-1].transaction_num}")
        elif transaction_num < -1:
            raise ValueError(f"Invalid initialization transaction number: {transaction_num} (must be >= -1)")
        
        # Récupération mapping précédent pour héritage SEULEMENT des comptes existants
        previous_mapping = {}
        if self.taxonomy_history:
            previous_mapping = self.taxonomy_history[-1].account_mappings.copy()
        
        # CORRECTION: Nouveau mapping contient SEULEMENT les comptes de cette transaction
        # mais avec héritage des mappings précédents pour comptes déjà existants
        new_mapping = {}
        
        # Phase 1: Validation et préparation
        requested_chars = {}  # character -> account_id pour détecter collisions
        auto_assign_accounts = []
        
        for account_id, requested_char in accounts.items():
            self.account_registry.add(account_id)
            
            if requested_char is None:
                raise ValueError(f"Explicit character mapping required for account '{account_id}'. Auto-assignment disabled.")
            else:
                # Validation caractère demandé
                if not self._is_valid_utf32_character(requested_char):
                    raise ValueError(f"Invalid UTF-32 character: {requested_char} for account {account_id}")
                
                # Détection collision caractères dans même transaction
                if requested_char in requested_chars:
                    raise ValueError(f"Character collision detected: '{requested_char}' used by {account_id} and {requested_chars[requested_char]}")
                requested_chars[requested_char] = account_id
                new_mapping[account_id] = requested_char
        
        # Phase 2: Pas d'auto-assignment - tous les mappings sont explicites
        
        # CORRECTION: Héritage comptes précédents NON mentionnés dans cette transaction
        for prev_account, prev_char in previous_mapping.items():
            if prev_account not in new_mapping:
                new_mapping[prev_account] = prev_char
        
        # Phase 3: Création snapshot historique
        snapshot = TaxonomySnapshot(
            transaction_num=transaction_num,
            account_mappings=new_mapping,
            timestamp=time.time()
        )
        
        # Insertion ordonnée pour recherche dichotomique
        bisect.insort(self.taxonomy_history, snapshot)
        
        # Mise à jour métriques
        self.stats['updates_count'] += 1
        self.stats['max_accounts_per_transaction'] = max(
            self.stats['max_accounts_per_transaction'], 
            len(accounts)
        )
        
        # CORRECTION: Retourner seulement mappings des comptes de cette transaction
        result_mapping = {account_id: new_mapping[account_id] for account_id in accounts.keys()}
        return result_mapping

    def update_taxonomy_with_sectors(self,
                                   accounts_with_sectors: Dict[str, str],
                                   transaction_num: int) -> Dict[str, str]:
        """
        NOUVEAU: Mise à jour taxonomie avec secteurs économiques (character-sets)

        Args:
            accounts_with_sectors: Mapping account_id → secteur
                {
                    'ALICE_sink': 'AGRICULTURE',
                    'BOB_sink': 'INDUSTRY',
                    'CHARLIE_sink': 'INDUSTRY'  # Même secteur, caractère différent
                }
            transaction_num: Numéro transaction pour historisation

        Returns:
            Mapping account_id → caractère alloué

        Raises:
            RuntimeError: Si mode character-sets non activé
            ValueError: Si secteur non défini ou capacité dépassée
        """
        if not self.use_character_sets:
            # Fallback vers méthode classique
            accounts_mapping = {account_id: None for account_id in accounts_with_sectors.keys()}
            return self.update_taxonomy(accounts_mapping, transaction_num)

        import time

        # Validation numéro transaction croissant
        if self.taxonomy_history:
            if transaction_num <= self.taxonomy_history[-1].transaction_num:
                raise ValueError(f"Transaction number must be strictly increasing: {transaction_num}")

        # Récupération mapping précédent pour héritage
        previous_mapping = {}
        if self.taxonomy_history:
            previous_mapping = self.taxonomy_history[-1].account_mappings.copy()

        new_mapping = previous_mapping.copy()  # Héritage comptes précédents

        # Phase 1: Allocation automatique avec character-sets
        allocated_mappings = {}
        for account_id, sector_name in accounts_with_sectors.items():
            self.account_registry.add(account_id)

            if account_id not in new_mapping:  # Nouveau compte
                try:
                    allocated_char = self.character_set_manager.allocate_character_for_sector(sector_name)
                    new_mapping[account_id] = allocated_char
                    allocated_mappings[account_id] = allocated_char
                    self.stats['sector_allocations'] += 1

                except (ValueError, RuntimeError) as e:
                    raise ValueError(f"Échec allocation secteur '{sector_name}' pour compte '{account_id}': {e}")

        # Phase 2: Freeze après première transaction (transaction_num == 0)
        if transaction_num == 0 and self.character_set_manager:
            self.character_set_manager.freeze()
            self.stats['freeze_transaction'] = transaction_num

        # Phase 3: Création snapshot historique
        snapshot = TaxonomySnapshot(
            transaction_num=transaction_num,
            account_mappings=new_mapping,
            timestamp=time.time()
        )

        # Insertion ordonnée pour recherche dichotomique
        bisect.insort(self.taxonomy_history, snapshot)

        # Mise à jour métriques
        self.stats['updates_count'] += 1
        self.stats['max_accounts_per_transaction'] = max(
            self.stats['max_accounts_per_transaction'],
            len(accounts_with_sectors)
        )

        # Retourner seulement mappings des comptes de cette transaction
        return {account_id: new_mapping[account_id] for account_id in accounts_with_sectors.keys()}
    
    def get_character_mapping(self, account_id: str, transaction_num: int) -> Optional[str]:
        """
        Récupère mapping historique pour account à transaction donnée
        Utilise recherche dichotomique pour complexité O(log n)
        """
        self.stats['queries_count'] += 1
        
        if not self.taxonomy_history:
            return None
        
        # Recherche dichotomique du snapshot approprié
        target_snapshot = TaxonomySnapshot(transaction_num, {}, 0.0)
        insertion_point = bisect.bisect_right(self.taxonomy_history, target_snapshot)
        
        # Parcours depuis snapshot le plus récent approprié
        for i in range(insertion_point - 1, -1, -1):
            snapshot = self.taxonomy_history[i]
            if account_id in snapshot.account_mappings:
                return snapshot.account_mappings[account_id]
        
        # Account non trouvé dans historique
        return None
    
    def convert_path_to_word(self, path: List['Node'], transaction_num: int) -> str:
        """Convertit chemin DAG en mot pour évaluation NFA"""
        word_chars = []
        
        for node in path:
            # Extraction account_id depuis node DAG - utiliser node_id comme account_id
            account_id = getattr(node, 'account_id', None) or getattr(node, 'node_id', None)
            if not account_id:
                raise ValueError(f"Node without account_id or node_id in path: {node}")
            
            # Récupération mapping historique
            character = self.get_character_mapping(account_id, transaction_num)
            if character is None:
                raise ValueError(f"No character mapping found for account {account_id} at transaction {transaction_num}")
            
            word_chars.append(character)
        
        return ''.join(word_chars)
    
    def get_taxonomy_snapshot(self, transaction_num: int) -> Optional[TaxonomySnapshot]:
        """Récupère snapshot complet à transaction donnée pour debug/analyse"""
        target = TaxonomySnapshot(transaction_num, {}, 0.0)
        insertion_point = bisect.bisect_right(self.taxonomy_history, target)
        
        if insertion_point > 0:
            return self.taxonomy_history[insertion_point - 1]
        return None
    
    def validate_historical_consistency(self) -> List[str]:
        """
        Validation cohérence historique pour tests académiques
        CORRECTION: Version robuste
        """
        errors = []
        
        # Vérification ordre transactions
        for i in range(1, len(self.taxonomy_history)):
            if self.taxonomy_history[i].transaction_num <= self.taxonomy_history[i-1].transaction_num:
                errors.append(f"Non-increasing transaction numbers: {self.taxonomy_history[i-1].transaction_num} >= {self.taxonomy_history[i].transaction_num}")
        
        # Vérification collisions dans chaque snapshot
        for snapshot in self.taxonomy_history:
            char_to_accounts = {}
            for account_id, character in snapshot.account_mappings.items():
                if character in char_to_accounts:
                    errors.append(f"Character collision in transaction {snapshot.transaction_num}: {character} used by {account_id} and {char_to_accounts[character]}")
                else:
                    char_to_accounts[character] = account_id
        
        return errors
    
    # Méthodes privées d'implémentation - VERSION CORRIGÉE
    
    def _is_valid_utf32_character(self, char: str) -> bool:
        """Validation caractère UTF-32 selon spécifications blueprint"""
        if len(char) != 1:
            return False
        try:
            ord_val = ord(char)
            return 0x41 <= ord_val <= 0x10FFFF  # A-Z puis UTF-32 étendu
        except (TypeError, ValueError):
            return False
    
    def _auto_assign_character(self, used_chars: Set[str]) -> str:
        """
        Auto-assignment caractère avec évitement collisions
        CORRECTION: Utilise caractère neutre 'N' pour comptes selon demande utilisateur
        """
        # CORRECTION CRITIQUE: Caractère neutre pour comptes (pas d'effet regex)
        # Utilise 'N' comme caractère neutre qui n'affecte pas la plupart des regex
        neutral_char = 'N'
        
        if neutral_char not in used_chars:
            return neutral_char
        
        # Fallback: auto-assignment séquentiel si 'N' déjà utilisé
        while True:
            candidate = chr(self.next_character)
            self.next_character += 1
            
            # Vérification collision avec caractères utilisés dans cette transaction
            if candidate not in used_chars:
                return candidate
            
            # Protection contre boucle infinie
            if self.next_character > 0x10FFFF:
                raise RuntimeError("UTF-32 character space exhausted - critical system error")


# Node stub pour type hints - sera remplacé par vraie implémentation DAG
class Node:
    """Stub pour type hints - classe Node sera définie dans dag.py"""
    def __init__(self, account_id: str):
        self.account_id = account_id