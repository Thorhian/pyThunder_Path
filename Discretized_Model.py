#!/usr/bin/env python3
import numpy as np

class DiscretizedModel:
    '''
    Contains the additive slices of a model to generate tool paths.
    Also contains functions to operate on images to generate tool paths.
    All images should be of the same system and the same resolution, in
    both width and height along with the length of a pixel in mm.

    Constructor Parameters:
        pixel_area (float): Describes the pixel's length and height in mm,
                            hence only a single float is needed.

        coordinate_offset ([float, float] or (float, float)):
                            The real world coordinate offset for each pixel.
                            Pixel[0][0] is not neccesarily X = 0.0 and Y = 0.0
                            in the system.
    '''
    def __init__(self, pixel_res: float, coordinate_offset: float = (0.0, 0.0)):
        self.pixel_res = pixel_res
        self.coordinate_offset = coordinate_offset
        self.images = []
        self.heights = []

    def add_layer(self, image, height):
        '''
        Adds an image to the object that should be an additive slice
        of the system being to be processed for path planning. The image
        should be some kind of random access compatible list, such as a
        numpy array. The Z-Height of the image should be provided (Z is assumed
        to be up/down).

        Parameters:
            image (list or array): The multidimensional array containing the pixels
                                   of an image representing an additive slice of the system.

            height (float): The Z coordinate of the slice.
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
