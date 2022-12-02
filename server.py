import socket
import json
import numpy as np
from job import Job

HEADERSIZE = 12

tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server_address = (socket.gethostname(), 43200)
tcp_socket.bind(server_address)

tcp_socket.listen(2)

while True:
    print("Waiting for connection")
    connection, client = tcp_socket.accept()
    print("Connected to client IP: {}".format(client))
    data = b''
    new_msg = True
    msglen = 0

    try:
        while True:
            chunk = connection.recv(2048)
            if(chunk == b''):
                break
            if new_msg:
                msglen = int(chunk[:HEADERSIZE])
                print(f"Data Arriving, Length: {msglen}")
                new_msg = False

            data += chunk

            if len(data) - HEADERSIZE == msglen:
                data = data[HEADERSIZE:].decode('utf-8')
                print(f"Parsing JSON Data")
                data = json.loads(data)
                print(f"Finished Parsing JSON Data")
                if data["type"] == "message":
                    print(data["contents"])
                elif data["type"] == "job":
                    job_name = data["job_name"]
                    target_verts = np.array(data["target_verts"])
                    target_normals = np.array(data["target_normals"])
                    stock_verts = np.array(data["stock_verts"])
                    stock_normals = np.array(data["stock_normals"])
                    tool_diameter = data["tool_diameter"]
                    depth_of_cut = data["depth_of_cut"]
                    origin_point = np.array(data["origin_point"])
                    target_res = 0.2

                    new_job = Job(target_verts, stock_verts, [],
                                  tool_diameter, target_res=target_res,
                                  debug=True)

                    new_job.render_layers(depth_of_cut)
                    path_data = new_job.generate_paths()
                    new_job.save_images()

                    print(f"Sending paths back to {client}")

                    response_data = []
                    
                    for path_chain in path_data:
                        match path_chain[0]:
                            case 0:
                                converted_chain = [0, path_chain[1].tolist()]
                                response_data.append(converted_chain)
                            case 1:
                                converted_chain = [1, path_chain[1].tolist()]
                                response_data.append(converted_chain)
                            case 2:
                                converted_chain = [2, path_chain[1].tolist()]
                                response_data.append(converted_chain)
                            case _:
                                pass

                    response_data = json.dumps(response_data).encode('utf-8')
                    header_data = bytes(f"{len(response_data):<{HEADERSIZE}}", "utf-8")
                    connection.sendall(header_data + response_data)
                    

                new_msg = True
                data = b''

    finally:
        connection.close()

