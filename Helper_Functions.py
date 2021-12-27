import moderngl
import glm
import numpy as np
import stl
import math

'''
Generates a series of lines forming a helix.
'''
def generate_helix(iterations, depth, diameter):
    z = np.linspace(0, depth, iterations)
    x = diameter * np.cos(z)
    y = diameter * np.sin(z)
    w = np.ones(iterations)

    return np.dstack([x, y, z, w])

def deg_to_rad(degrees):
    return (degrees * np.pi) / 180.0

def load_shader(filepath):
    shader_file = open(filepath)
    with shader_file as file:
        shader = file.read()

    shader_file.close()

    return shader

def calculate_aspect_ratio(res_tuple):
    gcd = np.gcd(res_tuple[0], res_tuple[1])

    return ((res_tuple[0] / gcd), (res_tuple[1] / gcd))

def get_model_min_max(model):
    x_min = np.min(model.vectors[:,:,0])
    x_max = np.max(model.vectors[:,:,0])
    y_min = np.min(model.vectors[:,:,1])
    y_max = np.max(model.vectors[:,:,1])
    z_min = np.min(model.vectors[:,:,2])
    z_max = np.max(model.vectors[:,:,2])

    return (x_min, x_max, y_min, y_max, z_min, z_max)

def determine_square_ortho(min_max_tuple):
    highest_coords = np.ceil(min_max_tuple[1::2])
    lowest_coords = np.floor(min_max_tuple[0::2])
    abs_max = np.maximum()
    
    xy_midpoint = (highest_coords[0:4] + lowest_coords[0:4]) / 2
    largest_dim = 0
    if xy_midpoint[0] > xy_midpoint[1]:
        largest_dim = xy_midpoint[0]
    else:
        largest_dim = xy_midpoint[1]

    return largest_dim

def bounding_box_circle(center, radius: float, target_res=0.1, margin=0):
    top = (math.floor(center[0]), math.ceil(center[1] + radius + margin))
    bottom = (math.floor(center[0]), math.floor(center[1] - radius - margin))
    left = (math.floor(center[0] - radius - margin), math.floor(center[1]))
    right = (math.ceil(center[0] + radius + margin), math.floor(center[1]))
    
    return (top, bottom, left, right)

def check_point_in_circle(circ_center, radius, pixel_coord):
    pythag = (pixel_coord[0] - circ_center[0])**2 + (pixel_coord[1] - circ_center[1])**2

    if pythag <= radius**2:
        return True
    else:
        return False
