"""Parser for the fly_in drone network map file format."""

import re
from typing import Optional, Tuple, Dict
from zone import Zone, ZoneType
from connection import Connection
from graph import Graph


class ParseError(Exception):
    """Raised when a map file contains invalid syntax or semantics."""

    def __init__(self, message: str, line_number: int = -1) -> None:
        """Initialize parse error with context.

        Args:
            message: Description of the error.
            line_number: Line number where error occurred.
        """
        if line_number >= 0:
            super().__init__(f"Line {line_number}: {message}")
        else:
            super().__init__(message)
        self.line_number = line_number


class MapParser:
    """Parses drone network map files into a Graph object."""

    # Regex patterns
    _NB_DRONES_PATTERN = re.compile(r"^nb_drones:\s*(\d+)\s*$")
    _ZONE_PATTERN = re.compile(
        r"^(start_hub|end_hub|hub):\s*(\S+)\s+(-?\d+)\s+(-?\d+)"
        r"(?:\s+\[([^\]]*)\])?\s*$"
    )
    _CONNECTION_PATTERN = re.compile(
        r"^connection:\s*([^-\s]+)-([^-\s\[]+)"
        r"(?:\s+\[([^\]]*)\])?\s*$"
    )
    _METADATA_PAIR = re.compile(r"(\w+)=(\S+)")

    def __init__(self) -> None:
        """Initialize the parser."""
        self._graph: Optional[Graph] = None

    def parse_file(self, filepath: str) -> Graph:
        """Parse a map file and return a populated Graph.

        Args:
            filepath: Path to the map file.

        Returns:
            Populated Graph instance.

        Raises:
            ParseError: On any syntax or semantic error.
            FileNotFoundError: If the file does not exist.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Map file not found: {filepath}")

        return self.parse_string(content)

    def parse_string(self, content: str) -> Graph:
        """Parse map content from a string.

        Args:
            content: Raw map file content.

        Returns:
            Populated Graph instance.

        Raises:
            ParseError: On any syntax or semantic error.
        """
        self._graph = Graph()
        lines = content.splitlines()
        nb_drones_found = False
        start_count = 0
        end_count = 0

        for line_num, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # nb_drones
            m = self._NB_DRONES_PATTERN.match(line)
            if m:
                if nb_drones_found:
                    raise ParseError(
                        "Duplicate nb_drones definition.", line_num)
                value = int(m.group(1))
                if value <= 0:
                    raise ParseError(
                        f"nb_drones must be a positive integer, got {value}.",
                        line_num
                    )
                self._graph.nb_drones = value
                nb_drones_found = True
                continue

            # Zone definition
            m = self._ZONE_PATTERN.match(line)
            if m:
                if not nb_drones_found:
                    raise ParseError(
                        "nb_drones must be defined before zones.", line_num
                    )
                hub_type = m.group(1)
                name = m.group(2)
                x = int(m.group(3))
                y = int(m.group(4))
                meta_str = m.group(5) or ""

                is_start = hub_type == "start_hub"
                is_end = hub_type == "end_hub"

                if is_start:
                    start_count += 1
                    if start_count > 1:
                        raise ParseError(
                            "Multiple start_hub zones defined.", line_num)
                if is_end:
                    end_count += 1
                    if end_count > 1:
                        raise ParseError(
                            "Multiple end_hub zones defined.", line_num)

                meta = self._parse_metadata(meta_str, line_num)
                zone_type = self._parse_zone_type(
                    meta.get("zone", "normal"), line_num
                )
                color = meta.get("color")
                max_drones_str = meta.get("max_drones", "1")
                max_drones = self._parse_positive_int(
                    max_drones_str, "max_drones", line_num
                )

                zone = Zone(
                    name=name,
                    x=x,
                    y=y,
                    zone_type=zone_type,
                    color=color,
                    max_drones=max_drones,
                    is_start=is_start,
                    is_end=is_end,
                )
                try:
                    self._graph.add_zone(zone)
                except ValueError as e:
                    raise ParseError(str(e), line_num)
                continue

            # Connection definition
            m = self._CONNECTION_PATTERN.match(line)
            if m:
                name_a = m.group(1).strip()
                name_b = m.group(2).strip()
                meta_str = m.group(3) or ""

                zone_a = self._graph.get_zone(name_a)
                zone_b = self._graph.get_zone(name_b)

                if zone_a is None:
                    raise ParseError(
                        f"Connection references undefined zone '{name_a}'.",
                        line_num
                    )
                if zone_b is None:
                    raise ParseError(
                        f"Connection references undefined zone '{name_b}'.",
                        line_num
                    )

                meta = self._parse_metadata(meta_str, line_num)
                max_cap_str = meta.get("max_link_capacity", "1")
                max_cap = self._parse_positive_int(
                    max_cap_str, "max_link_capacity", line_num
                )

                conn = Connection(zone_a, zone_b, max_cap)
                try:
                    self._graph.add_connection(conn)
                except ValueError as e:
                    raise ParseError(str(e), line_num)
                continue

            raise ParseError(f"Unrecognized line syntax: '{line}'", line_num)

        # Validate required fields
        if not nb_drones_found:
            raise ParseError("Missing nb_drones definition.")
        if start_count == 0:
            raise ParseError("Missing start_hub definition.")
        if end_count == 0:
            raise ParseError("Missing end_hub definition.")

        return self._graph

    def _parse_metadata(
        self, meta_str: str, line_num: int
    ) -> Dict[str, str]:
        """Parse key=value metadata pairs from a bracket-enclosed string.

        Args:
            meta_str: Raw metadata string (without brackets).
            line_num: Line number for error context.

        Returns:
            Dictionary of key-value metadata pairs.

        Raises:
            ParseError: If metadata syntax is invalid.
        """
        result: Dict[str, str] = {}
        if not meta_str.strip():
            return result

        pairs = self._METADATA_PAIR.findall(meta_str)
        for key, value in pairs:
            result[key] = value

        # Validate no unknown characters remain (crude check)
        cleaned = self._METADATA_PAIR.sub("", meta_str).strip()
        if cleaned:
            raise ParseError(
                f"Invalid metadata syntax near: '{cleaned}'", line_num
            )

        return result

    def _parse_zone_type(self, type_str: str, line_num: int) -> ZoneType:
        """Parse zone type string into ZoneType enum.

        Args:
            type_str: Zone type string.
            line_num: Line number for error context.

        Returns:
            Corresponding ZoneType value.

        Raises:
            ParseError: If type string is not recognized.
        """
        try:
            return ZoneType(type_str.lower())
        except ValueError:
            valid = [t.value for t in ZoneType]
            raise ParseError(
                f"Invalid zone type '{type_str}'. Must be one of: {valid}",
                line_num,
            )

    def _parse_positive_int(
        self, value_str: str, field_name: str, line_num: int
    ) -> int:
        """Parse and validate a positive integer.

        Args:
            value_str: String representation of the value.
            field_name: Field name for error messages.
            line_num: Line number for error context.

        Returns:
            Parsed positive integer.

        Raises:
            ParseError: If value is not a positive integer.
        """
        try:
            value = int(value_str)
        except ValueError:
            raise ParseError(
                f"'{field_name}' must be an integer, got '{value_str}'.",
                line_num)
        if value <= 0:
            raise ParseError(
                f"'{field_name}' must be a positive integer, got {value}.",
                line_num)
        return value

    def _parse_tuple(self, raw: str, line_num: int) -> Tuple[str, str]:
        """Split a raw connection string into two zone names.

        Args:
            raw: Raw connection string like 'zone1-zone2'.
            line_num: Line number for error context.

        Returns:
            Tuple of (zone_a_name, zone_b_name).

        Raises:
            ParseError: If syntax is invalid.
        """
        parts = raw.split("-", 1)
        if len(parts) != 2:
            raise ParseError(
                f"Connection must be 'zone1-zone2', got '{raw}'.", line_num
            )
        return parts[0].strip(), parts[1].strip()
