import ctypes
import sys

class RenderDocAPI:
    '''
    Class for hooking into the RenderDoc In-Application API
    to allow for capturing in this headless application.
    '''

    def __init__(self):
        '''
        Immediately loads the C++ bridge library between this
        python application and RenderDoc's API and proceeds
        initialize the API and get the capture functions
        ready for use.
        '''
        self.rdBridge = ctypes.CDLL(sys.path[0] + '/renderdocInterface.so')
        self.apiFetch = self.rdBridge.checkGetAPI
        self.apiFetch.restype = ctypes.POINTER(ctypes.c_void_p)
        self.apiPtr = self.apiFetch()

        self.startCap = self.rdBridge.startCapture
        self.startCap.argtypes = [ctypes.POINTER(ctypes.c_void_p)]

        self.endCap = self.rdBridge.endCapture
        self.endCap.argtypes = [ctypes.POINTER(ctypes.c_void_p)]


    def start_capture(self):
        '''
        Tells RenderDoc to begin capturing graphics "stuff".
        Make sure to use the "stop_capture()" function before
        stopping the program.
        '''
        self.startCap(self.apiPtr)

    def stop_capture(self):
        '''
        Tells RenderDoc to stop capturing graphics "stuff".
        Make sure to only call this after calling
        "start_capture()".
        '''
        self.endCap(self.apiPtr)
