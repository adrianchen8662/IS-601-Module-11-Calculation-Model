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
    
    This verifies that the Addition class correctly implements the
    polymorphic get_result() method for its specific operation.
    """
    inputs = [10, 5, 3.5]
    addition = Addition(user_id=dummy_user_id(), inputs=inputs)
    result = addition.get_result()
    assert result == sum(inputs), f"Expected {sum(inputs)}, got {result}"


def test_subtraction_get_result():
    """
    Test that Subtraction.get_result returns the correct difference.
    
    Subtraction performs sequential subtraction: first - second - third...
    """
    inputs = [20, 5, 3]
    subtraction = Subtraction(user_id=dummy_user_id(), inputs=inputs)
    # Expected: 20 - 5 - 3 = 12
    result = subtraction.get_result()
    assert result == 12, f"Expected 12, got {result}"


def test_multiplication_get_result():
    """
    Test that Multiplication.get_result returns the correct product.
    
    Multiplication multiplies all input numbers together.
    """
    inputs = [2, 3, 4]
    multiplication = Multiplication(user_id=dummy_user_id(), inputs=inputs)
    result = multiplication.get_result()
    assert result == 24, f"Expected 24, got {result}"


def test_division_get_result():
    """
    Test that Division.get_result returns the correct quotient.
    
    Division performs sequential division: first / second / third...
    """
    inputs = [100, 2, 5]
    division = Division(user_id=dummy_user_id(), inputs=inputs)
    # Expected: 100 / 2 / 5 = 10
    result = division.get_result()
    assert result == 10, f"Expected 10, got {result}"


def test_division_by_zero():
    """
    Test that Division.get_result raises ValueError when dividing by zero.
    
    This demonstrates EAFP (Easier to Ask for Forgiveness than Permission):
    We attempt the operation and catch the exception rather than checking
    beforehand.
    """
    inputs = [50, 0, 5]
    division = Division(user_id=dummy_user_id(), inputs=inputs)
    with pytest.raises(ValueError, match="Cannot divide by zero."):
        division.get_result()


# ============================================================================
# Tests for Polymorphic Factory Pattern
# ============================================================================

def test_calculation_factory_addition():
    """
    Test the Calculation.create factory method for addition.
    
    This demonstrates polymorphism: The factory method returns a specific
    subclass (Addition) that can be used through the common Calculation
    interface.
    
    Key Polymorphic Concepts:
    1. Factory returns the correct subclass type
    2. The returned object behaves as both Calculation and Addition
    3. Type-specific behavior (get_result) works correctly
    """
    inputs = [1, 2, 3]
    calc = Calculation.create(
        calculation_type='addition',
        user_id=dummy_user_id(),
        inputs=inputs,
    )
    # Verify polymorphism: factory returned the correct subclass
    assert isinstance(calc, Addition), \
        "Factory did not return an Addition instance."
    assert isinstance(calc, Calculation), \
        "Addition should also be an instance of Calculation."
    # Verify behavior: subclass implements get_result() correctly
    assert calc.get_result() == sum(inputs), "Incorrect addition result."


def test_calculation_factory_subtraction():
    """
    Test the Calculation.create factory method for subtraction.
    
    Demonstrates that the factory pattern works consistently across
    different calculation types.
    """
    inputs = [10, 4]
    calc = Calculation.create(
        calculation_type='subtraction',
        user_id=dummy_user_id(),
        inputs=inputs,
    )
    # Expected: 10 - 4 = 6
    assert isinstance(calc, Subtraction), \
        "Factory did not return a Subtraction instance."
    assert calc.get_result() == 6, "Incorrect subtraction result."


def test_calculation_factory_multiplication():
    """
    Test the Calculation.create factory method for multiplication.
    """
    inputs = [3, 4, 2]
    calc = Calculation.create(
        calculation_type='multiplication',
        user_id=dummy_user_id(),
        inputs=inputs,
    )
    # Expected: 3 * 4 * 2 = 24
    assert isinstance(calc, Multiplication), \
        "Factory did not return a Multiplication instance."
    assert calc.get_result() == 24, "Incorrect multiplication result."


def test_calculation_factory_division():
    """
    Test the Calculation.create factory method for division.
    """
    inputs = [100, 2, 5]
    calc = Calculation.create(
        calculation_type='division',
        user_id=dummy_user_id(),
        inputs=inputs,
    )
    # Expected: 100 / 2 / 5 = 10
    assert isinstance(calc, Division), \
        "Factory did not return a Division instance."
    assert calc.get_result() == 10, "Incorrect division result."


def test_calculation_factory_invalid_type():
    """
    Test that Calculation.create raises a ValueError for unsupported types.
    
    This verifies that the factory pattern properly handles invalid inputs
    and provides clear error messages.
    """
    with pytest.raises(ValueError, match="Unsupported calculation type"):
        Calculation.create(
            calculation_type='modulus',  # unsupported type
            user_id=dummy_user_id(),
            inputs=[10, 3],
        )


def test_calculation_factory_case_insensitive():
    """
    Test that the factory is case-insensitive.
    
    The factory should accept 'Addition', 'ADDITION', 'addition', etc.
    """
    inputs = [5, 3]
    
    # Test various cases
    for calc_type in ['addition', 'Addition', 'ADDITION', 'AdDiTiOn']:
        calc = Calculation.create(
            calculation_type=calc_type,
            user_id=dummy_user_id(),
            inputs=inputs,
        )
        assert isinstance(calc, Addition), \
            f"Factory failed for case: {calc_type}"
        assert calc.get_result() == 8


# ============================================================================
# Tests for Input Validation (Edge Cases)
# ============================================================================

def test_invalid_inputs_for_addition():
    """
    Test that providing non-list inputs to Addition.get_result raises error.
    
    This verifies that calculations properly validate their inputs before
    attempting operations.
    """
    addition = Addition(user_id=dummy_user_id(), inputs="not-a-list")
    with pytest.raises(ValueError, match="Inputs must be a list of numbers."):
        addition.get_result()


def test_invalid_inputs_for_subtraction():
    """
    Test that providing fewer than two numbers raises a ValueError.
    
    All calculations require at least two inputs to be meaningful.
    """
    subtraction = Subtraction(user_id=dummy_user_id(), inputs=[10])
    with pytest.raises(
        ValueError,
        match="Inputs must be a list with at least two numbers."
    ):
        subtraction.get_result()


def test_invalid_inputs_for_multiplication():
    """
    Test that Multiplication requires at least two inputs.
    """
    multiplication = Multiplication(user_id=dummy_user_id(), inputs=[5])
    with pytest.raises(
        ValueError,
        match="Inputs must be a list with at least two numbers."
    ):
        multiplication.get_result()


def test_invalid_inputs_for_division():
    """
    Test that Division requires at least two inputs.
    """
    division = Division(user_id=dummy_user_id(), inputs=[10])
    with pytest.raises(
        ValueError,
        match="Inputs must be a list with at least two numbers."
    ):
        division.get_result()


def test_division_by_zero_in_middle():
    """
    Test division by zero when zero appears in the middle of inputs.
    
    This ensures zero validation works for any position after the first.
    """
    inputs = [100, 5, 0, 2]
    division = Division(user_id=dummy_user_id(), inputs=inputs)
    with pytest.raises(ValueError, match="Cannot divide by zero."):
        division.get_result()


def test_division_by_zero_at_end():
    """
    Test division by zero when zero is the last input.
    """
    inputs = [50, 5, 0]
    division = Division(user_id=dummy_user_id(), inputs=inputs)
    with pytest.raises(ValueError, match="Cannot divide by zero."):
        division.get_result()


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
    user_id = dummy_user_id()
    
    # Create a list of different calculation types
    calculations = [
        Calculation.create('addition', user_id, [1, 2, 3]),
        Calculation.create('subtraction', user_id, [10, 3]),
        Calculation.create('multiplication', user_id, [2, 3, 4]),
        Calculation.create('division', user_id, [100, 5]),
    ]
    
    # Each calculation maintains its specific type
    assert isinstance(calculations[0], Addition)
    assert isinstance(calculations[1], Subtraction)
    assert isinstance(calculations[2], Multiplication)
    assert isinstance(calculations[3], Division)
    
    # All calculations share the same interface
    results = [calc.get_result() for calc in calculations]
    
    # Each produces its type-specific result
    assert results == [6, 7, 24, 20]


def test_polymorphic_method_calling():
    """
    Test that polymorphic methods work correctly.
    
    This demonstrates that you can call get_result() on any Calculation
    subclass and get the correct type-specific behavior without knowing
    the exact subclass type at compile time.
    """
    user_id = dummy_user_id()
    inputs = [10, 2]
    
    # Create calculations dynamically based on type string
    calc_types = ['addition', 'subtraction', 'multiplication', 'division']
    expected_results = [12, 8, 20, 5]
    
    for calc_type, expected in zip(calc_types, expected_results):
        calc = Calculation.create(calc_type, user_id, inputs)
        # Polymorphic method call: same method name, different behavior
        result = calc.get_result()
        assert result == expected, \
            f"{calc_type} failed: expected {expected}, got {result}"
