#!/usr/bin/env python3

import sys
import numpy as np
from stl import mesh
import moderngl
import glm
from PIL import Image

import Helper_Functions as hf

# Units should be in Metric.
tool_diameter = float(8.0)

if len(sys.argv) <= 1:
    print("Please specify an STL file.\n")
    sys.exit()

#Load STL File
stlFileName = sys.argv[1]
model_mesh = mesh.Mesh.from_file(stlFileName)
model_size = model_mesh.vectors.size
image_resolution = (1024, 1024)
aspect_ratio = hf.calculate_aspect_ratio(image_resolution)
model_min_max = hf.get_model_min_max(model_mesh)
print(model_min_max)

#Create OpenGL context
ctx = moderngl.create_standalone_context()

#Load shader code files
vert_shader = hf.load_shader("./v_shader.vert")
frag_shader = hf.load_shader("./frag_shader.frag")

#Create OpenGL program with loaded shaders, compile
prog = ctx.program(vertex_shader=vert_shader,
                   fragment_shader=frag_shader)

#Set model color
r = np.zeros(model_size)
g = np.zeros(model_size)
b = np.ones(model_size)
color_values = np.dstack([r, g, b])

#Flatten array of vertices from the stl and prepare for opengl
model_vertices = model_mesh.vectors.flatten().astype('f4').tobytes()

#Create Texture(s)
firstPass = ctx.texture(image_resolution, 4)
firstPassDepth = ctx.depth_texture(image_resolution)

ctx.enable(moderngl.DEPTH_TEST)

#Create Orthographic Projection Matrix and View Matrix
prog["projectionMatrix"].write(glm.ortho(-100, 100, -100, 100, -150, 200))
prog["viewMatrix"].write(glm.rotate(hf.deg_to_rad(0), glm.vec3(1.0, 0.0, 0.0)))

#Create buffers for model vertices and color values
vbo = ctx.buffer(model_vertices)
color_buffer = ctx.buffer(color_values.astype('f4').tobytes())

#Create Vertex Array Object
vao = ctx.vertex_array(prog, [
    (vbo, '3f', 'in_vert'),
    (color_buffer, '3f', 'in_color'),
    ])

#Create, use, and render to Framebuffer Object (FBO)
fbo = ctx.framebuffer([firstPass], firstPassDepth)
fbo.use()
fbo.clear(0.0, 0.0, 0.0, 1.0)
vao.render(moderngl.TRIANGLES)

#Render image from FBO
final_render = Image.frombytes('RGB', fbo.size, fbo.read(), 'raw', 'RGB', 0, -1)

final_render.save("./temp.png")
final_render.show()
