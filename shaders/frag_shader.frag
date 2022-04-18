#version 330

in vec4 v_color;

out vec4 f_color;

float near = 0.1;
float far = 20;

//https://learnopengl.com/Advanced-OpenGL/Depth-testing
float LinearizeDepth(float depth)
{
    float z = depth * 2.0 - 1.0; // back to NDC
    return (2.0 * near * far) / (far + near - z * (far - near));
}

void main() {
    vec4 newColor;
    if(v_color.b > 0.90) {
        newColor = vec4(v_color.r +  sqrt(gl_FragCoord.z), v_color.gba);
    } else {
        newColor = v_color;
    }
    f_color = newColor;
}
