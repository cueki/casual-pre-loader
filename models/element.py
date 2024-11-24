from dataclasses import dataclass
from typing import Dict, Any, Tuple
from core.constants import AttributeType

@dataclass
class PCFElement:
    type_name_index: int
    element_name: str
    data_signature: bytes
    attributes: Dict[str, Tuple[AttributeType, Any]]