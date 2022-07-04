#!/usr/bin/env python3

import numpy as np

def generate_helix(iterations, depth, diameter):
    '''
    Generates a series of lines forming a helix.
    '''
    z = np.linspace(0, depth, iterations)
    x = diameter * np.cos(z)
    y = diameter * np.sin(z)
    w = np.ones(iterations)

    return np.dstack([x, y, z, w])

def generate_box(dims: tuple):
    '''
    Generates a box to use for stock
    Expects tuple to be in this format: (-x, x, -y, y, -z, z)
    '''
    return np.array(
        [
            # Left face
            [
                [dims[0], dims[2], dims[4]],
                [dims[0], dims[3], dims[4]],
                [dims[0], dims[3], dims[5]],
            ],
            [
                [dims[0], dims[2], dims[4]],
                [dims[0], dims[2], dims[5]],
                [dims[0], dims[3], dims[5]],
            ],
            # Z bottom face
            [
                [dims[0], dims[2], dims[4]],
                [dims[0], dims[3], dims[4]],
                [dims[1], dims[2], dims[4]],
            ],
            [
                [dims[0], dims[3], dims[4]],
                [dims[1], dims[2], dims[4]],
                [dims[1], dims[3], dims[4]],
            ],
            # Z top face
            [
                [dims[0], dims[2], dims[5]],
                [dims[0], dims[3], dims[5]],
                [dims[1], dims[2], dims[5]],
            ],
            [
                [dims[0], dims[3], dims[5]],
                [dims[1], dims[2], dims[5]],
                [dims[1], dims[3], dims[5]],
            ],
            # Y top face
            [
                [dims[0], dims[3], dims[4]],
                [dims[0], dims[3], dims[5]],
                [dims[1], dims[3], dims[4]],
            ],
            [
                [dims[0], dims[3], dims[5]],
                [dims[1], dims[3], dims[5]],
                [dims[1], dims[3], dims[4]],
            ],
            # Y bottom face
            [
                [dims[0], dims[4], dims[4]],
                [dims[0], dims[4], dims[5]],
                [dims[1], dims[4], dims[4]],
            ],
            [
                [dims[0], dims[4], dims[5]],
                [dims[1], dims[4], dims[5]],
                [dims[1], dims[4], dims[4]],
            ],
            # X right face
            [
                [dims[1], dims[2], dims[4]],
                [dims[1], dims[3], dims[4]],
                [dims[1], dims[3], dims[5]],
            ],
            [
                [dims[1], dims[2], dims[4]],
                [dims[1], dims[2], dims[5]],
                [dims[1], dims[3], dims[5]],
            ],
        ]
    )
