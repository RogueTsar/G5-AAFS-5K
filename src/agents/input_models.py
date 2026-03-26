# pydantic schema validation
from typing import Literal, List
from pydantic import BaseModel, Field, field_validator



class InputRequest(BaseModel):
    raw_input: str = Field(..., min_length=1, max_length=120)

    @field_validator("raw_input")
    @classmethod
    def strip_input(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Input cannot be empty.")
        return v


class InputClassification(BaseModel):
    entity_type: Literal["company", "individual", "unknown"]
    intent: Literal["entity_lookup", "broad_search", "unsafe"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str


class InputValidationResult(BaseModel):
    raw_input: str
    normalized_input: str
    safe_query: str
    entity_type: Literal["company", "individual", "unknown"]
    intent: Literal["entity_lookup", "broad_search", "unsafe"]
    is_safe: bool
    is_valid: bool
    risk_flags: List[str]
    rationale: str = ""