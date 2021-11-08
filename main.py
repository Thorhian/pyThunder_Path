#!/usr/bin/env python3

import sys
import numpy as np
from stl import mesh
import moderngl
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
line_count = 100
z = np.linspace(-5, 1.0, line_count)
x = np.cos(z)
y = np.sin(z)
r = np.ones(line_count)
g = np.zeros(line_count)
b = np.zeros(line_count)

vertices = np.dstack([x, y, r, g, b])

vbo = ctx.buffer(vertices.astype('f4').tobytes())
vao = ctx.simple_vertex_array(prog, vbo, 'in_vert', 'in_color')

fbo = ctx.simple_framebuffer((512, 512))
fbo.use()
fbo.clear(0.0, 0.0, 0.0, 1.0)
vao.render(moderngl.LINE_STRIP)

Image.frombytes('RGB', fbo.size, fbo.read(), 'raw', 'RGB', 0, -1).show()
