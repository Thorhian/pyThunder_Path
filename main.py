#!/usr/bin/env python3

import sys
from stl import mesh
from PIL import Image

from job import Job

# Units should be in Metric.
tool_diameter = float(8.0)
target_res_per_pixel = 0.1 #Width/Height of each pixel

if len(sys.argv) <= 1:
    print("Please specify an STL file.\n")
    sys.exit()

#Load STL File
stlFileName = sys.argv[1]
model_mesh = mesh.Mesh.from_file(stlFileName)

newJob = Job(model_mesh, [], tool_diameter, target_res=target_res_per_pixel)
print(newJob.bounds)
print(newJob.model_render_prog["projectionMatrix"].value)
newJob.render()
job_render = Image.frombytes('RGB', newJob.fbo3.size, newJob.fbo3.read(), 'raw', 'RGB', 0, -1)
job_render.save("./temp.png")
