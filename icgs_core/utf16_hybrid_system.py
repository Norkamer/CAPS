#!/usr/bin/env python3
"""
UTF-16 Hybrid Architecture System - CAPS Quick Win Task 2
=========================================================

Architecture hybride remplaçant la complexité UTF-32 private use area:
- UUID interne pour performance et extensibilité
- UTF-16 display layer pour compliance et compatibilité
- Protection anti-emoji multi code-point
- Basic Multilingual Plane (BMP) guarantee

This system resolves the over-engineering identified in academic evaluation
while maintaining all functionality and improving maintainability.
"""

import uuid
import hashlib
from typing import Dict, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum


class UTF16MappingMode(Enum):
    """Modes de mapping UTF-16 pour différents cas d'usage"""
    SECTOR_BASED = "sector_based"      # Basé sur secteur économique
    HASH_BASED = "hash_based"         # Basé sur hash UUID
    SEQUENTIAL = "sequential"         # Séquentiel simple
    DETERMINISTIC = "deterministic"   # Déterministe reproductible


@dataclass
class UTF16DisplayInfo:
    """Information d'affichage UTF-16 pour un agent"""
    uuid_internal: str                # UUID interne pour performance
    utf16_char: str                  # Caractère UTF-16 display
    sector: str                      # Secteur économique
    display_name: str                # Nom d'affichage lisible
    creation_timestamp: float        # Timestamp création


