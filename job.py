#!/usr/bin/env python3

import sys
import math
import numpy as np
import moderngl
import glm
import os
from PIL import Image

import Helper_Functions as hf
import NumbaAccelerated as na
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
        model_size = self.target_model.size
        stock_size = self.stock_model.size
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
        model_verts = self.target_model.flatten().astype('f4')
        stock_verts = self.stock_model.flatten().astype('f4')
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
            image.save(f"./renders/layer{counter:04d}.png")
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

        scan_direction = 1
        if clockwiseScan == True:
            scan_direction = -1
            
        movement_vector = np.array([1, 0])
        theta = np.radians((direction) % 360.0)
        theta_inc = np.radians((deg_inc * scan_direction) % 360.0)
        c, s = np.cos(theta), np.sin(theta)
        c_inc, s_inc = np.cos(theta_inc), np.sin(theta_inc)

        initial_rot = np.array(((c, -s), (s, c)))
        scan_rot_v = np.array(((c_inc, -s_inc), (s_inc, c_inc)))

        test_vectors = np.array([np.dot(initial_rot, movement_vector)])
        for i in range(iterations - 1):
            increment = np.array(np.dot(scan_rot_v, test_vectors[-1]))
            test_vectors = np.append(test_vectors, [increment], axis=0)
            
        test_vectors = test_vectors * distance
        test_vectors = test_vectors + coords
        cut_stats = []
        for i in range(iterations):
            cut_stats.append(cw.check_cut(np.flip(coords), np.flip(test_vectors[i]), tool_rad))

        tested_directions = np.arange(direction, direction + (deg_inc * iterations), (deg_inc * scan_direction))
        tested_directions = np.mod(tested_directions, 360.0)
        return [test_vectors, np.array(cut_stats), tested_directions]

    def check_image(self, worker):
        dtype = np.dtype('u4')
        uint_counters = np.array([0, 0, 0, 0, 0], dtype=dtype)
        counter_buffer = self.ctx.buffer(uint_counters, dynamic=True)
        worker.count_pixels(counter_buffer)
        count = np.frombuffer(counter_buffer.read(), dtype=np.dtype('u4'))
        counter_buffer.release()

        return count

    def check_image_masked(self, worker, mask):
        dtype = np.dtype('u4')
        uint_counters = np.array([0, 0, 0, 0, 0], dtype=dtype)
        counter_buffer = self.ctx.buffer(uint_counters, dynamic=True)
        worker.mask_tex.write(mask)
        worker.count_pixels(counter_buffer, mask_buffer=True)
        count = np.frombuffer(counter_buffer.read(), dtype=np.dtype('u4'))
        counter_buffer.release()

        return count

    def cutting_move(self, worker, startLoc, start_dir = 0.0, dist_inc = 2.0,
                     material_removal_ratio = 0.2):
        distance = dist_inc
        distance_adjusted = distance / self.target_res

        tool_radius = self.tool_diam / 2 / self.target_res
        current_direction = start_dir
        materialRemovalRatio = material_removal_ratio
        currentLoc = startLoc
        locations = np.array([currentLoc * self.target_res])
        emptyCounter = 0
        easing_factor = 12
        lower_bound_per = 0.85
        for i in range(20000):
            if currentLoc[0] < 0 or currentLoc[0] > self.img_res[0]:
                print("Outside X Image Bounds")
                break
            if currentLoc[1] < 0 or currentLoc[1] > self.img_res[1]:
                print("Outside Y Image Bounds")
                break

            image = Image.fromarray(worker.retrieve_image())
            image.save(f"./renders/testCut{i:08d}.png")

            #if i % 1000 == 0:
            #print(f"Iteration: {i}")

            candidates = self.checkCuts(worker, currentLoc,
                                        direction=current_direction,
                                        tool_rad=tool_radius,
                                        deg_inc=0.5,
                                        iterations=280,
                                        distance=distance_adjusted,
                                        clockwiseScan=False)

            madeCut = False
            easing_iteration = i
            for i, candidate in enumerate(candidates[1][:, :]):
                if candidate[0] < 1 and candidate[1] < 1:
                    ratio = 0.0
                    if candidate[3] < 1: #If no empty space, ratio is 1.0
                        ratio = 1.0
                    else:
                        ratio = candidate[2] / candidate[3]
                    lower_bound = (material_removal_ratio * lower_bound_per)
                    low_bound_mod = (easing_iteration + 0.1) / easing_factor
                    lower_bound = lower_bound * na.clamp(low_bound_mod, 0.05, 1.0)
                    if ratio < materialRemovalRatio and ratio > lower_bound:
                        new_loc = candidates[0][i]
                        worker.make_cut(np.flip(currentLoc), np.flip(new_loc), tool_radius)
                        current_direction = candidates[2][i]
                        currentLoc = new_loc
                        madeCut = True
                        locations = np.append(locations, [currentLoc * self.target_res], axis=0)
                        if ratio < 0.01:
                            emptyCounter += 1
                        break

            if not madeCut:
                candidates = self.checkCuts(worker, currentLoc,
                                            direction=current_direction,
                                            tool_rad=tool_radius,
                                            deg_inc=-0.5,
                                            iterations=250,
                                            distance=distance_adjusted,
                                            clockwiseScan=False)

                for i, candidate in enumerate(candidates[1][:, :]):
                    #print(f"Candidate {i}: {candidate}")
                    if candidate[0] < 1 and candidate[1] < 1:
                        ratio = 0.0
                        if candidate[3] < 1: #If no empty space, ratio is 1.0
                            ratio = 1.0
                        else:
                            ratio = candidate[2] / candidate[3]
                        lower_bound = (material_removal_ratio * lower_bound_per)
                        low_bound_mod = (easing_iteration + 0.1) / easing_factor
                        lower_bound = lower_bound * na.clamp(low_bound_mod, 0.05, 1.0)
                        if ratio < materialRemovalRatio and ratio > lower_bound:
                            new_loc = candidates[0][i]
                            worker.make_cut(np.flip(currentLoc), np.flip(new_loc), tool_radius)
                            current_direction = candidates[2][i]
                            currentLoc = new_loc
                            madeCut = True
                            locations = np.append(locations, [currentLoc * self.target_res], axis=0)
                            if ratio < 0.01:
                                emptyCounter += 1
                            break

                if not madeCut:
                    #print("Failed to find valid cutting move.")
                    break

        return locations, current_direction


    def generate_paths(self, dist_inc = 2.0, material_removal_ratio = 0.2):
        if len(self.d_model.images) < 1:
            print("No images loaded in discrete model.")
            return -1

        image_count = len(self.d_model.images)
        image = self.d_model.images[image_count - 2]

        locations = []
        locations.append(self.process_layer(image, dist_inc, material_removal_ratio))


        return locations



    def process_layer(self, image, dist_inc = 2.0, material_removal_ratio = 0.2):
        tool_radius = self.tool_diam / 2 / self.target_res
        worker: ComputeWorker = ComputeWorker(self.target_res, image, self.img_res, self.tool_diam)
        self.ctx.finish()
        currentLoc = np.array([0.0, 0.0])
        current_direction = 0.0
        locations = []
        current_island = worker.island_list[0][2]
        try:
            (new_direction, link_locs) = self.navigate_link(worker, current_island,
                                                                tool_radius, dist_inc,
                                                                material_removal_ratio,
                                                                currentLoc)
        except:
            raise Exception("No paths could be generated for this layer.")

        for move in link_locs:
            locations.append(move)
        
        currentLoc = locations[-1][-1][-1] / self.target_res
        current_direction = new_direction

        #Generate Paths for an additive slice
        layer_completed = False
        for i in range(10):
            if i % 100 == 0:
                print(f"Link Iteration: {i}")
            #Initiate Cutting
            cut_moves, _last_dir = self.cutting_move(worker=worker, startLoc=currentLoc, 
                                                     start_dir=current_direction,
                                                     dist_inc=dist_inc,
                                                     material_removal_ratio=0.2)
            locations.append((0, cut_moves))
            before_cut_loc = currentLoc
            currentLoc = cut_moves[-1] / self.target_res

            try:
                (current_direction, link_locs) = self.navigate_link(worker, current_island,
                                                                    tool_radius, dist_inc,
                                                                    material_removal_ratio,
                                                                    before_cut_loc)
                for move in link_locs:
                    locations.append(move)

                currentLoc = locations[-1][-1][-1] / self.target_res
                current_direction = new_direction
            except Exception as error:
                print(error)
                print("Layer is complete")
                print(i)
                layer_completed = True


            if layer_completed:
                break

        return locations

    def navigate_link(self, worker, current_island,
                      tool_radius, dist_inc,
                      material_removal_ratio,
                      origin_loc):
        link_locations = worker.find_link_locations(current_island).copy()
        link_coords = na.search_link_points(link_locations, np.flip(origin_loc)).astype('int32')
        bool_array = link_coords == np.array([-1, -1])
        seed_cut_loc = np.array([-1, -1])
        current_direction = -1.0
        locations = []
        counter = 0
        while not np.any(bool_array):
            found_direction = False
            #Determine direction to start in
            #image = Image.fromarray(link_locations)
            #image.save(f"./renders/linkData{counter:08d}.png")
            candidates = self.checkCuts(worker, np.flip(link_coords),
                                        direction=0.0,
                                        tool_rad=tool_radius,
                                        deg_inc=1.0,
                                        iterations=360,
                                        distance=dist_inc / self.target_res,
                                        clockwiseScan=False)

            for i, candidate in enumerate(candidates[1][:, :]):
                if candidate[0] < 1 and candidate[1] < 1:
                    ratio = 0.0
                    if candidate[3] < 1: #If no empty space, ratio is 1.0
                        ratio = 1.0
                    else:
                        ratio = candidate[2] / candidate[3]
                    if ratio < material_removal_ratio and ratio > 0.00001:
                        seed_cut_loc = candidates[0][i]
                        current_direction = candidates[2][i]
                        found_direction = True
                        break

            if not found_direction:
                link_locations[link_coords[0]][link_coords[1]][1] = 0
                link_locations[link_coords[0]][link_coords[1]][3] = 0
                link_coords = na.search_link_points(link_locations, origin_loc).astype('int32')
                bool_array = link_coords == np.array([-1, -1])
                counter += 1
                continue

            #Check if chosen link movement needs to retract
            currentLoc = np.flip(link_coords)
            stats = worker.check_cut(np.flip(currentLoc), np.flip(link_coords), tool_radius)
            if stats[0] < 1 and stats[1] < 1:
                locations.append((1, currentLoc * self.target_res))
            else:
                locations.append((2, currentLoc * self.target_res))

            worker.make_cut(np.flip(currentLoc), np.flip(seed_cut_loc), tool_radius)
            currentLoc = seed_cut_loc
            locations.append((0, [currentLoc * self.target_res]))
            break

        if np.any(bool_array):
            raise Exception("Cannot Find a new link location.")

        return (current_direction, locations)
