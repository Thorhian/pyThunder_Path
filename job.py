#!/usr/bin/env python3

import sys
import math
import numpy as np
from stl import mesh
import moderngl
import glm
import os
from PIL import Image

import Helper_Functions as hf
from Discretized_Model import DiscretizedModel
from computeWorker import ComputeWorker

sys.path.insert(0, sys.path[0] + '/renderdoc_ctypes')
from renderdoc_api import RenderDocAPI

class Job:
    '''
    A class to handle the setup of the rendering of a targetted object
    and generating tool paths when a generator is provided.
    '''

    def __init__(self, target_model, stock_model, obstacles: list,
                 tool_diam: float, target_res: float = 0.1, debug = False):
        self.target_model = target_model
        self.stock_model = stock_model
        self.obstacles = obstacles
        self.tool_diam = tool_diam
        self.target_res = target_res
        self.debug = debug
        self.ctx = moderngl.create_standalone_context()
        self.bounds = self.calculate_bounds()
        self.img_res = self.calculate_resolution(self.bounds)
        
        if self.debug:
            self.api = RenderDocAPI()

        self.setup_opengl_objects()
        self.d_model = DiscretizedModel(target_res)

        self.degree_inc = 2
        self.pixelSize = 1 * self.target_res
        #print(f"Image Bounds: {self.bounds}mm")
        print(f"Image Resolution: {self.img_res}")
        print(f"Target Resolution Modifier: {self.target_res}")
        print(f"Pixel Height/Width: {self.pixelSize}mm")


    def __del__(self):
        self.firstPass.release()
        self.firstPassDepth.release()
        self.secondPass.release()
        self.secondPassDepth.release()
        self.thirdPass.release()
        self.thirdPassDepth.release()
        self.vbo_model.release()
        self.vbo_stock.release()
        self.color_buffer.release()
        self.color_stock.release()
        self.vao1.release()
        self.vao2.release()
        self.vao3.release()
        if self.debug:
            self.api.stop_capture()

    def calculate_bounds(self):
        '''
        Calculates the bounding box of the targetted model. Returns a
        tuple of (-x, x, -y, y, -z, z).
        '''
        rough_bounds = hf.get_model_min_max(self.stock_model)
        lower_bounds_with_margin = np.floor(rough_bounds[0::2]) - math.ceil(self.tool_diam + 5)
        higher_bounds_with_margin = np.ceil(rough_bounds[1::2]) + math.ceil(self.tool_diam + 5)
        return (lower_bounds_with_margin[0], higher_bounds_with_margin[0],
                lower_bounds_with_margin[1], higher_bounds_with_margin[1],
                rough_bounds[4], rough_bounds[5])

    def calculate_resolution(self, bounds):
        '''
        Determines resolution of the images to be rendered.
        '''
        res = (math.ceil((bounds[1] - bounds[0]) / self.target_res),
               math.ceil((bounds[3] - bounds[2]) / self.target_res))
        max_res = self.ctx.info["GL_MAX_TEXTURE_SIZE"]
        if res[0] > max_res or res[1] > max_res: #type: ignore
            raise Exception("Resolution is too high for GPU", res)

        return res

    def setup_opengl_objects(self):
        '''
        Creates VBOs, Programs, VAOs, and FBOs for the job.
        '''

        if self.debug:
            self.api.start_capture()
        
        GL_RGBA2 = 0x8055

        self.ctx.enable(moderngl.DEPTH_TEST)
        model_vertex_shader = hf.load_shader("./shaders/v_shader.vert")
        model_frag_shader = hf.load_shader("./shaders/frag_shader.frag")

        self.model_render_prog : moderngl.Program = self.ctx.program(vertex_shader=model_vertex_shader,
                                                                     fragment_shader=model_frag_shader)

        image_vertex_shader = hf.load_shader("./shaders/image_shader.vert")
        edge_frag_shader = hf.load_shader("./shaders/image_shader.frag")

        edge_detection_prog = self.ctx.program(vertex_shader=image_vertex_shader,
                                               fragment_shader=edge_frag_shader)

        edge_expand_frag_shader = hf.load_shader("./shaders/edge_expand.frag")

        edge_expand_prog = self.ctx.program(vertex_shader=image_vertex_shader,
                                            fragment_shader=edge_expand_frag_shader)

        #Create Textures
        self.firstPass = self.ctx.texture(self.img_res, 4)
        stockPassDepth = self.ctx.depth_texture(self.img_res)
        self.firstPassDepth = self.ctx.depth_texture(self.img_res)
        self.secondPass = self.ctx.texture(self.img_res, 4)
        self.secondPassDepth = self.ctx.depth_texture(self.img_res)
        self.thirdPass = self.ctx.texture(self.img_res, 4, dtype='f1', internal_format=GL_RGBA2)
        self.thirdPassDepth = self.ctx.depth_texture(self.img_res)

        #print(self.bounds[4], ',', self.bounds[5])

        self.projection_matrix = glm.ortho(
            self.bounds[0], self.bounds[1], self.bounds[2],
            self.bounds[3], -self.bounds[5], -self.bounds[5]
        )

        #Projection and View Matrices
        self.model_render_prog["projectionMatrix"].write(self.projection_matrix) #type: ignore
        self.model_render_prog["viewMatrix"].write(glm.rotate(glm.radians(0), glm.vec3(1.0, 0.0, 0.0))) #type: ignore

        #Get textures properly assigned to uniform samplers
        edge_detection_prog["prev_render"] = 4
        self.firstPass.use(location=4)
        edge_expand_prog["prev_render"] = 3
        self.secondPass.use(location=3)

        #Calculate cutter radius in pixels for edge expand algorithm
        edge_expand_prog["cutterRadius"] = (self.tool_diam / 2) / self.target_res


        #Get vertice and color data prepared
        model_size = self.target_model.vectors.size
        stock_size = self.stock_model.vectors.size
        r = np.zeros(model_size)
        g = np.zeros(model_size)
        b = np.ones(model_size)
        a = np.ones(model_size)
        model_colors = np.dstack([r, g, b, a]).flatten().astype('f4')
        rStock = np.zeros(stock_size)
        gStock = np.zeros(stock_size)
        bStock = np.zeros(stock_size)
        aStock = np.ones(stock_size)
        stock_colors = np.dstack([rStock, gStock, bStock, aStock]).flatten().astype('f4')
        image_vertices = np.array([
            -1, 1,
            -1, -1,
            1, 1,
            1, -1,
        ], dtype='f4')
        model_verts = self.target_model.vectors.flatten().astype('f4')
        stock_verts = self.stock_model.vectors.flatten().astype('f4')
        #rendered_verts = np.concatenate((model_verts, stock_verts)).astype('f4')
        #all_colors = np.concatenate((model_colors.flatten(), stock_colors.flatten())).astype('f4')

        self.vbo_model = self.ctx.buffer(model_verts)
        self.color_buffer = self.ctx.buffer(model_colors)
        self.vbo_stock = self.ctx.buffer(stock_verts)
        self.color_stock = self.ctx.buffer(stock_colors)
        image_vbo = self.ctx.buffer(image_vertices)

        self.vao_stock = self.ctx.vertex_array(self.model_render_prog, [
            (self.vbo_stock, '3f', 'in_vert'),
            (self.color_stock, '4f', 'in_color'),
        ])

        #Create Vertex Array Objects
        self.vao1 = self.ctx.vertex_array(self.model_render_prog, [
            (self.vbo_model, '3f', 'in_vert'),
            (self.color_buffer, '4f', 'in_color'),
        ])

        self.vao2 = self.ctx.vertex_array(edge_detection_prog, [
            (image_vbo, '2f', 'in_position'),
        ])

        self.vao3 = self.ctx.vertex_array(edge_expand_prog, [
            (image_vbo, '2f', 'in_position'),
        ])

        buffer_size = self.img_res[0] * self.img_res[1] * 4
        self.stock_only_buffer = self.ctx.buffer(reserve=buffer_size)
        self.fbo_stock = self.ctx.framebuffer([self.firstPass], stockPassDepth)
        self.fbo1 = self.ctx.framebuffer([self.firstPass], self.firstPassDepth)
        self.fbo2 = self.ctx.framebuffer([self.secondPass], self.secondPassDepth)
        self.fbo3 = self.ctx.framebuffer([self.thirdPass], self.thirdPassDepth)
        self.fbo1.clear(0.0, 0.0, 0.0, 0.0)
        self.fbo2.clear(0.0, 0.0, 0.0, 0.0)
        self.fbo3.clear(0.0, 0.0, 0.0, 0.0)

    def render(self):
        self.fbo_stock.clear()
        self.fbo_stock.use()
        self.vao_stock.render(moderngl.TRIANGLES)
        self.fbo_stock.read_into(self.stock_only_buffer, components=4, dtype='f1')
        self.fbo1.use()
        self.vao1.render(moderngl.TRIANGLES)
        self.fbo2.clear(0.0, 0.0, 0.0, 0.0)
        self.fbo2.use()
        self.vao2.render(moderngl.TRIANGLE_STRIP)
        self.fbo3.clear(0.0, 0.0, 0.0, 0.0)
        self.fbo3.use()
        self.vao3.render(moderngl.TRIANGLE_STRIP)
        self.ctx.finish()

    def change_ortho_matrix(self, new_depth):
        self.model_render_prog["projectionMatrix"].write( #type: ignore
            glm.ortho(
                self.bounds[0], self.bounds[1], self.bounds[2],
                self.bounds[3], -self.bounds[5] - 1, -self.bounds[5] + new_depth
            )
        )

        self.vao1 = self.ctx.vertex_array(self.model_render_prog, [
            (self.vbo_model, '3f', 'in_vert'),
            (self.color_buffer, '4f', 'in_color'),
        ])

    def render_layers(self, depth_of_cut):
        '''
        Renders the different \'additive slices\' of the model according
        to a given depth of cut. Stops at the bottom of the model.
        TODO: Make more flexible by supplying desired final depth.
        '''
        current_depth = 0.0
        model_depth = np.abs(self.bounds[5] - self.bounds[4])
        print(f"Model Depth:{model_depth}")

        while current_depth <= model_depth:
            current_depth += depth_of_cut
            if np.abs(current_depth - model_depth) < 0.05:
                current_depth = model_depth

            if current_depth > model_depth:
                break

            self.change_ortho_matrix(current_depth)
            self.render()
            result_image = self.fbo3.read(components=4, dtype='f1')
            stock_only = self.stock_only_buffer.read()
            self.d_model.add_layer((result_image, stock_only), current_depth)

        if current_depth != model_depth:
            self.change_ortho_matrix(model_depth)
            self.render()
            result_image = self.fbo3.read(components=4, dtype='f1')
            stock_only = self.stock_only_buffer.read()
            self.d_model.add_layer((result_image, stock_only), current_depth)

    def save_images(self):
        if not os.path.exists("renders"):
            os.makedirs("renders")

        counter = 0
        for render in self.d_model.images:
            image = np.frombuffer(render[0], dtype='u1')
            image = np.reshape(image, (self.img_res[1], self.img_res[0], 4))
            image = np.flip(image, 0)
            image = Image.fromarray(image)
            image.save(f"./renders/layer{counter}.png")
            counter += 1

    def checkCuts(self, cw : ComputeWorker,
                 coords : np.ndarray,
                 direction : float,
                 tool_rad: float,
                 deg_inc: float,
                 iterations: int,
                 distance: float,
                 clockwiseScan = True):
        '''
        Runs the cut counter compute shader from the given compute worker
        multiple times, incrememting the the angle of attack multiple
        times in order to return multiple possible cut results. It can
        scan in a clockwise direction (the default) or counter clockwise.
        Must be provided with the current endmill center coordinates
        and the current direction the end mill is going.

        Degree increment determines how far each iterations is rotated
        in the determined direction (clockwise or ccw).
        '''

        if direction >= 360.0 or direction < 0.0:
            raise Exception(f"direction should be between 0 (inclusive) to 360 (exclusive), not {direction}")

        scan_direction = -1
        if clockwiseScan == False:
            scan_direction = 1
            
        movement_vector = np.array([0, distance])
        theta = np.radians(direction)
        theta_inc = np.radians(direction + deg_inc * scan_direction)
        c, s = np.cos(theta), np.sin(theta)
        c_inc, s_inc = np.cos(theta_inc), np.sin(theta_inc)

        initial_rot = np.array(((c, -s), (s, c)))
        scan_rot_v = np.array(((c_inc, -s_inc), (s_inc, c_inc)))

        test_vectors = np.array([np.dot(initial_rot, movement_vector)])
        for i in range(iterations - 1):
            increment = np.array(np.dot(scan_rot_v, test_vectors[-1]))
            test_vectors = np.append(test_vectors, [increment], axis=0)
            
        test_vectors = test_vectors + coords
        cut_stats = []
        for i in range(iterations):
            cut_stats.append(cw.check_cut(np.flip(coords), np.flip(test_vectors[i]), tool_rad))

        return [test_vectors, np.array(cut_stats)]

    def generate_paths(self):
        if len(self.d_model.images) < 1:
            print("No images loaded in discrete model.")
            return -1

        image_count = len(self.d_model.images)
        img_center = np.array([self.img_res[0] / 2, self.img_res[1] / 2])
        offset = np.array([0, 100])
        bore_coord = img_center + offset
        tool_radius = self.tool_diam / 2 / self.target_res
        worker: ComputeWorker = ComputeWorker(self.target_res, self.d_model.images[image_count - 1], self.img_res, self.tool_diam)

        print(f"Image Center: {img_center}")
        worker.make_cut(np.flip(bore_coord), np.flip(bore_coord) + 0.1, (self.tool_diam * 1.5) / self.target_res)
        self.ctx.finish()
        distance = 10
        distance_adjusted = distance / self.target_res
        print(f"Distance of cut checking: {distance}mm")
        candidates = self.checkCuts(worker, bore_coord,
                                    direction=0, 
                                    tool_rad=tool_radius,
                                    deg_inc=20,
                                    iterations=8,
                                    distance=distance_adjusted)

        print(f"Candidate Cuts:\n{'Model Obstacle  Stock  Total' : >32}\n {candidates[1]}")

        image = Image.fromarray(worker.retrieve_image())
        image.save(f"./renders/testBore.png")

        for i, candidate in enumerate(candidates[1][:, :]):
            print(f"Candidate {i}: {candidate}")
            if candidate[0] < 1 and candidate[1] < 1:
                ratio = candidate[2] / candidate[3]
                if ratio < 0.2:
                    dest = candidates[0][i]
                    worker.make_cut(np.flip(bore_coord), np.flip(dest), tool_radius)
                    break
                else:
                    print(f"Candidate {i} Ratio is too high")
            else:
                print(f"Candidate {i} contains model/obstacle material")

        image = Image.fromarray(worker.retrieve_image())
        image.save(f"./renders/testCut.png")

        return 0
