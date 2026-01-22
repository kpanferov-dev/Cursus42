"""
Polymorphic Data Streaming System for Code Nexus.
This module provides an extensible framework for processing mixed data types
using polymorphic stream handlers.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Dict, Union, Optional


class DataStream(ABC):
    """
    Abstract base class for all data streams.
    
    This class defines the interface that all specialized streams must implement,
    enabling polymorphic behavior.
    """
    
    def __init__(self, stream_id: str) -> None:
        """
        Initialize a DataStream instance.
        
        Args:
            stream_id: Unique identifier for the stream
        """
        self.stream_id = stream_id
        self.items_processed = 0
        self.last_result = ""
    
    @abstractmethod
    def process_batch(self, data_batch: List[Any]) -> str:
        """
        Process a batch of data.
        
        Args:
            data_batch: List of data items to process
            
        Returns:
            String describing the processing results
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        pass
    
    def filter_data(self, data_batch: List[Any], 
                   criteria: Optional[str] = None) -> List[Any]:
        """
        Filter data based on criteria.
        
        Args:
            data_batch: List of data items to filter
            criteria: Optional filtering criteria string
            
        Returns:
            Filtered list of data items
        """
        if not criteria:
            return data_batch
        
        filtered_data = []
        for item in data_batch:
            # Default implementation filters based on item truthiness
            if item:
                filtered_data.append(item)
        
        return filtered_data
    
    def get_stats(self) -> Dict[str, Union[str, int, float]]:
        """
        Return stream statistics.
        
        Returns:
            Dictionary containing stream statistics
        """
        return {
            "stream_id": self.stream_id,
            "items_processed": self.items_processed,
            "last_result": self.last_result,
            "stream_type": self.__class__.__name__
        }
    
    def _update_stats(self, count: int, result: str) -> None:
        """
        Update internal statistics after processing.
        
        Args:
            count: Number of items processed
            result: Result description
        """
        self.items_processed += count
        self.last_result = result


class SensorStream(DataStream):
    """
    Stream for processing sensor data (temperature, humidity, pressure, etc.).
    
    Specializes in environmental and sensor data processing.
    """
    
    def __init__(self, stream_id: str) -> None:
        """
        Initialize a SensorStream instance.
        
        Args:
            stream_id: Unique identifier for the sensor stream
        """
        super().__init__(stream_id)
        self.stream_type = "Environmental Data"
    
    def process_batch(self, data_batch: List[Any]) -> str:
        """
        Process a batch of sensor readings.
        
        Args:
            data_batch: List of sensor readings to process
            
        Returns:
            String describing sensor analysis results
            
        Raises:
            ValueError: If data batch is empty
        """
        if not data_batch:
            raise ValueError("Sensor data batch cannot be empty")
        
        # Count valid sensor readings
        valid_readings = len(data_batch)
        
        # Calculate average temperature if present
        temp_sum = 0
        temp_count = 0
        for reading in data_batch:
            if isinstance(reading, dict) and "temp" in reading:
                temp_sum += reading["temp"]
                temp_count += 1
        
        avg_temp = temp_sum / temp_count if temp_count > 0 else 0
        
        result = (f"Sensor analysis: {valid_readings} readings processed, "
                 f"avg temp: {avg_temp}°C")
        
        self._update_stats(valid_readings, result)
        return result
    
    def filter_data(self, data_batch: List[Any], 
                   criteria: Optional[str] = None) -> List[Any]:
        """
        Filter sensor data based on criteria.
        
        Args:
            data_batch: List of sensor readings
            criteria: Optional filtering criteria
            
        Returns:
            Filtered list of sensor readings
        """
        if not criteria:
            return super().filter_data(data_batch, criteria)
        
        filtered_data = []
        for reading in data_batch:
            if isinstance(reading, dict):
                # Filter based on alert thresholds
                if criteria == "high_temp" and reading.get("temp", 0) > 30:
                    filtered_data.append(reading)
                elif criteria == "low_pressure" and reading.get("pressure", 0) < 1000:
                    filtered_data.append(reading)
                elif criteria == "high_humidity" and reading.get("humidity", 0) > 80:
                    filtered_data.append(reading)
        
        return filtered_data


