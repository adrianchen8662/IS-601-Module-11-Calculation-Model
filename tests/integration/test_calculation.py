# tests/integration/test_calculation.py
"""
Integration Tests for Polymorphic Calculation Models

These tests verify the polymorphic behavior of the Calculation model hierarchy.
Polymorphism in SQLAlchemy means that different calculation types (Addition,
Subtraction, etc.) can be treated uniformly while maintaining type-specific
behavior.

What Makes These Tests Polymorphic:
1. Factory Pattern: Calculation.create() returns different subclasses
2. Type Resolution: isinstance() checks verify correct subclass instantiation
3. Polymorphic Behavior: Each subclass implements get_result() differently
4. Common Interface: All calculations share the same methods/attributes

These tests demonstrate key OOP principles:
- Inheritance: Subclasses inherit from Calculation
- Polymorphism: Same interface, different implementations
- Encapsulation: Each class encapsulates its calculation logic

Note: No database is required here – these tests exercise Python-level logic
only. For DB-level tests see tests/integration/test_calculation_db.py.
"""

import pytest
import uuid

from app.models.calculation import (
    Calculation,
    Addition,
    Subtraction,
    Multiplication,
    Division,
)


# Helper function to create a dummy user_id for testing.
def dummy_user_id():
    """
    Generate a random UUID for testing purposes.

    In real tests with a database, you would create an actual user
    and use their ID. This helper is sufficient for unit-level testing
    of the calculation logic without database dependencies.
    """
    return uuid.uuid4()


# ============================================================================
# Tests for Individual Calculation Types
# ============================================================================

def test_addition_get_result():
    """
    Test that Addition.get_result returns the correct sum.

    Verifies that the Addition class correctly implements the polymorphic
    get_result() method for its specific operation (a + b).
    """
    calc = Addition(a=10, b=5)
    result = calc.get_result()
    assert result == 15.0, f"Expected 15.0, got {result}"


def test_subtraction_get_result():
    """
    Test that Subtraction.get_result returns the correct difference.

    Subtraction performs: result = a - b.
    """
    calc = Subtraction(a=20, b=8)
    result = calc.get_result()
    assert result == 12.0, f"Expected 12.0, got {result}"


def test_multiplication_get_result():
    """
    Test that Multiplication.get_result returns the correct product.

    Multiplication performs: result = a * b.
    """
    calc = Multiplication(a=3, b=4)
    result = calc.get_result()
    assert result == 12.0, f"Expected 12.0, got {result}"


def test_division_get_result():
    """
    Test that Division.get_result returns the correct quotient.

    Division performs: result = a / b.
    """
    calc = Division(a=100, b=4)
    result = calc.get_result()
    assert result == 25.0, f"Expected 25.0, got {result}"


def test_division_by_zero():
    """
    Test that Division.get_result raises ValueError when b is zero.

    This demonstrates EAFP (Easier to Ask for Forgiveness than Permission):
    we attempt the operation and catch the exception rather than checking
    beforehand.
    """
    calc = Division(a=50, b=0)
    with pytest.raises(ValueError, match="Cannot divide by zero."):
        calc.get_result()


# ============================================================================
# Tests for Polymorphic Factory Pattern
# ============================================================================

def test_factory_addition():
    """
    Test the Calculation.create factory method for addition.

    Key Polymorphic Concepts:
    1. Factory returns the correct subclass type
    2. The returned object behaves as both Calculation and Addition
    3. Type-specific behavior (get_result) works correctly
    4. result is pre-computed and stored on the instance
    """
    calc = Calculation.create("addition", a=1, b=2)
    # Verify polymorphism: factory returned the correct subclass
    assert isinstance(calc, Addition), \
        "Factory did not return an Addition instance."
    assert isinstance(calc, Calculation), \
        "Addition should also be an instance of Calculation."
    # Verify result was pre-computed by the factory
    assert calc.result == 3.0, "Factory did not pre-compute result."


