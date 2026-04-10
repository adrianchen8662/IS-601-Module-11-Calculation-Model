# app/models/calculation.py
"""
Calculation Models with Polymorphic Inheritance

This module demonstrates SQLAlchemy's polymorphic inheritance pattern, where
multiple calculation types (Addition, Subtraction, Multiplication, Division)
inherit from a base Calculation model. This is a powerful ORM feature that
allows different types of calculations to be stored in the same table while
maintaining type-specific behavior.

Polymorphic Inheritance Explained:
- Single Table Inheritance: All calculation types share one table
- Discriminator Column: The 'type' column determines which class to use
- Polymorphic Identity: Each subclass has a unique identifier
- Factory Pattern: Calculation.create() returns the appropriate subclass

This design pattern allows for:
1. Querying all calculations together: session.query(Calculation).all()
2. Automatic type resolution: SQLAlchemy returns the correct subclass
3. Type-specific behavior: Each subclass implements get_result() differently
4. Easy extensibility: Add new calculation types by creating new subclasses
"""

from datetime import datetime
import uuid
from typing import List
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declared_attr
from app.database import Base


class AbstractCalculation:
    """
    Abstract base class defining common attributes for all calculations.
    
    This class uses SQLAlchemy's @declared_attr decorator to define columns
    that will be shared across all calculation types. The @declared_attr
    decorator is necessary when defining columns in a mixin class.
    
    Design Pattern: This follows the Template Method pattern, where the
    abstract class defines the structure and subclasses provide specific
    implementations.
    """

    @declared_attr
    def __tablename__(cls):
        """All calculation types share the 'calculations' table"""
        return 'calculations'

    @declared_attr
    def id(cls):
        """Unique identifier for each calculation (UUID for distribution)"""
        return Column(
            UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            nullable=False
        )

    @declared_attr
    def user_id(cls):
        """
        Foreign key to the user who owns this calculation.
        
        CASCADE delete ensures calculations are deleted when user is deleted.
        Index improves query performance when filtering by user_id.
        """
        return Column(
            UUID(as_uuid=True),
            ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True
        )

    @declared_attr
    def type(cls):
        """
        Discriminator column for polymorphic inheritance.
        
        This column tells SQLAlchemy which subclass to instantiate when
        loading records from the database. Values include: 'addition',
        'subtraction', 'multiplication', 'division'.
        """
        return Column(
            String(50),
            nullable=False,
            index=True
        )

    @declared_attr
    def inputs(cls):
        """
        JSON column storing the list of numbers for the calculation.
        
        Using JSON allows for flexible storage of variable-length input lists.
        PostgreSQL's native JSON support provides efficient querying and
        indexing capabilities.
        """
        return Column(
            JSON,
            nullable=False
        )

    @declared_attr
    def result(cls):
        """
        The computed result of the calculation.
        
        Stored as Float to handle decimal values. Can be NULL initially
        and computed on-demand using get_result() method.
        """
        return Column(
            Float,
            nullable=True
        )

    @declared_attr
    def created_at(cls):
        """Timestamp when the calculation was created"""
        return Column(
            DateTime,
            default=datetime.utcnow,
            nullable=False
        )

    @declared_attr
    def updated_at(cls):
        """Timestamp when the calculation was last updated"""
        return Column(
            DateTime,
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
            nullable=False
        )

    @declared_attr
    def user(cls):
        """
        Relationship to the User model.
        
        back_populates creates a bidirectional relationship, allowing access
        to user.calculations and calculation.user.
        """
        return relationship("User", back_populates="calculations")

    @classmethod
    def create(cls, calculation_type: str, user_id: uuid.UUID,
               inputs: List[float]) -> "Calculation":
        """
        Factory method to create the appropriate calculation subclass.
        
        This implements the Factory Pattern, which provides a centralized way
        to create objects without specifying their exact class. The factory
        determines which subclass to instantiate based on calculation_type.
        
        Benefits of Factory Pattern:
        1. Encapsulation: Object creation logic is in one place
        2. Flexibility: Easy to add new calculation types
        3. Type Safety: Returns strongly-typed subclass instances
        
        Args:
            calculation_type: Type of calculation (e.g., 'addition')
            user_id: UUID of the user creating the calculation
            inputs: List of numbers to calculate
            
        Returns:
            An instance of the appropriate Calculation subclass
            
        Raises:
            ValueError: If calculation_type is not supported
            
        Example:
            calc = Calculation.create('addition', user_id, [1, 2, 3])
            assert isinstance(calc, Addition)
            assert calc.get_result() == 6
        """
        calculation_classes = {
            'addition': Addition,
            'subtraction': Subtraction,
            'multiplication': Multiplication,
            'division': Division,
        }
        calculation_class = calculation_classes.get(calculation_type.lower())
        if not calculation_class:
            raise ValueError(
                f"Unsupported calculation type: {calculation_type}"
            )
        return calculation_class(user_id=user_id, inputs=inputs)

    def get_result(self) -> float:
        """
        Abstract method to compute the calculation result.
        
        Each subclass must implement this method with its specific logic.
        This follows the Template Method pattern where the interface is
        defined here but implementation is deferred to subclasses.
        
        Raises:
            NotImplementedError: If called on base class
        """
        raise NotImplementedError(
            "Subclasses must implement get_result() method"
        )

    def __repr__(self):
        return f"<Calculation(type={self.type}, inputs={self.inputs})>"


