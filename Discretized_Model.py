#!/usr/bin/env python3
import numpy as np
import Helper_Functions as hf

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

    def check_cut(self, center1, center2, radius, image_indice):
        '''
        Checks pixels in an image where a given tool path
        (represented by two circles of the same radius) is located.
        Amount of various pixels are returned in a dictionary.

        TODO: Add circle and rectangle bounds checks next.
        '''
        search_bounds = hf.double_circle_bbox(center1, radius, center2, radius)
        image_shape = self.images[image_indice].shape
        print(image_shape)
        material_counter = dict()
        material_counter["stock"] = 0

        x = search_bounds[2]
        y = search_bounds[1]
        print(type(x), type(y), type(image_indice))
        while y < search_bounds[0] or y < image_shape[0]:
            x = search_bounds[2]
            while x < search_bounds[3] or x < image_shape[1]:
                current_pixel = self.images[image_indice][y][x]
                if current_pixel[3] > 0 and current_pixel[2] == 255:
                    material_counter["stock"] += 1

                x += 1

            y += 1


        return material_counter

    def __check_circle(center, radius, pixel_coords):
        eq_left_side = pow(pixel_coords[0] - center[0], 2) + pow(pixel_coords[1] - center[1], 2)

        return (eq_left_side < pow(radius, 2))

    def __check_rectangle(rect_points):

        return

    def __find_rectangle_points(center1, center2, radius):
        translated_cent1 = np.array(center1) - np.array(center2)
        translated_cent2 = np.array(center2) - np.array(center1)

        norm_rad1 = (translated_cent1 / np.linalg.norm(translated_cent1)) * radius
        norm_rad2 = (translated_cent2 / np.linalg.norm(translated_cent1)) * radius

        trans_point1 = (norm_rad1[1], -norm_rad1[0])
        trans_point2 = (-norm_rad1[1], norm_rad1[0])
        trans_point3 = (norm_rad2[1], -norm_rad2[0])
        trans_point4 = (-norm_rad2[1], norm_rad2[0])

        return np.array([trans_point1, trans_point2, trans_point3, trans_point4])

    def check_point_capsule(center1, center2, radius, point):

        return false