class TransactionStream(DataStream):
    """
    Stream for processing financial transactions.
    
    Specializes in financial data processing with net flow calculations.
    """
    
    def __init__(self, stream_id: str) -> None:
        """
        Initialize a TransactionStream instance.
        
        Args:
            stream_id: Unique identifier for the transaction stream
        """
        super().__init__(stream_id)
        self.stream_type = "Financial Data"
    
    def process_batch(self, data_batch: List[Any]) -> str:
        """
        Process a batch of financial transactions.
        
        Args:
            data_batch: List of transactions to process
            
        Returns:
            String describing transaction analysis results
            
        Raises:
            ValueError: If data batch is empty
        """
        if not data_batch:
            raise ValueError("Transaction data batch cannot be empty")
        
        # Calculate net flow
        net_flow = 0
        for transaction in data_batch:
            if isinstance(transaction, dict):
                if transaction.get("type") == "buy":
                    net_flow -= transaction.get("amount", 0)
                elif transaction.get("type") == "sell":
                    net_flow += transaction.get("amount", 0)
        
        result = (f"Transaction analysis: {len(data_batch)} operations, "
                 f"net flow: {net_flow:+} units")
        
        self._update_stats(len(data_batch), result)
        return result
    
    def filter_data(self, data_batch: List[Any], 
                   criteria: Optional[str] = None) -> List[Any]:
        """
        Filter transaction data based on criteria.
        
        Args:
            data_batch: List of transactions
            criteria: Optional filtering criteria
            
        Returns:
            Filtered list of transactions
        """
        if not criteria:
            return super().filter_data(data_batch, criteria)
        
        filtered_data = []
        for transaction in data_batch:
            if isinstance(transaction, dict):
                # Filter based on transaction characteristics
                if criteria == "large" and transaction.get("amount", 0) > 100:
                    filtered_data.append(transaction)
                elif criteria == "buy" and transaction.get("type") == "buy":
                    filtered_data.append(transaction)
                elif criteria == "sell" and transaction.get("type") == "sell":
                    filtered_data.append(transaction)
        
        return filtered_data


class EventStream(DataStream):
    """
    Stream for processing system events (logins, errors, logouts, etc.).
    
    Specializes in system event monitoring and analysis.
    """
    
    def __init__(self, stream_id: str) -> None:
        """
        Initialize an EventStream instance.
        
        Args:
            stream_id: Unique identifier for the event stream
        """
        super().__init__(stream_id)
        self.stream_type = "System Events"
        self.error_count = 0
    
    def process_batch(self, data_batch: List[Any]) -> str:
        """
        Process a batch of system events.
        
        Args:
            data_batch: List of events to process
            
        Returns:
            String describing event analysis results
            
        Raises:
            ValueError: If data batch is empty
        """
        if not data_batch:
            raise ValueError("Event data batch cannot be empty")
        
        # Count errors
        error_count = 0
        for event in data_batch:
            if isinstance(event, str) and event.lower() == "error":
                error_count += 1
        
        self.error_count += error_count
        
        result = (f"Event analysis: {len(data_batch)} events, "
                 f"{error_count} error(s) detected")
        
        self._update_stats(len(data_batch), result)
        return result
    
    def filter_data(self, data_batch: List[Any], 
                   criteria: Optional[str] = None) -> List[Any]:
        """
        Filter event data based on criteria.
        
        Args:
            data_batch: List of events
            criteria: Optional filtering criteria
            
        Returns:
            Filtered list of events
        """
        if not criteria:
            return super().filter_data(data_batch, criteria)
        
        filtered_data = []
        for event in data_batch:
            if isinstance(event, str):
                if criteria == "error" and event.lower() == "error":
                    filtered_data.append(event)
                elif criteria == "security" and event.lower() in ["login", "logout"]:
                    filtered_data.append(event)
        
        return filtered_data
    
    def get_stats(self) -> Dict[str, Union[str, int, float]]:
        """
        Return event stream statistics including error count.
        
        Returns:
            Dictionary containing event stream statistics
        """
        stats = super().get_stats()
        stats["error_count"] = self.error_count
        return stats


class StreamProcessor:
    """
    Manager class for handling multiple stream types polymorphically.

    This class demonstrates polymorphism by processing different stream types
    through a unified interface without
    needing to know specific implementations.
    """
    
    def __init__(self) -> None:
        """Initialize a StreamProcessor instance."""
        self.streams = []
    
    def add_stream(self, stream: DataStream) -> None:
        """
        Add a stream to the processor.
        
        Args:
            stream: DataStream instance to add
        """
        self.streams.append(stream)
    
    def process_all(self, data_map: Dict[str, List[Any]]) -> Dict[str, str]:
        """
        Process data for all registered streams.
        
        Args:
            data_map: Dictionary mapping stream IDs to data batches
            
        Returns:
            Dictionary mapping stream IDs to processing results
            
        Raises:
            KeyError: If a stream ID in data_map doesn't exist
        """
        results = {}
        
        for stream_id, data_batch in data_map.items():
            stream = next((s for s in self.streams if s.stream_id == stream_id), None)
            if not stream:
                raise KeyError(f"Stream {stream_id} not found")
            
            try:
                result = stream.process_batch(data_batch)
                results[stream_id] = result
            except Exception as e:
                results[stream_id] = f"Processing failed: {str(e)}"
        
        return results
    
    def filter_all(self, criteria: str) -> Dict[str, List[Any]]:
        """
        Apply filtering to all streams based on criteria.
        
        Args:
            criteria: Filtering criteria string
            
        Returns:
            Dictionary mapping stream types to filtered data examples
        """
        filtered_results = {}
        
        for stream in self.streams:
            # Create sample data for demonstration
            sample_data = self._get_sample_data(stream)
            filtered = stream.filter_data(sample_data, criteria)
            
            if filtered:
                stream_type = stream.__class__.__name__
                filtered_results[stream_type] = filtered
        
        return filtered_results
    
    def get_all_stats(self) -> List[Dict[str, Union[str, int, float]]]:
        """
        Get statistics from all streams.
        
        Returns:
            List of statistics dictionaries for all streams
        """
        return [stream.get_stats() for stream in self.streams]
    
    def _get_sample_data(self, stream: DataStream) -> List[Any]:
        """
        Generate sample data for a stream type.
        
        Args:
            stream: Stream instance
            
        Returns:
            Sample data appropriate for the stream type
        """
        if isinstance(stream, SensorStream):
            return [
                {"temp": 22.5, "humidity": 65, "pressure": 1013},
                {"temp": 35.0, "humidity": 45, "pressure": 990},
                {"temp": 18.0, "humidity": 85, "pressure": 1020}
            ]
        elif isinstance(stream, TransactionStream):
            return [
                {"type": "buy", "amount": 100},
                {"type": "sell", "amount": 150},
                {"type": "buy", "amount": 75},
                {"type": "sell", "amount": 50}
            ]
        elif isinstance(stream, EventStream):
            return ["login", "error", "logout", "startup", "shutdown"]
        
        return []


