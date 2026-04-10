# tests/integration/test_calculation_db.py
"""
Database Integration Tests for Calculation Model

These tests insert records into a real PostgreSQL database (provided by the
GitHub Actions service container) and verify that:

1. Correct data is persisted – a, b, type, and result columns match expected values.
2. Polymorphic type resolution works – SQLAlchemy loads the right subclass based
   on the 'type' discriminator column after a round-trip to the DB.
3. Error cases never reach the DB – invalid type strings and division-by-zero
   raise ValueError inside the factory before any INSERT is attempted.
4. user_id is nullable – calculations can exist without an associated user row.
5. Timestamps are set automatically on insert.

Fixtures
--------
db_session (from tests/conftest.py)
    Wraps each test in a transaction that is rolled back after the test
    completes.  This keeps tests fully independent: no test sees rows
    inserted by another test, and no manual cleanup is required.

Running locally
---------------
Set DATABASE_URL to point to a running PostgreSQL instance, e.g.::

    export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test_calculator_db
    pytest tests/integration/test_calculation_db.py -v

In CI (GitHub Actions) DATABASE_URL is set automatically by the workflow.
"""

import pytest

from app.models.calculation import (
    Calculation,
    Addition,
    Subtraction,
    Multiplication,
    Division,
)


# ============================================================================
# Helper
# ============================================================================

def insert_and_refresh(session, calc: Calculation) -> Calculation:
    """
    Persist calc to the database and reload it so that all DB-generated
    values (id, timestamps) are available on the instance.

    Steps:
    1. session.add(calc)    – mark for INSERT
    2. session.flush()      – send INSERT SQL; stays inside the transaction
    3. session.expire(calc) – discard the in-memory state
    4. session.refresh(calc)– re-SELECT from the DB

    Returns:
        Calculation: The refreshed ORM instance.
    """
    session.add(calc)
    session.flush()          # sends INSERT; still inside the transaction
    session.expire(calc)     # force next access to reload from DB
    session.refresh(calc)
    return calc


# ============================================================================
# Basic CRUD – one test per operation type
# ============================================================================

def test_db_insert_addition(db_session):
    """
    Test that an Addition record is stored with correct a, b, type, and result.
    """
    calc = Calculation.create("addition", a=10.0, b=5.0)
    insert_and_refresh(db_session, calc)

    # Verify all columns persisted correctly
    assert calc.id is not None, "id should be auto-generated"
    assert calc.a == 10.0
    assert calc.b == 5.0
    assert calc.type == "addition"
    assert calc.result == 15.0


def test_db_insert_subtraction(db_session):
    """
    Test that a Subtraction record is stored with correct result (a - b).
    """
    calc = Calculation.create("subtraction", a=20.0, b=8.0)
    insert_and_refresh(db_session, calc)

    assert calc.result == 12.0
    assert calc.type == "subtraction"


def test_db_insert_multiplication(db_session):
    """
    Test that a Multiplication record is stored with correct result (a * b).
    """
    calc = Calculation.create("multiplication", a=3.0, b=4.0)
    insert_and_refresh(db_session, calc)

    assert calc.result == 12.0
    assert calc.type == "multiplication"


def test_db_insert_division(db_session):
    """
    Test that a Division record is stored with correct result (a / b).
    """
    calc = Calculation.create("division", a=100.0, b=4.0)
    insert_and_refresh(db_session, calc)

    assert calc.result == 25.0
    assert calc.type == "division"


# ============================================================================
# Polymorphic retrieval – SQLAlchemy returns the right subclass
# ============================================================================

