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
        return f"Output: {result}"


class NumericProcessor(DataProcessor):
    def process(self, data: List[int]) -> str:
        """Process the data and return result
        string"""
        return str(data)

    def validate(self, data: List[int]) -> bool:
        """Validate if data is appropriate for
        this processor"""
        try:
            data[0]
        except IndexError:
            print("Empty list")
            return False
        for num in data:
            try:
                int(num)
            except ValueError:
                print("All list items should be a number")
                return False
        return True

    def format_output(self, result: str) -> str:
        """Format the output result"""
        numbers = [int(x) for x in result.strip("[]").split(",")]
        total = sum(n for n in numbers)
        length = len(numbers)
        avg = total / length
        return f"{super().format_output('')}Processed {length} numeric values, sum={total}, avg={avg}"


class TextProcessor(DataProcessor):
    def process(self, data: str) -> str:
        """Process the data and return result
        string"""
        return data

    def validate(self, data: str) -> bool:
        """Validate if data is appropriate for
        this processor"""
        try:
            data.strip()
            if data.strip() == "":
                raise ValueError("Empty string")
        except AttributeError:
            print("Data is not a string")
            return False
        except ValueError as e:
            print("Error:", e)
            return False
        return True

    def format_output(self, result: str) -> str:
        """Format the output result"""
        length = len(result)
        num_words = len(result.split())
        return (f"{super().format_output('')}" +
                f"Processed text: {length} characters, {num_words} words"
                )


class LogProcessor(DataProcessor):
    def process(self, data: Dict[str, str]) -> str:
        """Process the data and return result
        string"""
        key = list(data.keys())[0]
        value = list(data.values())[0]
        return f"Processing data: \"{key}: {value}\""

    def validate(self, data: Dict[str, str]) -> bool:
        """Validate if data is appropriate for
        this processor"""
        return True

    def format_output(self, result: str) -> str:
        """Format the output result"""
        return result


lista = {"Error": " Connection timeout"}
processor = LogProcessor()
if processor.validate(lista):
    print(processor.format_output(processor.process(lista)))
