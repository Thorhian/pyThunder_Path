#!/usr/bin/env python3
import ctypes
import time

rendoc = ctypes.CDLL('./renderdocInterface.so')

rendoc.helloWorld()

apiPtr = ctypes.POINTER(ctypes.c_void_p)

apiFetcher_func = rendoc.checkGetAPI
apiFetcher_func.restype = ctypes.POINTER(ctypes.c_void_p)

apiPtr = apiFetcher_func()
print(apiPtr)

startCap = rendoc.startCapture
endCap = rendoc.endCapture

startCap.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
endCap.argtypes   = [ctypes.POINTER(ctypes.c_void_p)]

startCap(apiPtr)
time.sleep(3)
endCap(apiPtr)