def test_db_polymorphic_type_resolution(db_session):
    """
    After a DB round-trip, SQLAlchemy should return the correct subclass
    based on the 'type' discriminator column.

    This verifies a core feature of SQLAlchemy single-table inheritance:
    rows are automatically mapped to the right Python class without any
    manual branching.
    """
    # 1. Insert a Multiplication record
    calc = Calculation.create("multiplication", a=6.0, b=7.0)
    db_session.add(calc)
    db_session.flush()
    saved_id = calc.id

    # 2. Expire the identity map so SQLAlchemy must re-fetch from the DB
    db_session.expire_all()
    loaded = db_session.get(Calculation, saved_id)

    # 3. Even though we queried via the base Calculation class, SQLAlchemy
    #    should return a Multiplication instance
    assert isinstance(loaded, Multiplication), (
        f"Expected Multiplication, got {type(loaded).__name__}"
    )
    assert loaded.get_result() == 42.0


def test_db_query_all_returns_correct_subclasses(db_session):
    """
    Querying Calculation.query.all() across a mixed set of records should
    return the correct subclass for each row.
    """
    # Insert three different calculation types
    records = [
        Calculation.create("addition", a=1, b=2),
        Calculation.create("subtraction", a=10, b=3),
        Calculation.create("division", a=100, b=5),
    ]
    for r in records:
        db_session.add(r)
    db_session.flush()

    # Expire and reload so we're hitting the DB
    db_session.expire_all()
    loaded = db_session.query(Calculation).all()

    type_names = {type(c).__name__ for c in loaded}
    assert "Addition" in type_names
    assert "Subtraction" in type_names
    assert "Division" in type_names


# ============================================================================
# result column persists correctly
# ============================================================================

def test_db_result_persisted(db_session):
    """
    The pre-computed result stored at creation should survive the round-trip
    to the database unchanged.
    """
    calc = Calculation.create("addition", a=3.3, b=1.7)
    db_session.add(calc)
    db_session.flush()
    saved_id = calc.id

    db_session.expire_all()
    reloaded = db_session.get(Calculation, saved_id)

    # Use a small tolerance for floating-point comparison
    assert abs(reloaded.result - 5.0) < 1e-9, (
        f"Expected 5.0, got {reloaded.result}"
    )


# ============================================================================
# Error cases – nothing should reach the DB
# ============================================================================

def test_invalid_type_raises_before_db(db_session):
    """
    An unsupported type string should raise ValueError inside the factory
    method, before any INSERT reaches the database.
    """
    with pytest.raises(ValueError, match="Unsupported calculation type"):
        Calculation.create("modulus", a=10, b=3)

    # Confirm the session is still clean – no rows were inserted
    count = db_session.query(Calculation).count()
    assert count == 0, "A row was unexpectedly inserted for an invalid type"


def test_division_by_zero_raises_before_db(db_session):
    """
    Division by zero is caught in get_result() which the factory calls
    immediately. No INSERT should ever be attempted.
    """
    with pytest.raises(ValueError, match="Cannot divide by zero."):
        Calculation.create("division", a=50, b=0)

    count = db_session.query(Calculation).count()
    assert count == 0, "A row was unexpectedly inserted for a zero divisor"


# ============================================================================
# nullable user_id – calculation without an owner
# ============================================================================

def test_db_calculation_without_user(db_session):
    """
    user_id is nullable; a Calculation row can exist without an owning User.

    This is useful for testing and for scenarios where anonymous calculations
    are permitted by the business rules.
    """
    calc = Calculation.create("addition", a=7, b=3)
    # user_id not provided → should be None
    assert calc.user_id is None

    db_session.add(calc)
    db_session.flush()
    db_session.expire_all()

    reloaded = db_session.get(Calculation, calc.id)
    assert reloaded.user_id is None, "user_id should remain NULL in the DB"
    assert reloaded.result == 10.0


# ============================================================================
# Timestamps
# ============================================================================

def test_db_timestamps_set_on_insert(db_session):
    """
    created_at and updated_at should be automatically populated by
    SQLAlchemy's server_default / default when the row is inserted.
    """
    calc = Calculation.create("subtraction", a=100, b=37)
    db_session.add(calc)
    db_session.flush()
    db_session.expire_all()

    reloaded = db_session.get(Calculation, calc.id)
    assert reloaded.created_at is not None, "created_at was not set"
    assert reloaded.updated_at is not None, "updated_at was not set"
