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

class Job:
    '''
    A class to handle the setup of the rendering of a targetted object
    and generating tool paths when a generator is provided.
    '''

    def __init__(self, target_model, stock_model, obstacles: list,
                 tool_diam: float, target_res: float = 0.1):
        self.target_model = target_model
        self.stock_model = stock_model
        self.obstacles = obstacles
        self.tool_diam = tool_diam
        self.target_res = target_res
        self.ctx = moderngl.create_standalone_context()
        self.bounds = self.calculate_bounds()
        self.img_res = self.calculate_resolution(self.bounds)
        print(self.img_res)
        self.setup_opengl_objects()
        self.d_model = DiscretizedModel(target_res)


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
        print(f"Maximum Resolution: {max_res}")
        if res[0] > max_res or res[1] > max_res: #type: ignore
            raise Exception("Resolution is too high for GPU", res)

        return res

    def setup_opengl_objects(self):
        '''
        Creates VBOs, Programs, VAOs, and FBOs for the job.
        '''

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
        firstPass = self.ctx.texture(self.img_res, 4)
        stockPassDepth = self.ctx.depth_texture(self.img_res)
        firstPassDepth = self.ctx.depth_texture(self.img_res)
        secondPass = self.ctx.texture(self.img_res, 4)
        secondPassDepth = self.ctx.depth_texture(self.img_res)
        thirdPass = self.ctx.texture(self.img_res, 4)
        thirdPassDepth = self.ctx.depth_texture(self.img_res)

        print(self.bounds[4], ',', self.bounds[5])

        self.projection_matrix = glm.ortho(
            self.bounds[0], self.bounds[1], self.bounds[2],
            self.bounds[3], -self.bounds[5], -self.bounds[5]
        )

        #Projection and View Matrices
        self.model_render_prog["projectionMatrix"].write(self.projection_matrix) #type: ignore
        self.model_render_prog["viewMatrix"].write(glm.rotate(glm.radians(0), glm.vec3(1.0, 0.0, 0.0))) #type: ignore

        #Get textures properly assigned to uniform samplers
        edge_detection_prog["prev_render"] = 4
        firstPass.use(location=4)
        edge_expand_prog["prev_render"] = 3
        secondPass.use(location=3)

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
        print(model_colors, stock_colors.shape)
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

        self.fbo_stock = self.ctx.framebuffer([firstPass], stockPassDepth)
        self.fbo1 = self.ctx.framebuffer([firstPass], firstPassDepth)
        self.fbo2 = self.ctx.framebuffer([secondPass], secondPassDepth)
        self.fbo3 = self.ctx.framebuffer([thirdPass], thirdPassDepth)
        self.fbo1.clear(0.0, 0.0, 0.0, 0.0)
        self.fbo2.clear(0.0, 0.0, 0.0, 0.0)
        self.fbo3.clear(0.0, 0.0, 0.0, 0.0)

    def render(self):
        self.fbo_stock.clear()
        self.fbo_stock.use()
        self.vao_stock.render(moderngl.TRIANGLES)
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
            print(f"Render depth: {current_depth}")
            self.render()
            image = np.frombuffer(self.fbo3.read(components=4, dtype='f1'),
                                  dtype='u1')
            image = np.reshape(image, (self.img_res[1], self.img_res[0], 4))
            image = np.flip(image, 0)
            self.d_model.add_layer(image,current_depth)

        if current_depth != model_depth:
            print(f"Render depth: {model_depth}")
            self.change_ortho_matrix(model_depth)
            self.render()
            image = np.frombuffer(self.fbo3.read(components=4, dtype='f1'),
                                  dtype='u1')
            image = np.reshape(image, (self.img_res[1], self.img_res[0], 4))
            image = np.flip(image, 0)
            self.d_model.add_layer(image,current_depth)

    def save_images(self):
        if not os.path.exists("renders"):
            os.makedirs("renders")

        counter = 0
        for render in self.d_model.images:
            print(f"Saving image {counter}")
            image = Image.fromarray(render)
            image.save(f"./renders/layer{counter}.png")
            counter += 1

    def generate_paths(self):
        if len(self.d_model.images) < 1:
            print("No images loaded in discrete model.")
            return -1;

        shape = self.d_model.images[0].shape
        image_center = (shape[0] / 2, shape[1] / 2)

        image_count = len(self.d_model.images)
        for indice in range(image_count):
            print(f"Indice: {indice}")
            self.d_model.cut_circle(image_center, self.tool_diam / 2, indice)
        return 0;
