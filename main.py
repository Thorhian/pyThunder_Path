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

vert_shader = open("./v_shader.vert")
frag_shader = open("./frag_shader.frag")

prog = ctx.program(vertex_shader=vert_shader,
                   fragment_shader=frag_shader)

x = np.linspace(-1.0, 1.0, 50)
y = np.random.rand(50) - 0.5
r = np.ones(50)
g = np.zeros(50)
b = np.zeros(50)

vertices = np.dstack([x, y, r, g, b])

vbo = ctx.buffer(vertices.astype('f4').tobytes())
vao = ctx.simple_vertex_array(prog, vbo, 'inVert', 'inColor')

fbo = ctx.simple_framebuffer((512, 512))
fbo.use()
fbo.clear(0.0, 0.0, 0.0, 1.0)
vao.render(moderngl.LINE_STRIP)

Image.frombytes('RGB', fbo.size, fbo.read(), 'raw', 'RGB', 0, -1).show()
