from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from core.constants import AttributeType
from core.types import AttributeData

@dataclass
class PCFElement:
    """Represents a PCF element with improved validation"""
    type_name_index: int
    element_name: str
    data_signature: bytes
    attributes: Dict[str, AttributeData] = field(default_factory=dict)

    def __post_init__(self):
        """Validate element data on creation"""
        if not isinstance(self.type_name_index, int) or self.type_name_index < 0:
            raise ValueError("type_name_index must be a non-negative integer")
        if len(self.data_signature) != 16:
            raise ValueError("data_signature must be exactly 16 bytes")

    def get_attribute(self, name: str) -> Optional[AttributeData]:
        """Get attribute by name with type safety"""
        return self.attributes.get(name)

    def set_attribute(self, name: str, attr_type: AttributeType, value: Any) -> None:
        """Set attribute with type validation"""
        # Add validation logic here
        self.attributes[name] = (attr_type, value)