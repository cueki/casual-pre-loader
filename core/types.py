from dataclasses import dataclass
from typing import Tuple, Union
from core.constants import AttributeType

AttributeValue = Union[int, float, bool, str, bytes, tuple, list]
AttributeData = Tuple[AttributeType, AttributeValue]

@dataclass
class ReclaimableSpace:
    """Information about space that can be reclaimed"""
    index: int
    size: int
    type: str
    risk: str
    data: bytes