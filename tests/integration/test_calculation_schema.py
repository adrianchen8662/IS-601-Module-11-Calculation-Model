# tests/integration/test_calculation_schema.py
"""
Integration Tests for Calculation Pydantic Schemas

These tests verify that Pydantic schemas correctly validate calculation data
before it reaches the application logic. This is an important security and
data integrity layer that prevents invalid data from entering the system.

Key Testing Concepts:
1. Valid Data: Ensure schemas accept correct data
2. Invalid Data: Ensure schemas reject incorrect data with clear messages
3. Edge Cases: Test boundary conditions
4. Business Rules: Verify domain-specific validation (e.g., no division by 0)

Note: The schemas now use 'a' and 'b' float fields (two operands) instead
of the previous 'inputs' list, matching the updated SQLAlchemy model.
"""

import pytest
from uuid import uuid4
from datetime import datetime
from pydantic import ValidationError

from app.schemas.calculation import (
    CalculationType,
    CalculationBase,
    CalculationCreate,
    CalculationRead,
    CalculationUpdate,
)


# ============================================================================
# Tests for CalculationType Enum
# ============================================================================

def test_calculation_type_values():
    """Test that CalculationType enum has the correct string values."""
    assert CalculationType.ADDITION.value == "addition"
    assert CalculationType.SUBTRACTION.value == "subtraction"
    assert CalculationType.MULTIPLICATION.value == "multiplication"
    assert CalculationType.DIVISION.value == "division"


# ============================================================================
# Tests for CalculationBase Schema – Valid Data
# ============================================================================

def test_calculation_base_valid_addition():
    """Test CalculationBase accepts valid addition data."""
    data = {"type": "addition", "a": 10.5, "b": 3.0}
    calc = CalculationBase(**data)
    assert calc.type == CalculationType.ADDITION
    assert calc.a == 10.5
    assert calc.b == 3.0


def test_calculation_base_valid_subtraction():
    """Test CalculationBase accepts valid subtraction data."""
    data = {"type": "subtraction", "a": 20, "b": 5.5}
    calc = CalculationBase(**data)
    assert calc.type == CalculationType.SUBTRACTION


def test_calculation_base_valid_multiplication():
    """Test CalculationBase accepts valid multiplication data."""
    data = {"type": "multiplication", "a": 4, "b": 7}
    calc = CalculationBase(**data)
    assert calc.type == CalculationType.MULTIPLICATION


def test_calculation_base_valid_division():
    """Test CalculationBase accepts valid division data (b != 0)."""
    data = {"type": "division", "a": 100, "b": 4}
    calc = CalculationBase(**data)
    assert calc.type == CalculationType.DIVISION


def test_calculation_base_case_insensitive_type():
    """Test that calculation type is case-insensitive."""
    for type_variant in ["Addition", "ADDITION", "AdDiTiOn"]:
        data = {"type": type_variant, "a": 1, "b": 2}
        calc = CalculationBase(**data)
        assert calc.type == CalculationType.ADDITION


# ============================================================================
# Tests for CalculationBase Schema – Invalid Data
# ============================================================================

def test_calculation_base_invalid_type():
    """Test that an invalid calculation type raises ValidationError."""
    data = {"type": "modulus", "a": 10, "b": 3}  # 'modulus' is not supported
    with pytest.raises(ValidationError) as exc_info:
        CalculationBase(**data)
    errors = exc_info.value.errors()
    assert any("Type must be one of" in str(err) for err in errors)


def test_calculation_base_division_by_zero():
    """
    Test that division by zero is caught by schema validation.

    This demonstrates LBYL (Look Before You Leap): We check for the error
    condition before attempting the operation. This is appropriate at the
    API boundary to provide immediate feedback to the client.
    """
    data = {"type": "division", "a": 100, "b": 0}  # b == 0 → invalid
    with pytest.raises(ValidationError) as exc_info:
        CalculationBase(**data)
    errors = exc_info.value.errors()
    assert any("Cannot divide by zero" in str(err) for err in errors)


def test_calculation_base_division_zero_numerator_ok():
    """Test that a=0 (zero numerator) is valid as long as b != 0."""
    data = {"type": "division", "a": 0, "b": 5}  # 0 / 5 = 0 – perfectly valid
    calc = CalculationBase(**data)
    assert calc.a == 0


def test_calculation_base_missing_a():
    """Test that omitting 'a' raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        CalculationBase(type="addition", b=2)
    assert any("a" in str(err) for err in exc_info.value.errors())


def test_calculation_base_missing_b():
    """Test that omitting 'b' raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        CalculationBase(type="addition", a=1)
    assert any("b" in str(err) for err in exc_info.value.errors())


def test_calculation_base_negative_numbers():
    """Test that negative operands are accepted."""
    data = {"type": "addition", "a": -5, "b": -10}
    calc = CalculationBase(**data)
    assert calc.a == -5
    assert calc.b == -10


