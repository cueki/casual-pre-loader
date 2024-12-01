import hashlib
from dataclasses import dataclass
from typing import Tuple
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import struct


@dataclass
class VPKHeader:
    signature: int  # 0x55aa1234
    version: int  # 2
    tree_size: int  # Size of directory tree
    file_data_section_size: int
    archive_md5_section_size: int
    other_md5_section_size: int
    signature_section_size: int

    @classmethod
    def from_file(cls, f):
        return cls(*struct.unpack('<7I', f.read(28)))


def compute_vpk_hashes(vpk_path: str):
    with open(vpk_path, 'rb') as f:
        # Read header but keep raw bytes
        header_bytes = f.read(28)
        header = VPKHeader(*struct.unpack('<7I', header_bytes))

        # Get directory tree data
        directory_data = f.read(header.tree_size)
        directory_hash = hashlib.md5(directory_data).digest()

        # Skip file data section if present
        file_data = f.read(header.file_data_section_size)

        # Read archive MD5 entries
        archive_md5_data = f.read(header.archive_md5_section_size)
        archive_md5_hash = hashlib.md5(archive_md5_data).digest()

        # Complete hash includes everything up through both hashes
        complete_data = (
                header_bytes +  # VPK header
                directory_data +  # Directory tree
                file_data +  # File data section
                archive_md5_data +  # Archive MD5 entries
                directory_hash +  # Directory hash
                archive_md5_hash  # Archive hash
        )
        complete_hash = hashlib.md5(complete_data).digest()

        return directory_hash, archive_md5_hash, complete_hash


def patch_vpk_hashes(vpk_path: str):
    """
    Update a VPK file with new hashes after directory modification.
    Modifies the file in place.
    """
    # First compute the new hashes
    directory_hash, archive_md5_hash, complete_hash = compute_vpk_hashes(vpk_path)

    with open(vpk_path, 'rb') as f:
        # Read header to get positions
        header = VPKHeader.from_file(f)

        # Calculate position of hash section
        hash_pos = (28 +  # Header size
                    header.tree_size +  # Directory tree
                    header.file_data_section_size +  # File data
                    header.archive_md5_section_size # Archive MD5 entries
                    )

    # Now write the new hashes
    with open(vpk_path, 'rb+') as f:
        # Write new directory hash
        f.seek(hash_pos)
        print("File pointer position:", f.tell())
        # f.write(directory_hash)
        # f.seek(hash_pos + 16)  # 16 bytes for archive hash
        # f.write(archive_md5_hash)
        # # Write new complete hash (after directory hash and archive hash)
        # f.seek(hash_pos + 32)  # + 32 for archive hash
        # f.write(complete_hash)


def get_vpk_sig(vpk_path: str):

    with open(vpk_path, 'rb+') as f:
        header = VPKHeader.from_file(f)
        print(header.other_md5_section_size)
        sig_pos = (28 +  # Header size
                    header.tree_size +  # Directory tree
                    header.file_data_section_size +  # File data
                    header.archive_md5_section_size + # Archive MD5 entries
                    header.other_md5_section_size  # Hashes
                    )

        f.seek(sig_pos)  # Move to signature position
        print("File pointer position:", f.tell())  # Print current pointer position

        data = f.read(200)  # Read 200 bytes
        # print("Read data:", data)  # Print the data read


def hex_print(data: bytes) -> None:
    """Print bytes as hex string."""
    print(''.join(f'{b:02x}' for b in data))


def decode_valve_key(key_hex: str) -> bytes:
    """Convert a Valve hex-encoded key string to bytes"""
    return bytes.fromhex(key_hex)


def unsign_vpk(vpk_path: str):
    """Remove the signature section from a VPK file"""
    with open(vpk_path, 'rb+') as f:
        # Read header
        header = VPKHeader.from_file(f)

        # Calculate position where signature section begins
        sig_pos = (28 +  # Header size
                   header.tree_size +
                   header.file_data_section_size +
                   header.archive_md5_section_size +
                   header.other_md5_section_size)

        # Set signature_section_size to 0 in header
        f.seek(24)  # Position of signature_section_size in header
        f.write(struct.pack('<I', 0))

        # Truncate file to remove signature section
        f.seek(sig_pos)
        f.truncate()


def read_signature_section(vpk_path: str, public_key_hex: str):
    """
    Read and attempt to verify the signature section of a VPK using a provided public key
    """
    # Convert hex public key to bytes and load it
    public_key_der = bytes.fromhex(public_key_hex)
    public_key = serialization.load_der_public_key(public_key_der)

    with open(vpk_path, 'rb') as f:
        # Read header
        header = VPKHeader.from_file(f)

        # Calculate signature section position
        sig_pos = (28 +  # Header
                   header.tree_size +
                   header.file_data_section_size +
                   header.archive_md5_section_size +
                   header.other_md5_section_size)

        # Read the signed data
        f.seek(0)
        signed_data = f.read(sig_pos)

        # Move to signature section
        f.seek(sig_pos)

        # Read signature section
        pub_key_len = struct.unpack('<I', f.read(4))[0]
        stored_pub_key = f.read(pub_key_len)
        sig_len = struct.unpack('<I', f.read(4))[0]
        signature = f.read(sig_len)

        print(f"Found signature section:")
        print(f"Public key length: {pub_key_len}")
        print(f"Stored public key: {stored_pub_key.hex()}")
        print(f"Signature length: {sig_len}")
        print(f"Signature: {signature.hex()}")

        try:
            # Try to verify the signature
            public_key.verify(
                signature,
                signed_data,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            print("Signature verified successfully!")
        except Exception as e:
            print(f"Signature verification failed: {e}")

        return signature, stored_pub_key


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python vpk_patcher.py <vpk_file>")
        sys.exit(1)

    # # Example: Read the VPK, modify directory, and patch hashes
    vpk_path = sys.argv[1]
    # get_vpk_sig(vpk_path)

    pub_key = "30819D300D06092A864886F70D010101050003818B0030818702818100B1C0F11CB2982F29259507A774D4834377C5B7A38D9A4B3892B598009F16AA109565CB09AD25DE0D3D1A089C3CB68E491921CC142F383383201DE98262A76ED8A6CC78BC51685A0A64A6172C67127AF23E78731F4A82C201D64C9AB80937322184B642727FE142D15CC045F3583E19E3E3E1A9C50C0FC84113573A520A8F7323020111"
    sig, stored_key = read_signature_section(vpk_path, pub_key)

