# app/schemas/calculation.py
"""
Calculation Pydantic Schemas

This module defines Pydantic schemas for validating calculation data at the
API boundary. Pydantic provides automatic validation, serialization, and
documentation generation for FastAPI.

Key Concepts:
- Schemas define the shape of data coming in/out of the API
- Validation happens automatically before data reaches your code
- Field validators provide custom validation logic
- Model validators can validate across multiple fields
- ConfigDict controls schema behavior and documentation

Design Pattern: Data Transfer Objects (DTOs)
These schemas act as DTOs, defining contracts between API and clients.

Changes from the original inputs-list design (Module 11):
- 'inputs' (JSON list) has been replaced with 'a' and 'b' (two floats),
  matching the SQLAlchemy Calculation model fields exactly.
- CalculationRead is the canonical read schema (CalculationResponse is kept
  as an alias for backwards compatibility).
"""

from enum import Enum
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    model_validator,
    field_validator,
)
from typing import Optional
from uuid import UUID
from datetime import datetime


class CalculationType(str, Enum):
    """
    Enumeration of valid calculation types.

    Using an Enum provides:
    1. Type safety: Only valid values can be used
    2. Auto-completion: IDEs can suggest valid values
    3. Documentation: Automatically appears in OpenAPI spec
    4. Validation: Pydantic automatically rejects invalid values

    Inheriting from str makes this a string enum, so values serialise
    naturally as strings in JSON.
    """

    ADDITION = "addition"
    SUBTRACTION = "subtraction"
    MULTIPLICATION = "multiplication"
    DIVISION = "division"


class CalculationBase(BaseModel):
    """
    Base schema for calculation data.

    Defines the common fields shared by all calculation request/response
    schemas: type, a, and b.

    Design Pattern: DRY – common fields are defined once and reused in
    CalculationCreate and CalculationRead.

    Validators
    ----------
    normalise_type
        Runs BEFORE Pydantic's enum coercion (mode="before").
        Converts the raw string to lowercase so 'Addition' == 'addition'.

    reject_division_by_zero
        Runs AFTER all fields are validated (mode="after").
        Implements LBYL: we check for the error condition at the API
        boundary before any business logic or DB write occurs.
    """

    type: CalculationType = Field(
        ...,
        description="Type of calculation to perform",
        examples=["addition"],
    )
    a: float = Field(
        ...,
        description="First operand",
        examples=[10.0],
    )
    b: float = Field(
        ...,
        description="Second operand",
        examples=[5.0],
    )

    @field_validator("type", mode="before")
    @classmethod
    def normalise_type(cls, v):
        """
        Validate and normalise the calculation type to lowercase.

        This validator runs BEFORE Pydantic's standard enum validation
        (mode="before") so that 'Addition', 'ADDITION', etc. are all
        accepted and stored as 'addition'.

        Args:
            v: The raw value provided for the 'type' field.

        Returns:
            str: The normalised lowercase type string.

        Raises:
            ValueError: If v is not a string or not a recognised type.
        """
        allowed = {e.value for e in CalculationType}
        # Ensure v is a string and that its lowercase form is in the allowed set.
        if not isinstance(v, str) or v.lower() not in allowed:
            raise ValueError(
                f"Type must be one of: {', '.join(sorted(allowed))}"
            )
        return v.lower()

    @model_validator(mode="after")
    def reject_division_by_zero(self) -> "CalculationBase":
        """
        Reject division requests where b == 0.

        This model validator runs AFTER all individual fields have been
        validated, so both self.type and self.b are available.

        Business Rule: Division by zero is mathematically undefined.
        We catch it here (LBYL) to give the API client an immediate,
        clear error rather than letting it propagate into the DB layer.

        Returns:
            self: The validated model instance.

        Raises:
            ValueError: If type is 'division' and b is zero.
        """
        if self.type == CalculationType.DIVISION and self.b == 0:
            raise ValueError("Cannot divide by zero")
        return self

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {"type": "addition", "a": 10.5, "b": 3.0},
                {"type": "division", "a": 100.0, "b": 4.0},
            ]
        },
    )


class CalculationCreate(CalculationBase):
    """
    Schema for creating a new Calculation.

    Received by POST /calculations (or equivalent endpoint).
    Inherits type, a, b and their validators from CalculationBase.

    user_id is optional; in a production application it would be derived
    from the authenticated session token rather than sent in the request body.
    """

    user_id: Optional[UUID] = Field(
        None,
        description="UUID of the user who owns this calculation",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "addition",
                "a": 10.5,
                "b": 3.0,
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
            }
        }
    )


class CalculationRead(CalculationBase):
    """
    Schema for reading a Calculation from the database.

    Returned by GET /calculations/{id} (or equivalent endpoint).
    Includes all DB-generated fields: id, result, and audit timestamps.

    from_attributes=True allows Pydantic to populate this schema directly
    from a SQLAlchemy ORM instance using CalculationRead.model_validate(orm_obj).
    """

    id: UUID = Field(
        ...,
        description="Unique UUID of the calculation",
        examples=["123e4567-e89b-12d3-a456-426614174999"],
    )
    user_id: Optional[UUID] = Field(
        None,
        description="UUID of the user who owns this calculation",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    result: float = Field(
        ...,
        description="Pre-computed result of the calculation",
        examples=[13.5],
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the calculation was created",
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp when the calculation was last updated",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174999",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "type": "addition",
                "a": 10.5,
                "b": 3.0,
                "result": 13.5,
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00",
            }
        },
    )


# Keep the original name as an alias so any existing references still work.
CalculationResponse = CalculationRead


class CalculationUpdate(BaseModel):
    """
    Schema for updating an existing Calculation.

    Only the operands (a and/or b) can be changed after creation.
    The calculation type is immutable; if a different type is needed
    the caller should create a new record instead.

    All fields are Optional so partial updates are supported.
    """

    a: Optional[float] = Field(
        None,
        description="Updated first operand",
        examples=[42.0],
    )
    b: Optional[float] = Field(
        None,
        description="Updated second operand",
        examples=[7.0],
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": {"a": 42.0, "b": 7.0}},
    )
