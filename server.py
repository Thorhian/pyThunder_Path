import multiprocessing
import threading
import socket
import json
import numpy as np
from job import Job

import Job_Process

HEADERSIZE = 12


def handle_connection(connection, client):
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

                    to_job_process = multiprocessing.Queue()
                    from_job_process = multiprocessing.Queue()

                    job_process = multiprocessing.Process(target=Job_Process.new_job_process,
                                                          args=(to_job_process, from_job_process),
                                                          daemon=True)

                    job_process.start()

                    to_job_process.put(data)
                    response_data = from_job_process.get(block=True)
                    job_process.join()
                     

                    print(f"Sending paths back to {client}")
                    response_data = json.dumps(response_data).encode('utf-8')
                    header_data = bytes(f"{len(response_data):<{HEADERSIZE}}", "utf-8")
                    connection.sendall(header_data + response_data)
                    

                new_msg = True
                data = b''

    finally:
        connection.close()
### End Connection Handle Function

tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server_address = (socket.gethostname(), 43200)
tcp_socket.bind(server_address)


tcp_socket.listen(2)

while True:
    print("Waiting for connection")
    connection, client = tcp_socket.accept()
    print("Connected to client IP: {}".format(client))
    threading.Thread(target=handle_connection, args=(connection, client), daemon=True).start()

