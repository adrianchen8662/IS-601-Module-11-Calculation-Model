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

Fields (per the Module 11 spec):
- id        : UUID primary key
- a         : First operand (Float)
- b         : Second operand (Float)
- type      : Discriminator string ('addition' | 'subtraction' |
              'multiplication' | 'division')
- result    : Pre-computed and stored result (Float, optional)
- user_id   : Optional FK → users.id (nullable for testing convenience)
- created_at / updated_at : audit timestamps
"""

from datetime import datetime
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Calculation(Base):
    """
    Base SQLAlchemy model for all calculation types.

    This class uses SQLAlchemy's single-table polymorphic inheritance.
    The __mapper_args__ dict tells SQLAlchemy to:
      - Use the 'type' column as the discriminator (polymorphic_on)
      - Assign the identity 'calculation' to this base class

    When SQLAlchemy loads a row it reads the 'type' column and automatically
    instantiates the correct subclass (Addition, Subtraction, etc.), so callers
    never need to branch on the type string themselves.

    Factory Pattern
    ---------------
    Calculation.create() centralises object creation. It:
      1. Maps the type string to the correct subclass
      2. Instantiates that subclass with a and b
      3. Pre-computes and stores the result
    This keeps creation logic in one place and makes it easy to add new types.
    """

    __tablename__ = "calculations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        # nullable=True so unit/integration tests can create calculations
        # without needing a real user row in the database.
        nullable=True,
        index=True,
    )

    # ── Operands ──────────────────────────────────────────────────────────────
    a = Column(
        Float,
        nullable=False,
        doc="First operand of the calculation.",
    )

    b = Column(
        Float,
        nullable=False,
        doc="Second operand of the calculation.",
    )

    # ── Discriminator ─────────────────────────────────────────────────────────
    type = Column(
        String(50),
        nullable=False,
        index=True,
        doc=(
            "Discriminator column for polymorphic inheritance. "
            "Values: 'addition', 'subtraction', 'multiplication', 'division'."
        ),
    )

    # ── Result ────────────────────────────────────────────────────────────────
    result = Column(
        Float,
        nullable=True,
        doc=(
            "Pre-computed result stored at creation time. "
            "Can also be obtained on demand via get_result()."
        ),
    )

    # ── Audit timestamps ──────────────────────────────────────────────────────
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    user = relationship(
        "User",
        back_populates="calculations",
        doc="Bidirectional relationship: calculation.user ↔ user.calculations.",
    )

    # ── Polymorphic configuration ──────────────────────────────────────────────
    __mapper_args__ = {
        "polymorphic_on": "type",
        "polymorphic_identity": "calculation",
    }

    # ──────────────────────────────────────────────────────────────────────────
    # Factory Method
    # ──────────────────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        calculation_type: str,
        a: float,
        b: float,
        user_id: uuid.UUID = None,
    ) -> "Calculation":
        """
        Factory method to create the appropriate calculation subclass.

        This implements the Factory Pattern, which provides a centralised way
        to create objects without specifying their exact class. The factory
        determines which subclass to instantiate based on calculation_type.

        Benefits of Factory Pattern:
        1. Encapsulation: Object creation logic is in one place
        2. Flexibility: Easy to add new calculation types
        3. Type Safety: Returns a strongly-typed subclass instance
        4. Result Pre-computation: result is computed and stored immediately

        Args:
            calculation_type (str): Type of calculation, e.g. 'addition'.
                                    Case-insensitive.
            a (float):              First operand.
            b (float):              Second operand.
            user_id (UUID, optional): UUID of the owning user.

        Returns:
            Calculation: An instance of the appropriate subclass with
                         result already set.

        Raises:
            ValueError: If calculation_type is not one of the supported types.
            ValueError: If the operation itself is invalid (e.g. division by 0).

        Example:
            calc = Calculation.create('addition', a=1, b=2)
            assert isinstance(calc, Addition)
            assert calc.result == 3.0
        """
        _type_map = {
            "addition": Addition,
            "subtraction": Subtraction,
            "multiplication": Multiplication,
            "division": Division,
        }

        calc_class = _type_map.get(calculation_type.lower())
        if calc_class is None:
            raise ValueError(
                f"Unsupported calculation type: {calculation_type}"
            )

        # Instantiate the correct subclass
        instance = calc_class(a=a, b=b, user_id=user_id)

        # Pre-compute and store the result.
        # get_result() may raise ValueError (e.g. division by zero) which
        # propagates to the caller before any DB write occurs.
        instance.result = instance.get_result()
        return instance

    # ──────────────────────────────────────────────────────────────────────────
    # Polymorphic interface
    # ──────────────────────────────────────────────────────────────────────────

    def get_result(self) -> float:
        """
        Compute and return the result of this calculation.

        This is the abstract method in the Template Method pattern; each
        subclass provides its own implementation.

        Raises:
            NotImplementedError: If called directly on the base Calculation
                                 class rather than a subclass.
        """
        raise NotImplementedError(  # pragma: no cover
            "Subclasses must implement get_result() method"
        )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Calculation(type={self.type}, a={self.a}, b={self.b}, "
            f"result={self.result})>"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Subclasses
# ──────────────────────────────────────────────────────────────────────────────

class Addition(Calculation):
    """
    Addition calculation subclass.

    Polymorphic Identity: 'addition'
    Operation: result = a + b

    Example:
        calc = Addition(a=10, b=5)
        assert calc.get_result() == 15.0
    """

    __mapper_args__ = {"polymorphic_identity": "addition"}

    def get_result(self) -> float:
        """
        Return the sum of a and b.

        Returns:
            float: a + b
        """
        return self.a + self.b


class Subtraction(Calculation):
    """
    Subtraction calculation subclass.

    Polymorphic Identity: 'subtraction'
    Operation: result = a - b

    Example:
        calc = Subtraction(a=10, b=3)
        assert calc.get_result() == 7.0
    """

    __mapper_args__ = {"polymorphic_identity": "subtraction"}

    def get_result(self) -> float:
        """
        Subtract b from a and return the result.

        Returns:
            float: a - b
        """
        return self.a - self.b


class Multiplication(Calculation):
    """
    Multiplication calculation subclass.

    Polymorphic Identity: 'multiplication'
    Operation: result = a * b

    Example:
        calc = Multiplication(a=3, b=4)
        assert calc.get_result() == 12.0
    """

    __mapper_args__ = {"polymorphic_identity": "multiplication"}

    def get_result(self) -> float:
        """
        Return the product of a and b.

        Returns:
            float: a * b
        """
        return self.a * self.b


class Division(Calculation):
    """
    Division calculation subclass.

    Polymorphic Identity: 'division'
    Operation: result = a / b

    Note: Uses EAFP (Easier to Ask for Forgiveness than Permission) –
    the zero check happens inside the operation rather than before it.
    The schema layer (CalculationCreate) also rejects b=0 before this
    point is reached via an API endpoint.

    Example:
        calc = Division(a=100, b=4)
        assert calc.get_result() == 25.0
    """

    __mapper_args__ = {"polymorphic_identity": "division"}

    def get_result(self) -> float:
        """
        Divide a by b and return the quotient.

        Returns:
            float: a / b

        Raises:
            ValueError: If b is zero (division by zero is undefined).
        """
        if self.b == 0:
            raise ValueError("Cannot divide by zero.")
        return self.a / self.b
