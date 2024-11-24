class PCFError(Exception):
    """Base exception for PCF-related errors"""
    pass

class PCFVersionError(PCFError):
    """Invalid PCF version"""
    pass

class PCFAttributeError(PCFError):
    """Invalid attribute type or value"""
    pass

class PCFEncodingError(PCFError):
    """Error during PCF encoding"""
    pass

class PCFDecodingError(PCFError):
    """Error during PCF decoding"""
    pass
