#!/usr/bin/env python3

import sys
import os
from stl import mesh
from PIL import Image

from job import Job

# Units should be in Metric.
tool_diameter = float(8.0)
target_res_per_pixel = 0.1 #Width/Height of each pixel

if len(sys.argv) <= 2:
    print("Please specify an STL file and depth of cut.\n")
    sys.exit()

#Load STL File
stlFileName = sys.argv[1]
model_mesh = mesh.Mesh.from_file(stlFileName)

depth_of_cut = float(sys.argv[2])

newJob = Job(model_mesh, [], tool_diameter, target_res=target_res_per_pixel)
print(newJob.bounds)
job_renders = newJob.render_layers(depth_of_cut)

if not os.path.exists("renders"):
    os.makedirs("renders")

counter = 0
for render in job_renders:
    print(f"Saving image {counter}")
    render.save(f"./renders/layer{counter}.png")
    counter += 1
