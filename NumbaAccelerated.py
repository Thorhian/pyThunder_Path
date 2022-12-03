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
