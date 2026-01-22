"""
ex1.data_stream
Learning advanced polymorphic
"""
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Union, Optional


class DataStream(ABC):
    """Base Abstract Class for Streams"""
    def __init__(self, stream_id: str):
        self.stream_id = stream_id
        self.stats = {}

    @abstractmethod
    def process_batch(self, data_batch: List[Any]) -> str:
        pass

    def filter_data(self, data_batch: List[Any], criteria: Optional[str] = None) -> List[Any]:
        if not criteria:
            return data_batch
        # Dummy filter implementation for illustration
        return [data for data in data_batch if criteria in str(data)]

    def get_stats(self) -> Dict[str, Union[str, int, float]]:
        return self.stats

# Specialized Streams
class SensorStream(DataStream):
    def __init__(self, stream_id: str):
        super().__init__(stream_id)
        self.stream_type = "Environmental Data"

    def process_batch(self, data_batch: List[Any]) -> str:
        temperatures = [data["temp"] for data in data_batch if "temp" in data]
        avg_temp = sum(temperatures) / len(temperatures) if temperatures else 0
        self.stats = {
            "readings_processed": len(data_batch),
            "avg_temperature": avg_temp
        }
        return f"Processed {len(data_batch)} sensor readings. Average Temperature: {avg_temp:.2f}°C"

class TransactionStream(DataStream):
    def __init__(self, stream_id: str):
        super().__init__(stream_id)
        self.stream_type = "Financial Data"

    def process_batch(self, data_batch: List[Any]) -> str:
        net_flow = sum(data[1] if data[0] == "buy" else -data[1] for data in data_batch)
        self.stats = {
            "operations_processed": len(data_batch),
            "net_flow": net_flow
        }
        return f"Processed {len(data_batch)} transactions. Net Flow: {net_flow} units"

class EventStream(DataStream):
    def __init__(self, stream_id: str):
        super().__init__(stream_id)
        self.stream_type = "System Events"

    def process_batch(self, data_batch: List[Any]) -> str:
        errors = sum(1 for event in data_batch if event == "error")
        self.stats = {
            "events_processed": len(data_batch),
            "errors_detected": errors
        }
        return f"Processed {len(data_batch)} system events. Errors detected: {errors}"

# Stream Processor to Handle Multiple Streams
class StreamProcessor:
    def __init__(self):
        self.streams = []

    def add_stream(self, stream: DataStream):
        self.streams.append(stream)

    def process_streams(self, batches: List[List[Any]]):
        results = []
        for stream, batch in zip(self.streams, batches):
            try:
                result = stream.process_batch(batch)
                results.append(result)
            except Exception as e:
                results.append(f"Error processing stream {stream.stream_id}: {e}")
        return results

# Code Execution
if __name__ == "__main__":
    print("=== CODE NEXUS - POLYMORPHIC STREAM SYSTEM ===")

    # Initialize Streams
    sensor_stream = SensorStream("SENSOR_001")
    transaction_stream = TransactionStream("TRANS_001")
    event_stream = EventStream("EVENT_001")

    print(f"Initializing {sensor_stream.stream_type} stream...")
    print(sensor_stream.process_batch([
        {"temp": 22.5, "humidity": 65, "pressure": 1013},
        {"temp": 23.0, "humidity": 70, "pressure": 1012}
    ]))

    print(f"Initializing {transaction_stream.stream_type} stream...")
    print(transaction_stream.process_batch([
        ("buy", 100), ("sell", 150), ("buy", 75)
    ]))

    print(f"Initializing {event_stream.stream_type} stream...")
    print(event_stream.process_batch([
        "login", "error", "logout"
    ]))

    print("=== Polymorphic Stream Processing ===")
    processor = StreamProcessor()
    processor.add_stream(sensor_stream)
    processor.add_stream(transaction_stream)
    processor.add_stream(event_stream)

    batch_results = processor.process_streams([
        [{"temp": 21.0, "humidity": 64}],  # Batch for sensor stream
        [("sell", 200), ("buy", 50), ("sell", 75)],  # Batch for transaction stream
        ["error", "warning", "logout"]  # Batch for event stream
    ])

    for result in batch_results:
        print(result)

    print("Filters applied...")
    filtered_sensor = sensor_stream.filter_data([
        {"temp": 25.0}, {"temp": 21.0}
    ], criteria="temp")
    print("Filtered Sensor Data:", filtered_sensor)

    print("All streams processed successfully.")