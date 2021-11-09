#!/usr/bin/env python3

import sys
import numpy as np
from stl import mesh
import moderngl
import glm
from PIL import Image

# Units should be in Metric.
tool_diameter = float(8.0)
if len(sys.argv) <= 1:
    print("Please specify an STL file.\n")
    sys.exit()

stlFileName = sys.argv[1]
model_mesh = mesh.Mesh.from_file(stlFileName)
ctx = moderngl.create_standalone_context()

vert_shader_file = open("./v_shader.vert")
frag_shader_file = open("./frag_shader.frag")

with vert_shader_file as file:
    vert_shader = file.read()

with frag_shader_file as file:
    frag_shader = file.read()

vert_shader_file.close()
frag_shader_file.close()

prog = ctx.program(vertex_shader=vert_shader,
                   fragment_shader=frag_shader)
line_count = 300
z = np.linspace(-5, 5.0, line_count)
x = 2 * np.cos(z * 8)
y = 2 * np.sin(z * 8)
w = np.ones(line_count)
r = np.zeros(line_count)
g = np.zeros(line_count)
b = np.ones(line_count)
viewMatrix = glm.mat4

prog["projectionMatrix"].write(glm.ortho(-10, 10, -10, 10, -8, 8))
prog["viewMatrix"].write(glm.rotate(90, glm.vec3(1.0, 0.0, 0.0)))
vertices = np.dstack([x, y, z, w])
color_values = np.dstack([r, g, b])

vbo = ctx.buffer(vertices.astype('f4').tobytes())
color_buffer = ctx.buffer(color_values.astype('f4').tobytes())
vao = ctx.vertex_array(prog, [
    (vbo, '4f', 'in_vert'),
    (color_buffer, '3f', 'in_color'),
    ])

fbo = ctx.simple_framebuffer((512, 512))
fbo.use()
fbo.clear(0.0, 0.0, 0.0, 1.0)
vao.render(moderngl.LINE_STRIP)

Image.frombytes('RGB', fbo.size, fbo.read(), 'raw', 'RGB', 0, -1).show()