def test_calculation_base_large_numbers():
    """Test that very large floats are handled correctly."""
    data = {"type": "multiplication", "a": 1e10, "b": 1e10}
    calc = CalculationBase(**data)
    assert isinstance(calc.a, float)


# ============================================================================
# Tests for CalculationCreate Schema
# ============================================================================

def test_calculation_create_valid_with_user_id():
    """Test CalculationCreate with all fields including user_id."""
    uid = uuid4()
    data = {
        "type": "multiplication",
        "a": 2,
        "b": 3,
        "user_id": str(uid),
    }
    calc = CalculationCreate(**data)
    assert calc.type == CalculationType.MULTIPLICATION
    assert calc.a == 2
    assert calc.b == 3
    assert calc.user_id == uid


def test_calculation_create_valid_without_user_id():
    """Test CalculationCreate without user_id (it is optional)."""
    calc = CalculationCreate(type="addition", a=1, b=2)
    assert calc.user_id is None


def test_calculation_create_invalid_user_id():
    """Test that an invalid UUID string raises ValidationError."""
    data = {"type": "subtraction", "a": 10, "b": 5, "user_id": "not-a-uuid"}
    with pytest.raises(ValidationError):
        CalculationCreate(**data)


def test_calculation_create_missing_type():
    """Test that omitting type raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        CalculationCreate(a=1, b=2)
    assert any("type" in str(err) for err in exc_info.value.errors())


def test_calculation_create_missing_a():
    """Test that omitting 'a' raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        CalculationCreate(type="addition", b=2)
    assert any("a" in str(err) for err in exc_info.value.errors())


def test_calculation_create_missing_b():
    """Test that omitting 'b' raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        CalculationCreate(type="addition", a=1)
    assert any("b" in str(err) for err in exc_info.value.errors())


# ============================================================================
# Tests for CalculationRead Schema
# ============================================================================

def test_calculation_read_valid():
    """Test CalculationRead with all required fields."""
    data = {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "type": "addition",
        "a": 10.0,
        "b": 5.0,
        "result": 15.0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    calc = CalculationRead(**data)
    assert calc.result == 15.0
    assert calc.type == CalculationType.ADDITION


def test_calculation_read_missing_result():
    """Test that CalculationRead requires the result field."""
    with pytest.raises(ValidationError) as exc_info:
        CalculationRead(
            id=str(uuid4()),
            type="multiplication",
            a=2,
            b=3,
            # 'result' deliberately omitted
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    errors = exc_info.value.errors()
    assert any("result" in str(err) for err in errors)


def test_calculation_read_without_user_id():
    """Test that user_id is optional in CalculationRead."""
    calc = CalculationRead(
        id=str(uuid4()),
        user_id=None,
        type="multiplication",
        a=3,
        b=4,
        result=12.0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    assert calc.user_id is None
    assert calc.result == 12.0


# ============================================================================
# Tests for CalculationUpdate Schema
# ============================================================================

def test_calculation_update_valid():
    """Test CalculationUpdate with both a and b provided."""
    upd = CalculationUpdate(a=42.0, b=7.0)
    assert upd.a == 42.0
    assert upd.b == 7.0


def test_calculation_update_all_fields_optional():
    """Test that CalculationUpdate can be created with no fields (partial update)."""
    upd = CalculationUpdate()
    assert upd.a is None
    assert upd.b is None


def test_calculation_update_only_a():
    """Test partial update where only 'a' is changed."""
    upd = CalculationUpdate(a=99.0)
    assert upd.a == 99.0
    assert upd.b is None


# ============================================================================
# Tests for Complex / Multi-type Scenarios
# ============================================================================

def test_multiple_calculations_with_different_types():
    """
    Test that schemas correctly validate multiple calculations of
    different types in a batch.
    """
    uid = uuid4()
    calcs_data = [
        {"type": "addition", "a": 1, "b": 2, "user_id": str(uid)},
        {"type": "subtraction", "a": 10, "b": 3, "user_id": str(uid)},
        {"type": "multiplication", "a": 2, "b": 4, "user_id": str(uid)},
        {"type": "division", "a": 100, "b": 5, "user_id": str(uid)},
    ]
    calcs = [CalculationCreate(**d) for d in calcs_data]

    assert len(calcs) == 4
    assert calcs[0].type == CalculationType.ADDITION
    assert calcs[1].type == CalculationType.SUBTRACTION
    assert calcs[2].type == CalculationType.MULTIPLICATION
    assert calcs[3].type == CalculationType.DIVISION


def test_schema_with_mixed_int_and_float():
    """Test that schemas correctly handle both int and float operands."""
    data = {"type": "subtraction", "a": 100, "b": 23.5}
    calc = CalculationBase(**data)
    # Pydantic coerces int to float for float-typed fields
    assert calc.a == 100.0
    assert calc.b == 23.5
