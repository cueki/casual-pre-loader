import copy
import os
from handlers.file_handler import FileHandler
from handlers.vpk_handler import VPKHandler
from models.pcf_file import PCFFile, PCFElement
from core.constants import AttributeType


def find_particle_system_definition(pcf: PCFFile, name: str):
    """
    Find a particle system definition element by name.
    Looks specifically for elements that have the characteristic arrays
    of a particle system definition.
    """
    name_bytes = name.encode('ascii')
    characteristic_arrays = {b'operators', b'renderers', b'initializers', b'emitters'}

    # First pass: look for exact name match
    for elem in pcf.elements:
        if elem.element_name == name_bytes:
            # Check if this element has the characteristic arrays of a particle system definition
            has_arrays = any(array_name in elem.attributes for array_name in characteristic_arrays)
            if has_arrays:
                return elem

    # Debug: Log all particle system names found in the PCF
    found_systems = []
    for elem in pcf.elements:
        has_arrays = any(array_name in elem.attributes for array_name in characteristic_arrays)
        if has_arrays:
            try:
                sys_name = elem.element_name.decode('ascii')
                found_systems.append(sys_name)
            except UnicodeDecodeError:
                continue

    print(f"\nDebug: Looking for system '{name}'")
    print(f"Debug: Found {len(found_systems)} particle systems in PCF:")
    print("\n".join(f"  - {sys}" for sys in sorted(found_systems)))

    return None


def can_update_attribute(attr_type: AttributeType, attr_name: bytes) -> bool:
    """Determine if an attribute can be safely updated without changing file size."""
    # Only allow numerical types
    safe_types = {
        AttributeType.INTEGER,
        AttributeType.FLOAT,
        AttributeType.COLOR,  # RGBA values are just numbers
        AttributeType.VECTOR2,
        AttributeType.VECTOR3,
        AttributeType.VECTOR4,
    }

    # Never modify certain attributes even if they're numerical
    unsafe_attributes = {
        b'child',
        b'children',
        b'parent',
        b'parents',
        b'operators',
        b'emitters',
        b'initializers',
        b'renderers',
        b'forces',
        b'constraints',
        b'type_name_index',  # Just to be extra safe
    }

    return (attr_type in safe_types and
            attr_name not in unsafe_attributes)


def get_array_elements(pcf: PCFFile, elem: PCFElement, array_name: bytes) -> list[PCFElement]:
    """Get all elements from an array attribute."""
    if array_name not in elem.attributes:
        return []

    attr_type, indices = elem.attributes[array_name]
    if attr_type != AttributeType.ELEMENT_ARRAY:
        return []

    elements = []
    for idx in indices:
        if 0 <= idx < len(pcf.elements):
            elements.append(pcf.elements[idx])

    return elements


def find_matching_element(target_elem: PCFElement, source_elements: list[PCFElement]):
    """Find a matching element in the source elements list based on name and functionName."""
    target_name = target_elem.element_name
    target_function_name = target_elem.attributes.get(b'functionName', (None, None))[1]

    for source_elem in source_elements:
        if source_elem.element_name == target_name:
            source_function_name = source_elem.attributes.get(b'functionName', (None, None))[1]
            if source_function_name == target_function_name:
                return source_elem
    return None


def format_value(value):
    """Format value for logging."""
    if isinstance(value, (tuple, list)):
        return f"{value}"
    return str(value)


def update_matching_attributes(target_elem: PCFElement, source_elem: PCFElement) -> tuple[bool, list[str]]:
    """
    Update numerical attributes that exist in both elements.
    Returns (changes_made, list of change descriptions)
    """
    changes_made = False
    changes = []

    for attr_name, (target_type, target_value) in target_elem.attributes.items():
        if attr_name not in source_elem.attributes:
            continue

        source_type, source_value = source_elem.attributes[attr_name]
        if source_type != target_type:
            continue

        if can_update_attribute(target_type, attr_name):
            if target_value != source_value:
                target_elem.attributes[attr_name] = (target_type, source_value)
                changes.append(
                    f"    {attr_name.decode('ascii')}: {format_value(target_value)} → {format_value(source_value)}")
                changes_made = True

    return changes_made, changes


