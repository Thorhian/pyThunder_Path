#version 330

in vec3 v_color;

out vec3 f_color;

float near = 0.1;
float far = 20;

//https://learnopengl.com/Advanced-OpenGL/Depth-testing
float LinearizeDepth(float depth)
{
    float z = depth * 2.0 - 1.0; // back to NDC
    return (2.0 * near * far) / (far + near - z * (far - near));
}

void main() {
    vec3 newColor = vec3(v_color.r +  sqrt(gl_FragCoord.z), v_color.gb);
    f_color = newColor;
}