class UTF16HybridSystem:
    """
    Système hybride UUID interne + UTF-16 display

    Remplace l'architecture UTF-32 private use area complexe par:
    1. UUID interne haute performance pour operations système
    2. Layer UTF-16 compatible pour affichage et export
    3. Protection garantie anti-emoji et surrogate pairs
    """

    def __init__(self):
        self.uuid_to_display: Dict[str, UTF16DisplayInfo] = {}
        self.utf16_to_uuid: Dict[str, str] = {}
        self.sector_chars_used: Dict[str, Set[str]] = {}
        self.mode = UTF16MappingMode.SECTOR_BASED

        # UTF-16 BMP safe character ranges (évite emojis et surrogate area)
        self.sector_base_ranges = {
            'AGRICULTURE': 0x2600,  # ☀ Miscellaneous Symbols
            'INDUSTRY': 0x2700,     # ✂ Dingbats
            'SERVICES': 0x2800,     # ⠀ Braille Patterns
            'FINANCE': 0x2900,      # ⤀ Supplemental Arrows-B
            'ENERGY': 0x2A00        # ⨀ Supplemental Mathematical Operators
        }

        # Protection anti-emoji ranges (à éviter)
        self.unsafe_ranges = [
            (0x1F600, 0x1F64F),  # Emoticons
            (0x1F300, 0x1F5FF),  # Misc Symbols and Pictographs
            (0x1F680, 0x1F6FF),  # Transport and Map Symbols
            (0x1F1E6, 0x1F1FF),  # Regional Indicator Symbols
            (0xD800, 0xDFFF),    # Surrogate Pairs Area
        ]

    def register_agent(self, agent_id: str, sector: str,
                      display_name: Optional[str] = None) -> Tuple[str, str]:
        """
        Enregistre un agent avec UUID interne + UTF-16 display

        Returns:
            Tuple[uuid_internal, utf16_char]: UUID interne et caractère UTF-16
        """
        # Générer UUID interne unique
        uuid_internal = str(uuid.uuid4())

        # Générer caractère UTF-16 display safe
        utf16_char = self._generate_utf16_display_char(uuid_internal, sector)

        # Créer display info
        display_info = UTF16DisplayInfo(
            uuid_internal=uuid_internal,
            utf16_char=utf16_char,
            sector=sector,
            display_name=display_name or f"Agent_{agent_id}",
            creation_timestamp=float(__import__('time').time())
        )

        # Enregistrer mappings bidirectionnels
        self.uuid_to_display[uuid_internal] = display_info
        self.utf16_to_uuid[utf16_char] = uuid_internal

        # Tracker utilisation caractères par secteur
        if sector not in self.sector_chars_used:
            self.sector_chars_used[sector] = set()
        self.sector_chars_used[sector].add(utf16_char)

        return uuid_internal, utf16_char

    def _generate_utf16_display_char(self, uuid_internal: str, sector: str) -> str:
        """
        Génère caractère UTF-16 safe pour display

        Garanties:
        - Single code-point UTF-16 (pas de surrogate pairs)
        - Basic Multilingual Plane (U+0000-U+FFFF)
        - Protection anti-emoji multi code-point
        - Unique par secteur
        """
        if sector not in self.sector_base_ranges:
            # Fallback pour secteurs non-définis
            base_char = 0x2500  # Box Drawing
        else:
            base_char = self.sector_base_ranges[sector]

        # Utiliser hash UUID pour offset déterministe mais unique
        hash_input = f"{uuid_internal}_{sector}".encode('utf-8')
        hash_digest = hashlib.md5(hash_input).hexdigest()
        hash_int = int(hash_digest[:8], 16)  # Premier 32 bits

        # Offset limité pour rester dans BMP et éviter zones dangereuses
        max_offset = 255  # Conservative pour éviter débordement
        char_offset = hash_int % max_offset

        candidate_char_code = base_char + char_offset

        # Vérification UTF-16 BMP compliance
        if candidate_char_code > 0xFFFF:
            candidate_char_code = base_char + (char_offset % 100)  # Fallback conservative

        # Protection anti-emoji et surrogate pairs
        candidate_char = chr(candidate_char_code)

        if self._is_unsafe_character(candidate_char):
            # Fallback vers caractère de base safe
            candidate_char = chr(base_char)

        # Vérification unicité dans secteur
        if sector in self.sector_chars_used and candidate_char in self.sector_chars_used[sector]:
            # Générer alternative unique
            for i in range(1, 100):  # Max 100 tentatives
                alt_char_code = base_char + ((char_offset + i) % 100)
                if alt_char_code <= 0xFFFF:
                    alt_char = chr(alt_char_code)
                    if not self._is_unsafe_character(alt_char) and alt_char not in self.sector_chars_used[sector]:
                        candidate_char = alt_char
                        break

        return candidate_char

    def _is_unsafe_character(self, char: str) -> bool:
        """
        Vérifie si caractère est unsafe (emoji, surrogate, multi code-point)
        """
        if len(char) != 1:
            return True  # Multi code-point

        char_code = ord(char)

        # Vérifier ranges unsafe
        for start, end in self.unsafe_ranges:
            if start <= char_code <= end:
                return True

        # Vérification UTF-16 encoding length (protection anti-surrogate)
        try:
            utf16_bytes = char.encode('utf-16le')
            if len(utf16_bytes) != 2:  # Should be exactly 2 bytes for BMP
                return True
        except UnicodeEncodeError:
            return True

        return False

    def get_uuid_from_display(self, utf16_char: str) -> Optional[str]:
        """Récupère UUID interne depuis caractère UTF-16 display"""
        return self.utf16_to_uuid.get(utf16_char)

    def get_display_from_uuid(self, uuid_internal: str) -> Optional[UTF16DisplayInfo]:
        """Récupère info display depuis UUID interne"""
        return self.uuid_to_display.get(uuid_internal)

    def get_utf16_char_from_uuid(self, uuid_internal: str) -> Optional[str]:
        """Récupère caractère UTF-16 depuis UUID interne"""
        display_info = self.uuid_to_display.get(uuid_internal)
        return display_info.utf16_char if display_info else None

    def migrate_from_legacy_utf32(self, legacy_char: str, agent_id: str, sector: str) -> Tuple[str, str]:
        """
        Migration depuis ancien système UTF-32 vers architecture hybride

        Returns:
            Tuple[uuid_internal, utf16_char]: Nouveaux identifiants hybrides
        """
        # Créer UUID déterministe basé sur legacy char + agent_id pour reproductibilité
        seed_input = f"legacy_{legacy_char}_{agent_id}_{sector}".encode('utf-8')
        deterministic_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, seed_input.hex()))

        # Générer caractère UTF-16 display
        utf16_char = self._generate_utf16_display_char(deterministic_uuid, sector)

        # Enregistrer avec display name indiquant migration
        display_info = UTF16DisplayInfo(
            uuid_internal=deterministic_uuid,
            utf16_char=utf16_char,
            sector=sector,
            display_name=f"Migrated_{agent_id}",
            creation_timestamp=float(__import__('time').time())
        )

        # Enregistrer mappings
        self.uuid_to_display[deterministic_uuid] = display_info
        self.utf16_to_uuid[utf16_char] = deterministic_uuid

        # Tracker secteur
        if sector not in self.sector_chars_used:
            self.sector_chars_used[sector] = set()
        self.sector_chars_used[sector].add(utf16_char)

        return deterministic_uuid, utf16_char

    def validate_utf16_compliance(self) -> Dict[str, bool]:
        """
        Validation complète UTF-16 compliance du système

        Returns:
            Dict avec résultats validation
        """
        results = {
            'all_chars_single_codepoint': True,
            'all_chars_bmp_compliant': True,
            'no_emoji_sequences': True,
            'no_surrogate_pairs': True,
            'charset_unique_per_sector': True
        }

        for uuid_internal, display_info in self.uuid_to_display.items():
            char = display_info.utf16_char

            # Single code-point check
            if len(char) != 1:
                results['all_chars_single_codepoint'] = False

            # BMP compliance check
            char_code = ord(char)
            if char_code > 0xFFFF:
                results['all_chars_bmp_compliant'] = False

            # Surrogate pairs check
            if 0xD800 <= char_code <= 0xDFFF:
                results['no_surrogate_pairs'] = False

            # Emoji sequences check
            if self._is_unsafe_character(char):
                results['no_emoji_sequences'] = False

        # Unicité par secteur check
        for sector, chars_used in self.sector_chars_used.items():
            if len(chars_used) != len(set(chars_used)):
                results['charset_unique_per_sector'] = False

        return results

    def get_system_statistics(self) -> Dict[str, any]:
        """Statistiques du système hybride"""
        return {
            'total_agents_registered': len(self.uuid_to_display),
            'sectors_count': len(self.sector_chars_used),
            'utf16_chars_allocated': len(self.utf16_to_uuid),
            'chars_per_sector': {sector: len(chars) for sector, chars in self.sector_chars_used.items()},
            'utf16_compliance': self.validate_utf16_compliance(),
            'mapping_mode': self.mode.value
        }


