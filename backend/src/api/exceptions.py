"""Centralized exception handling for the API."""

from typing import Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.logging_config import get_logger

logger = get_logger(__name__)


class DABException(Exception):
    """Base exception for Data Capsule Server."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or "INTERNAL_ERROR"
        self.details = details or {}
        super().__init__(message)


class NotFoundError(DABException):
    """Resource not found."""

    def __init__(self, resource_type: str, identifier: str):
        super().__init__(
            message=f"{resource_type} not found: {identifier}",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details={"resource_type": resource_type, "identifier": identifier},
        )


class ValidationError_(DABException):
    """Validation error for input data."""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            details={"field": field, **(details or {})},
        )


class ConflictError(DABException):
    """Resource already exists or conflict."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            details=details,
        )


class IngestionError(DABException):
    """Error during metadata ingestion."""

    def __init__(self, message: str, source_type: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="INGESTION_ERROR",
            details={"source_type": source_type, **(details or {})},
        )


class RuleValidationError(DABException):
    """Error validating conformance rules."""

    def __init__(self, message: str, rule_id: Optional[str] = None, details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="RULE_VALIDATION_ERROR",
            details={"rule_id": rule_id, **(details or {})},
        )


class DatabaseError(DABException):
    """Database operation error."""

    def __init__(self, message: str = "Database operation failed", details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="DATABASE_ERROR",
            details=details,
        )


def create_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: Optional[dict] = None,
    request_id: Optional[str] = None,
) -> dict:
    """Create a standardized error response."""
    response = {
        "error": {
            "code": error_code,
            "message": message,
            "status": status_code,
        }
    }
    if details:
        response["error"]["details"] = details
    if request_id:
        response["error"]["request_id"] = request_id
    return response


async def dab_exception_handler(request: Request, exc: DABException) -> JSONResponse:
    """Handle DAB custom exceptions."""
    logger.warning(
        f"DAB Exception: {exc.error_code} - {exc.message}",
        extra={"error_code": exc.error_code, "details": exc.details},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            status_code=exc.status_code,
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
        ),
    )


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    logger.warning(f"Validation error: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": errors},
        ),
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy database errors."""
    logger.error(f"Database error: {str(exc)}", exc_info=True)

    if isinstance(exc, IntegrityError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=create_error_response(
                status_code=status.HTTP_409_CONFLICT,
                error_code="INTEGRITY_ERROR",
                message="Database integrity constraint violated",
            ),
        )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=create_error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="DATABASE_ERROR",
            message="Database operation failed. Please try again later.",
        ),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred. Please try again later.",
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(DABException, dab_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    # Generic handler should be last
    app.add_exception_handler(Exception, generic_exception_handler)
