"""
    ex0.stream_processor.py
    Learn abstract classes, polimorphism and types
"""


from abc import ABC, abstractmethod
from typing import List, Dict, Union


class DataProcessor(ABC):
    """abstract class to process all kind of datas"""

    @abstractmethod
    def process(self, data: Union[List[int], str, Dict[str, str]]) -> str:
        """Process the data and return result
        string"""
        pass

    @abstractmethod
    def validate(self, data: Union[List[int], str, Dict[str, str]]) -> bool:
        """Validate if data is appropriate for
        this processor"""
        pass

    def format_output(self, result: str) -> str:
        """Format the output result"""
        return result


class NumericProcessor(DataProcessor):
    def process(self, data: List[int]) -> str:
        """Process the data and return result
        string"""
        return str(data)

    def validate(self, data: List[int]) -> bool:
        """Validate if data is appropriate for
        this processor"""
        if not data:
            return False
        for num in data:
            if not int(num):
                return False
        return True

    def format_output(self, result: str) -> str:
        """Format the output result"""
        return result


class TextProcessor(DataProcessor):
    def process(self, data: str) -> str:
        """Process the data and return result
        string"""

    def validate(self, data: str) -> bool:
        """Validate if data is appropriate for
        this processor"""

    def format_output(self, result: str) -> str:
        """Format the output result"""
        return result


class LogProcessor(DataProcessor):
    def process(self, data: Dict[str, str]) -> str:
        """Process the data and return result
        string"""

    def validate(self, data: Dict[str, str]) -> bool:
        """Validate if data is appropriate for
        this processor"""

    def format_output(self, result: str) -> str:
        """Format the output result"""
        return result