class PCFModifier:
    def __init__(self, target_pcf: PCFFile, source_pcf: PCFFile):
        self.target_pcf = target_pcf
        self.source_pcf = source_pcf

    def update_array_elements(self, pcf: PCFFile, target_elem: PCFElement, source_elem: PCFElement,
                              array_name: bytes) -> tuple[bool, list[str]]:
        """Update elements in a specific array."""
        changes_made = False
        all_changes = []

        target_elements = get_array_elements(pcf, target_elem, array_name)
        source_elements = get_array_elements(self.source_pcf, source_elem, array_name)

        for target_child in target_elements:
            matching_source = find_matching_element(target_child, source_elements)
            if matching_source:
                child_changed, child_changes = update_matching_attributes(target_child, matching_source)
                if child_changed:
                    all_changes.append(
                        f"  In {array_name.decode('ascii')} element {target_child.element_name.decode('ascii')}:")
                    all_changes.extend(child_changes)
                    changes_made = True

        return changes_made, all_changes

    def update_all_array_elements(self, pcf: PCFFile, target_elem: PCFElement, source_elem: PCFElement) -> tuple[
        bool, list[str]]:
        """Update elements in all arrays."""
        changes_made = False
        all_changes = []

        array_attributes = [
            b'operators',
            b'renderers',
            b'initializers',
            b'emitters',
            b'forces'
        ]

        for array_name in array_attributes:
            array_changed, array_changes = self.update_array_elements(pcf, target_elem, source_elem, array_name)
            if array_changed:
                changes_made = True
                all_changes.extend(array_changes)

        return changes_made, all_changes

    def modify_to_match(self, target_element_name: str, source_element_name: str) -> tuple[PCFFile, list[str]]:
        """
        Modify numerical attributes in target element to match source element where possible.
        Returns (modified PCF, list of changes made)
        """
        modified_pcf = copy.deepcopy(self.target_pcf)
        all_changes = []

        source_element = find_particle_system_definition(self.source_pcf, source_element_name)
        if not source_element:
            raise ValueError(f"Source particle system {source_element_name} not found in source PCF")

        target_element = find_particle_system_definition(modified_pcf, target_element_name)
        if not target_element:
            raise ValueError(f"Target particle system {target_element_name} not found in target PCF")

        # Update root attributes
        root_changed, root_changes = update_matching_attributes(target_element, source_element)
        if root_changed:
            all_changes.append("  Root element changes:")
            all_changes.extend(root_changes)

        # Update array elements
        arrays_changed, array_changes = self.update_all_array_elements(modified_pcf, target_element, source_element)
        if arrays_changed:
            all_changes.extend(array_changes)

        return modified_pcf, all_changes