def test_factory_subtraction():
    """
    Test the Calculation.create factory method for subtraction.

    Demonstrates that the factory pattern works consistently across
    different calculation types.
    """
    calc = Calculation.create("subtraction", a=10, b=4)
    assert isinstance(calc, Subtraction), \
        "Factory did not return a Subtraction instance."
    assert calc.result == 6.0, "Incorrect subtraction result."


def test_factory_multiplication():
    """
    Test the Calculation.create factory method for multiplication.
    """
    calc = Calculation.create("multiplication", a=3, b=4)
    assert isinstance(calc, Multiplication), \
        "Factory did not return a Multiplication instance."
    assert calc.result == 12.0, "Incorrect multiplication result."


def test_factory_division():
    """
    Test the Calculation.create factory method for division.
    """
    calc = Calculation.create("division", a=100, b=5)
    assert isinstance(calc, Division), \
        "Factory did not return a Division instance."
    assert calc.result == 20.0, "Incorrect division result."


def test_factory_invalid_type():
    """
    Test that Calculation.create raises a ValueError for unsupported types.

    Verifies that the factory pattern properly handles invalid inputs
    and provides clear error messages.
    """
    with pytest.raises(ValueError, match="Unsupported calculation type"):
        Calculation.create("modulus", a=10, b=3)


def test_factory_case_insensitive():
    """
    Test that the factory is case-insensitive.

    The factory should accept 'Addition', 'ADDITION', 'addition', etc.
    """
    for variant in ["addition", "Addition", "ADDITION", "AdDiTiOn"]:
        calc = Calculation.create(variant, a=5, b=3)
        assert isinstance(calc, Addition), \
            f"Factory failed for case: {variant}"
        assert calc.result == 8.0


def test_factory_sets_user_id():
    """
    Test that the factory correctly assigns user_id to the instance.
    """
    uid = dummy_user_id()
    calc = Calculation.create("addition", a=1, b=1, user_id=uid)
    assert calc.user_id == uid, "Factory did not set user_id correctly."


def test_factory_division_by_zero_raises():
    """
    Test that the factory raises ValueError when dividing by zero.

    The error is raised inside get_result() which the factory calls
    immediately, so no partially-constructed object is returned.
    """
    with pytest.raises(ValueError, match="Cannot divide by zero."):
        Calculation.create("division", a=10, b=0)


# ============================================================================
# Tests Demonstrating Polymorphic Behavior
# ============================================================================

def test_polymorphic_list_of_calculations():
    """
    Test that different calculation types can be stored in the same list.

    This demonstrates polymorphism: A list of Calculation objects can contain
    different subclasses, and each maintains its type-specific behavior.

    This is a key benefit of polymorphism: you can treat different types
    uniformly while they maintain their unique implementations.
    """
    uid = dummy_user_id()

    # Create a list of different calculation types
    calculations = [
        Calculation.create("addition", a=1, b=2, user_id=uid),
        Calculation.create("subtraction", a=10, b=3, user_id=uid),
        Calculation.create("multiplication", a=2, b=4, user_id=uid),
        Calculation.create("division", a=100, b=5, user_id=uid),
    ]

    # Each calculation maintains its specific type
    assert isinstance(calculations[0], Addition)
    assert isinstance(calculations[1], Subtraction)
    assert isinstance(calculations[2], Multiplication)
    assert isinstance(calculations[3], Division)

    # All calculations share the same interface
    results = [calc.get_result() for calc in calculations]

    # Each produces its type-specific result
    assert results == [3.0, 7.0, 8.0, 20.0]


def test_polymorphic_method_calling():
    """
    Test that polymorphic methods work correctly.

    Demonstrates that you can call get_result() on any Calculation
    subclass and get the correct type-specific behavior without knowing
    the exact subclass type at compile time.
    """
    uid = dummy_user_id()

    # Expected results for (a=10, b=2)
    expected = {
        "addition": 12.0,
        "subtraction": 8.0,
        "multiplication": 20.0,
        "division": 5.0,
    }

    for calc_type, exp in expected.items():
        calc = Calculation.create(calc_type, a=10, b=2, user_id=uid)
        # Polymorphic method call: same method name, different behavior
        result = calc.get_result()
        assert result == exp, \
            f"{calc_type} failed: expected {exp}, got {result}"