class Calculation(Base, AbstractCalculation):
    """
    Base calculation model with polymorphic configuration.
    
    This class combines SQLAlchemy's Base with our AbstractCalculation mixin
    and configures polymorphic inheritance through __mapper_args__.
    
    Polymorphic Configuration:
    - polymorphic_on: Specifies the discriminator column (type)
    - polymorphic_identity: The value stored for this base class
    
    When querying Calculation, SQLAlchemy automatically:
    1. Reads the 'type' column value
    2. Determines the appropriate subclass
    3. Returns an instance of that subclass
    """
    __mapper_args__ = {
        "polymorphic_on": "type",
        "polymorphic_identity": "calculation",
    }


class Addition(Calculation):
    """
    Addition calculation subclass.
    
    Polymorphic Identity: 'addition'
    Operation: Sums all numbers in the inputs list
    
    Example:
        add = Addition(user_id=user_id, inputs=[1, 2, 3])
        result = add.get_result()  # Returns 6
    """
    __mapper_args__ = {"polymorphic_identity": "addition"}

    def get_result(self) -> float:
        """
        Calculate the sum of all input numbers.
        
        Returns:
            The sum of all inputs
            
        Raises:
            ValueError: If inputs is not a list or has fewer than 2 numbers
        """
        if not isinstance(self.inputs, list):
            raise ValueError("Inputs must be a list of numbers.")
        if len(self.inputs) < 2:
            raise ValueError(
                "Inputs must be a list with at least two numbers."
            )
        return sum(self.inputs)


class Subtraction(Calculation):
    """
    Subtraction calculation subclass.
    
    Polymorphic Identity: 'subtraction'
    Operation: Subtracts subsequent numbers from the first number
    
    Example:
        sub = Subtraction(user_id=user_id, inputs=[10, 3, 2])
        result = sub.get_result()  # Returns 5 (10 - 3 - 2)
    """
    __mapper_args__ = {"polymorphic_identity": "subtraction"}

    def get_result(self) -> float:
        """
        Subtract all subsequent numbers from the first number.
        
        Returns:
            The result of sequential subtraction
            
        Raises:
            ValueError: If inputs is not a list or has fewer than 2 numbers
        """
        if not isinstance(self.inputs, list):
            raise ValueError("Inputs must be a list of numbers.")
        if len(self.inputs) < 2:
            raise ValueError(
                "Inputs must be a list with at least two numbers."
            )
        result = self.inputs[0]
        for value in self.inputs[1:]:
            result -= value
        return result


class Multiplication(Calculation):
    """
    Multiplication calculation subclass.
    
    Polymorphic Identity: 'multiplication'
    Operation: Multiplies all numbers in the inputs list
    
    Example:
        mult = Multiplication(user_id=user_id, inputs=[2, 3, 4])
        result = mult.get_result()  # Returns 24
    """
    __mapper_args__ = {"polymorphic_identity": "multiplication"}

    def get_result(self) -> float:
        """
        Calculate the product of all input numbers.
        
        Returns:
            The product of all inputs
            
        Raises:
            ValueError: If inputs is not a list or has fewer than 2 numbers
        """
        if not isinstance(self.inputs, list):
            raise ValueError("Inputs must be a list of numbers.")
        if len(self.inputs) < 2:
            raise ValueError(
                "Inputs must be a list with at least two numbers."
            )
        result = 1
        for value in self.inputs:
            result *= value
        return result


class Division(Calculation):
    """
    Division calculation subclass.
    
    Polymorphic Identity: 'division'
    Operation: Divides the first number by subsequent numbers sequentially
    
    Example:
        div = Division(user_id=user_id, inputs=[100, 2, 5])
        result = div.get_result()  # Returns 10 (100 / 2 / 5)
        
    Note: This implementation uses EAFP (Easier to Ask for Forgiveness than
    Permission) by checking for zero during calculation rather than before.
    """
    __mapper_args__ = {"polymorphic_identity": "division"}

    def get_result(self) -> float:
        """
        Divide the first number by all subsequent numbers sequentially.
        
        Returns:
            The result of sequential division
            
        Raises:
            ValueError: If inputs is not a list, has fewer than 2 numbers,
                       or if attempting to divide by zero
        """
        if not isinstance(self.inputs, list):
            raise ValueError("Inputs must be a list of numbers.")
        if len(self.inputs) < 2:
            raise ValueError(
                "Inputs must be a list with at least two numbers."
            )
        result = self.inputs[0]
        for value in self.inputs[1:]:
            if value == 0:
                raise ValueError("Cannot divide by zero.")
            result /= value
        return result
