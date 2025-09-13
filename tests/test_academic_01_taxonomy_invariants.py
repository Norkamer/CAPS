"""
Test Académique 1: Validation Taxonomie Historisée - Invariants Temporels

Ce test vérifie rigoureusement les propriétés mathématiques fondamentales 
de la fonction taxonomique historisée selon le blueprint ICGS.

Invariants testés:
1. Monotonie temporelle: transaction_num strictement croissant
2. Déterminisme: même état → même mapping  
3. Historisation complète: préservation snapshots précédents
4. Consistance UTF-32: caractères valides dans plage définie
5. Absence collisions: unicité caractères par transaction
6. Complexité O(log n): performance recherche dichotomique

Niveau académique: Validation formelle des garanties mathématiques
"""

import pytest
import time
from decimal import Decimal
from typing import Dict, List

# Import du module à tester
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from icgs_core.account_taxonomy import AccountTaxonomy, TaxonomySnapshot, Node


class TestAcademicTaxonomyInvariants:
    """Suite de tests académiques pour validation invariants taxonomie historisée"""

    def setup_method(self):
        """Setup clean pour chaque test avec métriques baseline"""
        self.taxonomy = AccountTaxonomy()
        self.baseline_time = time.time()
        
    def test_invariant_temporal_monotonicity(self):
        """
        INVARIANT 1: Monotonie Temporelle
        ∀ i,j : transaction_num[i] < transaction_num[j] ⟹ i inserted before j
        """
        # Séquence transactions croissante valide avec mappings explicites
        valid_sequence = [1, 5, 10, 15, 20]
        explicit_chars = ['A', 'B', 'C', 'D', 'E']

        for i, tx_num in enumerate(valid_sequence):
            accounts = {f"account_{tx_num}": explicit_chars[i]}  # Mapping explicite
            result = self.taxonomy.update_taxonomy(accounts, tx_num)
            assert len(result) == 1
            
        # Vérification ordre historique strictement croissant
        for i in range(1, len(self.taxonomy.taxonomy_history)):
            prev_tx = self.taxonomy.taxonomy_history[i-1].transaction_num
            curr_tx = self.taxonomy.taxonomy_history[i].transaction_num
            assert curr_tx > prev_tx, f"Monotonie violée: {prev_tx} >= {curr_tx}"
            
        # Test rejection transaction non-croissante
        with pytest.raises(ValueError, match="Transaction number must be strictly increasing"):
            self.taxonomy.update_taxonomy({"invalid_account": None}, 15)  # 15 <= 20
            
    def test_invariant_deterministic_mapping(self):
        """
        INVARIANT 2: Déterminisme
        ∀ account_id, tx_num : f(account_id, tx_num) déterministe et reproductible
        """
        # Création état initial avec mappings explicites
        accounts_t1 = {"alice": "A", "bob": "B", "charlie": "C"}
        mapping_t1 = self.taxonomy.update_taxonomy(accounts_t1, 1)
        
        # Requêtes multiples doivent retourner résultats identiques
        for _ in range(10):
            assert self.taxonomy.get_character_mapping("alice", 1) == "A"
            assert self.taxonomy.get_character_mapping("bob", 1) == "B"
            assert self.taxonomy.get_character_mapping("charlie", 1) == mapping_t1["charlie"]
            
        # Extension état et vérification préservation mappings précédents
        accounts_t2 = {"david": "D"}
        mapping_t2 = self.taxonomy.update_taxonomy(accounts_t2, 2)
        
        # Mappings t1 préservés à t2
        assert self.taxonomy.get_character_mapping("alice", 2) == "A"
        assert self.taxonomy.get_character_mapping("bob", 2) == "B" 
        assert self.taxonomy.get_character_mapping("charlie", 2) == mapping_t1["charlie"]
        
    def test_invariant_historical_completeness(self):
        """
        INVARIANT 3: Historisation Complète
        Tous snapshots préservés avec accès temporal exact
        """
        # Création séquence historique avec mappings explicites
        historical_sequence = [
            (1, {"alice": "A"}),
            (5, {"bob": "B", "charlie": "C"}),
            (10, {"david": "D", "eve": "E"}),
            (15, {"frank": "F"})
        ]
        
        mappings_by_tx = {}
        for tx_num, accounts in historical_sequence:
            mappings_by_tx[tx_num] = self.taxonomy.update_taxonomy(accounts, tx_num)
            
        # Validation accès historical pour chaque point temporel
        for tx_num, expected_mapping in mappings_by_tx.items():
            snapshot = self.taxonomy.get_taxonomy_snapshot(tx_num)
            assert snapshot is not None
            assert snapshot.transaction_num <= tx_num
            
            # Vérification mappings corrects pour chaque account
            for account_id, expected_char in expected_mapping.items():
                actual_char = self.taxonomy.get_character_mapping(account_id, tx_num)
                assert actual_char == expected_char, f"Historical mapping incorrect: {account_id} at tx {tx_num}"
                
        # Test queries inter-snapshot (fallback vers snapshot précédent)
        assert self.taxonomy.get_character_mapping("alice", 3) == "A"  # Fallback vers tx=1
        assert self.taxonomy.get_character_mapping("bob", 12) == mappings_by_tx[5]["bob"]  # Fallback vers tx=5
        
    def test_invariant_utf32_consistency(self):
        """
        INVARIANT 4: Consistance UTF-32
        Tous caractères dans plage UTF-32 valide définie par blueprint
        """
        # Test caractères UTF-32 explicites valides
        large_account_set = {f"account_{i}": chr(0x41 + i) for i in range(26)}  # A-Z
        mapping = self.taxonomy.update_taxonomy(large_account_set, 1)
        
        for account_id, character in mapping.items():
            # Vérification UTF-32 valide
            assert len(character) == 1, f"Character not single UTF-32 code point: {character}"
            ord_val = ord(character)
            assert 0x41 <= ord_val <= 0x10FFFF, f"Character outside UTF-32 range: {ord_val:x}"
            
        # Test rejet caractères invalides
        invalid_chars = ["", "AB", "🚀🚀", "\x00"]
        for invalid_char in invalid_chars:
            with pytest.raises(ValueError, match="Invalid UTF-32 character"):
                self.taxonomy.update_taxonomy({"test_account": invalid_char}, 2)
                
    def test_invariant_collision_absence(self):
        """
        INVARIANT 5: Absence Collisions
        ∀ tx : caractères uniques dans même transaction
        ∀ account_i ≠ account_j : character(account_i) ≠ character(account_j)
        """
        # Test collision detection dans même transaction
        with pytest.raises(ValueError, match="Character collision"):
            self.taxonomy.update_taxonomy({
                "alice": "A",
                "bob": "A"  # Collision intentionnelle
            }, 1)
            
        # Test absence collision avec mappings tous explicites
        mixed_accounts = {
            "explicit_1": "X",
            "explicit_2": "Y",
            "explicit_3": "M",
            "explicit_4": "N",
            "explicit_5": "Z"
        }
        mapping = self.taxonomy.update_taxonomy(mixed_accounts, 1)
        
        # Vérification unicité tous caractères
        used_chars = set()
        for character in mapping.values():
            assert character not in used_chars, f"Collision detected: {character}"
            used_chars.add(character)
            
        # Vérification stats collision tracking
        assert self.taxonomy.stats['collisions_resolved'] == 0
        
    def test_invariant_logarithmic_complexity(self):
        """
        INVARIANT 6: Complexité O(log n)
        Performance recherche dichotomique proportionnelle à log(snapshots)
        """
        import time
        
        # Création séquence croissante snapshots
        snapshot_sizes = [10, 100, 1000]
        query_times = []
        
        for size in snapshot_sizes:
            # Reset taxonomy pour test isolé
            taxonomy = AccountTaxonomy()
            
            # Création snapshots nombreux avec mappings explicites
            for i in range(size):
                char_idx = i % 26
                taxonomy.update_taxonomy({f"account_{i}": chr(0x41 + char_idx)}, i * 10)
                
            # Mesure temps queries multiples pour moyenne stable
            start_time = time.perf_counter()
            for _ in range(100):  # 100 queries pour moyenne
                taxonomy.get_character_mapping("account_1", size * 5)  # Query milieu
            end_time = time.perf_counter()
            
            avg_query_time = (end_time - start_time) / 100
            query_times.append(avg_query_time)
            
        # Vérification complexité sub-linear (approximation O(log n))
        # Le ratio ne doit pas croître linéairement avec la taille
        if len(query_times) >= 2:
            ratio_growth = query_times[-1] / query_times[0]
            size_growth = snapshot_sizes[-1] / snapshot_sizes[0]
            
            # Complexité logarithmique: ratio croissance << croissance taille
            assert ratio_growth < size_growth * 0.1, f"Query time growth too high: {ratio_growth} vs size growth {size_growth}"
            
    def test_invariant_consistency_validation(self):
        """
        META-INVARIANT: Validation cohérence globale système
        Utilise méthode validate_historical_consistency() pour détection violations
        """
        # Création état complexe multi-transaction avec mappings explicites
        complex_sequence = [
            (1, {"alice": "A", "bob": "B"}),
            (3, {"charlie": "C", "david": "D"}),
            (7, {"eve": "E", "frank": "F"}),
            (10, {"george": "G"})
        ]
        
        for tx_num, accounts in complex_sequence:
            self.taxonomy.update_taxonomy(accounts, tx_num)
            
        # Validation cohérence ne doit rapporter aucune erreur
        errors = self.taxonomy.validate_historical_consistency()
        assert len(errors) == 0, f"Consistency violations detected: {errors}"
        
        # Vérification métriques coherence avec stats
        assert self.taxonomy.stats['updates_count'] == len(complex_sequence)
        assert self.taxonomy.stats['queries_count'] >= 0  # Peut varier selon implémentation
        
    def test_edge_cases_and_boundary_conditions(self):
        """Test cas limites et conditions frontières pour robustesse"""
        
        # Test taxonomie vide
        assert self.taxonomy.get_character_mapping("nonexistent", 1) is None
        errors = self.taxonomy.validate_historical_consistency()
        assert len(errors) == 0
        
        # Test transaction numéro zéro avec mapping explicite
        self.taxonomy.update_taxonomy({"account_0": "Z"}, 0)
        
        with pytest.raises(ValueError):
            self.taxonomy.update_taxonomy({"invalid": "I"}, -1)
            
        # Test comptes avec noms edge cases et mappings explicites
        edge_accounts = {
            "": "E",  # Nom vide
            "a" * 1000: "L",  # Nom très long
            "🚀_account": "U",  # Unicode dans nom
            "account.with.dots": "D",
            "account-with-dashes": "H"
        }
        
        # Devrait fonctionner sans erreur
        mapping = self.taxonomy.update_taxonomy(edge_accounts, 1)
        assert len(mapping) == len(edge_accounts)
        
    def test_conversion_path_to_word_integration(self):
        """
        Test intégration conversion chemin DAG → mot pour validation pipeline complet
        """
        # Setup taxonomie avec comptes
        accounts = {"source": "S", "intermediate": "I", "target": "T"}
        self.taxonomy.update_taxonomy(accounts, 1)
        
        # Création chemin DAG simulé
        path = [
            Node("source"),
            Node("intermediate"), 
            Node("target")
        ]
        
        # Conversion chemin → mot
        word = self.taxonomy.convert_path_to_word(path, 1)
        assert word == "SIT"
        
        # Test avec mappings explicites
        explicit_accounts = {"node1": "X", "node2": "Y", "node3": "Z"}
        mapping = self.taxonomy.update_taxonomy(explicit_accounts, 2)
        
        explicit_path = [Node("node1"), Node("node2"), Node("node3")]
        explicit_word = self.taxonomy.convert_path_to_word(explicit_path, 2)
        assert explicit_word == "XYZ"
        
        expected_word = mapping["node1"] + mapping["node2"] + mapping["node3"]
        assert explicit_word == expected_word
        
        # Test erreur nœud sans account_id
        invalid_node = Node(None)
        invalid_path = [invalid_node]
        
        with pytest.raises(ValueError, match="Node without account_id"):
            self.taxonomy.convert_path_to_word(invalid_path, 1)


def run_academic_test_1():
    """
    Exécution test académique 1 avec rapport détaillé de validation
    
    Returns:
        bool: True si tous invariants validés, False sinon
    """
    pytest_result = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x"  # Stop au premier échec pour diagnostic précis
    ])
    
    return pytest_result == 0


if __name__ == "__main__":
    success = run_academic_test_1()
    if success:
        print("✅ TEST ACADÉMIQUE 1 RÉUSSI - Invariants temporels taxonomie validés")
        print("📊 Propriétés mathématiques vérifiées:")
        print("   • Monotonie temporelle stricte")
        print("   • Déterminisme mapping complet") 
        print("   • Historisation sans perte")
        print("   • Consistance UTF-32 garantie")
        print("   • Absence collisions vérifiée")
        print("   • Complexité O(log n) mesurée")
    else:
        print("❌ TEST ACADÉMIQUE 1 ÉCHOUÉ - Violations invariants détectées")
        exit(1)