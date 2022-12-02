import multiprocessing
import numpy as np
from job import Job

def new_job_process(in_queue : multiprocessing.Queue,
                    out_queue : multiprocessing.Queue):
    job_data = in_queue.get(block=True)
    job_name = job_data["job_name"]
    target_verts = np.array(job_data["target_verts"])
    target_normals = np.array(job_data["target_normals"])
    stock_verts = np.array(job_data["stock_verts"])
    stock_normals = np.array(job_data["stock_normals"])
    tool_diameter = job_data["tool_diameter"]
    depth_of_cut = job_data["depth_of_cut"]
    origin_point = np.array(job_data["origin_point"])
    target_res = 0.2

    new_job = Job(target_verts, stock_verts, [],
                  tool_diameter, target_res=target_res,
                  debug=True)

    new_job.render_layers(depth_of_cut)
    path_data = new_job.generate_paths()
    new_job.save_images()
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

    out_queue.put(response_data)
    print(f"Ending Job Process")
