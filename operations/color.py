import copy
import colorsys
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


def rgb_to_hsv(r, g, b):
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s * 100, v * 100


def hsv_to_rgb(h, s, v):
    h, s, v = h / 360, s / 100, v / 100
    return colorsys.hsv_to_rgb(h, s, v)


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


def average_rgb(rgb_list):
    """Calculate average RGB from a list of RGB tuples."""
    if not rgb_list:
        return 0, 0, 0
    r_sum = sum(rgb[0] for rgb in rgb_list)
    g_sum = sum(rgb[1] for rgb in rgb_list)
    b_sum = sum(rgb[2] for rgb in rgb_list)
    n = len(rgb_list)
    return round(r_sum / n), round(g_sum / n), round(b_sum / n)


def color_shift(rgb_color_list: list, target_color: RGB):
    # Convert input RGB colors to HSV
    hsv_colors = [rgb_to_hsv(*rgb) for rgb in rgb_color_list]

    # Convert target color to HSV
    target_hsv = rgb_to_hsv(*target_color)

    # Calculate average hue
    avg_hue = sum(hsv[0] for hsv in hsv_colors) / len(hsv_colors)

    # Calculate hue difference
    hue_diff = target_hsv[0] - avg_hue

    # Shift each color by the hue difference
    shifted_colors = []
    for hsv in hsv_colors:
        new_hue = hsv[0] + hue_diff
        # Normalize hue to 0-360 range
        if new_hue > 360:
            new_hue -= 360
        elif new_hue < 0:
            new_hue += 360

        # Convert back to RGB, scale to 0-255 range
        rgb = hsv_to_rgb(new_hue, hsv[1], hsv[2])
        shifted_colors.append(tuple(round(c * 255) for c in rgb))

    return shifted_colors


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