# backend/app/schemas/validate.py
"""Validation request/response schemas."""
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    severity: Severity
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    rule: Optional[str] = None


class ValidateRequest(BaseModel):
    template: str = Field(..., min_length=1, max_length=100000, description="IaC template content")
    provider: Optional[str] = Field(default=None, description="Provider hint for validation")
    target: Optional[str] = Field(default=None, description="Target cloud hint")


class ValidateResponse(BaseModel):
    valid: bool
    issues: List[ValidationIssue] = []
    summary: str = ""