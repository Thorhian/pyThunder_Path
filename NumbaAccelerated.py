import numpy as np
from numba import jit

@jit(nopython=True)
def search_link_points(link_points : np.ndarray, current_loc):
    '''
        Finds closest link point from shader image. Returns the X/Y coords
        of the closest link point. Returns array [-1, -1] if no link point is
        found
        '''
    bounds = np.array([link_points.shape[0], link_points.shape[1]])
    closest_point = np.array([-1, -1], dtype='f8')

    #Make default dist absurd for the math below, first dist should
    #should always be smaller. Removes check every loop iteration.
    current_distance = bounds[0] * bounds[1] * 1.2
    for i in range(bounds[0]):
        for j in range(bounds[1]):
            current_pix = link_points[i][j]
            is_link_loc = current_pix[3] > 250
            if not is_link_loc:
                continue

            new_dif = np.array([i, j], dtype='f8') - current_loc
            new_distance = np.hypot(new_dif[0], new_dif[1])
            if new_distance > current_distance:
                continue

            closest_point = np.array([i, j], dtype='f8')
            current_distance = new_distance

    return closest_point

@jit(nopython=True) #See: https://www.delftstack.com/howto/python/python-clamp/
def clamp(n, smallest, largest):
    return max(smallest, min(n, largest))

@jit(nopython=True)
def find_rectangle_points(center1, center2, radius):
    translated_cent1 = center1 - center2 #type: ignore
    translated_cent2 = center2 - center1 #type: ignore

    norm_rad1 = (translated_cent1 / np.linalg.norm(translated_cent1.astype('f4'))) * radius
    norm_rad2 = (translated_cent2 / np.linalg.norm(translated_cent2.astype('f4'))) * radius

    trans_point1 = np.array([norm_rad1[1], -norm_rad1[0]]) + center2 #type: ignore
    trans_point2 = np.array([-norm_rad1[1], norm_rad1[0]]) + center2 #type: ignore
    trans_point3 = np.array([norm_rad2[1], -norm_rad2[0]]) + center1 #type: ignore
    trans_point4 = np.array([-norm_rad2[1], norm_rad2[0]]) + center1 #type: ignore

    return np.vstack((trans_point1, trans_point2, trans_point3, trans_point4)).astype('f4')
    #return np.array([trans_point1, trans_point2, trans_point3, trans_point4], 
            #dtype=np.dtype('f4'))

@jit(nopython=True)
def sort_rectangle_verts(vertices):
    avg_center = np.array([0.0, 0.0])
    for vert in vertices:
        avg_center += vert

    avg_center = avg_center / 4

    offset_verts = vertices - avg_center
    polar_rotations = np.zeros(4)

    i = 0
    while i < 4:
        rotation = np.rad2deg(np.arctan2(offset_verts[i][1],
                                         offset_verts[i][0]))

        if rotation < 0:
            rotation = 360 + rotation

        polar_rotations[i] = rotation
        i += 1

    return np.argsort(polar_rotations).astype('i4')
