#!/usr/bin/env python3

import sys
import os
from stl import mesh

from job import Job
import Helper_Functions as hf
import cProfile



isDebugModeOn = False
# Units should be in Metric.
target_res_per_pixel = 0.2 #Width/Height of each pixel

for arg in sys.argv:
    if arg == '--help' or arg == '-h':
        hf.print_help()
        sys.exit()
    if arg == '--debug' or arg == '-d':
        isDebugModeOn = True

if len(sys.argv) <= 3:
    print("Please specify an STL file, depth of cut, and tool diameter (in mm).\n")
    sys.exit()


#Load STL File Target Model
stlTargetModel = os.path.abspath(sys.argv[1])
model_mesh = mesh.Mesh.from_file(stlTargetModel, speedups=False).vectors

#Load STL File Stock Model
stlStockModel = os.path.abspath(sys.argv[2])
stock_mesh = mesh.Mesh.from_file(stlStockModel, speedups=False).vectors

depth_of_cut = float(sys.argv[3])
tool_diameter = float(sys.argv[4])
x_coord = float(sys.argv[5])
y_coord = float(sys.argv[6])
z_coord = float(sys.argv[7])
offset_coord = [x_coord, y_coord, z_coord]

newJob = Job(model_mesh, stock_mesh, [],
             tool_diameter, target_res=target_res_per_pixel,
             offset_coord=offset_coord,
             debug=isDebugModeOn)

def generate_paths():
    newJob.render_layers(depth_of_cut)
    newJob.save_images()
    paths = newJob.generate_paths(dist_inc=2.0, material_removal_ratio=0.4)
    stock_height = newJob.bounds[-1]
    retract_height = 10 + stock_height
    hf.gen_test_gcode(paths, retract_height)

if isDebugModeOn:
    cProfile.run('generate_paths()', filename='stats')
else:
    generate_paths()
