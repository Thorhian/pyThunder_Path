
import Helper_Functions as hf
import moderngl
import numpy as np

class ComputeWorker:
    '''
    A class to represent a worker process/thread. Should be able to take
    and image and 
    '''
    def __init__(self,
            pixel_res: float,
            target_image: np.ndarray,
            ):
        self.pixel_res = pixel_res
        self.ctx = moderngl.create_standalone_context()
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.image_res = (target_image.shape[0], target_image.shape[1])



        count_program = hf.load_shader("./shaders/count_colors.glsl")
        self.counter_compute: moderngl.ComputeShader = self.ctx.compute_shader(count_program)
        self.counter_compute['imageSize'] = self.image_res[0], self.image_res[1]
        self.image_buffer = self.ctx.texture(self.image_res, 4)
        self.image_buffer.write(target_image)
        self.image_buffer.bind_to_image(1)
        self.counter_compute['imageSlice'] = 1
        dtype = np.dtype('u4')
        uint_counters = np.array([0, 0, 0], dtype=dtype)
        self.uint_buffer = self.ctx.buffer(uint_counters)
        self.uint_buffer.bind_to_storage_buffer(1)


        image_vertex_code = hf.load_shader("./shaders/image_shader.vert")
        paint_frag_code = hf.load_shader("./shaders/painter.frag")
        self.painter_prog = self.ctx.program(vertex_shader=image_vertex_code,
                fragment_shader=paint_frag_code)

        
        image_vertices = np.array([
            -1, 1,
            -1, -1,
            1, 1,
            1, -1,
        ], dtype='f4')
        imageVerts_vbo = self.ctx.buffer(image_vertices)
        self.painter_vao = self.ctx.vertex_array(self.painter_prog, [
            (imageVerts_vbo, '2f', 'in_position')
            ])


    def check_cut(self, center1, center2, radius):
        self.counter_compute['circleCenters'] = center1[0], center1[1], center2[0], center2[1]
        self.counter_compute['circleRadius'] = radius
        quadUniform = self.counter_compute['quadPoints']
        quadIUniform = self.counter_compute['quadIndices']
        
        quad: np.ndarray = self.find_rectangle_points(center1, center2, radius)
        sorted_quad_indices = self.sort_rectangle_verts(quad)
        quadUniform.write(quad) #type: ignore
        quadIUniform.write(sorted_quad_indices) #type: ignore
    


    def find_rectangle_points(self, center1, center2, radius):
        translated_cent1 = np.array(center1) - np.array(center2) #type: ignore
        translated_cent2 = np.array(center2) - np.array(center1) #type: ignore

        norm_rad1 = (translated_cent1 / np.linalg.norm(translated_cent1)) * radius
        norm_rad2 = (translated_cent2 / np.linalg.norm(translated_cent2)) * radius

        trans_point1 = (norm_rad1[1], -norm_rad1[0]) + np.array(center2) #type: ignore
        trans_point2 = (-norm_rad1[1], norm_rad1[0]) + np.array(center2) #type: ignore
        trans_point3 = (norm_rad2[1], -norm_rad2[0]) + np.array(center1) #type: ignore
        trans_point4 = (-norm_rad2[1], norm_rad2[0]) + np.array(center1) #type: ignore

        return np.array([trans_point1, trans_point2, trans_point3, trans_point4], 
                dtype=np.dtype('f4'))

    def sort_rectangle_verts(self, vertices):
        avg_center = np.add.reduce(vertices) / 4

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
