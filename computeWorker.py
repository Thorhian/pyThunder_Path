
from typing import Tuple
import Helper_Functions as hf
import moderngl
import numpy as np
from PIL import Image
import cv2
import sys

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
        print(f"Island Gen Program: {self.island_gen_prog._members}")
        self.island_gen_prog['fullRender'] = 6
        #self.island_gen_prog['stockOnlyRender'] = 1
        self.initial_state.use(6)
        self.island_buffer = self.ctx.buffer(reserve=self.buffer_size)
        self.island_fbo = self.ctx.simple_framebuffer(self.image_res, components=4)

        self.island_gen_vao = self.ctx.vertex_array(self.island_gen_prog, [
            (imageVerts_vbo, '2f', 'in_position')
            ])

        self.generate_islands()

        target_buffer = self.classify_islands(target_images[0])

        self.island_buffer.release()

        #Setup cutting pixel counter compute shader
        count_program = hf.load_shader("./shaders/count_colors.glsl")
        self.counter_compute: moderngl.ComputeShader = self.ctx.compute_shader(count_program)
        self.image_buffer = self.ctx.texture(self.image_res, 4)
        self.image_buffer.write(target_buffer)
        target_buffer.release()
        self.depthBuffer = self.ctx.depth_texture(self.image_res)
        self.image_buffer.bind_to_image(1)
        self.image_buffer.use(5)
        self.counter_compute['imageSlice'] = 1
        dtype = np.dtype('u4')
        uint_counters = np.array([0, 0, 0, 0,], dtype=dtype)
        self.uint_buffer = self.ctx.buffer(uint_counters)
        self.uint_buffer.bind_to_storage_buffer(1)

        #Setup painter/cutter shader program and vao
        paint_frag_code = hf.load_shader("./shaders/painter.frag")
        self.painter_prog = self.ctx.program(vertex_shader=image_vertex_code,
                fragment_shader=paint_frag_code)

        self.painter_prog['prev_render'] = 5

        self.painter_vao = self.ctx.vertex_array(self.painter_prog, [
            (imageVerts_vbo, '2f', 'in_position')
            ])

        self.cut_buffer = self.ctx.buffer(reserve=self.buffer_size)

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
        size = self.color_fill.size
        print(size)

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
        print(profileSearchProgram._members)
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

    def check_cut(self, center1, center2, radius):
        self.counter_compute['circleCenters'] = center1[0], center1[1], center2[0], center2[1]
        self.counter_compute['circleRadius'] = radius
        quadUniform = self.counter_compute['quadPoints']
        quadIUniform = self.counter_compute['quadIndices']
        
        quad: np.ndarray = self.find_rectangle_points(center1, center2, radius) #type: ignore
        sorted_quad_indices = self.sort_rectangle_verts(quad) #type: ignore
        quadUniform.write(quad.flatten()) #type: ignore
        quadIUniform.write(sorted_quad_indices) #type: ignore
    
        self.counter_compute.run(self.image_res[0] // 16 + 1, self.image_res[1] // 16 + 1)

        counters = np.frombuffer(self.uint_buffer.read(), dtype=np.dtype('u4'))
        dtype = np.dtype('u4')
        uint_counters = np.array([0, 0, 0, 0,], dtype=dtype)
        self.uint_buffer.write(uint_counters)
        print(counters)

    def make_cut(self, center1, center2, radius):
        self.painter_prog['circleCenters'] = center1[0], center1[1], center2[0], center2[1]
        self.painter_prog['circleRadius'] = radius

        quadUniform = self.painter_prog['quadPoints']
        quadIUniform = self.painter_prog['quadIndices']
        
        quad: np.ndarray = self.find_rectangle_points(center1, center2, radius) #type: ignore
        sorted_quad_indices = self.sort_rectangle_verts(quad) #type: ignore
        quadUniform.write(quad.flatten()) #type: ignore
        quadIUniform.write(sorted_quad_indices) #type: ignore

        self.island_fbo.use()
        self.island_fbo.clear()
        self.painter_vao.render(moderngl.TRIANGLE_STRIP)

        self.island_fbo.read_into(self.cut_buffer, components=4, dtype='f1')
        self.image_buffer.write(self.cut_buffer)



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
