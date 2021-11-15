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