def batch_process_pcf(game_vpk_path: str, mod_vpk_path: str, pcf_path: str,
                      element_mappings: list[tuple[str, str]], create_backup: bool = True) -> tuple[bool, list[str]]:
    """Process multiple elements in a PCF file in a single pass."""
    messages = []
    game_vpk = VPKHandler(game_vpk_path)
    mod_vpk = VPKHandler(mod_vpk_path)
    game_file_handler = FileHandler(game_vpk)

    temp_game_pcf = f"temp_game_{os.path.basename(pcf_path)}"
    temp_mod_pcf = f"temp_mod_{os.path.basename(pcf_path)}"

    try:
        print(f"\nDebug: Extracting files...")
        print(f"Debug: Game VPK Path: {game_vpk_path}")
        print(f"Debug: Mod VPK Path: {mod_vpk_path}")
        print(f"Debug: PCF Path: {pcf_path}")

        # Extract PCFs from both VPKs
        if not game_vpk.extract_file(pcf_path, temp_game_pcf):
            messages.append(f"Failed to extract {pcf_path} from game VPK")
            return False, messages

        if not mod_vpk.extract_file(pcf_path, temp_mod_pcf):
            messages.append(f"Failed to extract {pcf_path} from mod VPK")
            return False, messages

        print(f"Debug: Temp files created successfully")
        print(f"Debug: Game PCF temp file: {temp_game_pcf}")
        print(f"Debug: Mod PCF temp file: {temp_mod_pcf}")

        # Load and decode PCFs
        print(f"Debug: Loading PCFs...")
        source_pcf = PCFFile(temp_mod_pcf)
        source_pcf.decode()
        print(f"Debug: Source PCF loaded and decoded")

        def processor(target_pcf: PCFFile) -> PCFFile:
            modified_pcf = copy.deepcopy(target_pcf)
            modifier = PCFModifier(modified_pcf, source_pcf)

            successful_mappings = []
            failed_mappings = []
            all_changes = {}

            for game_element, mod_element in element_mappings:
                try:
                    print(f"\nDebug: Processing mapping {game_element} → {mod_element}")
                    modified_pcf, changes = modifier.modify_to_match(game_element, mod_element)
                    if changes:
                        successful_mappings.append((game_element, mod_element))
                        all_changes[(game_element, mod_element)] = changes
                    else:
                        messages.append(f"No changes needed for {game_element} → {mod_element}")
                except ValueError as e:
                    failed_mappings.append((game_element, mod_element, str(e)))

            if successful_mappings:
                messages.append("\nSuccessful updates:")
                for game_elem, mod_elem in successful_mappings:
                    messages.append(f"\n  {game_elem} → {mod_elem}:")
                    messages.extend(all_changes[(game_elem, mod_elem)])

            if failed_mappings:
                messages.append("\nFailed updates:")
                for game_elem, mod_elem, error in failed_mappings:
                    messages.append(f"  - {game_elem} → {mod_elem}: {error}")

            return modified_pcf

        success = game_file_handler.process_file(pcf_path, processor, create_backup)
        return success, messages

    finally:
        print("\nDebug: Cleaning up temporary files...")
        if os.path.exists(temp_game_pcf):
            os.remove(temp_game_pcf)
            print(f"Debug: Removed {temp_game_pcf}")
        if os.path.exists(temp_mod_pcf):
            os.remove(temp_mod_pcf)
            print(f"Debug: Removed {temp_mod_pcf}")


def update_from_config(config_path: str):
    """Update PCF files based on a YAML config file with detailed change reporting."""
    import yaml

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    game_vpk = config['game_vpk_path']
    if not os.path.exists(game_vpk):
        print(f"Game VPK not found: {game_vpk}")
        return

    all_messages = []

    for mod in config.get('mods', []):
        mod_vpk = mod['vpk_path']
        if not os.path.exists(mod_vpk):
            print(f"Mod VPK not found: {mod_vpk}")
            continue

        mod_messages = [f"\nProcessing mod: {os.path.basename(mod_vpk)}"]
        pcf_mappings = {}

        for pcf_patch in mod.get('patches', []):
            pcf_file = pcf_patch['pcf_file']
            if pcf_file not in pcf_mappings:
                pcf_mappings[pcf_file] = []

            for element_group in pcf_patch.get('elements', []):
                mod_element = element_group['mod_element']
                game_elements = element_group.get('game_elements', [])

                if game_elements:
                    pcf_mappings[pcf_file].extend(
                        (game_element, mod_element) for game_element in game_elements
                    )

        for pcf_file, mappings in pcf_mappings.items():
            mod_messages.append(f"\nPCF file: {pcf_file}")
            success, pcf_messages = batch_process_pcf(
                game_vpk,
                mod_vpk,
                pcf_file,
                mappings
            )
            mod_messages.extend(pcf_messages)
            mod_messages.append(f"Overall status: {'Success' if success else 'Failed'}")

        all_messages.extend(mod_messages)

    print("\n=== PCF Processing Report ===")
    for message in all_messages:
        print(message)
    print("\n=== End of Report ===")

def main():
    # update_from_config('dxhr_fx.yaml')
    update_from_config('medicgun_beam.yaml')

if __name__ == "__main__":
    main()