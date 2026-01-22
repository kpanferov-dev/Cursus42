"""
ex1.data_stream
Learning advanced polymorphic
"""
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Union, Optional


class DataStream(ABC):
    def __init__(self,stream_id):
        super().__init__(stream_id)
        self.stream_id = stream_id
    def algo():
        pass


class SensorStream(DataStream):


