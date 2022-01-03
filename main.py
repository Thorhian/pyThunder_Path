#!/usr/bin/env python3

import sys
import os
import numpy as np
from stl import mesh
from PIL import Image

from job import Job
from Discretized_Model import DiscretizedModel as DModel
import Helper_Functions as hf

# Units should be in Metric.
target_res_per_pixel = 0.1 #Width/Height of each pixel

for arg in sys.argv:
    if arg == '--help' or arg == '-h':
        hf.print_help()
        sys.exit()

if len(sys.argv) <= 3:
    print("Please specify an STL file, depth of cut, and tool diameter (in mm).\n")
    sys.exit()

#Load STL File
stlFileName = sys.argv[1]
model_mesh = mesh.Mesh.from_file(stlFileName, speedups=False)

depth_of_cut = float(sys.argv[2])
tool_diameter = float(sys.argv[3])

newJob = Job(model_mesh, [], tool_diameter, target_res=target_res_per_pixel)
print(newJob.bounds)
job_renders = newJob.render_layers(depth_of_cut)

#Convert byte buffers to Numpy arrays.
image_res = (newJob.img_res[1], newJob.img_res[0], 4)
d_model = DModel(target_res_per_pixel)
for render in job_renders:
    array = np.frombuffer(render, dtype='u1')
    array = np.reshape(array, image_res)
    array = np.flip(array, 0)
    d_model.add_layer(array, 0)


if not os.path.exists("renders"):
    os.makedirs("renders")

counter = 0
for render in job_renders:
    print(f"Saving image {counter}")
    image = Image.frombytes('RGBA', newJob.fbo3.size,
                            render, 'raw', 'RGBA', 0, -1)
    image.save(f"./renders/layer{counter}.png")
    counter += 1
