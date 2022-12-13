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
                  offset_coord=origin_point,
                  debug=True)

    new_job.render_layers(depth_of_cut)
    path_data = new_job.generate_paths(dist_inc=2.0, material_removal_ratio=0.4)
    new_job.save_images()
    stock_height = new_job.bounds[-1]
    retract_height = 10 + stock_height
    response_message = {"safe_retract": retract_height}
    response_data = []

    for layer, height in path_data: 
        layer_chains = []
        for path_chain in layer:
            match path_chain[0]:
                case 0:
                    cut_chain = []
                    for cut_move in path_chain[1]:
                        converted_chain = cut_move.tolist()
                        cut_chain.append(converted_chain)
                    layer_chains.append([0, cut_chain])
                case 1:
                    converted_chain = [1, path_chain[1].tolist()]
                    layer_chains.append(converted_chain)
                case 2:
                    converted_chain = [2, path_chain[1].tolist()]
                    layer_chains.append(converted_chain)
                case _:
                    pass

        
        response_data.append([layer_chains, height])
        print(layer_chains[0])

    response_message['tool_paths'] = response_data
    response_message['job_name'] = job_name

    out_queue.put(response_message)
    print(f"Ending Job Process")
