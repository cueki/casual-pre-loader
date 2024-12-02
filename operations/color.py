import copy
import colorsys
from collections import defaultdict
from typing import Tuple, List, Dict
from dataclasses import dataclass
from core.constants import AttributeType
from core.traversal import PCFTraversal
from models.pcf_file import PCFFile

RGB = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]


def rgb_to_hsv(r, g, b):
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, s * 100, v * 100


def hsv_to_rgb(h, s, v):
    h, s, v = h / 360, s / 100, v / 100
    return colorsys.hsv_to_rgb(h, s, v)


def is_color_attribute(name: str) -> bool:
    color_indicators = {b'color', b'color1', b'color2', b'color_fade', b'tint clamp'}
    if isinstance(name, str):
        name = name.encode('ascii')
    return any(indicator in name.lower() for indicator in color_indicators)


def average_rgb(rgb_list):
    """Calculate average RGB from a list of RGB tuples."""
    r_sum = sum(rgb[0] for rgb in rgb_list)
    g_sum = sum(rgb[1] for rgb in rgb_list)
    b_sum = sum(rgb[2] for rgb in rgb_list)
    n = len(rgb_list)
    return (r_sum / n), (g_sum / n), (b_sum / n)


def color_shift(rgb_color_list: list, target_color: RGB, vibe_enabled=True):
    # Calc average rgb
    avg_r, avg_g, avg_b = average_rgb(rgb_color_list)

    # Convert to average HSV
    average_hsv = rgb_to_hsv(avg_r, avg_g, avg_b)
    
    # Convert target color to HSV
    target_hsv = rgb_to_hsv(*target_color)

    # Calculate hue difference
    hue_diff = target_hsv[0] - average_hsv[0]

    # Convert input RGB colors to HSV
    hsv_colors = [rgb_to_hsv(*rgb) for rgb in rgb_color_list]

    if not vibe_enabled:
        shifted_colors = []
        for color in rgb_color_list:
            # I know this is really stupid but im tired and wanted a quick fix for toes that matched the logic
            new_hue = target_hsv[0]
            new_sat = target_hsv[1]
            new_vib = target_hsv[2]
            rgb = hsv_to_rgb(new_hue, new_sat, new_vib) #  hardcoded max vibrance
            shifted_colors.append(tuple(round(c * 255) for c in rgb))
        return shifted_colors

    # Shift each color by the hue difference
    if vibe_enabled:
        shifted_colors = []
        for hsv in hsv_colors:
            new_hue = hsv[0] + hue_diff
            # Normalize hue to 0-360 range
            if new_hue > 360:
                new_hue -= 360
            elif new_hue < 0:
                new_hue += 360

            # Convert back to RGB, scale to 0-255 range
            rgb = hsv_to_rgb(new_hue, hsv[1],  100)
            shifted_colors.append(tuple(round(c * 255) for c in rgb))

        return shifted_colors


def analyze_pcf_colors(pcf: PCFFile) -> Dict[str, Dict[str, List[tuple[RGB, bytes]]]]:

    traversal = PCFTraversal(pcf)
    colors = {
        'red': {'color1': [], 'color2': [], 'tint_clamp': [], 'color_fade': []},
        'blue': {'color1': [], 'color2': [], 'tint_clamp': [], 'color_fade': []},
        'neutral': {'color1': [], 'color2': [], 'tint_clamp': [], 'color_fade': []}
    }

    current_element = None
    color_attrs = traversal.find_attributes(attr_type=AttributeType.COLOR, max_depth=0)

    for element, attr_name, (_, rgba), _ in color_attrs:
        if not element.element_name.startswith(b'Color'):
            current_element = element.element_name
        elif current_element:
            r, g, b, a = rgba

            if (r + g + b) == 765 or (r + g + b) == 0 or (r == g == b):
                continue

            # Determine team
            is_red = b'_red' in current_element or b'red_' in current_element
            is_blue = b'_blue' in current_element or b'blue_' in current_element
            team = 'red' if is_red else 'blue' if is_blue else 'neutral'

            # Determine category
            if b'tint clamp' in attr_name:
                category = 'tint_clamp'
            elif b'color_fade' in attr_name:
                category = 'color_fade'
            elif b'color1' in attr_name:
                category = 'color1'
            elif b'color2' in attr_name:
                category = 'color2'
            else:
                continue
            colors[team][category].append(((r, g, b), current_element))

    return colors


def transform_with_shift(pcf: PCFFile,
                         original_colors_with_context: List[Tuple[Tuple[int, int, int], bytes]],
                         shifted_colors: List[Tuple[int, int, int]],) -> PCFFile:

    # Create mapping of (color, context) -> new_color
    color_map = {(orig, context): shifted
                 for (orig, context), shifted in zip(original_colors_with_context, shifted_colors)}

    result_pcf = copy.deepcopy(pcf)
    changes_made = []
    traversal = PCFTraversal(result_pcf)
    transforms_needed = len(original_colors_with_context)
    transforms_done = 0

    current_element = None
    color_attrs = traversal.find_attributes(attr_type=AttributeType.COLOR, max_depth=0)

    for element, attr_name, (attr_type, rgba), _ in color_attrs:
        if transforms_done == transforms_needed:
            break

        if not element.element_name.startswith(b'Color'):
            current_element = element.element_name
        elif current_element and is_color_attribute(attr_name):
            r, g, b, a = rgba
            rgb = (r, g, b)

            if (r + g + b) == 765 or (r + g + b) == 0 or (r == g == b):
                continue

            # Look up color using both RGB value and context
            color_context_key = (rgb, current_element)
            if color_context_key in color_map:
                new_r, new_g, new_b = color_map[color_context_key]
                new_value = (new_r, new_g, new_b, a)
                element.attributes[attr_name] = (attr_type, new_value)
                transforms_done += 1
    return result_pcf


def transform_team_colors(pcf: PCFFile, colors: Dict[str, Dict[str, List[tuple[RGB, bytes]]]],
                          targets: Dict[str, Dict[str, RGB]]) -> PCFFile:
    current_pcf = copy.deepcopy(pcf)
    has_red = any(colors['red'].values())
    has_blue = any(colors['blue'].values())
    has_neutral = any(colors['neutral'].values())

    if has_red or has_blue or has_neutral:
        for team in ['red', 'blue', 'neutral']:
            for category in ['color1', 'color2', 'tint_clamp', 'color_fade']:
                if colors[team][category] and targets[team][category]:

                    original_colors_with_context = colors[team][category]
                    original_colors = [c[0] for c in original_colors_with_context]
                    shifted = color_shift(original_colors, targets[team][category], vibe_enabled=False)
                    print("WARN: WILL BE IDENTICAL ON SECOND RUN:")
                    print("OlD:", original_colors)
                    print("NEW:", shifted)

                    current_pcf = transform_with_shift(
                        current_pcf,
                        original_colors_with_context,
                        shifted,
                    )
    else:
        print("WARN: you are attempting to color change particle that does not contain any color attributes! "
              "Nothing will happen!")
        current_pcf = current_pcf # maybe trap this in the future or do smthn here idk
    return current_pcf