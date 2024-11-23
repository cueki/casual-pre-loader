from dataclasses import dataclass, field
from typing import List
from core.constants import PCFVersion
from models.element import PCFElement

@dataclass
class PCFFile:
    """Main PCF file model with improved functionality"""
    version: PCFVersion
    string_dictionary: List[str] = field(default_factory=list)
    elements: List[PCFElement] = field(default_factory=list)

    def add_string(self, string: str) -> int:
        """Add string to dictionary and return index"""
        if string not in self.string_dictionary:
            self.string_dictionary.append(string)
        return self.string_dictionary.index(string)

    def get_string(self, index: int) -> str:
        """Get string from dictionary with bounds checking"""
        if 0 <= index < len(self.string_dictionary):
            return self.string_dictionary[index]
        raise IndexError(f"String index {index} out of range")

    def add_element(self, element: PCFElement) -> None:
        """Add element with validation"""
        if not isinstance(element, PCFElement):
            raise TypeError("Must be PCFElement instance")
        self.elements.append(element)