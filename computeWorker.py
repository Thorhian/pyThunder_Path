
import Helper_Functions as hf
import moderngl
import numpy as np

class ComputeWorker:
    '''
    A class to represent a worker process/thread. Should be able to take
    and image and 
    '''
    def __init__(self,
            pixel_res: float,
            target_image: np.ndarray,
            ):
        self.pixel_res = pixel_res
        self.target_image = target_image
        self.ctx = moderngl.create_standalone_context()
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.image_res = target_image.shape

        count_program = hf.load_shader("./shaders/count_colors.glsl")
        self.counter_compute = self.ctx.compute_shader(count_program)
        self.counter_compute['imageSize'] = self.image_res[0], self.image_res[1]
        self.image_buffer = self.ctx.texture(self.target_image, 4)
        self.image_buffer.bind_to_image(1)
        self.counter_compute['imageSlise'] = 1

        image_vertex_code = hf.load_shader("./shaders/image_shader.vert")
        paint_frag_code = hf.load_shader("./shaders/painter.frag")
        self.painter_prog = self.ctx.program(vertex_shader=image_vertex_code,
                fragment_shader=paint_frag_code)
        
        image_vertices = np.array([
            -1, 1,
            -1, -1,
            1, 1,
            1, -1,
        ], dtype='f4')
        imageVerts_vbo = self.ctx.buffer(image_vertices)
        self.painter_vao = self.ctx.vertex_array(self.painter_prog, [
            (imageVerts_vbo, '2f', 'in_position')
            ])
