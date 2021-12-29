#!/usr/bin/env python3
import numpy as np

class DiscretizedModel:

    def __init__(self, pixel_area: float):
        self.pixel_area = pixel_area
        self.images = []
        self.heights = []

    def add_layer(self, image, height):
        '''
        Adds an image to the object that should be an additive slice
        of the system being to be processed for path planning. The image
        should be some kind of random access compatible list, such as a
        numpy array. The Z-Height of the image should be provided (Z is assumed
        to be up/down).
        '''
        self.images.append(image)
        self.heights.append(height)

    def check_cut(self, center1, center2, radius, height):
        '''
        Checks pixels in an image where a given tool path
        (represented by two circles of the same radius) is located.
        Amount of various pixels are returned in a dictionary.
        '''
        return 0
