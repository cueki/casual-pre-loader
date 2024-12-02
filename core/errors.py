# this needs to be done but im very lazy and stupid and also I never have any errors ever.

class PCFError(Exception):
    pass

class PCFVersionError(PCFError):
    pass

class PCFAttributeError(PCFError):
    pass

class PCFEncodingError(PCFError):
    pass

class PCFDecodingError(PCFError):
    pass