def main() -> None:
    """
    Main demonstration function showing polymorphic stream processing.
    
    This function demonstrates:
    1. Creating different stream types
    2. Processing data polymorphically
    3. Filtering capabilities
    4. Statistics collection
    """
    print("=== CODE NEXUS - POLYMORPHIC STREAM SYSTEM ===\n")
    
    # Create streams
    print("Initializing Sensor Stream...")
    sensor_stream = SensorStream("SENSOR_001")
    print(f"Stream ID: {sensor_stream.stream_id}, "
          f"Type: {sensor_stream.stream_type}")
    
    print("\nInitializing Transaction Stream...")
    transaction_stream = TransactionStream("TRANS_001")
    print(f"Stream ID: {transaction_stream.stream_id}, "
          f"Type: {transaction_stream.stream_type}")
    
    print("\nInitializing Event Stream...")
    event_stream = EventStream("EVENT_001")
    print(f"Stream ID: {event_stream.stream_id}, "
          f"Type: {event_stream.stream_type}")
    
    # Create processor and add streams
    processor = StreamProcessor()
    processor.add_stream(sensor_stream)
    processor.add_stream(transaction_stream)
    processor.add_stream(event_stream)
    
    # Prepare data for processing
    data_to_process = {
        "SENSOR_001": [
            {"temp": 22.5, "humidity": 65, "pressure": 1013},
            {"temp": 35.0, "humidity": 45, "pressure": 990},
            {"temp": 18.0, "humidity": 85, "pressure": 1020}
        ],
        "TRANS_001": [
            {"type": "buy", "amount": 100},
            {"type": "sell", "amount": 150},
            {"type": "buy", "amount": 75},
            {"type": "sell", "amount": 200}
        ],
        "EVENT_001": ["login", "error", "logout", "startup", "shutdown", "error"]
    }
    
    # Demonstrate polymorphic processing
    print("\n=== Polymorphic Stream Processing ===")
    print("Processing mixed stream types through unified interface...\n")
    
    results = processor.process_all(data_to_process)
    
    print("Processing Results:")
    for stream_id, result in results.items():
        print(f"- {stream_id}: {result}")
    
    # Demonstrate filtering
    print("\n=== Stream Filtering ===")
    print("Filtering data with 'error' criteria...")
    filtered = processor.filter_all("error")
    
    for stream_type, data in filtered.items():
        print(f"- {stream_type}: Found {len(data)} matching items")
    
    print("\nFiltering data with 'large' criteria...")
    filtered = processor.filter_all("large")
    
    for stream_type, data in filtered.items():
        print(f"- {stream_type}: Found {len(data)} matching items")
    
    # Show statistics
    print("\n=== Stream Statistics ===")
    stats = processor.get_all_stats()
    for stat in stats:
        print(f"{stat['stream_type']} ({stat['stream_id']}): "
              f"Processed {stat['items_processed']} items")
    
    print("\nAll streams processed successfully. Nexus throughput optimal.")
    
    # Reflection on polymorphism
    print("\n=== Polymorphism Reflection ===")
    print("How does polymorphism allow the StreamProcessor to handle different")
    print("stream types without knowing their specific implementations?")
    print()
    print("1. The StreamProcessor works with the DataStream base class interface")
    print("2. All specialized streams (SensorStream, TransactionStream, EventStream)")
    print("   implement the same interface methods (process_batch, filter_data, etc.)")
    print("3. The processor calls methods on stream objects without needing to know")
    print("   their concrete types - it only knows they are DataStream instances")
    print()
    print("Benefits of this design approach:")
    print("1. Extensibility: New stream types can be added without modifying")
    print("   the StreamProcessor class")
    print("2. Maintainability: Changes to specific stream implementations don't")
    print("   affect the overall system")
    print("3. Type Safety: The interface enforces method implementation")
    print("4. Code Reuse: Common functionality can be implemented in base class")


if __name__ == "__main__":
    main()
