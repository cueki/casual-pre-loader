from codec.reader import PCFReader
from codec.writer import PCFWriter
from models.pcf_file import PCFFile

class PCFCodec:
    @staticmethod
    def decode(file_path: str) -> PCFFile:
        """Decode PCF from file"""
        with open(file_path, 'rb') as f:
            decode = PCFReader(f)
            return decode.decode()

    @staticmethod
    def encode(pcf: PCFFile, file_path: str) -> None:
        """Encode PCF to file"""
        with open(file_path, 'wb') as f:
            encode = PCFWriter(f)
            encode.encode(pcf)