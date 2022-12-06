
from typing import Tuple
import Helper_Functions as hf
import moderngl
import numpy as np
from PIL import Image
import cv2
import sys

import NumbaAccelerated as na

MAX_ITERATION_SIZE = 1024

class ComputeWorker:
    '''
    A class to represent a worker process/thread. Should be able to take
    and image and 
    '''
    def __init__(self,
            pixel_res: float,
            target_images: Tuple[bytes, bytes],
            img_res,
            diameter,
            ):
        self.pixel_res = pixel_res
        self.ctx = moderngl.create_standalone_context()
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.image_res = img_res
        self.tool_diameter = diameter

        #Setup buffers and program/vao for stock island detection.
        self.image_vertices = np.array([
            -1, 1,
            -1, -1,
            1, 1,
            1, -1,
        ], dtype='f4')
        imageVerts_vbo = self.ctx.buffer(self.image_vertices)

        image_vertex_code = hf.load_shader("./shaders/image_shader.vert")
        island_gen_code = hf.load_shader("./shaders/islandGenerator.frag")
        self.island_gen_prog = self.ctx.program(
                vertex_shader=image_vertex_code,
                fragment_shader=island_gen_code
                )

        self.buffer_size = self.image_res[0] * self.image_res[1] * 4
        self.stock_buffer = self.ctx.texture(self.image_res, 4)
        self.initial_state = self.ctx.texture(self.image_res, 4)
        self.initial_state.write(target_images[0])
        self.stock_buffer.write(target_images[1])
        self.island_gen_prog['fullRender'] = 6
        self.initial_state.use(6)
        self.island_buffer = self.ctx.buffer(reserve=self.buffer_size)
        self.island_fbo = self.ctx.simple_framebuffer(self.image_res, components=4)

        self.island_gen_vao = self.ctx.vertex_array(self.island_gen_prog, [
            (imageVerts_vbo, '2f', 'in_position')
            ])

        self.generate_islands()

        target_buffer = self.classify_islands(target_images[0])

        self.island_buffer.release()

        ########################################################################
        # Setup cutting pixel counter compute shader                           #
        ########################################################################
        count_program = hf.load_shader("./shaders/count_colors.glsl")
        self.counter_compute: moderngl.ComputeShader = self.ctx.compute_shader(count_program)
        self.image_buffer = self.ctx.texture(self.image_res, 4)
        self.image_buffer.write(target_buffer)
        target_buffer.release()

        self.center_buff_size = (16 * MAX_ITERATION_SIZE)
        self.quad_verts_buff_size = (32 * MAX_ITERATION_SIZE)
        self.quad_indices_buff_size = (16 * MAX_ITERATION_SIZE)
        self.counter_results_size = (16 * MAX_ITERATION_SIZE)
        self.cutter_center_buff = self.ctx.buffer(reserve=self.center_buff_size, dynamic=True)
        self.quad_verts_buff = self.ctx.buffer(reserve=self.quad_verts_buff_size, dynamic=True)
        self.quad_indices_buff = self.ctx.buffer(reserve=self.quad_indices_buff_size, dynamic=True)
        self.counter_results = self.ctx.buffer(reserve=self.counter_results_size, dynamic=True)

        self.depthBuffer = self.ctx.depth_texture(self.image_res)
        self.image_buffer.bind_to_image(1)
        self.image_buffer.use(5)
        self.counter_compute['imageSlice'] = 1

        self.counter_results.bind_to_storage_buffer(1)
        self.cutter_center_buff.bind_to_storage_buffer(2)
        self.quad_verts_buff.bind_to_storage_buffer(3)
        self.quad_indices_buff.bind_to_storage_buffer(4)
        ########################################################################

        ########################################################################
        # Setup whole image color counting                                     #
        ########################################################################
        image_count_code = hf.load_shader("./shaders/count_image_total.glsl")
        self.mask_tex = self.ctx.texture(self.image_res, 1)
        self.mask_tex.use(7)
        self.image_counter_compute: moderngl.ComputeShader = self.ctx.compute_shader(image_count_code)
        self.image_counter_compute['imageSlice'] = 5
        self.image_counter_compute['mask'] = 7
        ########################################################################

        ########################################################################
        # Setup Link Location Program                                          #
        ########################################################################
        link_loc_finder = hf.load_shader("./shaders/find_link_locs.frag")
        self.link_finder_prog : moderngl.Program = self.ctx.program(
            vertex_shader=image_vertex_code,
            fragment_shader=link_loc_finder
        )
        self.link_finder_prog['imageSlice'] = 5
        self.link_finder_prog['mask'] = 7
        self.link_finder_prog['circleRadius'] = (self.tool_diameter / 2) / self.pixel_res
        self.link_finder_vao = self.ctx.vertex_array(self.link_finder_prog, 
            [
                (imageVerts_vbo, '2f', 'in_position')
            ])
        ########################################################################

        ########################################################################
        # Setup painter/cutter shader program and vao                          #
        ########################################################################
        paint_frag_code = hf.load_shader("./shaders/painter.frag")
        self.painter_prog = self.ctx.program(vertex_shader=image_vertex_code,
                fragment_shader=paint_frag_code)

        self.painter_prog['prev_render'] = 5

        self.painter_vao = self.ctx.vertex_array(self.painter_prog, [
            (imageVerts_vbo, '2f', 'in_position')
            ])

        self.cut_buffer = self.ctx.buffer(reserve=self.buffer_size)
        ########################################################################

    def generate_islands(self):
        '''
        Takes an additive slice and generates masks that represent each
        stock island. A list of the of the island masks is returned,
        containing the number representing the island, the size of the
        mask, and the mask itself.
        '''
        self.island_fbo.clear()
        self.island_fbo.use()
        self.island_gen_vao.render(moderngl.TRIANGLE_STRIP)
        self.island_fbo.read_into(self.island_buffer, components=4)

        island_data = np.frombuffer(self.island_buffer.read(), dtype='u1')
        island_data = np.reshape(island_data, (self.image_res[1], self.image_res[0], 4))
        self.color_fill = Image.fromarray(island_data, mode="RGBA")

        self.island_list = []

        no_alpha = cv2.cvtColor(island_data, cv2.COLOR_RGBA2RGB)
        img = no_alpha.copy()

        for color in range(1, 255):
            seeds = np.argwhere(img[:, :, 2] > 250) #type: ignore
            if seeds.size > 0:
                seed_coord = seeds[0]
                seed_coord = np.array([seed_coord[1], seed_coord[0]])
            else:
                break

            floodval = (0, color, 0)
            lower_range = np.array([0, color, 0])
            upper_range = np.array([0, color, 0])
            cv2.floodFill(img, None, seedPoint=seed_coord, newVal=floodval)
            mask = cv2.inRange(img, lower_range, upper_range)

            mask_size = sys.getsizeof(mask)
            self.island_list.append([color, mask_size, mask.copy()])

    def classify_islands(self, imageSlice):
        #Get Buffers/Render Target Ready
        inputMaskBuffer = self.ctx.buffer(reserve=self.island_list[0][1])
        sliceInputBuffer = self.ctx.buffer(reserve=self.buffer_size)
        sliceInputBuffer.write(imageSlice)
        slice = self.ctx.texture(self.image_res, 4)
        slice.write(sliceInputBuffer)
        current_mask = self.ctx.texture(self.image_res, 1)
        sliceOut = self.ctx.texture(self.image_res, 4)
        depthBuf = self.ctx.depth_texture(self.image_res)
        fbo = self.ctx.framebuffer([sliceOut], depthBuf)
        imageVBO = self.ctx.buffer(self.image_vertices)

        #Get Programs/VAOs ready
        imageVertexCode = hf.load_shader("./shaders/image_shader.vert")
        profileDetectionCode = hf.load_shader("./shaders/profile_detection.frag")
        profileSearchProgram = self.ctx.program(
            vertex_shader=imageVertexCode,
            fragment_shader=profileDetectionCode
        )
        profileSearchProgram['slice'] = 0
        profileSearchProgram['islandMask'] = 1
        #profileSearchProgram['outColor'] = 2
        profileSearchProgram['cutterRadius'] = self.tool_diameter / 2
        slice.use(location=0)
        current_mask.use(location=1)
        fbo.clear()
        fbo.use()

        profileDetectionVAO = self.ctx.vertex_array(
            profileSearchProgram,
            [ 
                (imageVBO, '2f', 'in_position')
            ])
        
        
        for island in self.island_list:
            inputMaskBuffer.write(island[2])
            current_mask.write(inputMaskBuffer)
            profileDetectionVAO.render(moderngl.TRIANGLE_STRIP)
            fbo.read_into(sliceInputBuffer, components=4)
            slice.write(sliceInputBuffer)

        

        #Release GPU Memory, Please
        inputMaskBuffer.release()
        slice.release()
        current_mask.release()
        sliceOut.release()
        fbo.release()
        imageVBO.release()

        return sliceInputBuffer

    def check_cuts(self, current_loc: np.ndarray,
                   direction: float,
                   tool_radius: float,
                   deg_inc: float,
                   iterations: int,
                   distance: float):
        '''
        Checks many different cuts based on an intial direction angle
        and how many cut iterations need to be tested, changing
        the direction of each iteration by the deg_inc parameter.
        Returns a list of the potential cut locations, what pixels
        are encountered in each of those cuts, and the direction
        that cut is going (in order).
        '''
        if iterations > MAX_ITERATION_SIZE:
            raise Exception(f"Iterations Count: {iterations}, cannot go above {MAX_ITERATION_SIZE}")

        if direction >= 360.0 or direction < 0.0:
            raise Exception(f"direction should be between 0 (inclusive) to 360 (exclusive), not {direction}")

        cut_vectors = na.prepare_test_cut_vectors(
            current_loc,
            direction,
            deg_inc,
            iterations,
            distance
        )
        cut_vectors = np.flip(cut_vectors)
        centers = na.generate_cut_count_centers(cut_vectors, np.flip(current_loc))
        quad_verts = na.generate_cut_count_rect_points(centers, tool_radius)
        quad_indices = na.generate_cut_count_rect_indices(quad_verts)
        tested_directions = np.arange(direction, direction + (deg_inc * iterations), deg_inc)
        tested_directions = np.mod(tested_directions, 360.0)

        self.counter_results.write(np.zeros((iterations, 4), dtype='u4'))
        self.cutter_center_buff.write(centers)
        self.quad_verts_buff.write(quad_verts)
        self.quad_indices_buff.write(quad_indices)
        self.counter_compute['tool_radius'] = tool_radius
        self.counter_compute['iterations'] = iterations
        self.counter_compute.run(group_x=self.image_res[0] // 8 + 1,
                                 group_y=self.image_res[1] // 8 + 1,
                                 group_z=iterations // 4 + 1)

        counter_results = np.frombuffer(self.counter_results.read(size=(16 * iterations)),
                                        dtype='u4')
        counter_results = counter_results.view().reshape((iterations, 4))

        return [cut_vectors, counter_results, tested_directions]

    def make_cut(self, center1, center2, radius):
        self.painter_prog['circleCenters'] = center1[0], center1[1], center2[0], center2[1]
        self.painter_prog['circleRadius'] = radius

        quadUniform = self.painter_prog['quadPoints']
        quadIUniform = self.painter_prog['quadIndices']
        
        quad: np.ndarray = na.find_rectangle_points(center1, center2, radius) #type: ignore
        sorted_quad_indices = na.sort_rectangle_verts(quad) #type: ignore
        quadUniform.write(quad.flatten()) #type: ignore
        quadIUniform.write(sorted_quad_indices) #type: ignore

        self.island_fbo.use()
        self.island_fbo.clear()
        self.painter_vao.render(moderngl.TRIANGLE_STRIP)

        self.island_fbo.read_into(self.cut_buffer, components=4, dtype='f1')
        self.image_buffer.write(self.cut_buffer)

    def count_pixels(self, counter_buffer, mask_buffer = False):
        if mask_buffer:
            self.image_counter_compute['useMask'] = True;
        else:
            self.image_counter_compute['useMask'] = False;

        counter_buffer.bind_to_storage_buffer(2)
        self.image_counter_compute.run(self.image_res[0] // 16 + 1, self.image_res[1] // 16 + 1)

    def find_link_locations(self, mask : moderngl.Buffer):
        self.mask_tex.write(mask)
        self.island_fbo.use()
        self.island_fbo.clear()
        self.link_finder_vao.render(moderngl.TRIANGLE_STRIP)

        link_locations = np.frombuffer(self.island_fbo.read(components=4, dtype='f1'), dtype='u1')
        link_locations = np.reshape(link_locations, (self.image_res[1], self.image_res[0], 4))
        return np.flip(link_locations, 0)

    def retrieve_image(self):
        image = np.frombuffer(self.image_buffer.read(), dtype='u1')
        image = np.reshape(image, (self.image_res[1], self.image_res[0], 4))
        image = np.flip(image, 0)
        return image

    def retrieve_islands(self):
        image = np.frombuffer(self.island_fbo.read(components=4, dtype='f1'), dtype='u1')
        image = np.reshape(image, (self.image_res[1], self.image_res[0], 4))
        image = np.flip(image, 0)
        return image

    def find_rectangle_points(self, center1, center2, radius):
        '''
        This function is now depracated. Use the Numba Accelerated
        version instead.
        '''
        print("find_rectangle_points in class ComputeWorker is Depracated")
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
        '''
        This function is now depracated. Use the Numba Accelerated
        version instead.
        '''
        print("sort_rectangle_verts in class ComputeWorker is Depracated")
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
