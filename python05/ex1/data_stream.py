"""
ex1.data_stream
Learning how to play with polymorphism and StreamProcessor
"""
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Union, Optional


class DataStream(ABC):
    """Data Stream abstract class definng rules
        for other sub classes
    """
    def __init__(self, stream_id: str) -> None:
        """Constructor"""
        self.stream_id = stream_id
        self.last_value: Any = None
        self.batch_count: int = 0
        self.total_records: int = 0

    @abstractmethod
    def process_batch(self, data_batch: List[Any]) -> str:
        """Process info depending of class"""
        pass

    def filter_data(
        self,
        data_batch: List[Any],
        criteria: Optional[str] = None
    ) -> List[Any]:
        """filter data by criteria or just add values """
        if data_batch:
            self.last_value = data_batch[-1]
        if not criteria:
            return data_batch
        return data_batch

    def get_stats(self) -> Dict[str, Union[str, int, float]]:
        """return stats"""
        return {
            "stream_id": self.stream_id,
            "last_value": self.last_value,
            "batch_count": self.batch_count,
            "total_records": self.total_records,
        }


class SensorStream(DataStream):
    """Class to manage sensors"""
    def __init__(self, stream_id: str) -> None:
        """Constructor"""
        super().__init__(stream_id)
        self.stream_type = "Environmental Data"

    def process_batch(self, data_batch: List[Any]) -> str:
        """Process streams info"""
        try:
            if not data_batch or not isinstance(data_batch, list):
                raise ValueError("type error or empty data")

            self.last_value = data_batch[-1]
            self.batch_count = self.batch_count + 1
            self.total_records = self.total_records + len(data_batch)

            temps = [r["temp"] for r in data_batch
                     if isinstance(r, dict) and "temp" in r]
            avg_temp = sum(temps) / len(temps) if temps else 0

            return (f"Sensor analysis: {len(data_batch)}" +
                    f" readings processed, avg temp: {avg_temp}°C"
                    )
        except ValueError as e:
            print("Error:", e)

    def filter_data(
        self,
        data_batch: List[Any],
        criteria: Optional[str] = None
    ) -> List[Any]:
        """filter data by criteria or just add values """
        if data_batch:
            self.last_value = data_batch[-1]
        if not criteria:
            return super().filter_data(data_batch, criteria)
        if criteria == "high_priority":
            return [r for r in data_batch
                    if isinstance(r, dict) and r.get("temp", 0) > 30]
        return []

    def get_stats(self) -> Dict[str, Union[str, int, float]]:
        """Get stats from stream"""
        return {
            "stream_id": self.stream_id,
            "stream_type": self.stream_type,
            "last_value": self.last_value,
            "batch_count": self.batch_count,
            "total_records": self.total_records
        }


class TransactionStream(DataStream):
    """Class that works with Transactions"""
    def __init__(self, stream_id: str) -> None:
        """Constructor"""
        super().__init__(stream_id)
        self.stream_type = "Financial Data"
        self.format = ""

    def process_batch(self, data_batch: List[Any]) -> str:
        """Process transactions batches"""
        if not data_batch:
            raise ValueError("Transaction data batch cannot be empty")

        self.last_value = data_batch[-1]
        self.batch_count = self.batch_count + 1
        self.total_records = self.total_records + len(data_batch)

        net_flow = sum(
            t.get("amount", 0)
            if t.get("type") == "buy"
            else -t.get("amount", 0)
            for t in data_batch
            if isinstance(t, dict) and t.get("type") in ["buy", "sell"]
        )

        return (f"Transaction analysis: {len(data_batch)}" +
                f" operations, net flow: {net_flow:+} units")

    def filter_data(
        self,
        data_batch: List[Any],
        criteria: Optional[str] = None
    ) -> List[Any]:
        """Filter data by criteria or just add values """
        if data_batch:
            items = [f"{t.get('type')}:{t.get('amount')}"
                     for t in data_batch if isinstance(t, dict)]
            self.format = f"[{', '.join(items)}]"
        if not criteria:
            return super().filter_data(data_batch, criteria)
        if criteria == "high_priority":
            return [t for t in data_batch
                    if isinstance(t, dict) and t.get("amount", 0) > 100]
        return []

    def get_stats(self) -> Dict[str, Union[str, int, float]]:
        """Get stats"""
        return {
            "stream_id": self.stream_id,
            "stream_type": self.stream_type,
            "last_value": self.last_value,
            "batch_count": self.batch_count,
            "format": self.format,
            "total_records": self.total_records
        }


class EventStream(DataStream):
    """Class that process events"""

    def __init__(self, stream_id: str) -> None:
        """Constructor"""
        super().__init__(stream_id)
        self.stream_type = "System Events"
        self.format = ""

    def process_batch(self, data_batch: List[Any]) -> str:
        """Process event batches"""
        if not data_batch:
            raise ValueError("Event data batch cannot be empty")

        self.last_value = data_batch[-1]
        self.batch_count = self.batch_count + 1
        self.total_records = self.total_records + len(data_batch)

        error_count = len([e for e in data_batch
                           if isinstance(e, str) and e.lower() == "error"])

        return (f"Event analysis: {len(data_batch)}" +
                f" events, {error_count} error detected")

    def filter_data(
        self,
        data_batch: List[Any],
        criteria: Optional[str] = None
    ) -> List[Any]:
        """Filter events batches"""
        if data_batch:
            self.last_value = data_batch[-1]
            items = [f"{t}" for t in data_batch if isinstance(t, str)]
            self.format = f"[{', '.join(items)}]"
        if not criteria:
            return super().filter_data(data_batch, criteria)

        if criteria == "high_priority":
            return [e for e in data_batch
                    if isinstance(e, str) and e.lower() == "error"]
        return []

    def get_stats(self) -> Dict[str, Union[str, int, float]]:
        """Get stats"""
        return {
            "stream_id": self.stream_id,
            "stream_type": self.stream_type,
            "last_value": self.last_value,
            "batch_count": self.batch_count,
            "format": self.format,
            "total_records": self.total_records
        }


