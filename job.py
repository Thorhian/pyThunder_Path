#!/usr/bin/env python3

import sys
import math
import numpy as np
from stl import mesh
import moderngl
import glm
from PIL import Image

import Helper_Functions as hf


class Job:
    '''
    A class to handle the setup of the rendering of a targetted object
    and generating tool paths when a generator is provided.
    '''

    def __init__(self, target_model, obstacles: list, tool_diam: float,
                 target_res: float = 0.1):
        self.target_model = target_model
        self.obstacles = obstacles
        self.tool_diam = tool_diam
        self.target_res = target_res
        self.bounds = self.calculate_bounds()
        self.img_res = self.calculate_resolution(self.bounds)
        print(self.img_res)
        self.ctx = moderngl.create_standalone_context()
        self.setup_opengl_objects()


    def calculate_bounds(self):
        '''
        Calculates the bounding box of the targetted model. Returns a
        tuple of (-x, x, -y, y, -z, z).
        '''
        rough_bounds = hf.get_model_min_max(self.target_model)
        lower_bounds_with_margin = np.floor(rough_bounds[0::2]) - math.ceil(self.tool_diam + 5)
        higher_bounds_with_margin = np.ceil(rough_bounds[1::2]) + math.ceil(self.tool_diam + 5)
        return (lower_bounds_with_margin[0], higher_bounds_with_margin[0],
                lower_bounds_with_margin[1], higher_bounds_with_margin[1],
                rough_bounds[4], rough_bounds[5])

    def calculate_resolution(self, bounds):
        '''
        Determines resolution of the images to be rendered.
        '''
        return (math.ceil((bounds[1] - bounds[0]) / self.target_res),
                math.ceil((bounds[3] - bounds[2]) / self.target_res))

    def setup_opengl_objects(self):
        '''
        Creates VBOs, Programs, VAOs, and FBOs for the job.
        '''

        self.ctx.enable(moderngl.DEPTH_TEST)
        model_vertex_shader = hf.load_shader("./v_shader.vert")
        model_frag_shader = hf.load_shader("./frag_shader.frag")

        self.model_render_prog = self.ctx.program(vertex_shader=model_vertex_shader,
                                             fragment_shader=model_frag_shader)

        image_vertex_shader = hf.load_shader("./image_shader.vert")
        edge_frag_shader = hf.load_shader("./image_shader.frag")

        edge_detection_prog = self.ctx.program(vertex_shader=image_vertex_shader,
                                               fragment_shader=edge_frag_shader)

        edge_expand_frag_shader = hf.load_shader("./edge_expand.frag")

        edge_expand_prog = self.ctx.program(vertex_shader=image_vertex_shader,
                                            fragment_shader=edge_expand_frag_shader)

        #Create Textures
        firstPass = self.ctx.texture(self.img_res, 4)
        firstPassDepth = self.ctx.depth_texture(self.img_res)
        secondPass = self.ctx.texture(self.img_res, 4)
        secondPassDepth = self.ctx.depth_texture(self.img_res)

        print(self.bounds[4], ',', self.bounds[5])

        self.projection_matrix = glm.ortho(
            self.bounds[0], self.bounds[1], self.bounds[2],
            self.bounds[3], -self.bounds[5], -self.bounds[4]
        )

        #Projection and View Matrices
        self.model_render_prog["projectionMatrix"].write(self.projection_matrix)
        self.model_render_prog["viewMatrix"].write(glm.rotate(glm.radians(0), glm.vec3(1.0, 0.0, 0.0)))

        #Get textures properly assigned to uniform samplers
        edge_detection_prog["prev_render"] = 4
        firstPass.use(location=4)
        edge_expand_prog["prev_render"] = 3
        secondPass.use(location=3)

        #Calculate cutter radius in pixels for edge expand algorithm
        edge_expand_prog["cutterRadius"] = (self.tool_diam / 2) / self.target_res

        #Get vertice and color data prepared
        model_size = self.target_model.vectors.size
        r = np.zeros(model_size)
        g = np.zeros(model_size)
        b = np.ones(model_size)
        model_colors = np.dstack([r, g, b])
        image_vertices = np.array([
            -1, 1,
            -1, -1,
            1, 1,
            1, -1,
        ], dtype='f4')
        model_verts = self.target_model.vectors.flatten().astype('f4').tobytes()
        self.vbo_model = self.ctx.buffer(model_verts)
        self.color_buffer = self.ctx.buffer(model_colors.astype('f4').tobytes())
        image_vbo = self.ctx.buffer(image_vertices)


        #Create Vertex Array Objects
        self.vao1 = self.ctx.vertex_array(self.model_render_prog, [
            (self.vbo_model, '3f', 'in_vert'),
            (self.color_buffer, '3f', 'in_color'),
        ])

        self.vao2 = self.ctx.vertex_array(edge_detection_prog, [
            (image_vbo, '2f', 'in_position'),
        ])

        self.vao3 = self.ctx.vertex_array(edge_expand_prog, [
            (image_vbo, '2f', 'in_position'),
        ])

        self.fbo1 = self.ctx.framebuffer([firstPass], firstPassDepth)
        self.fbo2 = self.ctx.framebuffer([secondPass], secondPassDepth)
        self.fbo3 = self.ctx.simple_framebuffer(self.img_res)
        self.fbo1.clear(0.0, 0.0, 0.0, 1.0)
        self.fbo2.clear(0.0, 0.0, 0.0, 1.0)
        self.fbo3.clear(0.0, 0.0, 0.0, 1.0)

    def render(self):
        self.fbo1.clear(0.0, 0.0, 0.0, 1.0)
        self.fbo1.use()
        self.vao1.render(moderngl.TRIANGLES)
        self.fbo2.clear(0.0, 0.0, 0.0, 1.0)
        self.fbo2.use()
        self.vao2.render(moderngl.TRIANGLE_STRIP)
        self.fbo3.clear(0.0, 0.0, 0.0, 1.0)
        self.fbo3.use()
        self.vao3.render(moderngl.TRIANGLE_STRIP)

    def change_ortho_matrix(self, new_depth):
        self.model_render_prog["projectionMatrix"].write(
            glm.ortho(self.bounds[0], self.bounds[1], self.bounds[2],
                      self.bounds[3], self.bounds[5], new_depth)
        )

        self.vao1 = self.ctx.vertex_array(self.model_render_prog, [
            (self.vbo_model, '3f', 'in_vert'),
            (self.color_buffer, '3f', 'in_color'),
        ])

    #def generate_slice_coords(self, depth_of_cut):
