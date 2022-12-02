#!/usr/bin/env python3

import socket
import sys
import os
import json
from stl import mesh
import numpy as np

import Helper_Functions as hf

HEADERSIZE = 12

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

tcp_socket = socket.create_connection((socket.gethostname(), 43200))

#Load STL File Target Model
stlTargetModel = os.path.abspath(sys.argv[1])
target_mesh = mesh.Mesh.from_file(stlTargetModel, speedups=False)

#Load STL File Stock Model
stlStockModel = os.path.abspath(sys.argv[2])
stock_mesh = mesh.Mesh.from_file(stlStockModel, speedups=False)

depth_of_cut = float(sys.argv[3])
tool_diameter = float(sys.argv[4])

try:
    while True:
        try:
            data = input(">_ ")
        except:
            break

        if data == "/sendJob":
            job_name = "Test Job"
            file_size = os.path.getsize(sys.argv[1])
            target_verts = target_mesh.vectors
            target_normals = target_mesh.normals
            stock_verts = stock_mesh.vectors
            stock_normals = stock_mesh.normals
            msg = {
                "type": "job",
                "job_name": job_name,
                "target_verts": target_verts.tolist(),
                "target_normals": target_normals.tolist(),
                "stock_verts": stock_verts.tolist(),
                "stock_normals": stock_normals.tolist(),
                "tool_diameter": tool_diameter,
                "depth_of_cut": depth_of_cut,
                "origin_point": [0.0, 0.0],
            }
            msg_json = json.dumps(msg).encode('utf-8')
            msg_json_size = len(msg_json)
            msg_json = bytes(f'{msg_json_size:<{HEADERSIZE}}', "utf-8") + msg_json
            tcp_socket.sendall(msg_json)

            print(f"Waiting for response...")
            path_data : bytes = b''
            new_msg = True
            msglen = 0
            while True:
                chunk = tcp_socket.recv(2048)

                if(chunk == b''):
                    break

                if new_msg:
                    msglen = int(chunk[:HEADERSIZE])
                    print(f"Data Arriving, Length: {msglen}")
                    new_msg = False

                path_data += chunk

                if len(path_data) - HEADERSIZE == msglen:
                    path_data = json.loads(path_data[HEADERSIZE:].decode('utf-8'))
                    finished_paths = []
                    for path_chain in path_data:
                        match path_chain[0]:
                            case 0:
                                converted_chain = (0, np.array(path_chain[1]))
                                finished_paths.append(converted_chain)
                            case 1:
                                converted_chain = (1, np.array(path_chain[1]))
                                finished_paths.append(converted_chain)
                            case 2:
                                converted_chain = (2, np.array(path_chain[1]))
                                finished_paths.append(converted_chain)
                            case _:
                                pass

                    print(finished_paths)
                    hf.gen_test_gcode(finished_paths)
                    break

        else:
            msg = {
                "type": "message",
                "contents": data,
            }
            msg_json = json.dumps(msg).encode('utf-8')
            data = bytes(f'{len(msg_json):<{HEADERSIZE}}', "utf-8") + msg_json
            tcp_socket.sendall(data)

finally:
    print("Closing socket")
    tcp_socket.close()
