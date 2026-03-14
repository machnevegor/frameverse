from typing import Literal

from pydantic import BaseModel, Field


class PaginationInfo(BaseModel):
    """This object represents a pagination info."""

    page: int = Field(..., description="Page number (1-based).")
    per_page: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages.")
    total_items: int = Field(..., description="Total number of items.")
    has_next: bool = Field(..., description="_True_, if the current page is not the last page.")
    cursor: str | None = Field(default=None, description="_Optional_. ID of the last item.")


class FormattedError(BaseModel):
    """This object represents a formatted error."""

    message: str = Field(..., description="Formatted error message.")
    success: Literal[False] = Field(..., description="Always _False_.")
