"""Parser for the Fly-in map file format.

The :class:`MapParser` turns a textual map description into a validated
:class:`~models.Network`. Every syntactic or semantic problem raises a
:class:`ParseError` carrying the offending line number and a human
readable explanation, as required by the subject.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from models import Connection, Network, Zone, ZoneType


class ParseError(Exception):
    """Raised when a map file cannot be parsed.

    Attributes:
        message: Explanation of what went wrong.
        line_number: 1-based index of the offending line, if known.
    """

    def __init__(self, message: str, line_number: Optional[int] = None) -> None:
        self.message = message
        self.line_number = line_number
        if line_number is not None:
            super().__init__(f"line {line_number}: {message}")
        else:
            super().__init__(message)


class MapParser:
    """Parse a Fly-in map into a :class:`~models.Network`.

    The parser performs a single forward pass. Because connections may
    only reference zones that have already been declared, this single
    pass is sufficient to validate the whole file.
    """

    _ZONE_KEYS = frozenset({"zone", "color", "max_drones"})
    _CONNECTION_KEYS = frozenset({"max_link_capacity"})

    def __init__(self) -> None:
        self._network = Network()
        self._seen_nb_drones = False

    def parse_text(self, text: str) -> Network:
        """Parse a full map from a string.

        Args:
            text: The complete map file contents.

        Returns:
            The validated :class:`~models.Network`.

        Raises:
            ParseError: If the map is malformed in any way.
        """
        for index, raw_line in enumerate(text.splitlines(), start=1):
            line = self._strip_comment(raw_line).strip()
            if not line:
                continue
            self._parse_line(line, index)
        self._validate_final_state()
        return self._network

    def parse_file(self, path: str) -> Network:
        """Parse a map from a file on disk.

        Args:
            path: Path to the map file.

        Returns:
            The validated :class:`~models.Network`.

        Raises:
            ParseError: If the map is malformed.
            OSError: If the file cannot be read.
        """
        with open(path, "r", encoding="utf-8") as handle:
            return self.parse_text(handle.read())

    @staticmethod
    def _strip_comment(line: str) -> str:
        """Remove a trailing ``#`` comment from a line."""
        hash_index = line.find("#")
        if hash_index == -1:
            return line
        return line[:hash_index]

    def _parse_line(self, line: str, index: int) -> None:
        """Dispatch a single non-empty, comment-free line."""
        if not self._seen_nb_drones:
            self._parse_nb_drones(line, index)
            return
        if ":" not in line:
            raise ParseError(f"expected a 'key: value' directive, got "
                             f"'{line}'", index)
        prefix, _, remainder = line.partition(":")
        prefix = prefix.strip()
        remainder = remainder.strip()
        if prefix in ("start_hub", "end_hub", "hub"):
            self._parse_zone(prefix, remainder, index)
        elif prefix == "connection":
            self._parse_connection(remainder, index)
        elif prefix == "nb_drones":
            raise ParseError("nb_drones may only be declared once", index)
        else:
            raise ParseError(f"unknown directive '{prefix}'", index)

    def _parse_nb_drones(self, line: str, index: int) -> None:
        """Parse the mandatory leading ``nb_drones`` directive."""
        prefix, sep, remainder = line.partition(":")
        if sep != ":" or prefix.strip() != "nb_drones":
            raise ParseError("the first directive must be "
                             "'nb_drones: <positive_integer>'", index)
        self._network.nb_drones = self._positive_int(
            remainder.strip(), "nb_drones", index)
        self._seen_nb_drones = True

    def _parse_zone(self, prefix: str, remainder: str, index: int) -> None:
        """Parse a ``hub``, ``start_hub`` or ``end_hub`` directive."""
        body, metadata = self._split_metadata(remainder, index)
        tokens = body.split()
        if len(tokens) != 3:
            raise ParseError("zone must be '<name> <x> <y> [metadata]'", index)
        name, raw_x, raw_y = tokens
        self._check_zone_name(name, index)
        if name in self._network.zones:
            raise ParseError(f"duplicate zone name '{name}'", index)
        x = self._integer(raw_x, "x coordinate", index)
        y = self._integer(raw_y, "y coordinate", index)
        zone_type, color, capacity = self._zone_metadata(metadata, index)
        zone = Zone(
            name=name,
            x=x,
            y=y,
            zone_type=zone_type,
            color=color,
            capacity=capacity,
            is_start=prefix == "start_hub",
            is_end=prefix == "end_hub",
        )
        if zone.is_start and self._network._start is not None:
            raise ParseError("more than one start_hub defined", index)
        if zone.is_end and self._network._end is not None:
            raise ParseError("more than one end_hub defined", index)
        self._network.add_zone(zone)

    def _parse_connection(self, remainder: str, index: int) -> None:
        """Parse a ``connection`` directive."""
        body, metadata = self._split_metadata(remainder, index)
        tokens = body.split()
        if len(tokens) != 1:
            raise ParseError("connection must be '<zone1>-<zone2> "
                             "[metadata]'", index)
        endpoints = tokens[0].split("-")
        if len(endpoints) != 2 or not endpoints[0] or not endpoints[1]:
            raise ParseError("connection must join exactly two zones with a "
                             "single dash", index)
        first, second = endpoints
        if first == second:
            raise ParseError("a connection cannot join a zone to itself",
                             index)
        for endpoint in (first, second):
            if endpoint not in self._network.zones:
                raise ParseError(f"connection refers to undefined zone "
                                 f"'{endpoint}'", index)
        capacity = self._connection_metadata(metadata, index)
        connection = Connection(first=first, second=second, capacity=capacity)
        if connection.key in self._network.connections:
            raise ParseError(f"duplicate connection '{first}-{second}'", index)
        self._network.add_connection(connection)

    def _split_metadata(
        self, text: str, index: int
    ) -> Tuple[str, Dict[str, str]]:
        """Separate the body of a directive from its ``[...]`` metadata.

        Args:
            text: The directive text after its prefix.
            index: Line number for error reporting.

        Returns:
            A tuple of the body string and a mapping of metadata keys to
            values (empty if no metadata is present).

        Raises:
            ParseError: If the brackets are unbalanced or malformed.
        """
        open_index = text.find("[")
        if open_index == -1:
            if "]" in text:
                raise ParseError("found ']' without matching '['", index)
            return text.strip(), {}
        if not text.rstrip().endswith("]"):
            raise ParseError("metadata '[' is not closed with ']'", index)
        body = text[:open_index].strip()
        inner = text[open_index + 1:text.rstrip().rfind("]")].strip()
        return body, self._parse_metadata_tokens(inner, index)

    def _parse_metadata_tokens(
        self, inner: str, index: int
    ) -> Dict[str, str]:
        """Parse the ``key=value`` pairs inside a metadata block."""
        metadata: Dict[str, str] = {}
        for token in inner.split():
            if "=" not in token:
                raise ParseError(f"metadata entry '{token}' is not "
                                 f"'key=value'", index)
            key, _, value = token.partition("=")
            key = key.strip()
            value = value.strip()
            if not key or not value:
                raise ParseError(f"malformed metadata entry '{token}'", index)
            if key in metadata:
                raise ParseError(f"duplicate metadata key '{key}'", index)
            metadata[key] = value
        return metadata

    def _zone_metadata(
        self, metadata: Dict[str, str], index: int
    ) -> Tuple[ZoneType, Optional[str], int]:
        """Validate and extract zone metadata with defaults applied."""
        for key in metadata:
            if key not in self._ZONE_KEYS:
                raise ParseError(f"unknown zone metadata key '{key}'", index)
        zone_type = ZoneType.NORMAL
        if "zone" in metadata:
            try:
                zone_type = ZoneType.from_string(metadata["zone"])
            except ValueError as error:
                raise ParseError(str(error), index) from error
        color = metadata.get("color")
        capacity = 1
        if "max_drones" in metadata:
            capacity = self._positive_int(
                metadata["max_drones"], "max_drones", index)
        return zone_type, color, capacity

    def _connection_metadata(
        self, metadata: Dict[str, str], index: int
    ) -> int:
        """Validate and extract connection metadata with defaults."""
        for key in metadata:
            if key not in self._CONNECTION_KEYS:
                raise ParseError(f"unknown connection metadata key '{key}'",
                                 index)
        if "max_link_capacity" in metadata:
            return self._positive_int(
                metadata["max_link_capacity"], "max_link_capacity", index)
        return 1

    def _check_zone_name(self, name: str, index: int) -> None:
        """Reject zone names that contain dashes or whitespace."""
        if "-" in name:
            raise ParseError(f"zone name '{name}' may not contain a dash",
                             index)
        if any(character.isspace() for character in name):
            raise ParseError(f"zone name '{name}' may not contain whitespace",
                             index)

    @staticmethod
    def _integer(raw: str, label: str, index: int) -> int:
        """Parse a (possibly negative) integer or raise a ParseError."""
        try:
            return int(raw)
        except ValueError as error:
            raise ParseError(f"{label} must be an integer, got '{raw}'",
                             index) from error

    @staticmethod
    def _positive_int(raw: str, label: str, index: int) -> int:
        """Parse a strictly positive integer or raise a ParseError."""
        try:
            value = int(raw)
        except ValueError as error:
            raise ParseError(f"{label} must be a positive integer, got "
                             f"'{raw}'", index) from error
        if value <= 0:
            raise ParseError(f"{label} must be a positive integer, got "
                             f"'{raw}'", index)
        return value

    def _validate_final_state(self) -> None:
        """Run whole-file checks once every line has been read."""
        if not self._seen_nb_drones:
            raise ParseError("missing 'nb_drones' directive")
        if self._network._start is None:
            raise ParseError("missing 'start_hub' directive")
        if self._network._end is None:
            raise ParseError("missing 'end_hub' directive")
        start = self._network.start
        end = self._network.end
        start.capacity = -1
        end.capacity = -1
        if not end.zone_type.is_traversable:
            raise ParseError("the end zone may not be blocked")
        if not start.zone_type.is_traversable:
            raise ParseError("the start zone may not be blocked")
