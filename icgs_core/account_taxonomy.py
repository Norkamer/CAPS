"""
AccountTaxonomy - Fonction taxonomique historisée avec UTF-32 - VERSION CORRIGÉE

Module implémentant la fonction de classification historisée selon blueprint ICGS:
f(compte_id, transaction_number) → caractère UTF-32

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
    
    CORRECTION: Version simplifiée et robuste des algorithmes
    """
    
    def __init__(self, start_character: int = 0x41):  # Commence à 'A'
        self.taxonomy_history: List[TaxonomySnapshot] = []
        self.account_registry: Set[str] = set()
        self.next_character: int = start_character
        
        # Métriques performance et validation
        self.stats = {
            'updates_count': 0,
            'queries_count': 0,
            'collisions_resolved': 0,
            'auto_assignments': 0,
            'max_accounts_per_transaction': 0
        }
    
    def update_taxonomy(self, accounts: Dict[str, Optional[str]], transaction_num: int) -> Dict[str, str]:
        """
        Met à jour taxonomie pour transaction donnée avec auto-assignment
        CORRECTION: Logique simplifiée et correcte
        """
        import time
        
        # Validation numéro transaction croissant pour cohérence historique
        if self.taxonomy_history and transaction_num <= self.taxonomy_history[-1].transaction_num:
            raise ValueError(f"Transaction number must be strictly increasing: {transaction_num} <= {self.taxonomy_history[-1].transaction_num}")
        
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
                # Auto-assignment nécessaire
                auto_assign_accounts.append(account_id)
                self.stats['auto_assignments'] += 1
            else:
                # Validation caractère demandé
                if not self._is_valid_utf32_character(requested_char):
                    raise ValueError(f"Invalid UTF-32 character: {requested_char} for account {account_id}")
                
                # Détection collision dans cette transaction seulement
                if requested_char in requested_chars:
                    raise ValueError(f"Character collision in transaction {transaction_num}: {requested_char} requested by {account_id} and {requested_chars[requested_char]}")
                
                requested_chars[requested_char] = account_id
                new_mapping[account_id] = requested_char
        
        # Phase 2: Auto-assignment pour comptes sans mapping
        used_chars_in_transaction = set(requested_chars.keys())
        
        # CORRECTION: Collecter tous les caractères utilisés historiquement
        all_historical_chars = set()
        for snapshot in self.taxonomy_history:
            all_historical_chars.update(snapshot.account_mappings.values())
        
        for account_id in auto_assign_accounts:
            # Si compte déjà existe, préserver mapping précédent
            if account_id in previous_mapping:
                assigned_char = previous_mapping[account_id]
            else:
                # Nouveau compte - auto-assignment avec évitement historique complet
                all_used_chars = used_chars_in_transaction | all_historical_chars
                assigned_char = self._auto_assign_character(all_used_chars)
                used_chars_in_transaction.add(assigned_char)
            
            new_mapping[account_id] = assigned_char
        
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
        CORRECTION: Version simplifiée et correcte
        """
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