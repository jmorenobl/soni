"""Schemas for slot extraction."""

from pydantic import BaseModel, Field

from soni.core.commands import SetSlot


class SlotExtractionInput(BaseModel):
    """Input for slot extraction."""

    name: str = Field(description="Slot identifier")
    slot_type: str = Field(description="Data type: string, float, date, city, etc.")
    description: str = Field(default="", description="What this slot expects")
    examples: list[str] = Field(default_factory=list, description="Example valid values")

    def __str__(self) -> str:
        examples_str = f" (e.g., {', '.join(self.examples[:3])})" if self.examples else ""
        return f"- {self.name} ({self.slot_type}): {self.description}{examples_str}"


class SlotExtractionResult(BaseModel):
    """Result of slot extraction."""

    extracted_slots: list[SetSlot] = Field(
        default_factory=list,
        description="List of SetSlot commands",
    )
