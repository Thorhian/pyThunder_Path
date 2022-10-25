
from typing import Tuple
import Helper_Functions as hf
import moderngl
import numpy as np
from PIL import Image, ImageDraw
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
            img_res
            ):
        self.pixel_res = pixel_res
        self.ctx = moderngl.create_standalone_context()
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.image_res = img_res


        #Setup cutting pixel counter compute shader
        count_program = hf.load_shader("./shaders/count_colors.glsl")
        self.counter_compute: moderngl.ComputeShader = self.ctx.compute_shader(count_program)
        self.image_buffer = self.ctx.texture(self.image_res, 4)
        self.image_buffer.write(target_images[0])
        self.depthBuffer = self.ctx.depth_texture(self.image_res)
        self.image_buffer.bind_to_image(1)
        self.image_buffer.use(0)
        self.counter_compute['imageSlice'] = 1
        dtype = np.dtype('u4')
        uint_counters = np.array([0, 0, 0, 0,], dtype=dtype)
        self.uint_buffer = self.ctx.buffer(uint_counters)
        self.uint_buffer.bind_to_storage_buffer(1)

        #Setup painter/cutter shader program and vao
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
        self.painter_prog['prev_render'] = 0

        imageVerts_vbo = self.ctx.buffer(image_vertices)
        self.painter_vao = self.ctx.vertex_array(self.painter_prog, [
            (imageVerts_vbo, '2f', 'in_position')
            ])
        self.paintOut = self.ctx.texture(self.image_res, 4)
        self.paint_fbo = self.ctx.framebuffer([self.paintOut], self.depthBuffer)
        self.paint_fbo.clear(0.0, 0.0, 0.0, 0.0)

        #Setup buffers and program/vao for stock island detection.
        island_gen_code = hf.load_shader("./shaders/islandGenerator.frag")
        self.island_gen_prog = self.ctx.program(
                vertex_shader=image_vertex_code,
                fragment_shader=island_gen_code
                )

        buffer_size = self.image_res[0] * self.image_res[1] * 4
        self.stock_buffer = self.ctx.texture(self.image_res, 4)
        self.initial_state = self.ctx.texture(self.image_res, 4)
        self.initial_state.write(target_images[0])
        self.stock_buffer.write(target_images[1])
        print(self.island_gen_prog._members)
        self.island_gen_prog['fullRender'] = 0
        #self.island_gen_prog['stockOnlyRender'] = 1
        self.stock_buffer.use(2)
        self.initial_state.use(1)
        self.island_buffer = self.ctx.buffer(reserve=buffer_size)
        self.island_fbo = self.ctx.simple_framebuffer(self.image_res, components=4)

        self.island_gen_vao = self.ctx.vertex_array(self.island_gen_prog, [
            (imageVerts_vbo, '2f', 'in_position')
            ])

        self.generate_islands()

    def generate_islands(self):
        self.island_fbo.clear()
        self.island_fbo.use()
        self.island_gen_vao.render(moderngl.TRIANGLE_STRIP)
        self.island_fbo.read_into(self.island_buffer, components=4)

        island_data = np.frombuffer(self.island_buffer.read(), dtype='u1')
        island_data = np.reshape(island_data, (self.image_res[1], self.image_res[0], 4))
        self.color_fill = Image.fromarray(island_data, mode="RGBA")
        size = self.color_fill.size
        print(size)
        #for index in range(size[0] * size[1]):
        #    x = index % size[0]
        #    y = index // size[1]
        #    if self.color_fill.getpixel((x, y)) == (0, 0, 0, 255):
        #        ImageDraw.floodfill(self.color_fill, (x, y), (0, 100, 0, 255))

        self.island_list = []

        no_alpha = cv2.cvtColor(island_data, cv2.COLOR_RGBA2RGB)
        img = no_alpha.copy()
        #cv2.imshow("Image", no_alpha)
        #cv2.waitKey()
        for color in range(1, 255):
            print(img.flags)
            seeds = np.argwhere(img[:, :, 2] > 250)
            print(seeds.flags)
            if seeds.size > 0:
                seed_coord = seeds[0]
            else:
                print("gaben")
                break
                    
            floodval = (0, color, 0)
            lower_range = np.array([0, color, 0])
            upper_range = np.array([0, color, 0])
            print(img[seed_coord[0], seed_coord[1]])
            cv2.floodFill(img, None, seedPoint=seed_coord, newVal=floodval)
            print(img[seed_coord[0], seed_coord[1]])
            mask = cv2.inRange(img, lower_range, upper_range)
            print(seed_coord)
            cv2.imshow("image", img)
            cv2.waitKey()
            cv2.imshow("image", mask)
            cv2.waitKey()

            print(sys.getsizeof(no_alpha) / 1000000)
            print(sys.getsizeof(mask)/ 1000000)

        print(len(self.island_list))

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

        self.paint_fbo.clear()
        self.paint_fbo.use()
        self.painter_vao.render(moderngl.TRIANGLE_STRIP)
        self.ctx.finish()

        temp_buf = self.paintOut.read(alignment=4)
        self.image_buffer.write(temp_buf)

        self.paint_fbo.clear()
        self.paint_fbo.use()


    def retrieve_image(self):
        image = np.frombuffer(self.paint_fbo.read(components=4, dtype='f1'), dtype='u1')
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
