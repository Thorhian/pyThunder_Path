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
    def __init__(self, pixel_res: float, coordinate_offset: tuple[float, float] = (0.0, 0.0)):
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

    def cut_circle(self, center, radius, image_indice):
        search_bounds = hf.double_circle_bbox(center, radius, center, radius)
        image_shape = self.images[image_indice].shape
        img_res = self.images[image_indice].shape

        x = np.clip(search_bounds[2], 0, img_res[1])
        y = np.clip(search_bounds[1], 0, img_res[0])
        while y < search_bounds[0] or y < image_shape[0]:
            x = search_bounds[2]
            while x < search_bounds[3] or x < image_shape[1]:
                current_pixel = self.images[image_indice][y][x]
                if current_pixel[3] > 0 and self.check_in_circle(center, radius, (x, y)):
                    self.images[image_indice][y][x][3] = 0

                x += 1

            y += 1

        return 1

    def check_cut(self, center1, center2, radius, image_indice):
        '''
        Checks pixels in an image where a given tool path
        (represented by two circles of the same radius) is located.
        Amount of various pixels are returned in a dictionary.
        '''
        search_bounds = hf.double_circle_bbox(center1, radius, center2, radius)
        image_shape = self.images[image_indice].shape
        print(image_shape)
        material_counter = dict()
        material_counter["stock"] = 0
        img_res = self.images[image_indice].shape

        x = np.clip(search_bounds[2], 0, img_res[1])
        y = np.clip(search_bounds[1], 0, img_res[0])
        print(type(x), type(y), type(image_indice))
        while y < search_bounds[0] or y < image_shape[0]:
            x = search_bounds[2]
            while x < search_bounds[3] or x < image_shape[1]:
                current_pixel = self.images[image_indice][y][x]
                if current_pixel[3] > 0 and current_pixel[2] == 255 and self.check_in_capsule(center1, center2, radius, (x, y)):
                    material_counter["stock"] += 1

                x += 1

            y += 1


        return material_counter

    #FIXME Seems to always return true
    def check_in_capsule(self, center1, center2, radius, point):
        if not self.check_in_circle(center1, radius, point):
            if not self.check_in_circle(center2, radius, point):
                rect_verts = self.find_rectangle_points(center1, center2, radius)
                if not self.check_in_rectangle(rect_verts, point):
                    return False

        return True

    def find_rectangle_points(self, center1, center2, radius):
        translated_cent1 = np.array(center1) - np.array(center2) #type: ignore
        translated_cent2 = np.array(center2) - np.array(center1) #type: ignore

        norm_rad1 = (translated_cent1 / np.linalg.norm(translated_cent1)) * radius
        norm_rad2 = (translated_cent2 / np.linalg.norm(translated_cent2)) * radius

        trans_point1 = (norm_rad1[1], -norm_rad1[0]) + np.array(center2) #type: ignore
        trans_point2 = (-norm_rad1[1], norm_rad1[0]) + np.array(center2) #type: ignore
        trans_point3 = (norm_rad2[1], -norm_rad2[0]) + np.array(center1) #type: ignore
        trans_point4 = (-norm_rad2[1], norm_rad2[0]) + np.array(center1) #type: ignore

        return np.array([trans_point1, trans_point2, trans_point3, trans_point4])


    def check_in_circle(self, center, radius, pixel_coords):
        eq_left_side = pow(pixel_coords[0] - center[0], 2) + pow(pixel_coords[1] - center[1], 2)

        return (eq_left_side < pow(radius, 2))

    '''

    https://stackoverflow.com/questions/2752725/finding-whether-a-point-lies-inside-a-rectangle-or-not
    '''
    def check_in_rectangle(self, rect_points, point):
        sorted_indices = self.sort_rectangle_verts(rect_points)

        i = 0
        while i < 4:
            v1 = rect_points[sorted_indices[i]]
            v2 = rect_points[sorted_indices[(i + 1) % 4]]
            d = (v2[0] - v1[0]) * (point[1] - v1[1]) - (point[0] - v1[0]) * (v2[1] - v1[1])

            if d < 0:
                return False

            i += 1

        return True

    def sort_rectangle_verts(self, vertices):
        avg_center = np.add.reduce(vertices) / 4

        offset_verts = vertices + avg_center
        polar_rotations = np.zeros(4)

        i = 0
        while i < 4:
            rotation = np.rad2deg(np.arctan2(offset_verts[i][1],
                                             offset_verts[i][0]))

            if rotation < 0:
                rotation = 360 + rotation

            polar_rotations[i] = rotation
            i += 1


        return np.argsort(polar_rotations)
