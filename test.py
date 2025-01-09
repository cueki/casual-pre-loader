from handlers.file_handler import FileHandler
from handlers.vpk_handler import VPKHandler
from operations.file_processors import pcf_duplicate_index_processor

from handlers.file_handler import FileHandler
from operations.file_processors import pcf_duplicate_index_processor
from models.pcf_file import PCFFile


def process_pcf_to_test_file(vpk_handler, input_pcf_name: str, output_pcf_name: str = "test.pcf"):
    """
    Process a PCF file and write the result to a test file instead of patching the VPK.

    Args:
        vpk_handler: VPK handler instance
        input_pcf_name: Name of the input PCF file
        output_pcf_name: Name of the output test file
    """
    file_handler = FileHandler(vpk_handler)

    # Extract the PCF file to a temporary location
    full_path = vpk_handler.find_file_path(input_pcf_name)
    if not full_path:
        print(f"Could not find file: {input_pcf_name}")
        return False

    # Create temp file for processing
    temp_path = f"temp_{input_pcf_name}"

    try:
        # Extract file
        if not vpk_handler.extract_file(full_path, temp_path):
            print(f"Failed to extract {full_path}")
            return False

        # Process the PCF
        pcf = PCFFile(temp_path)
        pcf.decode()

        # Apply the processor
        processor = pcf_duplicate_index_processor()
        processed_pcf = processor(pcf)

        # Write to test file
        processed_pcf.encode(output_pcf_name)
        print(f"Processed PCF written to {output_pcf_name}")

        return True

    except Exception as e:
        print(f"Error processing PCF: {e}")
        return False

def main():
    vpk_handler = VPKHandler("tf2_misc_dir.vpk")
    file_handler = FileHandler(vpk_handler)

    # Process a specific PCF file
    # success = file_handler.process_file(
    #     "medicgun_beam.pcf",  # or whatever your PCF file is named
    #     pcf_duplicate_index_processor()
    # )
    process_pcf_to_test_file(vpk_handler, "medicgun_beam.pcf", "test.pcf")
    # print(f"Processing {'succeeded' if success else 'failed'}")


if __name__ == "__main__":
    main()