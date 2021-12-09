#!/usr/bin/env python3

import sys
import math
import numpy as np
from stl import mesh
import moderngl
import glm
from PIL import Image

import Helper_Functions as hf

# Units should be in Metric.
tool_diameter = float(8.0)
target_res_per_pixel = 0.1 #Width/Height of each pixel

tool_radius_adjusted = (tool_diameter / 2) / target_res_per_pixel

print(hf.bounding_box_circle((-200.0, 400.0), 8.0))

if len(sys.argv) <= 1:
    print("Please specify an STL file.\n")
    sys.exit()

#Load STL File
stlFileName = sys.argv[1]
model_mesh = mesh.Mesh.from_file(stlFileName)
model_size = model_mesh.vectors.size


#Calculate Bounding Box dimensions and Image Resolution
bounds = hf.get_model_min_max(model_mesh)
lower_bounds_with_margin = np.floor(bounds[0::2]) - math.ceil(tool_diameter + 5)
higher_bounds_with_margin = np.ceil(bounds[1::2]) + math.ceil(tool_diameter + 5)
image_res = (math.ceil((higher_bounds_with_margin[0] - lower_bounds_with_margin[0]) / target_res_per_pixel),
        math.ceil((higher_bounds_with_margin[1] - lower_bounds_with_margin[1]) / target_res_per_pixel))

#Calculates fairly exact pixel dimensions in mm, width and height
pixel_dimensions = (((higher_bounds_with_margin[0] - lower_bounds_with_margin[0]) / image_res[0]),
        ((higher_bounds_with_margin[1] - lower_bounds_with_margin[1]) / image_res[1]))

print((higher_bounds_with_margin[0] - lower_bounds_with_margin[0]),
        (higher_bounds_with_margin[1] - lower_bounds_with_margin[1]))
print(image_res)
print(pixel_dimensions)

#Create OpenGL context
ctx = moderngl.create_standalone_context()

#Load shader code files
vert_shader = hf.load_shader("./v_shader.vert")
frag_shader = hf.load_shader("./frag_shader.frag")

vert2_shader = hf.load_shader("./image_shader.vert")
frag2_shader = hf.load_shader("./image_shader.frag")

frag3_shader = hf.load_shader("./edge_expand.frag")

#Create OpenGL programs with loaded shaders, compile
prog1 = ctx.program(vertex_shader=vert_shader,
        fragment_shader=frag_shader)

prog2 = ctx.program(vertex_shader=vert2_shader,
        fragment_shader=frag2_shader)

prog3 = ctx.program(vertex_shader=vert2_shader,
                    fragment_shader=frag3_shader)

#Set model color
r = np.zeros(model_size)
g = np.zeros(model_size)
b = np.ones(model_size)
color_values = np.dstack([r, g, b])

#Flatten array of vertices from the stl and prepare for opengl
model_vertices = model_mesh.vectors.flatten().astype('f4').tobytes()

#Image Mesh for edge detection phase
image_vertices = np.array([
    -1, 1,
    -1, -1,
    1, 1,
    1, -1,
    ], dtype='f4')


#Create Texture(s)
firstPass = ctx.texture(image_res, 4)
firstPassDepth = ctx.depth_texture(image_res)

secondPass = ctx.texture(image_res, 4)
secondPassDepth = ctx.depth_texture(image_res)

ctx.enable(moderngl.DEPTH_TEST)

#Create Orthographic Projection Matrix and View Matrix
prog1["projectionMatrix"].write(glm.ortho(lower_bounds_with_margin[0],
    higher_bounds_with_margin[0],
    lower_bounds_with_margin[1],
    higher_bounds_with_margin[1],
    lower_bounds_with_margin[2],
    higher_bounds_with_margin[2]))
prog1["viewMatrix"].write(glm.rotate(hf.deg_to_rad(0), glm.vec3(1.0, 0.0, 0.0)))

prog2["prev_render"] = 4
firstPass.use(location=4)

prog3["prev_render"] = 3
secondPass.use(location=3)

prog3["cutterRadius"] = tool_radius_adjusted

#Create buffers for model vertices and color values
vbo = ctx.buffer(model_vertices)
color_buffer = ctx.buffer(color_values.astype('f4').tobytes())
image_vbo = ctx.buffer(image_vertices)

#Create Vertex Array Object
vao = ctx.vertex_array(prog1, [
    (vbo, '3f', 'in_vert'),
    (color_buffer, '3f', 'in_color'),
    ])

vao2 = ctx.vertex_array(prog2, [
    (image_vbo, '2f', 'in_position'),
    ])

vao3 = ctx.vertex_array(prog3, [
    (image_vbo, '2f', 'in_position'),
    ])

#Create, use, and render to Framebuffer Object (FBO)
fbo = ctx.framebuffer([firstPass], firstPassDepth)
fbo.use()
fbo.clear(0.0, 0.0, 0.0, 1.0)
vao.render(moderngl.TRIANGLES)

fbo2 = ctx.framebuffer([secondPass], secondPassDepth)
fbo2.use()
fbo2.clear(0.0, 0.0, 0.0, 1.0)
vao2.render(moderngl.TRIANGLE_STRIP)

fbo3 = ctx.simple_framebuffer(image_res)
fbo3.use()
fbo3.clear(0.0, 0.0, 0.0, 1.0)
vao3.render(moderngl.TRIANGLE_STRIP)

#Render image from FBO
final_render = Image.frombytes('RGB', fbo2.size, fbo3.read(), 'raw', 'RGB', 0, -1)

final_render.save("./temp.png")
#final_render.show()
