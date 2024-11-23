from dataclasses import dataclass
from typing import List
from models.element import PCFElement

@dataclass
class PCFFile:
    def __init__(self, version: str = "DMX_BINARY4_PCF2"):
        self.version = version
        self.string_dictionary: List[str] = []
        self.elements: List[PCFElement] = []

    def add_string(self, string: str) -> int:
        """Add a string to the dictionary if it doesn't exist and return its index"""
        if string not in self.string_dictionary:
            self.string_dictionary.append(string)
        return self.string_dictionary.index(string)

    def add_element(self, element: PCFElement):
        self.elements.append(element)