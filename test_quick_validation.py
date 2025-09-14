#!/usr/bin/env python3
"""Test rapide validation taxonomique"""

from icgs_core import DAG, Account
from decimal import Decimal

dag = DAG()
account = Account("test_validation", Decimal('100'))

print("=== Test validation taxonomique ===")

# Test 1: Dict vide
try:
    dag.add_account(account, taxonomic_chars={})
    print("❌ Dict vide devrait lever ValueError")
except ValueError as e:
    print(f"✅ Dict vide lève ValueError: {e}")

# Test 2: Caractères dupliqués
account2 = Account("test_validation2", Decimal('100'))
try:
    dag.add_account(account2, taxonomic_chars={'source': 'X', 'sink': 'X'})
    print("❌ Caractères dupliqués devraient lever ValueError")
except ValueError as e:
    print(f"✅ Caractères dupliqués lèvent ValueError: {e}")

# Test 3: Format correct
account3 = Account("test_validation3", Decimal('100'))
try:
    success = dag.add_account(account3, taxonomic_chars={'source': 'A', 'sink': 'B'})
    print(f"✅ Format correct réussit: {success}")
except Exception as e:
    print(f"❌ Format correct devrait réussir: {e}")