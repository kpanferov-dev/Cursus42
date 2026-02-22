"""
alien_contact.py
Master custom validation using @model_validator
"""

from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from enum import Enum
from typing import Optional


class ContactType(str, Enum):
    """Class for enumeration"""
    radio = "radio"
    visual = "visual"
    physical = "physical"
    telepathic = "telepathic"


class AlienContact(BaseModel):
    """Class with data details"""
    contact_id: str = Field(..., min_length=5, max_length=15)
    timestamp: datetime
    location: str = Field(..., min_length=3, max_length=100)
    contact_type: ContactType
    signal_strength: float = Field(..., ge=0.0, le=10.0)
    duration_minutes: int = Field(..., ge=1, le=1440)
    witness_count: int = Field(..., ge=1, le=100)
    message_received: Optional[str] = Field(None, max_length=500)
    is_verified: bool = False

    @model_validator(mode='after')
    def validate_contact(self) -> None:
        """Validate automatically after Pydantic def validations"""
        if not self.contact_id.startswith("AC"):
            raise ValueError("Contact ID must start with 'AC' (Alien Contact)")

        if self.contact_type == ContactType.physical and not self.is_verified:
            raise ValueError("Physical contact reports must be verified")

        if (self.contact_type == ContactType.telepathic and
           self.witness_count < 3):
            raise ValueError("Telepathic contact " +
                             "requires at least 3 witnesses")

        if self.signal_strength > 7.0 and not self.message_received:
            raise ValueError("Strong signals (>7.0) should " +
                             "include a received message")

        return self


def demonstrate_alien_contact_reports() -> None:
    """Main"""
    valid_report = AlienContact(
        contact_id="AC_2024_001",
        timestamp=datetime(2026, 2, 21, 14, 30),
        location="Area 51, Nevada",
        contact_type=ContactType.radio,
        signal_strength=8.5,
        duration_minutes=45,
        witness_count=5,
        message_received="Greetings from Zeta Reticuli"
    )
    print("=" * 40)
    print("Valid contact report:")
    print(f"ID: {valid_report.contact_id}")
    print(f"Type: {valid_report.contact_type}")
    print(f"Location: {valid_report.location}")
    print(f"Signal: {valid_report.signal_strength}/10")
    print(f"Duration: {valid_report.duration_minutes} minutes")
    print(f"Witnesses: {valid_report.witness_count}")
    print(f"Message: '{valid_report.message_received}'\n")
    print("=" * 40)

    try:
        invalid_report = AlienContact(
            contact_id="AC_2024_002",
            timestamp=datetime(2026, 2, 21, 15, 0),
            location="Mars",
            contact_type=ContactType.telepathic,
            signal_strength=6.0,
            duration_minutes=30,
            witness_count=2,  # < 3 error
            message_received=None
        )
        print(invalid_report)
    except ValueError as e:
        print("Expected validation error:")
        for error in e.errors():
            if ", " in error['msg']:
                print(error['msg'].split(", ")[1])
            else:
                print(error['msg'])


if __name__ == "__main__":
    demonstrate_alien_contact_reports()
