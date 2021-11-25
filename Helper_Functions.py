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