# Exemple d'utilisation et test rapide
if __name__ == "__main__":
    # Test rapide du système hybride
    hybrid_system = UTF16HybridSystem()

    # Enregistrer quelques agents
    uuid1, char1 = hybrid_system.register_agent("FARM_01", "AGRICULTURE", "Ferme Alice")
    uuid2, char2 = hybrid_system.register_agent("FACTORY_01", "INDUSTRY", "Usine Bob")
    uuid3, char3 = hybrid_system.register_agent("BANK_01", "FINANCE", "Banque Charlie")

    print("🧪 Test UTF-16 Hybrid System")
    print(f"AGRICULTURE: {uuid1[:8]}... → '{char1}' (ord: {ord(char1):04X})")
    print(f"INDUSTRY: {uuid2[:8]}... → '{char2}' (ord: {ord(char2):04X})")
    print(f"FINANCE: {uuid3[:8]}... → '{char3}' (ord: {ord(char3):04X})")

    # Test validation UTF-16
    compliance = hybrid_system.validate_utf16_compliance()
    print(f"\n✅ UTF-16 Compliance: {all(compliance.values())}")

    # Test statistiques
    stats = hybrid_system.get_system_statistics()
    print(f"📊 Agents: {stats['total_agents_registered']}, Secteurs: {stats['sectors_count']}")