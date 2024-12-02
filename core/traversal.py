from typing import Callable, Iterator, Any, Dict, List, Optional, Set
from models.pcf_file import PCFFile, PCFElement
from core.constants import AttributeType


class PCFTraversal:
    def __init__(self, pcf: PCFFile):
        self.pcf = pcf

    def get_child_elements(self, element: PCFElement) -> Iterator[PCFElement]:
        # Get all child elements through ELEMENT type attributes
        for attr_name, (type_, value) in element.attributes.items():
            if type_ == AttributeType.ELEMENT:
                if 0 <= value < len(self.pcf.elements):
                    yield self.pcf.elements[value]
            elif type_ == AttributeType.ELEMENT_ARRAY:
                for elem_idx in value:
                    if 0 <= elem_idx < len(self.pcf.elements):
                        yield self.pcf.elements[elem_idx]

    def iter_tree(self,
                  root: Optional[PCFElement] = None,
                  depth: int = -1,
                  seen_this_guy_before: Optional[Set[int]] = None) -> Iterator[tuple[PCFElement, int]]:
        """
        Recursively iterate through element tree, yielding (element, depth) pairs
        Use depth=-1 for unlimited depth traversal
        Handles circular references via seen_this_guy_before set
        I HAVE NO IDEA IF THIS WORKS EXACTLY HOW I INTENDED
        """
        if seen_this_guy_before is None:
            seen_this_guy_before = set()

        # Start from all root elements if no root specified
        if root is None:
            for element in self.pcf.elements:
                yield from self.iter_tree(element, depth, seen_this_guy_before)
            return

        # Avoid circular references
        elem_id = id(root)
        if elem_id in seen_this_guy_before:
            return
        seen_this_guy_before.add(elem_id)

        yield root, len(seen_this_guy_before) - 1

        # Recurse through children if depth allows
        if depth != 0:
            for child in self.get_child_elements(root):
                yield from self.iter_tree(child, depth - 1 if depth > 0 else -1, seen_this_guy_before)

        seen_this_guy_before.remove(elem_id)

    def find_attributes(self,
                        attr_type: Optional[AttributeType] = None,
                        attr_name_pattern: Optional[str] = None,
                        element_name_pattern: Optional[str] = None,
                        value_predicate: Optional[Callable[[Any], bool]] = None,
                        max_depth: int = 0
                        ) -> Iterator[tuple[PCFElement, str, tuple[AttributeType, Any], int]]:
        # Find attributes matching criteria
        for element, depth in self.iter_tree(depth=max_depth):
            if element_name_pattern and element_name_pattern not in str(element.element_name):
                continue

            for attr_name, (type_, value) in element.attributes.items():
                if attr_type and type_ != attr_type:
                    continue
                if attr_name_pattern and attr_name_pattern not in str(attr_name):
                    continue
                if value_predicate and not value_predicate(value):
                    continue
                yield element, attr_name, (type_, value), depth

    def modify_attributes(self,
                          modifier: Callable[[Any], Any],
                          attr_type: Optional[AttributeType] = None,
                          attr_name_pattern: Optional[str] = None,
                          element_name_pattern: Optional[str] = None,
                          value_predicate: Optional[Callable[[Any], bool]] = None,
                          max_depth: int = -1
                          ) -> List[Dict[str, Any]]:
        # Modify attributes matching criteria through the element tree - unused for now - offsets less scary ;w;
        changes = []
        for element, attr_name, (type_, old_value), depth in self.find_attributes(
                attr_type, attr_name_pattern, element_name_pattern, value_predicate, max_depth
        ):
            new_value = modifier(old_value)
            element.attributes[attr_name] = (type_, new_value)
            changes.append({
                'element_name': element.element_name,
                'attribute': attr_name,
                'old_value': old_value,
                'new_value': new_value,
                'depth': depth
            })
        return changes