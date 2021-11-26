import moderngl
import glm
import numpy as np

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
