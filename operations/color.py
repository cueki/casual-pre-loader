import copy
from typing import Tuple, List, Optional
from dataclasses import dataclass
from core.constants import AttributeType
from core.errors import PCFError
from models.pcf_file import PCFFile
from models.element import PCFElement

RGB = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]

@dataclass
class ColorChange:
    """Represents a color change in an element"""
    element_index: int
    element_type: str
    attribute_name: str
    old_color: RGBA
    new_color: RGBA


@dataclass
class ColorTransformResult:
    """Result of a color transformation operation"""
    changes: List[ColorChange]
    elements_processed: int
    attributes_changed: int

    @property
    def has_changes(self) -> bool:
        return len(self.changes) > 0


def is_color_attribute(name: str) -> bool:
    """Check if attribute name typically represents a color"""
    color_indicators = {'color', 'color1', 'color2', 'color_fade'}
    name = name.lower()
    return any(indicator in name for indicator in color_indicators)


def get_color_dominance(color: RGBA) -> Optional[str]:
    """
    Determine if a color is red or blue dominant.
    Returns: 'red', 'blue', or None if neither is dominant
    """
    r, g, b, a = color
    if r > b:
        return 'red'
    elif b > r:
        return 'blue'
    return None


def create_color(r: int, g: int, b: int, a: int = 255) -> RGBA:
    """Create a validated RGBA color tuple"""
    if not all(0 <= x <= 255 for x in (r, g, b, a)):
        raise PCFError("Color values must be between 0 and 255")
    return r, g, b, a


def transform_color(color: RGBA, transform_fn: callable) -> RGBA:
    """Transform a color while preserving alpha"""
    r, g, b, a = color
    new_r, new_g, new_b = transform_fn(r, g, b)
    return create_color(new_r, new_g, new_b, a)


class ColorTransform:
    """Handles PCF color transformations"""

    def __init__(self, pcf: PCFFile):
        self.pcf = copy.deepcopy(pcf)
        self.changes: List[ColorChange] = []

    def process_element(self, element_idx: int, element: PCFElement,
                        transform_fn: callable) -> List[ColorChange]:
        """Process an element's color attributes"""
        changes = []

        for attr_name, (attr_type, attr_value) in element.attributes.items():
            # Skip non-color attributes
            if attr_type != AttributeType.COLOR or not is_color_attribute(str(attr_name)):
                continue

            if not isinstance(attr_value, tuple) or len(attr_value) != 4:
                continue

            # Transform color
            try:
                new_color = transform_color(attr_value, transform_fn)
                if new_color != attr_value:
                    element.attributes[attr_name] = (attr_type, new_color)
                    changes.append(ColorChange(
                        element_index=element_idx,
                        element_type=self.pcf.string_dictionary[element.type_name_index],
                        attribute_name=str(attr_name),
                        old_color=attr_value,
                        new_color=new_color
                    ))
            except PCFError:
                continue

        return changes

    def apply_transform(self, transform_fn: callable,
                        element_filter: Optional[List[int]] = None) -> ColorTransformResult:
        """Apply color transformation to PCF"""
        self.changes = []
        elements_processed = 0

        for idx, element in enumerate(self.pcf.elements):
            if element_filter is not None and idx not in element_filter:
                continue

            changes = self.process_element(idx, element, transform_fn)
            self.changes.extend(changes)
            elements_processed += 1

        return ColorTransformResult(
            changes=self.changes,
            elements_processed=elements_processed,
            attributes_changed=len(self.changes)
        )

    def get_transformed_pcf(self) -> PCFFile:
        """Get the transformed PCF file"""
        return self.pcf


def transform_team_colors(pcf: PCFFile, red_color: RGB, blue_color: RGB,
                          elements: Optional[List[int]] = None) -> Tuple[PCFFile, ColorTransformResult]:
    """
    Transform team-specific colors in a PCF file.

    Args:
        pcf: PCF file to transform
        red_color: Target color for red team
        blue_color: Target color for blue team
        elements: Optional list of element indices to process

    Returns:
        Tuple of (transformed PCF, transformation result)
    """
    transformer = ColorTransform(pcf)

    def transform(r: int, g: int, b: int) -> RGB:
        dominance = get_color_dominance((r, g, b, 255))
        if dominance == 'red':
            target = red_color
        elif dominance == 'blue':
            target = blue_color
        else:
            return r, g, b

        # Calculate intensity factor
        intensity = (r + g + b) / (255 * 3)

        # Apply transformation while preserving intensity
        new_r = min(255, int(target[0] * intensity))
        new_g = min(255, int(target[1] * intensity))
        new_b = min(255, int(target[2] * intensity))

        return new_r, new_g, new_b

    result = transformer.apply_transform(transform, elements)
    return transformer.get_transformed_pcf(), result


def print_color_changes(result: ColorTransformResult) -> None:
    """Print a formatted summary of color changes"""
    if not result.has_changes:
        print("No color changes were made")
        return

    print(f"\nProcessed {result.elements_processed} elements")
    print(f"Changed {result.attributes_changed} color attributes\n")

    for change in result.changes:
        print(f"Element {change.element_index} ({change.element_type})")
        print(f"  Attribute: {change.attribute_name}")
        print(f"  Old: RGBA{change.old_color}")
        print(f"  New: RGBA{change.new_color}\n")