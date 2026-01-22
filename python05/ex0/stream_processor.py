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
        return (f"{super().format_output('')}Processed" +
                f" {length} numeric values, sum={total}, avg={avg}")


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
        return f"{key}: {value}"

    def validate(self, data: Dict[str, str]) -> bool:
        """Validate if data is appropriate for
        this processor"""
        try:
            for key, value in data.items():
                key + ""
                value + ""
            valid_keys = {"ERROR", "INFO", "WARNING", "SUCCESS"}
            if key.upper() not in valid_keys:
                raise ValueError(f"Invalid key: {key}." +
                                 f" Allowed keys: {', '.join(valid_keys)}")

            if len(data) == 0:
                raise ValueError("Data is an empty dictionary")

        except AttributeError:
            print("Data is not a dictionary or does not support .items()")
            return False
        except TypeError:
            print("Keys or values are not strings")
            return False
        except ValueError as e:
            print("Error:", e)
        except Exception as e:
            print(f"Validation failed due to: {e}")
            return False
        return True

    def format_output(self, result: str) -> str:
        """Format the output result"""
        if ": " in result:
            key, value = result.split(": ", 1)
        else:
            key, value = "UNKNOWN", result

        if key.upper() == "ERROR":
            prefix = "[ALERT]"
        else:
            prefix = f"[{key.upper()}]"
        return f"Output: {prefix} {key.upper()} level detected: {value}"


def main():
    """main program"""
    print("=== CODE NEXUS - DATA PROCESSOR FOUNDATION ===\n")

    print("Initializing Numeric Processor...")
    numeric_data = [1, 2, 3, 4, 5]
    numeric_processor = NumericProcessor()
    print(f"Processing data: {numeric_data}")
    if numeric_processor.validate(numeric_data):
        print("Validation: Numeric data verified")
        result = numeric_processor.process(numeric_data)
        print(numeric_processor.format_output(result))
    else:
        print("Validation failed: Invalid numeric data")

    print("\nInitializing Text Processor...")
    text_data = "Hello Nexus World"
    text_processor = TextProcessor()
    print(f'Processing data: "{text_data}"')
    if text_processor.validate(text_data):
        print("Validation: Text data verified")
        result = text_processor.process(text_data)
        print(text_processor.format_output(result))
    else:
        print("Validation failed: Invalid text data")

    print("\nInitializing Log Processor...")
    log_data = {"ERROR": "Connection timeout"}
    log_processor = LogProcessor()
    print(f'Processing data: "{log_processor.process(log_data)}"')
    if log_processor.validate(log_data):
        print("Validation: Log entry verified")
        result = log_processor.process(log_data)
        print(log_processor.format_output(result))
    else:
        print("Validation failed: Invalid log data")

    print("\n=== Polymorphic Processing Demo ===")
    processors = [
        (NumericProcessor(), [1, 2, 3]),
        (TextProcessor(), "Hello World"),
        (LogProcessor(), {"INFO": "System ready"})
    ]

    for i, (processor, data) in enumerate(processors, start=1):
        if processor.validate(data):
            result = processor.process(data)
            print(f"Result {i}: {processor.format_output(result)}")
        else:
            print(f"Result {i}: Validation failed")

    print("\nFoundation systems online. Nexus ready for advanced streams.")


if __name__ == "__main__":
    main()
