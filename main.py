#!/usr/bin/env python3

import sys
import os
from stl import mesh
from PIL import Image

from job import Job

# Units should be in Metric.
target_res_per_pixel = 0.1 #Width/Height of each pixel

if len(sys.argv) <= 3:
    print("Please specify an STL file, depth of cut, and tool diameter (in mm).\n")
    sys.exit()

#Load STL File
stlFileName = sys.argv[1]
model_mesh = mesh.Mesh.from_file(stlFileName)

depth_of_cut = float(sys.argv[2])
tool_diameter = float(sys.argv[3])

newJob = Job(model_mesh, [], tool_diameter, target_res=target_res_per_pixel)
print(newJob.bounds)
job_renders = newJob.render_layers(depth_of_cut)

if not os.path.exists("renders"):
    os.makedirs("renders")

counter = 0
for render in job_renders:
    print(f"Saving image {counter}")
    image = Image.frombytes('RGB', newJob.fbo3.size,
                            render, 'raw', 'RGB', 0, -1)
    image.save(f"./renders/layer{counter}.png")
    counter += 1
