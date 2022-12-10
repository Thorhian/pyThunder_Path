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
ip_address = socket.gethostname()
for arg in sys.argv:
    if arg == '--help' or arg == '-h':
        hf.print_help()
        sys.exit()
    if arg == '--debug' or arg == '-d':
        isDebugModeOn = True
    if arg == '--address' or arg =='-a':
        ip_address = sys.argv[-1]

if len(sys.argv) <= 4:
    print("Please specify an STL file, depth of cut, and tool diameter (in mm).\n")
    sys.exit()

tcp_socket = socket.create_connection((ip_address, 4320))

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
                    path_message = json.loads(path_data[HEADERSIZE:].decode('utf-8'))
                    path_data = []
                    safe_retract = 0.0
                    if 'tool_paths' in path_message:
                        path_data = path_message['tool_paths']
                    else:
                        raise Exception(f"No paths returned")
                    if 'safe_retract' in path_message:
                        safe_retract = path_message['safe_retract']
                    else:
                        raise Exception(f"No retract height returned")

                    finished_paths = []
                    for layer, height in path_data:
                        print(f"Height: {height}")
                        print(f"First Link: {layer[0]}")
                        layer_chains = []
                        for path_chain in layer:
                            match path_chain[0]:
                                case 0:
                                    cut_chain = []
                                    for cut_move in path_chain[1]:
                                        converted_chain = np.array(cut_move)
                                        cut_chain.append(converted_chain)
                                    layer_chains.append((0, cut_chain))
                                case 1:
                                    converted_chain = (1, np.array(path_chain[1]))
                                    layer_chains.append(converted_chain)
                                case 2:
                                    converted_chain = (2, np.array(path_chain[1]))
                                    layer_chains.append(converted_chain)
                                case _:
                                    pass
                        finished_paths.append((layer_chains, height))

                    hf.gen_test_gcode(finished_paths, safe_retract)
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
