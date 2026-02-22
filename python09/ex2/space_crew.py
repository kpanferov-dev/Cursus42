"""
space_crew.py
Master nested Pydantic models and complex data
relationships
"""

from pydantic import BaseModel, Field, model_validator
from enum import Enum
from datetime import datetime
from typing import List


class Rank(str, Enum):
    cadet = "cadet"
    officer = "officer"
    lieutenant = "lieutenant"
    captain = "captain"
    commander = "commander"


class CrewMember(BaseModel):
    member_id: str = Field(..., min_length=3, max_length=10)
    name: str = Field(..., min_length=2, max_length=50)
    rank: Rank
    age: int = Field(..., ge=18, le=80)
    specialization: str = Field(..., min_length=3, max_length=30)
    years_experience: int = Field(..., ge=0, le=50)
    is_active: bool = True


class SpaceMission(BaseModel):
    mission_id: str = Field(..., min_length=5, max_length=15)
    mission_name: str = Field(..., min_length=3, max_length=100)
    destination: str = Field(..., min_length=3, max_length=50)
    launch_date: datetime
    duration_days: int = Field(..., ge=1, le=3650)
    crew: List[CrewMember] = Field(..., min_length=1, max_length=12)
    mission_status: str = "planned"
    budget_millions: float = Field(..., ge=1.0, le=10000.0)

    @model_validator(mode="after")
    def validate_mission(self) -> "SpaceMission":
        if not self.mission_id.startswith("M"):
            raise ValueError('Mission ID must start with "M"')

        senior_ranks = {Rank.commander, Rank.captain}
        has_senior = any(member.rank in senior_ranks for member in self.crew)
        if not has_senior:
            raise ValueError("Mission must have at least " +
                             "one Commander or Captain")

        if self.duration_days > 365:
            experienced = sum(1 for m in self.crew if m.years_experience >= 5)
            if experienced / len(self.crew) < 0.5:
                raise ValueError(
                    "Long missions (> 365 days) require at least 50% of crew "
                    "to have 5+ years of experience"
                )

        inactive = [m.name for m in self.crew if not m.is_active]
        if inactive:
            raise ValueError(
                "All crew members must be active. " +
                f"Inactive members: {', '.join(inactive)}"
            )

        return self


def demonstrate_missions() -> None:
    print("Space Mission Crew Validation")
    print("="*41)

    print("Valid mission created:")

    valid_mission = SpaceMission(
        mission_id="M2024_MARS",
        mission_name="Mars Colony Establishment",
        destination="Mars",
        launch_date=datetime(2024, 6, 15, 9, 0, 0),
        duration_days=900,
        crew=[
            CrewMember(
                member_id="SC001",
                name="Sarah Connor",
                rank=Rank.commander,
                age=42,
                specialization="Mission Command",
                years_experience=20,
            ),
            CrewMember(
                member_id="JS002",
                name="John Smith",
                rank=Rank.lieutenant,
                age=35,
                specialization="Navigation",
                years_experience=10,
            ),
            CrewMember(
                member_id="AJ003",
                name="Alice Johnson",
                rank=Rank.officer,
                age=28,
                specialization="Engineering",
                years_experience=6,
            ),
        ],
        budget_millions=2500.0,
    )

    print(f"Mission: {valid_mission.mission_name}")
    print(f"ID: {valid_mission.mission_id}")
    print(f"Destination: {valid_mission.destination}")
    print(f"Duration: {valid_mission.duration_days} days")
    print(f"Budget: ${valid_mission.budget_millions}M")
    print(f"Crew size: {len(valid_mission.crew)}")
    print("Crew members:")
    for member in valid_mission.crew:
        print(f"  - {member.name} ({member.rank.value})" +
              f" - {member.specialization}")

    print("="*41)

    print("\nExpected validation error:")

    try:
        SpaceMission(
            mission_id="M9999_BAD",
            mission_name="Doomed Voyage",
            destination="Venus",
            launch_date=datetime(2024, 8, 1),
            duration_days=200,
            crew=[
                CrewMember(
                    member_id="RK001",
                    name="Rick Sanchez",
                    rank=Rank.cadet,          # No commander or captain
                    age=22,
                    specialization="Science",
                    years_experience=1,
                ),
            ],
            budget_millions=50.0,
        )
    except Exception as exc:
        for error in exc.errors():
            print(error["msg"].removeprefix("Value error, "))
            break


if __name__ == "__main__":
    demonstrate_missions()
