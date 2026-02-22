"""
space_statio.py
Implements a Class SpaceStation
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class SpaceStation(BaseModel):
    """Class with all stats"""
    station_id: str = Field(..., min_length=3, max_length=10)
    name: str = Field(..., min_length=1, max_length=50)
    crew_size: int = Field(..., ge=1, le=20)
    power_level: float = Field(..., ge=0.0, le=100.0)
    oxygen_level: float = Field(..., ge=0.0, le=100.0)
    last_maintenance: datetime
    is_operational: bool = True
    notes: Optional[str] = Field(None, max_length=200)


def main() -> None:
    """ main """
    # Valid Space Station instance
    print("="*40)
    try:
        station = SpaceStation(
            station_id="ISS001",
            name="International Space Station",
            crew_size=6,
            power_level=85.5,
            oxygen_level=92.3,
            last_maintenance=datetime(2026, 2, 22),
        )
        print("Valid station created:")
        print(f"ID: {station.station_id}")
        print(f"Name: {station.name}")
        print(f"Crew: {station.crew_size} people")
        print(f"Power: {station.power_level}%")
        print(f"Oxygen: {station.oxygen_level}%")
        print(f"Status: {'Operational' if station.is_operational
                         else 'Non-operational'}")
    except Exception as e:
        print(f"Error creating valid station: {e}")

    print()
    print("="*40)
    try:
        invalid_station = SpaceStation(
            station_id="STN002",
            name="Invalid Space Station",
            crew_size=25,  # Invalid crew size
            power_level=50.0,
            oxygen_level=80.0,
            last_maintenance=datetime(2026, 2, 21),
        )
        print(invalid_station)
    except Exception as e:
        print("Error creating valid station:")
        for error in e.errors():
            print(f"{error["msg"]}")


if __name__ == "__main__":
    main()