class StreamProcessor:
    """Class that process all kind streams"""
    def __init__(self) -> None:
        """Constructor"""
        self.streams: List[DataStream] = []

    def add_stream(self, stream: DataStream) -> None:
        """Add a stream to array"""
        self.streams.append(stream)

    def process_all(self, data_map: Dict[str, List[Any]]) -> List[DataStream]:
        """Process all streams"""
        for stream_id, data_batch in data_map.items():
            stream = next((s for s in self.streams
                           if s.stream_id == stream_id), None)
            if not stream:
                raise KeyError(f"Stream {stream_id} not found")
            try:
                stream.process_batch(data_batch)
            except Exception as e:
                print(f"Processing failed for {stream_id}: {str(e)}")
        return self.streams

    def filter_all(
        self,
        data_map: Dict[str, List[Any]],
        criteria: str
    ) -> Dict[str, List[Any]]:
        """Filter all streams"""
        filtered = {}
        for stream in self.streams:
            data = data_map.get(stream.stream_id, [])
            result = stream.filter_data(data, criteria)
            if result:
                filtered[stream.stream_id] = result
        return filtered


def main() -> None:
    """Main program"""
    batch_data = {
        "SENSOR_001": [
            {"temp": 22.5, "humidity": 65, "pressure": 1013},
            {"temp": 22.5, "humidity": 85, "pressure": 1020},
            {"temp": 22.5, "humidity": 65, "pressure": 1013}
        ],
        "TRANS_001": [
            {"type": "buy", "amount": 100},
            {"type": "sell", "amount": 150},
            {"type": "buy", "amount": 75},
        ],
        "EVENT_001": ["login", "error", "logout"]
    }
    print("=== CODE NEXUS - POLYMORPHIC STREAM SYSTEM ===\n")

    print("Initializing Sensor Stream...")
    sensor_stream = SensorStream("SENSOR_001")
    print(f"Stream ID: {sensor_stream.stream_id}," +
          f"Type: {sensor_stream.stream_type}")
    sensor_stream.filter_data(batch_data["SENSOR_001"])
    temp, hum, pres = sensor_stream.get_stats()["last_value"].values()
    print(f"Processing sensor batch: [temp:{temp}," +
          f" humidity:{hum}, pressure:{pres}]")
    sensor_data_init = batch_data["SENSOR_001"]
    print(sensor_stream.process_batch(sensor_data_init))

    # Initialize Transaction Stream
    print("\nInitializing Transaction Stream...")
    transaction_stream = TransactionStream("TRANS_001")
    print(f"Stream ID: {transaction_stream.stream_id}," +
          f" Type: {transaction_stream.stream_type}")
    transaction_stream.filter_data(batch_data["TRANS_001"])
    stats = transaction_stream.get_stats()["format"]
    trans_data_init = batch_data["TRANS_001"]
    print(f"Processing transaction batch: {stats}")
    print(transaction_stream.process_batch(trans_data_init))

    # Initialize Event Stream
    print("\nInitializing Event Stream...")
    event_stream = EventStream("EVENT_001")
    print(f"Stream ID: {event_stream.stream_id}," +
          f" Type: {event_stream.stream_type}")
    event_stream.filter_data(batch_data["EVENT_001"])
    stats = event_stream.get_stats()
    event_data_init = batch_data["EVENT_001"]
    print(f"Processing event batch: {stats['format']}")
    print(event_stream.process_batch(event_data_init))

    # Setup processor
    processor = StreamProcessor()
    sensor_stream1 = SensorStream("SENSOR_001")
    transaction_stream1 = TransactionStream("TRANS_001")
    event_stream1 = EventStream("EVENT_001")
    processor.add_stream(sensor_stream1)
    processor.add_stream(transaction_stream1)
    processor.add_stream(event_stream1)

    batch_data2 = {
        "SENSOR_001": [
            {"temp": 25.0, "humidity": 70, "pressure": 1010},
            {"temp": 26.0, "humidity": 68, "pressure": 1008}
        ],
        "TRANS_001": [
            {"type": "sell", "amount": 200},
            {"type": "buy", "amount": 50},
            {"type": "sell", "amount": 300},
            {"type": "buy", "amount": 125}
        ],
        "EVENT_001": ["startup", "warning", "error"]
    }
    print("\n=== Polymorphic Stream Processing ===")
    print("Processing mixed stream types through unified interface...\n")

    processed_streams = processor.process_all(batch_data2)

    print("Batch 1 Results:")
    for stream in processed_streams:
        stats = stream.get_stats()
        print(f"- {stats['stream_type']}: {stats['total_records']} processed")

    # Filtering
    filter_data = {
        "SENSOR_001": [
            {"temp": 35.0, "humidity": 45, "pressure": 990},
            {"temp": 40.0, "humidity": 30, "pressure": 985}
        ],
        "TRANS_001": [
            {"type": "buy", "amount": 50},
            {"type": "sell", "amount": 200}
        ],
        "EVENT_001": ["error", "warning"]
    }

    print("\nStream filtering active: High-priority data only")
    filtered = processor.filter_all(filter_data, "high_priority")

    sensor_alerts = len(filtered.get("SENSOR_001", []))
    large_trans = len(filtered.get("TRANS_001", []))
    print(f"Filtered results: {sensor_alerts} " +
          f"critical sensor alerts, {large_trans} large transaction")

    print("\nAll streams processed successfully. Nexus throughput optimal.")


if __name__ == "__main__":
    main()
