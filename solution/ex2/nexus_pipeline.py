"""
Nexus Integration - Enterprise Data Processing Pipeline System
This module implements a polymorphic pipeline architecture for processing
multiple data formats using method overriding and subtype polymorphism.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Dict, Union, Optional
import time
import json
import csv
from io import StringIO


# ==================== PROTOCOL INTERFACES ====================

class ProcessingStage:
    """Protocol defining the interface for pipeline stages using duck typing."""
    
    def process(self, data: Any) -> Any:
        """Process input data and return transformed output."""
        ...


# ==================== ABSTRACT BASE CLASSES ====================

class ProcessingPipeline(ABC):
    """Abstract base class for configurable data processing pipelines."""
    
    def __init__(self) -> None:
        """Initialize pipeline with empty stage list."""
        self.stages: List[ProcessingStage] = []
    
    @abstractmethod
    def process(self, data: Any) -> Union[str, Any]:
        """Process data through pipeline stages (must be overridden)."""
        pass
    
    def add_stage(self, stage: ProcessingStage) -> None:
        """Add a processing stage to the pipeline."""
        self.stages.append(stage)
    
    def execute_stages(self, data: Any) -> Any:
        """Execute all stages sequentially on the input data."""
        current_data = data
        for stage in self.stages:
            current_data = stage.process(current_data)
        return current_data


# ==================== STAGE IMPLEMENTATIONS ====================

class InputStage:
    """Processing stage for input validation and parsing."""
    
    def process(self, data: Any) -> Any:
        """Validate and parse input data."""
        return f"Input: {type(data).__name__}"


class TransformStage:
    """Processing stage for data transformation and enrichment."""
    
    def process(self, data: Any) -> Any:
        """Transform and enrich data."""
        return f"Transformed: {data}"


class OutputStage:
    """Processing stage for output formatting and delivery."""
    
    def process(self, data: Any) -> Any:
        """Format and prepare data for output."""
        return f"Output: {data}"


# ==================== ADAPTER IMPLEMENTATIONS ====================

class JSONAdapter(ProcessingPipeline):
    """Adapter for processing JSON data formats."""
    
    def __init__(self, pipeline_id: str) -> None:
        """Initialize JSON adapter with default stages."""
        super().__init__()
        self.pipeline_id = pipeline_id
        self.add_stage(InputStage())
        self.add_stage(TransformStage())
        self.add_stage(OutputStage())
    
    def process(self, data: Any) -> Union[str, Any]:
        """Process JSON data through pipeline stages."""
        try:
            if isinstance(data, str):
                json.loads(data)  # Validate JSON
            return f"JSON processed by {self.pipeline_id}: {self.execute_stages(data)}"
        except Exception:
            return f"JSON processing error in {self.pipeline_id}"


class CSVAdapter(ProcessingPipeline):
    """Adapter for processing CSV data formats."""
    
    def __init__(self, pipeline_id: str) -> None:
        """Initialize CSV adapter with default stages."""
        super().__init__()
        self.pipeline_id = pipeline_id
        self.add_stage(InputStage())
        self.add_stage(TransformStage())
        self.add_stage(OutputStage())
    
    def process(self, data: Any) -> Union[str, Any]:
        """Process CSV data through pipeline stages."""
        try:
            if isinstance(data, str):
                list(csv.reader(StringIO(data)))  # Validate CSV
            return f"CSV processed by {self.pipeline_id}: {self.execute_stages(data)}"
        except Exception:
            return f"CSV processing error in {self.pipeline_id}"


class StreamAdapter(ProcessingPipeline):
    """Adapter for processing streaming data formats."""
    
    def __init__(self, pipeline_id: str) -> None:
        """Initialize Stream adapter with default stages."""
        super().__init__()
        self.pipeline_id = pipeline_id
        self.add_stage(InputStage())
        self.add_stage(TransformStage())
        self.add_stage(OutputStage())
    
    def process(self, data: Any) -> Union[str, Any]:
        """Process streaming data through pipeline stages."""
        try:
            return f"Stream processed by {self.pipeline_id}: {self.execute_stages(data)}"
        except Exception:
            return f"Stream processing error in {self.pipeline_id}"


# ==================== MANAGER CLASS ====================

class NexusManager:
    """Orchestrator for multiple data processing pipelines."""
    
    def __init__(self) -> None:
        """Initialize manager with empty pipeline list."""
        self.pipelines: List[ProcessingPipeline] = []
    
    def add_pipeline(self, pipeline: ProcessingPipeline) -> None:
        """Add a pipeline to the manager."""
        self.pipelines.append(pipeline)
    
    def process_data(self, data: Any, pipeline_index: int = 0) -> str:
        """Process data through specified pipeline."""
        if pipeline_index < len(self.pipelines):
            return self.pipelines[pipeline_index].process(data)
        return "Pipeline not found"
    
    def chain_pipelines(self, data: Any, pipeline_indices: List[int]) -> str:
        """Chain multiple pipelines for sequential processing."""
        result = data
        for idx in pipeline_indices:
            if idx < len(self.pipelines):
                result = self.pipelines[idx].process(result)
            else:
                return f"Pipeline index {idx} out of range"
        return f"Chained result: {result}"
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Return overall manager statistics."""
        return {
            "total_pipelines": len(self.pipelines),
            "pipeline_types": [type(p).__name__ for p in self.pipelines]
        }


# ==================== DEMONSTRATION FUNCTION ====================

def demonstrate_nexus_pipeline() -> None:
    """Demonstrate the polymorphic pipeline system."""
    print("CODE NEXUS - ENTERPRISE PIPELINE SYSTEM")
    
    # Create manager
    manager = NexusManager()
    
    # Create and add pipelines
    json_pipe = JSONAdapter("JSON_001")
    csv_pipe = CSVAdapter("CSV_002")
    stream_pipe = StreamAdapter("STREAM_003")
    
    manager.add_pipeline(json_pipe)
    manager.add_pipeline(csv_pipe)
    manager.add_pipeline(stream_pipe)
    
    # Test processing
    test_data = '{"test": "data"}'
    print(manager.process_data(test_data, 0))
    
    # Test chaining
    print(manager.chain_pipelines("chain_test", [0, 1, 2]))
    
    # Show stats
    print(manager.get_manager_stats())


# ==================== MAIN ENTRY POINT ====================

if __name__ == "__main__":
    """Main entry point for the Nexus Pipeline system."""
    demonstrate_nexus_pipeline()